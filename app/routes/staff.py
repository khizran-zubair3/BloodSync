from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List
from app.database import get_db
from app.models.schemas import StaffResponse, StaffCreate

router = APIRouter(prefix="/staff", tags=["Staff"])

# Helper: Insert a live notification into the notifications table
async def _notify(db: AsyncSession, message: str, ntype: str = "STAFF"):
    try:
        await db.execute(
            text("INSERT INTO notifications (message, type) VALUES (:msg, :ntype)"),
            {"msg": message, "ntype": ntype}
        )
    except Exception:
        pass  # Non-critical, don't break main operation


# 1. READ: Get All Staff
@router.get("/", response_model=List[StaffResponse])
async def get_all_staff(db: AsyncSession = Depends(get_db)):
    query = text("SELECT * FROM staff ORDER BY id DESC")
    result = await db.execute(query)
    staff_list = []
    for r in result.fetchall():
        staff_list.append({
            "id": r[0],
            "user_id": r[1],
            "blood_type_id": r[2],
            "firstname": r[3],
            "lastname": r[4],
            "status": r[5]
        })
    return staff_list

# 2. CREATE: Register Staff Member
@router.post("/", response_model=StaffResponse, status_code=status.HTTP_201_CREATED)
async def create_staff(staff: StaffCreate, role: str = "Staff", db: AsyncSession = Depends(get_db)):
    if role != "Admin":
        raise HTTPException(status_code=403, detail="Access denied: Only Admin users can add staff members")
    query = text("""
        INSERT INTO staff (user_id, blood_type_id, firstname, lastname, status)
        VALUES (:user_id, :blood_type_id, :firstname, :lastname, :status)
        RETURNING id, user_id, blood_type_id, firstname, lastname, status
    """)
    result = await db.execute(query, {
        "user_id": staff.user_id,
        "blood_type_id": staff.blood_type_id,
        "firstname": staff.firstname,
        "lastname": staff.lastname,
        "status": staff.status
    })
    row = result.fetchone()
    await _notify(db, f"New staff member registered: {staff.firstname} {staff.lastname}", "STAFF_ADDED")
    await db.commit()
    return {
        "id": row[0],
        "user_id": row[1],
        "blood_type_id": row[2],
        "firstname": row[3],
        "lastname": row[4],
        "status": row[5]
    }
