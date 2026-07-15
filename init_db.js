const { Pool } = require('pg');
require('dotenv').config();

const pool = new Pool({
  connectionString: process.env.DB_CONNECTION_STRING,
  ssl: { rejectUnauthorized: false }
});

const createTablesQuery = `
    -- Users Table
    CREATE TABLE IF NOT EXISTS Users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(100) UNIQUE NOT NULL,
        password VARCHAR(255) NOT NULL,
        enabled BOOLEAN DEFAULT TRUE,
        role VARCHAR(50) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- BloodType Table
    CREATE TABLE IF NOT EXISTS BloodType (
        id SERIAL PRIMARY KEY,
        blood_group VARCHAR(10) UNIQUE NOT NULL,
        stock_units INT DEFAULT 0
    );

    -- Staff Table
    CREATE TABLE IF NOT EXISTS Staff (
        id SERIAL PRIMARY KEY,
        user_id INT REFERENCES Users(id) ON DELETE CASCADE,
        blood_type_id INT REFERENCES BloodType(id),
        firstname VARCHAR(100),
        lastname VARCHAR(100),
        status VARCHAR(50) DEFAULT 'Active'
    );

    -- BloodStock Table
    CREATE TABLE IF NOT EXISTS BloodStock (
        id SERIAL PRIMARY KEY,
        blood_type_id INT REFERENCES BloodType(id) ON DELETE CASCADE,
        unitsAvailable INT DEFAULT 0,
        receivedDate DATE,
        expiryDate DATE
    );

    -- InventoryLogs Table
    CREATE TABLE IF NOT EXISTS InventoryLogs (
        id SERIAL PRIMARY KEY,
        stock_id INT REFERENCES BloodStock(id) ON DELETE CASCADE,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        action VARCHAR(255)
    );

    -- Equipment Table
    CREATE TABLE IF NOT EXISTS Equipment (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        test_id INT,
        status VARCHAR(50) DEFAULT 'Available',
        last_maintenance DATE
    );

    -- DonorCategories Table
    CREATE TABLE IF NOT EXISTS DonorCategories (
        id SERIAL PRIMARY KEY,
        category_name VARCHAR(100),
        description TEXT
    );

    -- Donors Table
    CREATE TABLE IF NOT EXISTS Donors (
        id SERIAL PRIMARY KEY,
        user_id INT REFERENCES Users(id) ON DELETE SET NULL,
        blood_type_id INT REFERENCES BloodType(id),
        firstname VARCHAR(100),
        lastname VARCHAR(100),
        name VARCHAR(255), -- Maintaining legacy column for existing routes
        contact_info VARCHAR(255),
        customerPhone VARCHAR(20),
        eligibility_status BOOLEAN DEFAULT TRUE,
        last_donation_date DATE,
        address TEXT
    );

    -- Appointments Table
    CREATE TABLE IF NOT EXISTS Appointments (
        id SERIAL PRIMARY KEY,
        donor_id INT REFERENCES Donors(id) ON DELETE CASCADE,
        staff_id INT REFERENCES Staff(id) ON DELETE SET NULL,
        appointment_date DATE NOT NULL,
        status VARCHAR(50) DEFAULT 'Scheduled'
    );

    -- DonationEvent Table
    CREATE TABLE IF NOT EXISTS DonationEvent (
        id SERIAL PRIMARY KEY,
        appointment_id INT REFERENCES Appointments(id) ON DELETE CASCADE,
        date DATE NOT NULL,
        name VARCHAR(255),
        eligibility_confirmed BOOLEAN DEFAULT TRUE
    );

    -- DonationHistory Table
    CREATE TABLE IF NOT EXISTS DonationHistory (
        id SERIAL PRIMARY KEY,
        donor_id INT REFERENCES Donors(id) ON DELETE CASCADE,
        donation_id INT REFERENCES DonationEvent(id) ON DELETE CASCADE,
        blood_type_id INT REFERENCES BloodType(id),
        quantity_ml INT,
        blood_tests_results TEXT,
        status VARCHAR(50)
    );

    -- Hospitals Table
    CREATE TABLE IF NOT EXISTS Hospitals (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        address TEXT,
        contact_person VARCHAR(255),
        contact_info VARCHAR(255)
    );

    -- BloodRequests Table
    CREATE TABLE IF NOT EXISTS BloodRequests (
        id SERIAL PRIMARY KEY,
        blood_type_id INT REFERENCES BloodType(id) ON DELETE CASCADE,
        unitsRequested INT,
        units_requested INT, -- Maintaining legacy column
        requester_id INT REFERENCES Hospitals(id) ON DELETE CASCADE,
        hospital_id INT REFERENCES Hospitals(id) ON DELETE CASCADE, -- Maintaining legacy column
        urgency VARCHAR(50),
        request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status VARCHAR(50) DEFAULT 'Pending'
    );

    -- HospitalDepartments Table
    CREATE TABLE IF NOT EXISTS HospitalDepartments (
        id SERIAL PRIMARY KEY,
        hospital_id INT REFERENCES Hospitals(id) ON DELETE CASCADE,
        department_name VARCHAR(255)
    );

    -- Notifications Table
    CREATE TABLE IF NOT EXISTS Notifications (
        id SERIAL PRIMARY KEY,
        blood_type_id INT REFERENCES BloodType(id) ON DELETE CASCADE,
        message TEXT,
        type VARCHAR(50)
    );
    
    -- ScreeningResults Table (Legacy from existing codebase)
    CREATE TABLE IF NOT EXISTS ScreeningResults (
        id SERIAL PRIMARY KEY,
        donor_id INT REFERENCES Donors(id) ON DELETE CASCADE,
        test_type VARCHAR(255),
        result_status VARCHAR(50)
    );
`;

const insertMockData = `
    INSERT INTO BloodType (blood_group, stock_units) VALUES 
    ('A+', 15), ('A-', 5), ('B+', 20), ('B-', 8), ('O+', 30), ('O-', 10), ('AB+', 12), ('AB-', 4)
    ON CONFLICT (blood_group) DO NOTHING;

    INSERT INTO Users (username, password, role) VALUES 
    ('admin_mock', 'admin123', 'Admin'),
    ('staff_mock', 'staff123', 'Staff')
    ON CONFLICT (username) DO NOTHING;

    INSERT INTO Donors (name, firstname, lastname, contact_info, blood_type_id) VALUES 
    ('John Doe', 'John', 'Doe', '1234567890', 1),
    ('Jane Smith', 'Jane', 'Smith', '0987654321', 5)
    ON CONFLICT DO NOTHING;

    INSERT INTO Appointments (donor_id, appointment_date, status) VALUES 
    (1, CURRENT_DATE + INTERVAL '2 days', 'Scheduled'),
    (2, CURRENT_DATE - INTERVAL '1 day', 'Completed'),
    (1, CURRENT_DATE + INTERVAL '5 days', 'Scheduled'),
    (2, CURRENT_DATE + INTERVAL '10 days', 'Scheduled'),
    (1, CURRENT_DATE - INTERVAL '30 days', 'Completed'),
    (2, CURRENT_DATE - INTERVAL '15 days', 'Completed'),
    (1, CURRENT_DATE + INTERVAL '12 days', 'Scheduled')
    ON CONFLICT DO NOTHING;
`;

async function initializeDB() {
    try {
        console.log("Connecting to Neon Database...");
        await pool.query(createTablesQuery);
        console.log("✅ All ERD Tables created successfully.");
        
        console.log("Inserting Mock Data...");
        await pool.query(insertMockData);
        console.log("✅ Mock Data inserted successfully.");
        
    } catch (err) {
        console.error("❌ Error initializing database:", err);
    } finally {
        pool.end();
        console.log("Database connection closed.");
    }
}

initializeDB();
