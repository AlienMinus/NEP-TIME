// Drag-and-drop foundation for future course/faculty assignment screens.
document.querySelectorAll("[draggable=true]").forEach(el=>{
  el.addEventListener("dragstart",e=>e.dataTransfer.setData("text/plain",el.dataset.id||el.id));
});
document.querySelectorAll(".drop-zone").forEach(zone=>{
  zone.addEventListener("dragover",e=>e.preventDefault());
  zone.addEventListener("drop",e=>{
    e.preventDefault();
    const id=e.dataTransfer.getData("text/plain");
    const source=document.getElementById(id);
    if(source) zone.appendChild(source);
  });
});
