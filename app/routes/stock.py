from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List
from app.database import get_db
from app.models.schemas import BloodStockResponse, BloodStockBase

router = APIRouter(prefix="/stock", tags=["Blood Stock"])

# Helper: Insert a live notification into the notifications table
async def _notify(db: AsyncSession, message: str, ntype: str = "STOCK"):
    try:
        await db.execute(
            text("INSERT INTO notifications (message, type) VALUES (:msg, :ntype)"),
            {"msg": message, "ntype": ntype}
        )
    except Exception:
        pass  # Non-critical, don't break main operation


# 1. READ: Get All Stock
@router.get("/", response_model=List[BloodStockResponse])
async def get_all_stock(db: AsyncSession = Depends(get_db)):
    query = text("SELECT * FROM blood_stock ORDER BY id DESC")
    result = await db.execute(query)
    stock_list = []
    for r in result.fetchall():
        stock_list.append({
            "id": r[0],
            "blood_type_id": r[1],
            "units_available": r[2],
            "received_date": r[3],
            "expiry_date": r[4]
        })
    return stock_list

# 2. CREATE: Add Stock Entry
@router.post("/", response_model=BloodStockResponse, status_code=status.HTTP_201_CREATED)
async def create_stock(stock: BloodStockBase, db: AsyncSession = Depends(get_db)):
    query = text("""
        INSERT INTO blood_stock (blood_type_id, units_available, received_date, expiry_date)
        VALUES (:blood_type_id, :units_available, :received_date, :expiry_date)
        RETURNING id, blood_type_id, units_available, received_date, expiry_date
    """)
    result = await db.execute(query, {
        "blood_type_id": stock.blood_type_id,
        "units_available": stock.units_available,
        "received_date": stock.received_date,
        "expiry_date": stock.expiry_date
    })
    row = result.fetchone()
    await db.commit()
    
    # Write inventory log
    log_query = text("INSERT INTO inventory_logs (stock_id, action) VALUES (:stock_id, 'ADDITION')")
    await db.execute(log_query, {"stock_id": row[0]})
    await _notify(db, f"New blood stock added ({stock.units_available} units, Type ID: {stock.blood_type_id})", "STOCK_ADDED")
    await db.commit()
    
    return {
        "id": row[0],
        "blood_type_id": row[1],
        "units_available": row[2],
        "received_date": row[3],
        "expiry_date": row[4]
    }

# 3. UPDATE: Edit Stock
@router.put("/{stock_id}", response_model=BloodStockResponse)
async def update_stock(stock_id: int, stock: BloodStockBase, db: AsyncSession = Depends(get_db)):
    query = text("""
        UPDATE blood_stock
        SET blood_type_id = :blood_type_id,
            units_available = :units_available,
            received_date = :received_date,
            expiry_date = :expiry_date
        WHERE id = :id
        RETURNING id, blood_type_id, units_available, received_date, expiry_date
    """)
    result = await db.execute(query, {
        "id": stock_id,
        "blood_type_id": stock.blood_type_id,
        "units_available": stock.units_available,
        "received_date": stock.received_date,
        "expiry_date": stock.expiry_date
    })
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Stock entry not found")
    await db.commit()
    return {
        "id": row[0],
        "blood_type_id": row[1],
        "units_available": row[2],
        "received_date": row[3],
        "expiry_date": row[4]
    }

# 4. DELETE: Remove Stock Entry
@router.delete("/{stock_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_stock(stock_id: int, db: AsyncSession = Depends(get_db)):
    query = text("DELETE FROM blood_stock WHERE id = :id RETURNING id")
    result = await db.execute(query, {"id": stock_id})
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Stock entry not found")
    await _notify(db, f"Blood stock entry #{stock_id} removed from inventory", "STOCK_DELETED")
    await db.commit()
    return None
