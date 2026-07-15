const express = require('express');
const pool = require('../db');
const { authMiddleware, checkRole } = require('../middleware/authMiddleware');
const router = express.Router();

router.get('/stats', authMiddleware, async (req, res) => {
  try {
    const bloodStock = await pool.query('SELECT * FROM BloodType');
    const totalDonors = await pool.query('SELECT COUNT(*) FROM Donors');
    const totalHospitals = await pool.query('SELECT COUNT(*) FROM Hospitals');
    res.json({
      bloodStock: bloodStock.rows,
      totalDonors: totalDonors.rows[0].count,
      totalHospitals: totalHospitals.rows[0].count
    });
  } catch (err) { res.status(500).json({ error: err.message }); }
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

module.exports = router;
