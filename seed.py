"""
seed.py — Populate the database with demo data for the PoC presentation.
Run once after creating the database: python seed.py
"""
import sys
from datetime import datetime, timedelta, timezone

from werkzeug.security import generate_password_hash

from app import app
from models import Assignment, CallerID, TeamMember, User, db

# ---------------------------------------------------------------------------
# Demo users
# (username, password, display_name, role)
# ---------------------------------------------------------------------------
DEMO_USERS = [
    ('admin',       'Admin@123',      'Sarah Chen',    'admin'),
    ('jsmith',      'User@123',       'John Smith',    'user'),
    ('agarcia',     'User@123',       'Ana Garcia',    'user'),
    ('mwilson',     'User@123',       'Mike Wilson',   'user'),
    ('rwang',       'User@123',       'Rachel Wang',   'user'),
    ('tom.harris',  'Complaint@123',  'Tom Harris',    'complaint'),
    ('lisa.park',   'Complaint@123',  'Lisa Park',     'complaint'),
    ('raj.mehta',   'Complaint@123',  'Raj Mehta',     'complaint'),
    ('emma.brown',  'Complaint@123',  'Emma Brown',    'complaint'),
]

# ---------------------------------------------------------------------------
# Demo CallerIDs — all pre-seeded as 'queued' so the admin can trigger
# assignments live during the presentation.
# (caller_id_number, aws_recording_url, submitted_by_username)
# ---------------------------------------------------------------------------
DEMO_CALLER_IDS = [
    ('61294881234', 'https://demo-recordings.example.com/call-001.mp3', 'jsmith'),
    ('61295556789', 'https://demo-recordings.example.com/call-002.mp3', 'agarcia'),
    ('61296661234', 'https://demo-recordings.example.com/call-003.mp3', 'mwilson'),
    ('61297772345', 'https://demo-recordings.example.com/call-004.mp3', 'rwang'),
    ('61298883456', 'https://demo-recordings.example.com/call-005.mp3', 'jsmith'),
    ('61299994567', 'https://demo-recordings.example.com/call-006.mp3', 'agarcia'),
    ('61200005678', 'https://demo-recordings.example.com/call-007.mp3', 'mwilson'),
    ('61201116789', 'https://demo-recordings.example.com/call-008.mp3', 'rwang'),
    ('61202227890', None,                                               'jsmith'),
    ('61203338901', 'https://demo-recordings.example.com/call-010.mp3', 'agarcia'),
]


def seed():
    with app.app_context():
        db.create_all()

        if User.query.first():
            print('\n⚠️  Database already contains data. Skipping seed.')
            print('   To re-seed: DROP TABLE assignments, caller_ids, team_members, users; then run again.\n')
            sys.exit(0)

        # ── Create Users ────────────────────────────────────────────────────
        user_map = {}
        for username, password, name, role in DEMO_USERS:
            user = User(
                username=username,
                password_hash=generate_password_hash(password),
                name=name,
                role=role,
            )
            db.session.add(user)
            user_map[username] = user

        db.session.flush()  # get auto-generated IDs before FK references

        # ── Create TeamMember records for complaint users ────────────────────
        for username, _, _, role in DEMO_USERS:
            if role == 'complaint':
                db.session.add(TeamMember(
                    user_id=user_map[username].id,
                    self_status='offline',
                    admin_approved=False,
                ))

        db.session.flush()

        # ── Create demo CallerIDs (all queued, spread over the last 2 hours) ─
        base_time = datetime.now(timezone.utc) - timedelta(hours=2)
        for i, (cid_number, aws_url, submitter) in enumerate(DEMO_CALLER_IDS):
            db.session.add(CallerID(
                caller_id_number=cid_number,
                aws_recording_url=aws_url,
                submitted_by_id=user_map[submitter].id,
                submitted_at=base_time + timedelta(minutes=i * 12),
                status='queued',
            ))

        db.session.commit()

        # ── Print credentials ────────────────────────────────────────────────
        print('\n' + '=' * 52)
        print('  ✅  Database seeded — PoC ready to demo!')
        print('=' * 52)
        print(f'\n  {"ROLE":<12} {"USERNAME":<15} {"PASSWORD"}')
        print('  ' + '-' * 44)
        for username, password, _, role in DEMO_USERS:
            print(f'  {role:<12} {username:<15} {password}')
        print()
        print('  🚀  Start the app : python app.py')
        print('  🌐  Open browser  : http://localhost:5000')
        print()
        print('  Demo flow: Complaint members log in → click Present.')
        print('  Admin approves them → first CallerID auto-assigns.')
        print('=' * 52 + '\n')


if __name__ == '__main__':
    seed()
