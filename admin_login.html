(function(){
  "use strict";
  var STORAGE_KEY = "clsmc-interface-theme";
  var LIGHT_ID = "clsmc-light-theme";

  function normalizeTheme(value){
    return value === "light" ? "light" : "dark";
  }

  function readTheme(){
    try{return normalizeTheme(localStorage.getItem(STORAGE_KEY));}
    catch(error){return normalizeTheme(document.documentElement.dataset.theme);}
  }

  function saveTheme(theme){
    try{localStorage.setItem(STORAGE_KEY, theme);}catch(error){}
  }

  function setLightStylesheet(theme){
    var sheet = document.getElementById(LIGHT_ID);
    if(sheet){sheet.media = theme === "light" ? "all" : "not all";}
  }

  function updateButton(button, theme){
    var isLight = theme === "light";
    var icon = button.querySelector(".theme-icon");
    var label = button.querySelector(".theme-label");
    if(icon){icon.textContent = isLight ? "☀️" : "🌙";}
    if(label){label.textContent = isLight ? "Aydınlık Mod" : "Karanlık Mod";}
    button.setAttribute("aria-label", isLight ? "Karanlık arayüze geç" : "Aydınlık arayüze geç");
    button.title = isLight ? "Karanlık arayüze geç" : "Aydınlık arayüze geç";
    button.setAttribute("aria-pressed", String(isLight));
  }

  function applyTheme(theme, persist){
    theme = normalizeTheme(theme);
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
    setLightStylesheet(theme);
    document.querySelectorAll("[data-clsmc-theme-toggle]").forEach(function(button){
      updateButton(button, theme);
    });
    if(persist){saveTheme(theme);}
    window.dispatchEvent(new CustomEvent("clsmc:themechange", {detail:{theme:theme}}));
  }

  function locateHost(){
    var topbar = document.querySelector(".topbar");
    if(!topbar){return null;}
    var children = Array.prototype.slice.call(topbar.children);
    if(children.length > 1){return children[children.length - 1];}
    return topbar;
  }

  function createButton(){
    if(document.querySelector("[data-clsmc-theme-toggle]")){return;}
    var button = document.createElement("button");
    button.type = "button";
    button.className = "clsmc-theme-toggle";
    button.setAttribute("data-clsmc-theme-toggle", "");
    button.innerHTML = '<span class="theme-icon" aria-hidden="true"></span><span class="theme-label"></span>';
    button.addEventListener("click", function(){
      var next = document.documentElement.dataset.theme === "light" ? "dark" : "light";
      applyTheme(next, true);
    });

    var host = locateHost();
    if(host){
      host.appendChild(button);
    }else{
      button.classList.add("is-floating");
      document.body.appendChild(button);
    }
    updateButton(button, readTheme());
  }

  function start(){
    applyTheme(readTheme(), false);
    createButton();
  }

  if(document.readyState === "loading"){
    document.addEventListener("DOMContentLoaded", start, {once:true});
  }else{
    start();
  }

  window.CLSMCTheme = {set: function(theme){applyTheme(theme, true);}, get: readTheme};
})();
