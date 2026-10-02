<div align="center">

# Ahmed Youssef Bosha — Portfolio Platform

A full-stack portfolio builder and content-management platform built with Flask.

Create a personal portfolio, manage it from a dashboard, publish projects and achievements, receive contact messages, and keep live data persistent across deployments.

## 🌐 Live Website

### 👉 [Open the live platform](https://ahmed-bosha.onrender.com)

**Try the portfolio, sign in, or create your own portfolio directly from the live website.**

[![Open Live Website](https://img.shields.io/badge/Open%20Live%20Website-ahmed--bosha.onrender.com-6C63FF?style=for-the-badge)](https://ahmed-bosha.onrender.com)

[![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/SQLite-Local%20Runtime-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Supabase](https://img.shields.io/badge/Supabase-Cloud%20Persistence-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com/)

</div>

---

## Overview

This project started as a personal portfolio and evolved into a small **multi-user portfolio platform**.

The homepage presents a complete public portfolio, while authenticated users can manage their own content from a browser-based dashboard. New users can create an account, verify their email, customize their profile, and publish a portfolio at:

```text
/u/<username>
```

The main public page currently showcases **Ahmed Youssef Bosha's** portfolio, while the same application infrastructure supports additional user portfolios.

---

## What the Platform Includes

### Public Portfolio

Each portfolio can present:

- Profile photo and personal introduction
- Education
- Skills and technologies
- Experience and training
- Services
- Featured projects
- Achievements and certifications
- Testimonials
- Contact information
- Social links and CV/resume link

The frontend is responsive and supports dark/light appearance.

### Portfolio CMS

Users can update portfolio content without editing source code.

The dashboard includes management pages for:

- Profile and account information
- Portfolio settings
- Education
- Skills
- Experience
- Services
- Projects
- Achievements
- Testimonials
- Contact messages

### User Accounts

The platform supports:

- Account registration
- Email verification with a 6-digit OTP
- Secure login sessions
- Password reset
- Email-change verification
- Account status controls
- Separate portfolio URLs for users
- Owner-only super-admin controls

Registration is enabled by default and can be disabled with:

```env
ALLOW_REGISTRATION=0
```

### Profile Photo Cropper

Profile images include a browser-based crop editor with:

- 1:1 crop area
- Circular profile preview guide
- Movable crop box
- Resize handles
- Grid and center guides
- 800 × 800 output
- Direct upload from the crop dialog

### Contact & Email Workflows

Visitors can send messages from the portfolio contact form.

The application can use:

1. Brevo API
2. Resend API
3. Gmail / SMTP fallback

Email workflows are used for:

- OTP verification
- Password reset
- Email-change verification
- Contact notifications
- Admin email testing

---

## Persistent Data Across Deployments

Render's filesystem can be ephemeral, so the application does not rely on GitHub for live user data.

The runtime model is:

```text
                 Render Web Service
                        │
                        ▼
                 Local SQLite DB
                        │
              commit / restore
                        │
                        ▼
                Supabase Postgres
             ┌──────────┴──────────┐
             ▼                     ▼
 portfolio_snapshots         portfolio_media
 SQLite DB snapshot          uploaded images
```

### How it works

- SQLite is still used locally by Flask for simple and fast application queries.
- On startup, the latest database snapshot is restored from Supabase.
- After committed database changes, the SQLite database is synchronized back to Supabase.
- Uploaded images are mirrored to a protected Supabase table.
- If a local uploaded image disappears after a redeploy, Flask can load it again from Supabase.

This keeps live portfolio content independent from the Git repository.

> This architecture is intentionally simple for a small deployment. For a larger multi-instance production system, moving the application directly to PostgreSQL would be the next step.

---

## Tech Stack

| Technology | Role |
| --- | --- |
| Python | Backend application logic |
| Flask | Routing, views, sessions and server-side application |
| SQLite | Local runtime database |
| Supabase Postgres | Durable database snapshots and media persistence |
| Jinja2 | Server-rendered HTML templates |
| HTML / CSS / JavaScript | Frontend and interactive UI |
| Werkzeug | Password hashing and Flask utilities |
| Gunicorn | Production WSGI server |
| Brevo / Resend / SMTP | Transactional email delivery |
| Render | Current web deployment |

---

## Main Application Flow

```text
Visitor
  │
  ├── View portfolio
  ├── View projects
  ├── Send contact message
  ├── Sign in
  └── Create Portfolio
          │
          ▼
      Registration
          │
          ▼
    Email OTP Verification
          │
          ▼
       Dashboard
          │
    ┌─────┼────────────────────────────┐
    ▼     ▼        ▼        ▼          ▼
 Profile Skills Projects Education  Settings
          │
          ▼
      Public Portfolio
       /u/username
```

---

## Project Structure

```text
portfolio/
├── app.py
├── Procfile
├── requirements.txt
├── README.md
│
├── static/
│   ├── css/
│   │   └── style.css
│   ├── images/
│   │   └── default_avatar.png
│   ├── js/
│   │   └── profile-cropper.js
│   └── uploads/
│
└── templates/
    ├── base.html
    ├── index.html
    │
    ├── admin/
    │   ├── dashboard.html
    │   ├── profile.html
    │   ├── settings.html
    │   ├── education.html
    │   ├── skills.html
    │   ├── experience.html
    │   ├── services.html
    │   ├── project_form.html
    │   ├── achievements.html
    │   ├── testimonials.html
    │   ├── messages.html
    │   └── super_dashboard.html
    │
    ├── auth/
    │   ├── register.html
    │   ├── verify_otp.html
    │   ├── forgot_password.html
    │   ├── reset_password.html
    │   └── verify_email_change.html
    │
    └── errors/
        └── suspended.html
```

---

## Run Locally

### 1. Clone the repository

```bash
git clone https://github.com/R3Dzf/portfolio.git
cd portfolio
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux / macOS:

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

A minimal owner configuration:

```env
SECRET_KEY=replace-with-a-long-random-secret

ADMIN_USER=admin
ADMIN_EMAIL=admin@example.com
ADMIN_PASS=replace-with-a-strong-password

ALLOW_REGISTRATION=1
```

Then run:

```bash
python app.py
```

For a production-style process:

```bash
gunicorn app:app
```

---

## Environment Variables

### Application & Admin

| Variable | Description |
| --- | --- |
| `SECRET_KEY` | Flask session-signing secret |
| `ADMIN_USER` | Initial owner/admin username |
| `ADMIN_EMAIL` | Initial owner/admin email |
| `ADMIN_PASS` | Owner/admin password |
| `ALLOW_REGISTRATION` | `1` enables public registration, `0` disables it |
| `SESSION_COOKIE_SECURE` | Force secure session cookies when set to `1` |
| `DATABASE_PATH` | Optional custom SQLite path |
| `UPLOAD_FOLDER` | Optional custom local upload path |

### Supabase Persistence

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-publishable-key
SUPABASE_APP_KEY=your-private-application-sync-key
```

| Variable | Description |
| --- | --- |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase publishable/anon API key |
| `SUPABASE_APP_KEY` | Private application key checked by RLS policies |

> Keep `SUPABASE_APP_KEY`, admin credentials, email credentials, and `SECRET_KEY` in your hosting provider's secret environment variables. Do not commit them to Git.

### Email Providers

Brevo:

```env
BREVO_API_KEY=your-brevo-api-key
```

Resend:

```env
RESEND_API_KEY=your-resend-api-key
```

SMTP fallback:

```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-app-password
MAIL_RECIPIENT=your-email@example.com
```

---

## Security Measures

The application currently includes:

- Werkzeug password hashing
- CSRF protection for state-changing requests
- HttpOnly and SameSite session cookies
- Secure cookie support in HTTPS deployments
- Protected dashboard routes
- Owner-restricted super-admin routes
- OTP expiry and resend cooldowns
- OTP attempt throttling
- Secure password-reset tokens
- Email-change verification
- Upload type and size restrictions
- Generated upload filenames
- URL and theme value validation
- Basic contact-form cooldown
- Security response headers
- Content Security Policy
- Row Level Security around Supabase persistence tables
- No default hard-coded admin password

Security is an ongoing process; this project should still be reviewed before handling high-value or sensitive production data.

---

## Important Routes

| Route | Purpose |
| --- | --- |
| `/` | Main portfolio |
| `/u/<username>` | User portfolio |
| `/register` | Create account |
| `/login` | Sign in |
| `/admin` | User dashboard |
| `/admin/settings` | Portfolio settings |
| `/admin/profile` | Account profile |
| `/contact` | Contact-form endpoint |

---

## Current Deployment

Live application:

**https://ahmed-bosha.onrender.com**

The deployed homepage currently acts as both:

- Ahmed Youssef Bosha's public portfolio
- An entry point for users who want to create their own portfolio

---

## Future Improvements

Planned or logical next steps include:

- Replace synchronized SQLite snapshots with direct PostgreSQL access
- Add Alembic / Flask-Migrate database migrations
- Add automated backend and browser tests
- Add stronger distributed rate limiting
- Add portfolio analytics and visitor statistics
- Add custom domains
- Add more maintained portfolio themes
- Add image optimization and WebP conversion
- Add drag-and-drop section ordering
- Add richer onboarding for first-time users
- Add CI/CD checks before deployment

---

## Author

**Ahmed Youssef Bosha**  
Computer & Control Engineering Student — Tanta University

GitHub: [@R3Dzf](https://github.com/R3Dzf)

---

<div align="center">

Built as a real full-stack portfolio platform, not just a static personal page.

</div>
