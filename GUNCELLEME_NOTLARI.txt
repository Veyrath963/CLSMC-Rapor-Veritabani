from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-me")

database_url = os.environ.get("DATABASE_URL", "").strip()
if not database_url:
    # Production'da sessizce geçici SQLite'a düşmek veri kaybına yol açabilir.
    # Render üzerinde DATABASE_URL zorunludur; yerel geliştirmede SQLite kullanılabilir.
    if os.environ.get("RENDER"):
        raise RuntimeError(
            "DATABASE_URL is required on Render. Add your Neon PostgreSQL connection string "
            "to the Render service Environment settings."
        )
    database_url = "sqlite:///clsmc.db"

# Bazı sağlayıcılar eski postgres:// şemasını kullanabilir.
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Neon gibi yönetilen PostgreSQL servislerinde uyku/yeniden bağlantı sonrası eski
# bağlantıları otomatik doğrula. Bu ayar bağlantı bilgisini/logları açığa çıkarmaz.
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
if os.environ.get("RENDER"):
    app.config["SESSION_COOKIE_SECURE"] = True

db = SQLAlchemy(app)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("clsmc")


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    rank = db.Column(db.String(120), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )



class DeletedUser(db.Model):
    __tablename__ = "deleted_users"

    id = db.Column(db.Integer, primary_key=True)
    original_user_id = db.Column(db.Integer, nullable=True, index=True)
    username = db.Column(db.String(120), nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    rank = db.Column(db.String(120), nullable=True)
    original_created_at = db.Column(db.DateTime(timezone=True), nullable=True)
    deleted_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    deleted_by_admin = db.Column(db.String(120), nullable=False)


ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "Veyrath")
DEFAULT_ADMIN_PASSWORD_HASH = os.environ.get(
    "ADMIN_PASSWORD_HASH",
    "pbkdf2:sha256:600000$635c0576bd5c09ff4ec55048337f9610$e34636540b30e59930fa6ed88661c20e72a06cc652cf2b37969485149c50d7be",
)


class AdminAccount(db.Model):
    __tablename__ = "admin_accounts"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

class AppLog(db.Model):
    __tablename__ = "app_logs"

    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.String(20), nullable=False)
    event = db.Column(db.String(80), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )



class Report(db.Model):
    __tablename__ = "reports"

    id = db.Column(db.Integer, primary_key=True)
    report_type = db.Column(db.String(30), nullable=False, index=True)
    report_number = db.Column(db.String(80), nullable=False, index=True)
    doctor_name = db.Column(db.String(160), nullable=False, index=True)
    doctor_rank = db.Column(db.String(80), nullable=True)
    report_date = db.Column(db.String(64), nullable=True)
    bbcode = db.Column(db.Text, nullable=False)
    form_data = db.Column(db.Text, nullable=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    created_by_username = db.Column(db.String(120), nullable=False, index=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

def write_log(level: str, event: str, message: str) -> None:
    """Write sanitized logs to both platform logs and the persistent database."""
    log_line = f"{event} | {message}"
    getattr(logger, level.lower(), logger.info)(log_line)
    try:
        db.session.add(AppLog(level=level.upper(), event=event, message=message))
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("DB_LOG_WRITE_FAILED | event=%s", event)


with app.app_context():
    db.create_all()

    # Mevcut kurulumlarda users tablosuna rütbe alanını güvenli şekilde ekle.
    user_columns = {column["name"] for column in inspect(db.engine).get_columns("users")}
    if "rank" not in user_columns:
        with db.engine.begin() as connection:
            connection.execute(text("ALTER TABLE users ADD COLUMN rank VARCHAR(120)"))

    # Yeni seçmeli admin rapor düzenleyicisi için form verilerini JSON olarak sakla.
    report_columns = {column["name"] for column in inspect(db.engine).get_columns("reports")}
    if "form_data" not in report_columns:
        with db.engine.begin() as connection:
            connection.execute(text("ALTER TABLE reports ADD COLUMN form_data TEXT"))

    # Üyelik silindiğinde eski raporların korunabilmesi için rapor sahibi FK alanı
    # PostgreSQL üzerinde NULL kabul edecek şekilde gevşetilir.
    if db.engine.dialect.name == "postgresql":
        with db.engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE reports ALTER COLUMN created_by_user_id DROP NOT NULL")
            )

    # Özel yönetici hesabını yalnızca ilk kez oluşturur.
    # Sonraki başlangıçlarda mevcut admin parolası değiştirilmez.
    existing_admin = AdminAccount.query.filter_by(username=ADMIN_USERNAME).first()
    if not existing_admin:
        db.session.add(
            AdminAccount(
                username=ADMIN_USERNAME,
                password_hash=DEFAULT_ADMIN_PASSWORD_HASH,
            )
        )
        db.session.commit()


@app.get("/")
def login_page():
    if session.get("user_id"):
        return redirect(url_for("panel"))
    return render_template("login.html", prefill_username="")


@app.post("/login")
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    if not username or not password:
        flash("Kullanıcı adı ve şifre zorunludur.", "error")
        return render_template("login.html", prefill_username=username), 400

    try:
        user = User.query.filter_by(username=username).first()

        # Aktif hesap varsa normal giriş kontrolü uygulanır.
        if user and check_password_hash(user.password_hash, password):
            session.clear()
            session["user_id"] = user.id
            session["username"] = user.username
            write_log("INFO", "LOGIN_SUCCESS", f"username={username}")
            return redirect(url_for("panel"))

        # Aktif hesap bulunmuyorsa Silinen Üyelikler arşivi kontrol edilir.
        # Şifre doğru/yanlış bilgisi açıklanmaz; askıya alınmış hesap giriş yapamaz.
        if not user:
            deleted_user = (
                DeletedUser.query
                .filter_by(username=username)
                .order_by(DeletedUser.deleted_at.desc())
                .first()
            )
            if deleted_user:
                write_log(
                    "WARNING",
                    "LOGIN_SUSPENDED",
                    f"username={username}; deleted_user_id={deleted_user.id}",
                )
                flash(
                    "Hesabınız Askıya Alınmıştır, Yöneticiniz ile İletişime geçin.",
                    "error",
                )
                return render_template(
                    "login.html",
                    prefill_username=username,
                ), 403

        write_log("WARNING", "LOGIN_FAILED", f"username={username}")
        flash("Kullanıcı adı veya şifre hatalı.", "error")
        return render_template("login.html", prefill_username=username), 401

    except Exception as exc:
        db.session.rollback()
        logger.exception("LOGIN_ERROR | username=%s", username)
        try:
            write_log("ERROR", "LOGIN_ERROR", f"username={username}; type={type(exc).__name__}")
        except Exception:
            pass
        flash("Giriş sırasında bir hata oluştu.", "error")
        return render_template("login.html", prefill_username=username), 500


@app.route("/register", methods=["GET", "POST"])
def register():
    # V19.3: Kullanıcıların kendi hesabını oluşturması kapatıldı.
    # Yeni üyelikler yalnızca Admin Paneli > Yeni Üyelik Oluştur üzerinden açılır.
    flash(
        "Yeni kullanıcı hesapları yalnızca yönetici tarafından oluşturulabilir.",
        "error",
    )
    return redirect(url_for("login_page"))


@app.get("/panel")
def panel():
    if not session.get("user_id"):
        flash("Önce giriş yapmalısınız.", "error")
        return redirect(url_for("login_page"))

    user = db.session.get(User, session["user_id"])
    if not user:
        session.clear()
        flash("Kullanıcı hesabı bulunamadı. Tekrar giriş yapın.", "error")
        return redirect(url_for("login_page"))

    # Admin kullanıcı adını değiştirdiyse aktif oturuma da yansıt.
    session["username"] = user.username

    allowed_report_types = sorted(allowed_report_types_for_rank(user.rank))
    if not allowed_report_types:
        flash(
            "Hesabınıza rapor erişimi sağlayan geçerli bir rütbe atanmadı. Yöneticiniz ile iletişime geçin.",
            "error",
        )
        return redirect(url_for("settings"))

    initial_report_type = "ems" if "ems" in allowed_report_types else "vaka"
    ems_report_number = (
        next_report_number("ems", "CLSMC-EMS")
        if "ems" in allowed_report_types
        else "CLSMC-EMS-0001"
    )

    return render_template(
        "panel.html",
        username=user.username,
        user_rank=user.rank or "",
        allowed_report_types=allowed_report_types,
        initial_report_type=initial_report_type,
        ems_report_number=ems_report_number,
        is_ems_user=initial_report_type == "ems",
    )




MEDICAL_USER_RANKS = {
    "Doctor",
    "Attending Physician",
    "Psychiatrist",
}

EMS_USER_RANKS = {
    "Paramedic",
    "Senior Paramedic",
    "EMT",
    # Eski hesaplarla geriye dönük uyumluluk için korunur.
    "Emergency Medical Technician (EMT)",
}

ALLOWED_USER_RANKS = MEDICAL_USER_RANKS | EMS_USER_RANKS

MEDICAL_REPORT_TYPES = {"vaka", "adli", "otopsi", "ex"}
EMS_REPORT_TYPES = {"ems"}


def allowed_report_types_for_rank(rank: str | None) -> set[str]:
    normalized_rank = (rank or "").strip()
    if normalized_rank in EMS_USER_RANKS:
        return set(EMS_REPORT_TYPES)
    if normalized_rank in MEDICAL_USER_RANKS:
        return set(MEDICAL_REPORT_TYPES)
    return set()


def next_report_number(report_type: str, prefix: str) -> str:
    """Return the next display number without changing the database."""
    highest = 0
    rows = (
        db.session.query(Report.report_number)
        .filter(Report.report_type == report_type)
        .all()
    )
    expected_prefix = f"{prefix}-"
    for (number,) in rows:
        value = (number or "").strip()
        if not value.startswith(expected_prefix):
            continue
        suffix = value.rsplit("-", 1)[-1]
        if suffix.isdigit():
            highest = max(highest, int(suffix))
    return f"{prefix}-{highest + 1:04d}"


REPORT_TYPE_LABELS = {
    "vaka": "Vaka Raporu",
    "adli": "Adli Vaka Raporu",
    "otopsi": "Otopsi Raporu",
    "ex": "Ölüm (Ex) Raporu",
    "ems": "EMS Saha Raporu",
}


@app.post("/api/reports")
def save_report():
    if not session.get("user_id"):
        return {"ok": False, "message": "Oturum süresi dolmuş. Tekrar giriş yapın."}, 401

    data = request.get_json(silent=True) or {}
    report_type = str(data.get("report_type", "")).strip()
    report_number = str(data.get("report_number", "")).strip()
    report_date = str(data.get("report_date", "")).strip()
    bbcode = str(data.get("bbcode", "")).strip()
    form_data_raw = data.get("form_data", {})
    if not isinstance(form_data_raw, dict):
        form_data_raw = {}
    form_data_json = json.dumps(form_data_raw, ensure_ascii=False)

    current_user = db.session.get(User, session["user_id"])
    if not current_user:
        session.clear()
        return {"ok": False, "message": "Kullanıcı hesabı bulunamadı. Tekrar giriş yapın."}, 401

    # Doktor adı ve rütbesi tarayıcıdan alınmaz. Böylece kullanıcı kendi rütbesini
    # veya başka bir doktor adını değiştirerek rapor kaydedemez.
    doctor_name = current_user.username.strip()
    doctor_rank = (current_user.rank or "").strip()

    if report_type not in REPORT_TYPE_LABELS:
        return {"ok": False, "message": "Geçersiz rapor türü."}, 400

    allowed_report_types = allowed_report_types_for_rank(doctor_rank)
    if report_type not in allowed_report_types:
        write_log(
            "WARNING",
            "REPORT_ACCESS_DENIED",
            f"username={doctor_name}; rank={doctor_rank}; report_type={report_type}",
        )
        return {
            "ok": False,
            "message": "Rütbeniz bu rapor türünü oluşturma yetkisine sahip değil.",
        }, 403

    if not report_number:
        return {"ok": False, "message": "Rapor numarası zorunludur."}, 400
    if not doctor_name:
        return {"ok": False, "message": "Sorumlu hekim adı zorunludur."}, 400
    if not doctor_rank:
        return {
            "ok": False,
            "message": "Hesabınıza henüz rütbe atanmadı. Yönetici rütbe atadıktan sonra rapor kaydedebilirsiniz.",
        }, 400
    if not bbcode:
        return {"ok": False, "message": "BBCode oluşturulamadı."}, 400

    try:
        # Aynı rapor tekrar kopyalanırsa istatistiği şişirmesin; mevcut kaydı güncelle.
        report = Report.query.filter_by(
            report_type=report_type,
            report_number=report_number,
        ).first()

        is_new = report is None

        if is_new:
            report = Report(
                report_type=report_type,
                report_number=report_number,
                doctor_name=doctor_name,
                doctor_rank=doctor_rank or None,
                report_date=report_date or None,
                bbcode=bbcode,
                form_data=form_data_json,
                created_by_user_id=session["user_id"],
                created_by_username=session.get("username", ""),
            )
            db.session.add(report)
        else:
            # Mevcut bir rapor tekrar kaydedildiğinde rapor içeriği ve güncel
            # raporlayan hekim bilgisi yenilenir; ancak "Kaydeden Hesap" ilk
            # oluşturan kullanıcı olarak korunur. Böylece kullanıcı istatistikleri
            # ve rapor sahipliği başka bir hesabın aynı rapor numarasını kullanmasıyla
            # yanlışlıkla el değiştirmez.
            report.doctor_name = doctor_name
            report.doctor_rank = doctor_rank or None
            report.report_date = report_date or None
            report.bbcode = bbcode
            report.form_data = form_data_json

        db.session.commit()

        write_log(
            "INFO",
            "REPORT_SAVED" if is_new else "REPORT_UPDATED",
            f"type={report_type}; report_number={report_number}; doctor={doctor_name}; user={session.get('username', '')}",
        )

        return {
            "ok": True,
            "message": "Rapor kaydedildi." if is_new else "Rapor kaydı güncellendi.",
            "created": is_new,
            "next_report_number": (
                next_report_number("ems", "CLSMC-EMS")
                if report_type == "ems"
                else None
            ),
        }, 201 if is_new else 200

    except Exception as exc:
        db.session.rollback()
        logger.exception("REPORT_SAVE_ERROR | type=%s | number=%s", report_type, report_number)
        try:
            write_log(
                "ERROR",
                "REPORT_SAVE_ERROR",
                f"type={report_type}; report_number={report_number}; error={type(exc).__name__}",
            )
        except Exception:
            pass
        return {"ok": False, "message": "Rapor istatistiğe kaydedilemedi."}, 500


@app.get("/statistics")
def statistics():
    if not session.get("user_id"):
        flash("Önce giriş yapmalısınız.", "error")
        return redirect(url_for("login_page"))

    user = db.session.get(User, session["user_id"])
    if not user:
        session.clear()
        flash("Kullanıcı hesabı aktif değil. Tekrar giriş yapın.", "error")
        return redirect(url_for("login_page"))

    # Admin kullanıcı adını değiştirdiyse açık oturumdaki isim de güncel kalsın.
    session["username"] = user.username

    allowed_report_types = sorted(allowed_report_types_for_rank(user.rank))
    if not allowed_report_types:
        flash("Hesabınıza geçerli bir rapor rütbesi atanmadı.", "error")
        return redirect(url_for("settings"))

    type_rows = (
        db.session.query(Report.report_type, db.func.count(Report.id))
        .filter(Report.report_type.in_(allowed_report_types))
        .group_by(Report.report_type)
        .order_by(db.func.count(Report.id).desc())
        .all()
    )

    doctor_rows = (
        db.session.query(Report.doctor_name, db.func.count(Report.id))
        .filter(Report.report_type.in_(allowed_report_types))
        .group_by(Report.doctor_name)
        .order_by(db.func.count(Report.id).desc(), Report.doctor_name.asc())
        .all()
    )

    type_counts = [
        {
            "label": REPORT_TYPE_LABELS.get(report_type, report_type),
            "count": count,
        }
        for report_type, count in type_rows
    ]
    doctor_counts = [
        {"doctor": doctor, "count": count}
        for doctor, count in doctor_rows
    ]

    max_type_count = max([x["count"] for x in type_counts], default=1)
    max_doctor_count = max([x["count"] for x in doctor_counts], default=1)

    recent_reports = (
        Report.query
        .filter(Report.report_type.in_(allowed_report_types))
        .order_by(Report.updated_at.desc())
        .limit(20)
        .all()
    )
    total_reports = (
        Report.query
        .filter(Report.report_type.in_(allowed_report_types))
        .count()
    )

    return render_template(
        "statistics.html",
        username=user.username,
        user_rank=user.rank or "",
        total_reports=total_reports,
        doctor_counts=doctor_counts,
        type_counts=type_counts,
        max_type_count=max_type_count,
        max_doctor_count=max_doctor_count,
        recent_reports=recent_reports,
        report_type_labels=REPORT_TYPE_LABELS,
    )


@app.route("/settings", methods=["GET", "POST"])
def settings():
    if not session.get("user_id"):
        flash("Önce giriş yapmalısınız.", "error")
        return redirect(url_for("login_page"))

    user = db.session.get(User, session["user_id"])
    if not user:
        session.clear()
        flash("Kullanıcı hesabı aktif değil. Tekrar giriş yapın.", "error")
        return redirect(url_for("login_page"))

    session["username"] = user.username

    if request.method == "GET":
        return render_template(
            "settings.html",
            username=user.username,
        )

    old_password = request.form.get("old_password", "")
    new_password = request.form.get("new_password", "")
    new_password_repeat = request.form.get("new_password_repeat", "")

    if not old_password or not new_password or not new_password_repeat:
        flash("Tüm şifre alanlarını doldurun.", "error")
        write_log(
            "WARNING",
            "PASSWORD_CHANGE_FAILED",
            f"username={session.get('username', '')}; reason=missing_fields",
        )
        return render_template(
            "settings.html",
            username=session.get("username", ""),
        ), 400

    if len(new_password) < 6:
        flash("Yeni şifre en az 6 karakter olmalıdır.", "error")
        write_log(
            "WARNING",
            "PASSWORD_CHANGE_FAILED",
            f"username={session.get('username', '')}; reason=short_password",
        )
        return render_template(
            "settings.html",
            username=session.get("username", ""),
        ), 400

    if new_password != new_password_repeat:
        flash("Yeni şifre ve yeni şifre tekrarı eşleşmiyor.", "error")
        write_log(
            "WARNING",
            "PASSWORD_CHANGE_FAILED",
            f"username={session.get('username', '')}; reason=password_mismatch",
        )
        return render_template(
            "settings.html",
            username=session.get("username", ""),
        ), 400

    try:
        if not check_password_hash(user.password_hash, old_password):
            flash("Eski şifre hatalı.", "error")
            write_log(
                "WARNING",
                "PASSWORD_CHANGE_FAILED",
                f"username={user.username}; reason=wrong_old_password",
            )
            return render_template(
                "settings.html",
                username=user.username,
            ), 400

        if check_password_hash(user.password_hash, new_password):
            flash("Yeni şifre eski şifre ile aynı olamaz.", "error")
            write_log(
                "WARNING",
                "PASSWORD_CHANGE_FAILED",
                f"username={user.username}; reason=same_as_old_password",
            )
            return render_template(
                "settings.html",
                username=user.username,
            ), 400

        user.password_hash = generate_password_hash(new_password)
        db.session.commit()

        write_log(
            "INFO",
            "PASSWORD_CHANGED",
            f"username={user.username}",
        )

        flash("Şifreniz başarıyla güncellendi.", "success")
        return redirect(url_for("settings"))

    except Exception as exc:
        db.session.rollback()
        logger.exception("PASSWORD_CHANGE_ERROR | username=%s", session.get("username", ""))
        try:
            write_log(
                "ERROR",
                "PASSWORD_CHANGE_ERROR",
                f"username={session.get('username', '')}; error={type(exc).__name__}",
            )
        except Exception:
            pass

        flash("Şifre güncellenirken bir hata oluştu.", "error")
        return render_template(
            "settings.html",
            username=session.get("username", ""),
        ), 500


@app.post("/logout")
def logout():
    username = session.get("username", "")
    session.clear()
    try:
        write_log("INFO", "LOGOUT", f"username={username}")
    except Exception:
        pass
    return redirect(url_for("login_page"))


def admin_required():
    return bool(session.get("admin_id") and session.get("admin_username"))


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if admin_required():
        return redirect(url_for("admin_dashboard"))

    if request.method == "GET":
        return render_template("admin_login.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    if not username or not password:
        flash("Yönetici kullanıcı adı ve şifre zorunludur.", "error")
        return render_template("admin_login.html", username=username), 400

    try:
        admin = AdminAccount.query.filter_by(username=username).first()

        if admin and check_password_hash(admin.password_hash, password):
            session.clear()
            session["admin_id"] = admin.id
            session["admin_username"] = admin.username
            write_log("INFO", "ADMIN_LOGIN_SUCCESS", f"admin={admin.username}")
            return redirect(url_for("admin_dashboard"))

        write_log("WARNING", "ADMIN_LOGIN_FAILED", f"username={username}")
        flash("Yönetici kullanıcı adı veya şifre hatalı.", "error")
        return render_template("admin_login.html", username=username), 401

    except Exception as exc:
        db.session.rollback()
        logger.exception("ADMIN_LOGIN_ERROR | username=%s", username)
        try:
            write_log(
                "ERROR",
                "ADMIN_LOGIN_ERROR",
                f"username={username}; error={type(exc).__name__}",
            )
        except Exception:
            pass
        flash("Admin girişi sırasında bir hata oluştu.", "error")
        return render_template("admin_login.html", username=username), 500


@app.get("/admin")
def admin_dashboard():
    if not admin_required():
        flash("Bu bölüm yalnızca yönetici erişimine açıktır.", "error")
        return redirect(url_for("admin_login"))

    users = User.query.order_by(User.created_at.desc()).all()
    deleted_users = DeletedUser.query.order_by(DeletedUser.deleted_at.desc()).all()
    reports = Report.query.order_by(Report.updated_at.desc()).all()

    doctor_map = {}
    for report in reports:
        doctor_name = (report.doctor_name or "").strip()
        if not doctor_name:
            continue

        if doctor_name not in doctor_map:
            doctor_map[doctor_name] = {
                "name": doctor_name,
                "rank": report.doctor_rank or "—",
                "count": 0,
                "vaka_count": 0,
                "adli_count": 0,
                "otopsi_count": 0,
                "ex_count": 0,
                "ems_count": 0,
                "last_report": report.report_number,
                "last_updated": report.updated_at,
            }

        doctor_map[doctor_name]["count"] += 1

        if report.report_type == "vaka":
            doctor_map[doctor_name]["vaka_count"] += 1
        elif report.report_type == "adli":
            doctor_map[doctor_name]["adli_count"] += 1
        elif report.report_type == "otopsi":
            doctor_map[doctor_name]["otopsi_count"] += 1
        elif report.report_type == "ex":
            doctor_map[doctor_name]["ex_count"] += 1
        elif report.report_type == "ems":
            doctor_map[doctor_name]["ems_count"] += 1

    doctors = sorted(
        doctor_map.values(),
        key=lambda item: (-item["count"], item["name"].lower()),
    )

    type_counts = {}
    for report in reports:
        label = REPORT_TYPE_LABELS.get(report.report_type, report.report_type)
        type_counts[label] = type_counts.get(label, 0) + 1

    recent_logs = (
        AppLog.query
        .order_by(AppLog.created_at.desc())
        .limit(30)
        .all()
    )

    return render_template(
        "admin_dashboard.html",
        admin_username=session.get("admin_username", ""),
        users=users,
        deleted_users=deleted_users,
        doctors=doctors,
        reports=reports,
        recent_logs=recent_logs,
        type_counts=type_counts,
        report_type_labels=REPORT_TYPE_LABELS,
    )



@app.get("/admin/statistics")
def admin_statistics():
    # Eski V18 bağlantıları bozulmasın; yeni kullanıcı istatistiklerine yönlendir.
    selected_user = request.args.get("doctor", "").strip() or request.args.get("user", "").strip()
    if selected_user:
        return redirect(url_for("admin_user_statistics", user=selected_user))
    return redirect(url_for("admin_user_statistics"))


@app.get("/admin/user-statistics")
def admin_user_statistics():
    if not admin_required():
        flash("Bu bölüm yalnızca yönetici erişimine açıktır.", "error")
        return redirect(url_for("admin_login"))

    users = User.query.order_by(User.username.asc()).all()
    deleted_users = DeletedUser.query.order_by(DeletedUser.username.asc()).all()
    all_reports = Report.query.order_by(Report.updated_at.desc()).all()

    # Aktif kullanıcılar öncelikli. Silinmiş üyelikler de geçmiş raporlarıyla
    # görüntülenebilsin diye isim listesinde ayrıca korunur.
    user_map = {}
    for user in users:
        user_map[user.username] = {
            "name": user.username,
            "rank": user.rank or "—",
            "status": "Aktif",
        }

    for deleted in deleted_users:
        if deleted.username not in user_map:
            user_map[deleted.username] = {
                "name": deleted.username,
                "rank": deleted.rank or "—",
                "status": "Askıda / Silinen Üyelik",
            }

    # Hesabı artık mevcut olmasa bile geçmişte rapor yazan kişiler kaybolmasın.
    for report in all_reports:
        report_user = (report.created_by_username or "").strip()
        if report_user and report_user not in user_map:
            user_map[report_user] = {
                "name": report_user,
                # Kaydeden hesap ile raporlayan hekim farklı olabilir. Hesabın
                # gerçek rütbesi artık bulunamıyorsa doktor rütbesini kullanıcı
                # rütbesi gibi göstermeyelim.
                "rank": "—",
                "status": "Geçmiş Kayıt",
            }

    user_list = sorted(user_map.values(), key=lambda item: item["name"].lower())

    selected_name = request.args.get("user", "").strip()
    selected_user = user_map.get(selected_name) if selected_name else None

    grouped_reports = {
        "vaka": [],
        "adli": [],
        "otopsi": [],
        "ex": [],
        "ems": [],
    }

    stats = {
        "total": 0,
        "vaka": 0,
        "adli": 0,
        "otopsi": 0,
        "ex": 0,
        "ems": 0,
    }

    if selected_name and not selected_user:
        flash("Seçilen kullanıcı bulunamadı.", "error")
        selected_name = ""

    if selected_user:
        # Burada 'kullanıcının yazdığı rapor' kaydeden hesap üzerinden belirlenir.
        # Böylece raporlayan hekim daha sonra admin tarafından değiştirilse bile
        # raporu sisteme ilk kaydeden kullanıcı bilgisi korunur.
        for report in all_reports:
            if (report.created_by_username or "").strip() != selected_name:
                continue

            stats["total"] += 1
            if report.report_type in grouped_reports:
                grouped_reports[report.report_type].append(report)
                stats[report.report_type] += 1

    return render_template(
        "admin_user_statistics.html",
        admin_username=session.get("admin_username", ""),
        user_list=user_list,
        selected_name=selected_name,
        selected_user=selected_user,
        stats=stats,
        grouped_reports=grouped_reports,
        report_type_labels=REPORT_TYPE_LABELS,
    )


@app.get("/admin/reports/<int:report_id>/view")
def admin_view_report(report_id: int):
    if not admin_required():
        flash("Bu bölüm yalnızca yönetici erişimine açıktır.", "error")
        return redirect(url_for("admin_login"))

    report = db.session.get(Report, report_id)
    if not report:
        flash("Rapor kaydı bulunamadı.", "error")
        return redirect(url_for("admin_user_statistics"))

    try:
        form_data = json.loads(report.form_data or "{}")
        if not isinstance(form_data, dict):
            form_data = {}
    except (TypeError, ValueError, json.JSONDecodeError):
        form_data = {}

    return render_template(
        "admin_report_view.html",
        admin_username=session.get("admin_username", ""),
        report=report,
        form_data=form_data,
        report_type_labels=REPORT_TYPE_LABELS,
    )


@app.post("/admin/reports/<int:report_id>/delete")
def admin_delete_report(report_id: int):
    if not admin_required():
        flash("Bu bölüm yalnızca yönetici erişimine açıktır.", "error")
        return redirect(url_for("admin_login"))

    report = db.session.get(Report, report_id)
    if not report:
        flash("Rapor kaydı bulunamadı.", "error")
        return redirect(url_for("admin_user_statistics"))

    return_user = (report.created_by_username or "").strip()
    report_number = report.report_number
    report_type = report.report_type

    try:
        db.session.delete(report)
        db.session.commit()

        write_log(
            "WARNING",
            "ADMIN_REPORT_DELETED",
            (
                f"admin={session.get('admin_username', '')}; "
                f"report_id={report_id}; report_number={report_number}; "
                f"report_type={report_type}; created_by={return_user}"
            ),
        )

        flash(f"{report_number} numaralı rapor silindi.", "success")
        if return_user:
            return redirect(url_for("admin_user_statistics", user=return_user))
        return redirect(url_for("admin_user_statistics"))

    except Exception as exc:
        db.session.rollback()
        logger.exception("ADMIN_REPORT_DELETE_ERROR | report_id=%s", report_id)
        try:
            write_log(
                "ERROR",
                "ADMIN_REPORT_DELETE_ERROR",
                (
                    f"admin={session.get('admin_username', '')}; "
                    f"report_id={report_id}; error={type(exc).__name__}"
                ),
            )
        except Exception:
            pass

        flash("Rapor silinirken bir hata oluştu.", "error")
        if return_user:
            return redirect(url_for("admin_user_statistics", user=return_user))
        return redirect(url_for("admin_user_statistics"))


@app.route("/admin/users/new", methods=["GET", "POST"])
def admin_create_user():
    if not admin_required():
        flash("Bu bölüm yalnızca yönetici erişimine açıktır.", "error")
        return redirect(url_for("admin_login"))

    if request.method == "GET":
        return render_template(
            "admin_user_create.html",
            admin_username=session.get("admin_username", ""),
        )

    username = request.form.get("username", "").strip()
    rank = request.form.get("rank", "").strip()
    password = request.form.get("password", "")
    password_repeat = request.form.get("password_repeat", "")

    if not username:
        flash("Kullanıcı adı boş bırakılamaz.", "error")
        return render_template(
            "admin_user_create.html",
            admin_username=session.get("admin_username", ""),
        ), 400

    if rank not in ALLOWED_USER_RANKS:
        flash("Geçerli bir rütbe seçin.", "error")
        return render_template(
            "admin_user_create.html",
            admin_username=session.get("admin_username", ""),
        ), 400

    if len(password) < 6:
        flash("Şifre en az 6 karakter olmalıdır.", "error")
        return render_template(
            "admin_user_create.html",
            admin_username=session.get("admin_username", ""),
        ), 400

    if password != password_repeat:
        flash("Şifre ve şifre tekrarı eşleşmiyor.", "error")
        return render_template(
            "admin_user_create.html",
            admin_username=session.get("admin_username", ""),
        ), 400

    try:
        if User.query.filter_by(username=username).first():
            flash("Bu kullanıcı adı zaten kullanılıyor.", "error")
            return render_template(
                "admin_user_create.html",
                admin_username=session.get("admin_username", ""),
            ), 409

        if DeletedUser.query.filter_by(username=username).first():
            flash(
                "Bu kullanıcı adı Silinen Üyelikler arşivinde bulunuyor. "
                "Yeni hesap açmak yerine arşivdeki üyeliği geri getirin.",
                "error",
            )
            return render_template(
                "admin_user_create.html",
                admin_username=session.get("admin_username", ""),
            ), 409

        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            rank=rank,
        )
        db.session.add(user)
        db.session.commit()

        write_log(
            "INFO",
            "ADMIN_USER_CREATED",
            (
                f"admin={session.get('admin_username', '')}; "
                f"user_id={user.id}; username={user.username}; rank={user.rank}"
            ),
        )

        flash(f"{user.username} üyeliği başarıyla oluşturuldu.", "success")
        return redirect(url_for("admin_dashboard"))

    except Exception as exc:
        db.session.rollback()
        logger.exception("ADMIN_USER_CREATE_ERROR | username=%s", username)
        try:
            write_log(
                "ERROR",
                "ADMIN_USER_CREATE_ERROR",
                (
                    f"admin={session.get('admin_username', '')}; "
                    f"username={username}; error={type(exc).__name__}"
                ),
            )
        except Exception:
            pass

        flash("Yeni üyelik oluşturulurken bir hata oluştu.", "error")
        return render_template(
            "admin_user_create.html",
            admin_username=session.get("admin_username", ""),
        ), 500


@app.route("/admin/users/<int:user_id>", methods=["GET", "POST"])
def admin_edit_user(user_id: int):
    if not admin_required():
        flash("Bu bölüm yalnızca yönetici erişimine açıktır.", "error")
        return redirect(url_for("admin_login"))

    user = db.session.get(User, user_id)
    if not user:
        flash("Kullanıcı hesabı bulunamadı.", "error")
        return redirect(url_for("admin_dashboard"))

    if request.method == "GET":
        return render_template(
            "admin_user_edit.html",
            admin_username=session.get("admin_username", ""),
            user=user,
        )

    new_username = request.form.get("username", "").strip()
    new_rank = request.form.get("rank", "").strip()
    new_password = request.form.get("new_password", "")
    new_password_repeat = request.form.get("new_password_repeat", "")

    if not new_username:
        flash("Kullanıcı adı boş bırakılamaz.", "error")
        return render_template(
            "admin_user_edit.html",
            admin_username=session.get("admin_username", ""),
            user=user,
        ), 400

    if new_rank not in ALLOWED_USER_RANKS:
        flash("Geçerli bir rütbe seçin.", "error")
        return render_template(
            "admin_user_edit.html",
            admin_username=session.get("admin_username", ""),
            user=user,
        ), 400

    if new_password or new_password_repeat:
        if not new_password or not new_password_repeat:
            flash("Yeni şifreyi değiştirecekseniz iki şifre alanını da doldurun.", "error")
            return render_template(
                "admin_user_edit.html",
                admin_username=session.get("admin_username", ""),
                user=user,
            ), 400

        if len(new_password) < 6:
            flash("Yeni şifre en az 6 karakter olmalıdır.", "error")
            return render_template(
                "admin_user_edit.html",
                admin_username=session.get("admin_username", ""),
                user=user,
            ), 400

        if new_password != new_password_repeat:
            flash("Yeni şifre ve yeni şifre tekrarı eşleşmiyor.", "error")
            return render_template(
                "admin_user_edit.html",
                admin_username=session.get("admin_username", ""),
                user=user,
            ), 400

    try:
        duplicate = (
            User.query
            .filter(User.username == new_username, User.id != user.id)
            .first()
        )
        if duplicate:
            flash("Bu kullanıcı adı başka bir hesap tarafından kullanılıyor.", "error")
            return render_template(
                "admin_user_edit.html",
                admin_username=session.get("admin_username", ""),
                user=user,
            ), 409

        archived_collision = (
            DeletedUser.query.filter_by(username=new_username).first()
            if new_username != user.username
            else None
        )
        if archived_collision:
            flash(
                "Bu kullanıcı adı Silinen Üyelikler arşivindeki başka bir hesaba ait. "
                "Önce arşiv kaydını geri getirin veya farklı bir kullanıcı adı seçin.",
                "error",
            )
            return render_template(
                "admin_user_edit.html",
                admin_username=session.get("admin_username", ""),
                user=user,
            ), 409

        old_username = user.username
        old_rank = user.rank or ""
        password_changed = bool(new_password)

        user.username = new_username
        user.rank = new_rank

        if password_changed:
            user.password_hash = generate_password_hash(new_password)

        # Kullanıcı adı değişirse geçmiş raporlardaki "Kaydeden Kullanıcı" etiketi de
        # yeni hesap adıyla eşitlenir; rapor içeriği ve doktor kaydı korunur.
        if old_username != new_username:
            Report.query.filter_by(created_by_user_id=user.id).update(
                {"created_by_username": new_username},
                synchronize_session=False,
            )

        db.session.commit()

        write_log(
            "INFO",
            "ADMIN_USER_UPDATED",
            (
                f"admin={session.get('admin_username', '')}; "
                f"user_id={user.id}; old_username={old_username}; "
                f"new_username={new_username}; "
                f"rank_changed={'yes' if old_rank != new_rank else 'no'}; "
                f"password_reset={'yes' if password_changed else 'no'}"
            ),
        )

        flash(
            "Kullanıcı hesabı, rütbesi ve şifresi güncellendi."
            if password_changed
            else "Kullanıcı hesabı ve rütbesi güncellendi. Şifre değiştirilmedi.",
            "success",
        )
        return redirect(url_for("admin_edit_user", user_id=user.id))

    except Exception as exc:
        db.session.rollback()
        logger.exception("ADMIN_USER_UPDATE_ERROR | user_id=%s", user.id)
        try:
            write_log(
                "ERROR",
                "ADMIN_USER_UPDATE_ERROR",
                (
                    f"admin={session.get('admin_username', '')}; "
                    f"user_id={user.id}; error={type(exc).__name__}"
                ),
            )
        except Exception:
            pass

        flash("Kullanıcı hesabı güncellenirken bir hata oluştu.", "error")
        return render_template(
            "admin_user_edit.html",
            admin_username=session.get("admin_username", ""),
            user=user,
        ), 500


@app.post("/admin/users/<int:user_id>/delete")
def admin_delete_user(user_id: int):
    if not admin_required():
        flash("Bu bölüm yalnızca yönetici erişimine açıktır.", "error")
        return redirect(url_for("admin_login"))

    user = db.session.get(User, user_id)
    if not user:
        flash("Kullanıcı hesabı bulunamadı.", "error")
        return redirect(url_for("admin_dashboard"))

    try:
        username = user.username

        # Hesabı geri getirilebilir şekilde silinen üyelikler arşivine taşı.
        deleted_user = DeletedUser(
            original_user_id=user.id,
            username=user.username,
            password_hash=user.password_hash,
            rank=user.rank,
            original_created_at=user.created_at,
            deleted_by_admin=session.get("admin_username", ""),
        )
        db.session.add(deleted_user)

        # Geçmiş raporlar kesinlikle silinmez. Sadece aktif üyeliğe olan FK bağı
        # kaldırılır; kullanıcı adı, doktor bilgisi, rütbe ve BBCode geçmişi kalır.
        Report.query.filter_by(created_by_user_id=user.id).update(
            {"created_by_user_id": None},
            synchronize_session=False,
        )

        db.session.delete(user)
        db.session.commit()

        write_log(
            "INFO",
            "ADMIN_USER_DELETED",
            (
                f"admin={session.get('admin_username', '')}; "
                f"user_id={user_id}; username={username}; "
                f"reports_preserved=yes; archived=yes"
            ),
        )

        flash(
            f"{username} üyeliği Silinen Üyelikler arşivine taşındı. Geçmiş raporları korundu.",
            "success",
        )
        return redirect(url_for("admin_dashboard"))

    except Exception as exc:
        db.session.rollback()
        logger.exception("ADMIN_USER_DELETE_ERROR | user_id=%s", user_id)
        try:
            write_log(
                "ERROR",
                "ADMIN_USER_DELETE_ERROR",
                (
                    f"admin={session.get('admin_username', '')}; "
                    f"user_id={user_id}; error={type(exc).__name__}"
                ),
            )
        except Exception:
            pass

        flash("Üyelik silinirken bir hata oluştu.", "error")
        return redirect(url_for("admin_dashboard"))

@app.post("/admin/deleted-users/<int:deleted_user_id>/restore")
def admin_restore_user(deleted_user_id: int):
    if not admin_required():
        flash("Bu bölüm yalnızca yönetici erişimine açıktır.", "error")
        return redirect(url_for("admin_login"))

    deleted_user = db.session.get(DeletedUser, deleted_user_id)
    if not deleted_user:
        flash("Silinen üyelik kaydı bulunamadı.", "error")
        return redirect(url_for("admin_dashboard"))

    try:
        if User.query.filter_by(username=deleted_user.username).first():
            flash(
                f"{deleted_user.username} kullanıcı adı şu anda aktif bir hesap tarafından kullanılıyor. "
                "Geri getirmeden önce aktif hesabın kullanıcı adını değiştirin veya hesabı kaldırın.",
                "error",
            )
            return redirect(url_for("admin_dashboard"))

        restored_user = User(
            username=deleted_user.username,
            password_hash=deleted_user.password_hash,
            rank=deleted_user.rank,
        )

        # Mümkünse eski üyelik oluşturma zamanını koru.
        if deleted_user.original_created_at:
            restored_user.created_at = deleted_user.original_created_at

        db.session.add(restored_user)
        db.session.flush()

        # Silinmiş üyeliğin geçmiş raporlarını yeni aktif kullanıcı kaydına tekrar bağla.
        Report.query.filter(
            Report.created_by_user_id.is_(None),
            Report.created_by_username == deleted_user.username,
        ).update(
            {"created_by_user_id": restored_user.id},
            synchronize_session=False,
        )

        restored_username = deleted_user.username
        restored_rank = deleted_user.rank or ""
        db.session.delete(deleted_user)
        db.session.commit()

        write_log(
            "INFO",
            "ADMIN_USER_RESTORED",
            (
                f"admin={session.get('admin_username', '')}; "
                f"user_id={restored_user.id}; username={restored_username}; "
                f"rank={restored_rank}; reports_relinked=yes"
            ),
        )

        flash(
            f"{restored_username} üyeliği başarıyla geri getirildi. Eski şifresi ve rütbesi korunmuştur.",
            "success",
        )
        return redirect(url_for("admin_dashboard"))

    except Exception as exc:
        db.session.rollback()
        logger.exception(
            "ADMIN_USER_RESTORE_ERROR | deleted_user_id=%s",
            deleted_user_id,
        )
        try:
            write_log(
                "ERROR",
                "ADMIN_USER_RESTORE_ERROR",
                (
                    f"admin={session.get('admin_username', '')}; "
                    f"deleted_user_id={deleted_user_id}; error={type(exc).__name__}"
                ),
            )
        except Exception:
            pass

        flash("Üyelik geri getirilirken bir hata oluştu.", "error")
        return redirect(url_for("admin_dashboard"))


@app.route("/admin/reports/<int:report_id>", methods=["GET", "POST"])
def admin_edit_report(report_id: int):
    if not admin_required():
        flash("Bu bölüm yalnızca yönetici erişimine açıktır.", "error")
        return redirect(url_for("admin_login"))

    report = db.session.get(Report, report_id)
    if not report:
        flash("Rapor kaydı bulunamadı.", "error")
        return redirect(url_for("admin_dashboard"))

    users = User.query.order_by(User.username.asc()).all()

    def get_form_data():
        try:
            parsed = json.loads(report.form_data or "{}")
            if isinstance(parsed, dict) and parsed:
                return parsed, False
        except (TypeError, ValueError, json.JSONDecodeError):
            pass

        # Eski raporların structured form verisi yoktur. En azından temel
        # metadata alanları otomatik doldurulur; eski BBCode referans olarak korunur.
        fallback = {}
        number_fields = {
            "vaka": "rapor_no",
            "adli": "adli_rapor_no",
            "otopsi": "otp_rapor_no",
            "ex": "ex_rapor_no",
            "ems": "ems_rapor_no",
        }
        date_fields = {
            "vaka": "rapor_tarihi",
            "adli": "adli_tarih",
            "otopsi": "otp_otopsi_tarih",
            "ex": "ex_olum_tarih",
            "ems": "ems_vaka_tarih",
        }
        if report.report_type in number_fields:
            fallback[number_fields[report.report_type]] = report.report_number or ""
        if report.report_type in date_fields:
            fallback[date_fields[report.report_type]] = report.report_date or ""
        return fallback, True

    if request.method == "GET":
        report_form_data, report_is_legacy = get_form_data()
        return render_template(
            "admin_report_edit.html",
            admin_username=session.get("admin_username", ""),
            report=report,
            users=users,
            report_type_labels=REPORT_TYPE_LABELS,
            report_form_data=report_form_data,
            report_is_legacy=report_is_legacy,
            preview_mode=False,
        )

    report_type = request.form.get("report_type", "").strip()
    report_number = request.form.get("report_number", "").strip()
    doctor_name = request.form.get("doctor_name", "").strip()
    doctor_rank = request.form.get("doctor_rank", "").strip()
    report_date = request.form.get("report_date", "").strip()
    bbcode = request.form.get("bbcode", "").strip()
    form_data_text = request.form.get("form_data", "").strip()

    try:
        form_data_obj = json.loads(form_data_text or "{}")
        if not isinstance(form_data_obj, dict):
            raise ValueError("form_data must be an object")
    except (TypeError, ValueError, json.JSONDecodeError):
        report_form_data, report_is_legacy = get_form_data()
        flash("Rapor form verileri okunamadı.", "error")
        return render_template(
            "admin_report_edit.html",
            admin_username=session.get("admin_username", ""),
            report=report,
            users=users,
            report_type_labels=REPORT_TYPE_LABELS,
            report_form_data=report_form_data,
            report_is_legacy=report_is_legacy,
            preview_mode=False,
        ), 400

    if report_type not in REPORT_TYPE_LABELS:
        flash("Geçersiz rapor türü.", "error")
        return redirect(url_for("admin_edit_report", report_id=report.id))

    if doctor_rank not in ALLOWED_USER_RANKS:
        flash("Geçerli bir doktor rütbesi seçilmelidir.", "error")
        return redirect(url_for("admin_edit_report", report_id=report.id))

    if not report_number or not doctor_name or not bbcode:
        flash("Rapor numarası, doktor ve BBCode boş bırakılamaz.", "error")
        return redirect(url_for("admin_edit_report", report_id=report.id))

    try:
        old_number = report.report_number

        report.report_type = report_type
        report.report_number = report_number
        report.doctor_name = doctor_name
        report.doctor_rank = doctor_rank
        report.report_date = report_date or None
        report.bbcode = bbcode
        report.form_data = json.dumps(form_data_obj, ensure_ascii=False)

        db.session.commit()

        write_log(
            "INFO",
            "ADMIN_REPORT_UPDATED",
            (
                f"admin={session.get('admin_username', '')}; "
                f"report_id={report.id}; old_number={old_number}; "
                f"new_number={report.report_number}; doctor={report.doctor_name}; "
                f"structured_editor=yes"
            ),
        )

        flash("Rapor seçmeli form üzerinden başarıyla güncellendi.", "success")
        return redirect(url_for("admin_edit_report", report_id=report.id))

    except Exception as exc:
        db.session.rollback()
        logger.exception("ADMIN_REPORT_UPDATE_ERROR | report_id=%s", report.id)
        try:
            write_log(
                "ERROR",
                "ADMIN_REPORT_UPDATE_ERROR",
                f"admin={session.get('admin_username', '')}; report_id={report.id}; error={type(exc).__name__}",
            )
        except Exception:
            pass

        flash("Rapor güncellenirken bir hata oluştu.", "error")
        return redirect(url_for("admin_edit_report", report_id=report.id))

@app.post("/admin/logout")
def admin_logout():
    admin_username = session.get("admin_username", "")
    session.clear()
    try:
        write_log("INFO", "ADMIN_LOGOUT", f"admin={admin_username}")
    except Exception:
        pass
    return redirect(url_for("admin_login"))


@app.get("/health")
def health():
    return {"status": "ok", "service": "CLSMC Rapor Sistemi"}, 200
