/**
 * Re:Learn - 3-Column LeetCode Problem Workspace Controller
 * Live Timer, Editor, Test Runner, Execution Tracer, and Chatbot
 */

document.addEventListener('DOMContentLoaded', async () => {
  const user = await window.initRelearnHeader('problems');
  if (!user) return;

  // Extract problem ID from URL pathname e.g. /problems/3
  const pathParts = window.location.pathname.split('/').filter(Boolean);
  const problemId = parseInt(pathParts[pathParts.length - 1], 10) || 1;

  // State Variables
  let problemData = null;
  let timerInterval = null;
  let elapsedMs = 0;
  let lastTimestamp = performance.now();
  let isTimerRunning = true;
  let startedAtMs = Date.now();
  let lastErrorShownMs = null;
  let lastErrorType = null;
  let currentResults = [];
  let currentActiveTestCaseIdx = 0;
  let latestErrorInfo = null;

  // Tracer State
  let tracerSteps = [];
  let currentTracerStepIdx = 0;
  let tracerPlayInterval = null;

  // DOM Elements
  const tabBtnDesc = document.getElementById('tabBtnDesc');
  const tabBtnSol = document.getElementById('tabBtnSol');
  const descTabContent = document.getElementById('descTabContent');
  const solTabContent = document.getElementById('solTabContent');
  const solLockIcon = document.getElementById('solLockIcon');
  const problemSolBody = document.getElementById('problemSolBody');
  const probTitleDisplay = document.getElementById('probTitleDisplay');
  const probDiffDisplay = document.getElementById('probDiffDisplay');
  const probTopicDisplay = document.getElementById('probTopicDisplay');
  const probDescriptionText = document.getElementById('probDescriptionText');

  const liveTimerDisplay = document.getElementById('liveTimerDisplay');
  const btnRunCode = document.getElementById('btnRunCode');
  const btnSubmitCode = document.getElementById('btnSubmitCode');
  const btnVisualize = document.getElementById('btnVisualize');
  const cCodeEditor = document.getElementById('cCodeEditor');
  const editorLineGutter = document.getElementById('editorLineGutter');
  const editorErrorBanner = document.getElementById('editorErrorBanner');
  const errorBannerTitle = document.getElementById('errorBannerTitle');
  const errorBannerExplanation = document.getElementById('errorBannerExplanation');

  const testCasePillsRow = document.getElementById('testCasePillsRow');
  const overallVerdictBadge = document.getElementById('overallVerdictBadge');
  const resultsContentBody = document.getElementById('resultsContentBody');

  const chatMessageList = document.getElementById('chatMessageList');
  const chatInputForm = document.getElementById('chatInputForm');
  const chatPromptInput = document.getElementById('chatPromptInput');
  const chipHint = document.getElementById('chipHint');
  const chipExplainError = document.getElementById('chipExplainError');
  const chipExplainProblem = document.getElementById('chipExplainProblem');

  // ==========================================
  // 1. LIVE CENTISECOND TIMER (mm:ss.cs)
  // ==========================================
  function startLiveTimer() {
    lastTimestamp = performance.now();
    timerInterval = setInterval(() => {
      if (!isTimerRunning) return;
      const now = performance.now();
      elapsedMs += (now - lastTimestamp);
      lastTimestamp = now;
      renderTimerDisplay();
    }, 30);
  }

  function renderTimerDisplay() {
    const totalCentis = Math.floor(elapsedMs / 10);
    const cs = String(totalCentis % 100).padStart(2, '0');
    const totalSecs = Math.floor(totalCentis / 100);
    const s = String(totalSecs % 60).padStart(2, '0');
    const m = String(Math.floor(totalSecs / 60)).padStart(2, '0');
    liveTimerDisplay.textContent = `${m}:${s}.${cs}`;
  }

  // Handle Tab Switching / Visibility Change
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      isTimerRunning = false;
    } else {
      lastTimestamp = performance.now();
      isTimerRunning = true;
    }
  });

  // ==========================================
  // 2. CODE EDITOR & LINE GUTTER
  // ==========================================
  function updateLineNumbers(errorLine = null) {
    const lines = cCodeEditor.value.split('\n');
    const lineCount = Math.max(1, lines.length);
    let gutterHtml = '';
    for (let i = 1; i <= lineCount; i++) {
      const isError = (errorLine !== null && i === errorLine);
      gutterHtml += `<div class="gutter-line ${isError ? 'error-gutter' : ''}">${i}</div>`;
    }
    editorLineGutter.innerHTML = gutterHtml;
  }

  cCodeEditor.addEventListener('scroll', () => {
    editorLineGutter.scrollTop = cCodeEditor.scrollTop;
  });

  cCodeEditor.addEventListener('input', () => {
    updateLineNumbers();
    if (editorErrorBanner.classList.contains('visible')) {
      editorErrorBanner.classList.remove('visible');
    }
  });

  // Tab Key Support (4 Spaces)
  cCodeEditor.addEventListener('keydown', (e) => {
    if (e.key === 'Tab') {
      e.preventDefault();
      const start = cCodeEditor.selectionStart;
      const end = cCodeEditor.selectionEnd;
      cCodeEditor.value = cCodeEditor.value.substring(0, start) + '    ' + cCodeEditor.value.substring(end);
      cCodeEditor.selectionStart = cCodeEditor.selectionEnd = start + 4;
      updateLineNumbers();
    }
  });

  // ==========================================
  // 3. LOAD PROBLEM DATA
  // ==========================================
  async function loadProblem() {
    try {
      const res = await fetch(`/api/problems/${problemId}?student_id=${user.id}`);
      if (!res.ok) {
        let errDetail = 'Failed to load problem details.';
        try {
          const errData = await res.json();
          if (errData && errData.detail) errDetail = errData.detail;
        } catch (e) {}
        throw new Error(errDetail);
      }
      problemData = await res.json();

      probTitleDisplay.textContent = `${problemData.id}. ${problemData.title}`;
      probDiffDisplay.textContent = problemData.difficulty;
      probDiffDisplay.className = `badge-diff badge-${problemData.difficulty.toLowerCase()}`;
      probTopicDisplay.textContent = problemData.topic;
      probDescriptionText.innerHTML = problemData.description;

      cCodeEditor.value = problemData.starter_code || '';
      updateLineNumbers();

      if (problemData.is_solved) {
        unlockSolutionTab();
      }

      startLiveTimer();
    } catch (err) {
      probTitleDisplay.textContent = 'Error loading problem.';
      probDescriptionText.innerHTML = `<div style="color: var(--error-text);">${escapeHtml(err.message)}</div>`;
    }
  }

  function unlockSolutionTab() {
    solLockIcon.textContent = '✓';
    solLockIcon.style.color = '#34D399';
    if (problemData.model_solution) {
      const highlightedSolution = window.highlightCCode(problemData.model_solution);
      problemSolBody.innerHTML = `
        <h3>Model C Solution</h3>
        <pre style="padding: 1rem; border-radius: var(--radius-md);"><code class="hljs">${highlightedSolution}</code></pre>
        <h3>Complexity Analysis</h3>
        <p><strong>Time Complexity:</strong> <code>${problemData.time_complexity || 'O(N)'}</code></p>
        <p><strong>Space Complexity:</strong> <code>${problemData.space_complexity || 'O(1)'}</code></p>
        <h3>Detailed Explanation</h3>
        <div style="line-height: 1.6; color: var(--text-muted);">${problemData.solution_explanation || ''}</div>
      `;
    }
  }

  tabBtnDesc.addEventListener('click', () => {
    tabBtnDesc.classList.add('active');
    tabBtnSol.classList.remove('active');
    descTabContent.style.display = 'block';
    solTabContent.style.display = 'none';
  });

  tabBtnSol.addEventListener('click', () => {
    if (!problemData || !problemData.is_solved) {
      window.showToast('Solve the problem to unlock the official model solution!', 'error');
      return;
    }
    tabBtnSol.classList.add('active');
    tabBtnDesc.classList.remove('active');
    descTabContent.style.display = 'none';
    solTabContent.style.display = 'block';
  });

  // ==========================================
  // 4. CODE EXECUTION (RUN & SUBMIT)
  // ==========================================
  async function executeCode(isSubmit = false) {
    const code = cCodeEditor.value;
    const endpoint = isSubmit ? `/api/problems/${problemId}/submit` : `/api/problems/${problemId}/run`;
    
    btnRunCode.disabled = true;
    btnSubmitCode.disabled = true;
    overallVerdictBadge.textContent = isSubmit ? 'Evaluating All Test Cases...' : 'Running Public Tests...';
    overallVerdictBadge.style.color = '#38BDF8';
    resultsContentBody.innerHTML = `<div style="color: var(--text-dim); padding: 1.5rem;">Compiling with gcc -std=c99 -Wall...</div>`;

    const payload = {
      student_id: user.id,
      code: code,
      started_at_ms: startedAtMs,
      submitted_at_ms: Date.now(),
      error_shown_ms: lastErrorShownMs,
      last_error_type: lastErrorType
    };

    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        let errDetail = `Server returned HTTP ${res.status}: ${res.statusText}`;
        try {
          const errData = await res.json();
          if (errData && errData.detail) errDetail = errData.detail;
          else if (errData && errData.message) errDetail = errData.message;
        } catch (parseErr) {}
        throw new Error(errDetail);
      }

      const data = await res.json();
      handleExecutionResult(data, isSubmit);
    } catch (err) {
      overallVerdictBadge.textContent = 'Execution Error';
      overallVerdictBadge.style.color = '#EF4444';
      resultsContentBody.innerHTML = `
        <div style="color: var(--error-text); padding: 1rem; line-height: 1.5;">
          <strong>Server Error:</strong> ${escapeHtml(err.message)}
        </div>
      `;
    } finally {
      btnRunCode.disabled = false;
      btnSubmitCode.disabled = false;
    }
  }

  btnRunCode.addEventListener('click', () => executeCode(false));
  btnSubmitCode.addEventListener('click', () => executeCode(true));

  // ==========================================
  // VISUALIZE BUTTON
  // ==========================================
  btnVisualize.addEventListener('click', () => {
    if (!problemData) { window.showToast('Problem not loaded yet.', 'error'); return; }
    const code = cCodeEditor.value;
    // Grab the first public test case input (Case 1) for the animation
    const cases = problemData.public_test_cases || [];
    const testInput = cases.length > 0 ? cases[0].input : '';
    if (window.RelearnVisualizer) {
      window.RelearnVisualizer.open(code, problemData.id, testInput);
    } else {
      window.showToast('Visualizer not loaded.', 'error');
    }
  });

  // ==========================================
  // 5. RESULT HANDLING & ERROR BANNER
  // ==========================================
  function handleExecutionResult(data, isSubmit) {
    if (data.status === 'compile_error') {
      overallVerdictBadge.textContent = 'Compile Error';
      overallVerdictBadge.style.color = '#EF4444';
      
      const firstDiag = data.diagnostics && data.diagnostics.length > 0 ? data.diagnostics[0] : null;
      const errLine = data.error_line || (firstDiag ? firstDiag.line : 1);
      
      updateLineNumbers(errLine);

      editorErrorBanner.classList.add('visible');
      errorBannerTitle.textContent = `Line ${errLine}: ${firstDiag ? firstDiag.message : 'Compilation Error'}`;
      errorBannerExplanation.innerHTML = `
        <div><strong>💡 Friendly Explanation:</strong> ${firstDiag ? firstDiag.friendly_explanation : 'Review the syntax near line ' + errLine}</div>
      `;

      resultsContentBody.innerHTML = `
        <div style="color: #FCA5A5; line-height: 1.6;">
          <div style="font-weight: 700; margin-bottom: 0.5rem;">GCC Diagnostic Output:</div>
          <pre style="background: #06090F; padding: 0.75rem; border-radius: 4px; overflow-x: auto;"><code>${escapeHtml(data.raw_stderr || '')}</code></pre>
        </div>
      `;

      lastErrorShownMs = Date.now();
      lastErrorType = 'compile_error';
      latestErrorInfo = { diagnostic: firstDiag ? firstDiag.friendly_explanation : data.raw_stderr, error_type: 'compile_error' };
      return;
    }

    editorErrorBanner.classList.remove('visible');
    updateLineNumbers();

    if (data.is_accepted) {
      overallVerdictBadge.textContent = 'Accepted 🎉';
      overallVerdictBadge.style.color = '#10B981';

      problemData.is_solved = true;
      unlockSolutionTab();

      window.showToast(`Accepted! Solved in ${data.time_display} (+${data.xp_earned} XP)`, 'success', 5000);

      window.initRelearnHeader('problems');

      currentResults = data.results || [];
      renderTestCasePills();
      renderTestCaseDetail(0);

      latestErrorInfo = null;
      lastErrorShownMs = null;
      lastErrorType = null;
      return;
    }

    overallVerdictBadge.textContent = data.status === 'timeout' ? 'Time Limit Exceeded' : (data.status === 'runtime_error' ? 'Runtime Error' : 'Wrong Answer');
    overallVerdictBadge.style.color = '#EF4444';

    currentResults = data.results || [];
    renderTestCasePills();

    const failIdx = currentResults.findIndex(r => !r.passed);
    renderTestCaseDetail(failIdx >= 0 ? failIdx : 0, data.divergence);

    lastErrorShownMs = Date.now();
    lastErrorType = data.error_type || 'wrong_answer';
    latestErrorInfo = {
      explanation: data.divergence ? data.divergence.explanation : 'Wrong output',
      error_type: data.error_type
    };
  }

  function renderTestCasePills() {
    testCasePillsRow.innerHTML = currentResults.map((tc, idx) => {
      const cls = tc.passed ? 'passed' : 'failed';
      return `<button class="tc-pill-btn ${cls} ${idx === currentActiveTestCaseIdx ? 'active' : ''}" data-idx="${idx}">Case ${idx + 1}</button>`;
    }).join('');

    testCasePillsRow.querySelectorAll('.tc-pill-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        currentActiveTestCaseIdx = parseInt(btn.getAttribute('data-idx'), 10);
        renderTestCasePills();
        renderTestCaseDetail(currentActiveTestCaseIdx);
      });
    });
  }

  function renderTestCaseDetail(idx, divergenceData = null) {
    const tc = currentResults[idx];
    if (!tc) return;

    let content = `
      <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem; margin-bottom: 0.75rem;">
        <div>
          <div style="font-size: 0.75rem; color: var(--text-dim); text-transform: uppercase; font-weight: 700;">Input</div>
          <pre style="background: rgba(0,0,0,0.3); padding: 0.5rem; border-radius: 4px; margin-top: 0.25rem;"><code>${escapeHtml(tc.input)}</code></pre>
        </div>
        <div>
          <div style="font-size: 0.75rem; color: var(--text-dim); text-transform: uppercase; font-weight: 700;">Expected Output</div>
          <pre style="background: rgba(0,0,0,0.3); padding: 0.5rem; border-radius: 4px; margin-top: 0.25rem; color: #34D399;"><code>${escapeHtml(tc.expected)}</code></pre>
        </div>
        <div>
          <div style="font-size: 0.75rem; color: var(--text-dim); text-transform: uppercase; font-weight: 700;">Your Output</div>
          <pre style="background: rgba(0,0,0,0.3); padding: 0.5rem; border-radius: 4px; margin-top: 0.25rem; color: ${tc.passed ? '#34D399' : '#FCA5A5'};"><code>${escapeHtml(tc.actual)}</code></pre>
        </div>
      </div>
    `;

    if (!tc.passed && divergenceData) {
      content += `
        <div class="tracer-visualizer-card">
          <div style="color: #FCA5A5; font-size: 0.85rem; margin-bottom: 0.5rem;">
            <strong>🔍 Why did this happen?</strong> ${escapeHtml(divergenceData.explanation || '')}
          </div>
          <div class="tracer-controls">
            <span class="tracer-step-counter" id="tracerStepCounter">Step 1 of ${divergenceData.trace_steps.length}</span>
            <div class="tracer-btn-group">
              <button class="tracer-btn" id="btnTracerPrev">◀ Prev</button>
              <button class="tracer-btn" id="btnTracerPlay">▶ Play</button>
              <button class="tracer-btn" id="btnTracerNext">Next ▶</button>
            </div>
          </div>
          <div class="tracer-state-grid" id="tracerStateGrid"></div>
        </div>
      `;

      tracerSteps = divergenceData.trace_steps || [];
      currentTracerStepIdx = 0;
    }

    resultsContentBody.innerHTML = content;

    if (!tc.passed && divergenceData) {
      renderTracerStep();
      const btnPrev = document.getElementById('btnTracerPrev');
      const btnNext = document.getElementById('btnTracerNext');
      const btnPlay = document.getElementById('btnTracerPlay');

      if (btnPrev) btnPrev.addEventListener('click', () => {
        if (currentTracerStepIdx > 0) {
          currentTracerStepIdx--;
          renderTracerStep();
        }
      });
      if (btnNext) btnNext.addEventListener('click', () => {
        if (currentTracerStepIdx < tracerSteps.length - 1) {
          currentTracerStepIdx++;
          renderTracerStep();
        }
      });
      if (btnPlay) btnPlay.addEventListener('click', () => {
        if (tracerPlayInterval) {
          clearInterval(tracerPlayInterval);
          tracerPlayInterval = null;
          btnPlay.textContent = '▶ Play';
        } else {
          btnPlay.textContent = '⏸ Pause';
          tracerPlayInterval = setInterval(() => {
            if (currentTracerStepIdx < tracerSteps.length - 1) {
              currentTracerStepIdx++;
              renderTracerStep();
            } else {
              clearInterval(tracerPlayInterval);
              tracerPlayInterval = null;
              btnPlay.textContent = '▶ Play';
            }
          }, 800);
        }
      });
    }
  }

  function renderTracerStep() {
    const step = tracerSteps[currentTracerStepIdx];
    if (!step) return;

    const counter = document.getElementById('tracerStepCounter');
    const grid = document.getElementById('tracerStateGrid');
    if (counter) counter.textContent = `Step ${currentTracerStepIdx + 1} of ${tracerSteps.length} ${step.is_divergent ? '(Divergence Point!)' : ''}`;

    let varRows = Object.entries(step.variables || {}).map(([k, v]) => `
      <div class="tracer-var-item">
        <span style="color: var(--cyan-accent); font-family: monospace;">${escapeHtml(k)}</span>
        <span style="font-weight: 700; color: #FFFFFF;">${escapeHtml(String(v))}</span>
      </div>
    `).join('');

    let arrayCells = '';
    for (const [arrName, cells] of Object.entries(step.arrays || {})) {
      if (Array.isArray(cells)) {
        arrayCells += `<div style="margin-bottom: 0.35rem; font-size: 0.75rem; color: var(--text-dim);">${escapeHtml(arrName)}:</div><div class="tracer-array-cells">`;
        arrayCells += cells.map((c, i) => `
          <div class="tracer-cell">
            <div class="tracer-cell-idx">[${i}]</div>
            <div class="tracer-cell-val">${escapeHtml(String(c))}</div>
          </div>
        `).join('');
        arrayCells += `</div>`;
      }
    }

    if (grid) {
      grid.innerHTML = `
        <div class="tracer-box-sub">
          <div class="tracer-sub-title">Variables Snapshot (Line ${step.line})</div>
          ${varRows || '<div style="color: var(--text-dim);">No variables</div>'}
          <div style="font-size: 0.75rem; color: #94A3B8; margin-top: 0.5rem; font-style: italic;">${escapeHtml(step.note || '')}</div>
        </div>
        <div class="tracer-box-sub">
          <div class="tracer-sub-title">Memory State</div>
          ${arrayCells || '<div style="color: var(--text-dim);">No arrays</div>'}
        </div>
      `;
    }
  }

  // ==========================================
  // 6. CHATBOT INTERACTIONS
  // ==========================================
  async function sendChatMessage(promptText, mode = 'chat') {
    if (!promptText.trim()) return;

    const userMsg = document.createElement('div');
    userMsg.className = 'chat-msg user';
    userMsg.textContent = promptText;
    chatMessageList.appendChild(userMsg);
    chatMessageList.scrollTop = chatMessageList.scrollHeight;

    const loadingMsg = document.createElement('div');
    loadingMsg.className = 'chat-msg assistant';
    loadingMsg.textContent = 'Thinking...';
    chatMessageList.appendChild(loadingMsg);
    chatMessageList.scrollTop = chatMessageList.scrollHeight;

    const problemDescEl = document.getElementById('problemDescBody');
    const problemText = problemDescEl ? problemDescEl.innerText : (problemData ? problemData.title : '');
    const outputEl = document.getElementById('resultsContentBody');
    const outputText = outputEl ? outputEl.innerText : '';

    try {
      const res = await fetch('/api/coach', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode: mode,
          problem: problemText,
          code: cCodeEditor.value,
          output: outputText || JSON.stringify(latestErrorInfo || {}),
          question: promptText,
          problem_id: problemId,
          student_id: user.id
        })
      });

      const data = await res.json();
      loadingMsg.innerHTML = formatMarkdown(data.reply || 'Here is some guidance.');
    } catch (err) {
      loadingMsg.textContent = 'Sorry, could not reach the coaching assistant right now.';
    } finally {
      chatMessageList.scrollTop = chatMessageList.scrollHeight;
    }
  }

  chatInputForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const txt = chatPromptInput.value;
    chatPromptInput.value = '';
    sendChatMessage(txt, 'chat');
  });

  chipHint.addEventListener('click', () => sendChatMessage('Give me a hint on how to approach this problem without revealing the code solution.', 'hint'));
  chipExplainError.addEventListener('click', () => sendChatMessage('Explain my latest error or failing test case in simple words.', 'error'));
  chipExplainProblem.addEventListener('click', () => sendChatMessage('Explain this problem and its edge cases in plain English.', 'problem'));

  function formatMarkdown(text) {
    return text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\n/g, '<br>');
  }

  loadProblem();
});
