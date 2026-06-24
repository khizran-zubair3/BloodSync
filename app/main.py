from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Dict, Any
import os

from app.database import get_db
from app.routes import donors, stock, requests, staff, appointments, tests, notifications, analytics, auth
from app.models.schemas import DonorDetailsResponse

app = FastAPI(
    title="BloodSync Blood Bank Management System",
    description="A professional-grade backend for university project demonstration.",
    version="1.0.0"
)

# Enable CORS for frontend API calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include real PostgreSQL routes
app.include_router(auth.router, prefix="/api")
app.include_router(donors.router, prefix="/api")
app.include_router(stock.router, prefix="/api")
app.include_router(requests.router, prefix="/api")
app.include_router(staff.router, prefix="/api")
app.include_router(appointments.router, prefix="/api")
app.include_router(tests.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")

# Serve the frontend templates folder statically so the browser can perform local API requests
app.mount("/templates", StaticFiles(directory="templates"), name="templates")

# Automatically seed lookup tables (blood_types and donor_categories) on startup
@app.on_event("startup")
async def startup_event():
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        try:
            # Check if blood types are empty
            check_bt = await session.execute(text("SELECT COUNT(*) FROM blood_types"))
            if check_bt.scalar() == 0:
                print("Seeding blood types...")
                groups = ['O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-']
                for g in groups:
                    await session.execute(text("INSERT INTO blood_types (blood_group) VALUES (:g)"), {"g": g})
                await session.commit()

            # Check if donor categories are empty
            check_dc = await session.execute(text("SELECT COUNT(*) FROM donor_categories"))
            if check_dc.scalar() == 0:
                print("Seeding donor categories...")
                categories = [
                    ("Regular", "Donates blood at regular 3-month intervals."),
                    ("First-time", "First blood donation recorded in the system.")
                ]
                for cat, desc in categories:
                    await session.execute(
                        text("INSERT INTO donor_categories (category_name, description) VALUES (:cat, :desc)"),
                        {"cat": cat, "desc": desc}
                    )
                await session.commit()
        except Exception as e:
            print(f"Startup seeding warning (maybe tables are not created yet): {e}")
            await session.rollback()

from fastapi.responses import HTMLResponse, RedirectResponse

@app.get("/")
def get_root():
    return RedirectResponse(url="/templates/login.html")
