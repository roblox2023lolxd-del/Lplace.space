const express = require("express");
const fs = require("fs");
const path = require("path");
const bodyParser = require("body-parser");
const session = require("express-session");

const app = express();
const PORT = process.env.PORT || 3000;

// Data files
const usersFile = path.join(__dirname, "users.json");
const drawingsFile = path.join(__dirname, "drawings.json");

// Load or initialize
let users = fs.existsSync(usersFile) ? JSON.parse(fs.readFileSync(usersFile)) : {};
let drawings = fs.existsSync(drawingsFile) ? JSON.parse(fs.readFileSync(drawingsFile)) : {};

app.use(bodyParser.json());
app.use(session({
  secret: "lplace-secret",
  resave: false,
  saveUninitialized: true,
  cookie: { secure: false }
}));
app.use(express.static(path.join(__dirname, "public")));

// Signup
app.post("/signup", (req, res) => {
  const { username, password } = req.body;
  if (users[username]) return res.json({ success: false, message: "User already exists" });

  users[username] = { password };
  drawings[username] = { pixels: {}, strokes: [] };

  fs.writeFileSync(usersFile, JSON.stringify(users, null, 2));
  fs.writeFileSync(drawingsFile, JSON.stringify(drawings, null, 2));

  res.json({ success: true });
});

// Login
app.post("/login", (req, res) => {
  const { username, password } = req.body;
  if (!users[username] || users[username].password !== password) {
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
app.post("/save", (req, res) => {
  if (!req.session.user) return res.json({ success: false, message: "Not logged in" });

  drawings[req.session.user] = req.body;
  fs.writeFileSync(drawingsFile, JSON.stringify(drawings, null, 2));
  res.json({ success: true });
});

// Load drawings
app.get("/load", (req, res) => {
  if (!req.session.user) return res.json({ success: false });
  res.json(drawings[req.session.user] || { pixels: {}, strokes: [] });
});

app.listen(PORT, () => console.log(`Server running at http://localhost:${PORT}`));
