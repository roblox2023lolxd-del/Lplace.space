const express = require("express");
const bodyParser = require("body-parser");
const session = require("express-session");
const { Pool } = require("pg");

const app = express();
const PORT = process.env.PORT || 3000;

// Postgres connection
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }
});

// Middleware
app.use(bodyParser.json());
app.use(session({
  secret: "lplace-secret",
  resave: false,
  saveUninitialized: true,
  cookie: { secure: false }
}));
app.use(express.static("public"));

// Initialize tables
(async () => {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS users (
      username TEXT PRIMARY KEY,
      password TEXT NOT NULL
    );
  `);

  await pool.query(`
    CREATE TABLE IF NOT EXISTS drawings (
      username TEXT PRIMARY KEY REFERENCES users(username),
      data JSONB
    );
  `);
})();

// Signup
app.post("/signup", async (req, res) => {
  const { username, password } = req.body;
  const exists = await pool.query("SELECT 1 FROM users WHERE username=$1", [username]);
  if (exists.rowCount > 0) return res.json({ success: false, message: "User exists" });

  await pool.query("INSERT INTO users (username, password) VALUES ($1, $2)", [username, password]);
  await pool.query("INSERT INTO drawings (username, data) VALUES ($1, $2)", [username, { pixels: {}, strokes: [] }]);
  res.json({ success: true });
});

// Login
app.post("/login", async (req, res) => {
  const { username, password } = req.body;
  const result = await pool.query("SELECT password FROM users WHERE username=$1", [username]);
  if (result.rowCount === 0 || result.rows[0].password !== password) {
    return res.json({ success: false, message: "Invalid credentials" });
  }

  req.session.user = username;
  res.json({ success: true });
});

// Logout
app.post("/logout", (req, res) => {
  req.session.destroy(() => res.json({ success: true }));
});

// Current user
app.get("/me", (req, res) => {
  res.json({ user: req.session.user || null });
});

// Save drawings
app.post("/save", async (req, res) => {
  if (!req.session.user) return res.json({ success: false, message: "Not logged in" });
  await pool.query("UPDATE drawings SET data=$1 WHERE username=$2", [req.body, req.session.user]);
  res.json({ success: true });
});

// Load drawings
app.get("/load", async (req, res) => {
  if (!req.session.user) return res.json({ success: false });
  const result = await pool.query("SELECT data FROM drawings WHERE username=$1", [req.session.user]);
  res.json(result.rows[0]?.data || { pixels: {}, strokes: [] });
});

app.listen(PORT, () => console.log(`Server running at http://localhost:${PORT}`));
