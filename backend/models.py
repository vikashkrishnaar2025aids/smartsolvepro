# models.py
import json
from datetime import datetime
from database import db  # type: ignore


class Project(db.Model):
    __tablename__ = "projects"

    id          = db.Column(db.String(20),  primary_key=True)
    user_id     = db.Column(db.String(100), nullable=True)
    user_email  = db.Column(db.String(200), nullable=True)
    user_name   = db.Column(db.String(200), nullable=True)
    title       = db.Column(db.String(200), nullable=False)
    problem     = db.Column(db.Text,        nullable=False)
    deadline    = db.Column(db.String(100), nullable=True)
    summary     = db.Column(db.Text,        nullable=True)
    total_days  = db.Column(db.Integer,     default=0)
    status      = db.Column(db.String(20),  default="active")
    progress    = db.Column(db.Float,       default=0.0)
    created_at  = db.Column(db.DateTime,    default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime,    default=datetime.utcnow,
                            onupdate=datetime.utcnow)

    tasks     = db.relationship("Task",       backref="project",
                                cascade="all, delete-orphan")
    members   = db.relationship("TeamMember", backref="project",
                                cascade="all, delete-orphan")
    work_logs = db.relationship("WorkLog",    backref="project",
                                cascade="all, delete-orphan")

    def calculate_progress(self):
        if not self.tasks:
            return 0.0
        done = sum(1 for t in self.tasks if t.status == "done")
        return round((done / len(self.tasks)) * 100, 1) # type: ignore

    def to_dict(self):
        return {
            # ── identity ──────────────────────────────
            "project_id":   self.id,          # ← FIX: frontend needs this
            "id":           self.id,
            "user_id":      self.user_id,
            "user_email":   self.user_email or "Guest",
            "user_name":    self.user_name  or "Anonymous",
            # ── plan data ─────────────────────────────
            "projectTitle": self.title,       # ← FIX: was missing
            "problem":      self.problem,
            "deadline":     self.deadline,
            "summary":      self.summary,
            "totalDays":    self.total_days,
            "status":       self.status,
            "progress":     self.calculate_progress(),
            "created_at":   self.created_at.strftime("%Y-%m-%d %H:%M"),
            "updated_at":   self.updated_at.strftime("%Y-%m-%d %H:%M"),
            "tasks":        [t.to_dict() for t in self.tasks],
            "members":      [m.to_dict() for m in self.members],
        }


class Task(db.Model):
    __tablename__ = "tasks"

    id                = db.Column(db.Integer,    primary_key=True,
                                  autoincrement=True)
    project_id        = db.Column(db.String(20), db.ForeignKey("projects.id"),
                                  nullable=False)
    task_number       = db.Column(db.Integer,    default=1)
    name              = db.Column(db.String(200), nullable=False)
    description       = db.Column(db.Text,       nullable=True)
    type              = db.Column(db.String(50),  default="development")
    priority          = db.Column(db.String(20),  default="medium")
    assignee          = db.Column(db.String(100), nullable=True)
    duration          = db.Column(db.Integer,     default=1)
    start_day         = db.Column(db.Integer,     default=1)
    status            = db.Column(db.String(20),  default="todo")
    progress          = db.Column(db.Float,       default=0.0)
    dependencies_json = db.Column(db.Text,        default="[]")
    subtasks_json     = db.Column(db.Text,        default="[]")
    created_at        = db.Column(db.DateTime,    default=datetime.utcnow)
    updated_at        = db.Column(db.DateTime,    default=datetime.utcnow,
                                  onupdate=datetime.utcnow)

    work_logs = db.relationship("WorkLog", backref="task",
                                cascade="all, delete-orphan")
    comments  = db.relationship("Comment", backref="task",
                                cascade="all, delete-orphan")

    # ── Completion Proof ───────────────────────────
    completion_note     = db.Column(db.Text,        nullable=True)
    completion_file     = db.Column(db.String(300), nullable=True)
    completion_url      = db.Column(db.String(300), nullable=True)
    submitted_by        = db.Column(db.String(100), nullable=True)
    submitted_at        = db.Column(db.DateTime,    nullable=True)
    reviewed_by         = db.Column(db.String(100), nullable=True)
    reviewed_at         = db.Column(db.DateTime,    nullable=True)
    rejection_reason    = db.Column(db.Text,        nullable=True)
    approval_status     = db.Column(db.String(20),  default="none")
    ai_review_json      = db.Column(db.Text,        nullable=True)  # New: Stores AI's error analysis & corrections
    # none → pending → approved → rejected

    def to_dict(self):
        return {
            "id":               self.task_number,
            "db_id":            self.id,
            "name":             self.name,
            "description":      self.description,
            "type":             self.type,
            "priority":         self.priority,
            "assignee":         self.assignee,
            "durationDays":     self.duration,
            "startDay":         self.start_day,
            "status":           self.status,
            "progress":         self.progress,
            "dependencies":     json.loads(self.dependencies_json or "[]"),
            "subtasks":         json.loads(self.subtasks_json     or "[]"),
            # ── Proof Data ──
            "completion_note":  self.completion_note,
            "completion_file":  self.completion_file,
            "completion_url":   self.completion_url,
            "submitted_by":     self.submitted_by,
            "submitted_at":     self.submitted_at.strftime("%Y-%m-%d %H:%M") if self.submitted_at else None,
            "reviewed_by":      self.reviewed_by,
            "reviewed_at":      self.reviewed_at.strftime("%Y-%m-%d %H:%M") if self.reviewed_at else None,
            "rejection_reason": self.rejection_reason,
            "approval_status":  self.approval_status or "none",
            "ai_review":        json.loads(self.ai_review_json or "{}") if self.ai_review_json else None,
        }


class TeamMember(db.Model):
    __tablename__ = "team_members"

    id         = db.Column(db.Integer,    primary_key=True,
                           autoincrement=True)
    project_id = db.Column(db.String(20), db.ForeignKey("projects.id"),
                           nullable=True)   # ← FIX: nullable=True for global members
    name       = db.Column(db.String(100), nullable=False)
    skills     = db.Column(db.String(300), nullable=True)

    def to_dict(self):
        return {
            "id":     self.id,
            "name":   self.name,
            "skills": self.skills,
        }


class WorkLog(db.Model):
    __tablename__ = "work_logs"

    id           = db.Column(db.Integer,    primary_key=True,
                             autoincrement=True)
    project_id   = db.Column(db.String(20), db.ForeignKey("projects.id"),
                             nullable=False)
    task_id      = db.Column(db.Integer,    db.ForeignKey("tasks.id"),
                             nullable=False)
    member_name  = db.Column(db.String(100), nullable=False)
    date         = db.Column(db.Date,       nullable=False)
    hours_worked = db.Column(db.Float,      default=0.0)
    work_done    = db.Column(db.Text,       nullable=False)
    progress_pct = db.Column(db.Float,      default=0.0)
    blockers     = db.Column(db.Text,       nullable=True)
    ai_analysis_json = db.Column(db.Text,       nullable=True)  # Store AI analysis for this work log
    created_at   = db.Column(db.DateTime,   default=datetime.utcnow)

    def to_dict(self):
        return {
            "id":           self.id,
            "task_id":      self.task_id,
            "member_name":  self.member_name,
            "date":         self.date.isoformat(),
            "hours_worked": self.hours_worked,
            "work_done":    self.work_done,
            "progress_pct": self.progress_pct,
            "blockers":     self.blockers,
            "ai_analysis":  json.loads(self.ai_analysis_json or "{}") if self.ai_analysis_json else None,
            "created_at":   self.created_at.strftime("%Y-%m-%d %H:%M"),
        }


class Comment(db.Model):
    __tablename__ = "comments"

    id          = db.Column(db.Integer,    primary_key=True,
                            autoincrement=True)
    task_id     = db.Column(db.Integer,    db.ForeignKey("tasks.id"),
                            nullable=False)
    member_name = db.Column(db.String(100), nullable=False)
    message     = db.Column(db.Text,       nullable=False)
    created_at  = db.Column(db.DateTime,   default=datetime.utcnow)

    def to_dict(self):
        return {
            "id":          self.id,
            "member_name": self.member_name,
            "message":     self.message,
            "created_at":  self.created_at.strftime("%Y-%m-%d %H:%M"),
        }


# ── Risk Log ───────────────────────────────────────────────────────
class RiskLog(db.Model):
    """
    AI scans project daily and stores risk analysis.
    One entry per project per day.
    """
    __tablename__ = "risk_logs"

    id            = db.Column(db.Integer,    primary_key=True,
                              autoincrement=True)
    project_id    = db.Column(db.String(20), db.ForeignKey("projects.id"),
                              nullable=False)
    risk_score    = db.Column(db.Integer,    default=0)   # 0-100
    risk_level    = db.Column(db.String(20), default="low")
    # low / medium / high / critical
    summary       = db.Column(db.Text,       nullable=True)
    warnings      = db.Column(db.Text,       default="[]")  # JSON list
    recommendations = db.Column(db.Text,     default="[]")  # JSON list
    deadline_safe = db.Column(db.Boolean,    default=True)
    scanned_at    = db.Column(db.DateTime,   default=datetime.utcnow)

    def to_dict(self):
        return {
            "id":               self.id,
            "project_id":       self.project_id,
            "risk_score":       self.risk_score,
            "risk_level":       self.risk_level,
            "summary":          self.summary,
            "warnings":         json.loads(self.warnings or "[]"),
            "recommendations":  json.loads(self.recommendations or "[]"),
            "deadline_safe":    self.deadline_safe,
            "scanned_at":       self.scanned_at.strftime("%Y-%m-%d %H:%M"),
        }


# ── Member Score ───────────────────────────────────────────────────
class MemberScore(db.Model):
    """
    Live performance score for each team member per project.
    Updated every time work is logged or a task is completed.
    """
    __tablename__ = "member_scores"

    id              = db.Column(db.Integer,    primary_key=True,
                                autoincrement=True)
    project_id      = db.Column(db.String(20), db.ForeignKey("projects.id"),
                                nullable=False)
    member_name     = db.Column(db.String(100), nullable=False)
    total_score     = db.Column(db.Integer,    default=0)    # 0-100
    tasks_completed = db.Column(db.Integer,    default=0)
    tasks_rejected  = db.Column(db.Integer,    default=0)
    total_hours     = db.Column(db.Float,      default=0.0)
    streak_days     = db.Column(db.Integer,    default=0)
    last_active     = db.Column(db.Date,       nullable=True)
    consistency_pct = db.Column(db.Float,      default=0.0)
    quality_pct     = db.Column(db.Float,      default=0.0)
    badge           = db.Column(db.String(50), default="newcomer")
    # newcomer / contributor / achiever / champion / legend
    updated_at      = db.Column(db.DateTime,   default=datetime.utcnow)

    def to_dict(self):
        return {
            "id":               self.id,
            "project_id":       self.project_id,
            "member_name":      self.member_name,
            "total_score":      self.total_score,
            "tasks_completed":  self.tasks_completed,
            "tasks_rejected":   self.tasks_rejected,
            "total_hours":      round(self.total_hours, 1),
            "streak_days":      self.streak_days,
            "last_active":      self.last_active.isoformat()
                                if self.last_active else None,
            "consistency_pct":  round(self.consistency_pct, 1),
            "quality_pct":      round(self.quality_pct, 1),
            "badge":            self.badge,
            "updated_at":       self.updated_at.strftime("%Y-%m-%d %H:%M"),
        }


# ── Standup Report ─────────────────────────────────────────────────
class StandupReport(db.Model):
    """
    AI-generated daily standup report for a project.
    One report per project per day.
    """
    __tablename__ = "standup_reports"

    id              = db.Column(db.Integer,    primary_key=True,
                                autoincrement=True)
    project_id      = db.Column(db.String(20), db.ForeignKey("projects.id"),
                                nullable=False)
    report_date     = db.Column(db.Date,       nullable=False)
    completed_tasks = db.Column(db.Text,       default="[]")  # JSON
    in_progress     = db.Column(db.Text,       default="[]")  # JSON
    blockers        = db.Column(db.Text,       default="[]")  # JSON
    achievements    = db.Column(db.Text,       default="[]")  # JSON
    health_status   = db.Column(db.String(20), default="on_track")
    health_score    = db.Column(db.Integer,    default=100)
    days_remaining  = db.Column(db.Integer,    nullable=True)
    summary         = db.Column(db.Text,       nullable=True)
    ai_advice       = db.Column(db.Text,       nullable=True)
    generated_at    = db.Column(db.DateTime,   default=datetime.utcnow)

    def to_dict(self):
        return {
            "id":               self.id,
            "project_id":       self.project_id,
            "report_date":      self.report_date.isoformat(),
            "completed_tasks":  json.loads(self.completed_tasks or "[]"),
            "in_progress":      json.loads(self.in_progress     or "[]"),
            "blockers":         json.loads(self.blockers         or "[]"),
            "achievements":     json.loads(self.achievements     or "[]"),
            "health_status":    self.health_status,
            "health_score":     self.health_score,
            "days_remaining":   self.days_remaining,
            "summary":          self.summary,
            "ai_advice":        self.ai_advice,
            "generated_at":     self.generated_at.strftime("%Y-%m-%d %H:%M"),
        }
