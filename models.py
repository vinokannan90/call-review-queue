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
    caller_ids = db.relationship('CallerID', backref='submitted_by', lazy='dynamic')


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

    assignments = db.relationship('Assignment', backref='caller_id_ref', lazy='dynamic')


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
