"""
Smart Solve AI — AI Engine
Supports two modes:
  1. GPT/Claude API mode (set OPENAI_API_KEY or ANTHROPIC_API_KEY env var)
  2. Rule-based fallback (works with zero API keys)
"""

import os, json, re, math, requests # type: ignore
from typing import List, Dict, Any, Optional, Union

# ─── Try to import OpenAI ────────────────────────────────────────────────────
try:
    from openai import OpenAI # type: ignore
    _OPENAI_AVAILABLE = True
except ImportError:
    _OPENAI_AVAILABLE = False

# ─── Try to import Groq ──────────────────────────────────────────────────────
try:
    from groq import Groq # type: ignore
    _GROQ_AVAILABLE = True
except ImportError:
    _GROQ_AVAILABLE = False

# Anthropic removed as per user request


# ─── Skill → Task-type keyword maps ──────────────────────────────────────────
SKILL_KEYWORDS = {
    "development": ["python","javascript","react","node","java","c++","ruby","go","rust","backend","frontend","fullstack","api","flask","django","express","spring","php","typescript","kotlin","swift","android","ios","mobile"],
    "design":      ["ui","ux","figma","sketch","design","photoshop","illustrator","css","html","animation","branding","wireframe","prototype","visual","graphic"],
    "research":    ["research","data","analysis","ml","machine learning","ai","nlp","statistics","science","analytics","excel","tableau","power bi","r","pandas","numpy"],
    "testing":     ["testing","qa","quality","selenium","cypress","jest","pytest","automation","manual","test","tdd","bdd","playwright"],
    "planning":    ["pm","project","management","scrum","agile","jira","notion","trello","planning","coordination","stakeholder"],
    "deployment":  ["devops","docker","kubernetes","aws","azure","gcp","cloud","ci/cd","jenkins","terraform","linux","sysadmin","deployment","infra"],
}

TASK_TEMPLATES = {
    "web_app": [
        ("Project kickoff & scope definition","planning","high",1,1, ["Stakeholder meeting", "Requirement gathering", "Project setup"]),
        ("UI/UX wireframes & design system","design","high",2,3, ["Moodboard", "Wireframes", "Component library"]),
        ("Database schema design","development","high",2,2, ["ER diagram", "Migration scripts", "Seeding data"]),
        ("Backend API development","development","high",4,6, ["Auth routes", "Business logic", "API Documentation"]),
        ("Frontend implementation","development","high",5,7, ["UI components", "State management", "Service layer"]),
        ("Authentication & security","development","high",8,3, ["OAuth setup", "Rate limiting", "Encryption"]),
        ("Third-party integrations","development","medium",9,4, ["Payment gateway", "Email service", "Storage"]),
        ("Unit & integration testing","testing","high",11,3, ["Test cases", "Automated suites", "Bug fixes"]),
        ("UI/UX review & polish","design","medium",12,2, ["Responsiveness", "Motion design", "Accessibility"]),
        ("Performance optimization","development","medium",13,2, ["Caching", "Asset bundling", "Load testing"]),
        ("Deployment & CI/CD setup","deployment","high",14,2, ["Pipeline setup", "Env config", "SSL"]),
        ("Documentation & handoff","planning","low",15,2, ["User guide", "Technical docs", "Handoff meeting"]),
    ],
    "mobile_app": [
        ("Requirements & user stories","planning","high",1,1, ["Feature list", "User flow", "Mockups"]),
        ("App architecture design","development","high",1,2, ["Platform choice", "Dependency injection", "Module setup"]),
        ("UI mockups & style guide","design","high",2,3, ["App theme", "Screen designs", "Assets export"]),
        ("Core feature development","development","high",4,8, ["Navigation", "Primary screens", "Offline storage"]),
        ("API integration","development","high",7,4, ["REST client", "Data parsing", "Error handling"]),
        ("Push notifications setup","development","medium",10,2, ["FCM/APNS setup", "Deep linking", "Notification UI"]),
        ("QA & device testing","testing","high",11,4, ["Platform-specific testing", "Bug logging", "Final polish"]),
        ("App store assets & metadata","design","medium",13,2, ["Screenshots", "App icon", "Store listing"]),
        ("Beta release","deployment","high",14,2, ["Distibution setup", "Beta feedback", "Crash analytics"]),
        ("Bug fixes & polish","development","medium",15,3, ["Critical fixes", "Animation tuning", "Haptics"]),
    ],
    "ml_ai": [
        ("Problem framing & data audit","research","high",1,2, ["Scope defining", "Data sourcing", "Budgeting"]),
        ("Data collection & cleaning","research","high",2,4, ["Extraction", "Normalization", "Outlier removal"]),
        ("Exploratory data analysis","research","high",4,3, ["Correlation analysis", "Visualization", "Insights report"]),
        ("Feature engineering","research","high",6,3, ["Feature selection", "Dimensionality reduction", "Pipeline setup"]),
        ("Model selection & baseline","development","high",7,3, ["Algorithm evaluation", "Baseline metrics", "Training setup"]),
        ("Model training & tuning","development","high",9,5, ["Hyperparameters", "Cross-validation", "Model storage"]),
        ("Evaluation & validation","testing","high",12,3, ["Accuracy/Recall tests", "Bias audit", "Edge cases"]),
        ("API wrapper & deployment","development","medium",13,3, ["FastAPI wrapper", "Dockerization", "Model serving"]),
        ("Monitoring & logging","deployment","medium",15,2, ["Drift detection", "Performance logs", "Retraining trigger"]),
        ("Documentation","planning","low",16,2, ["Model cards", "Technical guide", "API spec"]),
    ],
    "generic": [
        ("Project planning & kickoff","planning","high",1,1, ["Goals setup", "Milestones", "Team roles"]),
        ("Research & requirements gathering","research","high",1,3, ["Competition audit", "User interviews", "FR/NFR docs"]),
        ("System architecture design","development","high",3,2, ["Tech stack choice", "Integration map", "Sec design"]),
        ("Core feature development","development","high",4,7, ["MVP features", "Logic flow", "Unit testing"]),
        ("UI/UX design","design","medium",4,4, ["Visual language", "Prototypes", "Assets"]),
        ("Frontend implementation","development","medium",7,5, ["Page layouts", "Iteractivity", "Refinement"]),
        ("Integration & API work","development","medium",10,3, ["Data flow", "Third-party APIs", "Connectors"]),
        ("Quality assurance & testing","testing","high",11,4, ["Manual QA", "Regression", "Fixing"]),
        ("Performance & security audit","testing","medium",13,2, ["Pentesting", "Load tests", "Final sweep"]),
        ("Deployment setup","deployment","high",14,2, ["Server config", "CI/CD", "Domain/SSL"]),
        ("Documentation","planning","low",15,2, ["Onboarding", "Technical", "Maintenance"]),
    ],
}

TASK_DESCRIPTIONS = {
    "Project kickoff & scope definition": "Define project goals, success metrics, timeline, and assign roles. Set up project management tools.",
    "UI/UX wireframes & design system": "Create low/high-fidelity wireframes, define color palette, typography, and reusable component library.",
    "Database schema design": "Design entity-relationship model, choose database technology, define indexes and relationships.",
    "Backend API development": "Build RESTful or GraphQL API endpoints, business logic, middleware, and data validation.",
    "Frontend implementation": "Implement responsive UI components, state management, routing, and API integration.",
    "Authentication & security": "Implement login/signup, JWT tokens, OAuth, role-based access control, and security hardening.",
    "Quality assurance & testing": "Write and execute unit, integration, and end-to-end tests. Document bugs and regressions.",
    "Deployment & CI/CD setup": "Configure hosting environment, set up automated pipelines, monitoring, and rollback strategies.",
    "Documentation": "Write technical docs, API reference, onboarding guides, and user manuals.",
}


class AIEngine:
    def __init__(self):
        self.groq_key      = os.environ.get("GROQ_API_KEY", "")
        self.gemini_key    = os.environ.get("GEMINI_API_KEY", "")
        self.openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")

        if self.groq_key and _GROQ_AVAILABLE:
            self.mode = "groq-ai"
        elif self.gemini_key:
            self.mode = "gemini-ai"
        elif self.openrouter_key and _OPENAI_AVAILABLE:
            self.mode = "openrouter-ai"
        else:
            self.mode = "rule-based"

    def set_keys(self, groq_key=None, gemini_key=None, openrouter_key=None):
        if groq_key is not None:
            self.groq_key = groq_key
        if gemini_key is not None:
            self.gemini_key = gemini_key
        if openrouter_key is not None:
            self.openrouter_key = openrouter_key
            
        # Recalculate mode if it was fallback and we got keys
        if self.mode == "rule-based":
            if self.groq_key and _GROQ_AVAILABLE:
                self.mode = "groq-ai"
            elif self.gemini_key:
                self.mode = "gemini-ai"
            elif self.openrouter_key and _OPENAI_AVAILABLE:
                self.mode = "openrouter-ai"

        print(f"[AIEngine] Keys updated. Mode: {self.mode}")

    # ─── Public entry point ───────────────────────────────────────────────────
    def generate_plan(self, problem: str, team: List[Dict], deadline: str) -> Dict:
        if self.mode == "groq-ai":
            return self._groq_plan(problem, team, deadline)
        elif self.mode == "gemini-ai":
            return self._gemini_plan(problem, team, deadline)
        elif self.mode == "openrouter-ai":
            return self._openrouter_plan(problem, team, deadline)
        else:
            return self._rule_based_plan(problem, team, deadline)



    def analyze_problem(self, problem: str, project_history: Dict[str, Any]) -> Dict[str, Any]:
        # Detect similar project from history
        problem_lower = problem.lower()
        words = set(re.findall(r'\w+', problem_lower))
        stop_words = {"a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "with", "build", "create", "make", "app", "project", "system", "i", "need", "want", "software", "my"}
        words -= stop_words

        best_match: Optional[Dict[str, Any]] = None
        best_score = 0

        for pid, proj in project_history.items():
            if not isinstance(proj, dict): continue
            hist_problem = str(proj.get("problem", "")).lower()
            hist_words = set(re.findall(r'\w+', hist_problem))
            score = len(words & hist_words)
            if score > best_score and score >= 2:
                best_score = score
                best_match = proj

        ideas: List[str] = []
        if self.mode != "rule-based":
            # Use AI for deeper analysis if available
            if isinstance(best_match, dict):
                similar_info = f"A similar past project was found: '{best_match.get('title')}' with problem: '{best_match.get('problem')}'."
            else:
                similar_info = "No similar past projects were found in local history."
                
            prompt = f"""You are an expert project consultant. Analyze the following project problem statement and provide 3-5 high-level strategic ideas or insights to help the user plan it better.
            
            PROBLEM: {problem}
            CONTEXT: {similar_info}
            
            Respond ONLY with a JSON object:
            {{
              "ideas": ["idea 1", "idea 2", ...],
              "strategic_focus": "one sentence summarizing the main challenge"
            }}
            """
            try:
                if self.mode == "groq-ai":
                    client = Groq(api_key=self.groq_key)
                    resp = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    raw = resp.choices[0].message.content.strip()
                    raw = raw.replace("```json", "").replace("```", "").strip()
                    ai_res = json.loads(raw)
                elif self.mode == "openrouter-ai":
                    headers = {
                        "Authorization": f"Bearer {self.openrouter_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "http://localhost:5000",
                        "X-Title": "Smart Solve AI",
                    }
                    body = {
                        "model": "meta-llama/llama-3.3-70b-instruct:free",
                        "messages": [{"role": "user", "content": prompt}],
                        "response_format": {"type": "json_object"}
                    }
                    resp = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=body)
                    data = resp.json()
                    raw = data["choices"][0]["message"]["content"].strip()
                    raw = raw.replace("```json", "").replace("```", "").strip()
                    ai_res = json.loads(raw)
                elif self.mode == "gemini-ai":
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
                    payload = {
                        "contents": [{"parts": [{"text": prompt + "\nRespond with raw JSON only."}]}],
                        "generationConfig": {"responseMimeType": "application/json"}
                    }
                    resp = requests.post(url, json=payload)
                    data = resp.json()
                    raw = data['candidates'][0]['content']['parts'][0]['text']
                    ai_res = json.loads(raw)
                else: 
                    ai_res = {}
                
                ideas = ai_res.get("ideas", [])
                if ai_res.get("strategic_focus"):
                    ideas.append(f"Strategic Focus: {ai_res['strategic_focus']}")
            except:
                ideas = self._get_rule_based_ideas(words)
        else:
            ideas = self._get_rule_based_ideas(words)

        result: Dict[str, Any] = {
            "ideas": ideas,
            "similar_project": None
        }

        if best_match:
            result["similar_project"] = {
                "title": best_match.get("title"),
                "problem": best_match.get("problem"),
                "date": best_match.get("created_at")
            }
            if not any("similar past project" in i.lower() for i in ideas):
                ideas.insert(0, f"Found a similar past project: '{best_match.get('title')}'. Consider reviewing it for reuse.")

        return result


    def _get_rule_based_ideas(self, words: set) -> List[str]:
        ideas = [
            "Define clear success metrics and KPIs before kickoff.",
            "Break the core functionality into small, testable milestones.",
            "Identify potential technical risks and dependencies early.",
        ]
        if any(w in words for w in ["ai", "ml", "model", "data"]):
            ideas.append("Prioritize data quality and collection strategy.")
        if any(w in words for w in ["mobile", "ios", "android", "app"]):
            ideas.append("Plan for cross-platform compatibility and offline support.")
        if any(w in words for w in ["web", "site", "dashboard"]):
            ideas.append("Focus on responsive design and load performance.")
        if any(w in words for w in ["security", "auth", "login"]):
            ideas.append("Implement industry-standard OAuth2 or JWT for security.")
        return ideas



    # ─── Task Completion Review ─────────────────────────────────────────────
    def review_completion(self, task_name, task_description,
                          task_type, completion_note,
                          completion_url, proof_filename):
        """
        AI reviews a task completion submission and returns
        a verdict: approved / rejected / needs_more_info
        """

        proof_info: List[str] = []
        if completion_url:
            proof_info.append(f"Proof link provided: {completion_url}")
        if proof_filename:
            proof_info.append(f"Proof file uploaded: {proof_filename}")
        if not proof_info:
            proof_info.append("No file or link provided — only text description")

        prompt = f"""You are a strict but fair AI project reviewer.
A team member has submitted a task completion for review.

TASK DETAILS:
- Task Name: {task_name}
- Task Type: {task_type}
- Task Description: {task_description or 'Not specified'}

MEMBER SUBMISSION:
- What they claim to have done: {completion_note}
- Proof provided: {', '.join(proof_info)}

YOUR JOB:
Review this submission carefully and decide:
1. Is the description specific and detailed enough?
2. Does it match what the task actually requires?
3. Is there sufficient proof provided?

STRICT RULES:
- Reject if the description is vague (e.g. "I did the task", "completed it")
- Reject if no proof file or link is provided for development/design/testing tasks
- Approve if description clearly explains what was done with specific details
- For research tasks, detailed notes can be enough without a file
- Always give actionable feedback

Respond ONLY with this exact JSON (no markdown, no extra text):
{{
  "verdict": "approved" | "rejected" | "needs_more_info",
  "confidence": 0-100,
  "summary": "One sentence summary of your decision",
  "feedback": "2-3 sentences of specific, actionable feedback for the member",
  "errors": ["list", "of", "detected", "logic/work", "errors"],
  "corrections": ["list", "of", "specific", "steps", "to", "fix", "them"],
  "missing": ["list", "of", "specific", "missing", "items"]
}}"""

        try:
            raw = self._call_ai(prompt)
            raw = raw.replace("```json", "").replace("```", "").strip()
            result = json.loads(raw)

            # Validate verdict
            if result.get("verdict") not in ["approved", "rejected", "needs_more_info"]:
                result["verdict"] = "needs_more_info"

            return result

        except Exception as e:
            print(f"[AI Review] Error: {e}")
            # Safe fallback — ask for more info instead of auto-approving
            return {
                "verdict":    "needs_more_info",
                "confidence": 0,
                "summary":    "AI review failed — please resubmit with clearer proof",
                "feedback":   "The AI could not process your submission. Please ensure your description is detailed and proof is clearly attached.",
                "missing":    ["Clearer description", "Valid proof file or link"]
            }

    def _call_ai(self, prompt):
        """Internal method — calls whichever AI is active"""
        if self.mode == "groq-ai" and self.groq_key:
            client = Groq(api_key=self.groq_key)
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            return resp.choices[0].message.content.strip()

        elif self.mode == "gemini-ai" and self.gemini_key:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt + "\nRespond with raw JSON only."}]}],
                "generationConfig": {"responseMimeType": "application/json"}
            }
            resp = requests.post(url, json=payload)
            data = resp.json()
            return data['candidates'][0]['content']['parts'][0]['text']

        elif self.mode == "openrouter-ai" and self.openrouter_key:
            headers = {
                "Authorization": f"Bearer {self.openrouter_key}",
                "Content-Type": "application/json",
            }
            body = {
                "model": "meta-llama/llama-3.3-70b-instruct:free",
                "messages": [{"role": "user", "content": prompt}]
            }
            resp = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=body)
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        else:
            return self._rule_based_review(prompt)

    def _rule_based_review(self, prompt):
        """Fallback rule-based reviewer when no AI key is set"""
        # Extract completion note from prompt
        if "vague" in prompt.lower() or len(prompt) < 100:
            verdict = "rejected"
            feedback = "Description is too vague. Please provide specific details."
        elif "completed" in prompt.lower() and ("link" in prompt.lower()
                                                 or "file" in prompt.lower()):
            verdict = "approved"
            feedback = "Good submission with proof provided."
        else:
            verdict = "needs_more_info"
            feedback = "Please provide a proof file or link along with your description."

        return json.dumps({
            "verdict":    verdict,
            "confidence": 70,
            "summary":    f"Rule-based review: {verdict}",
            "feedback":   feedback,
            "missing":    []
        })

    # OpenAI and Claude methods removed as per user request

    # ─── Gemini ───────────────────────────────────────────────────────────────
    def _gemini_plan(self, problem, team, deadline):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
        prompt = self._build_prompt(problem, team, deadline)
        payload = {
            "contents": [{"parts": [{"text": prompt + "\nRespond with raw JSON only."}]}],
            "generationConfig": {"responseMimeType": "application/json"}
        }
        try:
            resp = requests.post(url, json=payload)
            data = resp.json()
            raw = data['candidates'][0]['content']['parts'][0]['text']
            return self._parse_json(raw)
        except Exception as e:
            print(f"Gemini error: {e}")
            return self._rule_based_plan(problem, team, deadline)

    # ─── OpenRouter ───────────────────────────────────────────────────────────
    def _openrouter_plan(self, problem, team, deadline):
        """Uses OpenRouter's API (Llama 3.3 Free model)"""
        headers = {
            "Authorization": f"Bearer {self.openrouter_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5000",
            "X-Title": "Smart Solve AI",
        }
        prompt = self._build_prompt(problem, team, deadline)
        body = {
            "model": "meta-llama/llama-3.3-70b-instruct:free",
            "messages": [
                {"role": "system", "content": "You are a project planning expert. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 2000,
        }
        try:
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=body,
                timeout=30
            )
            if resp.status_code != 200:
                raise Exception(f"OpenRouter error: {resp.text}")
            data = resp.json()
            raw = data["choices"][0]["message"]["content"].strip()
            return self._parse_json(raw)
        except Exception as e:
            print(f"OpenRouter failed: {e}")
            return self._rule_based_plan(problem, team, deadline)



    # ─── Groq (High Speed) ───────────────────────────────────────────────────
    def _groq_plan(self, problem, team, deadline):
        """Uses Groq's high-speed inference (LPU)"""
        if not _GROQ_AVAILABLE: return self._rule_based_plan(problem, team, deadline)
        client = Groq(api_key=self.groq_key)
        prompt = self._build_prompt(problem, team, deadline)
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a project planning expert. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000,
        )
        raw = resp.choices[0].message.content.strip()
        return self._parse_json(raw)


    # ─── Rule-based fallback ──────────────────────────────────────────────────
    def _rule_based_plan(self, problem: str, team: List[Dict], deadline: str) -> Dict:
        problem_lower = problem.lower()

        # Detect project category
        if any(w in problem_lower for w in ["mobile","android","ios","app store","flutter","react native"]):
            template_key = "mobile_app"
            title = "Mobile Application Project"
        elif any(w in problem_lower for w in ["ml","machine learning","ai","model","neural","nlp","prediction","classification"]):
            template_key = "ml_ai"
            title = "AI/ML Project"
        elif any(w in problem_lower for w in ["web","website","dashboard","portal","saas","platform","react","angular","vue"]):
            template_key = "web_app"
            title = self._extract_title(problem)
        else:
            template_key = "generic"
            title = self._extract_title(problem)

        template = TASK_TEMPLATES[template_key]

        # Build initial tasks
        tasks: List[Dict[str, Any]] = []
        for i, (name, ttype, priority, start_day, duration, subs) in enumerate(template, 1):
            tasks.append({
                "id": i,
                "name": name,
                "description": TASK_DESCRIPTIONS.get(name, f"Complete {name.lower()} phase of the project."),
                "type": ttype,
                "priority": priority,
                "subtasks": subs,
                "durationDays": int(duration),
                "startDay": int(start_day),
                "dependencies": [i-1] if i > 1 and priority == "high" else [],
                "assignee": None, # Will be assigned during optimization
            })

        # Process scheduling and allocation
        optimized_tasks = self._calculate_optimized_schedule(tasks, team, deadline)

        total_days = max((int(t["startDay"]) + int(t["durationDays"]) - 1) for t in optimized_tasks)

        summary = (
            f"This optimized plan divides the project into {len(optimized_tasks)} structured phases with "
            f"{sum(len(t['subtasks']) for t in optimized_tasks)} specific subtasks. "
            f"Work is allocated to {len(team) if team else 'a general team'} based on specific skills. "
            f"The schedule is optimized for parallel execution, completing in {total_days} days."
        )

        return {
            "projectTitle": title,
            "summary": summary,
            "totalDays": total_days,
            "tasks": optimized_tasks,
        }

    def _calculate_optimized_schedule(self, tasks: List[Dict], team: List[Dict], deadline: str) -> List[Dict]:
        """
        Calculates an optimized execution schedule considering:
        1. Task dependencies
        2. Assignee capability & availability
        3. Deadline constraints
        """
        # 1. Assignment (Workforce Allocation)
        member_workload: Dict[str, int] = {str(m.get('name', '')): 0 for m in team} if team else {'Team': 0}
        
        for t in tasks:
            t['assignee'] = self._match_skill(t['type'], team)
            # Basic workload tracking - could be more complex
            if team:
                member_workload[t['assignee']] += t['durationDays']

        # 2. Scheduling (Timeline Generation)
        # Use a simple greedy approach for start days based on dependencies
        for i, t in enumerate(tasks):
            if i == 0:
                t['startDay'] = 1
                continue
            
            # Start after dependencies
            dep_finish_time = 0
            for dep_id in t.get('dependencies', []):
                dep_task = next((task for task in tasks if task['id'] == dep_id), None)
                if dep_task:
                    dep_finish_time = max(dep_finish_time, dep_task['startDay'] + dep_task['durationDays'] - 1)
            
            # Simple resource constraint: member can only do one task at a time
            member_busy_until = 0
            if team:
                member_tasks = [task for j, task in enumerate(tasks) if task['assignee'] == t['assignee'] and j < i]
                if member_tasks:
                    member_busy_until = max(task['startDay'] + task['durationDays'] - 1 for task in member_tasks)
            
            t['startDay'] = max(dep_finish_time + 1, member_busy_until + 1 if member_busy_until > 0 else 1)

        # 3. Deadline Adjustment
        if deadline:
            estimated_target = self._parse_deadline_days(deadline)
            if estimated_target:
                current_total = max(t['startDay'] + t['durationDays'] - 1 for t in tasks)
                if current_total > estimated_target:
                    # Compress (crash) the schedule by scaling durations
                    scale = estimated_target / current_total
                    for t in tasks:
                        t['durationDays'] = max(1, round(t['durationDays'] * scale))
                        t['startDay'] = max(1, round((t['startDay'] - 1) * scale) + 1)

        return tasks

    # ─── Helpers ──────────────────────────────────────────────────────────────
    def _build_prompt(self, problem, team, deadline):
        team_str = json.dumps(team) if team else "unspecified team"
        return f"""You are an advanced AI project architecture agent. Deconstruct the following problem into a high-performance execution plan.

PROBLEM: {problem}
TEAM_CONTEXT: {team_str}
DEADLINE: {deadline or 'Optimized for quality'}

Respond ONLY with valid JSON:
{{
  "projectTitle": "Clear, professional project name",
  "summary": "Strategic analysis of the problem, addressing technical risks and the rationale for the following allocation.",
  "totalDays": <integer>,
  "tasks": [
    {{
      "id": 1,
      "name": "Phase Name",
      "description": "High-level goal of this phase",
      "type": "development|design|research|testing|planning|deployment",
      "priority": "high|medium|low",
      "assignee": "Member Name (Match skills EXACTLY if team provided, else 'Team')",
      "durationDays": <int>,
      "startDay": <int>,
      "dependencies": [id1, id2],
      "subtasks": ["Granular subtask 1", "Granular subtask 2", "Granular subtask 3"]
    }}
  ]
}}

Rules:
1. Divide the problem into 8-12 logically structured tasks.
2. Each task MUST have 3-5 specific, actionable subtasks.
3. ALLOCATE work based on team member capabilities provided in TEAM_CONTEXT.
4. Calculate 'startDay' and 'durationDays' to create an OPTIMIZED EXECUTION SCHEDULE (allow parallel work for different members).
5. Ensure dependencies are logically mapped (e.g., design precedes development)."""

    def _parse_json(self, raw: str) -> Dict:
        cleaned = re.sub(r"```json|```", "", raw).strip()
        return json.loads(cleaned)

    def _extract_title(self, problem: str) -> str:
        words_list = problem.split()
        words = [words_list[i] for i in range(min(6, len(words_list)))]
        title = " ".join(w.capitalize() for w in words)
        return title if len(title) < 50 else "Smart Project"

    def _match_skill(self, task_type: str, team: List[Dict]) -> str:
        if not team:
            return "Team"
        keywords = SKILL_KEYWORDS.get(task_type, [])
        best_member = None
        best_score  = -1
        for member in team:
            skills_lower = member.get("skills", "").lower()
            score = sum(1 for kw in keywords if kw in skills_lower)
            if score > best_score:
                best_score  = score
                best_member = str(member.get("name", ""))
        return str(best_member) if best_member else str(team[0].get("name", "Team"))

    def _parse_deadline_days(self, deadline: str) -> Optional[int]:
        deadline = deadline.lower()
        nums = re.findall(r"\d+", deadline)
        if not nums:
            return None
        n = int(nums[0])
        if "month" in deadline:
            return n * 30
        if "week" in deadline:
            return n * 7
        return n  # assume days

# ══════════════════════════════════════════════════════════════════
#  WAR ROOM AI METHODS
# ══════════════════════════════════════════════════════════════════

    def calculate_progress(self, task_name, task_description,
                           task_type, work_done, hours_worked,
                           previous_progress, blockers):
        """
        AI reads what the member wrote and automatically
        calculates a realistic progress percentage.
        No manual slider needed.
        """
        prompt = f"""You are an AI project progress analyzer.
A team member has logged their daily work. 
Calculate the realistic progress percentage for this task.

TASK DETAILS:
- Task Name: {task_name}
- Task Type: {task_type}
- Task Description: {task_description or 'Not specified'}
- Previous Progress: {previous_progress}%

TODAY'S WORK LOG:
- Hours Worked: {hours_worked}
- What Was Done: {work_done}
- Blockers: {blockers or 'None'}

YOUR JOB:
Based on what was actually described as done today,
calculate how much total progress this task is at now.

RULES:
- Be realistic and strict — don't over-estimate
- If work description is vague, give low progress increase
- If specific completed items are mentioned, reward appropriately  
- If blockers exist, limit progress increase
- Never decrease progress from previous value ({previous_progress}%)
- 100% means fully complete and ready for review
- Consider hours worked vs typical task complexity

Respond ONLY with valid JSON (no markdown):
{{
  "progress": <integer 0-100>,
  "reasoning": "One sentence explaining why this percentage",
  "confidence": <integer 0-100>,
  "status": "todo" | "in_progress" | "done",
  "errors": ["list", "of", "detected", "logic/work", "errors", "if", "any"],
  "corrections": ["list", "of", "specific", "steps", "to", "fix", "them"],
  "encouragement": "One short motivating line for the member"
}}"""

        try:
            raw    = self._call_ai(prompt)
            raw    = raw.replace("```json","").replace("```","").strip()
            result = json.loads(raw)

            # Safety checks
            new_progress = int(result.get("progress", previous_progress))
            # Never go below previous progress
            new_progress = max(previous_progress, min(100, new_progress))
            result["progress"] = new_progress

            # Auto-set status based on progress
            if new_progress >= 100:
                result["status"] = "done"
            elif new_progress > 0:
                result["status"] = "in_progress"
            else:
                result["status"] = "todo"

            return result

        except Exception as e:
            print(f"[AI Progress] Error: {e}")
            # Fallback — rule based calculation
            increase = 0
            if hours_worked >= 6:   increase = 25
            elif hours_worked >= 4: increase = 18
            elif hours_worked >= 2: increase = 12
            elif hours_worked >= 1: increase = 7
            else:                   increase = 3

            # Reduce if blockers
            if blockers:
                increase = int(increase * 0.6)

            new_progress = min(100, previous_progress + increase)
            return {
                "progress":      new_progress,
                "reasoning":     f"Estimated based on {hours_worked}h worked",
                "confidence":    60,
                "status":        "done" if new_progress >= 100
                                 else "in_progress" if new_progress > 0
                                 else "todo",
                "encouragement": "Keep up the good work!"
            }

    def analyze_risks(self, project_title, problem, deadline,
                      tasks, work_logs, members):
        """
        AI scans the project and returns a full risk analysis.
        """
        # Build task summary for AI
        task_summary: List[str] = []
        for t in tasks:
            logs_for_task = [l for l in work_logs if l.get("task_id") == t.get("db_id")]
            last_log = logs_for_task[0]["date"] if logs_for_task else "Never"
            task_summary.append(
                f"- [{t['status'].upper()}] {t['name']} "
                f"(assigned: {t['assignee']}, "
                f"progress: {t['progress']}%, "
                f"last activity: {last_log})"
            )

        # Member activity summary
        member_summary: List[str] = []
        from datetime import date
        today = date.today()
        for m in members:
            m_logs = [l for l in work_logs if l.get("member_name") == m.get("name")]
            if m_logs:
                last_date = m_logs[0].get("date", "Unknown")
                total_h   = sum(float(l.get("hours_worked", 0)) for l in m_logs)
                member_summary.append(
                    f"- {m['name']}: {len(m_logs)} logs, "
                    f"{round(total_h * 10) / 10.0}h total, last active: {last_date}"
                )
            else:
                member_summary.append(
                    f"- {m['name']}: NO work logged yet ⚠"
                )

        done_count = sum(1 for t in tasks if t["status"] == "done")
        total      = len(tasks)
        progress   = round(((done_count / total * 100) if total else 0.0) * 10) / 10.0

        prompt = f"""You are an expert AI project risk analyst.
Analyze this project and return a detailed risk assessment.

PROJECT: {project_title}
PROBLEM: {problem}
DEADLINE: {deadline or 'Not set'}
OVERALL PROGRESS: {progress}% ({done_count}/{total} tasks done)

TASK STATUS:
{chr(10).join(task_summary) or 'No tasks found'}

TEAM ACTIVITY:
{chr(10).join(member_summary) or 'No members found'}

Analyze:
1. Is the project at risk of missing its deadline?
2. Which tasks are blocked or stalled?
3. Which team members are inactive?
4. What are the top risks right now?
5. What should the team do TODAY to get back on track?

Respond ONLY with valid JSON (no markdown):
{{
  "risk_score": 0-100,
  "risk_level": "low" | "medium" | "high" | "critical",
  "deadline_safe": true | false,
  "summary": "2-sentence overall assessment",
  "warnings": [
    "Specific warning 1",
    "Specific warning 2",
    "Specific warning 3"
  ],
  "recommendations": [
    "Specific action 1 to take today",
    "Specific action 2",
    "Specific action 3"
  ]
}}

Risk score guide:
0-25   = Low risk, everything on track
26-50  = Medium risk, some concerns
51-75  = High risk, immediate action needed
76-100 = Critical, project in danger"""

        try:
            raw    = self._call_ai(prompt)
            raw    = raw.replace("```json", "").replace("```", "").strip()
            result = json.loads(raw)
            # Clamp risk score
            result["risk_score"] = max(0, min(100, int(result.get("risk_score", 50))))
            return result
        except Exception as e:
            print(f"[AI Risk] Error: {e}")
            return {
                "risk_score":      50,
                "risk_level":      "medium",
                "deadline_safe":   True,
                "summary":         "Risk analysis temporarily unavailable.",
                "warnings":        ["AI analysis failed — check manually"],
                "recommendations": ["Review task progress manually",
                                    "Check team member activity"]
            }

    def score_member(self, member_name, tasks_completed,
                     tasks_rejected, total_hours,
                     streak_days, total_tasks):
        """
        Calculate a member's performance score based on their activity.
        Returns score 0-100 and badge.
        """
        # Rule-based scoring (works without AI key)
        score = 0

        # Delivery score (40 points max)
        if total_tasks > 0:
            completion_rate = tasks_completed / total_tasks
            score += int(completion_rate * 40)

        # Quality score (30 points max)
        total_submissions = tasks_completed + tasks_rejected
        if total_submissions > 0:
            quality_rate = tasks_completed / total_submissions
            score += int(quality_rate * 30)
        elif tasks_completed == 0:
            score += 15  # neutral if no submissions yet

        # Hours contribution (20 points max)
        if total_hours >= 40:
            score += 20
        elif total_hours >= 20:
            score += 15
        elif total_hours >= 10:
            score += 10
        elif total_hours > 0:
            score += 5

        # Streak bonus (10 points max)
        if streak_days >= 7:
            score += 10
        elif streak_days >= 5:
            score += 8
        elif streak_days >= 3:
            score += 5
        elif streak_days >= 1:
            score += 2

        score = max(0, min(100, score))

        # Badge assignment
        if score >= 90:
            badge = "legend"
        elif score >= 75:
            badge = "champion"
        elif score >= 55:
            badge = "achiever"
        elif score >= 30:
            badge = "contributor"
        else:
            badge = "newcomer"

        consistency = round(((tasks_completed / max(total_tasks, 1)) * 100) * 10) / 10.0
        quality     = round(((tasks_completed / max(tasks_completed + tasks_rejected, 1)) * 100) * 10) / 10.0

        return {
            "score":       score,
            "badge":       badge,
            "consistency": consistency,
            "quality":     quality,
        }

    def generate_standup(self, project_title, deadline,
                         tasks, work_logs, members,
                         days_remaining):
        """
        Generate a daily standup report using AI.
        """
        from datetime import date, timedelta
        today     = date.today()
        yesterday = today - timedelta(days=1)

        # Work done yesterday
        yesterday_logs = [
            l for l in work_logs
            if l.get("date") == yesterday.isoformat()
        ]
        today_logs = [
            l for l in work_logs
            if l.get("date") == today.isoformat()
        ]

        # Tasks in progress
        in_prog: List[Dict[str, Any]] = [t for t in tasks if t.get("status") == "in_progress"]
        done: List[Dict[str, Any]]    = [t for t in tasks if t.get("status") == "done"]
        blocked: List[str] = [
            str(l["work_done"]) for l in work_logs
            if l.get("blockers") and l.get("date", "") >= yesterday.isoformat()
        ]

        # Overall health
        total    = len(tasks)
        done_cnt = len(done)
        progress = round(((done_cnt / total * 100) if total else 0.0) * 10) / 10.0

        if progress >= 80:
            health = "excellent"
        elif progress >= 60:
            health = "on_track"
        elif progress >= 40:
            health = "at_risk"
        else:
            health = "behind"

        prompt = f"""You are an AI scrum master generating a daily standup report.

PROJECT: {project_title}
DEADLINE: {deadline or 'Not set'}
DAYS REMAINING: {days_remaining or 'Unknown'}
OVERALL PROGRESS: {progress}%

COMPLETED TASKS ({done_cnt} total):
{chr(10).join(f"- {t['name']} (by {t['assignee']})" for t in done[-5:]) or 'None yet'}  # type: ignore

IN PROGRESS ({len(in_prog)} tasks):
{chr(10).join(f"- {t['name']} ({t['progress']}%) — {t['assignee']}" for t in in_prog) or 'None'}

YESTERDAY WORK LOGS:
{chr(10).join(f"- {l['member_name']}: {l['work_done']}" for l in yesterday_logs) or 'No logs from yesterday'}

CURRENT BLOCKERS:
{chr(10).join(f"- {b}" for b in blocked) or 'No blockers reported'}

Generate a professional daily standup report.
Respond ONLY with valid JSON (no markdown):
{{
  "summary": "2-sentence project health summary",
  "completed_yesterday": ["task or activity 1", "task 2"],
  "in_progress_today":   ["what is being worked on today 1", "2"],
  "blockers":            ["blocker 1 if any"],
  "achievements":        ["notable achievement 1 if any"],
  "health_status":       "excellent|on_track|at_risk|behind",
  "health_score":        0-100,
  "ai_advice":           "2-3 sentences of specific advice for today"
}}"""

        try:
            raw    = self._call_ai(prompt)
            raw    = raw.replace("```json", "").replace("```", "").strip()
            result = json.loads(raw)
            result["health_score"] = max(0, min(100, int(
                result.get("health_score", progress)
            )))
            return result
        except Exception as e:
            print(f"[AI Standup] Error: {e}")
            return {
                "summary":             f"Project is {progress}% complete.",
                "completed_yesterday": [t["name"] for t in done[-3:]],  # type: ignore
                "in_progress_today":   [t["name"] for t in in_prog[:3]],  # type: ignore
                "blockers":            blocked[:3],  # type: ignore
                "achievements":        [],
                "health_status":       health,
                "health_score":        int(progress),
                "ai_advice":           "Keep logging work daily for better insights.",
            }
