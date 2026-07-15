const express = require('express');
const pool = require('../db');
const { authMiddleware, checkRole } = require('../middleware/authMiddleware');
const router = express.Router();

router.get('/blood-stock', authMiddleware, async (req, res) => {
    try {
        const result = await pool.query('SELECT * FROM BloodType ORDER BY id');
        res.json(result.rows);
    } catch (err) { res.status(500).json({ error: err.message }); }
});

router.put('/blood-stock/:id', authMiddleware, checkRole(['Admin']), async (req, res) => {
    const { stock_units } = req.body;
    try {
        const result = await pool.query('UPDATE BloodType SET stock_units = $1 WHERE id = $2 RETURNING *', [stock_units, req.params.id]);
        res.json(result.rows[0]);
    } catch (err) { res.status(500).json({ error: err.message }); }
});

router.get('/blood-requests', authMiddleware, async (req, res) => {
    try {
        const result = await pool.query('SELECT * FROM BloodRequests ORDER BY request_date DESC');
        res.json(result.rows);
    } catch (err) { res.status(500).json({ error: err.message }); }
});

router.post('/blood-requests', authMiddleware, async (req, res) => {
    const { hospital_id, blood_type_id, units_requested, urgency } = req.body;
    try {
        const result = await pool.query('INSERT INTO BloodRequests (hospital_id, blood_type_id, units_requested, urgency, status) VALUES ($1, $2, $3, $4, $5) RETURNING *', [hospital_id, blood_type_id, units_requested, urgency, 'Pending']);
        res.json(result.rows[0]);
    } catch (err) { res.status(500).json({ error: err.message }); }
});

router.put('/blood-requests/:id', authMiddleware, checkRole(['Admin']), async (req, res) => {
    const { status } = req.body;
    try {
        const result = await pool.query('UPDATE BloodRequests SET status = $1 WHERE id = $2 RETURNING *', [status, req.params.id]);
        res.json(result.rows[0]);
    } catch (err) { res.status(500).json({ error: err.message }); }
});

router.get('/equipment', authMiddleware, async (req, res) => {
    try {
        const result = await pool.query('SELECT * FROM Equipment ORDER BY id');
        res.json(result.rows);
    } catch (err) { res.status(500).json({ error: err.message }); }
});

router.post('/equipment', authMiddleware, checkRole(['Admin']), async (req, res) => {
    const { name, status, last_maintenance } = req.body;
    try {
        const result = await pool.query('INSERT INTO Equipment (name, status, last_maintenance) VALUES ($1, $2, $3) RETURNING *', [name, status, last_maintenance]);
        res.json(result.rows[0]);
    } catch (err) { res.status(500).json({ error: err.message }); }
});

router.put('/equipment/:id', authMiddleware, checkRole(['Admin']), async (req, res) => {
    const { name, status, last_maintenance } = req.body;
    try {
        const result = await pool.query('UPDATE Equipment SET name=$1, status=$2, last_maintenance=$3 WHERE id=$4 RETURNING *', [name, status, last_maintenance, req.params.id]);
        res.json(result.rows[0]);
    } catch (err) { res.status(500).json({ error: err.message }); }
});

router.get('/screening', authMiddleware, checkRole(['Admin']), async (req, res) => {
    try {
        const result = await pool.query('SELECT * FROM ScreeningResults ORDER BY id DESC');
        res.json(result.rows);
    } catch (err) { res.status(500).json({ error: err.message }); }
});

router.post('/screening', authMiddleware, checkRole(['Admin']), async (req, res) => {
    const { donor_id, test_type, result_status } = req.body;
    try {
        const res2 = await pool.query('INSERT INTO ScreeningResults (donor_id, test_type, result_status) VALUES ($1, $2, $3) RETURNING *', [donor_id, test_type, result_status]);
        res.json(res2.rows[0]);
    } catch (err) { res.status(500).json({ error: err.message }); }
});

router.get('/staff', authMiddleware, async (req, res) => {
    try {
        const result = await pool.query('SELECT id, username, role, created_at FROM Users');
        res.json(result.rows);
    } catch (err) { res.status(500).json({ error: err.message }); }
});

router.post('/staff', authMiddleware, checkRole(['Admin']), async (req, res) => {
    const { username, password, role } = req.body;
    try {
        const result = await pool.query('INSERT INTO Users (username, password, role) VALUES ($1, $2, $3) RETURNING id, username, role', [username, password, role]);
        res.json(result.rows[0]);
    } catch (err) { res.status(500).json({ error: err.message }); }
});

router.put('/staff/:id', authMiddleware, checkRole(['Admin']), async (req, res) => {
    const { role } = req.body;
    try {
        const result = await pool.query('UPDATE Users SET role = $1 WHERE id = $2 RETURNING id, username, role', [role, req.params.id]);
        res.json(result.rows[0]);
    } catch (err) { res.status(500).json({ error: err.message }); }
});

// SUPER FIX: Agar Staff table mein hai toh delete karo, warna skip karke User delete karo
router.delete('/staff/:id', authMiddleware, checkRole(['Admin']), async (req, res) => {
    const client = await pool.connect();
    try {
        await client.query('BEGIN');
        try { await client.query('DELETE FROM Staff WHERE user_id = $1', [req.params.id]); } catch(e) {}
        await client.query('DELETE FROM Users WHERE id = $1', [req.params.id]);
        await client.query('COMMIT');
        res.json({ message: 'Staff deleted successfully' });
    } catch (err) {
        await client.query('ROLLBACK');
        res.status(500).json({ error: err.message });
    } finally {
        client.release();
    }
});

router.get('/donors', authMiddleware, async (req, res) => {
    try {
        const result = await pool.query('SELECT * FROM Donors ORDER BY id DESC');
        res.json(result.rows);
    } catch (err) { res.status(500).json({ error: err.message }); }
});

router.post('/donors', authMiddleware, async (req, res) => {
    const { name, contact_info, blood_type_id } = req.body;
    try {
        const newDonor = await pool.query('INSERT INTO Donors (name, contact_info, blood_type_id) VALUES ($1, $2, $3) RETURNING *', [name, contact_info, blood_type_id]);
        res.json(newDonor.rows[0]);
    } catch (err) { res.status(500).json({ error: err.message }); }
});

router.put('/donors/:id', authMiddleware, checkRole(['Admin']), async (req, res) => {
    const { name, contact_info, blood_type_id } = req.body;
    try {
        const updateDonor = await pool.query('UPDATE Donors SET name=$1, contact_info=$2, blood_type_id=$3 WHERE id=$4 RETURNING *', [name, contact_info, blood_type_id, req.params.id]);
        res.json(updateDonor.rows[0]);
    } catch (err) { res.status(500).json({ error: err.message }); }
});

router.delete('/donors/:id', authMiddleware, checkRole(['Admin']), async (req, res) => {
    try {
        await pool.query('DELETE FROM Donors WHERE id = $1', [req.params.id]);
        res.json({ message: 'Donor deleted successfully' });
    } catch (err) { res.status(500).json({ error: err.message }); }
});

router.get('/hospitals', authMiddleware, async (req, res) => {
    try {
        const result = await pool.query('SELECT * FROM Hospitals ORDER BY id DESC');
        res.json(result.rows);
    } catch (err) { res.status(500).json({ error: err.message }); }
});

router.post('/hospitals', authMiddleware, checkRole(['Admin']), async (req, res) => {
    const { name, address, contact_info } = req.body;
    try {
        const newHosp = await pool.query('INSERT INTO Hospitals (name, address, contact_info) VALUES ($1, $2, $3) RETURNING *', [name, address, contact_info]);
        res.json(newHosp.rows[0]);
    } catch (err) { res.status(500).json({ error: err.message }); }
});

router.put('/hospitals/:id', authMiddleware, checkRole(['Admin']), async (req, res) => {
    const { name, address, contact_info } = req.body;
    try {
        const updateHosp = await pool.query('UPDATE Hospitals SET name=$1, address=$2, contact_info=$3 WHERE id=$4 RETURNING *', [name, address, contact_info, req.params.id]);
        res.json(updateHosp.rows[0]);
    } catch (err) { res.status(500).json({ error: err.message }); }
});

// ---- NEW APPOINTMENTS & DONATIONS ROUTES ---- //

router.get('/appointments', authMiddleware, async (req, res) => {
    try {
        const result = await pool.query('SELECT * FROM Appointments ORDER BY appointment_date DESC');
        res.json(result.rows);
    } catch (err) { res.status(500).json({ error: err.message }); }
});

router.post('/appointments', authMiddleware, async (req, res) => {
    const { donor_id, staff_id, appointment_date, status } = req.body;
    try {
        const result = await pool.query(
            'INSERT INTO Appointments (donor_id, staff_id, appointment_date, status) VALUES ($1, $2, $3, $4) RETURNING *',
            [donor_id, staff_id || null, appointment_date, status || 'Scheduled']
        );
        res.json(result.rows[0]);
    } catch (err) { res.status(500).json({ error: err.message }); }
});

router.put('/appointments/:id', authMiddleware, async (req, res) => {
    const { status } = req.body;
    try {
        const result = await pool.query('UPDATE Appointments SET status=$1 WHERE id=$2 RETURNING *', [status, req.params.id]);
        res.json(result.rows[0]);
    } catch (err) { res.status(500).json({ error: err.message }); }
});

router.post('/donations', authMiddleware, async (req, res) => {
    const { appointment_id, date, name, eligibility_confirmed } = req.body;
    try {
        const result = await pool.query('INSERT INTO DonationEvent (appointment_id, date, name, eligibility_confirmed) VALUES ($1, $2, $3, $4) RETURNING *', [appointment_id, date, name, eligibility_confirmed]);
        res.json(result.rows[0]);
    } catch (err) { res.status(500).json({ error: err.message }); }
});

module.exports = router;
