require('dotenv').config();
const express = require('express');
const cors = require('cors');
const authRoutes = require('./routes/auth');
const dashboardRoutes = require('./routes/dashboard');
const moduleRoutes = require('./routes/modules');
const notifRoutes = require('./routes/notifications');

const app = express();
app.use(cors());
app.use(express.json());

app.use('/api/auth', authRoutes);
app.use('/api/dashboard', dashboardRoutes);
app.use('/api/modules', moduleRoutes);
app.use('/api/notifications', notifRoutes);

app.listen(process.env.PORT || 5000, () => console.log('Server running on port 5000 with 14+ Routes'));
