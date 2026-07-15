const express = require('express');
const jwt = require('jsonwebtoken');
const pool = require('../db');
const router = express.Router();

router.post('/login', async (req, res) => {
  const { username, password } = req.body;
  try {
    const query = 'SELECT * FROM Users WHERE username = $1';
    const result = await pool.query(query, [username]);
    
    if (result.rows.length === 0) {
      return res.status(400).json({ message: 'User not found.' });
    }

    const user = result.rows[0];
    const dbPassword = user.password || '';
    
    if (password !== dbPassword) {
      return res.status(400).json({ message: 'Incorrect Password!' });
    }

    const token = jwt.sign({ id: user.id, role: user.role }, process.env.JWT_SECRET, { expiresIn: '1h' });
    
    res.json({ token, role: user.role, username: user.username });
  } catch (err) {
    res.status(500).json({ message: 'DB Error: ' + err.message });
  }
});

module.exports = router;
