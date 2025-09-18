const express = require("express");
const fs = require("fs");
const path = require("path");
const bodyParser = require("body-parser");
const session = require("express-session");
const http = require("http");
const { Server } = require("socket.io");

const app = express();
const server = http.createServer(app);
const io = new Server(server);
const PORT = 3000;

// Files
const usersFile = path.join(__dirname, "users.json");
const drawingsFile = path.join(__dirname, "drawings.json");

// Init/load
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

// Get current user
app.get("/me", (req, res) => {
  if (!req.session.user) return res.json({ user: null });
  res.json({ user: req.session.user });
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

// --- Socket.IO for real-time updates ---
io.on("connection", (socket) => {
  console.log("A user connected");

  // Broadcast drawing
  socket.on("draw", (data) => {
    socket.broadcast.emit("draw", data); // send to all other users
  });

  // Broadcast erase
  socket.on("erase", (data) => {
    socket.broadcast.emit("erase", data);
  });

  socket.on("disconnect", () => {
    console.log("A user disconnected");
  });
});

server.listen(PORT, () => console.log(`Server running at http://localhost:${PORT}`));
