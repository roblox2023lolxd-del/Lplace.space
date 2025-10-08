const socket = io();
const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");
const colorPicker = document.getElementById("colorPicker");
const sizePicker = document.getElementById("sizePicker");
const clearBtn = document.getElementById("clearBtn");
const eraserBtn = document.getElementById("eraserBtn");
const logoutBtn = document.getElementById("logoutBtn");

let drawing = false;
let color = colorPicker.value;
let size = sizePicker.value;
let erasing = false;

canvas.width = window.innerWidth;
canvas.height = window.innerHeight;

colorPicker.oninput = (e) => (color = e.target.value);
sizePicker.oninput = (e) => (size = e.target.value);
eraserBtn.onclick = () => (erasing = !erasing, eraserBtn.textContent = erasing ? "✏️ Draw" : "🩹 Eraser");
logoutBtn.onclick = () => (localStorage.removeItem("user"), window.location.href = "/");

clearBtn.onclick = () => socket.emit("clear");

canvas.onmousedown = () => (drawing = true);
canvas.onmouseup = () => (drawing = false);
canvas.onmouseout = () => (drawing = false);
canvas.onmousemove = (e) => {
  if (!drawing) return;
  const x = e.clientX;
  const y = e.clientY;
  const drawData = { x, y, color: erasing ? "#f5f5f5" : color, size };
  draw(drawData);
  socket.emit("draw", drawData);
};

socket.on("draw", draw);
socket.on("loadDrawings", (all) => all.forEach(draw));
socket.on("clear", () => ctx.clearRect(0, 0, canvas.width, canvas.height));

function draw({ x, y, color, size }) {
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.arc(x, y, size / 2, 0, Math.PI * 2);
  ctx.fill();
}
