/* ═══════════════════════════════════════
   SMART SOLVE AI — Tracker Logic
═══════════════════════════════════════ */
'use strict';

let selectedTaskId = null;
let selectedTaskName = "";
let memberChart = null;
let dailyChart = null;
let statusChart = null;

// ── Init ─────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    // Set default date to today
    const today = new Date().toISOString().split('T')[0];
    const dateInput = document.getElementById('log-date');
    if(dateInput) dateInput.value = today;

    refreshDashboard();
    loadActivityFeed();
});

// ── Refresh Dashboard Stats ──────────────────────
async function refreshDashboard() {
    try {
        const r = await fetch(`/api/project_stats/${PROJECT_ID}`);
        const d = await r.json();
        if (d.error) return;

        // UI Updates
        updateProgressRing(d.overall_progress);
        document.getElementById('overall-progress-nav').textContent = `${d.overall_progress}% Complete`;
        document.getElementById('project-status-tag').textContent = d.status.toUpperCase();
        
        document.getElementById('stat-todo').textContent = d.status_counts.todo;
        document.getElementById('stat-inprog').textContent = d.status_counts.in_progress;
        document.getElementById('stat-done').textContent = d.status_counts.done;
        document.getElementById('stat-logs').textContent = d.total_logs;

        const totalHours = Object.values(d.member_hours).reduce((a,b) => a+b, 0);
        document.getElementById('stat-hours').textContent = totalHours.toFixed(1);

        renderCharts(d);
    } catch (err) { console.error("Stats fail:", err); }
}

function updateProgressRing(pct) {
    const ring = document.getElementById('ring-fill');
    const text = document.getElementById('ring-text');
    const offset = 314 - (314 * pct / 100);
    ring.style.strokeDashoffset = offset;
    text.textContent = `${Math.round(pct)}%`;
}

// ── Task Management ──────────────────────────────
function filterTasks(status, btn) {
    // Tabs
    document.querySelectorAll('.ftab').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');

    // Filter list
    const tasks = document.querySelectorAll('.task-item');
    tasks.forEach(t => {
        if (status === 'all' || t.dataset.status === status) {
            t.style.display = 'block';
        } else {
            t.style.display = 'none';
        }
    });
}

function selectTask(el) {
    document.querySelectorAll('.task-item').forEach(t => t.classList.remove('selected'));
    el.classList.add('selected');

    selectedTaskId = el.dataset.taskId;
    selectedTaskName = el.querySelector('.task-item-name').textContent;

    // Show form
    document.getElementById('form-hint').style.display = 'none';
    document.getElementById('log-form').style.display = 'block';
    document.getElementById('selected-task-banner').textContent = `Task #${el.dataset.taskNum}: ${selectedTaskName}`;
}

async function quickStatus(e, taskId, status) {
    e.stopPropagation();
    try {
        const r = await fetch('/api/update_status', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_db_id: taskId, status: status })
        });
        const d = await r.json();
        if (d.success) {
            // Update UI list item without reload
            const taskItem = document.querySelector(`.task-item[data-task-id="${taskId}"]`);
            taskItem.dataset.status = status;
            taskItem.className = `task-item ${status}`;
            
            // Re-render UI progress if it was marked done
            if(status === 'done') {
                taskItem.querySelector('.task-progress-fill').style.width = '100%';
                taskItem.querySelector('.task-progress-pct').textContent = '100%';
            } else if(status === 'todo') {
                taskItem.querySelector('.task-progress-fill').style.width = '0%';
                taskItem.querySelector('.task-progress-pct').textContent = '0%';
            }

            refreshDashboard();
        }
    } catch (err) { console.error("Status update fail:", err); }
}

// ── Description Quality Indicator ─────────────────────────────────
function updateDescriptionQuality() {
  const text  = document.getElementById('work-done').value.trim();
  const bar   = document.getElementById('quality-bar');
  const label = document.getElementById('quality-label');
  const words = text.split(/\s+/).filter(w => w.length > 0).length;

  let pct, color, lbl;

  if (words >= 30)      { pct=100; color='#00FF94'; lbl='EXCELLENT'; }
  else if (words >= 20) { pct=80;  color='#00FF94'; lbl='GREAT';     }
  else if (words >= 12) { pct=60;  color='#FFE600'; lbl='GOOD';      }
  else if (words >= 6)  { pct=35;  color='#ff8c42'; lbl='FAIR';      }
  else if (words >= 2)  { pct=15;  color='#FF2D78'; lbl='POOR';      }
  else                  { pct=0;   color='#FF2D78'; lbl='EMPTY';     }

  bar.style.width      = pct + '%';
  bar.style.background = color;
  label.textContent    = lbl;
  label.style.color    = color;

  // Show AI preview when description is decent
  if (words >= 6) {
    previewAIEstimate();
  } else {
    document.getElementById('ai-preview-box').style.display = 'none';
  }
}

// ── AI Estimate Preview (rough rule-based preview) ────────────────
function previewAIEstimate() {
  const hours   = parseFloat(document.getElementById('hours-worked').value) || 0;
  const text    = document.getElementById('work-done').value.trim();
  const blocker = document.getElementById('blockers').value.trim();
  const words   = text.split(/\s+/).filter(w=>w.length>0).length;
  const box     = document.getElementById('ai-preview-box');

  if (!hours && words < 6) { box.style.display='none'; return; }
  box.style.display = 'block';

  // Rough estimate for preview only
  let base = 0;
  if (hours >= 8)      base = 30;
  else if (hours >= 6) base = 22;
  else if (hours >= 4) base = 16;
  else if (hours >= 2) base = 10;
  else if (hours >= 1) base = 6;
  else                 base = 3;

  // Quality bonus
  if (words >= 30)      base = Math.min(base * 1.4, 40);
  else if (words >= 20) base = Math.min(base * 1.2, 35);
  else if (words < 6)   base = Math.max(base * 0.5, 3);

  // Blocker penalty
  if (blocker) base = Math.floor(base * 0.7);

  const estimate = Math.round(base);
  document.getElementById('preview-pct').textContent = `~${estimate}%`;
  document.getElementById('preview-hint').textContent =
    words >= 20
      ? 'Good description! AI will give accurate progress.'
      : 'Add more detail for a higher and more accurate AI estimate.';
}

// ── Submit Work Log (AI calculates everything) ────────────────────
async function submitWorkLog() {
  if (!selectedTaskId) {
    alert('Please select a task first.'); return;
  }

  const memberName  = document.getElementById('member-select').value;
  const logDate     = document.getElementById('log-date').value;
  const hoursWorked = parseFloat(document.getElementById('hours-worked').value);
  const workDone    = document.getElementById('work-done').value.trim();
  const blockers    = document.getElementById('blockers').value.trim();

  // Validate
  if (!workDone) {
    showFormError('Please describe what was done today.'); return;
  }
  if (!hoursWorked || hoursWorked <= 0) {
    showFormError('Please enter valid hours worked.'); return;
  }
  if (workDone.split(/\s+/).length < 5) {
    showFormError(
      'Description too short. Be specific — AI needs details to calculate progress accurately.'
    ); return;
  }

  const btn = document.getElementById('btn-log-work');
  btn.disabled    = true;
  btn.textContent = '🤖 AI is calculating progress...';

  // Show thinking animation
  showAIThinking();

  try {
    const res = await fetch('/api/log_work', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_id:   PROJECT_ID,
        task_db_id:   parseInt(selectedTaskId),
        member_name:  memberName,
        date:         logDate,
        hours_worked: hoursWorked,
        work_done:    workDone,
        blockers:     blockers,
        // NOTE: No progress_pct sent — AI calculates it
      }),
    });

    const data = await res.json();
    if (!res.ok || data.error) throw new Error(data.error);

    // Show AI result
    hideAIThinking();
    showAIResult(data);

    // Update task card in list
    updateTaskProgressInList(
      selectedTaskId,
      data.task_progress,
      data.task_status
    );

    // Update project ring
    updateRingProgress(data.project_progress);

    // Refresh activity + stats
    loadActivityFeed();
    loadStats();

    // Clear form (but keep task selected)
    document.getElementById('work-done').value  = '';
    document.getElementById('blockers').value   = '';
    document.getElementById('hours-worked').value = '';
    document.getElementById('ai-preview-box').style.display = 'none';
    updateDescriptionQuality();

  } catch(err) {
    hideAIThinking();
    showFormError('Error: ' + err.message);
  } finally {
    btn.disabled    = false;
    btn.textContent = '🤖 SAVE & LET AI CALCULATE PROGRESS';
  }
}

// ── Show AI Thinking Animation ────────────────────────────────────
function showAIThinking() {
  const box = document.getElementById('ai-result-box');
  box.style.display = 'block';
  box.innerHTML = `
    <div style="padding:16px;background:rgba(255,230,0,0.04);
                border:1px solid rgba(255,230,0,0.2);
                text-align:center;margin-top:12px">
      <div style="font-size:24px;margin-bottom:8px;
                  animation:spin 1s linear infinite;
                  display:inline-block">🤖</div>
      <div style="font-family:'Space Mono',monospace;font-size:11px;
                  color:var(--y);letter-spacing:2px;
                  animation:blink 1.2s ease infinite">
        AI IS ANALYZING YOUR WORK...
      </div>
      <div style="font-size:11px;color:var(--muted);margin-top:6px">
        Reading description · Evaluating hours · Checking blockers
      </div>
    </div>`;
}
function hideAIThinking() {
  const box = document.getElementById('ai-result-box');
  box.style.display = 'none';
}

// ── Show AI Calculated Result ─────────────────────────────────────
function showAIResult(data) {
  const box   = document.getElementById('ai-result-box');
  const pct   = data.ai_progress;
  const delta = data.progress_change || 0;

  const statusConfig = {
    done:        { color:'#00FF94', label:'DONE ✅'        },
    in_progress: { color:'#FFE600', label:'IN PROGRESS'   },
    todo:        { color:'var(--muted)', label:'TODO'      },
  };
  const scfg = statusConfig[data.ai_status] || statusConfig.in_progress;

  box.style.display = 'block';
  box.innerHTML = `
    <div style="margin-top:12px;padding:18px;
                background:rgba(0,255,148,0.05);
                border:2px solid rgba(0,255,148,0.2)">

      <!-- Header -->
      <div style="display:flex;align-items:center;gap:10px;
                  margin-bottom:14px">
        <span style="font-size:20px">🤖</span>
        <div>
          <div style="font-family:'Space Mono',monospace;font-size:10px;
                      letter-spacing:2px;color:#00FF94">
            AI PROGRESS CALCULATED
          </div>
          <div style="font-size:11px;color:var(--muted);margin-top:2px">
            Work log saved successfully
          </div>
        </div>
      </div>

      <!-- Big progress number -->
      <div style="display:flex;align-items:center;
                  gap:20px;margin-bottom:14px;flex-wrap:wrap">
        <div style="text-align:center">
          <div style="font-family:'Orbitron',monospace;font-size:42px;
                      font-weight:900;color:#00FF94;line-height:1">
            ${pct}%
          </div>
          <div style="font-family:'Space Mono',monospace;font-size:9px;
                      color:var(--muted);letter-spacing:2px;margin-top:4px">
            TASK PROGRESS
          </div>
        </div>
        <div style="flex:1">
          <!-- Progress bar -->
          <div style="height:8px;background:rgba(255,255,255,0.08);
                      margin-bottom:8px">
            <div style="height:100%;background:#00FF94;
                        width:${pct}%;transition:width 0.8s ease"></div>
          </div>
          <!-- Change indicator -->
          <div style="font-family:'Space Mono',monospace;font-size:11px;
                      color:${delta > 0 ? '#00FF94' : 'var(--muted)'}">
            ${delta > 0 ? `↑ +${delta}% progress added` : 'No change in progress'}
          </div>
          <!-- Status -->
          <div style="font-family:'Space Mono',monospace;font-size:10px;
                      color:${scfg.color};margin-top:4px;letter-spacing:1px">
            Status: ${scfg.label}
          </div>
        </div>
      </div>

      <!-- AI Reasoning -->
      <div style="background:rgba(0,0,0,0.3);padding:10px 14px;
                  border-left:3px solid #00FF94;margin-bottom:10px">
        <div style="font-family:'Space Mono',monospace;font-size:9px;
                    letter-spacing:2px;color:rgba(0,255,148,0.6);
                    margin-bottom:4px">🧠 AI REASONING</div>
        <div style="font-size:12px;color:rgba(240,240,232,0.8);
                    line-height:1.5">${data.ai_reasoning}</div>
      </div>

      <!-- Confidence -->
      <div style="display:flex;align-items:center;gap:10px;
                  margin-bottom:10px">
        <div style="font-family:'Space Mono',monospace;font-size:9px;
                    color:var(--muted);letter-spacing:1px;white-space:nowrap">
          AI CONFIDENCE:
        </div>
        <div style="flex:1;height:4px;background:rgba(255,255,255,0.08)">
          <div style="height:100%;background:rgba(0,212,255,0.7);
                      width:${data.ai_confidence}%"></div>
        </div>
        <div style="font-family:'Space Mono',monospace;font-size:10px;
                    color:var(--b)">${data.ai_confidence}%</div>
      </div>

      <!-- Encouragement -->
      <div style="font-size:13px;color:var(--y);
                  text-align:center;padding:8px;
                  font-style:italic">
        "${data.ai_encouragement}"
      </div>

      <!-- Project progress -->
      <div style="margin-top:10px;padding:8px 12px;
                  background:rgba(0,0,0,0.3);
                  font-family:'Space Mono',monospace;
                  font-size:10px;color:var(--muted);
                  display:flex;justify-content:space-between">
        <span>Overall Project Progress</span>
        <span style="color:var(--y)">
          ${Math.round(data.project_progress)}%
        </span>
      </div>
    </div>`;
}

// ── Update Task Progress Bar in Task List ─────────────────────────
function updateTaskProgressInList(taskDbId, pct, status) {
  const taskEl = document.querySelector(`[data-task-id="${taskDbId}"]`);
  if (!taskEl) return;

  const fill  = taskEl.querySelector('.task-progress-fill');
  const label = taskEl.querySelector('.task-progress-pct');
  if (fill)  fill.style.width  = pct + '%';
  if (label) label.textContent = Math.round(pct) + '%';

  taskEl.className = `task-item ${status}`;
  if (taskEl.classList.contains('selected'))
    taskEl.classList.add('selected');
}

// ── Show Form Error ───────────────────────────────────────────────
function showFormError(msg) {
  const box = document.getElementById('ai-result-box');
  box.style.display = 'block';
  box.innerHTML = `
    <div style="margin-top:10px;padding:12px 14px;
                background:rgba(255,45,120,0.08);
                border:1px solid rgba(255,45,120,0.3);
                color:#FF2D78;font-size:12px;
                font-family:'Space Mono',monospace">
      ⚠ ${msg}
    </div>`;
}

// Add spin animation for AI thinking
const style = document.createElement('style');
style.textContent = `
  @keyframes spin {
    from { transform: rotate(0deg); }
    to   { transform: rotate(360deg); }
  }
`;
document.head.appendChild(style);

// ── Activity Feed ────────────────────────────────
async function loadActivityFeed() {
    const filter = document.getElementById('activity-filter').value;
    const feedBody = document.getElementById('activity-feed');
    
    try {
        let url = `/api/work_logs/${PROJECT_ID}`;
        if (filter !== 'all') {
            url = `/api/member_logs/${PROJECT_ID}/${filter}`;
        }

        const r = await fetch(url);
        const d = await r.json();

        let logs = [];
        if (filter === 'all') {
             // Response is grouped by date
             Object.values(d.grouped_by_date || {}).forEach(dayLogs => {
                 logs = logs.concat(dayLogs);
             });
        } else {
            logs = d.logs || [];
        }

        if (!logs.length) {
            feedBody.innerHTML = '<div class="activity-empty">No activity found.</div>';
            return;
        }

        feedBody.innerHTML = logs.map(log => `
            <div class="activity-item anim-fade-in">
                <div class="activity-header">
                    <span class="activity-member">${log.member_name}</span>
                    <span class="activity-date">${new Date(log.date).toLocaleDateString()}</span>
                </div>
                <div class="activity-work">${log.work_done}</div>
                ${log.ai_analysis ? `
                <div class="activity-ai-analysis" style="margin-top:8px; padding:8px 12px; background:rgba(0,212,255,0.05); border-left:2px solid var(--b); font-size:11px;">
                    <div style="font-family:'Space Mono',monospace; font-size:9px; color:var(--b); margin-bottom:4px;">🤖 AI ANALYSIS</div>
                    <div style="color:var(--y); font-style:italic; margin-bottom:4px;">"${log.ai_analysis.reasoning}"</div>
                    ${log.ai_analysis.errors && log.ai_analysis.errors.length ? `<div style="color:#FF2D78;">• ${log.ai_analysis.errors[0]}</div>` : ''}
                </div>
                ` : ''}
                <div class="activity-meta">
                    <span>⏱ ${log.hours_worked}h</span>
                    <span>📈 ${log.progress_pct}% Task completion</span>
                </div>
                ${log.blockers ? `<div class="activity-blocker">⚠️ Blockers: ${log.blockers}</div>` : ''}
            </div>
        `).join('');

    } catch (err) { console.error("Activity load fail:", err); }
}

// ── Charts ───────────────────────────────────────
function renderCharts(data) {
    const ctxMember = document.getElementById('memberChart').getContext('2d');
    const ctxDaily  = document.getElementById('dailyChart').getContext('2d');
    const ctxStatus = document.getElementById('statusChart').getContext('2d');

    // 1. Member Hours
    if (memberChart) memberChart.destroy();
    memberChart = new Chart(ctxMember, {
        type: 'bar',
        data: {
            labels: Object.keys(data.member_hours),
            datasets: [{
                label: 'Hours',
                data: Object.values(data.member_hours),
                backgroundColor: '#FFE600',
                borderWidth: 0,
                borderRadius: 4
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { ticks: { color: '#888' }, grid: { color: '#222' } },
                y: { ticks: { color: '#FFF' }, grid: { display: false } }
            }
        }
    });

    // 2. Daily Hours
    const last7Days = [...Array(7)].map((_, i) => {
        const d = new Date();
        d.setDate(d.getDate() - i);
        return d.toISOString().split('T')[0];
    }).reverse();

    const dailyData = last7Days.map(day => data.daily_hours[day] || 0);

    if (dailyChart) dailyChart.destroy();
    dailyChart = new Chart(ctxDaily, {
        type: 'line',
        data: {
            labels: last7Days.map(d => d.split('-').slice(1).join('/')),
            datasets: [{
                label: 'Hours',
                data: dailyData,
                borderColor: '#00FF94',
                backgroundColor: 'rgba(0,255,148,0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { ticks: { color: '#888' }, grid: { display: false } },
                y: { ticks: { color: '#888' }, grid: { color: '#222' } }
            }
        }
    });

    // 3. Status Doughnut
    if (statusChart) statusChart.destroy();
    statusChart = new Chart(ctxStatus, {
        type: 'doughnut',
        data: {
            labels: ['Todo', 'Active', 'Done'],
            datasets: [{
                data: [data.status_counts.todo, data.status_counts.in_progress, data.status_counts.done],
                backgroundColor: ['#333', '#FFE600', '#00FF94'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '70%',
            plugins: { legend: { position: 'bottom', labels: { color: '#888', boxWidth: 10 } } }
        }
    });
}


// ── Proof Modal ───────────────────────────────────────────────────
let selectedProofFile = null;

function openProofModal(taskDbId, taskName) {
  const taskIdEl = document.getElementById('proof-task-id');
  const taskNameEl = document.getElementById('proof-task-name');
  if(!taskIdEl || !taskNameEl) return;

  taskIdEl.value  = taskDbId;
  taskNameEl.textContent = taskName;
  document.getElementById('proof-note').value     = '';
  document.getElementById('proof-url').value      = '';
  document.getElementById('proof-status').style.display = 'none';
  const preview = document.getElementById('file-preview');
  if(preview) preview.style.display = 'none';
  const dropText = document.getElementById('file-drop-text');
  if(dropText) dropText.textContent = 'Click or drag file here';
  selectedProofFile = null;

  document.getElementById('proof-overlay').classList.add('open');
}

function closeProofModal() {
  document.getElementById('proof-overlay').classList.remove('open');
}

// Close modal when clicking outside
document.addEventListener('click', function(e) {
  const overlay = document.getElementById('proof-overlay');
  if (e.target === overlay) closeProofModal();
});

function handleFileSelect(input) {
  if (input.files && input.files[0]) {
    selectedProofFile = input.files[0];
    showFilePreview(selectedProofFile);
  }
}

function handleFileDrop(event) {
  event.preventDefault();
  const zone = document.getElementById('file-drop-zone');
  if(zone) zone.classList.remove('drag-over');
  const file = event.dataTransfer.files[0];
  if (file) {
    selectedProofFile = file;
    showFilePreview(file);
  }
}

function showFilePreview(file) {
  const sizeKB = (file.size / 1024).toFixed(1);
  const dropText = document.getElementById('file-drop-text');
  if(dropText) dropText.textContent = `✅ ${file.name}`;
  const preview = document.getElementById('file-preview');
  if(preview) {
    preview.textContent = `📎 ${file.name} (${sizeKB} KB)`;
    preview.style.display = 'block';
  }
}

// ── Submit Completion ─────────────────────────────────────────────
async function submitCompletion() {
  const taskDbId  = document.getElementById('proof-task-id').value;
  const member    = document.getElementById('proof-member').value;
  const note      = document.getElementById('proof-note').value.trim();
  const url       = document.getElementById('proof-url').value.trim();
  const statusEl  = document.getElementById('proof-status');
  const submitBtn = document.getElementById('proof-submit-btn');

  // Validate
  if (!note) {
    showProofStatus('error', '⚠ Please describe what was completed');
    return;
  }
  if (!selectedProofFile && !url) {
    showProofStatus('error', '⚠ Please upload a proof file OR provide a link');
    return;
  }

  submitBtn.disabled = true;
  submitBtn.textContent = '📨 Submitting...';

  try {
    // Use FormData because we're sending a file
    const formData = new FormData();
    formData.append('task_db_id',      taskDbId);
    formData.append('member_name',     member);
    formData.append('completion_note', note);
    formData.append('completion_url',  url);
    if (selectedProofFile) {
      formData.append('proof_file', selectedProofFile);
    }

    const res  = await fetch('/api/submit_completion', {
      method: 'POST',
      body:   formData,
    });
    const data = await res.json();

    if (!res.ok || data.error) throw new Error(data.error);

    // Success — update task UI immediately
    showProofStatus('success',
      '✅ Submitted! Waiting for admin approval before marking as Done.'
    );

    // ── New: Show AI Analysis in Modal ──
    if (data.ai_review) {
      showAIReviewInModal(data.ai_review);
    }

    // Update task card in the list with AI analysis
    updateTaskCardStatus(parseInt(taskDbId), 'pending_review', 'pending', data.ai_review);

    // Close modal after 2.5 seconds
    setTimeout(() => {
      closeProofModal();
      refreshDashboard(); // existing name for reloading stats
    }, 2500);

  } catch (err) {
    showProofStatus('error', '❌ Error: ' + err.message);
  } finally {
    submitBtn.disabled   = false;
    submitBtn.textContent = '📨 Submit for Admin Review';
  }
}

function showProofStatus(type, msg) {
  const el = document.getElementById('proof-status');
  if(!el) return;
  el.textContent   = msg;
  el.className     = `proof-status ${type}`;
  el.style.display = 'block';
}

// ── Update task card UI without page reload ───────────────────────
function updateTaskCardStatus(taskDbId, status, approvalStatus, aiReview = null) {
  const taskEl = document.querySelector(`[data-task-id="${taskDbId}"]`);
  if (!taskEl) return;

  taskEl.dataset.status = status;
  taskEl.className = `task-item ${status}`; // Updates appearance

  // Replace action buttons
  const actionRow = taskEl.querySelector('.task-action-row');
  if (actionRow) {
    if (approvalStatus === 'pending') {
      actionRow.innerHTML = `
        <button class="sbtn sbtn-active"
             onclick="quickStatus(event,'${taskDbId}','in_progress')">
          ▶ Set Active
        </button>
        <div class="sbtn sbtn-pending">⏳ Pending Review</div>`;
    } else if (status === 'done') {
      actionRow.innerHTML = `<div class="sbtn sbtn-done">✅ Approved Done</div>`;
    }
  }

  // Update AI Analysis box
  const aiBox = document.getElementById(`ai-review-${taskDbId}`);
  if (aiBox && aiReview) {
      aiBox.classList.remove('task-ai-analysis-hidden');
      aiBox.classList.add('task-ai-analysis-visible');
      const content = aiBox.querySelector('.ai-review-content');
      content.innerHTML = renderAIFeedbackSmall(aiReview);
  }
}

function showAIReviewInModal(review) {
    const modalBox = document.getElementById('modal-ai-analysis');
    const content = document.getElementById('modal-ai-feedback');
    if (!modalBox || !content) return;

    modalBox.style.display = 'block';
    
    let html = `
        <div style="margin-bottom:8px; font-weight:700; color:#00FF94;">VERDICT: ${review.verdict.toUpperCase()} (${review.confidence}%)</div>
        <div style="margin-bottom:12px; font-style:italic;">"${review.summary}"</div>
    `;

    if (review.errors && review.errors.length) {
        html += `<div style="color:#FF2D78; margin-bottom:4px; font-weight:700;">ERRORS DETECTED:</div>
                 <ul style="margin:0 0 12px 16px; padding:0;">${review.errors.map(e => `<li>${e}</li>`).join('')}</ul>`;
    }

    if (review.corrections && review.corrections.length) {
        html += `<div style="color:#00FF94; margin-bottom:4px; font-weight:700;">REQUIRED CORRECTIONS:</div>
                 <ul style="margin:0 0 12px 16px; padding:0;">${review.corrections.map(c => `<li>${c}</li>`).join('')}</ul>`;
    }

    html += `<div style="background:rgba(0,0,0,0.2); padding:8px; border-radius:4px; margin-top:8px;">${review.feedback}</div>`;
    
    content.innerHTML = html;
}

function renderAIFeedbackSmall(review) {
    let html = `<div style="margin-bottom:4px;">${review.summary}</div>`;
    if (review.errors && review.errors.length) {
        html += `<div style="color:#FF2D78; font-size:10px;">• ${review.errors[0]}</div>`;
    }
    return html;
}
