"""
Ahmed Bosha — Personal Portfolio & Admin CMS
Flask application with SQLite backend.
Features: Projects CRUD, Categorized Skills Badges (No Percentages), Site Settings, Contact Messages, Photo Uploads.
"""

import os
import sqlite3
import functools
import uuid
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, g, abort, jsonify,
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# ---------------------------------------------------------------------------
# App configuration
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me-in-production")
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024  # 4 MB upload limit

DATABASE = os.path.join(app.root_path, "portfolio.db")
UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "svg"}

# Mail configuration for Gmail forward
MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
MAIL_RECIPIENT = os.environ.get("MAIL_RECIPIENT")


def send_email_async(sender_name, sender_email, message_content, recipient_email):
    """Background worker to send email notification via Gmail SMTP."""
    mail_user = os.environ.get("MAIL_USERNAME")
    mail_pass = os.environ.get("MAIL_PASSWORD")
    if not mail_user or not mail_pass:
        return

    to_email = recipient_email or os.environ.get("MAIL_RECIPIENT") or mail_user

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🔔 New Portfolio Message from {sender_name}"
        msg["From"] = f"Portfolio Contact <{mail_user}>"
        msg["To"] = to_email
        if sender_email:
            msg["Reply-To"] = sender_email

        html = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; background: #161622; color: #f0f0f8; border-radius: 14px; padding: 28px; border: 1px solid #28283c;">
            <h2 style="color: #6c63ff; margin-top: 0; font-size: 20px;">📬 New Message on Your Portfolio</h2>
            <div style="background: #202030; padding: 16px; border-radius: 10px; margin: 20px 0; border: 1px solid rgba(255,255,255,0.06);">
                <p style="margin: 0 0 10px 0; font-size: 15px;"><strong>Sender:</strong> {sender_name}</p>
                <p style="margin: 0; font-size: 15px;"><strong>Email:</strong> <a href="mailto:{sender_email or ''}" style="color: #6c63ff; text-decoration: none;">{sender_email or 'Not provided'}</a></p>
            </div>
            <div style="background: #0c0c12; padding: 18px; border-radius: 10px; border-left: 4px solid #6c63ff;">
                <p style="margin: 0; white-space: pre-wrap; line-height: 1.7; font-size: 15px; color: #e4e4eb;">{message_content}</p>
            </div>
            <p style="font-size: 12px; color: #8e8ea6; margin-top: 24px; text-align: center; border-top: 1px solid #28283c; padding-top: 16px;">
                Sent automatically from your Ahmed Bosha Portfolio Web App
            </p>
        </div>
        """
        msg.attach(MIMEText(html, "html"))

        server = smtplib.SMTP(MAIL_SERVER, MAIL_PORT, timeout=10)
        server.starttls()
        server.login(mail_user, mail_pass)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print(f"[MAIL ERROR] Failed to forward message to Gmail: {e}")


def notify_new_message(sender_name, sender_email, message_content, recipient_email=None):
    """Fire and forget email notification thread."""
    thread = threading.Thread(
        target=send_email_async,
        args=(sender_name, sender_email, message_content, recipient_email),
    )
    thread.daemon = True
    thread.start()

DATABASE = os.path.join(app.root_path, "portfolio.db")
UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "svg"}

# Default admin credentials (override via env vars in production)
ADMIN_USERNAME = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD_HASH = generate_password_hash(
    os.environ.get("ADMIN_PASS", "admin123")
)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_upload(file, prefix="img"):
    """Save an uploaded file and return its filename."""
    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"{prefix}_{uuid.uuid4().hex[:8]}.{ext}"
    file.save(os.path.join(UPLOAD_FOLDER, filename))
    return filename


def delete_upload(filename):
    """Delete an uploaded file if it exists."""
    if filename:
        path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(path):
            os.remove(path)


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db():
    """Open a per-request database connection stored on *g*."""
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def get_settings(db=None):
    """Return the single site_settings row."""
    if db is None:
        db = get_db()
    return db.execute("SELECT * FROM site_settings WHERE id = 1").fetchone()


def init_db():
    """Create tables and insert seed data."""
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row

    db.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            title           TEXT    NOT NULL,
            description     TEXT    NOT NULL,
            tech_stack      TEXT    NOT NULL,
            github_link     TEXT,
            live_demo_link  TEXT,
            certificate_url TEXT,
            image           TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS site_settings (
            id              INTEGER PRIMARY KEY CHECK (id = 1),
            name            TEXT    DEFAULT 'Ahmed Bosha',
            greeting        TEXT    DEFAULT 'Hi, I''m',
            tagline         TEXT    DEFAULT 'Engineering Student & Software Developer',
            typing_texts    TEXT    DEFAULT 'Engineering Student,Software Developer,Problem Solver,Automation Enthusiast',
            bio             TEXT    DEFAULT 'Class of 2029. Passionate about automation, system analysis, and problem-solving. I build tools that turn complex workflows into clean, efficient solutions.',
            profile_photo   TEXT,
            email           TEXT,
            github_url      TEXT,
            linkedin_url    TEXT,
            twitter_url     TEXT,
            resume_url      TEXT,
            color_primary   TEXT    DEFAULT '#6c63ff',
            color_accent    TEXT    DEFAULT '#ff6b6b',
            color_bg        TEXT    DEFAULT '#0f0f13',
            color_surface   TEXT    DEFAULT '#1a1a23',
            color_text      TEXT    DEFAULT '#e4e4eb'
        );

        CREATE TABLE IF NOT EXISTS skills (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            category    TEXT    NOT NULL DEFAULT 'Languages & Backend',
            level_tag   TEXT,
            icon        TEXT,
            sort_order  INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS messages (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_name  TEXT    NOT NULL,
            sender_email TEXT,
            message      TEXT    NOT NULL,
            is_read      INTEGER DEFAULT 0,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # ---- seed site_settings ----
    if db.execute("SELECT COUNT(*) FROM site_settings").fetchone()[0] == 0:
        db.execute("INSERT INTO site_settings (id) VALUES (1)")
        db.commit()
        print("[OK] Default site settings created.")

    # ---- seed skills (categorized chips / badges, no arbitrary percentages) ----
    if db.execute("SELECT COUNT(*) FROM skills").fetchone()[0] == 0:
        db.executemany(
            "INSERT INTO skills (name, category, level_tag, icon, sort_order) VALUES (?, ?, ?, ?, ?)",
            [
                # Languages & Backend
                ("Python", "Programming & Backend", "Advanced", "🐍", 1),
                ("C / C++", "Programming & Backend", "Core", "⚡", 2),
                ("Flask", "Programming & Backend", "Framework", "🌐", 3),
                ("SQLite / SQL", "Programming & Backend", "Database", "🗄️", 4),
                ("REST APIs", "Programming & Backend", "Architecture", "🔌", 5),

                # Security & Systems
                ("Reverse Engineering", "Security & Systems", "Specialty", "🔬", 6),
                ("Frida", "Security & Systems", "Instrumentation", "💉", 7),
                ("Shizuku", "Security & Systems", "Android", "📱", 8),
                ("Binary Analysis", "Security & Systems", "Security", "🔍", 9),
                ("Linux & Shell", "Security & Systems", "Environment", "🐧", 10),

                # Tools & Automation
                ("Automation Scripts", "Tools & Automation", "Workflow", "⚙️", 11),
                ("Git & GitHub", "Tools & Automation", "VCS", "📦", 12),
                ("CSV Data Pipelines", "Tools & Automation", "Data", "📊", 13),
                ("CLI Development", "Tools & Automation", "Tooling", "💻", 14),

                # Engineering & Concepts
                ("System Analysis", "Core Engineering", "Mindset", "📐", 15),
                ("Problem Solving", "Core Engineering", "Strengths", "🧩", 16),
                ("Data Structures", "Core Engineering", "CS Fundamentals", "🌳", 17),
            ],
        )
        db.commit()
        print("[OK] Seed skills inserted.")

    # ---- seed projects ----
    if db.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 0:
        db.executemany(
            """INSERT INTO projects
               (title, description, tech_stack, github_link, live_demo_link, certificate_url, image)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    "HospitalSystem",
                    "A CLI-based appointment management application demonstrating "
                    "dynamic CSV file manipulation and structured data storage. "
                    "Built to streamline patient scheduling with clean data pipelines.",
                    "Python, CSV, CLI",
                    "https://github.com/AhmedBosha/HospitalSystem",
                    None, None, None,
                ),
                (
                    "Mobile Static Analysis",
                    "Automation scripts for reverse engineering binary libraries, "
                    "utilizing instrumentation tools like Shizuku to extract memory "
                    "offsets (e.g., GNames, GWorld). Designed to speed up mobile "
                    "security research workflows.",
                    "Python, Frida, Shizuku, Reverse Engineering",
                    "https://github.com/AhmedBosha/MobileStaticAnalysis",
                    None, None, None,
                ),
            ],
        )
        db.commit()
        print("[OK] Seed project data inserted.")

    db.close()


# ---------------------------------------------------------------------------
# Context processor
# ---------------------------------------------------------------------------

@app.context_processor
def inject_globals():
    """Inject site settings and unread message count into all templates."""
    try:
        settings = get_settings()
        unread = get_db().execute(
            "SELECT COUNT(*) FROM messages WHERE is_read = 0"
        ).fetchone()[0]
    except Exception:
        settings = None
        unread = 0
    return dict(settings=settings, unread_count=unread)


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def login_required(view):
    @functools.wraps(view)
    def wrapped(**kwargs):
        if not session.get("admin_logged_in"):
            flash("Please log in to access the dashboard.", "warning")
            return redirect(url_for("admin_login"))
        return view(**kwargs)
    return wrapped


# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    db = get_db()
    projects = db.execute(
        "SELECT * FROM projects ORDER BY created_at DESC"
    ).fetchall()
    
    # Fetch and group skills by category
    skills_raw = db.execute(
        "SELECT * FROM skills ORDER BY sort_order ASC, id ASC"
    ).fetchall()
    
    categories = {}
    for s in skills_raw:
        cat = s["category"] or "General"
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(s)

    return render_template("index.html", projects=projects, skill_categories=categories)


@app.route("/contact", methods=["POST"])
def contact():
    """Handle contact form submission (public, supports AJAX)."""
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json

    if request.is_json:
        data = request.get_json() or {}
        sender_name = data.get("sender_name", "").strip()
        sender_email = data.get("sender_email", "").strip() or None
        message = data.get("message", "").strip()
    else:
        sender_name = request.form.get("sender_name", "").strip()
        sender_email = request.form.get("sender_email", "").strip() or None
        message = request.form.get("message", "").strip()

    if not sender_name or not message:
        if is_ajax:
            return jsonify({"success": False, "error": "Name and message are required."}), 400
        flash("Name and message are required.", "danger")
        return redirect(url_for("index") + "#contact")

    db = get_db()
    db.execute(
        "INSERT INTO messages (sender_name, sender_email, message) VALUES (?, ?, ?)",
        (sender_name, sender_email, message),
    )
    db.commit()

    # Forward message directly to Gmail in background thread
    settings = get_settings(db)
    recipient = settings["email"] if settings and settings["email"] else None
    notify_new_message(sender_name, sender_email, message, recipient)

    if is_ajax:
        return jsonify({"success": True, "message": "Message sent! I'll get back to you soon."})

    flash("Message sent! I'll get back to you soon.", "success")
    return redirect(url_for("index") + "#contact")


# ---------------------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------------------

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin_dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session["admin_logged_in"] = True
            flash("Welcome back! Login successful.", "success")
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid credentials.", "danger")
    return render_template("admin/login.html")


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("index"))


@app.route("/admin")
@login_required
def admin_dashboard():
    db = get_db()
    projects = db.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
    return render_template("admin/dashboard.html", projects=projects)


# ---- Site Settings ----

@app.route("/admin/settings", methods=["GET", "POST"])
@login_required
def admin_settings():
    db = get_db()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        greeting = request.form.get("greeting", "").strip()
        tagline = request.form.get("tagline", "").strip()
        typing_texts = request.form.get("typing_texts", "").strip()
        bio = request.form.get("bio", "").strip()
        email = request.form.get("email", "").strip() or None
        github_url = request.form.get("github_url", "").strip() or None
        linkedin_url = request.form.get("linkedin_url", "").strip() or None
        twitter_url = request.form.get("twitter_url", "").strip() or None
        resume_url = request.form.get("resume_url", "").strip() or None
        color_primary = request.form.get("color_primary", "#6c63ff").strip()
        color_accent = request.form.get("color_accent", "#ff6b6b").strip()
        color_bg = request.form.get("color_bg", "#0f0f13").strip()
        color_surface = request.form.get("color_surface", "#1a1a23").strip()
        color_text = request.form.get("color_text", "#e4e4eb").strip()

        profile_photo = get_settings(db)["profile_photo"]
        if "profile_photo" in request.files:
            file = request.files["profile_photo"]
            if file and file.filename and allowed_file(file.filename):
                delete_upload(profile_photo)
                profile_photo = save_upload(file, "profile")
        if request.form.get("remove_photo") == "1":
            delete_upload(profile_photo)
            profile_photo = None

        db.execute(
            """UPDATE site_settings SET
                name=?, greeting=?, tagline=?, typing_texts=?, bio=?, profile_photo=?,
                email=?, github_url=?, linkedin_url=?, twitter_url=?, resume_url=?,
                color_primary=?, color_accent=?, color_bg=?, color_surface=?, color_text=?
               WHERE id=1""",
            (name, greeting, tagline, typing_texts, bio, profile_photo,
             email, github_url, linkedin_url, twitter_url, resume_url,
             color_primary, color_accent, color_bg, color_surface, color_text),
        )
        db.commit()
        flash("Site settings saved!", "success")
        return redirect(url_for("admin_settings"))

    return render_template("admin/settings.html", settings=get_settings(db))


# ---- Projects CRUD ----

@app.route("/admin/projects/add", methods=["GET", "POST"])
@login_required
def admin_add_project():
    if request.method == "POST":
        title = request.form["title"].strip()
        description = request.form["description"].strip()
        tech_stack = request.form["tech_stack"].strip()
        github_link = request.form.get("github_link", "").strip() or None
        live_demo_link = request.form.get("live_demo_link", "").strip() or None
        certificate_url = request.form.get("certificate_url", "").strip() or None

        image = None
        if "image" in request.files:
            file = request.files["image"]
            if file and file.filename and allowed_file(file.filename):
                image = save_upload(file, "project")

        if not title or not description or not tech_stack:
            flash("Title, Description, and Tech Stack are required.", "danger")
            return redirect(url_for("admin_add_project"))

        db = get_db()
        db.execute(
            """INSERT INTO projects
               (title, description, tech_stack, github_link, live_demo_link, certificate_url, image)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (title, description, tech_stack, github_link, live_demo_link, certificate_url, image),
        )
        db.commit()
        flash(f'Project "{title}" added!', "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("admin/project_form.html", project=None)


@app.route("/admin/projects/edit/<int:project_id>", methods=["GET", "POST"])
@login_required
def admin_edit_project(project_id):
    db = get_db()
    project = db.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if project is None:
        abort(404)

    if request.method == "POST":
        title = request.form["title"].strip()
        description = request.form["description"].strip()
        tech_stack = request.form["tech_stack"].strip()
        github_link = request.form.get("github_link", "").strip() or None
        live_demo_link = request.form.get("live_demo_link", "").strip() or None
        certificate_url = request.form.get("certificate_url", "").strip() or None

        image = project["image"]
        if "image" in request.files:
            file = request.files["image"]
            if file and file.filename and allowed_file(file.filename):
                delete_upload(image)
                image = save_upload(file, "project")
        if request.form.get("remove_image") == "1":
            delete_upload(image)
            image = None

        if not title or not description or not tech_stack:
            flash("Title, Description, and Tech Stack are required.", "danger")
            return redirect(url_for("admin_edit_project", project_id=project_id))

        db.execute(
            """UPDATE projects
               SET title=?, description=?, tech_stack=?, github_link=?,
                   live_demo_link=?, certificate_url=?, image=?
               WHERE id=?""",
            (title, description, tech_stack, github_link, live_demo_link,
             certificate_url, image, project_id),
        )
        db.commit()
        flash(f'Project "{title}" updated!', "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("admin/project_form.html", project=project)


@app.route("/admin/projects/delete/<int:project_id>", methods=["POST"])
@login_required
def admin_delete_project(project_id):
    db = get_db()
    project = db.execute("SELECT title FROM projects WHERE id = ?", (project_id,)).fetchone()
    if project is None:
        abort(404)
    delete_upload(project["image"])
    db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    db.commit()
    flash(f'Project "{project["title"]}" deleted.', "info")
    return redirect(url_for("admin_dashboard"))


# ---- Skills CRUD (Categorized chips / No percentages) ----

@app.route("/admin/skills")
@login_required
def admin_skills():
    db = get_db()
    skills = db.execute("SELECT * FROM skills ORDER BY category ASC, sort_order ASC, id ASC").fetchall()
    return render_template("admin/skills.html", skills=skills)


@app.route("/admin/skills/add", methods=["POST"])
@login_required
def admin_add_skill():
    name = request.form.get("name", "").strip()
    category = request.form.get("category", "General").strip() or "General"
    level_tag = request.form.get("level_tag", "").strip() or None
    icon = request.form.get("icon", "").strip() or None
    sort_order = int(request.form.get("sort_order", 0) or 0)

    if not name:
        flash("Skill name is required.", "danger")
        return redirect(url_for("admin_skills"))

    db = get_db()
    db.execute(
        "INSERT INTO skills (name, category, level_tag, icon, sort_order) VALUES (?, ?, ?, ?, ?)",
        (name, category, level_tag, icon, sort_order),
    )
    db.commit()
    flash(f'Skill "{name}" added!', "success")
    return redirect(url_for("admin_skills"))


@app.route("/admin/skills/edit/<int:skill_id>", methods=["POST"])
@login_required
def admin_edit_skill(skill_id):
    db = get_db()
    skill = db.execute("SELECT * FROM skills WHERE id = ?", (skill_id,)).fetchone()
    if skill is None:
        abort(404)

    name = request.form.get("name", "").strip()
    category = request.form.get("category", "General").strip() or "General"
    level_tag = request.form.get("level_tag", "").strip() or None
    icon = request.form.get("icon", "").strip() or None
    sort_order = int(request.form.get("sort_order", 0) or 0)

    if not name:
        flash("Skill name is required.", "danger")
        return redirect(url_for("admin_skills"))

    db.execute(
        "UPDATE skills SET name=?, category=?, level_tag=?, icon=?, sort_order=? WHERE id=?",
        (name, category, level_tag, icon, sort_order, skill_id),
    )
    db.commit()
    flash(f'Skill "{name}" updated!', "success")
    return redirect(url_for("admin_skills"))


@app.route("/admin/skills/delete/<int:skill_id>", methods=["POST"])
@login_required
def admin_delete_skill(skill_id):
    db = get_db()
    skill = db.execute("SELECT name FROM skills WHERE id = ?", (skill_id,)).fetchone()
    if skill is None:
        abort(404)
    db.execute("DELETE FROM skills WHERE id = ?", (skill_id,))
    db.commit()
    flash(f'Skill "{skill["name"]}" deleted.', "info")
    return redirect(url_for("admin_skills"))


# ---- Messages ----

@app.route("/admin/messages")
@login_required
def admin_messages():
    db = get_db()
    messages = db.execute("SELECT * FROM messages ORDER BY created_at DESC").fetchall()
    # Mark all as read
    db.execute("UPDATE messages SET is_read = 1 WHERE is_read = 0")
    db.commit()
    return render_template("admin/messages.html", messages=messages)


@app.route("/admin/messages/delete/<int:msg_id>", methods=["POST"])
@login_required
def admin_delete_message(msg_id):
    db = get_db()
    db.execute("DELETE FROM messages WHERE id = ?", (msg_id,))
    db.commit()
    flash("Message deleted.", "info")
    return redirect(url_for("admin_messages"))


# ---------------------------------------------------------------------------
# Bootstrap & run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    init_db()
    app.run(debug=True, port=5000)
