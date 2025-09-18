let currentUser = null;
let drawMode = false;
let tool = "pixel"; // "pixel" or "brush" or "eraser"
let brushSize = 5;
let pixels = {};
let strokes = [];
let canvas, ctx;

// Setup canvas
window.onload = async () => {
  canvas = document.getElementById("mapCanvas");
  ctx = canvas.getContext("2d");
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;

  const userRes = await fetch("/me");
  const data = await userRes.json();
  currentUser = data.user;

  if (currentUser) loadDrawings();

  setupDrawing();
};

function setupDrawing() {
  let drawing = false;

  canvas.addEventListener("mousedown", e => { if(drawMode) drawing=true; });
  canvas.addEventListener("mouseup", e => { drawing=false; saveDrawings(); });
  canvas.addEventListener("mousemove", e => {
    if (!drawing || !drawMode) return;

    const x = e.offsetX;
    const y = e.offsetY;

    if(tool === "pixel") {
      ctx.fillStyle = "red";
      ctx.fillRect(x, y, 1, 1);
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

async function saveDrawings() {
  if(!currentUser) return;
  await fetch("/save", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body: JSON.stringify({ pixels, strokes })
  });
}

async function loadDrawings() {
  const res = await fetch("/load");
  const data = await res.json();
  strokes = data.strokes || [];
  drawLoadedStrokes();
}

function drawLoadedStrokes() {
  for(let s of strokes) {
    if(s.tool === "pixel") ctx.fillRect(s.x,s.y,1,1);
    if(s.tool === "brush") {
      ctx.beginPath();
      ctx.arc(s.x,s.y,s.size,0,Math.PI*2);
      ctx.fill();
    }
    if(s.tool === "eraser") ctx.clearRect(s.x-s.size/2,s.y-s.size/2,s.size,s.size);
  }
}
