# app.py
from flask import Flask, render_template, request, jsonify, send_from_directory, session, redirect, url_for  # type: ignore
from flask_cors import CORS  # type: ignore
from flask_migrate import Migrate  # type: ignore
import os
import json
import uuid
from datetime import datetime, date
from dotenv import load_dotenv, set_key  # type: ignore
import urllib.request
from werkzeug.utils import secure_filename # type: ignore
from functools import wraps

from database import init_db, db  # type: ignore
from models import (Project, Task, TeamMember,
                    WorkLog, Comment,
                    RiskLog, MemberScore, StandupReport, User,
                    AdminUser, AICallLog)  # type: ignore
from ai_engine import AIEngine  # type: ignore

# ── Load env ───────────────────────────────────────────────────────
env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(env_path)

app = Flask(__name__)
CORS(app)

app.config["SQLALCHEMY_DATABASE_URI"]        = "sqlite:///smart_solve.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = os.environ.get("SECRET_KEY", "smartsolve-secret-2024")

init_db(app)
migrate = Migrate(app, db)
engine = AIEngine()

# UPLOAD CONFIG
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {"png","jpg","jpeg","gif","pdf","zip","txt","docx","mp4"}

def allowed_file(filename):
    return "." in filename and \
           filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ══════════════════════════════════════════════════════════════════
#  AUTHENTICATION DECORATORS
# ══════════════════════════════════════════════════════════════════

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_api_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            return jsonify({"error": "Admin authentication required"}), 403
        return f(*args, **kwargs)
    return decorated_function

def _check_admin(req):
    return 'admin_id' in session

@app.before_request
def require_global_login():
    # Allow access to the login page and static files (CSS/JS)
    if request.endpoint in ('admin_login', 'static'):
        return
        
    if 'admin_id' not in session:
        # If it's an API request, return JSON error instead of redirect
        if request.path.startswith('/api/'):
            return jsonify({"error": "Admin authentication required"}), 403
        # Otherwise redirect to login page
        return redirect(url_for('admin_login'))


# ══════════════════════════════════════════════════════════════════
#  AUTH MIDDLEWARE
# ══════════════════════════════════════════════════════════════════

@app.before_request
def require_login():
    # List of endpoints that don't require authentication
    allowed_endpoints = ['login', 'signup', 'static', 'google_auth', 'health']
    
    # Allow access if endpoint is in allowed list or if user is logged in
    if request.endpoint not in allowed_endpoints and 'user_id' not in session:
        # Check if it's an API request
        if request.path.startswith('/api/'):
            return jsonify({"error": "Unauthorized"}), 401
        return redirect(url_for('login'))

# ══════════════════════════════════════════════════════════════════
#  AUTH ROUTES
# ══════════════════════════════════════════════════════════════════

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = request.form
        email = data.get("email")
        password = data.get("password")
        
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['user_name'] = user.name
            session['user_email'] = user.email
            return redirect(url_for('dashboard'))
        
        return render_template("login.html", error="Invalid email or password")
        
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        name = request.form.get("name")
        
        if User.query.filter_by(email=email).first():
            return render_template("login.html", signup=True, error="Email already exists")
            
        new_user = User(email=email, name=name)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        session['user_id'] = new_user.id
        session['user_name'] = new_user.name
        session['user_email'] = new_user.email
        return redirect(url_for('dashboard'))
        
    return render_template("login.html", signup=True)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

# ══════════════════════════════════════════════════════════════════
#  PAGE ROUTES
# ══════════════════════════════════════════════════════════════════

@app.route("/")
def dashboard():
    return render_template("dashboard.html", active_page="dashboard",
        google_client_id=os.environ.get("GOOGLE_CLIENT_ID"))

@app.route("/planner")
def planner():
    return render_template("planner.html", active_page="planner",
        google_client_id=os.environ.get("GOOGLE_CLIENT_ID"))

@app.route("/team")
def team_mgmt():
    return render_template("team.html", active_page="team",
        google_client_id=os.environ.get("GOOGLE_CLIENT_ID"))

@app.route("/knowledge")
def knowledge():
    return render_template("base.html", active_page="knowledge",
        google_client_id=os.environ.get("GOOGLE_CLIENT_ID"))

@app.route("/settings")
def settings():
    return render_template("settings.html", active_page="settings",
        google_client_id=os.environ.get("GOOGLE_CLIENT_ID"))

@app.route("/admin-portal-99")
def admin_settings():
    return render_template("admin_settings.html", active_page="admin",
        ai_mode=engine.mode,
        has_groq=bool(engine.groq_key),
        has_gemini=bool(engine.gemini_key),
        has_openrouter=bool(engine.openrouter_key),
        google_client_id=os.environ.get("GOOGLE_CLIENT_ID"))

@app.route("/tracker/<project_id>")
def tracker(project_id):
    project = Project.query.get(project_id)
    if not project:
        return "<h2 style='color:red;font-family:monospace'>Project not found</h2>", 404
    return render_template("tracker.html", project=project, 
                           members=[m.to_dict() for m in project.members])

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        
        user = AdminUser.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session['admin_id'] = user.id
            user.last_login = datetime.utcnow()
            db.session.commit()
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template("admin_login.html", error="Invalid credentials")
            
    if 'admin_id' in session:
        return redirect(url_for('admin_dashboard'))
    return render_template("admin_login.html")

@app.route("/admin/logout")
def admin_logout():
    session.pop('admin_id', None)
    return redirect(url_for('admin_login'))

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    """
    Admin dashboard — shows ALL projects from ALL users.
    """
    return render_template("admin_dashboard.html", active_page="admin")


# ══════════════════════════════════════════════════════════════════
#  CORE API ROUTES
# ══════════════════════════════════════════════════════════════════

# ── Generate Plan ──────────────────────────────────────────────────
@app.route("/api/generate", methods=["POST"])
def generate_plan():
    try:
        data       = request.get_json()
        problem    = data.get("problem",   "").strip()
        team       = data.get("team",      [])
        deadline   = data.get("deadline",  "").strip()
        user_id    = data.get("user_id",   None)
        user_email = data.get("user_email","").strip()
        user_name  = data.get("user_name", "").strip()

        if not problem:
            return jsonify({"error": "Problem statement is required"}), 400

        # Generate plan via AI
        plan = engine.generate_plan(problem, team, deadline)

        # Build unique project ID
        project_id = str(uuid.uuid4()).replace("-", "")[:8].upper() # type: ignore

        new_project = Project(
            id          = project_id,
            user_id     = user_id    or None,
            user_email  = user_email or None,
            user_name   = user_name  or None,
            title       = plan.get("projectTitle", "Untitled Project"),
            problem     = problem,
            deadline    = deadline   or None,
            summary     = plan.get("summary", ""),
            total_days  = plan.get("totalDays", 0),
            status      = "active",
            progress    = 0.0,
            updated_at  = datetime.utcnow(),
        )
        db.session.add(new_project)

        # Save team members
        for member in team:
            if member.get("name"):
                db.session.add(TeamMember(
                    project_id = project_id,
                    name       = member["name"],
                    skills     = member.get("skills", ""),
                ))

        # Save tasks
        for task in plan.get("tasks", []):
            db.session.add(Task(
                project_id        = project_id,
                task_number       = task.get("id", 1),
                name              = task.get("name", ""),
                description       = task.get("description", ""),
                type              = task.get("type", "development"),
                priority          = task.get("priority", "medium"),
                assignee          = task.get("assignee", "Team"),
                duration          = task.get("durationDays", 1),
                start_day         = task.get("startDay", 1),
                dependencies_json = json.dumps(task.get("dependencies", [])),
                subtasks_json     = json.dumps(task.get("subtasks", [])),
                status            = "todo",
                progress          = 0.0,
            ))

        db.session.commit()
        print(f"[DB] Project {project_id} saved for user={user_email or 'guest'} [OK]")

        # Return project_id at top level AND inside plan
        plan["project_id"] = project_id
        return jsonify({"success": True, "plan": plan})

    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] /api/generate: {e}")
        return jsonify({"error": str(e)}), 500


# ── Analyze Problem ────────────────────────────────────────────────
@app.route("/api/analyze-problem", methods=["POST"])
def analyze_problem():
    try:
        data    = request.get_json()
        problem = data.get("problem", "").strip()
        if not problem:
            return jsonify({"error": "Problem statement is required"}), 400

        projects     = Project.query.all()
        history_dict = {
            p.id: {
                "title":      p.title,
                "problem":    p.problem,
                "created_at": p.created_at.strftime("%Y-%m-%d %H:%M"),
            }
            for p in projects
        }
        analysis = engine.analyze_problem(problem, history_dict)
        return jsonify({"success": True, "analysis": analysis})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Get History ────────────────────────────────────────────────────
@app.route("/api/history", methods=["GET"])
def get_history():
    """
    Returns projects for the current user.
    If no user_id provided → returns all projects (guest mode).
    """
    try:
        user_id  = request.args.get("user_id")
        if user_id:
            projects = Project.query.filter_by(user_id=user_id)\
                               .order_by(Project.created_at.desc()).all()
        else:
            # Guest — show all projects (no login)
            projects = Project.query.order_by(
                Project.created_at.desc()).limit(20).all()

        history = []
        for p in projects[:10]:
            history.append({
                "id":         p.id,
                "title":      p.title,
                "problem":    p.problem[:80] + ("..." if len(p.problem) > 80 else ""),
                "created_at": p.created_at.strftime("%Y-%m-%d %H:%M"),
                "task_count": len(p.tasks),
                "team_size":  len(p.members),
                "total_days": p.total_days,
                "progress":   p.calculate_progress(),
            })

        return jsonify({
            "history":        history,
            "total_projects": len(projects),
            "total_tasks":    Task.query.count(),
            "total_members":  TeamMember.query.filter(
                                  TeamMember.project_id.isnot(None)
                              ).count(),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Get Single Project ─────────────────────────────────────────────
@app.route("/api/history/<project_id>", methods=["GET"])
def get_project(project_id):
    try:
        project = Project.query.get(project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404
        return jsonify({"plan": project.to_dict()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Delete Project ─────────────────────────────────────────────────
@app.route("/api/history/<project_id>", methods=["DELETE"])
def delete_project(project_id):
    try:
        project = Project.query.get(project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404
        db.session.delete(project)
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ── Update Task ────────────────────────────────────────────────────
@app.route("/api/update-task", methods=["POST"])
def update_task():
    try:
        data       = request.get_json()
        project_id = data.get("project_id")
        task_num   = data.get("task_id")
        updates    = data.get("updates", {})

        task = Task.query.filter_by(
            project_id=project_id, task_number=task_num
        ).first()
        if not task:
            return jsonify({"error": "Task not found"}), 404

        for field, col in [
            ("name",        "name"),
            ("description", "description"),
            ("priority",    "priority"),
            ("assignee",    "assignee"),
            ("type",        "type"),
            ("durationDays","duration"),
            ("startDay",    "start_day"),
        ]:
            if field in updates:
                setattr(task, col, updates[field])

        db.session.commit()
        return jsonify({"success": True, "task": task.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ── Stats ──────────────────────────────────────────────────────────
@app.route("/api/stats", methods=["GET"])
def get_stats():
    try:
        latest = Project.query.order_by(Project.created_at.desc()).first()
        return jsonify({
            "total_projects": Project.query.count(),
            "total_tasks":    Task.query.count(),
            "latest_project": latest.title if latest else None,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Health Check ───────────────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status":   "ok",
        "version":  "2.0",
        "ai_mode":  engine.mode,
        "database": "SQLite [OK]",
    })


# ── Google Auth ────────────────────────────────────────────────────
@app.route("/api/auth/google", methods=["POST"])
def google_auth():
    try:
        data  = request.get_json()
        token = data.get("token")
        url   = f"https://oauth2.googleapis.com/tokeninfo?id_token={token}"
        with urllib.request.urlopen(url) as resp:
            id_info = json.loads(resp.read().decode())
        # Set session
        session['user_id'] = id_info.get("sub")
        session['user_name'] = id_info.get("name")
        session['user_email'] = id_info.get("email")
        
        return jsonify({"success": True, "user": {
            "name":    id_info.get("name"),
            "email":   id_info.get("email"),
            "picture": id_info.get("picture"),
            "id":      id_info.get("sub"),
        }})
    except Exception as e:
        print(f"[ERROR] Google Auth: {e}")
        return jsonify({"error": "Authentication failed"}), 401


# ── Settings ───────────────────────────────────────────────────────
@app.route("/api/settings", methods=["POST"])
def update_settings():
    try:
        data    = request.get_json()
        new_mode = data.get("ai_mode")
        if new_mode in ["groq-ai", "gemini-ai", "openrouter-ai", "rule-based"]:
            engine.mode = new_mode
            return jsonify({"success": True, "ai_mode": engine.mode})

        groq_key       = data.get("groq_key")
        gemini_key     = data.get("gemini_key")
        openrouter_key = data.get("openrouter_key")
        if groq_key or gemini_key or openrouter_key:
            if not os.path.exists(env_path):
                open(env_path, "w").close()
            if groq_key:       set_key(env_path, "GROQ_API_KEY",       groq_key)
            if gemini_key:     set_key(env_path, "GEMINI_API_KEY",     gemini_key)
            if openrouter_key: set_key(env_path, "OPENROUTER_API_KEY", openrouter_key)
            engine.set_keys(groq_key=groq_key, gemini_key=gemini_key,
                            openrouter_key=openrouter_key)
            return jsonify({"success": True, "message": "Keys saved"})
        return jsonify({"error": "Invalid settings"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Team (global members with project_id=None) ─────────────────────
@app.route("/api/team", methods=["GET"])
def get_team():
    members = TeamMember.query.filter_by(project_id=None).all()
    return jsonify({"team": [m.to_dict() for m in members]})

@app.route("/api/team", methods=["POST"])
def add_team_member():
    data = request.get_json()
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400
    member = TeamMember(name=name, skills=data.get("skills",""), project_id=None)
    db.session.add(member)
    db.session.commit()
    return jsonify({"success": True, "member": member.to_dict()})

@app.route("/api/team/<int:mid>", methods=["PUT"])
def update_team_member(mid):
    data   = request.get_json()
    member = TeamMember.query.get(mid)
    if not member:
        return jsonify({"error": "Not found"}), 404
    member.name   = data.get("name",   member.name)
    member.skills = data.get("skills", member.skills)
    db.session.commit()
    return jsonify({"success": True, "member": member.to_dict()})

@app.route("/api/team/<int:mid>", methods=["DELETE"])
def delete_team_member(mid):
    member = TeamMember.query.get(mid)
    if member:
        db.session.delete(member)
        db.session.commit()
    return jsonify({"success": True})


# ══════════════════════════════════════════════════════════════════
#  DAILY TRACKING ROUTES
# ══════════════════════════════════════════════════════════════════

# ── Submit Completion Proof ────────────────────────────────────────
@app.route("/api/submit_completion", methods=["POST"])
def submit_completion():
    """
    Team member submits proof that a task is done.
    Admin must then APPROVE before status changes to 'done'.
    """
    try:
        task_db_id      = int(request.form.get("task_db_id"))
        member_name     = request.form.get("member_name", "").strip()
        completion_note = request.form.get("completion_note", "").strip()
        completion_url  = request.form.get("completion_url",  "").strip()

        if not completion_note:
            return jsonify({"error": "Please describe what was completed"}), 400

        task = Task.query.get(task_db_id)
        if not task:
            return jsonify({"error": "Task not found"}), 404

        # Handle file upload
        file_path = None
        if "proof_file" in request.files:
            file = request.files["proof_file"]
            if file and file.filename and allowed_file(file.filename):
                filename  = secure_filename(
                    f"{task_db_id}_{int(datetime.utcnow().timestamp())}_{file.filename}"
                )
                file_path = filename
                file.save(os.path.join(UPLOAD_FOLDER, filename))

        # Mark as PENDING APPROVAL — not done yet
        task.approval_status  = "pending"
        task.completion_note  = completion_note
        task.completion_file  = file_path
        task.completion_url   = completion_url or None
        task.submitted_by     = member_name
        task.submitted_at     = datetime.utcnow()
        task.status           = "pending_review"   # new status
        task.rejection_reason = None

        # ── AI Review on submission ──
        print(f"[AI Review] Triggering analysis for task completion: {task.name}")
        ai_res = engine.review_completion(
            task_name        = task.name,
            task_description = task.description or "",
            task_type        = task.type,
            completion_note  = completion_note,
            completion_url   = completion_url or "",
            proof_filename   = file_path or ""
        )
        task.ai_review_json = json.dumps(ai_res)
        # If AI is very confident it is approved, maybe we can auto-approve?
        # For now, let's just store it and keep status as 'pending_review' 
        # so Admin can see it. But let's show the errors/corrections.

        db.session.commit()
        print(f"[Tracker] Task {task_db_id} submitted for review by {member_name} [OK]")

        return jsonify({
            "success":         True,
            "message":         "Submitted for admin review [OK]",
            "approval_status": task.approval_status,
            "task_status":     task.status,
        })

    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] submit_completion: {e}")
        return jsonify({"error": str(e)}), 500


# ── Admin: Approve Task ────────────────────────────────────────────
@app.route("/api/admin/approve_task", methods=["POST"])
def approve_task():
    """Admin approves a completion submission → task becomes DONE"""
    if not _check_admin(request):
        return jsonify({"error": "Unauthorized"}), 403
    try:
        data       = request.get_json()
        task_db_id = int(data.get("task_db_id"))
        reviewer   = data.get("reviewer", "Admin")

        task = Task.query.get(task_db_id)
        if not task:
            return jsonify({"error": "Task not found"}), 404

        task.approval_status = "approved"
        task.status          = "done"
        task.progress        = 100.0
        task.reviewed_by     = reviewer
        task.reviewed_at     = datetime.utcnow()

        # Update project progress
        project = Project.query.get(task.project_id)
        if project:
            project.progress   = project.calculate_progress()
            project.updated_at = datetime.utcnow()

        db.session.commit()
        return jsonify({
            "success":          True,
            "message":          f"Task approved [OK]",
            "project_progress": project.calculate_progress(),
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ── Admin: Reject Task ────────────────────────────────────────────
@app.route("/api/admin/reject_task", methods=["POST"])
def reject_task():
    """Admin rejects a completion — task goes back to in_progress"""
    if not _check_admin(request):
        return jsonify({"error": "Unauthorized"}), 403
    try:
        data       = request.get_json()
        task_db_id = int(data.get("task_db_id"))
        reason     = data.get("reason", "").strip()
        reviewer   = data.get("reviewer", "Admin")

        if not reason:
            return jsonify({"error": "Rejection reason required"}), 400

        task = Task.query.get(task_db_id)
        if not task:
            return jsonify({"error": "Task not found"}), 404

        task.approval_status  = "rejected"
        task.status           = "in_progress"  # send back to work
        task.rejection_reason = reason
        task.reviewed_by      = reviewer
        task.reviewed_at      = datetime.utcnow()

        db.session.commit()
        return jsonify({
            "success": True,
            "message": "Task rejected — member notified",
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ── Get Pending Approvals (Admin) ──────────────────────────────────
@app.route("/api/admin/pending_approvals", methods=["GET"])
def pending_approvals():
    """Admin sees all tasks waiting for approval"""
    if not _check_admin(request):
        return jsonify({"error": "Unauthorized"}), 403
    try:
        pending = Task.query.filter_by(
            approval_status="pending"
        ).order_by(Task.submitted_at.desc()).all()

        result = []
        for t in pending:
            project = Project.query.get(t.project_id)
            result.append({
                **t.to_dict(),
                "project_title": project.title if project else "Unknown",
                "project_id":    t.project_id,
            })

        return jsonify({
            "total_pending": len(result),
            "tasks":         result,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Serve uploaded proof files ─────────────────────────────────────
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route("/api/log_work", methods=["POST"])
def log_work():
    """
    Save daily work log.
    AI automatically calculates progress — no manual slider.
    """
    try:
        data         = request.get_json()
        project_id   = data.get("project_id")
        task_db_id   = int(data.get("task_db_id"))
        member_name  = data.get("member_name",  "").strip()
        hours_worked = float(data.get("hours_worked", 0))
        work_done    = data.get("work_done",    "").strip()
        blockers     = data.get("blockers",     "").strip()
        log_date     = data.get("date", date.today().isoformat())

        if not work_done:
            return jsonify({"error": "Please describe what was done"}), 400
        if hours_worked <= 0:
            return jsonify({"error": "Please enter hours worked"}), 400

        # Get current task
        task = Task.query.get(task_db_id)
        if not task:
            return jsonify({"error": "Task not found"}), 404

        previous_progress = task.progress or 0

        # ── AI CALCULATES PROGRESS AUTOMATICALLY ──────────────────
        print(f"[AI Progress] Calculating for task: {task.name}")
        ai_result = engine.calculate_progress(
            task_name         = task.name,
            task_description  = task.description or "",
            task_type         = task.type,
            work_done         = work_done,
            hours_worked      = hours_worked,
            previous_progress = previous_progress,
            blockers          = blockers,
        )

        new_progress = ai_result["progress"]
        new_status   = ai_result["status"]

        print(f"[AI Progress] {task.name}: "
              f"{previous_progress}% → {new_progress}% "
              f"({ai_result['reasoning']})")

        # Save work log with AI-calculated progress and error analysis
        work_log = WorkLog(
            project_id       = project_id,
            task_id          = task_db_id,
            member_name      = member_name,
            date             = date.fromisoformat(log_date),
            hours_worked     = hours_worked,
            work_done        = work_done,
            progress_pct     = new_progress,
            blockers         = blockers or None,
            ai_analysis_json = json.dumps(ai_result)
        )
        db.session.add(work_log)

        # Update task with AI-calculated values
        task.progress = new_progress
        task.status   = new_status

        # Update project overall progress
        project = Project.query.get(project_id)
        if project:
            project.progress   = project.calculate_progress()
            project.updated_at = datetime.utcnow()

        # Auto update member scores
        db.session.commit()

        # Trigger score update in background
        try:
            _update_member_score(project_id, member_name, project)
        except Exception as se:
            print(f"[Score] Update failed (non-critical): {se}")

        return jsonify({
            "success":          True,
            # AI result
            "ai_progress":      new_progress,
            "ai_reasoning":     ai_result.get("reasoning", ""),
            "ai_confidence":    ai_result.get("confidence", 0),
            "ai_encouragement": ai_result.get("encouragement", ""),
            "ai_status":        new_status,
            # Project
            "project_progress": project.calculate_progress(),
            "task_status":      new_status,
            "task_progress":    new_progress,
            "progress_change":  new_progress - previous_progress,
        })

    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] log_work: {e}")
        return jsonify({"error": str(e)}), 500


def _update_member_score(project_id, member_name, project):
    """Helper — recalculate one member's score after work log"""
    from datetime import date as date_type, timedelta
    tasks     = project.tasks
    work_logs = project.work_logs
    total_tasks = len(tasks)

    m_logs = [l for l in work_logs if l.member_name == member_name]
    total_hours   = sum(l.hours_worked for l in m_logs)
    tasks_done    = sum(1 for t in tasks
                        if t.assignee == member_name
                        and t.status == "done"
                        and getattr(t, 'approval_status', '') == "approved")
    tasks_rejected = sum(1 for t in tasks
                         if t.assignee == member_name
                         and getattr(t, 'approval_status', '') == "rejected")

    # Streak
    today   = date_type.today()
    streak  = 0
    check   = today
    log_dates = {l.date for l in m_logs}
    while check in log_dates:
        streak += 1
        check  -= timedelta(days=1)

    result = engine.score_member(
        member_name=member_name, tasks_completed=tasks_done,
        tasks_rejected=tasks_rejected, total_hours=total_hours,
        streak_days=streak, total_tasks=total_tasks,
    )

    ms = MemberScore.query.filter_by(
        project_id=project_id, member_name=member_name
    ).first()
    if not ms:
        ms = MemberScore(project_id=project_id, member_name=member_name)
        db.session.add(ms)

    ms.total_score     = result["score"]
    ms.badge           = result["badge"]
    ms.tasks_completed = tasks_done
    ms.tasks_rejected  = tasks_rejected
    ms.total_hours     = total_hours
    ms.streak_days     = streak
    ms.consistency_pct = result["consistency"]
    ms.quality_pct     = result["quality"]
    ms.last_active     = today
    ms.updated_at      = datetime.utcnow()
    db.session.commit()


@app.route("/api/work_logs/<project_id>", methods=["GET"])
def get_work_logs(project_id):
    try:
        logs    = WorkLog.query.filter_by(project_id=project_id)\
                         .order_by(WorkLog.date.desc()).all()
        grouped = {}
        for log in logs:
            day = log.date.isoformat()
            if day not in grouped: grouped[day] = []
            grouped[day].append(log.to_dict())  # type: ignore
        return jsonify({"total_logs": len(logs), "grouped_by_date": grouped})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/update_status", methods=["POST"])
def update_status():
    try:
        data       = request.get_json()
        task_db_id = int(data.get("task_db_id"))
        new_status = data.get("status")

        if new_status not in ["todo", "in_progress", "done"]:
            return jsonify({"error": "Invalid status"}), 400

        task = Task.query.get(task_db_id)
        if not task:
            return jsonify({"error": "Task not found"}), 404

        task.status   = new_status
        task.progress = (100.0 if new_status == "done" else
                         0.0   if new_status == "todo" else task.progress)

        project = Project.query.get(task.project_id)
        if project:
            project.progress   = project.calculate_progress()
            project.updated_at = datetime.utcnow()

        db.session.commit()
        return jsonify({
            "success":          True,
            "task_status":      task.status,
            "project_progress": project.calculate_progress(),
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route("/api/project_stats/<project_id>", methods=["GET"])
def project_stats(project_id):
    try:
        project = Project.query.get(project_id)
        if not project:
            return jsonify({"error": "Not found"}), 404

        tasks     = project.tasks
        work_logs = project.work_logs

        member_hours = {}
        daily_hours  = {}
        for log in work_logs:
            member_hours[log.member_name] = \
                member_hours.get(log.member_name, 0) + log.hours_worked
            day = log.date.isoformat()
            daily_hours[day] = daily_hours.get(day, 0) + log.hours_worked

        return jsonify({
            "project_id":       project_id,
            "title":            project.title,
            "overall_progress": project.calculate_progress(),
            "status":           project.status,
            "total_tasks":      len(tasks),
            "status_counts": {
                "todo":        sum(1 for t in tasks if t.status == "todo"),
                "in_progress": sum(1 for t in tasks if t.status == "in_progress"),
                "done":        sum(1 for t in tasks if t.status == "done"),
            },
            "total_logs":    len(work_logs),
            "member_hours":  member_hours,
            "daily_hours":   daily_hours,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/add_comment", methods=["POST"])
def add_comment():
    try:
        data        = request.get_json()
        task_db_id  = int(data.get("task_db_id"))
        member_name = data.get("member_name", "").strip()
        message     = data.get("message",     "").strip()
        if not message:
            return jsonify({"error": "Comment cannot be empty"}), 400
        comment = Comment(task_id=task_db_id,
                          member_name=member_name, message=message)
        db.session.add(comment)
        db.session.commit()
        return jsonify({"success": True, "comment": comment.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ── Admin Routes ───────────────────────────────────────────────────


@app.route("/api/admin/stats", methods=["GET"])
def admin_stats():
    if not _check_admin(request):
        return jsonify({"error": "Unauthorized"}), 403
    try:
        all_logs = WorkLog.query.all()
        all_proj = Project.query.all()
        return jsonify({
            "total_projects":  Project.query.count(),
            "total_tasks":     Task.query.count(),
            "total_work_logs": WorkLog.query.count(),
            "total_hours":     round(sum(l.hours_worked for l in all_logs), 1),
            "active_projects": sum(1 for p in all_proj if p.calculate_progress() < 100),
            "done_projects":   sum(1 for p in all_proj if p.calculate_progress() >= 100),
            "unique_users":    len(set(p.user_id for p in all_proj if p.user_id)),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/all_projects", methods=["GET"])
def admin_all_projects():
    if not _check_admin(request):
        return jsonify({"error": "Unauthorized"}), 403
    try:
        projects = Project.query.order_by(Project.created_at.desc()).all()
        result   = []
        for p in projects:
            total_hours = sum(l.hours_worked for l in p.work_logs)
            result.append({
                "id":           p.id,
                "user_id":      p.user_id,
                "user_email":   p.user_email or "Guest",
                "user_name":    p.user_name  or "Anonymous",
                "title":        p.title,
                "problem":      p.problem,
                "deadline":     p.deadline,
                "summary":      p.summary,
                "total_days":   p.total_days,
                "status":       p.status,
                "progress":     p.calculate_progress(),
                "task_count":   len(p.tasks),
                "member_count": len(p.members),
                "log_count":    len(p.work_logs),
                "total_hours":  round(total_hours, 1),
                "created_at":   p.created_at.strftime("%Y-%m-%d %H:%M"),
                "updated_at":   p.updated_at.strftime("%Y-%m-%d %H:%M"),
            })
        return jsonify({
            "total_projects": len(result),
            "projects":       result,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/project/<project_id>", methods=["GET"])
def admin_project_detail(project_id):
    if not _check_admin(request):
        return jsonify({"error": "Unauthorized"}), 403
    try:
        project = Project.query.get(project_id)
        if not project:
            return jsonify({"error": "Not found"}), 404

        tasks_data = []
        for t in project.tasks:
            logs      = [l.to_dict() for l in t.work_logs]
            total_h   = sum(l["hours_worked"] for l in logs)
            task_dict = t.to_dict()
            task_dict.update({
                "work_logs":   logs,
                "total_hours": round(total_h, 1),
                "comments":    [c.to_dict() for c in t.comments],
            })
            tasks_data.append(task_dict)

        return jsonify({
            "project":       project.to_dict(),
            "tasks":         tasks_data,
            "members":       [m.to_dict() for m in project.members],
            "all_work_logs": [l.to_dict() for l in project.work_logs],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/delete/<project_id>", methods=["DELETE"])
def admin_delete_project(project_id):
    if not _check_admin(request):
        return jsonify({"error": "Unauthorized"}), 403
    try:
        project = Project.query.get(project_id)
        if not project:
            return jsonify({"error": "Not found"}), 404
        db.session.delete(project)
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════════════════════════════
#  WAR ROOM ROUTES
# ══════════════════════════════════════════════════════════════════

# ── Risk Radar ─────────────────────────────────────────────────────
@app.route("/api/risk_scan/<project_id>", methods=["POST"])
def risk_scan(project_id):
    """
    Trigger AI risk scan for a project.
    Returns risk score, warnings, recommendations.
    """
    try:
        project = Project.query.get(project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404

        tasks     = [t.to_dict() for t in project.tasks]
        work_logs = [l.to_dict() for l in project.work_logs]
        members   = [m.to_dict() for m in project.members]

        # Call AI risk analysis
        result = engine.analyze_risks(
            project_title = project.title,
            problem       = project.problem,
            deadline      = project.deadline,
            tasks         = tasks,
            work_logs     = work_logs,
            members       = members,
        )

        # Save risk log to database
        risk_log = RiskLog(
            project_id      = project_id,
            risk_score      = result["risk_score"],
            risk_level      = result["risk_level"],
            summary         = result["summary"],
            warnings        = json.dumps(result.get("warnings", [])),
            recommendations = json.dumps(result.get("recommendations", [])),
            deadline_safe   = result.get("deadline_safe", True),
        )
        db.session.add(risk_log)
        db.session.commit()

        print(f"[Risk] Project {project_id} scanned — "
              f"Score: {result['risk_score']} ({result['risk_level']})")

        return jsonify({"success": True, "risk": result})

    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] risk_scan: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/risk_history/<project_id>", methods=["GET"])
def risk_history(project_id):
    """Get risk score history for a project (last 7 scans)"""
    try:
        logs = RiskLog.query.filter_by(project_id=project_id)\
                      .order_by(RiskLog.scanned_at.desc())\
                      .limit(7).all()
        return jsonify({
            "project_id": project_id,
            "history":    [l.to_dict() for l in logs],
            "latest":     logs[0].to_dict() if logs else None,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Member Scores ──────────────────────────────────────────────────
@app.route("/api/update_scores/<project_id>", methods=["POST"])
def update_scores(project_id):
    """
    Recalculate performance scores for ALL members in a project.
    Call this after every work log or task completion.
    """
    try:
        project = Project.query.get(project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404

        members   = project.members
        tasks     = project.tasks
        work_logs = project.work_logs
        total_tasks = len(tasks)

        scores = []
        for member in members:
            name = member.name

            # Calculate stats for this member
            m_logs = [l for l in work_logs if l.member_name == name]
            total_hours = sum(l.hours_worked for l in m_logs)

            tasks_done = sum(
                1 for t in tasks
                if t.assignee == name and t.status == "done"
                and t.approval_status == "approved"
            )
            tasks_rejected = sum(
                1 for t in tasks
                if t.assignee == name
                and t.approval_status == "rejected"
            )

            # Streak calculation
            from datetime import date, timedelta
            today   = date.today()
            streak  = 0
            check   = today
            log_dates = {l.date for l in m_logs}
            while check in log_dates:
                streak += 1
                check  -= timedelta(days=1)

            # Get AI score
            result = engine.score_member(
                member_name     = name,
                tasks_completed = tasks_done,
                tasks_rejected  = tasks_rejected,
                total_hours     = total_hours,
                streak_days     = streak,
                total_tasks     = total_tasks,
            )

            # Update or create MemberScore record
            ms = MemberScore.query.filter_by(
                project_id=project_id, member_name=name
            ).first()

            if not ms:
                ms = MemberScore(
                    project_id  = project_id,
                    member_name = name,
                )
                db.session.add(ms)

            ms.total_score     = result["score"]
            ms.badge           = result["badge"]
            ms.tasks_completed = tasks_done
            ms.tasks_rejected  = tasks_rejected
            ms.total_hours     = total_hours
            ms.streak_days     = streak
            ms.consistency_pct = result["consistency"]
            ms.quality_pct     = result["quality"]
            ms.last_active     = m_logs[-1].date if m_logs else None
            ms.updated_at      = datetime.utcnow()

            scores.append(ms.to_dict())

        db.session.commit()

        # Sort by score descending
        scores.sort(key=lambda x: x["total_score"], reverse=True)
        return jsonify({"success": True, "scores": scores})

    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] update_scores: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/leaderboard/<project_id>", methods=["GET"])
def leaderboard(project_id):
    """Get current leaderboard for a project"""
    try:
        scores = MemberScore.query.filter_by(project_id=project_id)\
                            .order_by(MemberScore.total_score.desc()).all()
        return jsonify({
            "project_id":  project_id,
            "leaderboard": [s.to_dict() for s in scores],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Daily Standup ──────────────────────────────────────────────────
@app.route("/api/generate_standup/<project_id>", methods=["POST"])
def generate_standup(project_id):
    """
    Generate AI daily standup report for a project.
    """
    try:
        project = Project.query.get(project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404

        tasks     = [t.to_dict() for t in project.tasks]
        work_logs = [l.to_dict() for l in project.work_logs]
        members   = [m.to_dict() for m in project.members]

        # Calculate days remaining
        days_remaining = None
        if project.deadline:
            try:
                from datetime import date
                # Try parsing common formats
                for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%B %d %Y"]:
                    try:
                        dl = datetime.strptime(project.deadline, fmt).date()
                        days_remaining = (dl - date.today()).days
                        break
                    except ValueError:
                        continue
            except Exception:
                pass

        # Generate via AI
        result = engine.generate_standup(
            project_title  = project.title,
            deadline       = project.deadline,
            tasks          = tasks,
            work_logs      = work_logs,
            members        = members,
            days_remaining = days_remaining,
        )

        # Save to database
        from datetime import date
        today = date.today()

        # Delete today's existing report if any
        StandupReport.query.filter_by(
            project_id  = project_id,
            report_date = today,
        ).delete()

        report = StandupReport(
            project_id      = project_id,
            report_date     = today,
            completed_tasks = json.dumps(result.get("completed_yesterday", [])),
            in_progress     = json.dumps(result.get("in_progress_today",   [])),
            blockers        = json.dumps(result.get("blockers",             [])),
            achievements    = json.dumps(result.get("achievements",         [])),
            health_status   = result.get("health_status", "on_track"),
            health_score    = result.get("health_score",  50),
            days_remaining  = days_remaining,
            summary         = result.get("summary",   ""),
            ai_advice       = result.get("ai_advice", ""),
        )
        db.session.add(report)
        db.session.commit()

        print(f"[Standup] Report generated for {project_id} [OK]")
        return jsonify({"success": True, "report": report.to_dict()})

    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] generate_standup: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/standup_history/<project_id>", methods=["GET"])
def standup_history(project_id):
    """Get last 7 standup reports"""
    try:
        reports = StandupReport.query\
                    .filter_by(project_id=project_id)\
                    .order_by(StandupReport.report_date.desc())\
                    .limit(7).all()
        return jsonify({
            "project_id": project_id,
            "reports":    [r.to_dict() for r in reports],
            "latest":     reports[0].to_dict() if reports else None,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── War Room Page ──────────────────────────────────────────────────
@app.route("/warroom/<project_id>")
def war_room(project_id):
    """Full War Room page for a project"""
    project = Project.query.get(project_id)
    if not project:
        return "Project not found", 404
    return render_template("war_room.html", project=project)

# ══════════════════════════════════════════════════════════════════
#  ADMIN LOGS API
# ══════════════════════════════════════════════════════════════════
@app.route("/api/admin/ai_logs", methods=["GET"])
@admin_api_required
def get_ai_logs():
    try:
        logs = AICallLog.query.order_by(AICallLog.created_at.desc()).limit(100).all()
        return jsonify({"logs": [log.to_dict() for log in logs]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def _seed_admin_if_empty():
    """Create a default admin user if none exists."""
    if not AdminUser.query.first():
        default_email    = os.environ.get("ADMIN_EMAIL", "admin@smartsolve.ai")
        default_password = os.environ.get("ADMIN_PASSWORD", "changeme123")
        
        user = AdminUser(email=default_email)
        user.set_password(default_password)
        db.session.add(user)
        try:
            db.session.commit()
            print(f"[Init] Seeded default admin: {default_email}")
        except Exception as e:
            db.session.rollback()
            print(f"[Init] Could not seed admin: {e}")

# ══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    with app.app_context():
        _seed_admin_if_empty()

    print("\n" + "=" * 55)
    print("  * SMART SOLVE AI - Server Starting")
    print("  * App:     http://localhost:5000")
    print("  * Tracker: http://localhost:5000/tracker/<ID>")
    print("  * Admin:   http://localhost:5000/admin/dashboard")
    print("  * DB:      SQLite")
    print("  * AI Mode:", engine.mode)
    print("=" * 55 + "\n")
    app.run(debug=True, port=5000)
    