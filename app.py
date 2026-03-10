import os
import logging
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for, jsonify
from flask_login import (LoginManager, current_user, login_required,
                         login_user, logout_user)
from flask_wtf import CSRFProtect
from werkzeug.security import check_password_hash

from models import Assignment, AttendanceLog, CallerID, QAReview, TeamMember, User, db
from security_config import (
    InputValidator, 
    rate_limiter, 
    rate_limit, 
    require_role,
    get_security_headers,
    validate_security_config
)

load_dotenv()

# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

def ensure_utc(dt):
    """
    Ensure a datetime object is timezone-aware (UTC).
    SQLite stores datetimes as naive strings; this helper adds timezone info.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

# Load version from VERSION file
def get_version():
    version_file = os.path.join(os.path.dirname(__file__), 'VERSION')
    try:
        with open(version_file, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return '0.2.0'

__version__ = get_version()

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Security Configuration
# ---------------------------------------------------------------------------

# Load SECRET_KEY from environment (REQUIRED for production)
secret_key = os.environ.get('SECRET_KEY')
if not secret_key or secret_key == 'dev-only-secret-change-in-prod':
    if os.environ.get('FLASK_ENV') == 'production':
        raise ValueError("SECRET_KEY must be set in production environment")
    # Development fallback (will show warning)
    secret_key = 'dev-only-secret-change-in-prod'
    print("[WARNING] Using default SECRET_KEY. Set SECRET_KEY environment variable for production.")

app.config['SECRET_KEY'] = secret_key
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 'sqlite:///callreview_poc.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Session Security
app.config['SESSION_COOKIE_HTTPONLY'] = os.environ.get('SESSION_COOKIE_HTTPONLY', 'True').lower() == 'true'
app.config['SESSION_COOKIE_SAMESITE'] = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
app.config['PERMANENT_SESSION_LIFETIME'] = int(os.environ.get('PERMANENT_SESSION_LIFETIME', '3600'))  # 1 hour

# Request size limit (prevent large payload attacks)
app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_CONTENT_LENGTH', str(16 * 1024 * 1024)))  # 16MB

# WTF/CSRF Configuration
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_TIME_LIMIT'] = None  # CSRF tokens don't expire (use session expiry)
app.config['WTF_CSRF_CHECK_DEFAULT'] = True

# Initialize extensions
db.init_app(app)
csrf = CSRFProtect(app)

# Configure logging
log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Flask-Login configuration
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'
login_manager.session_protection = 'strong'  # Protect against session hijacking


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ---------------------------------------------------------------------------
# Security Headers & Request/Response Hooks
# ---------------------------------------------------------------------------

@app.after_request
def set_security_headers(response):
    """Apply security headers to all responses."""
    headers = get_security_headers()
    for header, value in headers.items():
        response.headers[header] = value
    return response


@app.before_request
def log_request_info():
    """Log security-relevant request information."""
    if request.endpoint and not request.endpoint.startswith('static'):
        logger.info(f"{request.method} {request.path} - User: {current_user.username if current_user.is_authenticated else 'Anonymous'} - IP: {request.remote_addr}")


@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit exceeded errors."""
    logger.warning(f"Rate limit exceeded - IP: {request.remote_addr} - Endpoint: {request.endpoint}")
    flash('Too many requests. Please try again later.', 'danger')
    return render_template('login.html'), 429


@app.errorhandler(403)
def forbidden_handler(e):
    """Handle forbidden errors."""
    logger.warning(f"Forbidden access - User: {current_user.username if current_user.is_authenticated else 'Anonymous'} - IP: {request.remote_addr}")
    flash('Access denied.', 'danger')
    return redirect(url_for('dashboard' if current_user.is_authenticated else 'login'))


@app.errorhandler(404)
def not_found_handler(e):
    """Handle not found errors (prevent information disclosure)."""
    return render_template('login.html'), 404


@app.errorhandler(500)
def internal_error_handler(e):
    """Handle internal server errors (prevent information disclosure)."""
    logger.error(f"Internal server error: {str(e)}", exc_info=True)
    flash('An internal error occurred. Please try again later.', 'danger')
    return redirect(url_for('dashboard' if current_user.is_authenticated else 'login'))


# Make version available to all templates
@app.context_processor
def inject_version():
    return {'app_version': __version__}


# ---------------------------------------------------------------------------
# Queue assignment logic
# ---------------------------------------------------------------------------

def assign_queued_caller_ids():
    """Assign ONE queued CallerID to each eligible member who has no active assignment.

    Eligibility: self_status == 'present' AND admin_approved == True.
    Maximum ONE active assignment per eligible member at any time.
    Assignment order: 
      1. Manually reserved CallerIDs for this member (oldest first)
      2. General queue FIFO (oldest submitted_at first, not manually reserved)
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

        # First, check if there are any CallerIDs manually reserved for this member
        next_caller = (
            CallerID.query
            .filter_by(status='queued', reserved_for_member_id=member.id)
            .order_by(CallerID.reserved_at)
            .first()
        )
        
        # If no reserved CallerIDs, get from general queue (not reserved for anyone)
        if next_caller is None:
            next_caller = (
                CallerID.query
                .filter_by(status='queued', reserved_for_member_id=None)
                .order_by(CallerID.submitted_at)
                .first()
            )
        
        if next_caller is None:
            continue  # no CallerIDs available for this member

        assignment = Assignment(
            caller_id_id=next_caller.id,
            team_member_id=member.id,
            assigned_at=datetime.now(timezone.utc),
            status='active',
            outcome=None,
        )
        next_caller.status = 'assigned'
        # Clear reservation when assigned
        next_caller.reserved_for_member_id = None
        next_caller.reserved_at = None
        next_caller.reserved_by_id = None
        
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
@rate_limit(limit=10, window_seconds=300)  # 10 attempts per 5 minutes
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = InputValidator.sanitize_string(request.form.get('username', ''), 80)
        password = request.form.get('password', '')
        
        if not username or not password:
            logger.warning(f"Login attempt with missing credentials - IP: {request.remote_addr}")
            flash('Invalid username or password.', 'danger')
            return render_template('login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=False)
            rate_limiter.reset(request.remote_addr)  # Reset rate limit on successful login
            logger.info(f"Successful login - User: {username} - IP: {request.remote_addr}")
            return redirect(url_for('dashboard'))
        
        logger.warning(f"Failed login attempt - Username: {username} - IP: {request.remote_addr}")
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
@require_role('user')
def user_dashboard():
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
@require_role('user', 'qa')
@rate_limit(limit=30, window_seconds=60)  # 30 submissions per minute
def submit_caller_id():
    """Submit a new CallerID with input validation."""
    caller_id_number = InputValidator.sanitize_string(
        request.form.get('caller_id', ''), 
        InputValidator.MAX_CALLER_ID_LENGTH
    )
    aws_url = InputValidator.sanitize_string(
        request.form.get('aws_url', ''), 
        InputValidator.MAX_URL_LENGTH
    )
    reason = InputValidator.sanitize_string(
        request.form.get('reason', ''), 
        InputValidator.MAX_REASON_LENGTH
    )

    # Validate CallerID
    is_valid, error_msg = InputValidator.validate_caller_id(caller_id_number)
    if not is_valid:
        flash(error_msg, 'danger')
        logger.warning(f"Invalid CallerID submission - User: {current_user.username} - Error: {error_msg}")
        return redirect(url_for('qa_dashboard' if current_user.role == 'qa' else 'user_dashboard'))
    
    # Validate URL if provided
    if aws_url:
        is_valid, error_msg = InputValidator.validate_url(aws_url, required=False)
        if not is_valid:
            flash(error_msg, 'danger')
            logger.warning(f"Invalid URL submission - User: {current_user.username} - Error: {error_msg}")
            return redirect(url_for('qa_dashboard' if current_user.role == 'qa' else 'user_dashboard'))

    # Check for duplicates
    if CallerID.query.filter_by(caller_id_number=caller_id_number).first():
        flash(f'CallerID {caller_id_number} has already been submitted.', 'warning')
        return redirect(url_for('qa_dashboard' if current_user.role == 'qa' else 'user_dashboard'))

    try:
        new_entry = CallerID(
            caller_id_number=caller_id_number,
            aws_recording_url=aws_url or None,
            reason=reason or None,
            submitted_by_id=current_user.id,
            submitted_at=datetime.now(timezone.utc),
            status='queued',
        )
        db.session.add(new_entry)
        db.session.flush()
        assign_queued_caller_ids()
        
        logger.info(f"CallerID submitted - User: {current_user.username} - CallerID: {caller_id_number}")
        flash(f'CallerID {caller_id_number} submitted and queued for assignment.', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error submitting CallerID - User: {current_user.username} - Error: {str(e)}")
        flash('An error occurred while submitting. Please try again.', 'danger')
    
    if current_user.role == 'qa':
        return redirect(url_for('qa_dashboard'))
    return redirect(url_for('user_dashboard'))


# ---------------------------------------------------------------------------
# Admin role routes
# ---------------------------------------------------------------------------

@app.route('/admin/dashboard')
@login_required
@require_role('admin')
def admin_dashboard():
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
@require_role('admin')
@rate_limit(limit=60, window_seconds=60)
def toggle_approval(member_id):
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
        logger.info(f"Member approved - Admin: {current_user.username} - Member: {member.user.username}")
        flash(f'{member.user.name} approved — eligible to receive CallerID assignments.', 'success')
    else:
        member.admin_approved = False
        db.session.commit()
        logger.info(f"Member approval removed - Admin: {current_user.username} - Member: {member.user.username}")
        flash(f'{member.user.name} approval removed.', 'secondary')

    return redirect(url_for('admin_dashboard'))


@app.route('/admin/reports')
@login_required
@require_role('admin')
def admin_reports():
    """Generate performance reports for complaint team members."""
    from datetime import date, timedelta
    
    # Get filter parameters
    filter_type = request.args.get('filter', 'today')  # today, week, month, custom
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    # Calculate date range based on filter
    today = date.today()
    
    if filter_type == 'today':
        start_date = today
        end_date = today
        filter_label = 'Today'
    elif filter_type == 'week':
        start_date = today - timedelta(days=today.weekday())  # Monday of current week
        end_date = today
        filter_label = 'This Week'
    elif filter_type == 'month':
        start_date = today.replace(day=1)  # First day of current month
        end_date = today
        filter_label = 'This Month'
    elif filter_type == 'custom' and start_date_str and end_date_str:
        try:
            start_date = date.fromisoformat(start_date_str)
            end_date = date.fromisoformat(end_date_str)
            
            # Validate date range
            if end_date < start_date:
                flash('End date must be after start date.', 'danger')
                return redirect(url_for('admin_reports'))
            
            # Limit custom range to 14 days
            if (end_date - start_date).days > 14:
                flash('Date range cannot exceed 14 days.', 'danger')
                return redirect(url_for('admin_reports'))
            
            filter_label = f'{start_date.strftime("%b %d")} - {end_date.strftime("%b %d, %Y")}'
        except ValueError:
            flash('Invalid date format.', 'danger')
            return redirect(url_for('admin_reports'))
    else:
        # Default to today if invalid filter
        start_date = today
        end_date = today
        filter_label = 'Today'
        filter_type = 'today'
    
    # Query attendance logs for the date range
    attendance_logs = (
        AttendanceLog.query
        .filter(AttendanceLog.log_date >= start_date)
        .filter(AttendanceLog.log_date <= end_date)
        .join(TeamMember)
        .join(User)
        .order_by(User.name, AttendanceLog.log_date)
        .all()
    )
    
    # Aggregate data by team member
    member_data = {}
    for log in attendance_logs:
        member_id = log.team_member_id
        if member_id not in member_data:
            member_data[member_id] = {
                'member': log.team_member,
                'total_processed': 0,
                'total_dismissed': 0,
                'total_raised': 0,
                'total_working_seconds': 0,
                'total_break_seconds': 0,
                'days_worked': 0,
                'raised_details': []
            }
        
        member_data[member_id]['total_processed'] += log.callers_processed
        member_data[member_id]['total_dismissed'] += log.callers_dismissed
        member_data[member_id]['total_raised'] += log.callers_raised
        member_data[member_id]['days_worked'] += 1
        
        # Calculate working time for this day
        if log.clock_out_time:
            total_time = (log.clock_out_time - log.clock_in_time).total_seconds()
            working_time = total_time - log.total_break_seconds
            member_data[member_id]['total_working_seconds'] += working_time
            member_data[member_id]['total_break_seconds'] += log.total_break_seconds
        elif log.clock_in_time:
            # Still clocked in - calculate up to now
            now_utc = datetime.now(timezone.utc)
            clock_in_utc = ensure_utc(log.clock_in_time)
            total_time = (now_utc - clock_in_utc).total_seconds()
            current_break = log.total_break_seconds
            if log.current_break_start:
                break_start_utc = ensure_utc(log.current_break_start)
                current_break += (now_utc - break_start_utc).total_seconds()
            working_time = total_time - current_break
            member_data[member_id]['total_working_seconds'] += working_time
            member_data[member_id]['total_break_seconds'] += current_break
    
    # Get raised CallerID details for the date range
    raised_callers = (
        CallerID.query
        .join(Assignment)
        .filter(Assignment.status == 'completed')
        .filter(Assignment.outcome == 'raised')
        .filter(Assignment.completed_at >= datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc))
        .filter(Assignment.completed_at <= datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc))
        .all()
    )
    
    # Add raised details to member data
    for caller in raised_callers:
        # Find the assignment that raised this caller
        assignment = (
            Assignment.query
            .filter_by(caller_id_id=caller.id, outcome='raised')
            .order_by(Assignment.completed_at.desc())
            .first()
        )
        if assignment:
            member_id = assignment.team_member_id
            if member_id in member_data:
                member_data[member_id]['raised_details'].append({
                    'caller_id': caller.caller_id_number,
                    'core_id': caller.core_id,
                    'comment': caller.raised_comment,
                    'completed_at': assignment.completed_at
                })
    
    # Convert to list and sort by total processed
    report_data = list(member_data.values())
    report_data.sort(key=lambda x: x['total_processed'], reverse=True)
    
    return render_template(
        'admin_reports.html',
        report_data=report_data,
        filter_type=filter_type,
        filter_label=filter_label,
        start_date=start_date,
        end_date=end_date,
    )


@app.route('/admin/reset_timer/<int:member_id>/<timer_type>', methods=['POST'])
@login_required
@require_role('admin')
@rate_limit(limit=30, window_seconds=60)
def reset_timer(member_id, timer_type):
    """Reset working or break timer for a team member"""
    from datetime import datetime, timezone
    
    if timer_type not in ['working', 'break']:
        return jsonify({'success': False, 'error': 'Invalid timer type'}), 400
    
    member = TeamMember.query.get_or_404(member_id)
    attendance = member.today_attendance
    
    if not attendance:
        return jsonify({'success': False, 'error': 'No attendance record found for today'}), 404
    
    try:
        if timer_type == 'working':
            # Reset working timer: set clock_in to now, keep break times
            attendance.clock_in_time = datetime.now(timezone.utc)
            # If member is currently on break, reset break start time as well
            if attendance.current_break_start:
                attendance.current_break_start = datetime.now(timezone.utc)
        else:  # break
            # Reset break timer: clear all break data
            attendance.total_break_seconds = 0
            if attendance.current_break_start:
                # If currently on break, restart it from now
                attendance.current_break_start = datetime.now(timezone.utc)
        
        attendance.last_updated = datetime.now(timezone.utc)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/mark_reviewed/<int:caller_id_id>', methods=['POST'])
@login_required
@require_role('admin')
@rate_limit(limit=60, window_seconds=60)
def mark_reviewed(caller_id_id):
    caller = CallerID.query.get_or_404(caller_id_id)
    if caller.status != 'raised':
        flash('This CallerID is not in raised status.', 'warning')
        return redirect(url_for('admin_dashboard'))

    caller.status = 'reviewed'
    db.session.commit()
    logger.info(f"CallerID marked reviewed - Admin: {current_user.username} - CallerID: {caller.caller_id_number}")
    flash(f'CallerID {caller.caller_id_number} marked as reviewed.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/assign_manual/<int:caller_id_id>/<int:member_id>', methods=['POST'])
@login_required
@require_role('admin')
@rate_limit(limit=120, window_seconds=60)  # 120 drag-drop operations per minute
@csrf.exempt  # AJAX endpoint - CSRF handled by custom header check
def assign_manual(caller_id_id, member_id):
    # Verify AJAX request (additional security layer)
    if not request.is_json and request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        logger.warning(f"Invalid manual assignment request - Admin: {current_user.username}")
        return jsonify({'success': False, 'message': 'Invalid request'}), 400

    caller = CallerID.query.get_or_404(caller_id_id)
    member = TeamMember.query.get_or_404(member_id)

    # Validate CallerID is queued and not already reserved
    if caller.status != 'queued':
        return jsonify({'success': False, 'message': 'CallerID is not in queued status'}), 400
    
    if caller.reserved_for_member_id is not None:
        return jsonify({'success': False, 'message': 'CallerID is already reserved for another team member'}), 400

    # Validate team member can receive manual assignment
    if member.self_status not in ('present', 'break'):
        return jsonify({'success': False, 'message': f'{member.user.name} is not available (status: {member.self_status})'}), 400
    
    if member.reserved_count >= 3:
        return jsonify({'success': False, 'message': f'{member.user.name} already has 3 CallerIDs reserved'}), 400

    try:
        # Assign manually
        caller.reserved_for_member_id = member.id
        caller.reserved_at = datetime.now(timezone.utc)
        caller.reserved_by_id = current_user.id
        db.session.commit()
        
        logger.info(f"Manual assignment - Admin: {current_user.username} - CallerID: {caller.caller_id_number} - Member: {member.user.username}")
        
        return jsonify({
            'success': True, 
            'message': f'CallerID {caller.caller_id_number} reserved for {member.user.name}',
            'reserved_count': member.reserved_count
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in manual assignment - Error: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@app.route('/admin/unassign_manual/<int:caller_id_id>', methods=['POST'])
@login_required
@require_role('admin')
@rate_limit(limit=120, window_seconds=60)
@csrf.exempt  # AJAX endpoint - CSRF handled by custom header check
def unassign_manual(caller_id_id):
    # Verify AJAX request
    if not request.is_json and request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        logger.warning(f"Invalid unassignment request - Admin: {current_user.username}")
        return jsonify({'success': False, 'message': 'Invalid request'}), 400

    caller = CallerID.query.get_or_404(caller_id_id)

    if caller.reserved_for_member_id is None:
        return jsonify({'success': False, 'message': 'CallerID is not manually reserved'}), 400

    try:
        # Clear reservation
        member_name = caller.reserved_for.user.name
        member_username = caller.reserved_for.user.username
        caller.reserved_for_member_id = None
        caller.reserved_at = None
        caller.reserved_by_id = None
        db.session.commit()
        
        logger.info(f"Manual unassignment - Admin: {current_user.username} - CallerID: {caller.caller_id_number} - Member: {member_username}")
        
        return jsonify({
            'success': True,
            'message': f'CallerID {caller.caller_id_number} reservation removed from {member_name}'
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in manual unassignment - Error: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


# ---------------------------------------------------------------------------
# Complaint role routes
# ---------------------------------------------------------------------------

@app.route('/complaint/dashboard')
@login_required
@require_role('complaint')
def complaint_dashboard():
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
@require_role('complaint')
@rate_limit(limit=30, window_seconds=60)
def update_self_status():
    from datetime import date
    member = TeamMember.query.filter_by(user_id=current_user.id).first_or_404()
    new_status = InputValidator.sanitize_string(request.form.get('status', ''), 20)

    if new_status not in ('present', 'break', 'signoff'):
        flash('Invalid status.', 'danger')
        return redirect(url_for('complaint_dashboard'))
    
    # Get or create today's attendance log
    today = date.today()
    attendance = AttendanceLog.query.filter_by(
        team_member_id=member.id,
        log_date=today
    ).first()

    if new_status == 'signoff':
        # Clock out and finalize break time
        if attendance and attendance.current_break_start:
            # If currently on break, calculate and add final break duration
            now_utc = datetime.now(timezone.utc)
            break_start_utc = ensure_utc(attendance.current_break_start)
            break_duration = (now_utc - break_start_utc).total_seconds()
            attendance.total_break_seconds += int(break_duration)
            attendance.current_break_start = None
        
        if attendance:
            attendance.clock_out_time = datetime.now(timezone.utc)
            attendance.last_updated = datetime.now(timezone.utc)
        
        # Return any active assignment to queue — another member will pick it up
        active = member.active_assignment
        if active:
            active.caller_id_ref.status = 'queued'
            db.session.delete(active)
        
        # Clear any manually reserved CallerIDs — return them to general queue
        reserved_callers = CallerID.query.filter_by(
            reserved_for_member_id=member.id, status='queued'
        ).all()
        for caller in reserved_callers:
            caller.reserved_for_member_id = None
            caller.reserved_at = None
            caller.reserved_by_id = None
        
        # Reset admin approval — must be re-approved on the next shift
        member.admin_approved = False
        member.self_status = 'signoff'
        db.session.commit()
        logger.info(f"Member signed off - User: {current_user.username}")
        flash('You have signed off for this shift. See you next time!', 'info')
        return redirect(url_for('complaint_dashboard'))

    if new_status == 'break':
        # Start break timer
        if attendance and not attendance.current_break_start:
            attendance.current_break_start = datetime.now(timezone.utc)
            attendance.last_updated = datetime.now(timezone.utc)
        
        member.self_status = 'break'
        db.session.commit()
        logger.info(f"Member on break - User: {current_user.username}")
        flash(
            'You are on break. Complete your current assignment if you have one. '
            'No new CallerIDs will be assigned while you are on break.',
            'warning',
        )
        return redirect(url_for('complaint_dashboard'))

    # new_status == 'present' (returning from break or starting a new shift)
    if not attendance:
        # First time marking present today - create attendance log
        attendance = AttendanceLog(
            team_member_id=member.id,
            log_date=today,
            clock_in_time=datetime.now(timezone.utc),
            last_updated=datetime.now(timezone.utc)
        )
        db.session.add(attendance)
        logger.info(f"Member clocked in - User: {current_user.username}")
    elif attendance.current_break_start:
        # Returning from break - calculate break duration
        now_utc = datetime.now(timezone.utc)
        break_start_utc = ensure_utc(attendance.current_break_start)
        break_duration = (now_utc - break_start_utc).total_seconds()
        attendance.total_break_seconds += int(break_duration)
        attendance.current_break_start = None
        attendance.last_updated = datetime.now(timezone.utc)
        logger.info(f"Member returned from break - User: {current_user.username} - Break duration: {int(break_duration)}s")
    
    member.self_status = 'present'
    db.session.flush()
    if member.admin_approved:
        assign_queued_caller_ids()  # commits
        logger.info(f"Member marked present (approved) - User: {current_user.username}")
        flash('You are Present and eligible for assignments.', 'success')
    else:
        db.session.commit()
        logger.info(f"Member marked present (awaiting approval) - User: {current_user.username}")
        flash(
            'You are marked Present. Waiting for admin approval before assignments begin.',
            'info',
        )
    return redirect(url_for('complaint_dashboard'))


@app.route('/complaint/analyse/<int:assignment_id>')
@login_required
@require_role('complaint')
def analyse_assignment(assignment_id):
    member = TeamMember.query.filter_by(user_id=current_user.id).first_or_404()
    assignment = Assignment.query.get_or_404(assignment_id)

    if assignment.team_member_id != member.id:
        logger.warning(f"Unauthorized assignment access - User: {current_user.username} - Assignment: {assignment_id}")
        flash('You are not authorized to access this assignment.', 'danger')
        return redirect(url_for('complaint_dashboard'))

    if assignment.status != 'active':
        flash('This assignment is no longer active.', 'warning')
        return redirect(url_for('complaint_dashboard'))

    return render_template('complaint_analyse.html', assignment=assignment, member=member)


@app.route('/complaint/submit/<int:assignment_id>', methods=['POST'])
@login_required
@require_role('complaint')
@rate_limit(limit=60, window_seconds=60)
def submit_outcome(assignment_id):
    member = TeamMember.query.filter_by(user_id=current_user.id).first_or_404()
    assignment = Assignment.query.get_or_404(assignment_id)

    if assignment.team_member_id != member.id:
        logger.warning(f"Unauthorized outcome submission - User: {current_user.username} - Assignment: {assignment_id}")
        flash('You are not authorized to submit this assignment.', 'danger')
        return redirect(url_for('complaint_dashboard'))

    if assignment.status != 'active':
        flash('This assignment is no longer active.', 'warning')
        return redirect(url_for('complaint_dashboard'))

    outcome = InputValidator.sanitize_string(request.form.get('outcome', ''), 20)
    
    if outcome not in ('dismiss', 'raised'):
        flash('Please select an outcome — Dismiss or Raised — before submitting.', 'danger')
        return redirect(url_for('analyse_assignment', assignment_id=assignment_id))

    core_id = None
    raised_comment = None
    
    if outcome == 'raised':
        core_id = InputValidator.sanitize_string(
            request.form.get('core_id', ''), 
            InputValidator.MAX_CORE_ID_LENGTH
        )
        
        # Validate CORE ID
        is_valid, error_msg = InputValidator.validate_core_id(core_id)
        if not is_valid:
            flash(error_msg, 'danger')
            return redirect(url_for('analyse_assignment', assignment_id=assignment_id))
        
        raised_comment = InputValidator.sanitize_string(
            request.form.get('raised_comment', ''), 
            InputValidator.MAX_COMMENT_LENGTH
        )

    try:
        caller_number = assignment.caller_id_ref.caller_id_number
        assignment.status = 'completed'
        assignment.completed_at = datetime.now(timezone.utc)
        assignment.outcome = outcome
        assignment.caller_id_ref.status = 'dismissed' if outcome == 'dismiss' else 'raised'
        
        if outcome == 'raised':
            assignment.caller_id_ref.core_id = core_id
            assignment.caller_id_ref.raised_comment = raised_comment or None
            logger.info(f"CallerID raised - User: {current_user.username} - CallerID: {caller_number} - CORE ID: {core_id}")
        
        if outcome == 'dismiss':
            qa_record = QAReview(
                caller_id_id=assignment.caller_id_id,
                dismissed_by_id=current_user.id,
                dismissed_at=datetime.now(timezone.utc),
            )
            db.session.add(qa_record)
            logger.info(f"CallerID dismissed - User: {current_user.username} - CallerID: {caller_number}")
        
        # Update attendance log with processed caller count
        attendance = member.today_attendance
        if attendance:
            attendance.callers_processed += 1
            if outcome == 'dismiss':
                attendance.callers_dismissed += 1
            else:  # outcome == 'raised'
                attendance.callers_raised += 1
            attendance.last_updated = datetime.now(timezone.utc)
        
        db.session.flush()

        # If still eligible, immediately auto-assign next queued CallerID
        if member.is_eligible:
            assign_queued_caller_ids()  # commits
        else:
            db.session.commit()

        outcome_label = 'sent to QA queue' if outcome == 'dismiss' else 'raised for admin review'
        flash(f'CallerID {caller_number} {outcome_label}. You are ready for the next assignment.', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error submitting outcome - User: {current_user.username} - Error: {str(e)}")
        flash('An error occurred while submitting. Please try again.', 'danger')
    
    return redirect(url_for('complaint_dashboard'))


# ---------------------------------------------------------------------------
# QA Review role routes
# ---------------------------------------------------------------------------

@app.route('/qa/dashboard')
@login_required
@require_role('qa')
def qa_dashboard():
    # Get submissions by this QA user
    submissions = (
        CallerID.query
        .filter_by(submitted_by_id=current_user.id)
        .order_by(CallerID.submitted_at.desc())
        .all()
    )

    # Calculate stats
    stats = {
        'total': len(submissions),
        'queued': CallerID.query.filter_by(status='queued').count(),
    }

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
    return render_template('qa_dashboard.html', pending=pending, completed=completed, stats=stats, submissions=submissions)


@app.route('/qa/submit/<int:qa_review_id>', methods=['POST'])
@login_required
@require_role('qa')
@rate_limit(limit=60, window_seconds=60)
def qa_submit(qa_review_id):
    review = QAReview.query.get_or_404(qa_review_id)
    
    if review.verdict is not None:
        flash('This case has already been reviewed.', 'warning')
        return redirect(url_for('qa_dashboard'))

    verdict = InputValidator.sanitize_string(request.form.get('verdict', ''), 20)
    justification = InputValidator.sanitize_string(
        request.form.get('justification', ''), 
        InputValidator.MAX_JUSTIFICATION_LENGTH
    )

    if verdict not in ('required', 'not_required'):
        flash('Please select a verdict — Required or Not Required.', 'danger')
        return redirect(url_for('qa_dashboard'))

    # Validate justification
    is_valid, error_msg = InputValidator.validate_text_field(
        justification, 
        'Justification', 
        InputValidator.MAX_JUSTIFICATION_LENGTH, 
        required=True
    )
    if not is_valid:
        flash(error_msg, 'danger')
        return redirect(url_for('qa_dashboard'))

    try:
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
            logger.info(f"QA verdict: Required - QA: {current_user.username} - CallerID: {caller_number}")
            flash(f'CallerID {caller_number} marked as Required — re-queued for complaint review.', 'success')
        else:
            caller.status = 'qa_not_required'
            db.session.commit()
            logger.info(f"QA verdict: Not Required - QA: {current_user.username} - CallerID: {caller_number}")
            flash(f'CallerID {caller_number} marked as Not Required — case closed.', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error submitting QA review - User: {current_user.username} - Error: {str(e)}")
        flash('An error occurred while submitting. Please try again.', 'danger')

    return redirect(url_for('qa_dashboard'))


if __name__ == '__main__':
    # Security check on startup
    with app.app_context():
        issues = validate_security_config(app)
        if issues:
            print("\n" + "="*60)
            print("SECURITY CONFIGURATION WARNINGS:")
            print("="*60)
            for issue in issues:
                print(f"  • {issue}")
            print("="*60 + "\n")
    
    # Determine if we should run in debug mode
    debug_mode = os.environ.get('FLASK_ENV', 'development') == 'development'
    
    if not debug_mode:
        logger.info("Starting application in PRODUCTION mode")
    else:
        logger.warning("Starting application in DEVELOPMENT mode (debug enabled)")
    
    app.run(debug=debug_mode, port=5000, host='127.0.0.1')
