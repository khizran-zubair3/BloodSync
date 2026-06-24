from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Dict, Any
from app.database import get_db

router = APIRouter(prefix="/appointments", tags=["Appointments"])

# Helper: Insert a live notification into the notifications table
async def _notify(db: AsyncSession, message: str, ntype: str = "APPOINTMENT"):
    try:
        await db.execute(
            text("INSERT INTO notifications (message, type) VALUES (:msg, :ntype)"),
            {"msg": message, "ntype": ntype}
        )
    except Exception:
        pass  # Non-critical, don't break main operation


# 1. READ: Get all appointments (with Donor & Staff Name details using JOIN)
@router.get("/", response_model=List[Dict[str, Any]])
async def get_all_appointments(db: AsyncSession = Depends(get_db)):
    query = text("""
        SELECT 
            a.id, 
            a.appointment_date, 
            a.status,
            d.firstname AS donor_first, 
            d.lastname AS donor_last,
            s.firstname AS staff_first, 
            s.lastname AS staff_last
        FROM appointments a
        INNER JOIN donors d ON a.donor_id = d.id
        LEFT JOIN staff s ON a.staff_id = s.id
        ORDER BY a.appointment_date DESC
    """)
    result = await db.execute(query)
    appointments = []
    for r in result.fetchall():
        appointments.append({
            "id": r[0],
            "appointment_date": r[1].isoformat() if r[1] else None,
            "status": r[2],
            "donor_name": f"{r[3]} {r[4]}",
            "staff_name": f"{r[5]} {r[6]}" if r[5] else "Unassigned"
        })
    return appointments

# 2. CREATE: Book a new appointment
@router.post("/", status_code=status.HTTP_201_CREATED)
async def book_appointment(donor_id: int, appointment_date: str, staff_id: int = None, db: AsyncSession = Depends(get_db)):
    # Verify donor eligibility first using the DB Function
    eligibility_query = text("SELECT check_donor_eligibility(:d_id)")
    elig_res = await db.execute(eligibility_query, {"d_id": donor_id})
    is_eligible = elig_res.scalar()
    
    if not is_eligible:
        raise HTTPException(
            status_code=400, 
            detail="Donor is not eligible. Minimum 90 days wait period required since last donation."
        )

    query = text("""
        INSERT INTO appointments (donor_id, staff_id, appointment_date, status)
        VALUES (:donor_id, :staff_id, :app_date, 'Scheduled')
        RETURNING id, donor_id, appointment_date, status
    """)
    try:
        result = await db.execute(query, {
            "donor_id": donor_id,
            "staff_id": staff_id,
            "app_date": appointment_date
        })
        row = result.fetchone()
        await _notify(db, f"New appointment booked for donor #{donor_id}", "APPOINTMENT_BOOKED")
        await db.commit()
        return {"id": row[0], "donor_id": row[1], "appointment_date": row[2], "status": row[3]}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Booking failed: {str(e)}")

# 3. TRANSACTION / PROCEDURE CALL: Register Donation and update last donation date
@router.post("/{appointment_id}/complete-donation")
async def complete_donation(appointment_id: int, quantity_ml: int, db: AsyncSession = Depends(get_db)):
    """
    Marks appointment as completed, creates a DonationEvent, 
    and executes the Postgres stored procedure 'register_blood_donation' to log history.
    """
    try:
        # Fetch appointment details
        app_query = text("SELECT donor_id, staff_id FROM appointments WHERE id = :id FOR UPDATE")
        app_res = await db.execute(app_query, {"id": appointment_id})
        app_row = app_res.fetchone()
        
        if not app_row:
            raise HTTPException(status_code=404, detail="Appointment not found")
            
        donor_id, staff_id = app_row[0], app_row[1]

        # Get donor blood type
        donor_type_query = text("SELECT blood_type_id FROM donors WHERE id = :donor_id")
        type_res = await db.execute(donor_type_query, {"donor_id": donor_id})
        blood_type_id = type_res.scalar()

        # 1. Update appointment status to Completed
        await db.execute(
            text("UPDATE appointments SET status = 'Completed' WHERE id = :id"),
            {"id": appointment_id}
        )

        # 2. Insert into DonationEvent
        event_query = text("""
            INSERT INTO donation_events (appointment_id, name, eligibility_confirmed)
            VALUES (:app_id, 'Routine Donation Clinic Visit', true)
            RETURNING id
        """)
        event_res = await db.execute(event_query, {"app_id": appointment_id})
        donation_id = event_res.scalar()

        # 3. Call DB Stored Procedure atomically to update history and donor last donation date
        await db.execute(
            text("CALL register_blood_donation(:donor_id, :donation_id, :blood_type_id, :quantity)"),
            {
                "donor_id": donor_id,
                "donation_id": donation_id,
                "blood_type_id": blood_type_id,
                "quantity": quantity_ml
            }
        )
        
        await _notify(db, f"Donation completed via stored procedure for donor #{donor_id}", "DONATION_COMPLETED")
        await db.commit()
        return {"status": "success", "message": "Donation processed, last donation date updated via Stored Procedure!"}
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database Procedure Execution Failed: {str(e)}")
