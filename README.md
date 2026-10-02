<div align="center">

# 💼 Ahmed Bosha Portfolio & CMS

### A full-stack personal portfolio platform with a built-in CMS, authentication, admin dashboard, image uploads, contact messaging, and email workflows.

![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Web%20Framework-000000?style=for-the-badge&logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![Gunicorn](https://img.shields.io/badge/Gunicorn-Production%20Server-499848?style=for-the-badge&logo=gunicorn&logoColor=white)

</div>

---

## 📌 Overview

This project is not just a static personal website. It is a **dynamic portfolio platform with its own content management system** built using Flask and SQLite.

The public-facing portfolio presents professional information such as education, skills, experience, services, projects, achievements, certifications, testimonials, and contact details, while the private administration area allows the content to be managed without manually editing the source code.

The application also includes user authentication, email verification flows, password recovery, media uploads, contact-message management, and configurable email delivery.

---

## ✨ Core Features

### 🌐 Dynamic Portfolio Website
The public portfolio supports structured sections for:

- Hero / introduction.
- About Me.
- Education.
- Technical and professional skills.
- Work experience and training.
- Services.
- Featured projects.
- Achievements and certifications.
- Testimonials.
- Contact information and call-to-action sections.

Content is stored in the database and rendered dynamically instead of being hard-coded into a single static page.

### ⚙️ Built-In Content Management System
The administration dashboard provides dedicated management interfaces for portfolio content, including:

- Profile information.
- Education records.
- Skills.
- Experience.
- Services.
- Projects.
- Achievements.
- Testimonials.
- Website settings.
- Contact messages.

This makes the portfolio maintainable from the browser without editing HTML or Python code every time content changes.

### 🔐 Authentication System
The application includes a complete authentication workflow with:

- User registration.
- Secure password hashing with Werkzeug.
- Login sessions.
- Email verification using OTP codes.
- Password-reset workflow.
- Email-change verification.
- Protected administration routes.

### 📧 Email Integration
Email workflows can use multiple providers depending on deployment configuration:

- **Brevo API**.
- **Resend API**.
- **Gmail SMTP** fallback.

These integrations support workflows such as:

- OTP verification emails.
- Password-reset emails.
- Account-related notifications.
- Contact-form communication.

### 🖼️ Media Uploads
The CMS supports image uploads for portfolio content.

Uploaded files are:

- Restricted to approved image formats.
- Renamed using generated unique identifiers.
- Stored under the application's static upload directory.
- Limited in size for safer uploads.

Supported formats include:

```text
PNG, JPG, JPEG, GIF, WEBP
```

### 💬 Contact System
Visitors can submit messages directly through the portfolio.

Messages can then be handled through the administration dashboard, while email integration can be used to forward or notify the portfolio owner.

### 🗄️ SQLite Database
Portfolio content, settings, user data, and administrative information are stored in a local SQLite database, making the project easy to run locally while still supporting a full dynamic backend.

---

## 🧠 Architecture

```text
                    Visitor
                       │
                       ▼
               Public Portfolio
                       │
                 Flask Routes
                       │
          ┌────────────┴────────────┐
          │                         │
          ▼                         ▼
      SQLite DB                Email Services
          │              Brevo / Resend / SMTP
          │
          ▼
      Admin CMS
          │
 ┌────────┼─────────┬──────────┐
 ▼        ▼         ▼          ▼
Projects Skills  Education  Experience ...
```

---

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| **Python** | Backend application logic |
| **Flask** | Web framework and routing |
| **SQLite** | Persistent application database |
| **Werkzeug** | Password hashing, security helpers, and file handling |
| **Jinja2** | Dynamic HTML templating through Flask |
| **HTML / CSS / JavaScript** | Frontend interface and interaction |
| **Gunicorn** | Production WSGI server |
| **Brevo / Resend / SMTP** | Transactional email workflows |

---

## 📁 Project Structure

```text
portfolio/
│
├── app.py                  # Main Flask application and backend logic
├── portfolio.db            # SQLite database
├── requirements.txt        # Python dependencies
├── Procfile                # Production process configuration
│
├── templates/
│   ├── index.html          # Public portfolio page
│   ├── base.html           # Shared template layout
│   │
│   ├── admin/              # CMS and admin dashboard templates
│   │   ├── dashboard.html
│   │   ├── profile.html
│   │   ├── education.html
│   │   ├── skills.html
│   │   ├── experience.html
│   │   ├── services.html
│   │   ├── project_form.html
│   │   ├── achievements.html
│   │   ├── testimonials.html
│   │   ├── messages.html
│   │   └── settings.html
│   │
│   ├── auth/               # Authentication templates
│   │   ├── register.html
│   │   ├── verify_otp.html
│   │   ├── forgot_password.html
│   │   ├── reset_password.html
│   │   └── verify_email_change.html
│   │
│   ├── errors/             # Custom error pages
│   └── themes/             # Theme-related templates
│
└── static/
    └── uploads/             # Uploaded portfolio media
```

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/R3Dzf/portfolio.git
cd portfolio
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it:

#### Windows

```bash
venv\Scripts\activate
```

#### Linux / macOS

```bash
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Set a secure Flask secret key and explicit administrator credentials before deployment. The application no longer creates a default administrator password.

Example:

```env
SECRET_KEY=replace-with-a-secure-random-value
ADMIN_USER=admin
ADMIN_EMAIL=admin@example.com
ADMIN_PASS=replace-with-a-strong-password
```

Optional email configuration:

```env
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-app-password
MAIL_RECIPIENT=your-email@example.com

RESEND_API_KEY=your-resend-api-key
BREVO_API_KEY=your-brevo-api-key
```

> Do not commit real passwords or API keys to the repository.

### 5. Run locally

```bash
python app.py
```

For a production-style deployment using Gunicorn:

```bash
gunicorn app:app
```

---

## 🔐 Security Features

The project includes several practical security measures:

- Password hashing instead of plain-text passwords.
- Session-based authentication.
- Protected administrative routes.
- Restricted upload extensions.
- Maximum upload-size limit.
- Secure generated filenames for uploaded media.
- Environment-variable configuration for credentials and API keys.
- OTP-based verification workflows.

For any real production deployment, administrator passwords and the Flask secret key should always be changed from development defaults.

---

## 📧 Email Delivery Strategy

The application can attempt email delivery through multiple channels:

```text
Brevo API
    ↓ fallback
Resend API
    ↓ fallback
Gmail SMTP
```

This provides flexibility across different hosting environments where SMTP access or a specific email provider may not always be available.

---

## 💡 Engineering Highlights

This project demonstrates practical experience with:

- Full-stack Flask development.
- Relational database integration.
- Authentication and session management.
- Secure password handling.
- OTP verification systems.
- CRUD-based content management.
- Dynamic Jinja templates.
- File upload handling.
- Transactional email integrations.
- Admin dashboard development.
- Contact-form processing.
- Production deployment using Gunicorn.
- Environment-based application configuration.

---

## 🔮 Possible Future Improvements

- Move from SQLite to PostgreSQL for larger deployments.
- Add database migrations with Flask-Migrate / Alembic.
- Add automated tests.
- Add CSRF protection across forms.
- Add rate limiting for authentication and contact endpoints.
- Add image compression and automatic WebP conversion.
- Add analytics for portfolio visitors and project clicks.
- Add REST API endpoints for external integrations.
- Add Docker support and CI/CD deployment workflows.

---

## 👨‍💻 Author

**Ahmed Youssef (Ahmed Bosha)**  
Computer & Control Engineering Student

GitHub: [@R3Dzf](https://github.com/R3Dzf)

---

<div align="center">

### ⭐ Built as a dynamic portfolio, CMS, and practical full-stack Flask project.

</div>
