from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List
from app.database import get_db
from app.models.schemas import DonorCreate, DonorResponse, DonorDetailsResponse

router = APIRouter(prefix="/donors", tags=["Donors"])

# Helper: Insert a live notification into the notifications table
async def _notify(db: AsyncSession, message: str, ntype: str = "DONOR"):
    try:
        await db.execute(
            text("INSERT INTO notifications (message, type) VALUES (:msg, :ntype)"),
            {"msg": message, "ntype": ntype}
        )
    except Exception:
        pass  # Non-critical, don't break main operation

# ----------------------------------------------------------------------------
# 1. READ: Get All Donors (Using JOIN query to retrieve Blood Group & Category)
# ----------------------------------------------------------------------------
@router.get("/", response_model=List[DonorDetailsResponse])
async def get_all_donors(db: AsyncSession = Depends(get_db)):
    """
    Retrieve all donors with associated blood groups and donor categories.
    Demonstrates a complex multi-table SQL INNER JOIN / LEFT JOIN.
    """
    query = text("""
        SELECT 
            d.id, 
            d.firstname, 
            d.lastname, 
            bt.blood_group, 
            dc.category_name, 
            d.last_donation_date, 
            d.customer_phone
        FROM donors d
        LEFT JOIN blood_types bt ON d.blood_type_id = bt.id
        LEFT JOIN donor_categories dc ON d.donor_category_id = dc.id
        ORDER BY d.id DESC
    """)
    
    result = await db.execute(query)
    # Convert Row mapping to list of dictionaries compatible with Pydantic
    donors_list = []
    for row in result.fetchall():
        donors_list.append({
            "id": row[0],
            "firstname": row[1],
            "lastname": row[2],
            "blood_group": row[3],
            "category_name": row[4],
            "last_donation_date": row[5],
            "customer_phone": row[6]
        })
    return donors_list

# ----------------------------------------------------------------------------
# 2. CREATE: Register New Donor
# ----------------------------------------------------------------------------
@router.post("/", response_model=DonorResponse, status_code=status.HTTP_201_CREATED)
async def create_donor(donor: DonorCreate, db: AsyncSession = Depends(get_db)):
    """
    Inserts a new donor record into the database.
    """
    query = text("""
        INSERT INTO donors (
            user_id, blood_type_id, firstname, lastname, 
            customer_phone, eligibility_state, last_donation_date, address, donor_category_id
        ) VALUES (
            :user_id, :blood_type_id, :firstname, :lastname, 
            :customer_phone, :eligibility_state, :last_donation_date, :address, :donor_category_id
        ) RETURNING id, user_id, blood_type_id, firstname, lastname, customer_phone, eligibility_state, last_donation_date, address, donor_category_id
    """)
    
    try:
        result = await db.execute(query, {
            "user_id": donor.user_id,
            "blood_type_id": donor.blood_type_id,
            "firstname": donor.firstname,
            "lastname": donor.lastname,
            "customer_phone": donor.customer_phone,
            "eligibility_state": donor.eligibility_state,
            "last_donation_date": donor.last_donation_date,
            "address": donor.address,
            "donor_category_id": donor.donor_category_id
        })
        new_row = result.fetchone()
        
        if not new_row:
            raise HTTPException(status_code=400, detail="Failed to create donor")
        
        # Live Notification
        await _notify(db, f"New donor registered: {donor.firstname} {donor.lastname}", "DONOR_ADDED")
        
        await db.commit()
        return {
            "id": new_row[0],
            "user_id": new_row[1],
            "blood_type_id": new_row[2],
            "firstname": new_row[3],
            "lastname": new_row[4],
            "customer_phone": new_row[5],
            "eligibility_state": new_row[6],
            "last_donation_date": new_row[7],
            "address": new_row[8],
            "donor_category_id": new_row[9]
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Database Integrity Error: {str(e)}")

# ----------------------------------------------------------------------------
# 3. READ: Get Donor By ID
# ----------------------------------------------------------------------------
@router.get("/{donor_id}", response_model=DonorResponse)
async def get_donor(donor_id: int, db: AsyncSession = Depends(get_db)):
    """
    Fetch a single donor's details by their database ID.
    """
    query = text("SELECT * FROM donors WHERE id = :id")
    result = await db.execute(query, {"id": donor_id})
    row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Donor not found")
        
    return {
        "id": row[0],
        "user_id": row[1],
        "blood_type_id": row[2],
        "firstname": row[3],
        "lastname": row[4],
        "customer_phone": row[5],
        "eligibility_state": row[6],
        "last_donation_date": row[7],
        "address": row[8],
        "donor_category_id": row[9]
    }

# ----------------------------------------------------------------------------
# 4. UPDATE: Modify Existing Donor
# ----------------------------------------------------------------------------
@router.put("/{donor_id}", response_model=DonorResponse)
async def update_donor(donor_id: int, donor: DonorCreate, db: AsyncSession = Depends(get_db)):
    """
    Update donor attributes (name, phone, address, eligibility, etc.).
    """
    query = text("""
        UPDATE donors 
        SET blood_type_id = :blood_type_id, 
            firstname = :firstname, 
            lastname = :lastname, 
            customer_phone = :customer_phone, 
            eligibility_state = :eligibility_state, 
            last_donation_date = :last_donation_date, 
            address = :address, 
            donor_category_id = :donor_category_id
        WHERE id = :id
        RETURNING id, user_id, blood_type_id, firstname, lastname, customer_phone, eligibility_state, last_donation_date, address, donor_category_id
    """)
    
    result = await db.execute(query, {
        "id": donor_id,
        "blood_type_id": donor.blood_type_id,
        "firstname": donor.firstname,
        "lastname": donor.lastname,
        "customer_phone": donor.customer_phone,
        "eligibility_state": donor.eligibility_state,
        "last_donation_date": donor.last_donation_date,
        "address": donor.address,
        "donor_category_id": donor.donor_category_id
    })
    
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Donor not found or update failed")
    
    # Live Notification
    await _notify(db, f"Donor profile updated: {donor.firstname} {donor.lastname}", "DONOR_UPDATED")
    
    await db.commit()
    return {
        "id": row[0],
        "user_id": row[1],
        "blood_type_id": row[2],
        "firstname": row[3],
        "lastname": row[4],
        "customer_phone": row[5],
        "eligibility_state": row[6],
        "last_donation_date": row[7],
        "address": row[8],
        "donor_category_id": row[9]
    }

# ----------------------------------------------------------------------------
# 5. DELETE: Remove Donor Record
# ----------------------------------------------------------------------------
@router.delete("/{donor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_donor(donor_id: int, db: AsyncSession = Depends(get_db)):
    """
    Deletes a donor from the system.
    """
    # Get donor name before deleting for notification
    name_query = text("SELECT firstname, lastname FROM donors WHERE id = :id")
    name_res = await db.execute(name_query, {"id": donor_id})
    name_row = name_res.fetchone()
    
    query = text("DELETE FROM donors WHERE id = :id RETURNING id")
    result = await db.execute(query, {"id": donor_id})
    row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Donor not found")
    
    # Live Notification
    donor_name = f"{name_row[0]} {name_row[1]}" if name_row else f"ID#{donor_id}"
    await _notify(db, f"Donor removed from system: {donor_name}", "DONOR_DELETED")
    
    await db.commit()
    return None
