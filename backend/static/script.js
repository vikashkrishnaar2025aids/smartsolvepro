/* ═══════════════════════════════════════════════
   SMART SOLVE AI — Frontend Logic (script.js)
═══════════════════════════════════════════════ */
'use strict';

let allTasks          = [];
let currentProjId     = null;
let typeChartInst     = null;
let workloadChartInst = null;
let loaderTimer       = null;

// ── User Identity ─────────────────────────────
function getUser() {
  try { return JSON.parse(localStorage.getItem('user') || 'null'); }
  catch { return null; }
}
function getUserId()    { return getUser()?.id    || null; }
function getUserEmail() { return getUser()?.email || ''; }
function getUserName()  { return getUser()?.name  || ''; }

// ── Type colours ──────────────────────────────
const TYPE_COLORS = {
  development: { bg: '#00d4ff', border: '#000000', text: '#000000' },
  design:      { bg: '#ff44cc', border: '#000000', text: '#000000' },
  research:    { bg: '#ffaa00', border: '#000000', text: '#000000' },
  testing:     { bg: '#00ff9d', border: '#000000', text: '#000000' },
  planning:    { bg: '#b44dff', border: '#000000', text: '#000000' },
  deployment:  { bg: '#ff8c42', border: '#000000', text: '#000000' },
  other:       { bg: '#aac4ff', border: '#000000', text: '#000000' },
};

// ── Init ──────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  restoreDraft();
  await initTeam();
  checkAIMode();
  loadHistory();

  const ta = document.getElementById('problem');
  if (ta) {
    ta.addEventListener('input', () => {
      const n = Math.min(ta.value.length, 1000);
      const cc = document.getElementById('char-count');
      if (cc) cc.textContent = `${n} / 1000`;
      if (ta.value.length > 1000) ta.value = ta.value.slice(0, 1000);
      saveDraft();
    });
  }
  const dl = document.getElementById('deadline');
  if (dl) dl.addEventListener('input', saveDraft);
});

async function initTeam() {
  try {
    const list = document.getElementById('team-list');
    if (!list) return;
    if (list.children.length > 0) return;
    const r = await fetch('/api/team');
    const d = await r.json();
    if (d.team && d.team.length > 0) {
      d.team.forEach(m => addMember(m.name, m.skills));
    } else {
      addMember();
    }
  } catch { addMember(); }
}

async function checkAIMode() {
  try {
    const r = await fetch('/api/health');
    const d = await r.json();
    const modeMap = {
      'groq-ai':       ['mode-openai', 'Groq (Llama 3)'],
      'gemini-ai':     ['mode-rules',  'Google Gemini'],
      'openrouter-ai': ['mode-claude', 'OpenRouter AI'],
      'rule-based':    ['mode-rules',  'Rule-Based Engine'],
    };
    const [cls, label] = modeMap[d.ai_mode] || ['mode-rules', 'AI Active'];
    const badge = document.getElementById('ai-mode-badge');
    if (badge) { badge.className = `ai-mode-badge ${cls}`; badge.textContent = label; }
    const sb = document.getElementById('sidebar-ai-badge');
    if (sb)    { sb.className = `ai-mode-badge ${cls}`;
                 sb.textContent = d.ai_mode === 'rule-based' ? 'AI Offline' : 'AI Online'; }
  } catch {}
}

// ── Team rows ────────────────────────────────
function addMember(name = '', skills = '') {
  const list = document.getElementById('team-list');
  const row  = document.createElement('div');
  row.className = 'team-row';
  row.innerHTML = `
    <input type="text" class="field-input member-name"
           placeholder="Name" value="${name}" style="flex:0.7"
           oninput="saveDraft()">
    <input type="text" class="field-input member-skills"
           placeholder="Skills e.g. React, Python, UI/UX" value="${skills}"
           oninput="saveDraft()">
    <button class="btn-icon-sm" onclick="removeMember(this)" title="Remove">×</button>`;
  list.appendChild(row);
  saveDraft();
}
function removeMember(btn) {
  if (document.querySelectorAll('.team-row').length > 1) {
    btn.closest('.team-row').remove();
    saveDraft();
  }
}
function getTeam() {
  return [...document.querySelectorAll('.team-row')]
    .map(r => ({
      name:   r.querySelector('.member-name').value.trim(),
      skills: r.querySelector('.member-skills').value.trim(),
    }))
    .filter(m => m.name);
}

// ── Draft auto-save ──────────────────────────
function saveDraft() {
  if (new URLSearchParams(window.location.search).get('pid')) return;
  localStorage.setItem('smart_solve_draft', JSON.stringify({
    problem:  document.getElementById('problem')?.value  || '',
    deadline: document.getElementById('deadline')?.value || '',
    team: [...document.querySelectorAll('.team-row')].map(r => ({
      name:   r.querySelector('.member-name').value,
      skills: r.querySelector('.member-skills').value,
    })),
  }));
}
function restoreDraft() {
  if (new URLSearchParams(window.location.search).get('pid')) return;
  const raw = localStorage.getItem('smart_solve_draft');
  if (!raw) return;
  try {
    const draft  = JSON.parse(raw);
    const probEl = document.getElementById('problem');
    const deadEl = document.getElementById('deadline');
    const teamEl = document.getElementById('team-list');
    if (probEl) {
      probEl.value = draft.problem || '';
      const cc = document.getElementById('char-count');
      if (cc) cc.textContent = `${probEl.value.length} / 1000`;
    }
    if (deadEl) deadEl.value = draft.deadline || '';
    if (teamEl && draft.team?.length) {
      teamEl.innerHTML = '';
      draft.team.forEach(m => addMember(m.name, m.skills));
    }
  } catch {}
}
function clearDraft() { localStorage.removeItem('smart_solve_draft'); }

// ── History drawer ───────────────────────────
function toggleHistory() {
  const drawer = document.getElementById('history-drawer');
  drawer.classList.remove('hidden');
  requestAnimationFrame(() => drawer.classList.toggle('open'));
}

async function loadHistory() {
  try {
    const uid = getUserId();
    const url = uid ? `/api/history?user_id=${uid}` : '/api/history';
    const r   = await fetch(url);
    const d   = await r.json();
    renderHistory(d.history || []);
  } catch {}
}

// ── renderHistory now has TRACK button ──
function renderHistory(items) {
  const list = document.getElementById('history-list');
  if (!list) return;
  if (!items.length) {
    list.innerHTML = '<p class="empty-msg">No projects yet. Generate your first plan!</p>';
    return;
  }
  list.innerHTML = items.map(p => `
    <div class="history-item">
      <div style="display:flex;justify-content:space-between;align-items:start">
        <div class="history-item-title">${p.title}</div>
        <button class="history-item-del"
                onclick="deleteProject('${p.id}',event)">✕</button>
      </div>
      <div class="history-item-meta">
        <span>${p.task_count} tasks · ${p.team_size} members</span>
        <span>${p.created_at}</span>
      </div>
      <div style="font-size:11px;color:rgba(150,190,255,0.4);
                  margin-top:5px;font-style:italic">${p.problem}</div>

      <!-- Progress bar -->
      <div style="margin-top:8px;height:4px;background:rgba(255,255,255,0.08);border-radius:2px">
        <div style="height:100%;background:#00d4ff;border-radius:2px;
                    width:${Math.round(p.progress || 0)}%;transition:width 0.4s"></div>
      </div>
      <div style="font-size:10px;color:rgba(0,212,255,0.6);
                  font-family:'Space Mono',monospace;margin-top:3px">
        ${Math.round(p.progress || 0)}% complete
      </div>

      <!-- Action buttons -->
      <div style="display:flex;gap:6px;margin-top:10px">
        <button onclick="loadProject('${p.id}')"
          style="flex:1;background:rgba(0,212,255,0.07);
                 border:1px solid rgba(0,212,255,0.2);
                 color:rgba(0,212,255,0.8);padding:7px 4px;
                 border-radius:4px;cursor:pointer;font-size:10px;
                 font-family:'Space Mono',monospace;letter-spacing:1px;
                 transition:all 0.2s">
          LOAD →
        </button>
        <button onclick="window.open('/tracker/${p.id}','_blank')"
          style="flex:1;background:rgba(0,255,148,0.07);
                 border:1px solid rgba(0,255,148,0.2);
                 color:rgba(0,255,148,0.8);padding:7px 4px;
                 border-radius:4px;cursor:pointer;font-size:10px;
                 font-family:'Space Mono',monospace;letter-spacing:1px;
                 transition:all 0.2s">
          📊 TRACK
        </button>
        <button onclick="window.open('/warroom/${p.id}','_blank')"
          style="flex:1;background:rgba(255,230,0,0.07);
                 border:1px solid rgba(255,230,0,0.2);
                 color:rgba(255,230,0,0.8);padding:7px 4px;
                 border-radius:4px;cursor:pointer;font-size:10px;
                 font-family:'Space Mono',monospace;letter-spacing:1px">
          ⚡ WAR ROOM
        </button>
      </div>
    </div>`).join('');
}

async function loadProject(pid) {
  try {
    const r = await fetch(`/api/history/${pid}`);
    const d = await r.json();
    if (d.plan) { renderOutput(d.plan); toggleHistory(); }
  } catch (e) { showError(e.message); }
}

async function deleteProject(pid, e) {
  e.stopPropagation();
  if (!confirm('Delete this project?')) return;
  await fetch(`/api/history/${pid}`, { method: 'DELETE' });
  loadHistory();
}

// ── Loader ───────────────────────────────────
const LOAD_STEPS = [
  ['PARSING INPUT',       'Extracting key concepts...',       8],
  ['NLP ANALYSIS',        'Classifying project domain...',   18],
  ['TASK GENERATION',     'Breaking into subtasks...',       35],
  ['SKILL MATCHING',      'Assigning team members...',       52],
  ['TIMELINE ESTIMATION', 'Calculating durations...',        68],
  ['WORKLOAD BALANCING',  'Optimising distribution...',      82],
  ['GANTT BUILDING',      'Scheduling parallel tasks...',    92],
  ['FINALISING',          'Preparing your plan...',          97],
];
function startLoader() {
  document.getElementById('loading-panel').classList.remove('hidden');
  let step = 0;
  function tick() {
    if (step >= LOAD_STEPS.length) return;
    const [title, sub, pct] = LOAD_STEPS[step++];
    document.getElementById('loader-step').textContent = title;
    document.getElementById('loader-sub').textContent  = sub;
    document.getElementById('loader-bar').style.width  = pct + '%';
    loaderTimer = setTimeout(tick, 1300 + Math.random() * 400);
  }
  tick();
}
function stopLoader() {
  clearTimeout(loaderTimer);
  document.getElementById('loader-bar').style.width = '100%';
  setTimeout(() => document.getElementById('loading-panel').classList.add('hidden'), 400);
}

// ── Generate ─────────────────────────────────
async function generatePlan() {
  const problem = document.getElementById('problem').value.trim();
  if (!problem) { showError('Please enter a problem statement.'); return; }

  const team     = getTeam();
  const deadline = document.getElementById('deadline').value.trim();
  const btn      = document.getElementById('gen-btn');

  hideError();
  btn.disabled = true;
  document.getElementById('output-section').classList.add('hidden');
  startLoader();

  try {
    const res = await fetch('/api/generate', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        problem,
        team,
        deadline,
        user_id:    getUserId(),
        user_email: getUserEmail(),
        user_name:  getUserName(),
      }),
    });
    const data = await res.json();
    if (!res.ok || data.error) throw new Error(data.error || 'Server error');

    renderOutput(data.plan);
    loadHistory();
    clearDraft();

    const url = new URL(window.location);
    url.searchParams.delete('pid');
    window.history.pushState({}, '', url);

  } catch (err) {
    showError('Error: ' + err.message);
  } finally {
    stopLoader();
    btn.disabled = false;
  }
}

// ── Analyze ──────────────────────────────────
async function analyzeProblem() {
  const problem = document.getElementById('problem').value.trim();
  if (!problem) { showError('Enter a problem statement first.'); return; }

  const btn       = document.getElementById('btn-analyze');
  const container = document.getElementById('analyze-results');
  btn.disabled = true;
  btn.innerHTML = `⏳ Analyzing...`;

  try {
    const res  = await fetch('/api/analyze-problem', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ problem }),
    });
    const data = await res.json();
    if (!res.ok || data.error) throw new Error(data.error);

    const analysis = data.analysis;
    let html = `<strong>💡 AI Ideas & Insights</strong>
      <ul style="margin-top:8px;padding-left:20px">`;
    (analysis.ideas || []).forEach(idea => {
      html += `<li style="margin-bottom:4px;color:#aac4ff">${idea}</li>`;
    });
    html += `</ul>`;
    if (analysis.similar_project) {
      const sp = analysis.similar_project;
      html += `<div style="margin-top:10px;padding:8px;
                background:rgba(0,212,255,0.1);
                border-left:3px solid #00d4ff">
        <strong>🔍 Similar Past Project:</strong><br>
        <span style="color:#7de8ff">${sp.title}</span>
        <span style="font-size:0.8em;color:rgba(125,232,255,0.6)"> — ${sp.date}</span>
      </div>`;
    }
    container.innerHTML = html;
    container.style.display = 'block';
  } catch (err) {
    showError('Error: ' + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `🔍 Analyze & Get Ideas`;
  }
}

// ── Render Output ────────────────────────────
function renderOutput(plan) {
  allTasks      = plan.tasks || [];
  currentProjId = plan.project_id || plan.id || null;

  document.getElementById('proj-title').textContent    = plan.projectTitle || 'Project Plan';
  document.getElementById('proj-summary').textContent  = plan.summary      || '';
  
  const probEl = document.getElementById('problem');
  if (probEl && plan.problem) {
    probEl.value = plan.problem;
    const cc = document.getElementById('char-count');
    if (cc) cc.textContent = `${probEl.value.length} / 1000`;
  }

  document.getElementById('proj-id-badge').textContent = currentProjId ? `ID: ${currentProjId}` : '';
  const statusBadge = document.getElementById('proj-status-badge');
  if (statusBadge) statusBadge.style.display = 'inline-block';
  document.getElementById('proj-time').textContent     = new Date().toLocaleString();

  const totalDays = plan.totalDays ||
    allTasks.reduce((mx, t) => Math.max(mx,(t.startDay||1)+(t.durationDays||1)-1), 0);

  document.getElementById('stats-row').innerHTML = [
    [allTasks.length,                         'Total Tasks'],
    [allTasks.filter(t=>t.priority==='high').length, 'High Priority'],
    [new Set(allTasks.map(t=>t.type)).size,   'Task Types'],
    [totalDays,                                'Est. Days'],
    [[...new Set(allTasks.map(t=>t.assignee).filter(Boolean))].length || '—', 'Members'],
  ].map(([v,l],i) =>
    `<div class="stat-card" style="animation-delay:${i*0.07}s">
       <div class="stat-val">${v}</div>
       <div class="stat-label">${l}</div>
     </div>`
  ).join('');

  renderCharts(plan);
  renderGantt(plan);
  renderTasks(allTasks, 'all');
  buildFilters();

  // Add TRACK button to output header
  const badge = document.getElementById('proj-id-badge');
  if (badge && currentProjId) {
    badge.innerHTML = `ID: ${currentProjId}
      <button onclick="window.open('/tracker/${currentProjId}','_blank')"
        style="margin-left:10px;background:rgba(0,255,148,0.12);
               border:1px solid rgba(0,255,148,0.3);color:#00ff9d;
               padding:3px 10px;border-radius:4px;cursor:pointer;
               font-family:'Space Mono',monospace;font-size:9px;
               letter-spacing:1px;transition:all 0.2s">
        📊 TRACK PROGRESS
      </button>`;
  }

  const out = document.getElementById('output-section');
  out.classList.remove('hidden');
  setTimeout(() => out.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
}

// ── Charts ───────────────────────────────────
function renderCharts(plan) {
  const typeCounts = {};
  plan.tasks.forEach(t => {
    const k = t.type || 'other';
    typeCounts[k] = (typeCounts[k] || 0) + 1;
  });
  const tLabels = Object.keys(typeCounts);
  const tVals   = Object.values(typeCounts);
  const tBGs    = tLabels.map(l => (TYPE_COLORS[l] || TYPE_COLORS.other).bg);
  const tBorders= tLabels.map(l => (TYPE_COLORS[l] || TYPE_COLORS.other).border);

  if (typeChartInst) typeChartInst.destroy();
  typeChartInst = new Chart(document.getElementById('typeChart'), {
    type: 'doughnut',
    data: { labels: tLabels,
            datasets: [{ data: tVals, backgroundColor: tBGs,
                         borderColor: tBorders, borderWidth: 2 }] },
    options: { responsive: true, maintainAspectRatio: false,
               cutout: '68%', plugins: { legend: { display: false } } },
  });

  const legend = document.getElementById('type-legend');
  if (legend) {
    legend.innerHTML = tLabels.map((l, i) => `
      <div class="legend-item">
        <div class="legend-dot" style="background:${tBGs[i]}"></div>
        ${l} (${tVals[i]})
      </div>`).join('');
  }

  const mWork = {};
  plan.tasks.forEach(t => {
    const a = t.assignee || 'Team';
    mWork[a] = (mWork[a] || 0) + (t.durationDays || 1);
  });
  const mLabels   = Object.keys(mWork);
  const mVals     = Object.values(mWork);
  const barColors = ['#00d4ff','#b44dff','#00ff9d','#ff44cc','#ffaa00','#ff8c42'];

  if (workloadChartInst) workloadChartInst.destroy();
  workloadChartInst = new Chart(document.getElementById('workloadChart'), {
    type: 'bar',
    data: { labels: mLabels, datasets: [{
      label: 'Days allocated', data: mVals,
      backgroundColor: mLabels.map((_,i) => barColors[i%barColors.length]+'28'),
      borderColor:     mLabels.map((_,i) => barColors[i%barColors.length]),
      borderWidth: 2, borderRadius: 6,
    }]},
    options: {
      responsive: true, maintainAspectRatio: false, indexAxis: 'y',
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color:'rgba(180,210,255,0.5)', font:{size:10} },
             grid:  { color:'rgba(0,212,255,0.05)' } },
        y: { ticks: { color:'rgba(180,210,255,0.6)', font:{size:11} },
             grid:  { display: false } },
      },
    },
  });
}

// ── Gantt ────────────────────────────────────
function renderGantt(plan) {
  const tasks  = plan.tasks;
  const maxDay = tasks.reduce((mx,t) =>
    Math.max(mx,(t.startDay||1)+(t.durationDays||1)-1), 0);
  const cols   = Math.max(maxDay, 10);

  const note = document.getElementById('gantt-note');
  if (note) note.textContent = `${cols} day${cols>1?'s':''} total`;

  let dayHeaders = '';
  for (let d = 1; d <= cols; d++) {
    dayHeaders += `<th style="text-align:center;padding:4px 0;font-size:10px">${d<=30?d:''}</th>`;
  }

  const rows = tasks.map(t => {
    const col   = TYPE_COLORS[t.type] || TYPE_COLORS.other;
    const start = t.startDay    || 1;
    const dur   = t.durationDays || 1;
    let cells   = '';
    if (start > 1) cells += `<td colspan="${start-1}"></td>`;
    cells += `<td colspan="${Math.min(dur, cols-start+1)}">
      <div class="g-bar" style="background:${col.bg};color:${col.text}"
           title="${t.name} · ${dur}d">${dur}d</div></td>`;
    const rem = cols - (start-1) - dur;
    if (rem > 0) cells += `<td colspan="${rem}"></td>`;
    return `<tr>
      <td class="g-name" title="${t.name}">${t.name}</td>
      <td class="g-who">${t.assignee||'—'}</td>
      ${cells}</tr>`;
  }).join('');

  document.getElementById('gantt-wrap').innerHTML = `
    <table class="gantt">
      <thead><tr>
        <th style="min-width:140px;text-align:left">Task</th>
        <th style="min-width:70px;text-align:left">Assigned</th>
        ${dayHeaders}
      </tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

// ── Task Board ───────────────────────────────
function buildFilters() {
  const types   = [...new Set(allTasks.map(t => t.type))];
  const filters = [
    ['all',  'All'],
    ['high', '🔴 High'],
    ...types.map(t => [t, t.charAt(0).toUpperCase()+t.slice(1)]),
  ];
  const bar = document.getElementById('filter-bar');
  if (bar) {
    bar.innerHTML = filters.map(([key, label], i) =>
      `<button class="filter-btn${i===0?' active':''}"
               onclick="filterTasks('${key}',this)">${label}</button>`
    ).join('');
  }
}

function filterTasks(key, btn) {
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const filtered = key === 'all'  ? allTasks :
                   key === 'high' ? allTasks.filter(t => t.priority === 'high') :
                                    allTasks.filter(t => t.type === key);
  renderTasks(filtered, key);
}

function renderTasks(tasks) {
  const container = document.getElementById('task-list');
  if (!tasks.length) {
    container.innerHTML =
      '<p style="text-align:center;color:rgba(150,190,255,0.4);padding:30px;font-size:13px">No tasks match this filter.</p>';
    return;
  }
  container.innerHTML = tasks.map((t, i) => `
    <div class="task-card ${t.priority}" style="animation-delay:${i*0.05}s" data-id="${t.id}">
      <div>
        <div class="task-title" contenteditable="true" spellcheck="false"
             onblur="saveTaskEdit(${t.id},this)">${t.name}</div>
        <div class="task-desc">${t.description||''}</div>
        ${t.subtasks?.length ? `
          <div class="subtask-list">
            ${t.subtasks.map(s=>`
              <div class="subtask-item">
                <span class="subtask-check">○</span>
                <span class="subtask-text">${s}</span>
              </div>`).join('')}
          </div>` : ''}
        <div class="task-tags">
          <span class="tag tag-${t.type||'other'}">${t.type||'task'}</span>
          <span class="priority-badge pb-${t.priority}">${t.priority}</span>
          <span style="font-size:10px;color:rgba(150,190,255,0.4);
                       font-family:'Space Mono',monospace">Day ${t.startDay||1}</span>
          ${t.dependencies?.length
            ? `<span style="font-size:10px;color:rgba(150,190,255,0.4)">
                 Requires: ${t.dependencies.join(', ')}</span>` : ''}
        </div>
      </div>
      <div class="task-right">
        <div class="task-assignee">${t.assignee||'Unassigned'}</div>
        <div class="task-duration">${t.durationDays||1}d</div>
      </div>
    </div>`).join('');
}

async function saveTaskEdit(taskId, el) {
  const newName = el.textContent.trim();
  if (!newName || !currentProjId) return;
  const task = allTasks.find(t => t.id === taskId);
  if (task) task.name = newName;
  try {
    await fetch('/api/update-task', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_id: currentProjId, task_id: taskId,
        updates: { name: newName },
      }),
    });
  } catch {}
}

// ── Utilities ─────────────────────────────────
function showError(msg) {
  const box = document.getElementById('error-box');
  if (box) { box.textContent = msg; box.classList.remove('hidden'); }
}
function hideError() {
  const box = document.getElementById('error-box');
  if (box) box.classList.add('hidden');
}
