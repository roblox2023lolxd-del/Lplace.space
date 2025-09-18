document.addEventListener('DOMContentLoaded', () => {

  // ===== MAP SETUP =====
  const map = L.map('map').setView([40.7128, -74.006], 13);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution:'&copy; OpenStreetMap contributors'
  }).addTo(map);

  // ===== CANVAS SETUP =====
  const canvas = document.getElementById('drawCanvas');
  const ctx = canvas.getContext('2d');

  function resizeCanvas(){
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
      redrawCanvas();
  }
  window.addEventListener('resize', resizeCanvas);
  resizeCanvas();

  // ===== CONTROLS =====
  let drawMode=false, drawing=false, eraser=false, brushMode=false, pixelMode=true;
  let size=5;
  const minZoomForDrawing = 10;

  const drawModeBtn = document.getElementById('drawModeBtn');
  const pixelBtn = document.getElementById('pixelBtn');
  const brushBtn = document.getElementById('brushBtn');
  const eraserBtn = document.getElementById('eraserBtn');
  const sizeInput = document.getElementById('sizeInput');

  function setMode(mode){
      brushMode = pixelMode = eraser = false;
      if(mode==='brush') brushMode=true;
      else if(mode==='pixel') pixelMode=true;
      else if(mode==='eraser') eraser=true;
      updateIndicators();
  }

  function updateIndicators(){
      drawModeBtn.style.background = drawMode ? "#0f0" : "#fff";
      pixelBtn.style.background = pixelMode ? "#0f0" : "#fff";
      brushBtn.style.background = brushMode ? "#0f0" : "#fff";
      eraserBtn.style.background = eraser ? "#f00" : "#fff";

      if(drawMode){
          canvas.style.pointerEvents="auto";
          canvas.style.cursor = eraser ? "crosshair" : "crosshair";
          map.dragging.disable();
          map.scrollWheelZoom.disable();
      } else {
          canvas.style.pointerEvents="none";
          canvas.style.cursor="default";
          map.dragging.enable();
          map.scrollWheelZoom.enable();
      }
  }

  drawModeBtn.addEventListener('click', ()=>{ drawMode = !drawMode; updateIndicators(); });
  pixelBtn.addEventListener('click', ()=>{ setMode('pixel'); });
  brushBtn.addEventListener('click', ()=>{ setMode('brush'); });
  eraserBtn.addEventListener('click', ()=>{ setMode('eraser'); });
  sizeInput.addEventListener('input', e=>{ size=parseInt(e.target.value); });

  updateIndicators();

  // ===== USER & DRAWINGS =====
  let allDrawings={};
  let currentUser=null;

  fetch('/me').then(r=>r.json()).then(data=>{
      currentUser = data.user;
      if(!currentUser){
          alert("Not logged in!");
          window.location.href="/login.html";
      }
      loadDrawings();
  });

  function loadDrawings(){
      fetch('/load').then(r=>r.json()).then(userDrawings=>{
          if(userDrawings) allDrawings[currentUser] = userDrawings;
          fetch('/allDrawings').then(r=>r.json()).then(all=>{
              allDrawings = all;
              redrawCanvas();
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

  // ===== DRAWING =====
  let currentStroke=null;

  function getColor(){
      if(eraser) return null;
      if(brushMode) return "#00ffff";
      return "#000"; // pixel mode
  }

  function latLngToCanvasPoint(latlng){
      const point = map.latLngToContainerPoint(latlng);
      return {x:point.x, y:point.y};
  }

  function canvasPointToLatLng(point){
      return map.containerPointToLatLng([point.x, point.y]);
  }

  canvas.addEventListener('mousedown', e=>{
      if(!drawMode || !currentUser) return;
      if(map.getZoom() < minZoomForDrawing){
          alert("Zoom in closer to draw!");
          return;
      }
      drawing=true;
      const latlng = map.containerPointToLatLng([e.offsetX,e.offsetY]);
      currentStroke = { size, color:getColor(), points:[latlng], user: currentUser };
  });

  canvas.addEventListener('mousemove', e=>{
      if(!drawing || !drawMode || !currentUser) return;
      const latlng = map.containerPointToLatLng([e.offsetX,e.offsetY]);
      currentStroke.points.push(latlng);
      redrawCanvas();
      drawCurrentStroke();
  });

  canvas.addEventListener('mouseup', ()=>{
      if(drawing && currentStroke && currentUser){
          if(!allDrawings[currentUser]) allDrawings[currentUser]={strokes:[]};
          if(eraser){
              const userStrokes = allDrawings[currentUser].strokes;
              allDrawings[currentUser].strokes = userStrokes.filter(s=>{
                  for(const p1 of s.points){
                      for(const p2 of currentStroke.points){
                          const pt1 = latLngToCanvasPoint(p1);
                          const pt2 = latLngToCanvasPoint(p2);
                          if(Math.abs(pt1.x-pt2.x)<size && Math.abs(pt1.y-pt2.y)<size) return false;
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

  canvas.addEventListener('mouseout', ()=>{ drawing=false; currentStroke=null; });

  // ===== DRAW HELPERS =====
  function drawStroke(s){
      if(!s.points || s.points.length<1) return;
      ctx.lineWidth=s.size;
      ctx.lineCap='round';
      ctx.strokeStyle=s.color||"#ffffff";
      if(pixelMode){
          s.points.forEach(p=>{
              const pt = latLngToCanvasPoint(p);
              ctx.fillStyle=s.color;
              ctx.fillRect(pt.x-size/2, pt.y-size/2, size, size);
          });
      } else {
          ctx.beginPath();
          s.points.forEach((p,i)=>{
              const pt = latLngToCanvasPoint(p);
              if(i===0) ctx.moveTo(pt.x, pt.y);
              else ctx.lineTo(pt.x, pt.y);
          });
          ctx.stroke();
      }
  }

  function drawCurrentStroke(){
      if(currentStroke) drawStroke(currentStroke);
  }

  function redrawCanvas(){
      ctx.clearRect(0,0,canvas.width,canvas.height);
      for(const user in allDrawings){
          const strokes = allDrawings[user].strokes || [];
          strokes.forEach(s=>drawStroke(s));
      }
  }

  map.on('move zoom', redrawCanvas);

  // ===== HOVER USERNAME =====
  canvas.addEventListener('mousemove', e=>{
      let hoverUser=null;
      for(const user in allDrawings){
          if(user===currentUser) continue;
          allDrawings[user].strokes.forEach(s=>{
              s.points.forEach(p=>{
                  const pt = latLngToCanvasPoint(p);
                  if(Math.abs(pt.x-e.offsetX)<size && Math.abs(pt.y-e.offsetY)<size){
                      hoverUser=user;
                  }
              });
          });
      }
      canvas.title = hoverUser ? `Drawing by: ${hoverUser}` : '';
  });

  // ===== LOGOUT BUTTON =====
  const logoutBtn = document.createElement('button');
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
