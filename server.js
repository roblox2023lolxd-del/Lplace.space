// server.js
const express = require('express');
const fs = require('fs');
const path = require('path');
const bodyParser = require('body-parser');
const session = require('express-session');
const pgSession = require('connect-pg-simple')(session);
const { Pool } = require('pg');

const app = express();
const PORT = process.env.PORT || 10000;

// ===== DATA FILES (fallback) =====
const usersFile = path.join(__dirname, 'users.json');
const drawingsFile = path.join(__dirname, 'drawings.json');

// Load or initialize
let users = fs.existsSync(usersFile) ? JSON.parse(fs.readFileSync(usersFile)) : {};
let drawings = fs.existsSync(drawingsFile) ? JSON.parse(fs.readFileSync(drawingsFile)) : {};

// ===== MIDDLEWARE =====
app.use(bodyParser.json());
app.use(express.static(path.join(__dirname, 'public')));

// ===== POSTGRES SESSION STORE =====
const pool = new Pool({
    connectionString: process.env.DATABASE_URL,
    ssl: { rejectUnauthorized: false }
});

app.use(session({
    store: new pgSession({
        pool: pool,
        tableName: 'user_sessions'
    }),
    secret: 'lplace-secret',
    resave: false,
    saveUninitialized: false,
    cookie: { secure: process.env.NODE_ENV === 'production' }
}));

// ===== ROUTES =====

// Signup
app.post('/signup', (req, res) => {
    const { username, password } = req.body;
    if (!username || !password) return res.json({ success: false, message: "Missing credentials" });
    if (users[username]) return res.json({ success: false, message: "User already exists" });

    users[username] = { password };
    drawings[username] = { strokes: [] };

    fs.writeFileSync(usersFile, JSON.stringify(users, null, 2));
    fs.writeFileSync(drawingsFile, JSON.stringify(drawings, null, 2));

    req.session.user = username;
    res.json({ success: true });
});

// Login
app.post('/login', (req, res) => {
    const { username, password } = req.body;
    if (!users[username] || users[username].password !== password) {
        return res.json({ success: false, message: "Invalid credentials" });
    }
    req.session.user = username;
    res.json({ success: true });
});

// Logout
app.post('/logout', (req, res) => {
    req.session.destroy(() => res.json({ success: true }));
});

// Get current user
app.get('/me', (req, res) => {
    res.json({ user: req.session.user || null });
});

// Save drawings
app.post('/save', (req, res) => {
    if (!req.session.user) return res.json({ success: false, message: "Not logged in" });
    drawings[req.session.user] = req.body;
    fs.writeFileSync(drawingsFile, JSON.stringify(drawings, null, 2));
    res.json({ success: true });
});

// Load current user drawings
app.get('/load', (req, res) => {
    if (!req.session.user) return res.json({ success: false });
    res.json(drawings[req.session.user] || { strokes: [] });
});

// Load all drawings (for hover & multiplayer view)
app.get('/allDrawings', (req, res) => {
    res.json(drawings);
});

// ===== START SERVER =====
app.listen(PORT, () => console.log(`Server running at http://localhost:${PORT}`));
