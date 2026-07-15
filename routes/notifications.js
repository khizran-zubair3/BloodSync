const express = require('express');
const pool = require('../db');
const { authMiddleware } = require('../middleware/authMiddleware');
const router = express.Router();

// Get latest notifications
router.get('/', authMiddleware, async (req, res) => {
    try {
        const result = await pool.query('SELECT * FROM Notifications ORDER BY created_at DESC LIMIT 10');
        res.json(result.rows);
    } catch (err) { res.status(500).json({ error: err.message }); }
});

// Add new notification (Admin only)
router.post('/', authMiddleware, async (req, res) => {
    const { message, type } = req.body;
    try {
        const result = await pool.query('INSERT INTO Notifications (message, type) VALUES ($1, $2) RETURNING *', [message, type]);
        res.json(result.rows[0]);
    } catch (err) { res.status(500).json({ error: err.message }); }
});

module.exports = router;
