# Smart Solve AI - Project Rebuild Prompt

Use the following detailed prompt when you want to recreate or continue building the Smart Solve AI project from scratch with an AI agent.

---

## 🚀 Mission Objective
You are an expert full-stack developer and AI engineer tasked with building **Smart Solve AI**, an AI-powered project management, planning, and task execution platform. The goal is to develop a highly polished, functional application with a neo-brutalist/cyberpunk dark mode UI.

## 🛠️ Technology Stack
*   **Backend:** Python 3.10+, Flask, Flask-SQLAlchemy, Flask-Migrate, Flask-CORS.
*   **Database:** SQLite (default for development), structured with relational models.
*   **Authentication:** Session-based authentication using Werkzeug security password hashing.
*   **AI Integration:** Groq, Google Gemini, OpenRouter. Validation using Pydantic.
*   **Frontend Reference:** Vanilla JS/HTML/CSS or React, adhering to an intense dark theme (glassmorphism/neon elements).

## 🗄️ Core Architecture & Database Schema (`models.py`)
Implement `database.py` with an initialized SQLAlchemy `db`. Create these specific models:
1.  **`AdminUser`**: Handles secure login credentials (`id`, `email`, `password_hash`, `role`). Implement `set_password` and `check_password` functions.
2.  **`Project`**: Base project model (`id` (String UUID), `user_email`, `title`, `problem`, `deadline`, `status`, `progress`).
3.  **`Task`**: Belongs to a project (`db_id`, `project_id`, `name`, `type`, `priority`, `durationDays`, `startDay`, `status`, `progress`, `completion_note`, `completion_file`, `completion_url`, `approval_status`, `ai_review_json`).
4.  **`TeamMember`**: Represents project members (`id`, `project_id`, `name`, `skills`).
5.  **`WorkLog`**: Tracking daily progress (`id`, `project_id`, `task_id`, `member_name`, `hours_worked`, `work_done`, `progress_pct`, `ai_analysis_json`).
6.  **`AICallLog`**: Observability model recording LLM calls (`id`, `project_id`, `call_type`, `provider`, `success`, `retry_count`, `error_message`, `duration_ms`).
7.  **`RiskLog`, `StandupReport`, `MemberScore`**: Additional models for AI-driven project risk assessment and gamification.

## ⚙️ Application Logic (`app.py`)
1.  **Environment Variables:** Load `SECRET_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`.
2.  **Authentication Decorators:**
    *   `@admin_required`: Redirects browser requests to `/admin/login`.
    *   `@admin_api_required`: Returns `403 Flask JSON Forbidden` for programmatic access.
3.  **Automatic Seeding:** Check if `AdminUser` is empty on startup. If so, create the default admin using `.env` credentials.
4.  **Endpoints:**
    *   `GET /admin/login`, `POST /admin/login` (Create session)
    *   `GET /api/admin/ai_logs` (Fetch observability data)
    *   `POST /api/project/create` (Triggers AI Engine to parse problem + generate tasks)
    *   `GET /api/project/<project_id>` (Fetch full project data)
    *   `POST /api/tasks/<task_id>/complete` (Upload proof)
    *   `POST /api/tasks/<task_id>/review` (Triggers AI Engine to approve/reject task execution)

## 🧠 AI Engine (`ai_engine.py`)
The system analyzes problem descriptions and generates execution plans. It supports Groq, Gemini, and OpenRouter, with a rule-based fallback.
1.  **Validation:** Enforce structured JSON generation. Consider incorporating Pydantic to strictly type the AI responses to prevent JSON decoding errors. Always implement automatic corrective retries (up to 3 times) if the provider fails to output valid JSON.
2.  **`generate_plan(problem, team, deadline)`**: Instructs the AI to produce 8-12 logically sequenced tasks based on skill matching to the team.
3.  **`calculate_progress(hours_worked, work_done)`**: Calculates realistic progress dynamically instead of trusting arbitrary sliders.
4.  **`review_completion(completion_note, file/url)`**: A dual-reviewer AI that strictly rejects vague task submissions and approves explicit ones.

## 🗺️ Implementation Roadmap
1.  Initialize standard Flask app directory (`backend/app.py`, `backend/models.py`, `backend/ai_engine.py`, `backend/.env`).
2.  Implement the AI Engine first, using Postman/CURL scripts to test the JSON outputs are correctly structured.
3.  Wire up the Flask API with robust error handling and admin required tags.
4.  Build an intense, dark-themed frontend that consumes these APIs seamlessly.
5.  Check AI logging tables (`AICallLog`) to ensure cost control and performance monitoring works correctly.
