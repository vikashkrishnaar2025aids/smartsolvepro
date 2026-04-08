# ⚡ Smart Solve AI — Intelligent Project Planning System

An AI-powered system that converts a problem statement into a complete execution plan with Gantt charts, skill-based task assignment, and beautiful visualizations.

---

## 🚀 Quick Start

### 1. Install dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Set your API key (optional but recommended)
```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY or OPENAI_API_KEY
```

### 3. Run the server
```bash
python app.py
```

### 4. Open in browser
```
http://localhost:5000
```

---

## 🧠 AI Modes

| Mode | Setup | Quality |
|------|-------|---------|
| **Claude AI** | Set `ANTHROPIC_API_KEY` in `.env` | ⭐⭐⭐ Best |
| **OpenAI GPT** | Set `OPENAI_API_KEY` in `.env` | ⭐⭐⭐ Best |
| **Rule-Based** | No keys needed | ⭐⭐ Good (works offline) |

The app auto-detects which mode to use.

---

## 📁 Project Structure
```
backend/
├── app.py           ← Flask routes & API
├── ai_engine.py     ← AI logic (Claude / GPT / rules)
├── requirements.txt
├── .env.example     ← Copy to .env and add keys
├── templates/
│   └── index.html   ← Main UI (Jinja2)
└── static/
    ├── style.css      ← Main styles (cyberpunk theme)
    ├── animations.css ← All animations
    └── script.js      ← Frontend logic + Chart.js
```

---

## 🌐 API Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| `GET`  | `/` | Main app UI |
| `POST` | `/api/generate` | Generate project plan |
| `GET`  | `/api/history` | List saved projects |
| `GET`  | `/api/history/<id>` | Get specific project |
| `DELETE` | `/api/history/<id>` | Delete project |
| `POST` | `/api/update-task` | Edit a task name |
| `GET`  | `/api/health` | Server status + AI mode |

---

## 🎨 Features
- ⚡ Real AI task generation (Claude / GPT / rule-based fallback)
- 📊 Task type distribution doughnut chart
- 📊 Team workload horizontal bar chart
- ⏳ Gantt chart with parallel task visualization
- 🎯 Smart skill-based task assignment
- 🔍 Editable task names (click to edit)
- 🗂️ Project history with save/load/delete
- 🌙 Cyberpunk dark theme with neon effects
- ✨ Smooth animations and loading states
- 📱 Responsive layout

---

## 💡 Tips for Demo
1. Enter a detailed problem like: *"Build a food delivery app with real-time GPS tracking, restaurant management, payment integration, and admin dashboard"*
2. Add 3-4 team members with specific skills
3. Set a deadline like "6 weeks"
4. Hit Generate and watch the AI build your plan!
