"""
Ahmed Bosha — Personal Portfolio & CMS (Complete 9-Component Architecture)
Aligned with the NTI Portfolio Framework:
1. Cover / Hero   2. About Me   3. Education   4. Skills & Tech Stack
5. Work Experience & Training   6. Offered Services   7. Featured Projects
8. Achievements & Certifications   9. Testimonials   10. Contact & CTA
"""

import os
import sqlite3
import functools
import uuid
import smtplib
import threading
import json
import urllib.request
import urllib.error
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

# Mail configuration
MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
MAIL_RECIPIENT = os.environ.get("MAIL_RECIPIENT")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")

# Admin credentials
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
# Email Forwarding (Resend HTTPS API & Gmail SMTP fallback)
# ---------------------------------------------------------------------------

def send_via_resend(api_key, to_email, sender_name, sender_email, message_content):
    """Send email over HTTPS via Resend API (Never blocked by cloud firewalls)."""
    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
        "User-Agent": "Portfolio-App/1.0",
    }
    payload = {
        "from": "Portfolio Contact <onboarding@resend.dev>",
        "to": [to_email],
        "subject": f"🔔 New Portfolio Message from {sender_name}",
        "reply_to": sender_email if sender_email else None,
        "html": f"""
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
        """,
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=12) as response:
            res_body = response.read().decode("utf-8")
            print(f"[RESEND SUCCESS] Forwarded to {to_email}: {res_body}")
            return True, f"Sent via Resend API to {to_email}"
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8")
        print(f"[RESEND HTTP ERROR] {err}")
        return False, f"Resend API Error: {err}"
    except Exception as e:
        print(f"[RESEND ERROR] {e}")
        return False, f"Resend Connection Error: {e}"


def send_email_core(sender_name, sender_email, message_content, recipient_email=None):
    """Core function to send email via HTTPS API (Resend) or Gmail SMTP fallback."""
    resend_key = os.environ.get("RESEND_API_KEY", "").strip()
    mail_user = os.environ.get("MAIL_USERNAME", "").strip()
    mail_pass = os.environ.get("MAIL_PASSWORD", "").strip()

    to_email = (recipient_email or os.environ.get("MAIL_RECIPIENT") or mail_user or "ahmedbosha2566@gmail.com").strip()

    if resend_key:
        return send_via_resend(resend_key, to_email, sender_name, sender_email, message_content)

    if not mail_user or not mail_pass:
        return False, "Neither RESEND_API_KEY nor MAIL_USERNAME/PASSWORD are configured in environment."

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🔔 New Portfolio Message from {sender_name}"
    msg["From"] = f"Portfolio <{mail_user}>"
    msg["To"] = to_email
    if sender_email:
        msg["Reply-To"] = sender_email.strip()

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

    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10)
        server.login(mail_user, mail_pass)
        server.send_message(msg)
        server.quit()
        print(f"[MAIL SUCCESS (SSL 465)] Notification forwarded to {to_email}")
        return True, f"Sent via SSL to {to_email}"
    except Exception as e_ssl:
        try:
            server = smtplib.SMTP("smtp.gmail.com", 587, timeout=10)
            server.starttls()
            server.login(mail_user, mail_pass)
            server.send_message(msg)
            server.quit()
            print(f"[MAIL SUCCESS (TLS 587)] Notification forwarded to {to_email}")
            return True, f"Sent via TLS to {to_email}"
        except Exception as e_tls:
            err_msg = f"Network is blocking SMTP ports on Render Free. Please use RESEND_API_KEY. Details: {e_ssl}"
            print(f"[MAIL ERROR] {err_msg}")
            return False, err_msg


def notify_new_message(sender_name, sender_email, message_content, recipient_email=None):
    """Fire and forget email notification thread."""
    thread = threading.Thread(
        target=send_email_core,
        args=(sender_name, sender_email, message_content, recipient_email),
    )
    thread.daemon = True
    thread.start()


# ---------------------------------------------------------------------------
# Database Helpers & Initialization
# ---------------------------------------------------------------------------

def get_db():
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
    if db is None:
        db = get_db()
    return db.execute("SELECT * FROM site_settings WHERE id = 1").fetchone()


def init_db():
    """Create all 9 tables and insert high quality seed data."""
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row

    db.executescript("""
        CREATE TABLE IF NOT EXISTS site_settings (
            id              INTEGER PRIMARY KEY CHECK (id = 1),
            name            TEXT    DEFAULT 'Ahmed Bosha',
            greeting        TEXT    DEFAULT 'Hi, I''m',
            tagline         TEXT    DEFAULT 'Engineering Student & Software Developer',
            typing_texts    TEXT    DEFAULT 'Engineering Student,Software Developer,Problem Solver,Automation Enthusiast',
            bio             TEXT    DEFAULT 'Class of 2029. Passionate about automation, system analysis, and reverse engineering. I build tools that turn complex workflows into clean, efficient solutions.',
            profile_photo   TEXT,
            email           TEXT    DEFAULT 'ahmedbosha2566@gmail.com',
            github_url      TEXT    DEFAULT 'https://github.com/AhmedBosha',
            linkedin_url    TEXT,
            twitter_url     TEXT,
            resume_url      TEXT,
            color_primary   TEXT    DEFAULT '#6c63ff',
            color_accent    TEXT    DEFAULT '#ff6b6b',
            color_bg        TEXT    DEFAULT '#0c0c12',
            color_surface   TEXT    DEFAULT '#161622',
            color_text      TEXT    DEFAULT '#f0f0f8'
        );

        CREATE TABLE IF NOT EXISTS education (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            institution         TEXT    NOT NULL,
            degree              TEXT    NOT NULL,
            field_of_study      TEXT    NOT NULL,
            start_year          TEXT    NOT NULL,
            end_year            TEXT    NOT NULL,
            grade_or_details    TEXT,
            sort_order          INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS skills (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            category    TEXT    NOT NULL DEFAULT 'Programming & Backend',
            level_tag   TEXT,
            icon        TEXT,
            sort_order  INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS experiences (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT    NOT NULL,
            company     TEXT    NOT NULL,
            location    TEXT,
            start_date  TEXT    NOT NULL,
            end_date    TEXT,
            description TEXT    NOT NULL,
            is_current  INTEGER DEFAULT 0,
            sort_order  INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS services (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT    NOT NULL,
            description TEXT    NOT NULL,
            icon        TEXT    DEFAULT '⚙️',
            sort_order  INTEGER DEFAULT 0
        );

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

        CREATE TABLE IF NOT EXISTS achievements (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            title           TEXT    NOT NULL,
            issuer          TEXT,
            date_earned     TEXT,
            credential_url  TEXT,
            icon            TEXT    DEFAULT '🏆',
            description     TEXT,
            sort_order      INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS testimonials (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name     TEXT    NOT NULL,
            client_role     TEXT    NOT NULL,
            quote           TEXT    NOT NULL,
            avatar          TEXT,
            sort_order      INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS messages (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_name  TEXT    NOT NULL,
            sender_email TEXT    NOT NULL,
            message      TEXT    NOT NULL,
            is_read      INTEGER DEFAULT 0,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # ---- 1. Seed site_settings ----
    if db.execute("SELECT COUNT(*) FROM site_settings").fetchone()[0] == 0:
        db.execute("INSERT INTO site_settings (id) VALUES (1)")
        db.commit()

    # ---- 2. Seed Education ----
    if db.execute("SELECT COUNT(*) FROM education").fetchone()[0] == 0:
        db.executemany(
            "INSERT INTO education (institution, degree, field_of_study, start_year, end_year, grade_or_details, sort_order) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    "Faculty of Engineering",
                    "Bachelor of Engineering (B.Eng.)",
                    "Computer & Systems Engineering",
                    "2024",
                    "2029 (Expected)",
                    "Class of 2029. Focus on Systems Analysis, Low-Level Architecture & Automation Pipelines.",
                    1,
                ),
            ],
        )
        db.commit()

    # ---- 3. Seed Skills ----
    if db.execute("SELECT COUNT(*) FROM skills").fetchone()[0] == 0:
        db.executemany(
            "INSERT INTO skills (name, category, level_tag, icon, sort_order) VALUES (?, ?, ?, ?, ?)",
            [
                ("Python", "Programming & Backend", "Advanced", "🐍", 1),
                ("C / C++", "Programming & Backend", "Core", "⚡", 2),
                ("Flask", "Programming & Backend", "Framework", "🌐", 3),
                ("SQLite / SQL", "Programming & Backend", "Database", "🗄️", 4),
                ("REST APIs", "Programming & Backend", "Architecture", "🔌", 5),

                ("Reverse Engineering", "Security & Systems", "Specialty", "🔬", 6),
                ("Frida", "Security & Systems", "Instrumentation", "💉", 7),
                ("Shizuku", "Security & Systems", "Android", "📱", 8),
                ("Binary Analysis", "Security & Systems", "Security", "🔍", 9),
                ("Linux & Shell", "Security & Systems", "Environment", "🐧", 10),

                ("Automation Scripts", "Tools & Automation", "Workflow", "⚙️", 11),
                ("Git & GitHub", "Tools & Automation", "VCS", "📦", 12),
                ("CSV Data Pipelines", "Tools & Automation", "Data", "📊", 13),
                ("CLI Development", "Tools & Automation", "Tooling", "💻", 14),

                ("System Analysis", "Core Engineering", "Mindset", "📐", 15),
                ("Problem Solving", "Core Engineering", "Strengths", "🧩", 16),
                ("Data Structures", "Core Engineering", "CS Fundamentals", "🌳", 17),
            ],
        )
        db.commit()

    # ---- 4. Seed Experiences ----
    if db.execute("SELECT COUNT(*) FROM experiences").fetchone()[0] == 0:
        db.executemany(
            "INSERT INTO experiences (title, company, location, start_date, end_date, description, is_current, sort_order) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    "Mobile Security & Reverse Engineering Researcher",
                    "Independent Research",
                    "Remote",
                    "2024",
                    "Present",
                    "Engineered automation tools for Android binary library inspection, utilizing Frida and Shizuku instrumentation to extract dynamic memory structures (GNames, GWorld) and streamline reverse engineering workflows.",
                    1,
                    1,
                ),
                (
                    "Software Systems & Automation Engineering Trainee",
                    "National Telecommunication Institute (NTI)",
                    "Egypt",
                    "2025",
                    "2025",
                    "Completed intensive practical training in modern software architecture, backend system design, database integration, and building automated data manipulation pipelines.",
                    0,
                    2,
                ),
            ],
        )
        db.commit()

    # ---- 5. Seed Services ----
    if db.execute("SELECT COUNT(*) FROM services").fetchone()[0] == 0:
        db.executemany(
            "INSERT INTO services (title, description, icon, sort_order) VALUES (?, ?, ?, ?)",
            [
                (
                    "Workflow Automation & Pipelines",
                    "Developing bespoke automation scripts, scheduled tasks, and structured CSV/database data pipelines that eliminate repetitive manual workflows.",
                    "⚙️",
                    1,
                ),
                (
                    "Reverse Engineering & Binary Analysis",
                    "Security research, static/dynamic inspection of compiled native binaries, memory offset extraction, and instrumentation using Frida & Shizuku.",
                    "🔬",
                    2,
                ),
                (
                    "Backend APIs & Custom Web Tooling",
                    "Designing fast, lightweight, and maintainable Python/Flask backend applications, RESTful endpoints, and custom administrative CMS dashboards.",
                    "🌐",
                    3,
                ),
                (
                    "CLI Tool Development",
                    "Creating robust, ergonomic command-line applications and developer tools with structured data manipulation and high-speed execution.",
                    "💻",
                    4,
                ),
            ],
        )
        db.commit()

    # ---- 6. Seed Projects ----
    if db.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 0:
        db.executemany(
            """INSERT INTO projects
               (title, description, tech_stack, github_link, live_demo_link, certificate_url, image)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    "HospitalSystem",
                    "A CLI-based appointment management application demonstrating dynamic CSV file manipulation and structured data storage. Built to streamline patient scheduling with clean data pipelines.",
                    "Python, CSV, CLI, Data Structures",
                    "https://github.com/AhmedBosha/HospitalSystem",
                    None, None, None,
                ),
                (
                    "Mobile Static Analysis",
                    "Automation scripts for reverse engineering binary libraries, utilizing instrumentation tools like Shizuku to extract memory offsets (e.g., GNames, GWorld). Designed to speed up mobile security research workflows.",
                    "Python, Frida, Shizuku, Reverse Engineering",
                    "https://github.com/AhmedBosha/MobileStaticAnalysis",
                    None, None, None,
                ),
            ],
        )
        db.commit()

    # ---- 7. Seed Achievements ----
    if db.execute("SELECT COUNT(*) FROM achievements").fetchone()[0] == 0:
        db.executemany(
            "INSERT INTO achievements (title, issuer, date_earned, credential_url, icon, description, sort_order) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    "NTI Software Engineering & Foundations",
                    "National Telecommunication Institute (NTI)",
                    "2025",
                    "https://nti.sci.eg",
                    "🎓",
                    "Awarded for comprehensive practical coursework in software engineering, backend paradigms, and modern system development.",
                    1,
                ),
                (
                    "Competitive Problem Solving Milestone",
                    "Algorithms & Data Structures",
                    "2024 - 2025",
                    None,
                    "🏆",
                    "Solved over 150+ algorithmic challenges and problem-solving puzzles focusing on time/space complexity optimization.",
                    2,
                ),
            ],
        )
        db.commit()

    # ---- 8. Seed Testimonials ----
    if db.execute("SELECT COUNT(*) FROM testimonials").fetchone()[0] == 0:
        db.executemany(
            "INSERT INTO testimonials (client_name, client_role, quote, avatar, sort_order) VALUES (?, ?, ?, ?, ?)",
            [
                (
                    "Eng. Mohamed Tarek",
                    "Software Systems Instructor & Mentor",
                    "Ahmed demonstrates exceptional problem-solving depth and passion for low-level systems and automation. His ability to turn complex logic into clean code is outstanding.",
                    None,
                    1,
                ),
            ],
        )
        db.commit()

    db.close()
    print("[OK] Database initialized with all 9 NTI components.")


# ---------------------------------------------------------------------------
# Context processor
# ---------------------------------------------------------------------------

@app.context_processor
def inject_globals():
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
    
    # 1. Projects
    projects = db.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
    
    # 2. Skills grouped by category
    skills_raw = db.execute("SELECT * FROM skills ORDER BY category ASC, sort_order ASC, id ASC").fetchall()
    skill_categories = {}
    for s in skills_raw:
        cat = s["category"] or "General"
        if cat not in skill_categories:
            skill_categories[cat] = []
        skill_categories[cat].append(s)

    # 3. Education
    education_list = db.execute("SELECT * FROM education ORDER BY sort_order ASC, start_year DESC").fetchall()

    # 4. Work Experience & Training
    experiences_list = db.execute("SELECT * FROM experiences ORDER BY sort_order ASC, id ASC").fetchall()

    # 5. Services
    services_list = db.execute("SELECT * FROM services ORDER BY sort_order ASC, id ASC").fetchall()

    # 6. Achievements & Certifications
    achievements_list = db.execute("SELECT * FROM achievements ORDER BY sort_order ASC, id ASC").fetchall()

    # 7. Testimonials
    testimonials_list = db.execute("SELECT * FROM testimonials ORDER BY sort_order ASC, id ASC").fetchall()

    return render_template(
        "index.html",
        projects=projects,
        skill_categories=skill_categories,
        education_list=education_list,
        experiences_list=experiences_list,
        services_list=services_list,
        achievements_list=achievements_list,
        testimonials_list=testimonials_list,
    )


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

    if not sender_name or not sender_email or not message:
        if is_ajax:
            return jsonify({"success": False, "error": "Name, email, and message are required."}), 400
        flash("Name, email, and message are required.", "danger")
        return redirect(url_for("index") + "#contact")

    db = get_db()
    db.execute(
        "INSERT INTO messages (sender_name, sender_email, message) VALUES (?, ?, ?)",
        (sender_name, sender_email, message),
    )
    db.commit()

    settings = get_settings(db)
    recipient = settings["email"] if settings and settings["email"] else None
    notify_new_message(sender_name, sender_email, message, recipient)

    if is_ajax:
        return jsonify({"success": True, "message": "Message sent! I'll get back to you soon."})

    flash("Message sent! I'll get back to you soon.", "success")
    return redirect(url_for("index") + "#contact")


# ---------------------------------------------------------------------------
# Admin Auth & Dashboard Hub
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


# ---------------------------------------------------------------------------
# Admin: Site Settings
# ---------------------------------------------------------------------------

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
        color_bg = request.form.get("color_bg", "#0c0c12").strip()
        color_surface = request.form.get("color_surface", "#161622").strip()
        color_text = request.form.get("color_text", "#f0f0f8").strip()

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


# ---------------------------------------------------------------------------
# Admin: Projects CRUD
# ---------------------------------------------------------------------------

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
    project = db.execute("SELECT title, image FROM projects WHERE id = ?", (project_id,)).fetchone()
    if project is None:
        abort(404)
    delete_upload(project["image"])
    db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    db.commit()
    flash(f'Project "{project["title"]}" deleted.', "info")
    return redirect(url_for("admin_dashboard"))


# ---------------------------------------------------------------------------
# Admin: Skills CRUD
# ---------------------------------------------------------------------------

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
    category = request.form.get("category", "Programming & Backend").strip()
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
    name = request.form.get("name", "").strip()
    category = request.form.get("category", "Programming & Backend").strip()
    level_tag = request.form.get("level_tag", "").strip() or None
    icon = request.form.get("icon", "").strip() or None
    sort_order = int(request.form.get("sort_order", 0) or 0)

    if not name:
        flash("Skill name is required.", "danger")
        return redirect(url_for("admin_skills"))

    db = get_db()
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
    if skill:
        db.execute("DELETE FROM skills WHERE id = ?", (skill_id,))
        db.commit()
        flash(f'Skill "{skill["name"]}" deleted.', "info")
    return redirect(url_for("admin_skills"))


# ---------------------------------------------------------------------------
# Admin: Education CRUD
# ---------------------------------------------------------------------------

@app.route("/admin/education")
@login_required
def admin_education():
    db = get_db()
    items = db.execute("SELECT * FROM education ORDER BY sort_order ASC, start_year DESC").fetchall()
    return render_template("admin/education.html", education_list=items)


@app.route("/admin/education/add", methods=["POST"])
@login_required
def admin_add_education():
    institution = request.form.get("institution", "").strip()
    degree = request.form.get("degree", "").strip()
    field_of_study = request.form.get("field_of_study", "").strip()
    start_year = request.form.get("start_year", "").strip()
    end_year = request.form.get("end_year", "").strip()
    grade_or_details = request.form.get("grade_or_details", "").strip() or None
    sort_order = int(request.form.get("sort_order", 0) or 0)

    if not institution or not degree or not field_of_study:
        flash("Institution, Degree, and Field of Study are required.", "danger")
        return redirect(url_for("admin_education"))

    db = get_db()
    db.execute(
        """INSERT INTO education (institution, degree, field_of_study, start_year, end_year, grade_or_details, sort_order)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (institution, degree, field_of_study, start_year, end_year, grade_or_details, sort_order),
    )
    db.commit()
    flash("Education entry added!", "success")
    return redirect(url_for("admin_education"))


@app.route("/admin/education/edit/<int:item_id>", methods=["POST"])
@login_required
def admin_edit_education(item_id):
    institution = request.form.get("institution", "").strip()
    degree = request.form.get("degree", "").strip()
    field_of_study = request.form.get("field_of_study", "").strip()
    start_year = request.form.get("start_year", "").strip()
    end_year = request.form.get("end_year", "").strip()
    grade_or_details = request.form.get("grade_or_details", "").strip() or None
    sort_order = int(request.form.get("sort_order", 0) or 0)

    if not institution or not degree:
        flash("Institution and Degree are required.", "danger")
        return redirect(url_for("admin_education"))

    db = get_db()
    db.execute(
        """UPDATE education SET institution=?, degree=?, field_of_study=?, start_year=?, end_year=?, grade_or_details=?, sort_order=?
           WHERE id=?""",
        (institution, degree, field_of_study, start_year, end_year, grade_or_details, sort_order, item_id),
    )
    db.commit()
    flash("Education entry updated!", "success")
    return redirect(url_for("admin_education"))


@app.route("/admin/education/delete/<int:item_id>", methods=["POST"])
@login_required
def admin_delete_education(item_id):
    db = get_db()
    db.execute("DELETE FROM education WHERE id = ?", (item_id,))
    db.commit()
    flash("Education entry deleted.", "info")
    return redirect(url_for("admin_education"))


# ---------------------------------------------------------------------------
# Admin: Work Experience & Training CRUD
# ---------------------------------------------------------------------------

@app.route("/admin/experience")
@login_required
def admin_experience():
    db = get_db()
    items = db.execute("SELECT * FROM experiences ORDER BY sort_order ASC, id ASC").fetchall()
    return render_template("admin/experience.html", experiences_list=items)


@app.route("/admin/experience/add", methods=["POST"])
@login_required
def admin_add_experience():
    title = request.form.get("title", "").strip()
    company = request.form.get("company", "").strip()
    location = request.form.get("location", "").strip() or None
    start_date = request.form.get("start_date", "").strip()
    end_date = request.form.get("end_date", "").strip() or None
    description = request.form.get("description", "").strip()
    is_current = 1 if request.form.get("is_current") == "1" else 0
    sort_order = int(request.form.get("sort_order", 0) or 0)

    if not title or not company or not description:
        flash("Role Title, Organization, and Description are required.", "danger")
        return redirect(url_for("admin_experience"))

    db = get_db()
    db.execute(
        """INSERT INTO experiences (title, company, location, start_date, end_date, description, is_current, sort_order)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (title, company, location, start_date, end_date, description, is_current, sort_order),
    )
    db.commit()
    flash(f'Experience "{title}" added!', "success")
    return redirect(url_for("admin_experience"))


@app.route("/admin/experience/edit/<int:item_id>", methods=["POST"])
@login_required
def admin_edit_experience(item_id):
    title = request.form.get("title", "").strip()
    company = request.form.get("company", "").strip()
    location = request.form.get("location", "").strip() or None
    start_date = request.form.get("start_date", "").strip()
    end_date = request.form.get("end_date", "").strip() or None
    description = request.form.get("description", "").strip()
    is_current = 1 if request.form.get("is_current") == "1" else 0
    sort_order = int(request.form.get("sort_order", 0) or 0)

    if not title or not company or not description:
        flash("Role Title, Organization, and Description are required.", "danger")
        return redirect(url_for("admin_experience"))

    db = get_db()
    db.execute(
        """UPDATE experiences SET title=?, company=?, location=?, start_date=?, end_date=?, description=?, is_current=?, sort_order=?
           WHERE id=?""",
        (title, company, location, start_date, end_date, description, is_current, sort_order, item_id),
    )
    db.commit()
    flash(f'Experience "{title}" updated!', "success")
    return redirect(url_for("admin_experience"))


@app.route("/admin/experience/delete/<int:item_id>", methods=["POST"])
@login_required
def admin_delete_experience(item_id):
    db = get_db()
    db.execute("DELETE FROM experiences WHERE id = ?", (item_id,))
    db.commit()
    flash("Experience entry deleted.", "info")
    return redirect(url_for("admin_experience"))


# ---------------------------------------------------------------------------
# Admin: Offered Services CRUD
# ---------------------------------------------------------------------------

@app.route("/admin/services")
@login_required
def admin_services():
    db = get_db()
    items = db.execute("SELECT * FROM services ORDER BY sort_order ASC, id ASC").fetchall()
    return render_template("admin/services.html", services_list=items)


@app.route("/admin/services/add", methods=["POST"])
@login_required
def admin_add_service():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    icon = request.form.get("icon", "⚙️").strip() or "⚙️"
    sort_order = int(request.form.get("sort_order", 0) or 0)

    if not title or not description:
        flash("Service Title and Description are required.", "danger")
        return redirect(url_for("admin_services"))

    db = get_db()
    db.execute(
        "INSERT INTO services (title, description, icon, sort_order) VALUES (?, ?, ?, ?)",
        (title, description, icon, sort_order),
    )
    db.commit()
    flash(f'Service "{title}" added!', "success")
    return redirect(url_for("admin_services"))


@app.route("/admin/services/edit/<int:item_id>", methods=["POST"])
@login_required
def admin_edit_service(item_id):
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    icon = request.form.get("icon", "⚙️").strip() or "⚙️"
    sort_order = int(request.form.get("sort_order", 0) or 0)

    if not title or not description:
        flash("Service Title and Description are required.", "danger")
        return redirect(url_for("admin_services"))

    db = get_db()
    db.execute(
        "UPDATE services SET title=?, description=?, icon=?, sort_order=? WHERE id=?",
        (title, description, icon, sort_order, item_id),
    )
    db.commit()
    flash(f'Service "{title}" updated!', "success")
    return redirect(url_for("admin_services"))


@app.route("/admin/services/delete/<int:item_id>", methods=["POST"])
@login_required
def admin_delete_service(item_id):
    db = get_db()
    db.execute("DELETE FROM services WHERE id = ?", (item_id,))
    db.commit()
    flash("Service deleted.", "info")
    return redirect(url_for("admin_services"))


# ---------------------------------------------------------------------------
# Admin: Achievements & Certifications CRUD
# ---------------------------------------------------------------------------

@app.route("/admin/achievements")
@login_required
def admin_achievements():
    db = get_db()
    items = db.execute("SELECT * FROM achievements ORDER BY sort_order ASC, id ASC").fetchall()
    return render_template("admin/achievements.html", achievements_list=items)


@app.route("/admin/achievements/add", methods=["POST"])
@login_required
def admin_add_achievement():
    title = request.form.get("title", "").strip()
    issuer = request.form.get("issuer", "").strip() or None
    date_earned = request.form.get("date_earned", "").strip() or None
    credential_url = request.form.get("credential_url", "").strip() or None
    icon = request.form.get("icon", "🏆").strip() or "🏆"
    description = request.form.get("description", "").strip() or None
    sort_order = int(request.form.get("sort_order", 0) or 0)

    if not title:
        flash("Achievement Title is required.", "danger")
        return redirect(url_for("admin_achievements"))

    db = get_db()
    db.execute(
        """INSERT INTO achievements (title, issuer, date_earned, credential_url, icon, description, sort_order)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (title, issuer, date_earned, credential_url, icon, description, sort_order),
    )
    db.commit()
    flash(f'Achievement "{title}" added!', "success")
    return redirect(url_for("admin_achievements"))


@app.route("/admin/achievements/edit/<int:item_id>", methods=["POST"])
@login_required
def admin_edit_achievement(item_id):
    title = request.form.get("title", "").strip()
    issuer = request.form.get("issuer", "").strip() or None
    date_earned = request.form.get("date_earned", "").strip() or None
    credential_url = request.form.get("credential_url", "").strip() or None
    icon = request.form.get("icon", "🏆").strip() or "🏆"
    description = request.form.get("description", "").strip() or None
    sort_order = int(request.form.get("sort_order", 0) or 0)

    if not title:
        flash("Achievement Title is required.", "danger")
        return redirect(url_for("admin_achievements"))

    db = get_db()
    db.execute(
        """UPDATE achievements SET title=?, issuer=?, date_earned=?, credential_url=?, icon=?, description=?, sort_order=?
           WHERE id=?""",
        (title, issuer, date_earned, credential_url, icon, description, sort_order, item_id),
    )
    db.commit()
    flash(f'Achievement "{title}" updated!', "success")
    return redirect(url_for("admin_achievements"))


@app.route("/admin/achievements/delete/<int:item_id>", methods=["POST"])
@login_required
def admin_delete_achievement(item_id):
    db = get_db()
    db.execute("DELETE FROM achievements WHERE id = ?", (item_id,))
    db.commit()
    flash("Achievement deleted.", "info")
    return redirect(url_for("admin_achievements"))


# ---------------------------------------------------------------------------
# Admin: Testimonials CRUD
# ---------------------------------------------------------------------------

@app.route("/admin/testimonials")
@login_required
def admin_testimonials():
    db = get_db()
    items = db.execute("SELECT * FROM testimonials ORDER BY sort_order ASC, id ASC").fetchall()
    return render_template("admin/testimonials.html", testimonials_list=items)


@app.route("/admin/testimonials/add", methods=["POST"])
@login_required
def admin_add_testimonial():
    client_name = request.form.get("client_name", "").strip()
    client_role = request.form.get("client_role", "").strip()
    quote = request.form.get("quote", "").strip()
    avatar = request.form.get("avatar", "").strip() or None
    sort_order = int(request.form.get("sort_order", 0) or 0)

    if not client_name or not quote:
        flash("Client/Mentor Name and Recommendation Quote are required.", "danger")
        return redirect(url_for("admin_testimonials"))

    db = get_db()
    db.execute(
        "INSERT INTO testimonials (client_name, client_role, quote, avatar, sort_order) VALUES (?, ?, ?, ?, ?)",
        (client_name, client_role, quote, avatar, sort_order),
    )
    db.commit()
    flash(f'Testimonial from "{client_name}" added!', "success")
    return redirect(url_for("admin_testimonials"))


@app.route("/admin/testimonials/edit/<int:item_id>", methods=["POST"])
@login_required
def admin_edit_testimonial(item_id):
    client_name = request.form.get("client_name", "").strip()
    client_role = request.form.get("client_role", "").strip()
    quote = request.form.get("quote", "").strip()
    avatar = request.form.get("avatar", "").strip() or None
    sort_order = int(request.form.get("sort_order", 0) or 0)

    if not client_name or not quote:
        flash("Client/Mentor Name and Recommendation Quote are required.", "danger")
        return redirect(url_for("admin_testimonials"))

    db = get_db()
    db.execute(
        "UPDATE testimonials SET client_name=?, client_role=?, quote=?, avatar=?, sort_order=? WHERE id=?",
        (client_name, client_role, quote, avatar, sort_order, item_id),
    )
    db.commit()
    flash(f'Testimonial from "{client_name}" updated!', "success")
    return redirect(url_for("admin_testimonials"))


@app.route("/admin/testimonials/delete/<int:item_id>", methods=["POST"])
@login_required
def admin_delete_testimonial(item_id):
    db = get_db()
    db.execute("DELETE FROM testimonials WHERE id = ?", (item_id,))
    db.commit()
    flash("Testimonial deleted.", "info")
    return redirect(url_for("admin_testimonials"))


# ---------------------------------------------------------------------------
# Admin: Messages
# ---------------------------------------------------------------------------

@app.route("/admin/messages")
@login_required
def admin_messages():
    db = get_db()
    messages = db.execute("SELECT * FROM messages ORDER BY created_at DESC").fetchall()
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


@app.route("/admin/test-email", methods=["POST"])
@login_required
def admin_test_email():
    """Send a diagnostic test email to verify credentials."""
    db = get_db()
    settings = get_settings(db)
    recipient = settings["email"] if settings and settings["email"] else None

    success, result_msg = send_email_core(
        sender_name="Portfolio System Test",
        sender_email="test@portfolio.local",
        message_content="🎉 Great news! Your email notification forwarding is connected and working 100% with your Portfolio Web App!",
        recipient_email=recipient,
    )

    if success:
        flash(f"✅ Success! {result_msg}", "success")
    else:
        flash(f"❌ Diagnostic: {result_msg}", "danger")

    return redirect(url_for("admin_messages"))


# ---------------------------------------------------------------------------
# Bootstrap & run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    init_db()
    app.run(debug=True, port=5000)
