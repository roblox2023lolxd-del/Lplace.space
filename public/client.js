document.addEventListener('DOMContentLoaded', () => {

  // ===== MAP SETUP =====
  const map = L.map('map').setView([40.7128, -74.006], 13);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution:'&copy; OpenStreetMap contributors'
  }).addTo(map);

  // ===== CANVAS SETUP =====
  const canvas = document.getElementById('drawCanvas');
  const ctx = canvas.getContext('2d');
  function resizeCanvas(){ canvas.width=window.innerWidth; canvas.height=window.innerHeight; }
  window.addEventListener('resize', resizeCanvas);
  resizeCanvas();

  // ===== CONTROLS =====
  let drawMode=false, drawing=false, eraser=false, brushMode=false, pixelMode=true;
  let size=parseInt(document.getElementById('sizeInput').value);
  const minZoomForDrawing = 10;

  const drawModeBtn=document.getElementById('drawModeBtn');
  const pixelBtn=document.getElementById('pixelBtn');
  const brushBtn=document.getElementById('brushBtn');
  const eraserBtn=document.getElementById('eraserBtn');
  const sizeInput=document.getElementById('sizeInput');

  function updateModeIndicators(){
      drawModeBtn.style.background = drawMode ? "#0f0" : "#fff";
      pixelBtn.style.background = pixelMode && !brushMode && !eraser ? "#0f0" : "#fff";
      brushBtn.style.background = brushMode ? "#0f0" : "#fff";
      eraserBtn.style.background = eraser ? "#f00" : "#fff";
  }

  drawModeBtn.addEventListener('click', ()=>{
      drawMode=!drawMode;
      if(drawMode){ 
          map.dragging.disable(); map.scrollWheelZoom.disable(); 
      } else { 
          map.dragging.enable(); map.scrollWheelZoom.enable(); 
      }
      updateModeIndicators();
  });
  pixelBtn.addEventListener('click', ()=>{pixelMode=true; brushMode=false; eraser=false; updateModeIndicators();});
  brushBtn.addEventListener('click', ()=>{brushMode=true; pixelMode=false; eraser=false; updateModeIndicators();});
  eraserBtn.addEventListener('click', ()=>{eraser=true; pixelMode=false; brushMode=false; updateModeIndicators();});
  sizeInput.addEventListener('input', e=>{size=parseInt(e.target.value);});

  updateModeIndicators();

  // ===== USER AND DRAWINGS =====
  let allDrawings={}; 
  let currentUser=null;

  fetch('/me').then(r=>r.json()).then(data=>{ 
      currentUser=data.user; 
      if(!currentUser){
          alert("Not logged in! Redirecting to login.");
          window.location.href="/login.html";
      }
      loadDrawings(); 
  });

  function loadDrawings(){
      fetch('/load').then(r=>r.json()).then(userDrawings=>{
          if(userDrawings) allDrawings[currentUser]=userDrawings;
          fetch('/allDrawings').then(r=>r.json()).then(all=>{
              allDrawings=all; redrawCanvas();
          });
      });
  }

  function saveDrawings(){
      if(!currentUser) return;
      fetch('/save',{
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body:JSON.stringify(allDrawings[currentUser])
      });
  }

  function redrawCanvas(){
      ctx.clearRect(0,0,canvas.width,canvas.height);
      for(const user in allDrawings){
          const strokes=allDrawings[user].strokes||[];
          strokes.forEach(s=>{
              ctx.lineWidth=s.size;
              ctx.lineCap='round';
              ctx.strokeStyle=s.color;
              ctx.beginPath();
              for(let i=0;i<s.points.length;i++){
                  const p=s.points[i];
                  if(i===0) ctx.moveTo(p.x,p.y);
                  else ctx.lineTo(p.x,p.y);
              }
              ctx.stroke();
          });
      }
  }

  // ===== DRAWING =====
  let currentStroke=null;

  function getColor(){
      if(eraser) return null; // null for eraser
      if(brushMode) return "#00ffff";
      return "#000"; // pixel mode
  }

  canvas.addEventListener('mousedown', e=>{
      if(!drawMode || !currentUser) return;
      if(map.getZoom() < minZoomForDrawing){
          alert("Zoom in closer to a city to draw!");
          return;
      }
      drawing=true;
      const color = getColor();
      currentStroke={size, color, points:[{x:e.offsetX, y:e.offsetY}], user: currentUser};
  });

  canvas.addEventListener('mousemove', e=>{
      if(!drawing || !drawMode || !currentUser) return;
      const point={x:e.offsetX, y:e.offsetY};
      currentStroke.points.push(point);
      ctx.lineWidth=currentStroke.size;
      ctx.lineCap='round';
      ctx.strokeStyle=currentStroke.color||"#ffffff";
      ctx.beginPath();
      const pts=currentStroke.points;
      ctx.moveTo(pts[pts.length-2].x, pts[pts.length-2].y);
      ctx.lineTo(pts[pts.length-1].x, pts[pts.length-1].y);
      ctx.stroke();
  });

  canvas.addEventListener('mouseup', e=>{
      if(drawing && currentStroke && currentUser){
          if(!allDrawings[currentUser]) allDrawings[currentUser]={strokes:[]};
          if(eraser){
              // Remove strokes intersecting currentStroke points (only your strokes)
              const userStrokes = allDrawings[currentUser].strokes;
              allDrawings[currentUser].strokes = userStrokes.filter(s=>{
                  for(const p1 of s.points){
                      for(const p2 of currentStroke.points){
                          if(Math.abs(p1.x-p2.x)<size && Math.abs(p1.y-p2.y)<size) return false;
                      }
                  }
                  return true;
              });
          } else {
              allDrawings[currentUser].strokes.push(currentStroke);
          }
          saveDrawings();
          redrawCanvas();
          currentStroke=null;
      }
      drawing=false;
  });

  canvas.addEventListener('mouseout',()=>{drawing=false; currentStroke=null;});

  // ===== HOVER USERNAME =====
  canvas.addEventListener('mousemove', e=>{
      let hoverUser=null;
      for(const user in allDrawings){
          if(user===currentUser) continue;
          allDrawings[user].strokes.forEach(s=>{
              s.points.forEach(p=>{
                  if(Math.abs(p.x-e.offsetX)<size && Math.abs(p.y-e.offsetY)<size){
                      hoverUser=user;
                  }
              });
          });
      }
      canvas.title = hoverUser?`Drawing by: ${hoverUser}`:'';
  });

  // ===== CURSOR =====
  map.on('zoomend', ()=>{
      canvas.style.cursor = map.getZoom() < minZoomForDrawing ? 'not-allowed':'crosshair';
  });

  // ===== LOGOUT BUTTON =====
  const logoutBtn=document.createElement('button');
  logoutBtn.textContent="Logout";
  logoutBtn.style.position="absolute";
  logoutBtn.style.top="10px";
  logoutBtn.style.right="10px";
  logoutBtn.style.zIndex=20;
  logoutBtn.style.fontFamily="monospace";
  document.body.appendChild(logoutBtn);
  logoutBtn.addEventListener('click', ()=>{
      fetch('/logout',{method:'POST'}).then(()=>window.location.href="/login.html");
  });

});
