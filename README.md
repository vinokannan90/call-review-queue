# Call Review Queue — Proof of Concept

A Python + PostgreSQL web application demonstrating the proposed replacement
for the Microsoft Access call review workflow.

---

## What This PoC Demonstrates

| Feature | Microsoft Access (Current) | This Web App (Proposed) |
|---|---|---|
| Concurrent users | Corrupts above ~15 reliable | Handles hundreds natively |
| User role — submit CallerIDs | Access form | Browser-based form |
| Admin role — team availability | Access form | Live dashboard with toggle |
| Auto queue assignment | VBA macro (fragile) | Server-side logic (reliable) |
| Complaint role — review queue | Access form | Browser-based dashboard |
| Data storage | `.accdb` file on network share | PostgreSQL database (server) |
| Corruption risk | High (file-locking) | None (client-server) |
| Backup proliferation risk | Yes | No |
| Multi-user safety | No | Yes |

---

## Prerequisites

- **Python 3.9+** — [python.org](https://www.python.org/downloads/)
- **No database install required for the PoC** — SQLite is built into Python and works natively
  on all platforms including **Windows ARM (Snapdragon X)**.

> **Production note:** The production deployment uses PostgreSQL. SQLite is used here
> exclusively for the PoC demo. See the *Switching to PostgreSQL* section below.

---

## Setup Instructions (Windows ARM / Any Platform)

### 1. Set Up the Environment

Copy the environment file template:
```
copy .env.example .env
```

The default `.env` is pre-configured for SQLite — **no edits needed** to run the PoC.

```
# Default .env for PoC (SQLite — zero install)
DATABASE_URL=sqlite:///callreview_poc.db
SECRET_KEY=replace-with-any-long-random-string
```

---

### 2. Install Python Dependencies

```
pip install -r requirements.txt
```

---

### 3. Seed the Database with Demo Data

```
python seed.py
```

This creates the `callreview_poc.db` SQLite file, all tables, demo users,
and 10 pre-queued CallerIDs.

---

### 4. Start the Application

```
python app.py
```

Open your browser and go to: **http://localhost:5000**

---

## Switching to PostgreSQL (Production)

When deploying on a proper server, switch the database as follows:

1. Install PostgreSQL on the server
2. Create the database: `psql -U postgres -c "CREATE DATABASE callreview_poc;"`
3. In `.env`, change `DATABASE_URL`:
   ```
   DATABASE_URL=postgresql://postgres:yourpassword@localhost/callreview_poc
   ```
4. In `requirements.txt`, uncomment `psycopg2-binary==2.9.9` and run `pip install -r requirements.txt`
5. Run `python seed.py` to initialize the PostgreSQL database

No application code changes are required — Flask-SQLAlchemy handles both databases
through the same interface.

---

## Demo Credentials

| Role | Username | Password | Purpose |
|------|----------|----------|---------|
| Admin | `admin` | `Admin@123` | Manage team availability, monitor queue |
| User | `jsmith` | `User@123` | Submit CallerIDs for review |
| User | `agarcia` | `User@123` | Submit CallerIDs for review |
| User | `mwilson` | `User@123` | Submit CallerIDs for review |
| User | `rwang` | `User@123` | Submit CallerIDs for review |
| Complaint | `tom.harris` | `Complaint@123` | Process assigned CallerIDs |
| Complaint | `lisa.park` | `Complaint@123` | Process assigned CallerIDs |
| Complaint | `raj.mehta` | `Complaint@123` | Process assigned CallerIDs |
| Complaint | `emma.brown` | `Complaint@123` | Process assigned CallerIDs |

---

## Suggested Demo Walkthrough (for Leadership Presentation)

**Step 1 — The Queue (show the problem this solves)**
1. Log in as `admin`
2. Show the Admin Control Panel — 10 CallerIDs sitting in the queue
3. Point out: all team members are currently Absent, so nothing has been assigned yet

**Step 2 — Trigger Automatic Assignment (the key feature)**
1. Click "Mark Present" on Tom Harris
2. Watch — the first queued CallerID is immediately assigned to Tom
3. Click "Mark Present" on Lisa Park, Raj Mehta, Emma Brown
4. Queue drops by 4 — each present member receives an assignment automatically

**Step 3 — User Submitting (live demo)**
1. Open a new browser tab and log in as `jsmith`
2. Submit a new CallerID with an AWS Recording URL
3. Switch back to the Admin tab — the new CallerID appears already assigned
   (because team members are present and auto-receive assignments)

**Step 4 — Complaint Team Processing**
1. Open a browser tab and log in as `tom.harris`
2. Show the assigned CallerID in the queue
3. Click "Listen to Recording" (opens the AWS URL)
4. Click "Mark Complete"
5. Immediately — the next queued CallerID automatically appears in Tom's queue

**Step 5 — Admin Live View**
1. Switch back to Admin — show the Completed section populating
2. Point out the admin sees every member's current assignment load in real time

---

## Project Structure

```
MicrosoftAccess/
├── app.py                  # Flask application — routes and queue logic
├── models.py               # Database models (User, TeamMember, CallerID, Assignment)
├── seed.py                 # Demo data seeder
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── .gitignore
└── templates/
    ├── base.html           # Shared layout (navbar, flash messages)
    ├── login.html          # Login page
    ├── user_dashboard.html     # User role
    ├── admin_dashboard.html    # Admin role
    └── complaint_dashboard.html # Complaint team role
```

---

## Database Schema

```
users           — id, username, password_hash, name, role
team_members    — id, user_id (FK), is_present
caller_ids      — id, caller_id_number, aws_recording_url, submitted_by_id (FK),
                  submitted_at, status (queued | assigned | completed)
assignments     — id, caller_id_id (FK), team_member_id (FK),
                  assigned_at, completed_at, status (active | completed)
```

---

## Important: Production Requirements

This is a Proof of Concept. Before production use, the following must be addressed:

- [ ] **CSRF Protection** — Add Flask-WTF to protect all forms
- [ ] **HTTPS** — Deploy behind a TLS-terminated reverse proxy (nginx / Azure App Gateway)
- [ ] **Secret Key** — Generate a cryptographically strong `SECRET_KEY` (not the default)
- [ ] **Database Password** — Use a strong PostgreSQL password and environment variables
- [ ] **SELECT FOR UPDATE** — Add row-level locking in `assign_queued_caller_ids()` to prevent
      race conditions under high concurrency (see comment in app.py)
- [ ] **Authentication** — Consider replacing password login with Azure AD SSO via `msal`
- [ ] **Audit Logging** — Add a log table for all user actions (required for finance domain)
- [ ] **Role Enforcement Middleware** — Use a decorator for role checks instead of per-route checks
- [ ] **Production WSGI Server** — Use `gunicorn` instead of Flask's built-in dev server

---

*Built as a PoC to demonstrate the proposed replacement for Microsoft Access.*
*Technology: Python 3 / Flask / PostgreSQL / Bootstrap 5*
