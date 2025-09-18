const socket = io();

const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");
canvas.width = window.innerWidth;
canvas.height = window.innerHeight;

let drawing = false;
let tool = "pen";
let color = "#000000";
let size = 5;
let eraserSize = 20;

// Toolbar elements
const penBtn = document.getElementById("pen");
const eraserBtn = document.getElementById("eraser");
const logoutBtn = document.getElementById("logout");
const penSizeInput = document.getElementById("penSize");
const eraserSizeInput = document.getElementById("eraserSize");
const colorPicker = document.getElementById("colorPicker");
const tooltip = document.getElementById("tooltip");

penBtn.onclick = () => tool = "pen";
eraserBtn.onclick = () => tool = "eraser";
logoutBtn.onclick = () => {
  fetch("/logout", { method: "POST" }).then(() => {
    window.location.href = "/login.html";
  });
};

penSizeInput.oninput = e => size = e.target.value;
eraserSizeInput.oninput = e => eraserSize = e.target.value;
colorPicker.oninput = e => color = e.target.value;

canvas.addEventListener("mousedown", e => {
  drawing = true;
  draw(e);
});
canvas.addEventListener("mouseup", () => drawing = false);
canvas.addEventListener("mouseout", () => drawing = false);
canvas.addEventListener("mousemove", e => {
  if (drawing) draw(e);
  showTooltip(e);
});

function draw(e) {
  const x = e.clientX;
  const y = e.clientY;

  if (tool === "pen") {
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(x, y, size / 2, 0, Math.PI * 2);
    ctx.fill();
    socket.emit("draw", { x, y, color, size, user: "You" });
  } else if (tool === "eraser") {
    ctx.clearRect(x - eraserSize / 2, y - eraserSize / 2, eraserSize, eraserSize);
    socket.emit("erase", { x, y, size: eraserSize, user: "You" });
  }
}

function showTooltip(e) {
  // Simple hover tooltip showing username (dummy here)
  tooltip.style.display = "block";
  tooltip.style.left = (e.clientX + 10) + "px";
  tooltip.style.top = (e.clientY + 10) + "px";
  tooltip.textContent = "User: You";
}

// Listen for others drawing
socket.on("draw", data => {
  ctx.fillStyle = data.color;
  ctx.beginPath();
  ctx.arc(data.x, data.y, data.size / 2, 0, Math.PI * 2);
  ctx.fill();
});

socket.on("erase", data => {
  ctx.clearRect(data.x - data.size / 2, data.y - data.size / 2, data.size, data.size);
});
