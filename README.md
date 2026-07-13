# Trekk Management App

A multi-user trek booking and management system built for the MAD-I project.
Admins publish and manage treks, trek staff run them on the ground, and
trekkers browse, book, and track their trekking history.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Flask (application factory + blueprints) |
| Auth | Flask-Login with role-based access control |
| ORM / DB | Flask-SQLAlchemy on **SQLite** (created programmatically — no manual DB tools) |
| Frontend | Jinja2 templates, HTML, custom CSS, Bootstrap 5 |
| Charts | Chart.js (visual enhancement only — all data is computed server-side; core features work without JavaScript) |

## Setup

```bash
# 1. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create the database tables and the admin account (programmatic)
python seed_admin.py

# 4. Apply the lifecycle schema columns (idempotent; safe to re-run)
python migrate_db.py

# 5. Run
python run.py
```

Open **http://127.0.0.1:5000**.

## Default Credentials

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `admin123` |

Trekkers self-register (active immediately). Trek staff self-register but
**cannot log in until an admin approves them** (Admin → Staff → Approve).

## Roles & Features

### Admin
- Dashboard with totals (treks, users, staff, bookings, revenue) and Chart.js analytics
- Create / edit / delete treks
- Trek lifecycle control: `pending → approved → open → closed/ongoing → completed`
  (a trek accepts bookings **only** while `open`)
- Approve, reject, blacklist/reactivate staff; assign/unassign staff to treks
- Blacklist/reactivate users (a blacklisted user loses access immediately)
- View all users, staff, treks, bookings; full trekking history with filters
- Search across treks, staff, and users

### Trek Staff
- Self-registration with profile (requires admin approval)
- Dashboard of assigned treks with participant counts and analytics
- Update available slots and trek status (start → ongoing → completed, with completion notes)
- View participant lists per trek
- **Only assigned staff** can manage a trek's records

### Trekker (User)
- Self-registration, login, profile editing (email / password)
- Browse **open** treks; search by keyword; filter by difficulty and location; sort
- Book treks (participant count, auto-calculated total)
- View bookings with live status; cancel active bookings (slots are released)
- Trekking history of completed and cancelled treks with personal analytics

## Core Rules Enforced

- **No overbooking** — bookings beyond available slots are rejected
- **No duplicate bookings** — one active booking per user per trek
- **Open-only booking** — pending/approved/closed/ongoing/completed treks cannot be booked
- **Completion cascade** — completing a trek marks every active booking completed,
  which is what populates each trekker's history
- **Full history** — admins can view all users' booking records at `/admin/history`

## Project Structure

```
app/
├── models/        # User, Trek, Booking, StaffProfile, TrekAssignment
├── routes/        # auth, admin, staff, trekker blueprints
├── templates/     # Jinja2 (base + per-role pages + reusable chart component)
├── static/        # custom CSS, Chart.js dashboard components
└── utils/         # role decorators, trek status lifecycle, analytics queries
config.py          # SQLite config
seed_admin.py      # programmatic DB creation + admin seed
migrate_db.py      # idempotent schema migration
run.py             # entry point
```

## Notes

- The database file lives in `instance/` (gitignored); it is always created by
  the scripts above, never manually.
- Bootstrap, Chart.js, and fonts load from CDNs, so first load needs internet;
  every core feature is server-rendered and works with JavaScript disabled.
