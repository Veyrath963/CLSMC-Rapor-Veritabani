(function(){
  "use strict";
  function forceLight(){
    document.documentElement.dataset.theme="light";
    document.documentElement.style.colorScheme="light";
    try{localStorage.setItem("clsmc-interface-theme","light");}catch(error){}
    var sheet=document.getElementById("clsmc-light-theme");
    if(sheet){sheet.media="all";}
    document.querySelectorAll("[data-clsmc-theme-toggle]").forEach(function(button){button.remove();});
  }
  forceLight();
  if(document.readyState==="loading"){document.addEventListener("DOMContentLoaded",forceLight,{once:true});}
  window.CLSMCTheme={set:forceLight,get:function(){return "light";}};
})();
