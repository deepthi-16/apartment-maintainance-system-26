# Apartment Maintenance Management System

A full-stack Flask web application for apartment maintenance ticketing. Residents can submit issues, admins can assign staff and monitor analytics, and staff can resolve assigned tasks.

## Features

- Session-based login with role-aware dashboards for Resident, Admin, and Staff
- Unique tracking IDs generated for every maintenance ticket
- Resident request form and personal ticket tracking
- Admin overview with ticket assignment and status analytics
- Staff task board with quick resolution workflow
- SQLAlchemy ORM with SQLite by default and optional MySQL support via `pymysql`

## Tech Stack

- Python
- Flask
- Flask-SQLAlchemy
- SQLite by default, switchable to MySQL through `DATABASE_URL`
- HTML, CSS, JavaScript

## Project Structure

```text
.
|-- app.py
|-- init_db.py
|-- requirements.txt
|-- templates/
|   |-- base.html
|   |-- login.html
|   |-- resident_dashboard.html
|   |-- admin_dashboard.html
|   `-- staff_dashboard.html
`-- static/
    |-- css/style.css
    `-- js/app.js
```

## How to Run

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the app:

```bash
python app.py
```

4. Open your browser at:

```text
http://127.0.0.1:5000
```

The app auto-creates `maintenance.db` and seeds demo users on first run.

## Demo Credentials

- Resident: `resident1` / `resident123`
- Admin: `admin1` / `admin123`
- Staff: `staff1` / `staff123`
- Staff: `staff2` / `staff123`

## Required API Routes

- `POST /api/tickets`
- `GET /api/tickets/user/<id>`
- `PATCH /api/tickets/assign`
- `PATCH /api/tickets/status`

## Switching to MySQL

Set `DATABASE_URL` before running the app. Example:

```bash
set DATABASE_URL=mysql+pymysql://username:password@localhost/maintenance_db
python app.py
```

## Deployment Notes

- Render can deploy directly from `requirements.txt` with start command `gunicorn app:app`.
- PythonAnywhere is a good free-tier option for Flask hosting.
