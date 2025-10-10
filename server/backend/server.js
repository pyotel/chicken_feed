const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const { Pool } = require('pg');
const cron = require('node-cron');
const winston = require('winston');
const Joi = require('joi');
const rateLimit = require('express-rate-limit');

const app = express();
const PORT = process.env.PORT || 3001;

// Logger setup
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: 'error.log', level: 'error' }),
    new winston.transports.File({ filename: 'combined.log' })
  ]
});

// Database connection
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: false
});

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 1000 // limit each IP to 1000 requests per windowMs
});

// Middleware
app.use(helmet({
  crossOriginResourcePolicy: false,
}));
app.use(cors({
  origin: true,  // Allow all origins for development
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization']
}));
app.use(express.json());
app.use('/api', limiter);

// Validation schemas
const feedingLogSchema = Joi.object({
  device_id: Joi.string().required(),
  action: Joi.string().valid('open', 'close', 'error', 'startup', 'shutdown').required(),
  timestamp: Joi.date().iso().required(),
  details: Joi.object().optional()
});

const configUpdateSchema = Joi.object({
  device_id: Joi.string().required(),
  feeding_times: Joi.array().items(Joi.string().pattern(/^([01]\d|2[0-3]):([0-5]\d)$/)).required(),
  duration_minutes: Joi.number().min(1).max(120).required()
});

// Store device configurations
const deviceConfigs = new Map();

// API Routes

// Health check
app.get('/api/health', (req, res) => {
  res.json({ status: 'healthy', timestamp: new Date() });
});

// Register/Update device configuration
app.post('/api/device/config', async (req, res) => {
  try {
    const { error } = configUpdateSchema.validate(req.body);
    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }

    const { device_id, feeding_times, duration_minutes } = req.body;

    // Store configuration
    deviceConfigs.set(device_id, {
      feeding_times,
      duration_minutes,
      last_update: new Date()
    });

    // Save to database
    await pool.query(
      `INSERT INTO device_configs (device_id, feeding_times, duration_minutes, updated_at)
       VALUES ($1, $2, $3, NOW())
       ON CONFLICT (device_id)
       DO UPDATE SET feeding_times = $2, duration_minutes = $3, updated_at = NOW()`,
      [device_id, feeding_times, duration_minutes]
    );

    logger.info(`Device config updated: ${device_id}`);
    res.json({ success: true, message: 'Configuration updated' });
  } catch (error) {
    logger.error('Error updating device config:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Log feeding event
app.post('/api/feeding/log', async (req, res) => {
  try {
    const { error } = feedingLogSchema.validate(req.body);
    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }

    const { device_id, action, timestamp, details } = req.body;

    await pool.query(
      `INSERT INTO feeding_logs (device_id, action, timestamp, details)
       VALUES ($1, $2, $3, $4)`,
      [device_id, action, timestamp, details || {}]
    );

    logger.info(`Feeding event logged: ${device_id} - ${action}`);
    res.json({ success: true });
  } catch (error) {
    logger.error('Error logging feeding event:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get feeding logs
app.get('/api/feeding/logs/:device_id', async (req, res) => {
  try {
    const { device_id } = req.params;
    const { start_date, end_date, limit = 100 } = req.query;

    let query = `
      SELECT * FROM feeding_logs
      WHERE device_id = $1
    `;
    const params = [device_id];

    if (start_date) {
      query += ` AND timestamp >= $${params.length + 1}`;
      params.push(start_date);
    }

    if (end_date) {
      query += ` AND timestamp <= $${params.length + 1}`;
      params.push(end_date);
    }

    query += ` ORDER BY timestamp DESC LIMIT $${params.length + 1}`;
    params.push(limit);

    const result = await pool.query(query, params);
    res.json(result.rows);
  } catch (error) {
    logger.error('Error fetching logs:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get missed feedings
app.get('/api/feeding/missed/:device_id', async (req, res) => {
  try {
    const { device_id } = req.params;
    const { date = new Date().toISOString().split('T')[0] } = req.query;

    const result = await pool.query(
      `SELECT * FROM missed_feedings
       WHERE device_id = $1 AND DATE(scheduled_time) = $2
       ORDER BY scheduled_time`,
      [device_id, date]
    );

    res.json(result.rows);
  } catch (error) {
    logger.error('Error fetching missed feedings:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get statistics
app.get('/api/stats/:device_id', async (req, res) => {
  try {
    const { device_id } = req.params;
    const { days = 7 } = req.query;

    const stats = await pool.query(
      `SELECT
        DATE(timestamp) as date,
        COUNT(CASE WHEN action = 'open' THEN 1 END) as opens,
        COUNT(CASE WHEN action = 'close' THEN 1 END) as closes,
        COUNT(CASE WHEN action = 'error' THEN 1 END) as errors
       FROM feeding_logs
       WHERE device_id = $1
       AND timestamp >= NOW() - INTERVAL '${days} days'
       GROUP BY DATE(timestamp)
       ORDER BY date DESC`,
      [device_id]
    );

    const missed = await pool.query(
      `SELECT DATE(scheduled_time) as date, COUNT(*) as missed_count
       FROM missed_feedings
       WHERE device_id = $1
       AND scheduled_time >= NOW() - INTERVAL '${days} days'
       GROUP BY DATE(scheduled_time)`,
      [device_id]
    );

    res.json({
      feeding_stats: stats.rows,
      missed_feedings: missed.rows
    });
  } catch (error) {
    logger.error('Error fetching statistics:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Check for missed feedings (runs every minute)
cron.schedule('* * * * *', async () => {
  try {
    const now = new Date();
    const currentTime = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;

    for (const [deviceId, config] of deviceConfigs.entries()) {
      if (config.feeding_times.includes(currentTime)) {
        // Check if feeding was logged in the last 5 minutes
        const result = await pool.query(
          `SELECT COUNT(*) FROM feeding_logs
           WHERE device_id = $1
           AND action = 'open'
           AND timestamp >= NOW() - INTERVAL '5 minutes'`,
          [deviceId]
        );

        if (result.rows[0].count === '0') {
          // Log missed feeding
          await pool.query(
            `INSERT INTO missed_feedings (device_id, scheduled_time, detected_at)
             VALUES ($1, $2, NOW())
             ON CONFLICT (device_id, scheduled_time) DO NOTHING`,
            [deviceId, now]
          );

          logger.warn(`Missed feeding detected for device: ${deviceId} at ${currentTime}`);
        }
      }
    }
  } catch (error) {
    logger.error('Error checking for missed feedings:', error);
  }
});

// Start server
app.listen(PORT, () => {
  logger.info(`Server running on port ${PORT}`);
});