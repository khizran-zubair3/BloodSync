from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Dict, Any
from app.database import get_db

router = APIRouter(prefix="/notifications", tags=["Notifications"])

# 1. READ: Get all alerts & notifications
@router.get("/", response_model=List[Dict[str, Any]])
async def get_notifications(db: AsyncSession = Depends(get_db)):
    # Automatically generate alerts for low blood stock (< 10 units) if we fetch alerts
    try:
        check_query = text("""
            SELECT bt.blood_group, SUM(bs.units_available) 
            FROM blood_stock bs
            INNER JOIN blood_types bt ON bs.blood_type_id = bt.id
            GROUP BY bt.blood_group
            HAVING SUM(bs.units_available) < 10
        """)
        low_res = await db.execute(check_query)
        for r in low_res.fetchall():
            blood_group, qty = r[0], r[1]
            # Write alert record if it doesn't already exist to prevent duplicates
            msg = f"Alert: Low stock level for {blood_group}. Only {qty} units remaining."
            dup_check = await db.execute(text("SELECT id FROM notifications WHERE message = :msg"), {"msg": msg})
            if not dup_check.fetchone():
                await db.execute(
                    text("INSERT INTO notifications (message, type) VALUES (:msg, 'CRITICAL_STOCK')"),
                    {"msg": msg}
                )
        await db.commit()
    except Exception:
        pass # If stock table is not seeded or query fails, skip auto-creation

    # Fetch alerts
    query = text("SELECT id, message, type FROM notifications ORDER BY id DESC LIMIT 30")
    result = await db.execute(query)
    alerts = []
    for r in result.fetchall():
        alerts.append({"id": r[0], "message": r[1], "type": r[2]})
    return alerts

# 2. CREATE: Manually post a notification
@router.post("/", status_code=201)
async def create_notification(message: str, type: str = "INFO", db: AsyncSession = Depends(get_db)):
    query = text("""
        INSERT INTO notifications (message, type) 
        VALUES (:message, :type) 
        RETURNING id, message, type
    """)
    result = await db.execute(query, {"message": message, "type": type})
    row = result.fetchone()
    await db.commit()
    return {"id": row[0], "message": row[1], "type": row[2]}

# 3. DELETE: Remove a notification
@router.delete("/{notification_id}", status_code=204)
async def delete_notification(notification_id: int, db: AsyncSession = Depends(get_db)):
    query = text("DELETE FROM notifications WHERE id = :id RETURNING id")
    result = await db.execute(query, {"id": notification_id})
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Notification not found")
    await db.commit()
    return None

# 4. GET: Count of unread/new notifications (for badge)
@router.get("/count")
async def get_notification_count(db: AsyncSession = Depends(get_db)):
    query = text("SELECT COUNT(*) FROM notifications")
    result = await db.execute(query)
    count = result.scalar()
    return {"count": count}
