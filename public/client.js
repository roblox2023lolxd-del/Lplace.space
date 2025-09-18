document.addEventListener('DOMContentLoaded', () => {

  // MAP
  const map = L.map('map').setView([40.7128, -74.006], 13);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution:'&copy; OpenStreetMap contributors'
  }).addTo(map);

  // CANVAS
  const canvas = document.getElementById('drawCanvas');
  const ctx = canvas.getContext('2d');
  function resizeCanvas(){ canvas.width=window.innerWidth; canvas.height=window.innerHeight; }
  window.addEventListener('resize', resizeCanvas);
  resizeCanvas();

  // CONTROLS
  let drawMode=false, drawing=false, eraser=false, brushMode=false;
  let size=parseInt(document.getElementById('sizeInput').value);
  const minZoomForDrawing = 10;
  document.getElementById('drawModeBtn').onclick = ()=>{
      drawMode=!drawMode;
      if(drawMode){ map.dragging.disable(); map.scrollWheelZoom.disable(); }
      else{ map.dragging.enable(); map.scrollWheelZoom.enable(); }
  };
  document.getElementById('pixelBtn').onclick=()=>{brushMode=false; eraser=false;};
  document.getElementById('brushBtn').onclick=()=>{brushMode=true; eraser=false;};
  document.getElementById('eraserBtn').onclick=()=>{eraser=true;};
  document.getElementById('sizeInput').oninput=e=>{size=parseInt(e.target.value);};

  // DRAWINGS
  let allDrawings={}; 
  let currentUser=null;

  // Fetch logged-in user
  fetch('/me').then(r=>r.json()).then(data=>{ 
      currentUser=data.user; 
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

  // DRAWING LOGIC
  let currentStroke=null;
  canvas.addEventListener('mousedown', e=>{
      if(!drawMode || !currentUser) return;
      if(map.getZoom() < minZoomForDrawing){
          alert("Zoom in closer to a city to draw!");
          return;
      }
      drawing=true;
      const color = eraser?'#ffffff':'#00ffff';
      currentStroke={size, color, points:[{x:e.offsetX, y:e.offsetY}]};
  });
  canvas.addEventListener('mousemove', e=>{
      if(!drawing||!drawMode||!currentUser) return;
      const point={x:e.offsetX, y:e.offsetY};
      currentStroke.points.push(point);
      ctx.lineWidth=currentStroke.size;
      ctx.lineCap='round';
      ctx.strokeStyle=currentStroke.color;
      ctx.beginPath();
      const pts=currentStroke.points;
      ctx.moveTo(pts[pts.length-2].x, pts[pts.length-2].y);
      ctx.lineTo(pts[pts.length-1].x, pts[pts.length-1].y);
      ctx.stroke();
  });
  canvas.addEventListener('mouseup', e=>{
      if(drawing && currentStroke && currentUser){
          if(!allDrawings[currentUser]) allDrawings[currentUser]={strokes:[]};
          allDrawings[currentUser].strokes.push(currentStroke);
          saveDrawings();
          currentStroke=null;
      }
      drawing=false;
  });
  canvas.addEventListener('mouseout',()=>{drawing=false; currentStroke=null;});

  // Hover username
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

  // Cursor for zoom restriction
  map.on('zoomend', ()=>{
      canvas.style.cursor = map.getZoom() < minZoomForDrawing ? 'not-allowed':'crosshair';
  });

});
