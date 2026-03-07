import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for
from flask_login import (LoginManager, current_user, login_required,
                         login_user, logout_user)
from werkzeug.security import check_password_hash

from models import Assignment, CallerID, QAReview, TeamMember, User, db

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-only-secret-change-in-prod')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 'sqlite:///callreview_poc.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ---------------------------------------------------------------------------
# Queue assignment logic
# ---------------------------------------------------------------------------

def assign_queued_caller_ids():
    """Assign ONE queued CallerID to each eligible member who has no active assignment.

    Eligibility: self_status == 'present' AND admin_approved == True.
    Maximum ONE active assignment per eligible member at any time.
    Assignment order: FIFO (oldest submitted_at first).
    Always commits the session before returning.
    """
    eligible = (
        TeamMember.query
        .filter_by(self_status='present', admin_approved=True)
        .all()
    )

    for member in eligible:
        if member.active_assignment is not None:
            continue  # already has one — skip

        next_caller = (
            CallerID.query
            .filter_by(status='queued')
            .order_by(CallerID.submitted_at)
            .first()
        )
        if next_caller is None:
            break  # queue exhausted

        assignment = Assignment(
            caller_id_id=next_caller.id,
            team_member_id=member.id,
            assigned_at=datetime.now(timezone.utc),
            status='active',
            outcome=None,
        )
        next_caller.status = 'assigned'
        db.session.add(assignment)
        db.session.flush()

    db.session.commit()


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    return redirect(url_for('dashboard') if current_user.is_authenticated else url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    routes = {
        'admin': 'admin_dashboard',
        'complaint': 'complaint_dashboard',
        'user': 'user_dashboard',
        'qa': 'qa_dashboard',
    }
    return redirect(url_for(routes.get(current_user.role, 'user_dashboard')))


# ---------------------------------------------------------------------------
# User role routes
# ---------------------------------------------------------------------------

@app.route('/user/dashboard')
@login_required
def user_dashboard():
    if current_user.role != 'user':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    submissions = (
        CallerID.query
        .filter_by(submitted_by_id=current_user.id)
        .order_by(CallerID.submitted_at.desc())
        .all()
    )
    stats = {
        'total': len(submissions),
        'queued': sum(1 for s in submissions if s.status == 'queued'),
        'assigned': sum(1 for s in submissions if s.status == 'assigned'),
        'completed': sum(1 for s in submissions if s.status in ('dismissed', 'raised', 'reviewed', 'qa_not_required')),
    }
    return render_template('user_dashboard.html', submissions=submissions, stats=stats)


@app.route('/user/submit', methods=['POST'])
@login_required
def submit_caller_id():
    if current_user.role != 'user':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))

    caller_id_number = request.form.get('caller_id', '').strip()
    aws_url = request.form.get('aws_url', '').strip() or None
    reason = request.form.get('reason', '').strip() or None

    if not caller_id_number:
        flash('CallerID is required.', 'danger')
        return redirect(url_for('user_dashboard'))

    if CallerID.query.filter_by(caller_id_number=caller_id_number).first():
        flash(f'CallerID {caller_id_number} has already been submitted.', 'warning')
        return redirect(url_for('user_dashboard'))

    new_entry = CallerID(
        caller_id_number=caller_id_number,
        aws_recording_url=aws_url,
        reason=reason,
        submitted_by_id=current_user.id,
        submitted_at=datetime.now(timezone.utc),
        status='queued',
    )
    db.session.add(new_entry)
    db.session.flush()
    assign_queued_caller_ids()

    flash(f'CallerID {caller_id_number} submitted and queued for assignment.', 'success')
    return redirect(url_for('user_dashboard'))


# ---------------------------------------------------------------------------
# Admin role routes
# ---------------------------------------------------------------------------

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))

    team_members = TeamMember.query.join(User).order_by(User.name).all()

    queued = (
        CallerID.query.filter_by(status='queued')
        .order_by(CallerID.submitted_at)
        .all()
    )

    assigned_items = []
    for caller in (CallerID.query.filter_by(status='assigned')
                   .order_by(CallerID.submitted_at).all()):
        asn = Assignment.query.filter_by(caller_id_id=caller.id, status='active').first()
        assigned_items.append({
            'caller': caller,
            'assigned_to': asn.team_member.user.name if asn else '—',
            'assigned_at': asn.assigned_at if asn else None,
        })

    raised_items = (
        CallerID.query.filter_by(status='raised')
        .order_by(CallerID.submitted_at)
        .all()
    )

    dismissed_items = (
        CallerID.query.filter_by(status='dismissed')
        .order_by(CallerID.submitted_at.desc())
        .limit(20)
        .all()
    )

    stats = {
        'total': CallerID.query.count(),
        'queued': CallerID.query.filter_by(status='queued').count(),
        'assigned': CallerID.query.filter_by(status='assigned').count(),
        'raised': CallerID.query.filter_by(status='raised').count(),
        'dismissed': CallerID.query.filter_by(status='dismissed').count(),
        'eligible': TeamMember.query.filter_by(self_status='present', admin_approved=True).count(),
        'self_present': TeamMember.query.filter_by(self_status='present').count(),
        'team_size': TeamMember.query.count(),
    }

    return render_template(
        'admin_dashboard.html',
        team_members=team_members,
        queued=queued,
        assigned_items=assigned_items,
        raised_items=raised_items,
        dismissed_items=dismissed_items,
        stats=stats,
    )


@app.route('/admin/toggle_approval/<int:member_id>', methods=['POST'])
@login_required
def toggle_approval(member_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))

    member = TeamMember.query.get_or_404(member_id)

    if not member.admin_approved:
        if member.self_status != 'present':
            flash(
                f'{member.user.name} has not marked themselves as Present yet. '
                'Ask them to log in and set their status to Present first.',
                'warning',
            )
            return redirect(url_for('admin_dashboard'))
        member.admin_approved = True
        assign_queued_caller_ids()  # commits
        flash(f'{member.user.name} approved — eligible to receive CallerID assignments.', 'success')
    else:
        member.admin_approved = False
        db.session.commit()
        flash(f'{member.user.name} approval removed.', 'secondary')

    return redirect(url_for('admin_dashboard'))


@app.route('/admin/mark_reviewed/<int:caller_id_id>', methods=['POST'])
@login_required
def mark_reviewed(caller_id_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))

    caller = CallerID.query.get_or_404(caller_id_id)
    if caller.status != 'raised':
        flash('This CallerID is not in raised status.', 'warning')
        return redirect(url_for('admin_dashboard'))

    caller.status = 'reviewed'
    db.session.commit()
    flash(f'CallerID {caller.caller_id_number} marked as reviewed.', 'success')
    return redirect(url_for('admin_dashboard'))


# ---------------------------------------------------------------------------
# Complaint role routes
# ---------------------------------------------------------------------------

@app.route('/complaint/dashboard')
@login_required
def complaint_dashboard():
    if current_user.role != 'complaint':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))

    member = TeamMember.query.filter_by(user_id=current_user.id).first_or_404()
    assignment = member.active_assignment
    history = (
        Assignment.query
        .filter_by(team_member_id=member.id, status='completed')
        .order_by(Assignment.completed_at.desc())
        .limit(15)
        .all()
    )

    return render_template(
        'complaint_dashboard.html',
        member=member,
        assignment=assignment,
        history=history,
    )


@app.route('/complaint/status', methods=['POST'])
@login_required
def update_self_status():
    if current_user.role != 'complaint':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))

    member = TeamMember.query.filter_by(user_id=current_user.id).first_or_404()
    new_status = request.form.get('status', '').strip()

    if new_status not in ('present', 'break', 'signoff'):
        flash('Invalid status.', 'danger')
        return redirect(url_for('complaint_dashboard'))

    if new_status == 'signoff':
        # Return any active assignment to queue — another member will pick it up
        active = member.active_assignment
        if active:
            active.caller_id_ref.status = 'queued'
            db.session.delete(active)
        # Reset admin approval — must be re-approved on the next shift
        member.admin_approved = False
        member.self_status = 'signoff'
        db.session.commit()
        flash('You have signed off for this shift. See you next time!', 'info')
        return redirect(url_for('complaint_dashboard'))

    if new_status == 'break':
        member.self_status = 'break'
        db.session.commit()
        flash(
            'You are on break. Complete your current assignment if you have one. '
            'No new CallerIDs will be assigned while you are on break.',
            'warning',
        )
        return redirect(url_for('complaint_dashboard'))

    # new_status == 'present' (returning from break or starting a new shift)
    member.self_status = 'present'
    db.session.flush()
    if member.admin_approved:
        assign_queued_caller_ids()  # commits
        flash('You are Present and eligible for assignments.', 'success')
    else:
        db.session.commit()
        flash(
            'You are marked Present. Waiting for admin approval before assignments begin.',
            'info',
        )
    return redirect(url_for('complaint_dashboard'))


@app.route('/complaint/analyse/<int:assignment_id>')
@login_required
def analyse_assignment(assignment_id):
    if current_user.role != 'complaint':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))

    member = TeamMember.query.filter_by(user_id=current_user.id).first_or_404()
    assignment = Assignment.query.get_or_404(assignment_id)

    if assignment.team_member_id != member.id:
        flash('You are not authorized to access this assignment.', 'danger')
        return redirect(url_for('complaint_dashboard'))

    if assignment.status != 'active':
        flash('This assignment is no longer active.', 'warning')
        return redirect(url_for('complaint_dashboard'))

    return render_template('complaint_analyse.html', assignment=assignment, member=member)


@app.route('/complaint/submit/<int:assignment_id>', methods=['POST'])
@login_required
def submit_outcome(assignment_id):
    if current_user.role != 'complaint':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))

    member = TeamMember.query.filter_by(user_id=current_user.id).first_or_404()
    assignment = Assignment.query.get_or_404(assignment_id)

    if assignment.team_member_id != member.id:
        flash('You are not authorized to submit this assignment.', 'danger')
        return redirect(url_for('complaint_dashboard'))

    if assignment.status != 'active':
        flash('This assignment is no longer active.', 'warning')
        return redirect(url_for('complaint_dashboard'))

    outcome = request.form.get('outcome', '').strip()
    if outcome not in ('dismiss', 'raised'):
        flash('Please select an outcome — Dismiss or Raised — before submitting.', 'danger')
        return redirect(url_for('analyse_assignment', assignment_id=assignment_id))

    core_id = None
    raised_comment = None
    if outcome == 'raised':
        core_id = request.form.get('core_id', '').strip() or None
        if not core_id:
            flash('Please provide a CORE ID when raising a case.', 'danger')
            return redirect(url_for('analyse_assignment', assignment_id=assignment_id))
        raised_comment = request.form.get('raised_comment', '').strip() or None

    caller_number = assignment.caller_id_ref.caller_id_number
    assignment.status = 'completed'
    assignment.completed_at = datetime.now(timezone.utc)
    assignment.outcome = outcome
    assignment.caller_id_ref.status = 'dismissed' if outcome == 'dismiss' else 'raised'
    if outcome == 'raised':
        assignment.caller_id_ref.core_id = core_id
        assignment.caller_id_ref.raised_comment = raised_comment
    if outcome == 'dismiss':
        qa_record = QAReview(
            caller_id_id=assignment.caller_id_id,
            dismissed_by_id=current_user.id,
            dismissed_at=datetime.now(timezone.utc),
        )
        db.session.add(qa_record)
    db.session.flush()

    # If still eligible, immediately auto-assign next queued CallerID
    if member.is_eligible:
        assign_queued_caller_ids()  # commits
    else:
        db.session.commit()

    outcome_label = 'sent to QA queue' if outcome == 'dismiss' else 'raised for admin review'
    flash(f'CallerID {caller_number} {outcome_label}. You are ready for the next assignment.', 'success')
    return redirect(url_for('complaint_dashboard'))


# ---------------------------------------------------------------------------
# QA Review role routes
# ---------------------------------------------------------------------------

@app.route('/qa/dashboard')
@login_required
def qa_dashboard():
    if current_user.role != 'qa':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))

    pending = (
        QAReview.query
        .filter_by(verdict=None)
        .order_by(QAReview.dismissed_at)
        .all()
    )
    completed = (
        QAReview.query
        .filter(QAReview.verdict.isnot(None))
        .order_by(QAReview.reviewed_at.desc())
        .limit(20)
        .all()
    )
    return render_template('qa_dashboard.html', pending=pending, completed=completed)


@app.route('/qa/submit/<int:qa_review_id>', methods=['POST'])
@login_required
def qa_submit(qa_review_id):
    if current_user.role != 'qa':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))

    review = QAReview.query.get_or_404(qa_review_id)
    if review.verdict is not None:
        flash('This case has already been reviewed.', 'warning')
        return redirect(url_for('qa_dashboard'))

    verdict = request.form.get('verdict', '').strip()
    justification = request.form.get('justification', '').strip() or None

    if verdict not in ('required', 'not_required'):
        flash('Please select a verdict — Required or Not Required.', 'danger')
        return redirect(url_for('qa_dashboard'))

    if not justification:
        flash('Please provide a justification before submitting.', 'danger')
        return redirect(url_for('qa_dashboard'))

    review.verdict = verdict
    review.justification = justification
    review.reviewed_by_id = current_user.id
    review.reviewed_at = datetime.now(timezone.utc)

    caller = review.caller_id_ref
    caller_number = caller.caller_id_number

    if verdict == 'required':
        caller.status = 'queued'
        db.session.flush()
        assign_queued_caller_ids()  # commits
        flash(f'CallerID {caller_number} marked as Required — re-queued for complaint review.', 'success')
    else:
        caller.status = 'qa_not_required'
        db.session.commit()
        flash(f'CallerID {caller_number} marked as Not Required — case closed.', 'success')

    return redirect(url_for('qa_dashboard'))


if __name__ == '__main__':
    app.run(debug=True, port=5000)
