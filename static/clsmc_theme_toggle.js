/* CLSMC V20.5 — Karanlık / Aydınlık Tema Denetimi */
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

.clsmc-theme-toggle{
  appearance:none;
  border:1px solid rgba(164,191,213,.48);
  border-radius:11px;
  min-height:38px;
  padding:8px 12px;
  display:inline-flex;
  align-items:center;
  justify-content:center;
  gap:7px;
  font:inherit;
  font-size:12px;
  font-weight:800;
  letter-spacing:.01em;
  cursor:pointer;
  white-space:nowrap;
  transition:transform .16s ease,background .16s ease,border-color .16s ease,box-shadow .16s ease;
}
.clsmc-theme-toggle:hover{transform:translateY(-1px)}
.clsmc-theme-toggle:active{transform:translateY(0)}
.clsmc-theme-toggle:focus-visible{outline:3px solid rgba(47,145,197,.30);outline-offset:2px}
.clsmc-theme-toggle .theme-icon{font-size:15px;line-height:1}

html[data-theme="dark"] .clsmc-theme-toggle{
  background:#202b49;
  color:#eef3ff;
  border-color:#405075;
  box-shadow:0 7px 18px rgba(0,0,0,.20);
}
html[data-theme="dark"] .clsmc-theme-toggle:hover{
  background:#293657;
  border-color:#6074a0;
}
html[data-theme="light"] .clsmc-theme-toggle{
  background:#ffffff;
  color:#17465b;
  border-color:#aed0da;
  box-shadow:0 7px 18px rgba(22,75,94,.10);
}
html[data-theme="light"] .clsmc-theme-toggle:hover{
  background:#eef8fa;
  border-color:#79b5c5;
}
.topbar .clsmc-theme-toggle{
  background:rgba(255,255,255,.11) !important;
  color:#ffffff !important;
  border-color:rgba(255,255,255,.30) !important;
  box-shadow:none !important;
}
.topbar .clsmc-theme-toggle:hover{
  background:rgba(255,255,255,.19) !important;
  border-color:rgba(255,255,255,.50) !important;
}
.clsmc-theme-toggle.is-floating{
  position:fixed;
  top:14px;
  right:14px;
  z-index:9999;
  backdrop-filter:blur(12px);
}

@media(max-width:650px){
  .clsmc-theme-toggle{padding:8px 10px}
  .clsmc-theme-toggle .theme-label{display:none}
  .clsmc-theme-toggle.is-floating .theme-label{display:inline}
}
@media(prefers-reduced-motion:reduce){
  html,body,.clsmc-theme-toggle{transition:none !important}
}

.clsmc-theme-toggle{border-radius:999px !important;min-height:40px !important;padding:8px 14px !important;font-weight:800 !important}.topbar .clsmc-theme-toggle{margin-left:4px}

/* CLSMC V23.4 KRİTİK YEDEK DÜZEN */
html{
  width:100%;
  min-width:320px;
  overflow-y:scroll;
  scrollbar-gutter:stable;
}
body{
  width:100%;
  min-width:320px;
  overflow-x:hidden !important;
}
*,*::before,*::after{box-sizing:border-box}
img,svg,video,canvas{max-width:100%}

.shell,.v22-dashboard-shell{
  width:min(1440px,calc(100% - 40px)) !important;
  max-width:1440px !important;
  margin-left:auto !important;
  margin-right:auto !important;
  padding-left:0 !important;
  padding-right:0 !important;
}

.topbar{
  width:100% !important;
  min-height:76px !important;
  padding:12px max(20px,calc((100vw - 1440px)/2)) !important;
  display:flex !important;
  align-items:center !important;
  justify-content:space-between !important;
  gap:16px !important;
  flex-wrap:nowrap !important;
}
.topbar>*{min-width:0}
.topbar .brand,.topbar-brand{
  flex:1 1 auto;
  min-width:0 !important;
  max-width:650px;
}
.topbar>:last-child,
.topbar .actions,
.topbar .v22-top-actions{
  flex:0 1 auto;
  max-width:65%;
  min-width:0;
  display:flex !important;
  align-items:center !important;
  justify-content:flex-end !important;
  gap:8px !important;
  flex-wrap:nowrap !important;
  overflow-x:auto !important;
  overflow-y:hidden !important;
  scrollbar-width:none;
}
.topbar>:last-child::-webkit-scrollbar,
.topbar .actions::-webkit-scrollbar,
.topbar .v22-top-actions::-webkit-scrollbar{display:none}
.topbar a,.topbar button{flex:0 0 auto;white-space:nowrap}

main,section,article,aside,header,footer,nav,
.panel,.card,.metric,.v22-grid,.v23-grid,
.v22-tab-panel,.v23-box,.table-wrap{min-width:0}

.grid,.grid2,.metrics,.v22-grid,.v23-grid,
.v23-metrics,.v22-metrics,.v23-manager-cards,
.v23-module-grid,.v23-announcement-form,
.v23-leave-form,.filter-grid,.data-grid{width:100%}

.grid>*,.grid2>*,.metrics>*,
.v22-grid>*,.v23-grid>*,.v23-metrics>*,
.v22-metrics>*,.v23-manager-cards>*,
.v23-module-grid>*,.v23-announcement-form>*,
.v23-leave-form>*,.filter-grid>*,.data-grid>*{min-width:0}

.table-wrap{
  width:100% !important;
  max-width:100% !important;
  overflow-x:auto !important;
  overflow-y:hidden !important;
  overscroll-behavior-inline:contain;
  -webkit-overflow-scrolling:touch;
}
.table-wrap table{
  width:100% !important;
  min-width:860px;
  margin:0;
}
table th{white-space:nowrap}
table td{overflow-wrap:anywhere}

.developer-credit{
  position:fixed !important;
  left:auto !important;
  right:16px !important;
  top:auto !important;
  bottom:14px !important;
  width:max-content !important;
  max-width:calc(100vw - 32px) !important;
  min-width:0 !important;
  margin:0 !important;
  z-index:9000 !important;
  white-space:nowrap;
  pointer-events:none;
}

.btn:hover,.btn:focus,
.btn-primary:hover,.btn-primary:focus,
.btn-secondary:hover,.btn-secondary:focus,
.primary:hover,.primary:focus,
.danger:hover,.danger:focus,
.btn-good:hover,.btn-good:focus,
.card:hover,.v22-quick-card:hover,
input:focus,select:focus,textarea:focus{
  transform:none !important;
}
.v22-tab-panel.active{animation:none !important}

@media(max-width:900px){
  .shell,.v22-dashboard-shell{
    width:calc(100% - 28px) !important;
  }
  .topbar{
    min-height:auto !important;
    padding:12px 14px !important;
    align-items:flex-start !important;
    flex-wrap:wrap !important;
  }
  .topbar .brand,.topbar-brand{
    width:100%;
    max-width:100%;
  }
  .topbar>:last-child,
  .topbar .actions,
  .topbar .v22-top-actions{
    width:100%;
    max-width:100%;
    justify-content:flex-start !important;
  }
}
@media(max-width:650px){
  .shell,.v22-dashboard-shell{
    width:calc(100% - 20px) !important;
  }
  .v23-announcement-form{grid-template-columns:1fr !important}
  .developer-credit{
    right:10px !important;
    bottom:8px !important;
    font-size:10px !important;
  }
}
