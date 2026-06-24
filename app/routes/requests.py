from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List
from app.database import get_db
from app.models.schemas import BloodRequestResponse, BloodRequestBase

router = APIRouter(prefix="/requests", tags=["Blood Requests"])

# Helper: Insert a live notification into the notifications table
async def _notify(db: AsyncSession, message: str, ntype: str = "REQUEST"):
    try:
        await db.execute(
            text("INSERT INTO notifications (message, type) VALUES (:msg, :ntype)"),
            {"msg": message, "ntype": ntype}
        )
    except Exception:
        pass  # Non-critical, don't break main operation


# 1. READ: Get All Requests
@router.get("/", response_model=List[BloodRequestResponse])
async def get_all_requests(db: AsyncSession = Depends(get_db)):
    query = text("SELECT * FROM blood_requests ORDER BY id DESC")
    result = await db.execute(query)
    req_list = []
    for r in result.fetchall():
        req_list.append({
            "id": r[0],
            "blood_type_id": r[1],
            "units_requested": r[2],
            "requester_id": r[3],
            "status": r[4]
        })
    return req_list

# 2. CREATE: Register Blood Request
@router.post("/", response_model=BloodRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_request(req: BloodRequestBase, db: AsyncSession = Depends(get_db)):
    query = text("""
        INSERT INTO blood_requests (blood_type_id, units_requested, requester_id, status)
        VALUES (:blood_type_id, :units_requested, :requester_id, :status)
        RETURNING id, blood_type_id, units_requested, requester_id, status
    """)
    result = await db.execute(query, {
        "blood_type_id": req.blood_type_id,
        "units_requested": req.units_requested,
        "requester_id": req.requester_id,
        "status": req.status
    })
    row = result.fetchone()
    await _notify(db, f"New blood request submitted (Type ID: {req.blood_type_id}, {req.units_requested} units)", "REQUEST_CREATED")
    await db.commit()
    return {
        "id": row[0],
        "blood_type_id": row[1],
        "units_requested": row[2],
        "requester_id": row[3],
        "status": row[4]
    }

# 3. TRANSACTION OPERATION: Atomic Request Fulfillment
@router.post("/{request_id}/fulfill", response_model=BloodRequestResponse)
async def fulfill_request(request_id: int, db: AsyncSession = Depends(get_db)):
    """
    Atomically process a blood request using a database transaction.
    Reduces inventory units, logs the movement, and updates request status.
    """
    # 1. Get Request Details
    req_query = text("SELECT blood_type_id, units_requested, status FROM blood_requests WHERE id = :id FOR UPDATE")
    req_res = await db.execute(req_query, {"id": request_id})
    req_row = req_res.fetchone()
    
    if not req_row:
        raise HTTPException(status_code=404, detail="Request not found")
        
    blood_type_id, units, current_status = req_row[0], req_row[1], req_row[2]
    
    if current_status == "Fulfilled":
        raise HTTPException(status_code=400, detail="Request is already fulfilled")

    # Start explicit transaction context (handled automatically by get_db or db.begin())
    try:
        # 2. Find eligible stock with sufficient units
        stock_query = text("""
            SELECT id, units_available 
            FROM blood_stock 
            WHERE blood_type_id = :bt_id AND units_available >= :units 
            ORDER BY expiry_date ASC LIMIT 1 FOR UPDATE
        """)
        stock_res = await db.execute(stock_query, {"bt_id": blood_type_id, "units": units})
        stock_row = stock_res.fetchone()
        
        if not stock_row:
            raise HTTPException(status_code=400, detail="Insufficient blood stock available for this blood group.")
            
        stock_id, available_units = stock_row[0], stock_row[1]
        
        # 3. Update stock quantity
        update_stock = text("""
            UPDATE blood_stock 
            SET units_available = units_available - :units 
            WHERE id = :stock_id
        """)
        await db.execute(update_stock, {"units": units, "stock_id": stock_id})
        
        # 4. Write Inventory Log
        log_query = text("""
            INSERT INTO inventory_logs (stock_id, action) 
            VALUES (:stock_id, :action)
        """)
        await db.execute(log_query, {"stock_id": stock_id, "action": f"DISPATCH_{units}_UNITS_FOR_REQ_{request_id}"})
        
        # 5. Update Request Status to 'Fulfilled'
        update_req = text("""
            UPDATE blood_requests 
            SET status = 'Fulfilled' 
            WHERE id = :id 
            RETURNING id, blood_type_id, units_requested, requester_id, status
        """)
        final_res = await db.execute(update_req, {"id": request_id})
        final_row = final_res.fetchone()
        
        await _notify(db, f"Blood request #{request_id} fulfilled — stock updated", "REQUEST_FULFILLED")
        
        # Commit the transaction
        await db.commit()
        
        return {
            "id": final_row[0],
            "blood_type_id": final_row[1],
            "units_requested": final_row[2],
            "requester_id": final_row[3],
            "status": final_row[4]
        }
        
    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Transaction Failed: {str(e)}")
