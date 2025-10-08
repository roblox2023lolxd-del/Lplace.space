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

let users = {};
let drawings = [];

// Load existing users and drawings
if (fs.existsSync("users.json")) users = JSON.parse(fs.readFileSync("users.json"));
if (fs.existsSync("drawings.json")) drawings = JSON.parse(fs.readFileSync("drawings.json"));

// --- Auth Routes ---
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

// --- Socket.io Drawing Logic ---
io.on("connection", (socket) => {
  console.log("User connected");

  socket.emit("loadDrawings", drawings);

  socket.on("draw", (data) => {
    drawings.push(data);
    fs.writeFileSync("drawings.json", JSON.stringify(drawings, null, 2));
    io.emit("draw", data);
  });

  socket.on("clear", () => {
    drawings = [];
    fs.writeFileSync("drawings.json", JSON.stringify(drawings, null, 2));
    io.emit("clear");
  });

  socket.on("disconnect", () => {
    console.log("User disconnected");
  });
});

server.listen(PORT, () => console.log(`Server running at http://localhost:${PORT}`));
