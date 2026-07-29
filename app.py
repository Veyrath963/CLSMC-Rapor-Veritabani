from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone

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

SYSTEM_NAME = "CLSMC Merkezi Takip ve Raporlama Sistemi"


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
    last_login_at = db.Column(db.DateTime(timezone=True), nullable=True)



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
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_by_admin = db.Column(db.String(120), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    last_login_at = db.Column(db.DateTime(timezone=True), nullable=True)

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
    workflow_status = db.Column(db.String(40), nullable=False, default="completed", index=True)
    admin_note = db.Column(db.Text, nullable=True)
    is_favorite = db.Column(db.Boolean, nullable=False, default=False)

class ReportArchive(db.Model):
    __tablename__ = "report_archives"

    id = db.Column(db.Integer, primary_key=True)
    # Bilerek ForeignKey kullanılmaz. Aktif rapor veya kullanıcı silinse bile
    # arşiv kaydı bağımsız ve kalıcı olarak korunur.
    source_report_id = db.Column(db.Integer, nullable=True, index=True)
    report_type = db.Column(db.String(30), nullable=False, index=True)
    report_number = db.Column(db.String(80), nullable=False, index=True)
    doctor_name = db.Column(db.String(160), nullable=False, index=True)
    doctor_rank = db.Column(db.String(120), nullable=True)
    report_date = db.Column(db.String(64), nullable=True)
    bbcode = db.Column(db.Text, nullable=False)
    form_data = db.Column(db.Text, nullable=True)
    created_by_user_id = db.Column(db.Integer, nullable=True, index=True)
    created_by_username = db.Column(db.String(120), nullable=False, index=True)
    # Bu arşiv sürümünü gerçekten kaydeden kullanıcı. Rapor sahibi bilgisi
    # yukarıdaki created_by alanlarında ayrıca korunur.
    submitted_by_user_id = db.Column(db.Integer, nullable=True, index=True)
    submitted_by_username = db.Column(db.String(120), nullable=False, index=True)
    archive_action = db.Column(db.String(40), nullable=False, index=True)
    archived_by_admin = db.Column(db.String(120), nullable=True)
    source_created_at = db.Column(db.DateTime(timezone=True), nullable=True)
    source_updated_at = db.Column(db.DateTime(timezone=True), nullable=True)
    archived_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )


class UserNotification(db.Model):
    __tablename__ = "user_notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    username = db.Column(db.String(120), nullable=False, index=True)
    title = db.Column(db.String(180), nullable=False)
    message = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(40), nullable=False, default="info", index=True)
    related_type = db.Column(db.String(50), nullable=True)
    related_id = db.Column(db.Integer, nullable=True)
    is_read = db.Column(db.Boolean, nullable=False, default=False, index=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )


class Announcement(db.Model):
    __tablename__ = "announcements"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    body = db.Column(db.Text, nullable=False)
    target_type = db.Column(db.String(30), nullable=False, default="all", index=True)
    target_value = db.Column(db.String(160), nullable=True)
    created_by_admin = db.Column(db.String(120), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )


class LeaveRequest(db.Model):
    __tablename__ = "leave_requests"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    username = db.Column(db.String(120), nullable=False, index=True)
    rank = db.Column(db.String(120), nullable=True)
    leave_type = db.Column(db.String(80), nullable=False)
    start_date = db.Column(db.String(10), nullable=False, index=True)
    end_date = db.Column(db.String(10), nullable=False, index=True)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), nullable=False, default="pending", index=True)
    admin_note = db.Column(db.Text, nullable=True)
    reviewed_by = db.Column(db.String(120), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    reviewed_at = db.Column(db.DateTime(timezone=True), nullable=True)


class ReportDraft(db.Model):
    __tablename__ = "report_drafts"
    __table_args__ = (
        db.UniqueConstraint("user_id", "report_type", name="uq_report_draft_user_type"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    username = db.Column(db.String(120), nullable=False, index=True)
    report_type = db.Column(db.String(30), nullable=False, index=True)
    form_data = db.Column(db.Text, nullable=False, default="{}")
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        index=True,
    )


ARCHIVE_ACTION_LABELS = {
    "initial_backup": "İlk arşiv aktarımı",
    "created": "Kullanıcı tarafından oluşturuldu",
    "updated": "Kullanıcı tarafından güncellendi",
    "admin_updated": "Yönetici tarafından güncellendi",
    "deleted_by_admin": "Aktif kayıttan silinmeden önce yedeklendi",
}


REPORT_STATUS_LABELS = {
    "draft": "Taslak",
    "completed": "Tamamlandı",
    "review": "İnceleme Bekliyor",
    "needs_revision": "Düzeltilmesi Gerekiyor",
    "archived": "Arşivlendi",
}

LEAVE_STATUS_LABELS = {
    "pending": "İnceleme Bekliyor",
    "approved": "Onaylandı",
    "rejected": "Reddedildi",
    "cancelled": "İptal Edildi",
}

LEAVE_TYPE_LABELS = {
    "annual": "Yıllık İzin",
    "medical": "Sağlık İzni",
    "personal": "Mazeret İzni",
    "training": "Eğitim İzni",
    "other": "Diğer",
}


def create_user_notification(
    user: User | None,
    title: str,
    message: str,
    category: str = "info",
    related_type: str | None = None,
    related_id: int | None = None,
    username: str | None = None,
) -> UserNotification:
    resolved_username = ((username or "").strip() or (user.username if user else "Sistem"))
    notification = UserNotification(
        user_id=user.id if user else None,
        username=resolved_username,
        title=title.strip(),
        message=message.strip(),
        category=category.strip() or "info",
        related_type=related_type,
        related_id=related_id,
    )
    db.session.add(notification)
    return notification


def user_owns_report(user: User, report: Report) -> bool:
    if report.created_by_user_id is not None:
        return report.created_by_user_id == user.id
    return (report.created_by_username or "").strip() == user.username


def announcement_matches_user(announcement: Announcement, user: User) -> bool:
    target_type = (announcement.target_type or "all").strip()
    target_value = (announcement.target_value or "").strip()
    rank = (user.rank or "").strip()
    if target_type == "all":
        return True
    if target_type == "medical":
        return rank in MEDICAL_USER_RANKS
    if target_type == "ems":
        return rank in EMS_USER_RANKS
    if target_type == "rank":
        return rank == target_value
    if target_type == "user":
        return user.username == target_value
    return False


def add_report_archive_snapshot(
    report: Report,
    action: str,
    archived_by_admin: str | None = None,
    submitted_by_user_id: int | None = None,
    submitted_by_username: str | None = None,
) -> ReportArchive:
    """Raporun o anki hâlini değiştirilemez bir arşiv kopyası olarak ekler."""
    archive = ReportArchive(
        source_report_id=report.id,
        report_type=report.report_type,
        report_number=report.report_number,
        doctor_name=report.doctor_name,
        doctor_rank=report.doctor_rank,
        report_date=report.report_date,
        bbcode=report.bbcode,
        form_data=report.form_data,
        created_by_user_id=report.created_by_user_id,
        created_by_username=report.created_by_username,
        submitted_by_user_id=(
            submitted_by_user_id
            if submitted_by_user_id is not None
            else report.created_by_user_id
        ),
        submitted_by_username=(
            (submitted_by_username or "").strip()
            or report.created_by_username
        ),
        archive_action=action,
        archived_by_admin=archived_by_admin or None,
        source_created_at=report.created_at,
        source_updated_at=report.updated_at,
    )
    db.session.add(archive)
    return archive


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
    if "last_login_at" not in user_columns:
        with db.engine.begin() as connection:
            connection.execute(text("ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP"))

    # Yeni seçmeli admin rapor düzenleyicisi için form verilerini JSON olarak sakla.
    report_columns = {column["name"] for column in inspect(db.engine).get_columns("reports")}
    if "form_data" not in report_columns:
        with db.engine.begin() as connection:
            connection.execute(text("ALTER TABLE reports ADD COLUMN form_data TEXT"))
    if "workflow_status" not in report_columns:
        with db.engine.begin() as connection:
            connection.execute(text("ALTER TABLE reports ADD COLUMN workflow_status VARCHAR(40) DEFAULT 'completed'"))
    if "admin_note" not in report_columns:
        with db.engine.begin() as connection:
            connection.execute(text("ALTER TABLE reports ADD COLUMN admin_note TEXT"))
    if "is_favorite" not in report_columns:
        with db.engine.begin() as connection:
            connection.execute(text("ALTER TABLE reports ADD COLUMN is_favorite BOOLEAN DEFAULT FALSE"))
    with db.engine.begin() as connection:
        connection.execute(text("UPDATE reports SET workflow_status='completed' WHERE workflow_status IS NULL OR workflow_status=''"))

    # Üyelik silindiğinde eski raporların korunabilmesi için rapor sahibi FK alanı
    # PostgreSQL üzerinde NULL kabul edecek şekilde gevşetilir.
    if db.engine.dialect.name == "postgresql":
        with db.engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE reports ALTER COLUMN created_by_user_id DROP NOT NULL")
            )

    # V23.1: Birden fazla yönetici hesabı ve hesap durum takibi.
    admin_columns = {
        column["name"] for column in inspect(db.engine).get_columns("admin_accounts")
    }
    if "is_active" not in admin_columns:
        with db.engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE admin_accounts ADD COLUMN is_active BOOLEAN DEFAULT TRUE")
            )
    if "created_by_admin" not in admin_columns:
        with db.engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE admin_accounts ADD COLUMN created_by_admin VARCHAR(120)")
            )
    if "last_login_at" not in admin_columns:
        with db.engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE admin_accounts ADD COLUMN last_login_at TIMESTAMP")
            )
    with db.engine.begin() as connection:
        connection.execute(
            text("UPDATE admin_accounts SET is_active=TRUE WHERE is_active IS NULL")
        )

    # Özel yönetici hesabını yalnızca ilk kez oluşturur.
    # Sonraki başlangıçlarda mevcut admin parolası değiştirilmez.
    existing_admin = AdminAccount.query.filter_by(username=ADMIN_USERNAME).first()
    if not existing_admin:
        db.session.add(
            AdminAccount(
                username=ADMIN_USERNAME,
                password_hash=DEFAULT_ADMIN_PASSWORD_HASH,
                is_active=True,
                created_by_admin="Sistem",
            )
        )
        db.session.commit()

    # V20.5.8: Sistemde önceden bulunan tüm raporlar ilk kez arşive aktarılır.
    # Aynı aktif rapor için daha önce bir arşiv kaydı varsa tekrar oluşturulmaz.
    archived_source_ids = {
        source_id
        for (source_id,) in (
            db.session.query(ReportArchive.source_report_id)
            .filter(ReportArchive.source_report_id.isnot(None))
            .distinct()
            .all()
        )
    }
    initial_archive_count = 0
    for existing_report in Report.query.order_by(Report.id.asc()).all():
        if existing_report.id in archived_source_ids:
            continue
        add_report_archive_snapshot(existing_report, "initial_backup")
        initial_archive_count += 1
    if initial_archive_count:
        db.session.commit()
        logger.info(
            "REPORT_ARCHIVE_BACKFILL | archived_reports=%s",
            initial_archive_count,
        )


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
            user.last_login_at = datetime.now(timezone.utc)
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

    session["username"] = user.username
    allowed_report_types = sorted(allowed_report_types_for_rank(user.rank))
    if not allowed_report_types:
        flash(
            "Hesabınıza rapor erişimi sağlayan geçerli bir görev rolü atanmadı. Yöneticiniz ile iletişime geçin.",
            "error",
        )
        return redirect(url_for("settings"))

    initial_report_type = "ems" if "ems" in allowed_report_types else "vaka"
    ems_report_number = (
        next_report_number("ems", "CLSMC-EMS")
        if "ems" in allowed_report_types
        else "CLSMC-EMS-0001"
    )

    own_filter = db.or_(
        Report.created_by_user_id == user.id,
        db.and_(
            Report.created_by_user_id.is_(None),
            Report.created_by_username == user.username,
        ),
    )
    own_reports = (
        Report.query.filter(own_filter)
        .order_by(Report.updated_at.desc(), Report.id.desc())
        .all()
    )
    now_utc = datetime.now(timezone.utc)
    week_cutoff = now_utc - timedelta(days=7)
    month_cutoff = now_utc - timedelta(days=30)

    def normalized_utc(value):
        if not value:
            return None
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)

    personal_stats = {
        "total": len(own_reports),
        "week": sum(1 for report in own_reports if normalized_utc(report.created_at) and normalized_utc(report.created_at) >= week_cutoff),
        "month": sum(1 for report in own_reports if normalized_utc(report.created_at) and normalized_utc(report.created_at) >= month_cutoff),
        "favorites": sum(1 for report in own_reports if bool(report.is_favorite)),
    }

    report_type_counts = {}
    for report in own_reports:
        report_type_counts[report.report_type] = report_type_counts.get(report.report_type, 0) + 1
    favorite_type = max(report_type_counts, key=report_type_counts.get) if report_type_counts else None
    personal_stats["favorite_type"] = REPORT_TYPE_LABELS.get(favorite_type, "—") if favorite_type else "—"

    notification_filter = db.or_(
        UserNotification.user_id == user.id,
        db.and_(UserNotification.user_id.is_(None), UserNotification.username == user.username),
    )
    notifications = (
        UserNotification.query
        .filter(notification_filter)
        .order_by(UserNotification.created_at.desc(), UserNotification.id.desc())
        .limit(12)
        .all()
    )
    unread_notification_count = UserNotification.query.filter(
        notification_filter,
        UserNotification.is_read.is_(False),
    ).count()

    active_announcements = Announcement.query.filter_by(is_active=True).order_by(Announcement.created_at.desc()).all()
    announcements = [item for item in active_announcements if announcement_matches_user(item, user)][:5]

    leave_requests = (
        LeaveRequest.query
        .filter(
            db.or_(
                LeaveRequest.user_id == user.id,
                db.and_(LeaveRequest.user_id.is_(None), LeaveRequest.username == user.username),
            )
        )
        .order_by(LeaveRequest.created_at.desc(), LeaveRequest.id.desc())
        .limit(8)
        .all()
    )

    drafts = ReportDraft.query.filter_by(user_id=user.id).order_by(ReportDraft.updated_at.desc()).all()
    draft_payloads = {}
    for draft in drafts:
        try:
            parsed = json.loads(draft.form_data or "{}")
            draft_payloads[draft.report_type] = parsed if isinstance(parsed, dict) else {}
        except (TypeError, ValueError, json.JSONDecodeError):
            draft_payloads[draft.report_type] = {}

    return render_template(
        "panel.html",
        system_name=SYSTEM_NAME,
        username=user.username,
        user_rank=user.rank or "",
        user_created_at=user.created_at,
        last_login_at=user.last_login_at,
        allowed_report_types=allowed_report_types,
        initial_report_type=initial_report_type,
        ems_report_number=ems_report_number,
        is_ems_user=initial_report_type == "ems",
        personal_stats=personal_stats,
        recent_reports=own_reports[:8],
        report_type_labels=REPORT_TYPE_LABELS,
        report_status_labels=REPORT_STATUS_LABELS,
        notifications=notifications,
        unread_notification_count=unread_notification_count,
        announcements=announcements,
        leave_requests=leave_requests,
        leave_status_labels=LEAVE_STATUS_LABELS,
        leave_type_labels=LEAVE_TYPE_LABELS,
        drafts=drafts,
        draft_payloads=draft_payloads,
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
                workflow_status="completed",
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
            # Kullanıcı kaydı anında tamamlanır; ayrıca yönetici/rütbeli onayı beklemez.
            report.workflow_status = "completed"

        # Yeni kayıtta rapor kimliğinin oluşması için flush yapılır; ardından
        # kullanıcının gönderdiği tam veri arşiv tablosuna ayrı kopya olarak eklenir.
        db.session.flush()
        add_report_archive_snapshot(
            report,
            "created" if is_new else "updated",
            submitted_by_user_id=current_user.id,
            submitted_by_username=current_user.username,
        )
        ReportDraft.query.filter_by(user_id=current_user.id, report_type=report_type).delete()
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


@app.route("/api/drafts/<report_type>", methods=["GET", "POST", "DELETE"])
def report_draft_api(report_type: str):
    if not session.get("user_id"):
        return {"ok": False, "message": "Oturum süresi dolmuş."}, 401
    user = db.session.get(User, session["user_id"])
    if not user:
        session.clear()
        return {"ok": False, "message": "Kullanıcı hesabı bulunamadı."}, 401
    if report_type not in allowed_report_types_for_rank(user.rank):
        return {"ok": False, "message": "Bu rapor türüne erişiminiz yok."}, 403

    draft = ReportDraft.query.filter_by(user_id=user.id, report_type=report_type).first()
    if request.method == "GET":
        if not draft:
            return {"ok": True, "exists": False, "form_data": {}}, 200
        try:
            parsed = json.loads(draft.form_data or "{}")
            if not isinstance(parsed, dict):
                parsed = {}
        except (TypeError, ValueError, json.JSONDecodeError):
            parsed = {}
        return {"ok": True, "exists": True, "form_data": parsed, "updated_at": draft.updated_at.isoformat() if draft.updated_at else None}, 200

    if request.method == "DELETE":
        if draft:
            db.session.delete(draft)
            db.session.commit()
        return {"ok": True, "message": "Taslak silindi."}, 200

    data = request.get_json(silent=True) or {}
    form_data = data.get("form_data", {})
    if not isinstance(form_data, dict):
        return {"ok": False, "message": "Taslak verisi geçersiz."}, 400
    if not draft:
        draft = ReportDraft(user_id=user.id, username=user.username, report_type=report_type)
        db.session.add(draft)
    draft.username = user.username
    draft.form_data = json.dumps(form_data, ensure_ascii=False)
    draft.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return {"ok": True, "message": "Taslak kaydedildi.", "updated_at": draft.updated_at.isoformat()}, 200


@app.get("/reports")
def user_report_center():
    if not session.get("user_id"):
        flash("Önce giriş yapmalısınız.", "error")
        return redirect(url_for("login_page"))
    user = db.session.get(User, session["user_id"])
    if not user:
        session.clear()
        return redirect(url_for("login_page"))

    query = Report.query.filter(
        db.or_(
            Report.created_by_user_id == user.id,
            db.and_(Report.created_by_user_id.is_(None), Report.created_by_username == user.username),
        )
    )
    search = request.args.get("q", "").strip()
    selected_type = request.args.get("type", "").strip()
    selected_status = request.args.get("status", "").strip()
    favorites_only = request.args.get("favorites", "") == "1"
    if search:
        like = f"%{search}%"
        query = query.filter(db.or_(Report.report_number.ilike(like), Report.form_data.ilike(like), Report.bbcode.ilike(like)))
    if selected_type in REPORT_TYPE_LABELS:
        query = query.filter(Report.report_type == selected_type)
    else:
        selected_type = ""
    if selected_status in REPORT_STATUS_LABELS:
        query = query.filter(Report.workflow_status == selected_status)
    else:
        selected_status = ""
    if favorites_only:
        query = query.filter(Report.is_favorite.is_(True))
    reports = query.order_by(Report.updated_at.desc(), Report.id.desc()).all()
    return render_template(
        "report_center.html",
        system_name=SYSTEM_NAME,
        username=user.username,
        user_rank=user.rank or "",
        reports=reports,
        search=search,
        selected_type=selected_type,
        selected_status=selected_status,
        favorites_only=favorites_only,
        report_type_labels=REPORT_TYPE_LABELS,
        report_status_labels=REPORT_STATUS_LABELS,
    )


@app.get("/reports/<int:report_id>")
def user_report_view(report_id: int):
    if not session.get("user_id"):
        flash("Önce giriş yapmalısınız.", "error")
        return redirect(url_for("login_page"))
    user = db.session.get(User, session["user_id"])
    report = db.session.get(Report, report_id)
    if not user or not report or not user_owns_report(user, report):
        flash("Rapor bulunamadı veya bu kayda erişiminiz yok.", "error")
        return redirect(url_for("user_report_center"))
    try:
        form_data = json.loads(report.form_data or "{}")
        if not isinstance(form_data, dict):
            form_data = {}
    except (TypeError, ValueError, json.JSONDecodeError):
        form_data = {}
    versions = ReportArchive.query.filter_by(source_report_id=report.id).order_by(ReportArchive.archived_at.desc(), ReportArchive.id.desc()).all()
    return render_template(
        "user_report_view.html",
        system_name=SYSTEM_NAME,
        username=user.username,
        report=report,
        form_data=form_data,
        versions=versions,
        report_type_labels=REPORT_TYPE_LABELS,
        report_status_labels=REPORT_STATUS_LABELS,
        archive_action_labels=ARCHIVE_ACTION_LABELS,
    )


@app.get("/reports/<int:report_id>/versions/<int:archive_id>")
def user_report_version_view(report_id: int, archive_id: int):
    if not session.get("user_id"):
        return redirect(url_for("login_page"))
    user = db.session.get(User, session["user_id"])
    report = db.session.get(Report, report_id)
    archive = db.session.get(ReportArchive, archive_id)
    if (
        not user
        or not report
        or not archive
        or archive.source_report_id != report.id
        or not user_owns_report(user, report)
    ):
        flash("Rapor sürümü bulunamadı veya erişiminiz yok.", "error")
        return redirect(url_for("user_report_center"))
    try:
        form_data = json.loads(archive.form_data or "{}")
        if not isinstance(form_data, dict):
            form_data = {}
    except (TypeError, ValueError, json.JSONDecodeError):
        form_data = {}
    return render_template(
        "user_report_version_view.html",
        system_name=SYSTEM_NAME,
        username=user.username,
        report=report,
        archive=archive,
        form_data=form_data,
        report_type_labels=REPORT_TYPE_LABELS,
        archive_action_labels=ARCHIVE_ACTION_LABELS,
    )


@app.post("/reports/<int:report_id>/favorite")
def user_report_favorite(report_id: int):
    if not session.get("user_id"):
        return redirect(url_for("login_page"))
    user = db.session.get(User, session["user_id"])
    report = db.session.get(Report, report_id)
    if not user or not report or not user_owns_report(user, report):
        flash("Rapor bulunamadı.", "error")
        return redirect(url_for("user_report_center"))
    report.is_favorite = not bool(report.is_favorite)
    db.session.commit()
    flash("Rapor favorilere eklendi." if report.is_favorite else "Rapor favorilerden çıkarıldı.", "success")
    return redirect(request.referrer or url_for("user_report_center"))


@app.post("/notifications/<int:notification_id>/read")
def user_notification_read(notification_id: int):
    if not session.get("user_id"):
        return redirect(url_for("login_page"))
    user = db.session.get(User, session["user_id"])
    notification = db.session.get(UserNotification, notification_id)
    if user and notification and (notification.user_id == user.id or (notification.user_id is None and notification.username == user.username)):
        notification.is_read = True
        db.session.commit()
    return redirect(url_for("panel") + "#notifications")


@app.post("/notifications/read-all")
def user_notifications_read_all():
    if not session.get("user_id"):
        return redirect(url_for("login_page"))
    user = db.session.get(User, session["user_id"])
    if user:
        UserNotification.query.filter(
            db.or_(
                UserNotification.user_id == user.id,
                db.and_(UserNotification.user_id.is_(None), UserNotification.username == user.username),
            ),
            UserNotification.is_read.is_(False),
        ).update({"is_read": True}, synchronize_session=False)
        db.session.commit()
    return redirect(url_for("panel") + "#notifications")


@app.post("/leave-requests")
def user_create_leave_request():
    if not session.get("user_id"):
        flash("Önce giriş yapmalısınız.", "error")
        return redirect(url_for("login_page"))
    user = db.session.get(User, session["user_id"])
    if not user:
        session.clear()
        return redirect(url_for("login_page"))
    leave_type = request.form.get("leave_type", "").strip()
    start_date = request.form.get("start_date", "").strip()
    end_date = request.form.get("end_date", "").strip()
    reason = request.form.get("reason", "").strip()
    if leave_type not in LEAVE_TYPE_LABELS or not start_date or not end_date or not reason:
        flash("İzin türü, tarih aralığı ve açıklama zorunludur.", "error")
        return redirect(url_for("panel") + "#leave-center")
    try:
        start_value = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_value = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        flash("İzin tarihleri geçersiz.", "error")
        return redirect(url_for("panel") + "#leave-center")
    if end_value < start_value:
        flash("İzin bitiş tarihi başlangıç tarihinden önce olamaz.", "error")
        return redirect(url_for("panel") + "#leave-center")
    existing_pending = LeaveRequest.query.filter_by(user_id=user.id, status="pending").first()
    if existing_pending:
        flash("Zaten inceleme bekleyen bir izin talebiniz bulunuyor.", "error")
        return redirect(url_for("panel") + "#leave-center")
    leave_request = LeaveRequest(
        user_id=user.id,
        username=user.username,
        rank=user.rank or None,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
        status="pending",
    )
    db.session.add(leave_request)
    db.session.commit()
    write_log("INFO", "LEAVE_REQUEST_CREATED", f"username={user.username}; leave_request_id={leave_request.id}")
    flash("İzin talebiniz Hastane Yöneticisi paneline iletildi.", "success")
    return redirect(url_for("panel") + "#leave-center")


@app.post("/leave-requests/<int:leave_request_id>/cancel")
def user_cancel_leave_request(leave_request_id: int):
    if not session.get("user_id"):
        return redirect(url_for("login_page"))
    user = db.session.get(User, session["user_id"])
    leave_request = db.session.get(LeaveRequest, leave_request_id)
    if not user or not leave_request or leave_request.user_id != user.id:
        flash("İzin talebi bulunamadı.", "error")
        return redirect(url_for("panel") + "#leave-center")
    if leave_request.status != "pending":
        flash("Yalnızca inceleme bekleyen izin talebi iptal edilebilir.", "error")
        return redirect(url_for("panel") + "#leave-center")
    leave_request.status = "cancelled"
    db.session.commit()
    flash("İzin talebiniz iptal edildi.", "success")
    return redirect(url_for("panel") + "#leave-center")


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

    session["username"] = user.username
    own_filter = db.or_(
        Report.created_by_user_id == user.id,
        db.and_(Report.created_by_user_id.is_(None), Report.created_by_username == user.username),
    )
    reports = Report.query.filter(own_filter).order_by(Report.updated_at.desc()).all()

    type_map = {}
    for report in reports:
        type_map[report.report_type] = type_map.get(report.report_type, 0) + 1
    type_counts = [
        {"label": REPORT_TYPE_LABELS.get(report_type, report_type), "count": count}
        for report_type, count in sorted(type_map.items(), key=lambda item: (-item[1], item[0]))
    ]
    doctor_counts = [{"doctor": user.username, "count": len(reports)}] if reports else []
    max_type_count = max([item["count"] for item in type_counts], default=1)
    max_doctor_count = max([item["count"] for item in doctor_counts], default=1)

    now_utc = datetime.now(timezone.utc)
    week_cutoff = now_utc - timedelta(days=7)
    month_cutoff = now_utc - timedelta(days=30)
    def normalized_utc(value):
        if not value:
            return None
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)

    return render_template(
        "statistics.html",
        username=user.username,
        user_rank=user.rank or "",
        total_reports=len(reports),
        week_reports=sum(1 for item in reports if normalized_utc(item.created_at) and normalized_utc(item.created_at) >= week_cutoff),
        month_reports=sum(1 for item in reports if normalized_utc(item.created_at) and normalized_utc(item.created_at) >= month_cutoff),
        favorite_reports=sum(1 for item in reports if bool(item.is_favorite)),
        doctor_counts=doctor_counts,
        type_counts=type_counts,
        max_type_count=max_type_count,
        max_doctor_count=max_doctor_count,
        recent_reports=reports[:20],
        report_type_labels=REPORT_TYPE_LABELS,
        report_status_labels=REPORT_STATUS_LABELS,
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
            user_rank=user.rank or "",
            user_created_at=user.created_at,
            last_login_at=user.last_login_at,
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

        if admin and not admin.is_active:
            write_log("WARNING", "ADMIN_LOGIN_INACTIVE", f"username={username}")
            flash("Bu yönetici hesabı pasif durumdadır.", "error")
            return render_template("admin_login.html", username=username), 403

        if admin and check_password_hash(admin.password_hash, password):
            session.clear()
            session["admin_id"] = admin.id
            session["admin_username"] = admin.username
            admin.last_login_at = datetime.now(timezone.utc)
            db.session.commit()
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
        report_type_key = f"{report.report_type}_count"
        if report_type_key in doctor_map[doctor_name]:
            doctor_map[doctor_name][report_type_key] += 1

    doctors = sorted(
        doctor_map.values(),
        key=lambda item: (-item["count"], item["name"].lower()),
    )

    type_counts = {}
    type_key_counts = {}
    for report in reports:
        label = REPORT_TYPE_LABELS.get(report.report_type, report.report_type)
        type_counts[label] = type_counts.get(label, 0) + 1
        type_key_counts[report.report_type] = type_key_counts.get(report.report_type, 0) + 1

    now_utc = datetime.now(timezone.utc)

    def normalized_utc(value):
        if not value:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    reports_today = 0
    reports_last_7_days = 0
    reports_last_30_days = 0
    cutoff_7 = now_utc - timedelta(days=7)
    cutoff_30 = now_utc - timedelta(days=30)
    for report in reports:
        created_at = normalized_utc(report.created_at)
        if not created_at:
            continue
        if created_at.date() == now_utc.date():
            reports_today += 1
        if created_at >= cutoff_7:
            reports_last_7_days += 1
        if created_at >= cutoff_30:
            reports_last_30_days += 1

    rank_counts = {}
    users_without_rank = 0
    for user in users:
        rank = (user.rank or "").strip()
        if not rank:
            users_without_rank += 1
            rank = "Rütbe Atanmadı"
        rank_counts[rank] = rank_counts.get(rank, 0) + 1

    total_reports = len(reports)
    report_type_summary = []
    for report_type, label in REPORT_TYPE_LABELS.items():
        count = type_key_counts.get(report_type, 0)
        percent = round((count / total_reports) * 100) if total_reports else 0
        report_type_summary.append({
            "key": report_type,
            "label": label,
            "count": count,
            "percent": percent,
        })

    rank_summary = []
    active_user_count = len(users)
    for rank, count in sorted(rank_counts.items(), key=lambda item: (-item[1], item[0].lower())):
        percent = round((count / active_user_count) * 100) if active_user_count else 0
        rank_summary.append({"label": rank, "count": count, "percent": percent})

    contributor_counts = {}
    for report in reports:
        username = (report.created_by_username or "Bilinmeyen Kullanıcı").strip()
        contributor_counts[username] = contributor_counts.get(username, 0) + 1
    top_contributors = [
        {"username": username, "count": count}
        for username, count in sorted(
            contributor_counts.items(),
            key=lambda item: (-item[1], item[0].lower()),
        )[:8]
    ]

    recent_logs = (
        AppLog.query
        .order_by(AppLog.created_at.desc())
        .limit(40)
        .all()
    )
    archive_count = ReportArchive.query.count()
    latest_archive = (
        ReportArchive.query
        .order_by(ReportArchive.archived_at.desc(), ReportArchive.id.desc())
        .first()
    )
    archived_source_ids = {
        source_id
        for (source_id,) in (
            db.session.query(ReportArchive.source_report_id)
            .filter(ReportArchive.source_report_id.isnot(None))
            .distinct()
            .all()
        )
    }
    active_report_ids = {report.id for report in reports}
    archived_active_count = len(active_report_ids.intersection(archived_source_ids))
    archive_coverage = round((archived_active_count / total_reports) * 100) if total_reports else 100
    unarchived_report_count = max(total_reports - archived_active_count, 0)

    reports_without_form_data = sum(1 for report in reports if not (report.form_data or "").strip())
    reports_without_date = sum(1 for report in reports if not (report.report_date or "").strip())

    system_alerts = []
    if users_without_rank:
        system_alerts.append({
            "level": "warning",
            "title": "Rütbesi atanmamış kullanıcılar",
            "detail": f"{users_without_rank} aktif kullanıcı için rütbe seçilmesi gerekiyor.",
            "target": "users",
        })
    if unarchived_report_count:
        system_alerts.append({
            "level": "danger",
            "title": "Arşiv kopyası bulunmayan raporlar",
            "detail": f"{unarchived_report_count} aktif raporun arşiv eşleşmesi bulunmuyor.",
            "target": "reports",
        })
    if reports_without_form_data:
        system_alerts.append({
            "level": "info",
            "title": "Eski biçimli rapor kayıtları",
            "detail": f"{reports_without_form_data} raporda seçmeli form verisi bulunmuyor; BBCode korunuyor.",
            "target": "reports",
        })
    if reports_without_date:
        system_alerts.append({
            "level": "info",
            "title": "Rapor tarihi eksik kayıtlar",
            "detail": f"{reports_without_date} raporda rapor tarihi alanı boş.",
            "target": "reports",
        })
    if not system_alerts:
        system_alerts.append({
            "level": "success",
            "title": "Sistem düzenli görünüyor",
            "detail": "Kullanıcı, rapor ve arşiv kontrollerinde dikkat gerektiren bir durum bulunmadı.",
            "target": "overview",
        })

    database_label = (
        "Neon PostgreSQL"
        if db.engine.dialect.name == "postgresql"
        else db.engine.dialect.name.title()
    )

    pending_leave_count = LeaveRequest.query.filter_by(status="pending").count()
    active_announcement_count = Announcement.query.filter_by(is_active=True).count()

    return render_template(
        "admin_dashboard.html",
        system_name=SYSTEM_NAME,
        admin_username=session.get("admin_username", ""),
        users=users,
        deleted_users=deleted_users,
        doctors=doctors,
        reports=reports,
        recent_reports=reports[:15],
        recent_logs=recent_logs,
        type_counts=type_counts,
        report_type_labels=REPORT_TYPE_LABELS,
        archive_count=archive_count,
        latest_archive=latest_archive,
        archive_coverage=archive_coverage,
        unarchived_report_count=unarchived_report_count,
        reports_today=reports_today,
        reports_last_7_days=reports_last_7_days,
        reports_last_30_days=reports_last_30_days,
        report_type_summary=report_type_summary,
        rank_summary=rank_summary,
        top_contributors=top_contributors,
        system_alerts=system_alerts,
        users_without_rank=users_without_rank,
        reports_without_form_data=reports_without_form_data,
        reports_without_date=reports_without_date,
        database_label=database_label,
        generated_at=now_utc,
        pending_leave_count=pending_leave_count,
        active_announcement_count=active_announcement_count,
    )


@app.route("/admin/accounts", methods=["GET", "POST"])
def admin_accounts():
    if not admin_required():
        flash("Bu bölüm yalnızca yönetici erişimine açıktır.", "error")
        return redirect(url_for("admin_login"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        password_confirm = request.form.get("password_confirm", "")

        if len(username) < 3 or len(username) > 120:
            flash("Admin kullanıcı adı 3 ile 120 karakter arasında olmalıdır.", "error")
        elif len(password) < 8:
            flash("Admin şifresi en az 8 karakter olmalıdır.", "error")
        elif password != password_confirm:
            flash("Admin şifreleri eşleşmiyor.", "error")
        elif AdminAccount.query.filter_by(username=username).first():
            flash("Bu admin kullanıcı adı zaten kullanılıyor.", "error")
        elif User.query.filter_by(username=username).first():
            flash("Bu kullanıcı adı normal bir personel hesabında kullanılıyor.", "error")
        else:
            try:
                account = AdminAccount(
                    username=username,
                    password_hash=generate_password_hash(password),
                    is_active=True,
                    created_by_admin=session.get("admin_username", ""),
                )
                db.session.add(account)
                db.session.commit()
                write_log(
                    "INFO",
                    "ADMIN_ACCOUNT_CREATED",
                    f"admin={session.get('admin_username','')}; created_admin={username}",
                )
                flash(f"{username} yönetici hesabı oluşturuldu.", "success")
                return redirect(url_for("admin_accounts"))
            except Exception as exc:
                db.session.rollback()
                logger.exception("ADMIN_ACCOUNT_CREATE_ERROR | username=%s", username)
                try:
                    write_log(
                        "ERROR",
                        "ADMIN_ACCOUNT_CREATE_ERROR",
                        f"admin={session.get('admin_username','')}; username={username}; error={type(exc).__name__}",
                    )
                except Exception:
                    pass
                flash("Yönetici hesabı oluşturulamadı.", "error")

    accounts = AdminAccount.query.order_by(AdminAccount.created_at.asc()).all()
    active_admin_count = sum(1 for account in accounts if account.is_active)
    return render_template(
        "admin_accounts.html",
        system_name=SYSTEM_NAME,
        admin_username=session.get("admin_username", ""),
        current_admin_id=session.get("admin_id"),
        accounts=accounts,
        active_admin_count=active_admin_count,
    )


@app.post("/admin/accounts/<int:admin_id>/reset-password")
def admin_reset_account_password(admin_id: int):
    if not admin_required():
        return redirect(url_for("admin_login"))

    account = db.session.get(AdminAccount, admin_id)
    if not account:
        flash("Yönetici hesabı bulunamadı.", "error")
        return redirect(url_for("admin_accounts"))

    password = request.form.get("new_password", "")
    password_confirm = request.form.get("new_password_confirm", "")
    if len(password) < 8:
        flash("Yeni admin şifresi en az 8 karakter olmalıdır.", "error")
        return redirect(url_for("admin_accounts"))
    if password != password_confirm:
        flash("Yeni admin şifreleri eşleşmiyor.", "error")
        return redirect(url_for("admin_accounts"))
    if check_password_hash(account.password_hash, password):
        flash("Yeni şifre mevcut admin şifresiyle aynı olamaz.", "error")
        return redirect(url_for("admin_accounts"))

    account.password_hash = generate_password_hash(password)
    db.session.commit()
    write_log(
        "INFO",
        "ADMIN_ACCOUNT_PASSWORD_RESET",
        f"admin={session.get('admin_username','')}; target_admin={account.username}",
    )
    flash(f"{account.username} hesabının şifresi güncellendi.", "success")
    return redirect(url_for("admin_accounts"))


@app.post("/admin/accounts/<int:admin_id>/toggle")
def admin_toggle_account(admin_id: int):
    if not admin_required():
        return redirect(url_for("admin_login"))

    account = db.session.get(AdminAccount, admin_id)
    if not account:
        flash("Yönetici hesabı bulunamadı.", "error")
        return redirect(url_for("admin_accounts"))
    if account.id == session.get("admin_id"):
        flash("Oturum açtığınız yönetici hesabını pasif yapamazsınız.", "error")
        return redirect(url_for("admin_accounts"))

    if account.is_active:
        active_count = AdminAccount.query.filter_by(is_active=True).count()
        if active_count <= 1:
            flash("Sistemde en az bir aktif yönetici hesabı bulunmalıdır.", "error")
            return redirect(url_for("admin_accounts"))

    account.is_active = not account.is_active
    db.session.commit()
    write_log(
        "INFO",
        "ADMIN_ACCOUNT_STATUS_CHANGED",
        f"admin={session.get('admin_username','')}; target_admin={account.username}; active={account.is_active}",
    )
    flash(
        f"{account.username} hesabı {'aktif' if account.is_active else 'pasif'} duruma getirildi.",
        "success",
    )
    return redirect(url_for("admin_accounts"))


@app.post("/admin/accounts/<int:admin_id>/delete")
def admin_delete_account(admin_id: int):
    if not admin_required():
        return redirect(url_for("admin_login"))

    account = db.session.get(AdminAccount, admin_id)
    if not account:
        flash("Yönetici hesabı bulunamadı.", "error")
        return redirect(url_for("admin_accounts"))
    if account.id == session.get("admin_id"):
        flash("Oturum açtığınız yönetici hesabını silemezsiniz.", "error")
        return redirect(url_for("admin_accounts"))
    if AdminAccount.query.count() <= 1:
        flash("Sistemde en az bir yönetici hesabı bulunmalıdır.", "error")
        return redirect(url_for("admin_accounts"))

    deleted_username = account.username
    db.session.delete(account)
    db.session.commit()
    write_log(
        "WARNING",
        "ADMIN_ACCOUNT_DELETED",
        f"admin={session.get('admin_username','')}; deleted_admin={deleted_username}",
    )
    flash(f"{deleted_username} yönetici hesabı silindi.", "success")
    return redirect(url_for("admin_accounts"))


@app.get("/admin/hospital-management")
def admin_hospital_management():
    if not admin_required():
        flash("Bu bölüm yalnızca yönetici erişimine açıktır.", "error")
        return redirect(url_for("admin_login"))
    leave_requests = LeaveRequest.query.order_by(
        text("CASE WHEN status='pending' THEN 0 ELSE 1 END"),
        LeaveRequest.created_at.desc(),
    ).all()
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
    users = User.query.order_by(User.username.asc()).all()
    rank_counts = {}
    for user in users:
        rank = (user.rank or "Atanmadı").strip() or "Atanmadı"
        rank_counts[rank] = rank_counts.get(rank, 0) + 1
    return render_template(
        "admin_hospital_management.html",
        system_name=SYSTEM_NAME,
        admin_username=session.get("admin_username", ""),
        leave_requests=leave_requests,
        announcements=announcements,
        users=users,
        rank_counts=rank_counts,
        pending_leave_count=sum(1 for item in leave_requests if item.status == "pending"),
        approved_leave_count=sum(1 for item in leave_requests if item.status == "approved"),
        leave_status_labels=LEAVE_STATUS_LABELS,
        leave_type_labels=LEAVE_TYPE_LABELS,
        allowed_user_ranks=sorted(ALLOWED_USER_RANKS),
    )


@app.post("/admin/leave-requests/<int:leave_request_id>/review")
def admin_review_leave_request(leave_request_id: int):
    if not admin_required():
        return redirect(url_for("admin_login"))
    leave_request = db.session.get(LeaveRequest, leave_request_id)
    if not leave_request:
        flash("İzin talebi bulunamadı.", "error")
        return redirect(url_for("admin_hospital_management"))
    decision = request.form.get("decision", "").strip()
    admin_note = request.form.get("admin_note", "").strip()
    if decision not in {"approved", "rejected"}:
        flash("Geçersiz izin kararı.", "error")
        return redirect(url_for("admin_hospital_management"))
    if leave_request.status != "pending":
        flash("Bu izin talebi daha önce sonuçlandırılmış.", "error")
        return redirect(url_for("admin_hospital_management"))
    leave_request.status = decision
    leave_request.admin_note = admin_note or None
    leave_request.reviewed_by = session.get("admin_username", "")
    leave_request.reviewed_at = datetime.now(timezone.utc)
    user = db.session.get(User, leave_request.user_id) if leave_request.user_id else User.query.filter_by(username=leave_request.username).first()
    result_label = "onaylandı" if decision == "approved" else "reddedildi"
    notification_message = (
        f"{leave_request.start_date} - {leave_request.end_date} tarihleri arasındaki "
        f"{LEAVE_TYPE_LABELS.get(leave_request.leave_type, leave_request.leave_type)} talebiniz {result_label}."
    )
    if admin_note:
        notification_message += f" Yönetici notu: {admin_note}"
    create_user_notification(
        user,
        "İzin talebiniz sonuçlandı",
        notification_message,
        "success" if decision == "approved" else "warning",
        "leave_request",
        leave_request.id,
        username=leave_request.username,
    )
    db.session.commit()
    write_log("INFO", "LEAVE_REQUEST_REVIEWED", f"admin={session.get('admin_username','')}; leave_request_id={leave_request.id}; decision={decision}")
    flash(f"İzin talebi {result_label}; kullanıcıya bildirim gönderildi.", "success")
    return redirect(url_for("admin_hospital_management") + "#leave-requests")


@app.post("/admin/announcements")
def admin_create_announcement():
    if not admin_required():
        return redirect(url_for("admin_login"))
    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()
    target_type = request.form.get("target_type", "all").strip()
    target_value = request.form.get("target_value", "").strip()
    if not title or not body:
        flash("Duyuru başlığı ve içeriği zorunludur.", "error")
        return redirect(url_for("admin_hospital_management") + "#announcements")
    if target_type not in {"all", "medical", "ems", "rank", "user"}:
        target_type = "all"
    if target_type in {"rank", "user"} and not target_value:
        flash("Seçilen duyuru hedefi için değer girilmelidir.", "error")
        return redirect(url_for("admin_hospital_management") + "#announcements")
    announcement = Announcement(
        title=title,
        body=body,
        target_type=target_type,
        target_value=target_value or None,
        created_by_admin=session.get("admin_username", ""),
    )
    db.session.add(announcement)
    db.session.flush()
    notified = 0
    for user in User.query.all():
        if announcement_matches_user(announcement, user):
            create_user_notification(user, title, body, "announcement", "announcement", announcement.id)
            notified += 1
    db.session.commit()
    write_log("INFO", "ANNOUNCEMENT_CREATED", f"admin={session.get('admin_username','')}; announcement_id={announcement.id}; notified={notified}")
    flash(f"Duyuru yayımlandı ve {notified} kullanıcıya bildirim gönderildi.", "success")
    return redirect(url_for("admin_hospital_management") + "#announcements")


@app.post("/admin/announcements/<int:announcement_id>/toggle")
def admin_toggle_announcement(announcement_id: int):
    if not admin_required():
        return redirect(url_for("admin_login"))
    announcement = db.session.get(Announcement, announcement_id)
    if not announcement:
        flash("Duyuru bulunamadı.", "error")
        return redirect(url_for("admin_hospital_management"))
    announcement.is_active = not bool(announcement.is_active)
    db.session.commit()
    flash("Duyuru durumu güncellendi.", "success")
    return redirect(url_for("admin_hospital_management") + "#announcements")


@app.post("/admin/reports/<int:report_id>/workflow")
def admin_update_report_workflow(report_id: int):
    if not admin_required():
        return redirect(url_for("admin_login"))
    report = db.session.get(Report, report_id)
    if not report:
        flash("Rapor bulunamadı.", "error")
        return redirect(url_for("admin_dashboard"))
    status = request.form.get("workflow_status", "completed").strip()
    admin_note = request.form.get("admin_note", "").strip()
    if status not in REPORT_STATUS_LABELS:
        flash("Geçersiz rapor durumu.", "error")
        return redirect(url_for("admin_view_report", report_id=report.id))
    report.workflow_status = status
    report.admin_note = admin_note or None
    owner = db.session.get(User, report.created_by_user_id) if report.created_by_user_id else User.query.filter_by(username=report.created_by_username).first()
    message = f"{report.report_number} numaralı raporun durumu '{REPORT_STATUS_LABELS[status]}' olarak güncellendi."
    if admin_note:
        message += f" Yönetici notu: {admin_note}"
    create_user_notification(owner, "Rapor durumunuz güncellendi", message, "report", "report", report.id, username=report.created_by_username)
    db.session.commit()
    write_log("INFO", "REPORT_WORKFLOW_UPDATED", f"admin={session.get('admin_username','')}; report_id={report.id}; status={status}")
    flash("Rapor durumu güncellendi ve kullanıcıya bildirim gönderildi.", "success")
    return redirect(url_for("admin_view_report", report_id=report.id))


@app.get("/admin/export/system-data.json")
def admin_export_system_data():
    if not admin_required():
        flash("Bu bölüm yalnızca yönetici erişimine açıktır.", "error")
        return redirect(url_for("admin_login"))

    users = User.query.order_by(User.username.asc()).all()
    deleted_users = DeletedUser.query.order_by(DeletedUser.deleted_at.desc()).all()
    reports = Report.query.order_by(Report.updated_at.desc()).all()
    archives = ReportArchive.query.order_by(ReportArchive.archived_at.desc()).all()
    leave_requests = LeaveRequest.query.order_by(LeaveRequest.created_at.desc()).all()
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
    notifications = UserNotification.query.order_by(UserNotification.created_at.desc()).all()

    def iso(value):
        return value.isoformat() if value else None

    def form_data_value(raw_value):
        try:
            parsed = json.loads(raw_value or "{}")
            return parsed if isinstance(parsed, dict) else {}
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}

    payload = {
        "system": SYSTEM_NAME,
        "version": "V23.4",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "security_note": "Parolalar ve parola özetleri bu dışa aktarıma dahil edilmez.",
        "summary": {
            "active_users": len(users),
            "deleted_user_archive_records": len(deleted_users),
            "reports": len(reports),
            "report_archives": len(archives),
            "leave_requests": len(leave_requests),
            "announcements": len(announcements),
            "notifications": len(notifications),
        },
        "users": [
            {
                "id": user.id,
                "username": user.username,
                "rank": user.rank,
                "created_at": iso(user.created_at),
            }
            for user in users
        ],
        "deleted_users": [
            {
                "id": deleted.id,
                "original_user_id": deleted.original_user_id,
                "username": deleted.username,
                "rank": deleted.rank,
                "original_created_at": iso(deleted.original_created_at),
                "deleted_at": iso(deleted.deleted_at),
                "deleted_by_admin": deleted.deleted_by_admin,
            }
            for deleted in deleted_users
        ],
        "reports": [
            {
                "id": report.id,
                "report_type": report.report_type,
                "report_number": report.report_number,
                "doctor_name": report.doctor_name,
                "doctor_rank": report.doctor_rank,
                "report_date": report.report_date,
                "form_data": form_data_value(report.form_data),
                "bbcode": report.bbcode,
                "created_by_user_id": report.created_by_user_id,
                "created_by_username": report.created_by_username,
                "created_at": iso(report.created_at),
                "updated_at": iso(report.updated_at),
                "workflow_status": report.workflow_status,
                "admin_note": report.admin_note,
                "is_favorite": bool(report.is_favorite),
            }
            for report in reports
        ],
        "report_archives": [
            {
                "id": archive.id,
                "source_report_id": archive.source_report_id,
                "report_type": archive.report_type,
                "report_number": archive.report_number,
                "doctor_name": archive.doctor_name,
                "doctor_rank": archive.doctor_rank,
                "report_date": archive.report_date,
                "form_data": form_data_value(archive.form_data),
                "bbcode": archive.bbcode,
                "created_by_user_id": archive.created_by_user_id,
                "created_by_username": archive.created_by_username,
                "submitted_by_user_id": archive.submitted_by_user_id,
                "submitted_by_username": archive.submitted_by_username,
                "archive_action": archive.archive_action,
                "archived_by_admin": archive.archived_by_admin,
                "source_created_at": iso(archive.source_created_at),
                "source_updated_at": iso(archive.source_updated_at),
                "archived_at": iso(archive.archived_at),
            }
            for archive in archives
        ],
        "leave_requests": [
            {
                "id": item.id,
                "user_id": item.user_id,
                "username": item.username,
                "rank": item.rank,
                "leave_type": item.leave_type,
                "start_date": item.start_date,
                "end_date": item.end_date,
                "reason": item.reason,
                "status": item.status,
                "admin_note": item.admin_note,
                "reviewed_by": item.reviewed_by,
                "created_at": iso(item.created_at),
                "reviewed_at": iso(item.reviewed_at),
            }
            for item in leave_requests
        ],
        "announcements": [
            {
                "id": item.id,
                "title": item.title,
                "body": item.body,
                "target_type": item.target_type,
                "target_value": item.target_value,
                "created_by_admin": item.created_by_admin,
                "is_active": bool(item.is_active),
                "created_at": iso(item.created_at),
            }
            for item in announcements
        ],
        "notifications": [
            {
                "id": item.id,
                "user_id": item.user_id,
                "username": item.username,
                "title": item.title,
                "message": item.message,
                "category": item.category,
                "related_type": item.related_type,
                "related_id": item.related_id,
                "is_read": bool(item.is_read),
                "created_at": iso(item.created_at),
            }
            for item in notifications
        ],
    }

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"clsmc_merkezi_takip_yedegi_{timestamp}.json"
    try:
        write_log(
            "INFO",
            "ADMIN_DATA_EXPORT",
            f"admin={session.get('admin_username', '')}; reports={len(reports)}; archives={len(archives)}",
        )
    except Exception:
        pass

    return app.response_class(
        json.dumps(payload, ensure_ascii=False, indent=2),
        mimetype="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/admin/archive")
def admin_archive():
    if not admin_required():
        flash("Bu bölüm yalnızca yönetici erişimine açıktır.", "error")
        return redirect(url_for("admin_login"))

    selected_user = request.args.get("user", "").strip()
    selected_type = request.args.get("type", "").strip()
    search = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int) or 1
    page = max(page, 1)

    query = ReportArchive.query
    if selected_user:
        query = query.filter(ReportArchive.submitted_by_username == selected_user)
    if selected_type in REPORT_TYPE_LABELS:
        query = query.filter(ReportArchive.report_type == selected_type)
    else:
        selected_type = ""
    if search:
        query = query.filter(ReportArchive.report_number.ilike(f"%{search}%"))

    pagination = (
        query.order_by(ReportArchive.archived_at.desc(), ReportArchive.id.desc())
        .paginate(page=page, per_page=100, error_out=False)
    )
    archive_rows = pagination.items

    archive_users = [
        username
        for (username,) in (
            db.session.query(ReportArchive.submitted_by_username)
            .filter(ReportArchive.submitted_by_username != "")
            .distinct()
            .order_by(ReportArchive.submitted_by_username.asc())
            .all()
        )
    ]
    total_archives = ReportArchive.query.count()
    archived_user_count = len(archive_users)
    latest_archive = (
        ReportArchive.query
        .order_by(ReportArchive.archived_at.desc(), ReportArchive.id.desc())
        .first()
    )

    return render_template(
        "admin_archive.html",
        admin_username=session.get("admin_username", ""),
        archive_rows=archive_rows,
        archive_users=archive_users,
        selected_user=selected_user,
        selected_type=selected_type,
        search=search,
        pagination=pagination,
        total_archives=total_archives,
        archived_user_count=archived_user_count,
        latest_archive=latest_archive,
        report_type_labels=REPORT_TYPE_LABELS,
        archive_action_labels=ARCHIVE_ACTION_LABELS,
    )


@app.get("/admin/archive/<int:archive_id>")
def admin_archive_view(archive_id: int):
    if not admin_required():
        flash("Bu bölüm yalnızca yönetici erişimine açıktır.", "error")
        return redirect(url_for("admin_login"))

    archive = db.session.get(ReportArchive, archive_id)
    if not archive:
        flash("Arşiv kaydı bulunamadı.", "error")
        return redirect(url_for("admin_archive"))

    try:
        form_data = json.loads(archive.form_data or "{}")
        if not isinstance(form_data, dict):
            form_data = {}
    except (TypeError, ValueError, json.JSONDecodeError):
        form_data = {}

    return render_template(
        "admin_archive_view.html",
        admin_username=session.get("admin_username", ""),
        archive=archive,
        form_data=form_data,
        report_type_labels=REPORT_TYPE_LABELS,
        archive_action_labels=ARCHIVE_ACTION_LABELS,
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
        report_status_labels=REPORT_STATUS_LABELS,
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
        # Aktif rapor silinse bile son hâli Veri Arşivi'nde kalıcı olarak korunur.
        add_report_archive_snapshot(
            report,
            "deleted_by_admin",
            session.get("admin_username", ""),
        )
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
            UserNotification.query.filter_by(user_id=user.id).update(
                {"username": new_username}, synchronize_session=False
            )
            LeaveRequest.query.filter_by(user_id=user.id).update(
                {"username": new_username}, synchronize_session=False
            )
            ReportDraft.query.filter_by(user_id=user.id).update(
                {"username": new_username}, synchronize_session=False
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
        # Yeni merkezi modül kayıtları da kullanıcı silinince veri kaybetmeden
        # kullanıcı adını korur ve aktif kullanıcı bağlantısını bırakır.
        UserNotification.query.filter_by(user_id=user.id).update(
            {"user_id": None}, synchronize_session=False
        )
        LeaveRequest.query.filter_by(user_id=user.id).update(
            {"user_id": None}, synchronize_session=False
        )
        # Taslaklar kalıcı rapor/veri değildir; hesap kapatılırken temizlenir.
        ReportDraft.query.filter_by(user_id=user.id).delete(synchronize_session=False)

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
        UserNotification.query.filter(
            UserNotification.user_id.is_(None),
            UserNotification.username == deleted_user.username,
        ).update({"user_id": restored_user.id}, synchronize_session=False)
        LeaveRequest.query.filter(
            LeaveRequest.user_id.is_(None),
            LeaveRequest.username == deleted_user.username,
        ).update({"user_id": restored_user.id}, synchronize_session=False)

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


@app.post("/admin/deleted-users/<int:deleted_user_id>/delete-permanently")
def admin_permanently_delete_user(deleted_user_id: int):
    if not admin_required():
        flash("Bu bölüm yalnızca yönetici erişimine açıktır.", "error")
        return redirect(url_for("admin_login"))

    deleted_user = db.session.get(DeletedUser, deleted_user_id)
    if not deleted_user:
        flash("Kalıcı olarak silinecek üyelik arşiv kaydı bulunamadı.", "error")
        return redirect(url_for("admin_dashboard"))

    username = deleted_user.username
    try:
        # Yalnızca silinen üyelik arşiv kaydı kaldırılır. Kullanıcının geçmiş
        # raporları, created_by_username alanı üzerinden tarihsel kayıt olarak korunur.
        db.session.delete(deleted_user)
        db.session.commit()

        write_log(
            "WARNING",
            "ADMIN_DELETED_USER_PERMANENTLY_DELETED",
            (
                f"admin={session.get('admin_username', '')}; "
                f"deleted_user_id={deleted_user_id}; username={username}; "
                "reports_preserved=yes"
            ),
        )

        flash(
            f"{username} silinen üyelik arşivinden kalıcı olarak kaldırıldı. "
            "Geçmiş rapor kayıtları korunmuştur.",
            "success",
        )
        return redirect(url_for("admin_dashboard"))

    except Exception as exc:
        db.session.rollback()
        logger.exception(
            "ADMIN_DELETED_USER_PERMANENT_DELETE_ERROR | deleted_user_id=%s",
            deleted_user_id,
        )
        try:
            write_log(
                "ERROR",
                "ADMIN_DELETED_USER_PERMANENT_DELETE_ERROR",
                (
                    f"admin={session.get('admin_username', '')}; "
                    f"deleted_user_id={deleted_user_id}; "
                    f"error={type(exc).__name__}"
                ),
            )
        except Exception:
            pass

        flash("Silinen üyelik kalıcı olarak kaldırılırken bir hata oluştu.", "error")
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

        db.session.flush()
        add_report_archive_snapshot(
            report,
            "admin_updated",
            session.get("admin_username", ""),
        )
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
    return {"status": "ok", "service": SYSTEM_NAME, "version": "V23.4"}, 200
