from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Dict, Any
from app.database import get_db

router = APIRouter(prefix="/tests", tags=["Blood Screening Tests"])

# Helper: Insert a live notification into the notifications table
async def _notify(db: AsyncSession, message: str, ntype: str = "TEST"):
    try:
        await db.execute(
            text("INSERT INTO notifications (message, type) VALUES (:msg, :ntype)"),
            {"msg": message, "ntype": ntype}
        )
    except Exception:
        pass  # Non-critical, don't break main operation


# 1. READ: Get all test outcomes with details of the donation history
@router.get("/", response_model=List[Dict[str, Any]])
async def get_all_tests(db: AsyncSession = Depends(get_db)):
    query = text("""
        SELECT 
            t.id, 
            t.disease_screened, 
            t.outcome, 
            t.tested_at,
            dh.id AS history_id,
            d.firstname, 
            d.lastname
        FROM blood_tests t
        INNER JOIN donation_histories dh ON t.donation_history_id = dh.id
        INNER JOIN donors d ON dh.donor_id = d.id
        ORDER BY t.tested_at DESC
    """)
    result = await db.execute(query)
    tests = []
    for r in result.fetchall():
        tests.append({
            "id": r[0],
            "disease_screened": r[1],
            "outcome": r[2],
            "tested_at": r[3].isoformat() if r[3] else None,
            "donation_history_id": r[4],
            "donor_name": f"{r[5]} {r[6]}"
        })
    return tests

# 2. CREATE: Register screening outcome and update blood history status
@router.post("/", status_code=status.HTTP_201_CREATED)
async def run_screening_test(donation_history_id: int, disease_screened: str, outcome: str, db: AsyncSession = Depends(get_db)):
    """
    Log results of screening tests (HIV, Hep B, etc.).
    If test outcome is 'Failed', we mark donation history as 'Discarded'.
    If it passes, we mark it as 'Processed'.
    """
    try:
        # Create test log
        test_query = text("""
            INSERT INTO blood_tests (donation_history_id, disease_screened, outcome)
            VALUES (:dh_id, :disease, :outcome)
            RETURNING id, donation_history_id, disease_screened, outcome, tested_at
        """)
        res = await db.execute(test_query, {
            "dh_id": donation_history_id,
            "disease": disease_screened,
            "outcome": outcome
        })
        row = res.fetchone()

        # Update donation history status
        hist_status = "Processed" if outcome == "Passed" else "Discarded"
        await db.execute(
            text("UPDATE donation_histories SET status = :status WHERE id = :dh_id"),
            {"status": hist_status, "dh_id": donation_history_id}
        )

        # If it passes, we also add the quantity to active blood stock!
        if outcome == "Passed":
            # Get quantity and blood type
            info_query = text("SELECT blood_type_id, quantity_ml FROM donation_histories WHERE id = :dh_id")
            info_res = await db.execute(info_query, {"dh_id": donation_history_id})
            info = info_res.fetchone()
            
            # Check if stock record exists for this blood type
            stock_check = text("SELECT id FROM blood_stock WHERE blood_type_id = :bt_id LIMIT 1")
            stock_res = await db.execute(stock_check, {"bt_id": info[0]})
            stock_row = stock_res.fetchone()
            
            units = max(1, round(info[1] / 450)) # standard bag is ~450ml
            
            if stock_row:
                # Update existing stock
                await db.execute(
                    text("UPDATE blood_stock SET units_available = units_available + :units WHERE id = :id"),
                    {"units": units, "id": stock_row[0]}
                )
                stock_id = stock_row[0]
            else:
                # Create new stock entry
                new_stock = text("""
                    INSERT INTO blood_stock (blood_type_id, units_available, expiry_date)
                    VALUES (:bt_id, :units, CURRENT_DATE + INTERVAL '42 days')
                    RETURNING id
                """)
                new_res = await db.execute(new_stock, {"bt_id": info[0], "units": units})
                stock_id = new_res.scalar()
                
            # Log inventory action
            await db.execute(
                text("INSERT INTO inventory_logs (stock_id, action) VALUES (:stock_id, 'ADDITION_VIA_SCREENING')"),
                {"stock_id": stock_id}
            )

        await _notify(db, f"Screening test recorded — {outcome} (Disease: {disease_screened})", "SCREENING_RESULT")
        await db.commit()
        return {
            "id": row[0],
            "donation_history_id": row[1],
            "disease_screened": row[2],
            "outcome": row[3],
            "tested_at": row[4].isoformat() if row[4] else None
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Screening registration failed: {str(e)}")

# 3. READ: Get active testing equipment status
@router.get("/equipment", response_model=List[Dict[str, Any]])
async def get_equipment(db: AsyncSession = Depends(get_db)):
    query = text("SELECT id, name, test_id FROM equipment ORDER BY id ASC")
    result = await db.execute(query)
    eq_list = []
    for r in result.fetchall():
        eq_list.append({"id": r[0], "name": r[1], "test_id": r[2]})
    return eq_list
