let currentUser = null;
const MIN_DRAW_ZOOM = 10;
let pixels = {};
let brushStrokes = [];
let socket = io();

document.addEventListener("DOMContentLoaded", () => checkUser());

async function checkUser() {
  const res = await fetch("/me");
  const data = await res.json();
  if (!data.user) {
    window.location.href = "login.html";
  } else {
    currentUser = data.user;
    initMapApp();
    loadDrawings();
  }
}

function initMapApp() {
  if (window._mapInitialized) return;
  window._mapInitialized = true;

  const map = L.map("map").setView([20,0],3);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '© OpenStreetMap contributors',
    maxZoom: 19
  }).addTo(map);

  const canvas = document.createElement("canvas");
  canvas.style.position = "absolute";
  canvas.style.top = "0";
  canvas.style.left = "0";
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
  canvas.style.zIndex = 500;
  canvas.style.pointerEvents = "none";
  document.getElementById("map").appendChild(canvas);
  const ctx = canvas.getContext("2d");

  let drawing = false;
  let drawMode = false;
  let eraserMode = false;
  let brushMode = false;
  let currentColor = "#ff0000";
  let size = 10;
  let eraserSize = 20;

  let hoverLabel = document.createElement("div");
  hoverLabel.style.position = "absolute";
  hoverLabel.style.background = "rgba(0,0,0,0.7)";
  hoverLabel.style.color = "#fff";
  hoverLabel.style.padding = "2px 5px";
  hoverLabel.style.borderRadius = "3px";
  hoverLabel.style.pointerEvents = "none";
  hoverLabel.style.display = "none";
  hoverLabel.style.zIndex = 1001;
  document.body.appendChild(hoverLabel);

  function setActive(buttonId) {
    document.querySelectorAll("#toolbar button").forEach(btn => btn.classList.remove("active"));
    if(buttonId) document.getElementById(buttonId).classList.add("active");
  }

  document.getElementById("toggleDraw").onclick = () => {
    drawMode = !drawMode;
    eraserMode = false;
    canvas.style.pointerEvents = drawMode ? "auto" : "none";
    map.dragging[drawMode ? "disable" : "enable"]();
    map.scrollWheelZoom[drawMode ? "disable" : "enable"]();
    setActive(drawMode ? "toggleDraw" : null);
  };
  document.getElementById("toggleEraser").onclick = () => {
    eraserMode = !eraserMode;
    drawMode = eraserMode;
    canvas.style.pointerEvents = eraserMode ? "auto" : "none";
    map.dragging[eraserMode ? "disable" : "enable"]();
    map.scrollWheelZoom[eraserMode ? "disable" : "enable"]();
    setActive(eraserMode ? "toggleEraser" : null);
  };
  document.getElementById("toggleBrush").onclick = () => {
    brushMode = !brushMode;
    alert("Mode: " + (brushMode ? "Brush" : "Pixel"));
  };
  document.getElementById("color").oninput = (e) => currentColor = e.target.value;
  document.getElementById("size").oninput = (e) => size = parseInt(e.target.value);

  // Eraser slider
  const eraserSlider = document.createElement("input");
  eraserSlider.type = "range";
  eraserSlider.min = 5;
  eraserSlider.max = 100;
  eraserSlider.value = eraserSize;
  eraserSlider.oninput = (e)=> eraserSize = parseInt(e.target.value);
  document.getElementById("toolbar").appendChild(document.createTextNode(" Eraser Size: "));
  document.getElementById("toolbar").appendChild(eraserSlider);

  document.getElementById("logout").onclick = async () => {
    await fetch("/logout", { method: "POST" });
    window.location.href = "login.html";
  };

  function getMousePos(e) {
    const rect = canvas.getBoundingClientRect();
    return { x:e.clientX-rect.left, y:e.clientY-rect.top };
  }

  canvas.addEventListener("mousedown", e => {
    if((!drawMode && !eraserMode) || map.getZoom() < MIN_DRAW_ZOOM) return;
    drawing = true;
    draw(e);
  });
  canvas.addEventListener("mouseup", () => drawing=false);
  canvas.addEventListener("mouseout", () => drawing=false);
  canvas.addEventListener("mousemove", e => {
    if(drawing) draw(e);
    showHover(e);
  });

  function draw(e) {
    if(map.getZoom() < MIN_DRAW_ZOOM) return;
    const pos = getMousePos(e);

    if (eraserMode) {
      brushStrokes = brushStrokes.filter(s => {
        const dx = s.x - pos.x;
        const dy = s.y - pos.y;
        return !(s.user === currentUser && Math.abs(dx) < eraserSize && Math.abs(dy) < eraserSize);
      });
      for (let key in pixels) {
        const p = pixels[key];
        if(p.user===currentUser){
          const [x,y] = key.split(",").map(Number);
          if(Math.abs(x-pos.x)<eraserSize && Math.abs(y-pos.y)<eraserSize){
            delete pixels[key];
          }
        }
      }
      redrawAll();
      socket.emit("erase",{pos, eraserSize, user:currentUser});
    } else if (brushMode) {
      ctx.fillStyle = currentColor;
      ctx.beginPath();
      ctx.arc(pos.x,pos.y,size/2,0,Math.PI*2);
      ctx.fill();
      brushStrokes.push({x:pos.x,y:pos.y,color:currentColor,size,user:currentUser});
      socket.emit("draw",{x:pos.x,y:pos.y,color:currentColor,size,user:currentUser,mode:"brush"});
    } else {
      ctx.fillStyle = currentColor;
      ctx.fillRect(pos.x-size/2,pos.y-size/2,size,size);
      pixels[`${pos.x},${pos.y}`]={color:currentColor,size,user:currentUser};
      socket.emit("draw",{x:pos.x,y:pos.y,color:currentColor,size,user:currentUser,mode:"pixel"});
    }
  }

  socket.on("draw", (data)=>{
    if(data.mode==="brush") brushStrokes.push(data);
    else pixels[`${data.x},${data.y}`]=data;
    redrawAll();
  });

  socket.on("erase", (data)=>{
    brushStrokes = brushStrokes.filter(s => {
      const dx = s.x - data.pos.x;
      const dy = s.y - data.pos.y;
      return !(s.user === data.user && Math.abs(dx)<data.eraserSize && Math.abs(dy)<data.eraserSize);
    });
    for (let key in pixels){
      const p = pixels[key];
      if(p.user===data.user){
        const [x,y] = key.split(",").map(Number);
        if(Math.abs(x-data.pos.x)<data.eraserSize && Math.abs(y-data.pos.y)<data.eraserSize){
          delete pixels[key];
        }
      }
    }
    redrawAll();
  });

  function redrawAll() {
    ctx.clearRect(0,0,canvas.width,canvas.height);
    if(map.getZoom()<MIN_DRAW_ZOOM) return;
    for(let key in pixels){
      const [x,y] = key.split(",").map(Number);
      const p = pixels[key];
      ctx.fillStyle = p.color;
      ctx.fillRect(x-p.size/2,y-p.size/2,p.size,p.size);
    }
    for(let s of brushStrokes){
      ctx.fillStyle = s.color;
      ctx.beginPath();
      ctx.arc(s.x,s.y,s.size/2,0,Math.PI*2);
      ctx.fill();
    }
  }

  function showHover(e){
    const pos = getMousePos(e);
    let foundUser = null;
    for(let key in pixels){
      const [x,y] = key.split(",").map(Number);
      const p = pixels[key];
      if(Math.abs(x-pos.x)<5 && Math.abs(y-pos.y)<5){ foundUser=p.user; break; }
    }
    if(!foundUser){
      for(let s of brushStrokes){
        if(Math.abs(s.x-pos.x)<5 && Math.abs(s.y-pos.y)<5){ foundUser=s.user; break; }
      }
    }
    if(foundUser){
      hoverLabel.innerText = foundUser;
      hoverLabel.style.left = e.pageX+10+"px";
      hoverLabel.style.top = e.pageY+10+"px";
      hoverLabel.style.display = "block";
    } else hoverLabel.style.display = "none";
  }

  window.addEventListener("resize", ()=>{
    canvas.width=window.innerWidth;
    canvas.height=window.innerHeight;
    redrawAll();
  });

  async function saveDrawings(){
    if(!currentUser) return;
    const payload = { pixels, strokes: brushStrokes };
    await fetch("/save", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(payload) });
  }

  async function loadDrawings(){
    if(!currentUser) return;
    const res = await fetch("/load");
    const data = await res.json();
    if(data.pixels) pixels = data.pixels;
    if(data.strokes) brushStrokes = data.strokes;
    redrawAll();
  }

  window.addEventListener("beforeunload", saveDrawings);
  map.on("zoomend", redrawAll);
}
