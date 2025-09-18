let currentUser = null;
let drawMode = false;
let tool = "pixel"; // pixel/brush/eraser
let brushSize = 5;
let strokes = [];

let map, canvas, ctx;

// Initialize map
window.onload = async () => {
  // Leaflet map
  map = L.map('map').setView([20, 0], 2);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);

  // Canvas overlay
  canvas = document.getElementById('drawCanvas');
  ctx = canvas.getContext('2d');
  resizeCanvas();

  window.addEventListener('resize', resizeCanvas);

  // Check logged in user
  const userRes = await fetch("/me");
  const data = await userRes.json();
  currentUser = data.user;

  if(currentUser) await loadDrawings();

  setupDrawing();
  setupUI();
};

function resizeCanvas() {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
}

// Drawing
function setupDrawing() {
  let drawing = false;

  canvas.addEventListener("mousedown", e => {
    if(!drawMode) return;
    drawing = true;
  });

  canvas.addEventListener("mouseup", e => {
    if(!drawMode) return;
    drawing = false;
    saveDrawings();
  });

  canvas.addEventListener("mousemove", e => {
    if(!drawMode || !drawing) return;

    const x = e.offsetX;
    const y = e.offsetY;

    if(tool === "pixel") {
      ctx.fillStyle = "red";
      ctx.fillRect(x,y,1,1);
      strokes.push({x,y,tool:"pixel"});
    } else if(tool === "brush") {
      ctx.fillStyle = "blue";
      ctx.beginPath();
      ctx.arc(x,y,brushSize,0,Math.PI*2);
      ctx.fill();
      strokes.push({x,y,tool:"brush",size:brushSize});
    } else if(tool === "eraser") {
      ctx.clearRect(x-brushSize/2, y-brushSize/2, brushSize, brushSize);
      strokes.push({x,y,tool:"eraser",size:brushSize});
    }
  });
}

// Save drawings
async function saveDrawings() {
  if(!currentUser) return;
  await fetch("/save", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body: JSON.stringify({strokes})
  });
}

// Load drawings
async function loadDrawings() {
  const res = await fetch("/load");
  const data = await res.json();
  strokes = data.strokes || [];
  drawLoadedStrokes();
}

function drawLoadedStrokes() {
  for(let s of strokes) {
    if(s.tool==="pixel") ctx.fillRect(s.x,s.y,1,1);
    if(s.tool==="brush") { ctx.beginPath(); ctx.arc(s.x,s.y,s.size,0,Math.PI*2); ctx.fill(); }
    if(s.tool==="eraser") ctx.clearRect(s.x-s.size/2,s.y-s.size/2,s.size,s.size);
  }
}

// UI
function setupUI() {
  document.getElementById("pixelBtn").onclick = () => tool="pixel";
  document.getElementById("brushBtn").onclick = () => tool="brush";
  document.getElementById("eraserBtn").onclick = () => tool="eraser";
  document.getElementById("sizeInput").oninput = e => brushSize = parseInt(e.target.value);

  document.getElementById("drawModeBtn").onclick = () => {
    drawMode = !drawMode;
    canvas.style.pointerEvents = drawMode ? "auto" : "none";
    map.dragging[drawMode ? "disable":"enable"]();
    map.scrollWheelZoom[drawMode ? "disable":"enable"]();
    canvas.style.cursor = drawMode ? "crosshair":"default";
  };
}
