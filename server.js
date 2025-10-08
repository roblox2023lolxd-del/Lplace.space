const express = require("express");
const fs = require("fs");
const path = require("path");
const http = require("http");
const { Server } = require("socket.io");

const app = express();
const server = http.createServer(app);
const io = new Server(server);
const PORT = process.env.PORT || 3000;

app.use(express.static(path.join(__dirname, "public")));
app.use(express.json());

// --- Load data from JSON files ---
let users = {};
let drawings = [];

// Load saved users
if (fs.existsSync("users.json")) {
  try {
    users = JSON.parse(fs.readFileSync("users.json", "utf8"));
  } catch {
    users = {};
  }
}

// Load saved drawings
if (fs.existsSync("drawings.json")) {
  try {
    drawings = JSON.parse(fs.readFileSync("drawings.json", "utf8"));
  } catch {
    drawings = [];
  }
}

// --- Auth routes ---
app.post("/signup", (req, res) => {
  const { username, password } = req.body;
  if (users[username]) return res.status(400).json({ error: "Username already exists" });
  users[username] = { password };
  fs.writeFileSync("users.json", JSON.stringify(users, null, 2));
  res.json({ success: true });
});

app.post("/login", (req, res) => {
  const { username, password } = req.body;
  if (!users[username] || users[username].password !== password)
    return res.status(400).json({ error: "Invalid username or password" });
  res.json({ success: true });
});

// --- Socket.io Drawing System ---
io.on("connection", (socket) => {
  console.log("✅ User connected:", socket.id);

  // Send saved drawings to the new client
  socket.emit("loadDrawings", drawings);

  // Handle new draw events
  socket.on("draw", (data) => {
    drawings.push(data);
    fs.writeFileSync("drawings.json", JSON.stringify(drawings, null, 2));
    io.emit("draw", data); // send to everyone
  });

  // Handle clear (wipe all)
  socket.on("clear", () => {
    drawings = [];
    fs.writeFileSync("drawings.json", JSON.stringify(drawings, null, 2));
    io.emit("clear"); // notify all clients
  });

  socket.on("disconnect", () => console.log("❌ User disconnected:", socket.id));
});

server.listen(PORT, () => console.log(`🚀 Server running at http://localhost:${PORT}`));
