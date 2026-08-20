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
import datetime
import random
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

def send_custom_email(to_email, subject, html_body, reply_to=None):
    """Core unified email sender: Tries Resend API (HTTPS), then falls back to Gmail SMTP (SSL/TLS)."""
    resend_key = os.environ.get("RESEND_API_KEY", "").strip()
    brevo_key = (
        os.environ.get("BREVO_API_KEY")
        or os.environ.get("BREVO_KEY")
        or os.environ.get("SENDINBLUE_API_KEY")
        or os.environ.get("BREVO_API_TOKEN")
        or ""
    ).strip()
    mail_user = os.environ.get("MAIL_USERNAME", "").strip()
    mail_pass = os.environ.get("MAIL_PASSWORD", "").strip()

    if not to_email:
        to_email = (os.environ.get("MAIL_RECIPIENT") or mail_user or "ahmedbosha2566@gmail.com").strip()

    # 1. Try Brevo HTTPS API (100% Free - 300 emails/day to ANY recipient in the world over HTTPS port 443!)
    if brevo_key:
        brevo_key_clean = brevo_key.strip("'\" \t\r\n")
        try:
            url = "https://api.brevo.com/v3/smtp/email"
            headers = {
                "api-key": brevo_key_clean,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "Portfolio-App/1.0",
            }
            sender_email_val = (
                os.environ.get("BREVO_SENDER_EMAIL")
                or mail_user
                or os.environ.get("MAIL_RECIPIENT")
                or "ahmedyoussefmansourbosha@gmail.com"
            ).strip("'\" \t\r\n")
            payload = {
                "sender": {"name": "BoshaCraft", "email": sender_email_val},
                "to": [{"email": to_email}],
                "subject": subject,
                "htmlContent": html_body,
            }
            if reply_to:
                payload["replyTo"] = {"email": reply_to.strip()}

            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=12) as response:
                res_body = response.read().decode("utf-8")
                print(f"[BREVO SUCCESS] Sent '{subject}' → {to_email}: {res_body}")
                return True, f"Sent via Brevo to {to_email}"
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8")
            print(f"[BREVO HTTP ERROR {e.code}] {err}")
            # Automatic retry with alternative sender email if Brevo rejects sender
            alt_senders = ["ahmedyoussefmansourbosha@gmail.com", "ahmedbosha2566@gmail.com"]
            for alt in alt_senders:
                if alt != sender_email_val:
                    try:
                        print(f"[BREVO RETRY] Retrying Brevo with sender '{alt}'...")
                        payload["sender"]["email"] = alt
                        data = json.dumps(payload).encode("utf-8")
                        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
                        with urllib.request.urlopen(req, timeout=12) as response:
                            res_body = response.read().decode("utf-8")
                            print(f"[BREVO RETRY SUCCESS] Sent '{subject}' → {to_email}: {res_body}")
                            return True, f"Sent via Brevo to {to_email}"
                    except Exception as ex:
                        print(f"[BREVO RETRY ERROR for {alt}] {ex}")
        except Exception as e:
            print(f"[BREVO ERROR] {e}")

    # 2. Try Resend HTTPS API if key configured
    if resend_key:
        try:
            url = "https://api.resend.com/emails"
            headers = {
                "Authorization": f"Bearer {resend_key}",
                "Content-Type": "application/json",
                "User-Agent": "Portfolio-App/1.0",
            }
            payload = {
                "from": "BoshaCraft <onboarding@resend.dev>",
                "to": [to_email],
                "subject": subject,
                "html": html_body,
            }
            if reply_to:
                payload["reply_to"] = reply_to.strip()

            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=12) as response:
                res_body = response.read().decode("utf-8")
                print(f"[RESEND SUCCESS] Sent '{subject}' → {to_email}: {res_body}")
                return True, f"Sent via Resend to {to_email}"
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8")
            print(f"[RESEND HTTP ERROR {e.code}] {err}")
        except Exception as e:
            print(f"[RESEND ERROR] {e}")

    # 2. Try Gmail SMTP Fallback (SSL port 465 or TLS port 587)
    if mail_user and mail_pass:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"BoshaCraft <{mail_user}>"
        msg["To"] = to_email
        if reply_to:
            msg["Reply-To"] = reply_to.strip()
        msg.attach(MIMEText(html_body, "html"))

        try:
            server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10)
            server.login(mail_user, mail_pass)
            server.send_message(msg)
            server.quit()
            print(f"[SMTP SSL SUCCESS] Sent '{subject}' → {to_email}")
            return True, f"Sent via SMTP SSL to {to_email}"
        except Exception as e_ssl:
            try:
                server = smtplib.SMTP("smtp.gmail.com", 587, timeout=10)
                server.starttls()
                server.login(mail_user, mail_pass)
                server.send_message(msg)
                server.quit()
                print(f"[SMTP TLS SUCCESS] Sent '{subject}' → {to_email}")
                return True, f"Sent via SMTP TLS to {to_email}"
            except Exception as e_tls:
                err_msg = f"SMTP Error: {e_tls}"
                print(f"[SMTP ERROR] {err_msg}")
                return False, err_msg

    print(f"[EMAIL SIMULATION] (No API Key or SMTP credentials set) To: {to_email} | Subject: {subject}")
    return False, "Neither RESEND_API_KEY nor MAIL_USERNAME/PASSWORD are configured."


def send_email_async(to_email, subject, html_body, reply_to=None):
    """Fire-and-forget background thread for sending email asynchronously."""
    thread = threading.Thread(
        target=send_custom_email,
        args=(to_email, subject, html_body, reply_to),
    )
    thread.daemon = True
    thread.start()


def send_otp_email(to_email, full_name, otp_code):
    """Send beautiful OTP verification code email."""
    subject = f"🔐 Your BoshaCraft Verification Code: {otp_code}"
    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 540px; margin: 0 auto; background: #0d0e15; color: #f0f0f8; border-radius: 18px; overflow: hidden; border: 1px solid rgba(108, 99, 255, 0.25); box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);">
        <div style="background: linear-gradient(135deg, #6c63ff 0%, #3b82f6 100%); padding: 32px 28px; text-align: center;">
            <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 800; letter-spacing: -0.5px;">Bosha<span style="opacity: 0.85;">Craft</span></h1>
            <p style="color: rgba(255, 255, 255, 0.9); margin: 6px 0 0 0; font-size: 14px; font-weight: 500;">Account Verification System</p>
        </div>
        <div style="padding: 32px 28px;">
            <h2 style="color: #ffffff; margin-top: 0; font-size: 20px; font-weight: 700;">Welcome, {full_name}! 👋</h2>
            <p style="font-size: 15px; line-height: 1.7; color: #a0a0b8; margin-bottom: 24px;">
                Thank you for creating your engineering portfolio. Please use the 6-digit verification code below to activate your account:
            </p>
            <div style="text-align: center; margin: 30px 0;">
                <div style="display: inline-block; background: #161722; border: 2px solid #6c63ff; border-radius: 16px; padding: 20px 40px; box-shadow: 0 10px 30px rgba(108, 99, 255, 0.25);">
                    <span style="font-size: 3rem; font-weight: 900; letter-spacing: 14px; color: #6c63ff; font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;">{otp_code}</span>
                </div>
            </div>
            <div style="background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 12px; padding: 14px 18px; margin: 24px 0; text-align: center;">
                <p style="margin: 0; font-size: 14px; color: #fbbf24; font-weight: 600;">
                    ⏱ Code Expires in 5 Minutes
                </p>
            </div>
            <p style="font-size: 13px; color: #6e6e86; line-height: 1.6; text-align: center; margin-top: 28px; border-top: 1px solid #1f2030; padding-top: 20px;">
                If you did not request this registration, you can safely ignore this email.
            </p>
        </div>
    </div>
    """
    send_email_async(to_email, subject, html)


def send_password_reset_email(to_email, username, reset_url):
    """Send beautiful password reset email."""
    subject = "🔒 Reset Your BoshaCraft Password"
    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 540px; margin: 0 auto; background: #0d0e15; color: #f0f0f8; border-radius: 18px; overflow: hidden; border: 1px solid rgba(239, 68, 68, 0.25); box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);">
        <div style="background: linear-gradient(135deg, #ef4444 0%, #f59e0b 100%); padding: 32px 28px; text-align: center;">
            <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 800; letter-spacing: -0.5px;">Bosha<span style="opacity: 0.85;">Craft</span></h1>
            <p style="color: rgba(255, 255, 255, 0.9); margin: 6px 0 0 0; font-size: 14px; font-weight: 500;">Password Recovery Center</p>
        </div>
        <div style="padding: 32px 28px;">
            <h2 style="color: #ffffff; margin-top: 0; font-size: 20px; font-weight: 700;">Password Reset Request</h2>
            <p style="font-size: 15px; line-height: 1.7; color: #a0a0b8; margin-bottom: 24px;">
                Hi <strong>{username}</strong>, we received a request to reset your portfolio password. Click the button below to set a new password:
            </p>
            <div style="text-align: center; margin: 32px 0;">
                <a href="{reset_url}" style="display: inline-block; background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); color: #ffffff; text-decoration: none; padding: 16px 36px; border-radius: 12px; font-weight: 700; font-size: 16px; box-shadow: 0 10px 25px rgba(239, 68, 68, 0.35);">
                    🔒 Reset My Password
                </a>
            </div>
            <div style="background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 14px 18px; margin: 24px 0; word-break: break-all; font-size: 12px; color: #8e8ea6;">
                <strong>Direct Link:</strong> <a href="{reset_url}" style="color: #ef4444; text-decoration: underline;">{reset_url}</a>
            </div>
            <div style="background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 12px; padding: 12px 16px; text-align: center;">
                <p style="margin: 0; font-size: 13px; color: #fbbf24; font-weight: 600;">
                    ⏱ Link Expires in 15 Minutes
                </p>
            </div>
        </div>
    </div>
    """
    send_email_async(to_email, subject, html)


def notify_new_message(sender_name, sender_email, message_content, recipient_email=None):
    """Send portfolio contact notification email."""
    subject = f"🔔 New Portfolio Message from {sender_name}"
    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 540px; margin: 0 auto; background: #0d0e15; color: #f0f0f8; border-radius: 18px; overflow: hidden; border: 1px solid rgba(16, 185, 129, 0.25); box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);">
        <div style="background: linear-gradient(135deg, #10b981 0%, #06b6d4 100%); padding: 32px 28px; text-align: center;">
            <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 800;">Bosha<span style="opacity: 0.85;">Craft</span></h1>
            <p style="color: rgba(255, 255, 255, 0.9); margin: 6px 0 0 0; font-size: 14px; font-weight: 500;">New Contact Form Submission</p>
        </div>
        <div style="padding: 32px 28px;">
            <h2 style="color: #ffffff; margin-top: 0; font-size: 20px; font-weight: 700;">📬 You Have a New Message</h2>
            <div style="background: #161722; padding: 18px; border-radius: 12px; margin: 20px 0; border: 1px solid rgba(255, 255, 255, 0.08);">
                <p style="margin: 0 0 8px 0; font-size: 15px; color: #ffffff;"><strong>From:</strong> {sender_name}</p>
                <p style="margin: 0; font-size: 15px; color: #10b981;"><strong>Email:</strong> <a href="mailto:{sender_email or ''}" style="color: #10b981; text-decoration: underline;">{sender_email or 'Not provided'}</a></p>
            </div>
            <div style="background: #08090e; padding: 20px; border-radius: 12px; border-left: 4px solid #10b981;">
                <p style="margin: 0; white-space: pre-wrap; line-height: 1.7; font-size: 15px; color: #e4e4eb;">{message_content}</p>
            </div>
        </div>
    </div>
    """
    send_email_async(recipient_email, subject, html, reply_to=sender_email)


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


def get_settings(user_id=None, db=None):
    if db is None:
        db = get_db()
    if user_id is None:
        user_id = session.get("user_id", 1)
    s = db.execute("SELECT * FROM site_settings WHERE user_id = ?", (user_id,)).fetchone()
    if not s:
        # Fallback to default user 1 settings
        s = db.execute("SELECT * FROM site_settings WHERE user_id = 1 OR id = 1").fetchone()
    return s


def init_db():
    """Create all 9 tables and insert high quality seed data."""
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row

    db.executescript("""
        CREATE TABLE IF NOT EXISTS site_settings (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER DEFAULT 1,
            name            TEXT    DEFAULT 'Ahmed Bosha',
            logo_text       TEXT    DEFAULT 'AhmedBosha',
            site_title      TEXT    DEFAULT 'Ahmed Bosha — Engineering & Software Portfolio',
            greeting        TEXT    DEFAULT 'Hi, I''m',
            tagline         TEXT    DEFAULT 'Engineering Student & Software Developer',
            typing_texts    TEXT    DEFAULT 'Engineering Student,Software Developer,Problem Solver,Automation Enthusiast',
            bio             TEXT    DEFAULT 'Class of 2029. Passionate about automation, system analysis, and reverse engineering. I build tools that turn complex workflows into clean, efficient solutions.',
            footer_text     TEXT    DEFAULT '© 2026 Ahmed Bosha',
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
            color_text      TEXT    DEFAULT '#f0f0f8',
            admin_user      TEXT    DEFAULT 'admin',
            admin_pass_hash TEXT
        );

        CREATE TABLE IF NOT EXISTS users (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            username       TEXT UNIQUE NOT NULL,
            email          TEXT UNIQUE NOT NULL,
            password_hash  TEXT NOT NULL,
            role           TEXT DEFAULT 'user',
            account_status TEXT DEFAULT 'active',
            plan_tier      TEXT DEFAULT 'free',
            created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS education (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id             INTEGER DEFAULT 1,
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
            user_id     INTEGER DEFAULT 1,
            name        TEXT    NOT NULL,
            category    TEXT    NOT NULL DEFAULT 'Programming & Backend',
            level_tag   TEXT,
            icon        TEXT,
            sort_order  INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS experiences (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER DEFAULT 1,
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
            user_id     INTEGER DEFAULT 1,
            title       TEXT    NOT NULL,
            description TEXT    NOT NULL,
            icon        TEXT    DEFAULT '⚙️',
            sort_order  INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS projects (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER DEFAULT 1,
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
            user_id         INTEGER DEFAULT 1,
            title           TEXT    NOT NULL,
            issuer          TEXT,
            date_earned     TEXT,
            credential_url  TEXT,
            credential_id   TEXT,
            image           TEXT,
            icon            TEXT    DEFAULT '🏆',
            description     TEXT,
            sort_order      INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS testimonials (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER DEFAULT 1,
            client_name     TEXT    NOT NULL,
            client_role     TEXT    NOT NULL,
            quote           TEXT    NOT NULL,
            avatar          TEXT,
            sort_order      INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS messages (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER DEFAULT 1,
            sender_name  TEXT    NOT NULL,
            sender_email TEXT    NOT NULL,
            message      TEXT    NOT NULL,
            is_read      INTEGER DEFAULT 0,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Safe Schema Migrations (for backwards compatibility & multi-tenancy)
    cursor = db.cursor()

    # Rebuild site_settings if it has legacy CHECK (id = 1) constraint
    sqlite_master_row = cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='site_settings'").fetchone()
    if sqlite_master_row and "CHECK" in sqlite_master_row[0]:
        cursor.execute("""
            CREATE TABLE site_settings_new (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER DEFAULT 1,
                name            TEXT    DEFAULT 'Ahmed Bosha',
                logo_text       TEXT    DEFAULT 'AhmedBosha',
                site_title      TEXT    DEFAULT 'Ahmed Bosha — Engineering & Software Portfolio',
                greeting        TEXT    DEFAULT 'Hi, I''m',
                tagline         TEXT    DEFAULT 'Engineering Student & Software Developer',
                typing_texts    TEXT    DEFAULT 'Engineering Student,Software Developer,Problem Solver,Automation Enthusiast',
                bio             TEXT    DEFAULT 'Class of 2029. Passionate about automation, system analysis, and reverse engineering. I build tools that turn complex workflows into clean, efficient solutions.',
                footer_text     TEXT    DEFAULT '© 2026 Ahmed Bosha',
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
                color_text      TEXT    DEFAULT '#f0f0f8',
                admin_user      TEXT    DEFAULT 'admin',
                admin_pass_hash TEXT,
                theme_name      TEXT    DEFAULT 'default'
            )
        """)
        try:
            cursor.execute("INSERT INTO site_settings_new (id, name, logo_text, site_title, greeting, tagline, typing_texts, bio, footer_text, profile_photo, email, github_url, linkedin_url, twitter_url, resume_url, color_primary, color_accent, color_bg, color_surface, color_text, admin_user, admin_pass_hash) SELECT id, name, logo_text, site_title, greeting, tagline, typing_texts, bio, footer_text, profile_photo, email, github_url, linkedin_url, twitter_url, resume_url, color_primary, color_accent, color_bg, color_surface, color_text, admin_user, admin_pass_hash FROM site_settings")
        except Exception:
            pass
        cursor.execute("DROP TABLE site_settings")
        cursor.execute("ALTER TABLE site_settings_new RENAME TO site_settings")
        db.commit()
    
    # Ensure user_id column exists across all data tables
    target_tables = [
        "site_settings", "projects", "skills", "experiences",
        "education", "services", "achievements", "testimonials", "messages"
    ]
    for table in target_tables:
        cursor.execute(f"PRAGMA table_info({table})")
        cols = [row[1] for row in cursor.fetchall()]
        if "user_id" not in cols:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER DEFAULT 1")

    # Safe Schema Migrations for users table
    cursor.execute("PRAGMA table_info(users)")
    user_cols = [row[1] for row in cursor.fetchall()]
    needed_user_cols = [
        ("verification_code", "TEXT"),
        ("code_expires_at", "TIMESTAMP"),
        ("reset_token", "TEXT"),
        ("reset_token_expires_at", "TIMESTAMP"),
        ("is_verified", "INTEGER DEFAULT 1"),
    ]
    for col, definition in needed_user_cols:
        if col not in user_cols:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {definition}")

    cursor.execute("PRAGMA table_info(site_settings)")
    existing_cols = [row[1] for row in cursor.fetchall()]
    needed_cols = [
        ("logo_text", "TEXT DEFAULT 'AhmedBosha'"),
        ("site_title", "TEXT DEFAULT 'Ahmed Bosha — Engineering & Software Portfolio'"),
        ("footer_text", "TEXT DEFAULT '© 2026 Ahmed Bosha'"),
        ("admin_user", "TEXT DEFAULT 'admin'"),
        ("admin_pass_hash", "TEXT"),
        ("theme_name", "TEXT DEFAULT 'default'"),
    ]
    for col, definition in needed_cols:
        if col not in existing_cols:
            cursor.execute(f"ALTER TABLE site_settings ADD COLUMN {col} {definition}")

    # Check achievements table columns
    cursor.execute("PRAGMA table_info(achievements)")
    ach_cols = [row[1] for row in cursor.fetchall()]
    if "credential_id" not in ach_cols:
        cursor.execute("ALTER TABLE achievements ADD COLUMN credential_id TEXT")
    if "image" not in ach_cols:
        cursor.execute("ALTER TABLE achievements ADD COLUMN image TEXT")

    # Seed Default Super Admin User (Ahmed Bosha)
    if db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        admin_pass = os.environ.get("ADMIN_PASS", "admin123")
        db.execute(
            """INSERT INTO users (id, username, email, password_hash, role, account_status, plan_tier)
               VALUES (1, 'admin', 'admin@ahmedbosha.com', ?, 'admin', 'active', 'pro')""",
            (generate_password_hash(admin_pass),),
        )

    db.commit()

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
        user_id = session.get("user_id", 1)
        settings = get_settings(user_id=user_id)
        unread = get_db().execute(
            "SELECT COUNT(*) FROM messages WHERE user_id = ? AND is_read = 0", (user_id,)
        ).fetchone()[0]
    except Exception:
        settings = None
        unread = 0
    return dict(settings=settings, unread_count=unread)


# ---------------------------------------------------------------------------
# Auth helpers & Decorators
# ---------------------------------------------------------------------------

def get_current_user_id():
    return session.get("user_id", 1)


def login_required(view):
    @functools.wraps(view)
    def wrapped(**kwargs):
        if not session.get("user_id") and not session.get("admin_logged_in"):
            flash("Please log in to access the dashboard.", "warning")
            return redirect(url_for("admin_login"))
        return view(**kwargs)
    return wrapped


def superadmin_required(view):
    @functools.wraps(view)
    def wrapped(**kwargs):
        if not session.get("user_id") or session.get("role") != "admin":
            flash("Super Admin access required.", "danger")
            return redirect(url_for("admin_login"))
        return view(**kwargs)
    return wrapped


# ---------------------------------------------------------------------------
# Public & User Portfolio Routes
# ---------------------------------------------------------------------------

def render_user_portfolio(user_id):
    db = get_db()
    settings = get_settings(user_id=user_id, db=db)
    if not settings:
        settings = get_settings(user_id=1, db=db)

    projects = db.execute("SELECT * FROM projects WHERE user_id = ? ORDER BY created_at DESC", (user_id,)).fetchall()
    skills_raw = db.execute("SELECT * FROM skills WHERE user_id = ? ORDER BY category ASC, sort_order ASC, id ASC", (user_id,)).fetchall()
    
    skill_categories = {}
    for s in skills_raw:
        cat = s["category"] or "General"
        if cat not in skill_categories:
            skill_categories[cat] = []
        skill_categories[cat].append(s)

    education_list = db.execute("SELECT * FROM education WHERE user_id = ? ORDER BY sort_order ASC, start_year DESC", (user_id,)).fetchall()
    experiences_list = db.execute("SELECT * FROM experiences WHERE user_id = ? ORDER BY sort_order ASC, id ASC", (user_id,)).fetchall()
    services_list = db.execute("SELECT * FROM services WHERE user_id = ? ORDER BY sort_order ASC, id ASC", (user_id,)).fetchall()
    achievements_list = db.execute("SELECT * FROM achievements WHERE user_id = ? ORDER BY sort_order ASC, id ASC", (user_id,)).fetchall()
    testimonials_list = db.execute("SELECT * FROM testimonials WHERE user_id = ? ORDER BY sort_order ASC, id ASC", (user_id,)).fetchall()

    theme = "default"
    if settings and "theme_name" in settings.keys() and settings["theme_name"]:
        theme = settings["theme_name"]

    theme_template = f"themes/{theme}/index.html"
    if not os.path.exists(os.path.join(app.root_path, "templates", "themes", theme, "index.html")):
        theme_template = "index.html"

    return render_template(
        theme_template,
        settings=settings,
        projects=projects,
        skill_categories=skill_categories,
        education_list=education_list,
        experiences_list=experiences_list,
        services_list=services_list,
        achievements_list=achievements_list,
        testimonials_list=testimonials_list,
    )


@app.route("/")
def index():
    return render_user_portfolio(1)


@app.route("/u/<username>")
def user_portfolio(username):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE LOWER(username) = ?", (username.strip().lower(),)).fetchone()
    if not user:
        abort(404)
    if user["account_status"] == "suspended":
        return render_template("errors/suspended.html", username=username), 403
    return render_user_portfolio(user["id"])
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

# ---------------------------------------------------------------------------
# Auth Routes (Register, Login, Logout)
# ---------------------------------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def auth_register():
    if session.get("user_id"):
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        full_name = request.form.get("full_name", "").strip() or username.title()

        if not username or not email or not password:
            flash("Username, Email, and Password are required.", "danger")
            return render_template("auth/register.html")

        if len(username) < 3 or not username.isalnum():
            flash("Username must be at least 3 alphanumeric characters (letters and numbers only).", "danger")
            return render_template("auth/register.html")

        if len(password) < 8:
            flash("Password must be at least 8 characters long.", "danger")
            return render_template("auth/register.html")

        db = get_db()
        existing = db.execute("SELECT id FROM users WHERE LOWER(username) = ? OR LOWER(email) = ?", (username, email)).fetchone()
        if existing:
            flash("Username or Email is already registered. Please log in.", "warning")
            return redirect(url_for("admin_login"))

        # Generate 6-digit OTP with 5 min expiry
        otp_code = str(random.randint(100000, 999999))
        otp_expires_at = (datetime.datetime.now() + datetime.timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")

        cur = db.cursor()
        cur.execute(
            """INSERT INTO users (username, email, password_hash, role, account_status, plan_tier, verification_code, code_expires_at, is_verified)
               VALUES (?, ?, ?, 'user', 'pending', 'free', ?, ?, 0)""",
            (username, email, generate_password_hash(password), otp_code, otp_expires_at),
        )
        new_user_id = cur.lastrowid

        # Seed site_settings for new user
        db.execute(
            """INSERT INTO site_settings (user_id, name, logo_text, site_title, bio, footer_text, theme_name)
               VALUES (?, ?, ?, ?, ?, ?, 'default')""",
            (
                new_user_id,
                full_name,
                username,
                f"{full_name} — Engineering & Software Portfolio",
                f"Welcome to my portfolio! I build software and innovative engineering solutions.",
                f"© 2026 {full_name}",
            ),
        )
        db.commit()

        # Store pending user info in session for OTP verification step
        session["pending_user_id"] = new_user_id
        session["pending_username"] = username
        session["pending_email"] = email
        session["pending_full_name"] = full_name

        # Send OTP email via unified dispatcher (Resend API or Gmail SMTP fallback)
        send_otp_email(email, full_name, otp_code)

        # Mask email for display
        parts = email.split("@")
        masked = parts[0][:2] + "***@" + parts[1] if len(parts) == 2 else email

        flash(f"A 6-digit verification code was sent to your email ({masked}). Check your inbox!", "success")
        return render_template("auth/verify_otp.html", masked_email=masked)

    return render_template("auth/register.html")


@app.route("/verify-otp", methods=["GET", "POST"])
def auth_verify_otp():
    pending_user_id = session.get("pending_user_id")
    if not pending_user_id:
        flash("Session expired. Please register again.", "warning")
        return redirect(url_for("auth_register"))

    if request.method == "POST":
        otp_input = request.form.get("otp", "").strip()
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE id = ?", (pending_user_id,)).fetchone()

        if not user:
            flash("Account not found. Please register again.", "danger")
            return redirect(url_for("auth_register"))

        # Check expiry
        if user["code_expires_at"]:
            try:
                exp_time = datetime.datetime.strptime(user["code_expires_at"], "%Y-%m-%d %H:%M:%S")
                if datetime.datetime.now() > exp_time:
                    flash("Code expired. Please request a new one.", "danger")
                    parts = user["email"].split("@")
                    masked = parts[0][:2] + "***@" + parts[1] if len(parts) == 2 else user["email"]
                    return render_template("auth/verify_otp.html", masked_email=masked)
            except Exception:
                pass

        if otp_input != user["verification_code"]:
            flash("Invalid verification code. Please try again.", "danger")
            parts = user["email"].split("@")
            masked = parts[0][:2] + "***@" + parts[1] if len(parts) == 2 else user["email"]
            return render_template("auth/verify_otp.html", masked_email=masked)

        # OTP correct — activate user
        db.execute(
            "UPDATE users SET is_verified = 1, account_status = 'active', verification_code = NULL, code_expires_at = NULL WHERE id = ?",
            (pending_user_id,)
        )
        db.commit()

        # Clear pending session, start real session
        full_name = session.pop("pending_full_name", user["username"])
        session.pop("pending_email", None)
        session.pop("pending_user_id", None)
        session.pop("pending_username", None)

        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["role"] = user["role"]
        session["admin_logged_in"] = True

        flash(f"🎉 Welcome, {full_name}! Your portfolio is live at /u/{user['username']}", "success")
        return redirect(url_for("admin_dashboard"))

    # GET request - show verify form
    pending_email = session.get("pending_email", "")
    parts = pending_email.split("@")
    masked = parts[0][:2] + "***@" + parts[1] if len(parts) == 2 else pending_email
    return render_template("auth/verify_otp.html", masked_email=masked)


@app.route("/resend-otp", methods=["POST"])
def auth_resend_otp():
    pending_user_id = session.get("pending_user_id")
    if not pending_user_id:
        flash("Session expired. Please register again.", "warning")
        return redirect(url_for("auth_register"))

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (pending_user_id,)).fetchone()
    if not user:
        return redirect(url_for("auth_register"))

    # Generate new OTP
    otp_code = str(random.randint(100000, 999999))
    otp_expires_at = (datetime.datetime.now() + datetime.timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
    db.execute(
        "UPDATE users SET verification_code = ?, code_expires_at = ? WHERE id = ?",
        (otp_code, otp_expires_at, pending_user_id)
    )
    db.commit()

    full_name = session.get("pending_full_name", user["username"])
    send_otp_email(user["email"], full_name, otp_code)

    parts = user["email"].split("@")
    masked = parts[0][:2] + "***@" + parts[1] if len(parts) == 2 else user["email"]
    flash("New verification code sent! Check your email inbox.", "success")
    return render_template("auth/verify_otp.html", masked_email=masked)


@app.route("/admin/login", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def admin_login():
    if session.get("user_id"):
        if session.get("role") == "admin":
            return redirect(url_for("super_admin_dashboard"))
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        login_input = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE LOWER(username) = ? OR LOWER(email) = ?", (login_input, login_input)
        ).fetchone()

        if user and check_password_hash(user["password_hash"], password):
            if user["account_status"] == "suspended":
                flash("Your account has been suspended by the administrator.", "danger")
                return render_template("admin/login.html")

            # Check if user has pending verification
            user_dict = dict(user)
            if user["account_status"] == "pending" or (user_dict.get("is_verified") == 0 and user["role"] != "admin"):
                session["pending_user_id"] = user["id"]
                session["pending_email"] = user["email"]
                session["pending_full_name"] = user["username"]
                parts = user["email"].split("@")
                masked = parts[0][:2] + "***@" + parts[1] if len(parts) == 2 else user["email"]
                flash("Please verify your email first.", "warning")
                return render_template("auth/verify_otp.html", masked_email=masked)

            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            session["admin_logged_in"] = True

            flash(f"Welcome back, {user['username']}!", "success")
            if user["role"] == "admin":
                return redirect(url_for("super_admin_dashboard"))
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid username/email or password.", "danger")

    return render_template("admin/login.html")


@app.route("/admin/logout")
@app.route("/logout")
def admin_logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("index"))



# ---------------------------------------------------------------------------
# Super Admin Master Control Center (Ahmed Bosha Dashboard)
# ---------------------------------------------------------------------------

@app.route("/super-admin")
@superadmin_required
def super_admin_dashboard():
    db = get_db()
    users_list = db.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    
    total_users = len(users_list)
    total_projects = db.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    total_skills = db.execute("SELECT COUNT(*) FROM skills").fetchone()[0]
    total_achievements = db.execute("SELECT COUNT(*) FROM achievements").fetchone()[0]
    total_messages = db.execute("SELECT COUNT(*) FROM messages").fetchone()[0]

    return render_template(
        "admin/super_dashboard.html",
        users_list=users_list,
        total_users=total_users,
        total_projects=total_projects,
        total_skills=total_skills,
        total_achievements=total_achievements,
        total_messages=total_messages,
    )


@app.route("/super-admin/user/status/<int:target_user_id>", methods=["POST"])
@superadmin_required
def super_admin_toggle_status(target_user_id):
    if target_user_id == 1:
        flash("Cannot suspend Super Admin account.", "danger")
        return redirect(url_for("super_admin_dashboard"))
    
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (target_user_id,)).fetchone()
    if user:
        new_status = "suspended" if user["account_status"] == "active" else "active"
        db.execute("UPDATE users SET account_status = ? WHERE id = ?", (new_status, target_user_id))
        db.commit()
        flash(f"User '{user['username']}' status changed to '{new_status}'.", "info")
    return redirect(url_for("super_admin_dashboard"))


@app.route("/super-admin/user/delete/<int:target_user_id>", methods=["POST"])
@superadmin_required
def super_admin_delete_user(target_user_id):
    if target_user_id == 1:
        flash("Cannot delete Super Admin account.", "danger")
        return redirect(url_for("super_admin_dashboard"))
    
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (target_user_id,)).fetchone()
    if user:
        tables = ["site_settings", "projects", "skills", "experiences", "education", "services", "achievements", "testimonials", "messages"]
        for table in tables:
            db.execute(f"DELETE FROM {table} WHERE user_id = ?", (target_user_id,))
        db.execute("DELETE FROM users WHERE id = ?", (target_user_id,))
        db.commit()
        flash(f"User '{user['username']}' and all their data deleted permanently.", "success")
    return redirect(url_for("super_admin_dashboard"))


@app.route("/admin")
@login_required
def admin_dashboard():
    db = get_db()
    user_id = session.get("user_id", 1)
    projects = db.execute("SELECT * FROM projects WHERE user_id = ? ORDER BY created_at DESC", (user_id,)).fetchall()
    return render_template("admin/dashboard.html", projects=projects)


# ---------------------------------------------------------------------------
# Admin: Site Settings (100% White-label Ownership)
# ---------------------------------------------------------------------------

@app.route("/admin/settings", methods=["GET", "POST"])
@login_required
def admin_settings():
    db = get_db()
    user_id = session.get("user_id", 1)
    settings = get_settings(user_id=user_id, db=db)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        logo_text = request.form.get("logo_text", "").strip() or name.replace(" ", "")
        site_title = request.form.get("site_title", "").strip() or f"{name} — Portfolio"
        greeting = request.form.get("greeting", "").strip()
        tagline = request.form.get("tagline", "").strip()
        typing_texts = request.form.get("typing_texts", "").strip()
        bio = request.form.get("bio", "").strip()
        footer_text = request.form.get("footer_text", "").strip() or f"© 2026 {name}"
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
        theme_name = request.form.get("theme_name", "default").strip()

        # Update user password if provided
        new_admin_pass = request.form.get("admin_password", "").strip()
        if new_admin_pass:
            db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (generate_password_hash(new_admin_pass), user_id))

        profile_photo = settings["profile_photo"] if settings else None
        if "profile_photo" in request.files:
            file = request.files["profile_photo"]
            if file and file.filename and allowed_file(file.filename):
                delete_upload(profile_photo)
                profile_photo = save_upload(file, "profile")
        if request.form.get("remove_photo") == "1":
            delete_upload(profile_photo)
            profile_photo = None

        if settings:
            db.execute(
                """UPDATE site_settings SET
                    name=?, logo_text=?, site_title=?, greeting=?, tagline=?, typing_texts=?, bio=?,
                    footer_text=?, profile_photo=?, email=?, github_url=?, linkedin_url=?, twitter_url=?, resume_url=?,
                    color_primary=?, color_accent=?, color_bg=?, color_surface=?, color_text=?, theme_name=?
                   WHERE user_id=?""",
                (name, logo_text, site_title, greeting, tagline, typing_texts, bio,
                 footer_text, profile_photo, email, github_url, linkedin_url, twitter_url, resume_url,
                 color_primary, color_accent, color_bg, color_surface, color_text, theme_name, user_id),
            )
        else:
            db.execute(
                """INSERT INTO site_settings
                    (user_id, name, logo_text, site_title, greeting, tagline, typing_texts, bio,
                    footer_text, profile_photo, email, github_url, linkedin_url, twitter_url, resume_url,
                    color_primary, color_accent, color_bg, color_surface, color_text, theme_name)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, name, logo_text, site_title, greeting, tagline, typing_texts, bio,
                 footer_text, profile_photo, email, github_url, linkedin_url, twitter_url, resume_url,
                 color_primary, color_accent, color_bg, color_surface, color_text, theme_name),
            )

        db.commit()
        flash("Portfolio settings and theme updated successfully!", "success")
        return redirect(url_for("admin_settings"))

    return render_template("admin/settings.html", settings=settings)


# ---------------------------------------------------------------------------
# Admin: Projects CRUD
# ---------------------------------------------------------------------------

@app.route("/admin/projects/add", methods=["GET", "POST"])
@login_required
def admin_add_project():
    user_id = session.get("user_id", 1)
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
               (user_id, title, description, tech_stack, github_link, live_demo_link, certificate_url, image)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, title, description, tech_stack, github_link, live_demo_link, certificate_url, image),
        )
        db.commit()
        flash(f'Project "{title}" added!', "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("admin/project_form.html", project=None)


@app.route("/admin/projects/edit/<int:project_id>", methods=["GET", "POST"])
@login_required
def admin_edit_project(project_id):
    user_id = session.get("user_id", 1)
    db = get_db()
    project = db.execute("SELECT * FROM projects WHERE id = ? AND user_id = ?", (project_id, user_id)).fetchone()
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
               WHERE id=? AND user_id=?""",
            (title, description, tech_stack, github_link, live_demo_link,
             certificate_url, image, project_id, user_id),
        )
        db.commit()
        flash(f'Project "{title}" updated!', "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("admin/project_form.html", project=project)


@app.route("/admin/projects/delete/<int:project_id>", methods=["POST"])
@login_required
def admin_delete_project(project_id):
    user_id = session.get("user_id", 1)
    db = get_db()
    project = db.execute("SELECT title, image FROM projects WHERE id = ? AND user_id = ?", (project_id, user_id)).fetchone()
    if project is None:
        abort(404)
    delete_upload(project["image"])
    db.execute("DELETE FROM projects WHERE id = ? AND user_id = ?", (project_id, user_id))
    db.commit()
    flash(f'Project "{project["title"]}" deleted.', "info")
    return redirect(url_for("admin_dashboard"))


# ---------------------------------------------------------------------------
# Admin: Skills CRUD
# ---------------------------------------------------------------------------

@app.route("/admin/skills")
@login_required
def admin_skills():
    user_id = session.get("user_id", 1)
    db = get_db()
    skills = db.execute("SELECT * FROM skills WHERE user_id = ? ORDER BY category ASC, sort_order ASC, id ASC", (user_id,)).fetchall()
    return render_template("admin/skills.html", skills=skills)


@app.route("/admin/skills/add", methods=["POST"])
@login_required
def admin_add_skill():
    user_id = session.get("user_id", 1)
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
        "INSERT INTO skills (user_id, name, category, level_tag, icon, sort_order) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, name, category, level_tag, icon, sort_order),
    )
    db.commit()
    flash(f'Skill "{name}" added!', "success")
    return redirect(url_for("admin_skills"))


@app.route("/admin/skills/edit/<int:skill_id>", methods=["POST"])
@login_required
def admin_edit_skill(skill_id):
    user_id = session.get("user_id", 1)
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
        "UPDATE skills SET name=?, category=?, level_tag=?, icon=?, sort_order=? WHERE id=? AND user_id=?",
        (name, category, level_tag, icon, sort_order, skill_id, user_id),
    )
    db.commit()
    flash(f'Skill "{name}" updated!', "success")
    return redirect(url_for("admin_skills"))


@app.route("/admin/skills/delete/<int:skill_id>", methods=["POST"])
@login_required
def admin_delete_skill(skill_id):
    user_id = session.get("user_id", 1)
    db = get_db()
    skill = db.execute("SELECT name FROM skills WHERE id = ? AND user_id = ?", (skill_id, user_id)).fetchone()
    if skill:
        db.execute("DELETE FROM skills WHERE id = ? AND user_id = ?", (skill_id, user_id))
        db.commit()
        flash(f'Skill "{skill["name"]}" deleted.', "info")
    return redirect(url_for("admin_skills"))


# ---------------------------------------------------------------------------
# Admin: Education CRUD
# ---------------------------------------------------------------------------

@app.route("/admin/education")
@login_required
def admin_education():
    user_id = session.get("user_id", 1)
    db = get_db()
    items = db.execute("SELECT * FROM education WHERE user_id = ? ORDER BY sort_order ASC, start_year DESC", (user_id,)).fetchall()
    return render_template("admin/education.html", education_list=items)


@app.route("/admin/education/add", methods=["POST"])
@login_required
def admin_add_education():
    user_id = session.get("user_id", 1)
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
        """INSERT INTO education (user_id, institution, degree, field_of_study, start_year, end_year, grade_or_details, sort_order)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, institution, degree, field_of_study, start_year, end_year, grade_or_details, sort_order),
    )
    db.commit()
    flash("Education entry added!", "success")
    return redirect(url_for("admin_education"))


@app.route("/admin/education/edit/<int:item_id>", methods=["POST"])
@login_required
def admin_edit_education(item_id):
    user_id = session.get("user_id", 1)
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
           WHERE id=? AND user_id=?""",
        (institution, degree, field_of_study, start_year, end_year, grade_or_details, sort_order, item_id, user_id),
    )
    db.commit()
    flash("Education entry updated!", "success")
    return redirect(url_for("admin_education"))


@app.route("/admin/education/delete/<int:item_id>", methods=["POST"])
@login_required
def admin_delete_education(item_id):
    user_id = session.get("user_id", 1)
    db = get_db()
    db.execute("DELETE FROM education WHERE id = ? AND user_id = ?", (item_id, user_id))
    db.commit()
    flash("Education entry deleted.", "info")
    return redirect(url_for("admin_education"))


# ---------------------------------------------------------------------------
# Admin: Work Experience & Training CRUD
# ---------------------------------------------------------------------------

@app.route("/admin/experience")
@login_required
def admin_experience():
    user_id = session.get("user_id", 1)
    db = get_db()
    items = db.execute("SELECT * FROM experiences WHERE user_id = ? ORDER BY sort_order ASC, id ASC", (user_id,)).fetchall()
    return render_template("admin/experience.html", experiences_list=items)


@app.route("/admin/experience/add", methods=["POST"])
@login_required
def admin_add_experience():
    user_id = session.get("user_id", 1)
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
        """INSERT INTO experiences (user_id, title, company, location, start_date, end_date, description, is_current, sort_order)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, title, company, location, start_date, end_date, description, is_current, sort_order),
    )
    db.commit()
    flash(f'Experience "{title}" added!', "success")
    return redirect(url_for("admin_experience"))


@app.route("/admin/experience/edit/<int:item_id>", methods=["POST"])
@login_required
def admin_edit_experience(item_id):
    user_id = session.get("user_id", 1)
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
           WHERE id=? AND user_id=?""",
        (title, company, location, start_date, end_date, description, is_current, sort_order, item_id, user_id),
    )
    db.commit()
    flash(f'Experience "{title}" updated!', "success")
    return redirect(url_for("admin_experience"))


@app.route("/admin/experience/delete/<int:item_id>", methods=["POST"])
@login_required
def admin_delete_experience(item_id):
    user_id = session.get("user_id", 1)
    db = get_db()
    db.execute("DELETE FROM experiences WHERE id = ? AND user_id = ?", (item_id, user_id))
    db.commit()
    flash("Experience entry deleted.", "info")
    return redirect(url_for("admin_experience"))


# ---------------------------------------------------------------------------
# Admin: Offered Services CRUD
# ---------------------------------------------------------------------------

@app.route("/admin/services")
@login_required
def admin_services():
    user_id = session.get("user_id", 1)
    db = get_db()
    items = db.execute("SELECT * FROM services WHERE user_id = ? ORDER BY sort_order ASC, id ASC", (user_id,)).fetchall()
    return render_template("admin/services.html", services_list=items)


@app.route("/admin/services/add", methods=["POST"])
@login_required
def admin_add_service():
    user_id = session.get("user_id", 1)
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    icon = request.form.get("icon", "⚙️").strip() or "⚙️"
    sort_order = int(request.form.get("sort_order", 0) or 0)

    if not title or not description:
        flash("Service Title and Description are required.", "danger")
        return redirect(url_for("admin_services"))

    db = get_db()
    db.execute(
        "INSERT INTO services (user_id, title, description, icon, sort_order) VALUES (?, ?, ?, ?, ?)",
        (user_id, title, description, icon, sort_order),
    )
    db.commit()
    flash(f'Service "{title}" added!', "success")
    return redirect(url_for("admin_services"))


@app.route("/admin/services/edit/<int:item_id>", methods=["POST"])
@login_required
def admin_edit_service(item_id):
    user_id = session.get("user_id", 1)
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    icon = request.form.get("icon", "⚙️").strip() or "⚙️"
    sort_order = int(request.form.get("sort_order", 0) or 0)

    if not title or not description:
        flash("Service Title and Description are required.", "danger")
        return redirect(url_for("admin_services"))

    db = get_db()
    db.execute(
        "UPDATE services SET title=?, description=?, icon=?, sort_order=? WHERE id=? AND user_id=?",
        (title, description, icon, sort_order, item_id, user_id),
    )
    db.commit()
    flash(f'Service "{title}" updated!', "success")
    return redirect(url_for("admin_services"))


@app.route("/admin/services/delete/<int:item_id>", methods=["POST"])
@login_required
def admin_delete_service(item_id):
    user_id = session.get("user_id", 1)
    db = get_db()
    db.execute("DELETE FROM services WHERE id = ? AND user_id = ?", (item_id, user_id))
    db.commit()
    flash("Service deleted.", "info")
    return redirect(url_for("admin_services"))


# ---------------------------------------------------------------------------
# Admin: Achievements & Certifications CRUD
# ---------------------------------------------------------------------------

@app.route("/admin/achievements")
@login_required
def admin_achievements():
    user_id = session.get("user_id", 1)
    db = get_db()
    items = db.execute("SELECT * FROM achievements WHERE user_id = ? ORDER BY sort_order ASC, id ASC", (user_id,)).fetchall()
    return render_template("admin/achievements.html", achievements_list=items)


@app.route("/admin/achievements/add", methods=["POST"])
@login_required
def admin_add_achievement():
    user_id = session.get("user_id", 1)
    title = request.form.get("title", "").strip()
    issuer = request.form.get("issuer", "").strip() or None
    date_earned = request.form.get("date_earned", "").strip() or None
    credential_url = request.form.get("credential_url", "").strip() or None
    credential_id = request.form.get("credential_id", "").strip() or None
    icon = request.form.get("icon", "🏆").strip() or "🏆"
    description = request.form.get("description", "").strip() or None
    sort_order = int(request.form.get("sort_order", 0) or 0)

    image_filename = None
    if "image" in request.files:
        file = request.files["image"]
        if file and file.filename and allowed_file(file.filename):
            image_filename = save_upload(file, "certificate")

    if not title:
        flash("Achievement Title is required.", "danger")
        return redirect(url_for("admin_achievements"))

    db = get_db()
    db.execute(
        """INSERT INTO achievements (user_id, title, issuer, date_earned, credential_url, credential_id, image, icon, description, sort_order)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, title, issuer, date_earned, credential_url, credential_id, image_filename, icon, description, sort_order),
    )
    db.commit()
    flash(f'Achievement "{title}" added!', "success")
    return redirect(url_for("admin_achievements"))


@app.route("/admin/achievements/edit/<int:item_id>", methods=["POST"])
@login_required
def admin_edit_achievement(item_id):
    user_id = session.get("user_id", 1)
    db = get_db()
    current = db.execute("SELECT * FROM achievements WHERE id = ? AND user_id = ?", (item_id, user_id)).fetchone()
    if not current:
        flash("Achievement not found.", "danger")
        return redirect(url_for("admin_achievements"))

    title = request.form.get("title", "").strip()
    issuer = request.form.get("issuer", "").strip() or None
    date_earned = request.form.get("date_earned", "").strip() or None
    credential_url = request.form.get("credential_url", "").strip() or None
    credential_id = request.form.get("credential_id", "").strip() or None
    icon = request.form.get("icon", "🏆").strip() or "🏆"
    description = request.form.get("description", "").strip() or None
    sort_order = int(request.form.get("sort_order", 0) or 0)

    image_filename = current["image"]
    if "image" in request.files:
        file = request.files["image"]
        if file and file.filename and allowed_file(file.filename):
            delete_upload(image_filename)
            image_filename = save_upload(file, "certificate")
    if request.form.get("remove_image") == "1":
        delete_upload(image_filename)
        image_filename = None

    if not title:
        flash("Achievement Title is required.", "danger")
        return redirect(url_for("admin_achievements"))

    db.execute(
        """UPDATE achievements SET
            title=?, issuer=?, date_earned=?, credential_url=?, credential_id=?, image=?, icon=?, description=?, sort_order=?
           WHERE id=? AND user_id=?""",
        (title, issuer, date_earned, credential_url, credential_id, image_filename, icon, description, sort_order, item_id, user_id),
    )
    db.commit()
    flash(f'Achievement "{title}" updated!', "success")
    return redirect(url_for("admin_achievements"))


@app.route("/admin/achievements/delete/<int:item_id>", methods=["POST"])
@login_required
def admin_delete_achievement(item_id):
    user_id = session.get("user_id", 1)
    db = get_db()
    current = db.execute("SELECT image FROM achievements WHERE id = ? AND user_id = ?", (item_id, user_id)).fetchone()
    if current and current["image"]:
        delete_upload(current["image"])
    db.execute("DELETE FROM achievements WHERE id = ? AND user_id = ?", (item_id, user_id))
    db.commit()
    flash("Achievement deleted.", "info")
    return redirect(url_for("admin_achievements"))


# ---------------------------------------------------------------------------
# Admin: Testimonials CRUD
# ---------------------------------------------------------------------------

@app.route("/admin/testimonials")
@login_required
def admin_testimonials():
    user_id = session.get("user_id", 1)
    db = get_db()
    items = db.execute("SELECT * FROM testimonials WHERE user_id = ? ORDER BY sort_order ASC, id ASC", (user_id,)).fetchall()
    return render_template("admin/testimonials.html", testimonials_list=items)


@app.route("/admin/testimonials/add", methods=["POST"])
@login_required
def admin_add_testimonial():
    user_id = session.get("user_id", 1)
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
        "INSERT INTO testimonials (user_id, client_name, client_role, quote, avatar, sort_order) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, client_name, client_role, quote, avatar, sort_order),
    )
    db.commit()
    flash(f'Testimonial from "{client_name}" added!', "success")
    return redirect(url_for("admin_testimonials"))


@app.route("/admin/testimonials/edit/<int:item_id>", methods=["POST"])
@login_required
def admin_edit_testimonial(item_id):
    user_id = session.get("user_id", 1)
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
        "UPDATE testimonials SET client_name=?, client_role=?, quote=?, avatar=?, sort_order=? WHERE id=? AND user_id=?",
        (client_name, client_role, quote, avatar, sort_order, item_id, user_id),
    )
    db.commit()
    flash(f'Testimonial from "{client_name}" updated!', "success")
    return redirect(url_for("admin_testimonials"))


@app.route("/admin/testimonials/delete/<int:item_id>", methods=["POST"])
@login_required
def admin_delete_testimonial(item_id):
    user_id = session.get("user_id", 1)
    db = get_db()
    db.execute("DELETE FROM testimonials WHERE id = ? AND user_id = ?", (item_id, user_id))
    db.commit()
    flash("Testimonial deleted.", "info")
    return redirect(url_for("admin_testimonials"))


# ---------------------------------------------------------------------------
# Admin: Messages
# ---------------------------------------------------------------------------

@app.route("/admin/messages")
@login_required
def admin_messages():
    user_id = session.get("user_id", 1)
    db = get_db()
    messages = db.execute("SELECT * FROM messages WHERE user_id = ? ORDER BY created_at DESC", (user_id,)).fetchall()
    db.execute("UPDATE messages SET is_read = 1 WHERE user_id = ? AND is_read = 0", (user_id,))
    db.commit()
    return render_template("admin/messages.html", messages=messages)


@app.route("/admin/messages/delete/<int:msg_id>", methods=["POST"])
@login_required
def admin_delete_message(msg_id):
    user_id = session.get("user_id", 1)
    db = get_db()
    db.execute("DELETE FROM messages WHERE id = ? AND user_id = ?", (msg_id, user_id))
    db.commit()
    flash("Message deleted.", "info")
    return redirect(url_for("admin_messages"))


# ---------------------------------------------------------------------------
# Password Reset & Email OTP Verification Routes
# ---------------------------------------------------------------------------

@app.route("/forgot-password", methods=["GET", "POST"])
def auth_forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE LOWER(email) = ?", (email,)).fetchone()

        if user:
            reset_token = uuid.uuid4().hex
            expires_at = datetime.datetime.now() + datetime.timedelta(minutes=15)
            expires_str = expires_at.strftime("%Y-%m-%d %H:%M:%S")

            db.execute("UPDATE users SET reset_token = ?, reset_token_expires_at = ? WHERE id = ?", (reset_token, expires_str, user["id"]))
            db.commit()

            reset_url = url_for("auth_reset_password", token=reset_token, _external=True)
            send_password_reset_email(email, user["username"], reset_url)

            flash("✅ Password reset link sent to your email! Check your inbox.", "success")
            return redirect(url_for("admin_login"))
        else:
            flash("No account registered with that email address.", "danger")

    return render_template("auth/forgot_password.html")


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def auth_reset_password(token):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE reset_token = ?", (token,)).fetchone()

    if not user:
        flash("Invalid or expired password reset link.", "danger")
        return redirect(url_for("auth_forgot_password"))

    if user["reset_token_expires_at"]:
        try:
            exp_time = datetime.datetime.strptime(user["reset_token_expires_at"], "%Y-%m-%d %H:%M:%S")
            if datetime.datetime.now() > exp_time:
                flash("Password reset link has expired. Please request a new one.", "danger")
                return redirect(url_for("auth_forgot_password"))
        except Exception:
            pass

    if request.method == "POST":
        new_password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        if not new_password or new_password != confirm_password:
            flash("Passwords do not match or are empty.", "danger")
            return render_template("auth/reset_password.html", token=token)

        db.execute("UPDATE users SET password_hash = ?, reset_token = NULL, reset_token_expires_at = NULL WHERE id = ?", (generate_password_hash(new_password), user["id"]))
        db.commit()

        flash("Your password has been reset successfully! Please log in.", "success")
        return redirect(url_for("admin_login"))

    return render_template("auth/reset_password.html", token=token)


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
