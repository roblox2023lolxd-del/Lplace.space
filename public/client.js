const map = L.map('map').setView([0, 0], 2);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

let drawMode = false;
let brushMode = true;
let eraserMode = false;
let size = 5;
let color = '#ff0000';
let drawing = false;
let currentStroke = [];
let strokes = [];

const canvasLayer = L.canvasLayer().delegate({
  onDrawLayer: function(info) {
    const ctx = info.canvas.getContext('2d');
    ctx.clearRect(0,0,info.canvas.width, info.canvas.height);
    strokes.forEach(s => {
      ctx.strokeStyle = s.color;
      ctx.lineWidth = s.size;
      ctx.beginPath();
      s.points.forEach((p,i) => {
        const pos = info.layer._map.latLngToContainerPoint(p);
        if(i===0) ctx.moveTo(pos.x,pos.y);
        else ctx.lineTo(pos.x,pos.y);
      });
      ctx.stroke();
    });
  }
}).addTo(map);

// Toolbar events
document.getElementById('drawMode').onclick = ()=>drawMode=!drawMode;
document.getElementById('brushMode').onclick = ()=>{brushMode=true; eraserMode=false;}
document.getElementById('pixelMode').onclick = ()=>{brushMode=false; eraserMode=false;}
document.getElementById('eraser').onclick = ()=>{eraserMode=true;}
document.getElementById('size').onchange = e=>size=parseInt(e.target.value);
document.getElementById('color').onchange = e=>color=e.target.value;

// Mouse events
map.on('mousedown', e=>{if(drawMode){drawing=true; currentStroke=[e.latlng];}});
map.on('mousemove', e=>{
  if(drawMode && drawing){
    if(eraserMode){
      strokes = strokes.filter(s=>!s.points.some(p=>p.distanceTo(e.latlng)<size));
    } else {
      currentStroke.push(e.latlng);
    }
    canvasLayer.redraw();
  }
});
map.on('mouseup', e=>{
  if(drawing){
    if(!eraserMode) strokes.push({points: currentStroke, color, size});
    drawing=false; currentStroke=[];
    canvasLayer.redraw();
  }
});

// Save/load drawings
async function save() {
  await fetch('/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pixels:{},strokes})});
}
async function load() {
  const res = await fetch('/load');
  const data = await res.json();
  if(data.strokes) strokes = data.strokes;
  canvasLayer.redraw();
}
load();
