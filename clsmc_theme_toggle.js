
/* CLSMC V21.0 — Modern UI Overhaul */
:root{--radius-xs:12px;--radius-sm:16px;--radius-md:20px;--radius-lg:26px;--shadow-1:0 10px 30px rgba(5,18,40,.18);--shadow-2:0 20px 60px rgba(5,18,40,.22);--transition:.18s ease;}
html[data-theme='dark']{--bg:#07111f;--bg-soft:#0c1830;--panel:#0f1c34;--panel-2:#132342;--panel-3:#0d1730;--line:#223a61;--line-soft:#314972;--text:#edf4ff;--muted:#9aa9c6;--accent:#67a8ff;--accent-2:#8a6bff;--accent-3:#4ee0b3;--danger:#ff7b8f;--warning:#ffc770;--good:#52d7a4;color-scheme:dark;}
html[data-theme='light']{--bg:#eff7f9;--bg-soft:#f7fbfc;--panel:#ffffff;--panel-2:#f6fbfc;--panel-3:#eef6f8;--line:#d6e5ea;--line-soft:#c1d6de;--text:#17384b;--muted:#6c8793;--accent:#0f8ab0;--accent-2:#4e87f5;--accent-3:#10b69f;--danger:#db6173;--warning:#d19933;--good:#2eaa7a;color-scheme:light;}
html,body{min-height:100%}
body{background:radial-gradient(circle at 0% 0%, color-mix(in srgb, var(--accent) 18%, transparent), transparent 22%),radial-gradient(circle at 100% 8%, color-mix(in srgb, var(--accent-3) 16%, transparent), transparent 26%),linear-gradient(160deg, color-mix(in srgb, var(--bg) 92%, white 8%) 0%, var(--bg) 62%, color-mix(in srgb, var(--bg-soft) 88%, black 12%) 100%) !important;color:var(--text) !important;letter-spacing:.01em}
body::before{content:'';position:fixed;inset:0;z-index:-1;pointer-events:none;background-image:linear-gradient(color-mix(in srgb, var(--line) 34%, transparent) 1px, transparent 1px),linear-gradient(90deg, color-mix(in srgb, var(--line) 28%, transparent) 1px, transparent 1px);background-size:38px 38px;opacity:.22;mask-image:linear-gradient(to bottom, black, transparent 80%)}
.topbar{background:color-mix(in srgb, var(--bg) 75%, transparent) !important;border-bottom:1px solid color-mix(in srgb, var(--line) 92%, white 8%) !important;backdrop-filter:blur(18px) saturate(130%);box-shadow:0 8px 40px rgba(5,18,40,.12)}
.topbar .brand h1,.topbar .brand h2,.topbar-brand strong,.topbar-brand h1{color:var(--text) !important}.topbar .brand small,.topbar-brand small{color:var(--muted) !important}
.logo,.topbar-logo-shell,.mini-logo{background:#fff !important;border:1px solid color-mix(in srgb, var(--line) 75%, white 25%) !important;border-radius:16px !important;box-shadow:0 10px 24px rgba(8,24,48,.12) !important}
.logo img,.topbar-logo-shell img,.mini-logo img{object-fit:contain !important;padding:4px}.topbar-logo-shell{width:44px !important;height:44px !important}
.shell{max-width:1440px !important;padding:28px 24px 70px !important}
.hero{margin:4px 0 22px !important;padding:24px 26px !important;background:linear-gradient(135deg, color-mix(in srgb, var(--panel) 97%, white 3%), color-mix(in srgb, var(--panel-2) 96%, white 4%)) !important;border:1px solid var(--line) !important;border-radius:var(--radius-lg) !important;box-shadow:var(--shadow-1) !important;position:relative;overflow:hidden}
.hero::after{content:'';position:absolute;right:-60px;top:-60px;width:180px;height:180px;border-radius:50%;background:radial-gradient(circle, color-mix(in srgb, var(--accent) 26%, transparent), transparent 65%);pointer-events:none}
.hero h1,.hero h2{font-size:clamp(28px,4vw,38px) !important;margin:0 0 8px !important;line-height:1.08}.hero p{font-size:14px !important;line-height:1.7 !important;color:var(--muted) !important;max-width:900px}
.metrics{display:grid !important;gap:16px !important;margin:20px 0 22px !important}.metrics .metric{position:relative;overflow:hidden;border-radius:var(--radius-md) !important;border:1px solid var(--line) !important;background:linear-gradient(160deg, color-mix(in srgb, var(--panel) 97%, white 3%), color-mix(in srgb, var(--panel-2) 97%, white 3%)) !important;box-shadow:var(--shadow-1) !important;padding:20px 18px !important}.metrics .metric::before{content:'';position:absolute;inset:0 auto 0 0;width:5px;background:linear-gradient(180deg, var(--accent), var(--accent-3));opacity:.95}.metric span{color:var(--muted) !important;font-size:12px !important;font-weight:700;text-transform:uppercase;letter-spacing:.08em}.metric strong{font-size:clamp(28px,4vw,34px) !important;color:var(--text) !important;margin-top:8px !important}
.panel,.card,.doctor-box,.profile,.auth-card,.login-card,.metric{border:1px solid var(--line) !important;background:linear-gradient(165deg, color-mix(in srgb, var(--panel) 97%, white 3%), color-mix(in srgb, var(--panel-2) 96%, white 4%)) !important;box-shadow:var(--shadow-1) !important;border-radius:var(--radius-md) !important}
.panel{padding:22px !important;position:relative;overflow:hidden}.panel.full{grid-column:1/-1 !important}.panel h3,.panel h2,.panel-head h3,.category-head h3{margin:0 0 6px !important;font-size:20px !important;color:var(--text) !important}.sub,.subtitle,.empty{color:var(--muted) !important;line-height:1.6}.panel-head,.category-head{border-radius:14px !important;border:1px solid var(--line) !important;background:color-mix(in srgb, var(--panel-2) 90%, transparent) !important}
.grid{gap:18px !important}.grid2{gap:16px !important}.table-wrap{margin-top:14px !important;border-radius:18px !important;border:1px solid var(--line) !important;background:color-mix(in srgb, var(--panel-3) 92%, transparent) !important;box-shadow:inset 0 1px 0 rgba(255,255,255,.03)}table{background:transparent !important}th{background:color-mix(in srgb, var(--panel-3) 92%, transparent) !important;color:var(--text) !important;font-size:12px !important;text-transform:uppercase;letter-spacing:.05em}td{color:var(--text) !important}th,td{border-bottom:1px solid color-mix(in srgb, var(--line) 88%, transparent) !important}tbody tr:hover td{background:color-mix(in srgb, var(--panel-2) 90%, transparent) !important}
.field label,label{color:var(--text) !important;font-size:12px !important;font-weight:800 !important;letter-spacing:.05em;text-transform:uppercase}input,select,textarea{border-radius:14px !important;border:1px solid var(--line) !important;background:color-mix(in srgb, var(--panel-3) 90%, transparent) !important;color:var(--text) !important;min-height:46px;padding:12px 14px !important;transition:border-color var(--transition), box-shadow var(--transition), transform var(--transition) !important}textarea{min-height:110px}input:focus,select:focus,textarea:focus{border-color:color-mix(in srgb, var(--accent) 80%, white 20%) !important;box-shadow:0 0 0 4px color-mix(in srgb, var(--accent) 20%, transparent) !important;transform:translateY(-1px)}
.btn,.btn-primary,.btn-secondary,.primary,.danger,.btn-good{min-height:44px !important;padding:11px 16px !important;border-radius:14px !important;font-weight:800 !important;letter-spacing:.01em;transition:transform var(--transition), box-shadow var(--transition), filter var(--transition), background var(--transition) !important;box-shadow:0 8px 18px rgba(10,20,40,.08)}.btn:hover,.btn-primary:hover,.btn-secondary:hover,.primary:hover,.danger:hover,.btn-good:hover{transform:translateY(-1px)}.btn-primary,.primary{background:linear-gradient(135deg, var(--accent), var(--accent-2)) !important;color:#fff !important;border:0 !important}.btn-secondary,.btn:not(.btn-primary):not(.btn-good):not(.btn-danger):not(.primary):not(.danger){background:color-mix(in srgb, var(--panel-2) 95%, white 5%) !important;color:var(--text) !important;border:1px solid var(--line-soft) !important}.btn-good{background:linear-gradient(135deg, var(--good), color-mix(in srgb, var(--good) 70%, white 30%)) !important;color:#062118 !important;border:0 !important}.btn-danger,.danger{background:color-mix(in srgb, var(--danger) 12%, var(--panel)) !important;color:color-mix(in srgb, var(--danger) 78%, white 22%) !important;border:1px solid color-mix(in srgb, var(--danger) 42%, transparent) !important}.danger-link,.edit{color:var(--accent) !important;font-weight:800 !important}
.badge,.chip,.status,.count{background:color-mix(in srgb, var(--panel-3) 88%, transparent) !important;color:var(--text) !important;border:1px solid var(--line-soft) !important;border-radius:999px !important;padding:6px 10px !important;font-size:11px !important;font-weight:700}.note,.notice,.doctor-identity,.data,.user,details.legacy{border:1px solid var(--line) !important;background:color-mix(in srgb, var(--panel-3) 90%, transparent) !important;color:var(--muted) !important;border-radius:16px !important}.flash{border-radius:16px !important;font-weight:700 !important;box-shadow:var(--shadow-1)}.flash.success{background:color-mix(in srgb, var(--good) 14%, var(--panel)) !important;border:1px solid color-mix(in srgb, var(--good) 42%, transparent) !important;color:color-mix(in srgb, var(--good) 75%, white 25%) !important}.flash.error{background:color-mix(in srgb, var(--danger) 12%, var(--panel)) !important;border:1px solid color-mix(in srgb, var(--danger) 42%, transparent) !important;color:color-mix(in srgb, var(--danger) 75%, white 25%) !important}.notice.warning{background:color-mix(in srgb, var(--warning) 12%, var(--panel)) !important;border:1px solid color-mix(in srgb, var(--warning) 42%, transparent) !important;color:color-mix(in srgb, var(--warning) 80%, white 20%) !important}
pre,.bbcode,.legacy-code{border-radius:18px !important;background:linear-gradient(180deg, #061221, #091a31) !important;color:#e9f4ff !important;border:1px solid #163861 !important;box-shadow:inset 0 1px 0 rgba(255,255,255,.04)}html[data-theme='light'] pre,html[data-theme='light'] .bbcode,html[data-theme='light'] .legacy-code{background:linear-gradient(180deg, #14384a, #102d3d) !important;border-color:#2c6980 !important}
.auth-card,.login-card,.card{border-radius:28px !important}.login-card,.auth-card,.card{overflow:hidden}.login-card::after,.auth-card::after{content:'';position:absolute;inset:auto -30px -40px auto;width:140px;height:140px;border-radius:50%;background:radial-gradient(circle, color-mix(in srgb, var(--accent-3) 28%, transparent), transparent 70%);pointer-events:none}
.developer-credit{right:16px !important;bottom:14px !important;padding:8px 12px !important;border-radius:999px !important;background:color-mix(in srgb, var(--panel) 86%, transparent) !important;border:1px solid var(--line) !important;box-shadow:var(--shadow-1) !important;color:var(--muted) !important}
main a[style*='background:#0d172b'], main div[style*='background:#152039'], [style*='background:#0f162a'], [style*='background:#0d1426']{background:color-mix(in srgb, var(--panel-3) 90%, transparent) !important;border-color:var(--line) !important;color:var(--text) !important;border-radius:16px !important}[style*='color:#9fc0ff'], [style*='color: #9fc0ff']{color:var(--accent) !important}[style*='color:#cbd6ee'], [style*='color: #cbd6ee'], [style*='color:#eef3ff']{color:var(--text) !important}
@media (max-width:980px){.shell{padding:20px 16px 62px !important}.hero{padding:20px 18px !important}}@media (max-width:700px){.metrics{grid-template-columns:1fr !important}.topbar{padding:14px 16px !important}.topbar, .topbar > div{gap:10px !important}}


/* CLSMC V21.1 — Yüksek Kontrast Okunabilirlik Düzeltmesi */

/* Koyu tema */
html[data-theme="dark"]{
  --bg:#040a13 !important;
  --bg-soft:#081426 !important;
  --panel:#0d192b !important;
  --panel-2:#12223b !important;
  --panel-3:#071322 !important;
  --line:#3a557d !important;
  --line-soft:#4b678f !important;
  --text:#ffffff !important;
  --muted:#c5d1e5 !important;
  --accent:#76b8ff !important;
  --accent-2:#a18aff !important;
  --accent-3:#61e8bd !important;
}
html[data-theme="dark"] body{color:#ffffff !important}
html[data-theme="dark"] .topbar{
  background:rgba(5,13,25,.96) !important;
  border-bottom-color:#385179 !important;
}
html[data-theme="dark"] .topbar h1,
html[data-theme="dark"] .topbar h2,
html[data-theme="dark"] .topbar strong,
html[data-theme="dark"] .topbar-brand strong{color:#ffffff !important}
html[data-theme="dark"] .topbar small,
html[data-theme="dark"] .topbar p,
html[data-theme="dark"] .topbar-brand div{color:#c9d7ec !important}
html[data-theme="dark"] .panel,
html[data-theme="dark"] .card,
html[data-theme="dark"] .metric,
html[data-theme="dark"] .auth-card,
html[data-theme="dark"] .login-card,
html[data-theme="dark"] .doctor-box,
html[data-theme="dark"] .profile{
  background:linear-gradient(160deg,#0f1d32,#0b1728) !important;
  border-color:#365178 !important;
}
html[data-theme="dark"] h1,
html[data-theme="dark"] h2,
html[data-theme="dark"] h3,
html[data-theme="dark"] h4,
html[data-theme="dark"] strong,
html[data-theme="dark"] td{color:#ffffff !important}
html[data-theme="dark"] .sub,
html[data-theme="dark"] .subtitle,
html[data-theme="dark"] .empty,
html[data-theme="dark"] .hero p,
html[data-theme="dark"] .metric span,
html[data-theme="dark"] .note,
html[data-theme="dark"] .doctor-identity,
html[data-theme="dark"] .developer-credit{color:#c5d1e5 !important}
html[data-theme="dark"] label,
html[data-theme="dark"] .field label{color:#f4f8ff !important}
html[data-theme="dark"] input,
html[data-theme="dark"] select,
html[data-theme="dark"] textarea{
  background:#071321 !important;
  color:#ffffff !important;
  border-color:#45638e !important;
}
html[data-theme="dark"] input::placeholder,
html[data-theme="dark"] textarea::placeholder{
  color:#91a4c2 !important;
  opacity:1 !important;
}
html[data-theme="dark"] th{
  background:#101f35 !important;
  color:#f2f7ff !important;
}
html[data-theme="dark"] .btn-secondary,
html[data-theme="dark"] .btn:not(.btn-primary):not(.btn-good):not(.btn-danger):not(.primary):not(.danger){
  background:#182b49 !important;
  color:#ffffff !important;
  border-color:#4d698f !important;
}
html[data-theme="dark"] .badge,
html[data-theme="dark"] .chip,
html[data-theme="dark"] .status,
html[data-theme="dark"] .count{
  background:#152844 !important;
  color:#eef5ff !important;
  border-color:#48658c !important;
}

/* Aydınlık tema */
html[data-theme="light"]{
  --bg:#e7f0f4 !important;
  --bg-soft:#f4f9fb !important;
  --panel:#ffffff !important;
  --panel-2:#f5fafc !important;
  --panel-3:#edf5f8 !important;
  --line:#b5ccd6 !important;
  --line-soft:#9ebac6 !important;
  --text:#0c2838 !important;
  --muted:#476575 !important;
  --accent:#006f94 !important;
  --accent-2:#356fd6 !important;
  --accent-3:#008e7e !important;
}
html[data-theme="light"] body{
  color:#0c2838 !important;
  background:
    radial-gradient(circle at 0% 0%,rgba(0,111,148,.11),transparent 24%),
    radial-gradient(circle at 100% 8%,rgba(0,142,126,.09),transparent 24%),
    linear-gradient(160deg,#f9fcfd 0%,#eaf3f6 58%,#e2edf1 100%) !important;
}
html[data-theme="light"] .topbar{
  background:rgba(8,73,98,.97) !important;
  border-bottom-color:#0b617f !important;
}
html[data-theme="light"] .topbar h1,
html[data-theme="light"] .topbar h2,
html[data-theme="light"] .topbar strong,
html[data-theme="light"] .topbar-brand strong{color:#ffffff !important}
html[data-theme="light"] .topbar small,
html[data-theme="light"] .topbar p,
html[data-theme="light"] .topbar-brand div{color:#d8f2fa !important}
html[data-theme="light"] .panel,
html[data-theme="light"] .card,
html[data-theme="light"] .metric,
html[data-theme="light"] .auth-card,
html[data-theme="light"] .login-card,
html[data-theme="light"] .doctor-box,
html[data-theme="light"] .profile{
  background:#ffffff !important;
  border-color:#b5ccd6 !important;
}
html[data-theme="light"] h1,
html[data-theme="light"] h2,
html[data-theme="light"] h3,
html[data-theme="light"] h4,
html[data-theme="light"] strong,
html[data-theme="light"] td{color:#0c2838 !important}
html[data-theme="light"] .sub,
html[data-theme="light"] .subtitle,
html[data-theme="light"] .empty,
html[data-theme="light"] .hero p,
html[data-theme="light"] .metric span,
html[data-theme="light"] .note,
html[data-theme="light"] .doctor-identity,
html[data-theme="light"] .developer-credit{color:#476575 !important}
html[data-theme="light"] label,
html[data-theme="light"] .field label{color:#123548 !important}
html[data-theme="light"] input,
html[data-theme="light"] select,
html[data-theme="light"] textarea{
  background:#ffffff !important;
  color:#102d3d !important;
  border-color:#9fbcc7 !important;
}
html[data-theme="light"] input::placeholder,
html[data-theme="light"] textarea::placeholder{
  color:#718995 !important;
  opacity:1 !important;
}
html[data-theme="light"] th{
  background:#dcebf0 !important;
  color:#153b4d !important;
}
html[data-theme="light"] .btn-secondary,
html[data-theme="light"] .btn:not(.btn-primary):not(.btn-good):not(.btn-danger):not(.primary):not(.danger){
  background:#eef6f8 !important;
  color:#173a4c !important;
  border-color:#9ebbc6 !important;
}
html[data-theme="light"] .badge,
html[data-theme="light"] .chip,
html[data-theme="light"] .status,
html[data-theme="light"] .count{
  background:#e2f0f4 !important;
  color:#17475a !important;
  border-color:#9ebdc8 !important;
}
html[data-theme="light"] .topbar .clsmc-theme-toggle,
html[data-theme="dark"] .topbar .clsmc-theme-toggle{
  color:#ffffff !important;
  border-color:rgba(255,255,255,.42) !important;
  background:rgba(255,255,255,.14) !important;
}

/* Genel okunabilirlik */
body,input,select,textarea,button,table{font-weight:500}
p,.sub,.subtitle,.note,.empty{line-height:1.65 !important}
table td,table th{font-size:13px !important}
