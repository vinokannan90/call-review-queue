from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # user | admin | complaint

    team_member = db.relationship('TeamMember', backref='user', uselist=False)
    caller_ids = db.relationship('CallerID', foreign_keys='CallerID.submitted_by_id', backref='submitted_by', lazy='dynamic')


class TeamMember(db.Model):
    __tablename__ = 'team_members'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)

    # Self-reported by the complaint member: offline | present | break | signoff
    self_status = db.Column(db.String(20), nullable=False, default='offline')
    # Admin approval — only effective when self_status == 'present'
    admin_approved = db.Column(db.Boolean, default=False, nullable=False)

    assignments = db.relationship('Assignment', backref='team_member', lazy='dynamic')

    @property
    def is_eligible(self):
        """True when member is self-present AND admin-approved — receives new assignments."""
        return self.self_status == 'present' and self.admin_approved

    @property
    def active_assignment(self):
        """Returns the single active assignment for this member, or None."""
        return Assignment.query.filter_by(
            team_member_id=self.id, status='active'
        ).first()
    
    @property
    def reserved_count(self):
        """Count of CallerIDs manually reserved for this member."""
        return CallerID.query.filter_by(
            reserved_for_member_id=self.id, status='queued'
        ).count()
    
    @property
    def can_receive_manual_assignment(self):
        """True if member can receive manual assignments (present/break and < 3 reserved)."""
        return self.self_status in ('present', 'break') and self.reserved_count < 3
    
    @property
    def today_attendance(self):
        """Get today's attendance log for this member, or None if not clocked in."""
        from datetime import date
        return AttendanceLog.query.filter_by(
            team_member_id=self.id,
            log_date=date.today()
        ).first()
    
    @property
    def is_clocked_in(self):
        """True if member has clocked in today and not yet clocked out."""
        log = self.today_attendance
        return log is not None and log.clock_out_time is None


class CallerID(db.Model):
    __tablename__ = 'caller_ids'

    id = db.Column(db.Integer, primary_key=True)
    caller_id_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    aws_recording_url = db.Column(db.String(500), nullable=True)
    submitted_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    submitted_at = db.Column(db.DateTime, nullable=False)
    # queued → assigned → dismissed (QA queue) | raised (admin review) | reviewed
    status = db.Column(db.String(20), nullable=False, default='queued', index=True)
    reason = db.Column(db.String(500), nullable=True)
    core_id = db.Column(db.String(100), nullable=True)
    raised_comment = db.Column(db.Text, nullable=True)
    
    # Manual assignment fields (admin can reserve up to 3 CallerIDs per team member)
    reserved_for_member_id = db.Column(db.Integer, db.ForeignKey('team_members.id'), nullable=True, index=True)
    reserved_at = db.Column(db.DateTime, nullable=True)
    reserved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    assignments = db.relationship('Assignment', backref='caller_id_ref', lazy='dynamic')
    reserved_for = db.relationship('TeamMember', foreign_keys=[reserved_for_member_id], backref='reserved_caller_ids')
    reserved_by = db.relationship('User', foreign_keys=[reserved_by_id], backref='reserved_callers')


class Assignment(db.Model):
    __tablename__ = 'assignments'

    id = db.Column(db.Integer, primary_key=True)
    caller_id_id = db.Column(db.Integer, db.ForeignKey('caller_ids.id'), nullable=False)
    team_member_id = db.Column(db.Integer, db.ForeignKey('team_members.id'), nullable=False)
    assigned_at = db.Column(db.DateTime, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='active')  # active | completed
    # Outcome chosen by complaint member: None | dismiss | raised
    outcome = db.Column(db.String(20), nullable=True)


class QAReview(db.Model):
    __tablename__ = 'qa_reviews'

    id = db.Column(db.Integer, primary_key=True)
    # A CallerID may be dismissed, required back, dismissed again — multiple reviews possible
    caller_id_id = db.Column(db.Integer, db.ForeignKey('caller_ids.id'), nullable=False)
    dismissed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    dismissed_at = db.Column(db.DateTime, nullable=False)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    # Verdict chosen by QA: required | not_required
    verdict = db.Column(db.String(20), nullable=True)
    justification = db.Column(db.Text, nullable=True)

    caller_id_ref = db.relationship('CallerID', backref=db.backref('qa_reviews', lazy='dynamic'))
    dismissed_by = db.relationship('User', foreign_keys=[dismissed_by_id])
    reviewed_by = db.relationship('User', foreign_keys=[reviewed_by_id])


class AttendanceLog(db.Model):
    """Daily attendance tracking for complaint team members."""
    __tablename__ = 'attendance_logs'

    id = db.Column(db.Integer, primary_key=True)
    team_member_id = db.Column(db.Integer, db.ForeignKey('team_members.id'), nullable=False, index=True)
    log_date = db.Column(db.Date, nullable=False, index=True)  # Date of attendance (for reporting)
    
    # Time tracking
    clock_in_time = db.Column(db.DateTime, nullable=False)  # When marked "Present"
    clock_out_time = db.Column(db.DateTime, nullable=True)  # When marked "Sign Off" or end of day
    
    # Break tracking
    total_break_seconds = db.Column(db.Integer, default=0, nullable=False)  # Accumulated break time
    current_break_start = db.Column(db.DateTime, nullable=True)  # When current break started (null = not on break)
    
    # Performance tracking
    callers_processed = db.Column(db.Integer, default=0, nullable=False)  # CallerIDs completed today
    callers_dismissed = db.Column(db.Integer, default=0, nullable=False)  # Dismissed count
    callers_raised = db.Column(db.Integer, default=0, nullable=False)  # Raised count
    
    # Metadata
    last_updated = db.Column(db.DateTime, nullable=False)
    
    # Relationships
    team_member = db.relationship('TeamMember', backref=db.backref('attendance_logs', lazy='dynamic'))
    
    # Unique constraint: one log per team member per day
    __table_args__ = (
        db.UniqueConstraint('team_member_id', 'log_date', name='uix_member_date'),
    )
