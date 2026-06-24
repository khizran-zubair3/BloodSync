import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://neondb_owner:npg_ErxNj8bPOR6G@ep-polished-sound-aq89y7xn-pooler.c-8.us-east-1.aws.neon.tech/neondb?sslmode=require"
)

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

if "?" in DATABASE_URL:
    clean_db_url = DATABASE_URL.split("?")[0]
else:
    clean_db_url = DATABASE_URL

DDL_SQL = """
-- ============================================================================
-- BloodSync Database Initialization Script
-- ============================================================================

DROP TABLE IF EXISTS notifications CASCADE;
DROP TABLE IF EXISTS inventory_logs CASCADE;
DROP TABLE IF EXISTS blood_requests CASCADE;
DROP TABLE IF EXISTS hospital_departments CASCADE;
DROP TABLE IF EXISTS hospitals CASCADE;
DROP TABLE IF EXISTS blood_stock CASCADE;
DROP TABLE IF EXISTS equipment CASCADE;
DROP TABLE IF EXISTS blood_tests CASCADE;
DROP TABLE IF EXISTS donation_histories CASCADE;
DROP TABLE IF EXISTS donation_events CASCADE;
DROP TABLE IF EXISTS appointments CASCADE;
DROP TABLE IF EXISTS staff CASCADE;
DROP TABLE IF EXISTS donors CASCADE;
DROP TABLE IF EXISTS donor_categories CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS blood_types CASCADE;

DROP TYPE IF EXISTS user_role CASCADE;
DROP TYPE IF EXISTS staff_status CASCADE;
DROP TYPE IF EXISTS appointment_status CASCADE;
DROP TYPE IF EXISTS request_status CASCADE;
DROP TYPE IF EXISTS donation_status CASCADE;
DROP TYPE IF EXISTS test_outcome CASCADE;

CREATE TYPE user_role AS ENUM ('Admin', 'Staff', 'Donor', 'Hospital');
CREATE TYPE staff_status AS ENUM ('Active', 'OnLeave', 'Inactive');
CREATE TYPE appointment_status AS ENUM ('Scheduled', 'Completed', 'Cancelled', 'NoShow');
CREATE TYPE request_status AS ENUM ('Pending', 'Approved', 'Rejected', 'Fulfilled');
CREATE TYPE donation_status AS ENUM ('Pending', 'Processed', 'Discarded');
CREATE TYPE test_outcome AS ENUM ('Passed', 'Failed');

CREATE TABLE blood_types (
    id SERIAL PRIMARY KEY,
    blood_group VARCHAR(10) UNIQUE NOT NULL
);

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    role user_role NOT NULL DEFAULT 'Donor',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE donor_categories (
    id SERIAL PRIMARY KEY,
    category_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT
);

CREATE TABLE donors (
    id SERIAL PRIMARY KEY,
    user_id INT UNIQUE REFERENCES users(id) ON DELETE SET NULL,
    blood_type_id INT REFERENCES blood_types(id) ON DELETE RESTRICT,
    firstname VARCHAR(100) NOT NULL,
    lastname VARCHAR(100) NOT NULL,
    customer_phone VARCHAR(20) NOT NULL,
    eligibility_state BOOLEAN DEFAULT TRUE,
    last_donation_date DATE,
    address TEXT,
    donor_category_id INT REFERENCES donor_categories(id) ON DELETE SET NULL
);

CREATE TABLE staff (
    id SERIAL PRIMARY KEY,
    user_id INT UNIQUE REFERENCES users(id) ON DELETE SET NULL,
    blood_type_id INT REFERENCES blood_types(id) ON DELETE RESTRICT,
    firstname VARCHAR(100) NOT NULL,
    lastname VARCHAR(100) NOT NULL,
    status staff_status DEFAULT 'Active'
);

CREATE TABLE hospitals (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    address TEXT NOT NULL,
    contact_person VARCHAR(100) NOT NULL
);

CREATE TABLE hospital_departments (
    id SERIAL PRIMARY KEY,
    hospital_id INT REFERENCES hospitals(id) ON DELETE CASCADE,
    department_name VARCHAR(100) NOT NULL,
    UNIQUE(hospital_id, department_name)
);

CREATE TABLE appointments (
    id SERIAL PRIMARY KEY,
    donor_id INT REFERENCES donors(id) ON DELETE CASCADE,
    staff_id INT REFERENCES staff(id) ON DELETE SET NULL,
    appointment_date TIMESTAMP NOT NULL,
    status appointment_status DEFAULT 'Scheduled'
);

CREATE TABLE donation_events (
    id SERIAL PRIMARY KEY,
    appointment_id INT REFERENCES appointments(id) ON DELETE CASCADE,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    name VARCHAR(150) NOT NULL,
    eligibility_confirmed BOOLEAN DEFAULT TRUE
);

CREATE TABLE donation_histories (
    id SERIAL PRIMARY KEY,
    donor_id INT REFERENCES donors(id) ON DELETE RESTRICT,
    donation_id INT REFERENCES donation_events(id) ON DELETE SET NULL,
    blood_type_id INT REFERENCES blood_types(id) ON DELETE RESTRICT,
    quantity_ml INT NOT NULL CHECK (quantity_ml > 0),
    blood_test_results TEXT,
    status donation_status DEFAULT 'Pending'
);

CREATE TABLE blood_stock (
    id SERIAL PRIMARY KEY,
    blood_type_id INT REFERENCES blood_types(id) ON DELETE RESTRICT,
    units_available INT DEFAULT 0 CHECK (units_available >= 0),
    received_date DATE DEFAULT CURRENT_DATE,
    expiry_date DATE NOT NULL
);

CREATE TABLE inventory_logs (
    id SERIAL PRIMARY KEY,
    stock_id INT REFERENCES blood_stock(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    action VARCHAR(255) NOT NULL
);

CREATE TABLE blood_requests (
    id SERIAL PRIMARY KEY,
    blood_type_id INT REFERENCES blood_types(id) ON DELETE RESTRICT,
    units_requested INT NOT NULL CHECK (units_requested > 0),
    requester_id INT REFERENCES hospitals(id) ON DELETE CASCADE,
    status request_status DEFAULT 'Pending'
);

CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    blood_type_id INT REFERENCES blood_types(id) ON DELETE SET NULL,
    message TEXT NOT NULL,
    type VARCHAR(50) NOT NULL
);

CREATE TABLE equipment (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    test_id INT
);

CREATE TABLE blood_tests (
    id SERIAL PRIMARY KEY,
    donation_history_id INT REFERENCES donation_histories(id) ON DELETE CASCADE,
    tested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    disease_screened VARCHAR(100) NOT NULL,
    outcome test_outcome DEFAULT 'Passed'
);

CREATE INDEX idx_donors_blood_type ON donors(blood_type_id);
CREATE INDEX idx_donors_last_donation ON donors(last_donation_date);
CREATE INDEX idx_appointments_date ON appointments(appointment_date);
CREATE INDEX idx_blood_stock_expiry ON blood_stock(expiry_date);
CREATE INDEX idx_blood_requests_status ON blood_requests(status);
CREATE INDEX idx_donation_histories_donor ON donation_histories(donor_id);

CREATE OR REPLACE FUNCTION check_donor_eligibility(d_id INT)
RETURNS BOOLEAN AS $$
DECLARE
    last_donation DATE;
    is_eligible BOOLEAN := TRUE;
BEGIN
    SELECT last_donation_date INTO last_donation 
    FROM donors 
    WHERE id = d_id;
    
    IF last_donation IS NOT NULL AND (CURRENT_DATE - last_donation) < 90 THEN
        is_eligible := FALSE;
    END IF;
    
    RETURN is_eligible;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE PROCEDURE register_blood_donation(
    p_donor_id INT,
    p_donation_id INT,
    p_blood_type_id INT,
    p_quantity_ml INT
) AS $$
BEGIN
    INSERT INTO donation_histories (donor_id, donation_id, blood_type_id, quantity_ml, status)
    VALUES (p_donor_id, p_donation_id, p_blood_type_id, p_quantity_ml, 'Pending');

    UPDATE donors
    SET last_donation_date = CURRENT_DATE
    WHERE id = p_donor_id;

    COMMIT;
END;
$$ LANGUAGE plpgsql;
"""

async def init_db():
    print(f"Connecting to: {clean_db_url}")
    engine = create_async_engine(clean_db_url, connect_args={"ssl": True}, echo=True)
    async with engine.begin() as conn:
        print("Executing DDL Queries...")
        # Split sql statements by semicolon if driver requires it, 
        # or execute as a single block (PostgreSQL allows multi-statement executions).
        await conn.execute(text(DDL_SQL))
        print("Database initialized successfully with all 16 tables, functions, & procedures!")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(init_db())
