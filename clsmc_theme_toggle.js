/* CLSMC V20.6 — Sol Alt Hızlı Menü ve Tema Denetimi */
html{transition:background-color .18s ease}
body{transition:background-color .18s ease,color .18s ease}

/* Logo her iki temada da özgün haliyle kalır. */
.logo,.mini-logo,.topbar-logo-shell{
  overflow:hidden !important;
  background:#ffffff !important;
  border:1px solid rgba(148,181,198,.72) !important;
  box-shadow:0 0 0 3px rgba(37,139,171,.08),0 9px 22px rgba(0,0,0,.15) !important;
  flex:0 0 auto;
}
.logo img,.mini-logo img,.topbar-logo-shell img{
  display:block !important;
  width:100% !important;
  height:100% !important;
  object-fit:cover !important;
  border-radius:inherit !important;
}
.topbar-logo-shell{width:40px;height:40px;border-radius:12px}

.clsmc-sr-only{
  position:absolute!important;width:1px!important;height:1px!important;padding:0!important;
  margin:-1px!important;overflow:hidden!important;clip:rect(0,0,0,0)!important;
  white-space:nowrap!important;border:0!important;
}

.clsmc-quick-menu{
  position:fixed;
  left:18px;
  bottom:18px;
  z-index:10050;
  display:flex;
  flex-direction:column;
  align-items:center;
  gap:10px;
  pointer-events:none;
}
.clsmc-quick-menu-trigger,.clsmc-quick-action{
  appearance:none;
  width:46px;
  height:46px;
  border-radius:14px;
  display:inline-flex;
  align-items:center;
  justify-content:center;
  padding:0;
  font:inherit;
  font-size:19px;
  line-height:1;
  text-decoration:none;
  cursor:pointer;
  pointer-events:auto;
  transition:transform .16s ease,background .16s ease,border-color .16s ease,box-shadow .16s ease,opacity .16s ease;
}
.clsmc-quick-menu-trigger:hover,.clsmc-quick-action:hover{transform:translateY(-1px)}
.clsmc-quick-menu-trigger:active,.clsmc-quick-action:active{transform:translateY(0)}
.clsmc-quick-menu-trigger:focus-visible,.clsmc-quick-action:focus-visible{
  outline:3px solid rgba(47,145,197,.34);
  outline-offset:3px;
}
.clsmc-quick-menu-trigger{
  border:1px solid #405075;
  background:#202b49;
  color:#eef3ff;
  box-shadow:0 10px 26px rgba(0,0,0,.26);
}
.clsmc-quick-menu-trigger:hover{background:#293657;border-color:#6074a0}

.clsmc-quick-menu-panel{
  display:flex;
  flex-direction:column;
  gap:9px;
  padding:9px;
  border-radius:18px;
  opacity:0;
  visibility:hidden;
  transform:translateY(10px) scale(.96);
  transform-origin:bottom center;
  pointer-events:none;
  transition:opacity .16s ease,transform .16s ease,visibility .16s ease;
}
.clsmc-quick-menu-panel.is-open{
  opacity:1;
  visibility:visible;
  transform:translateY(0) scale(1);
  pointer-events:auto;
}
.clsmc-quick-action{
  position:relative;
  border:1px solid #405075;
  background:#202b49;
  color:#eef3ff;
  box-shadow:0 7px 18px rgba(0,0,0,.20);
}
.clsmc-quick-action:hover{background:#293657;border-color:#6074a0}
.clsmc-quick-action::after{
  content:attr(data-tooltip);
  position:absolute;
  left:56px;
  top:50%;
  transform:translateY(-50%) translateX(-4px);
  padding:7px 9px;
  border-radius:8px;
  background:#0b1020;
  color:#eef3ff;
  border:1px solid #344264;
  box-shadow:0 7px 18px rgba(0,0,0,.24);
  font-size:11px;
  font-weight:750;
  line-height:1;
  white-space:nowrap;
  opacity:0;
  visibility:hidden;
  pointer-events:none;
  transition:opacity .14s ease,transform .14s ease,visibility .14s ease;
}
.clsmc-quick-action:hover::after,.clsmc-quick-action:focus-visible::after{
  opacity:1;
  visibility:visible;
  transform:translateY(-50%) translateX(0);
}

html[data-theme="light"] .clsmc-quick-menu-trigger{
  background:#ffffff;
  color:#17465b;
  border-color:#aed0da;
  box-shadow:0 9px 22px rgba(22,75,94,.16);
}
html[data-theme="light"] .clsmc-quick-menu-trigger:hover{
  background:#eef8fa;
  border-color:#79b5c5;
}
html[data-theme="light"] .clsmc-quick-menu-panel{
  background:rgba(255,255,255,.94);
  border:1px solid #c7dce3;
  box-shadow:0 14px 34px rgba(22,75,94,.16);
  backdrop-filter:blur(14px);
}
html[data-theme="dark"] .clsmc-quick-menu-panel{
  background:rgba(17,26,46,.94);
  border:1px solid #344264;
  box-shadow:0 14px 34px rgba(0,0,0,.30);
  backdrop-filter:blur(14px);
}
html[data-theme="light"] .clsmc-quick-action{
  background:#ffffff;
  color:#17465b;
  border-color:#aed0da;
  box-shadow:0 7px 18px rgba(22,75,94,.10);
}
html[data-theme="light"] .clsmc-quick-action:hover{
  background:#eef8fa;
  border-color:#79b5c5;
}
html[data-theme="light"] .clsmc-quick-action::after{
  background:#ffffff;
  color:#17465b;
  border-color:#aed0da;
  box-shadow:0 7px 18px rgba(22,75,94,.14);
}

@media(max-width:650px){
  .clsmc-quick-menu{left:12px;bottom:12px}
  .clsmc-quick-menu-trigger,.clsmc-quick-action{width:44px;height:44px;border-radius:13px}
  .clsmc-quick-action::after{display:none}
}
@media(prefers-reduced-motion:reduce){
  html,body,.clsmc-quick-menu-trigger,.clsmc-quick-action,.clsmc-quick-menu-panel{transition:none!important}
}
