/**
 * Re:Learn - Practice Screen Logic (Vanilla JS)
 */

document.addEventListener('DOMContentLoaded', () => {
  // 1. Auth Guard
  const storedUser = localStorage.getItem('relearn_user');
  if (!storedUser) {
    window.location.href = '/login';
    return;
  }

  // State
  let currentQuestion = null;
  let questionsAnsweredCount = 0;

  // DOM Elements
  const practiceMainCard = document.getElementById('practiceMainCard');
  const practiceCompletionCard = document.getElementById('practiceCompletionCard');
  const questionProgressText = document.getElementById('questionProgressText');
  const progressFillBar = document.getElementById('progressFillBar');
  const questionPromptTitle = document.getElementById('questionPromptTitle');
  const questionDifficultyBadge = document.getElementById('questionDifficultyBadge');
  const codeLineNumbers = document.getElementById('codeLineNumbers');
  const codeLinesContainer = document.getElementById('codeLinesContainer');
  const codeFilename = document.getElementById('codeFilename');
  
  const predictionForm = document.getElementById('predictionForm');
  const predictedOutputInput = document.getElementById('predictedOutputInput');
  const checkAnswerBtn = document.getElementById('checkAnswerBtn');
  const btnText = checkAnswerBtn.querySelector('.btn-text');
  const btnSpinner = checkAnswerBtn.querySelector('.btn-spinner');

  const feedbackCard = document.getElementById('feedbackCard');
  const feedbackTitleText = document.getElementById('feedbackTitleText');
  const dispYourPrediction = document.getElementById('dispYourPrediction');
  const dispActualOutput = document.getElementById('dispActualOutput');
  const nextQuestionBtn = document.getElementById('nextQuestionBtn');
  const restartPracticeBtn = document.getElementById('restartPracticeBtn');
  const logoutBtn = document.getElementById('logoutBtn');

  // Logout handler
  if (logoutBtn) {
    logoutBtn.addEventListener('click', (e) => {
      e.preventDefault();
      localStorage.removeItem('relearn_user');
      window.location.href = '/login';
    });
  }

  // Load First Question
  loadQuestion();

  // Handle Form Submission
  predictionForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!currentQuestion) return;

    const prediction = predictedOutputInput.value;

    setButtonLoading(true, 'Checking...');

    try {
      const response = await fetch('/api/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question_id: currentQuestion.id,
          predicted_output: prediction,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to verify answer.');
      }

      const result = await response.json();
      renderFeedback(result);
    } catch (err) {
      alert(err.message || 'An error occurred while checking your prediction.');
    } finally {
      setButtonLoading(false, 'Check my answer');
    }
  });

  // Handle Next Question
  nextQuestionBtn.addEventListener('click', () => {
    questionsAnsweredCount++;
    if (questionsAnsweredCount >= (currentQuestion?.total_questions || 6)) {
      showCompletion();
    } else {
      loadQuestion(currentQuestion ? currentQuestion.id : null);
    }
  });

  // Handle Restart
  if (restartPracticeBtn) {
    restartPracticeBtn.addEventListener('click', () => {
      questionsAnsweredCount = 0;
      practiceCompletionCard.style.display = 'none';
      practiceMainCard.style.display = 'block';
      loadQuestion(null);
    });
  }

  // Fetch Question from Backend
  async function loadQuestion(currentId = null) {
    resetCardState();
    
    try {
      const url = currentId ? `/api/question/next?current_id=${currentId}` : '/api/question/next';
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error('Could not load question.');
      }

      const data = await response.json();
      currentQuestion = data;
      renderQuestion(data);
    } catch (err) {
      console.error(err);
      questionPromptTitle.textContent = 'Error loading question.';
    }
  }

  function renderQuestion(q) {
    // Update progress
    questionProgressText.textContent = `Question ${q.question_index} of ${q.total_questions}`;
    const percent = Math.round((q.question_index / q.total_questions) * 100);
    progressFillBar.style.width = `${percent}%`;

    // Title & badge
    questionPromptTitle.textContent = q.question_text || 'What will this print?';
    questionDifficultyBadge.textContent = q.difficulty ? q.difficulty.toUpperCase() : 'C BASICS';
    codeFilename.textContent = `question_${q.id}.c`;

    // Render code with line numbers
    const lines = q.code.split('\n');
    let lineNumHtml = '';
    for (let i = 1; i <= lines.length; i++) {
      lineNumHtml += `${i}<br>`;
    }
    codeLineNumbers.innerHTML = lineNumHtml;

    // Syntax highlight code lines
    codeLinesContainer.innerHTML = highlightCCode(q.code);

    // Reset input
    predictedOutputInput.value = '';
    predictedOutputInput.disabled = false;
    predictedOutputInput.focus();
    checkAnswerBtn.style.display = 'inline-flex';
    feedbackCard.style.display = 'none';
  }

  function renderFeedback(result) {
    feedbackCard.className = `feedback-card ${result.is_correct ? 'correct' : 'incorrect'}`;

    if (result.is_correct) {
      feedbackTitleText.innerHTML = `
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
          <polyline points="22 4 12 14.01 9 11.01"></polyline>
        </svg>
        <span>Correct! Exactly matches real C output.</span>
      `;
      dispYourPrediction.textContent = result.predicted_output;
      dispActualOutput.textContent = result.actual_output;
    } else {
      feedbackTitleText.innerHTML = `
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="15" y1="9" x2="9" y2="15"></line>
          <line x1="9" y1="9" x2="15" y2="15"></line>
        </svg>
        <span>Mismatch Detected</span>
      `;

      const diff = highlightFirstDiff(result.predicted_output, result.actual_output);
      dispYourPrediction.innerHTML = diff.userHtml;
      dispActualOutput.innerHTML = diff.actualHtml;
    }

    feedbackCard.style.display = 'block';
    predictedOutputInput.disabled = true;
    checkAnswerBtn.style.display = 'none';
    nextQuestionBtn.focus();
  }

  function showCompletion() {
    practiceMainCard.style.display = 'none';
    practiceCompletionCard.style.display = 'block';
  }

  function resetCardState() {
    feedbackCard.style.display = 'none';
    predictedOutputInput.disabled = false;
    checkAnswerBtn.style.display = 'inline-flex';
  }

  function setButtonLoading(isLoading, text) {
    checkAnswerBtn.disabled = isLoading;
    btnText.textContent = text;
    btnSpinner.style.display = isLoading ? 'inline-block' : 'none';
  }

  // Character Diff Highlighter
  function highlightFirstDiff(strUser, strActual) {
    const rawUser = strUser ?? '';
    const rawActual = strActual ?? '';
    const maxLen = Math.max(rawUser.length, rawActual.length);

    let diffIdx = -1;
    for (let i = 0; i < maxLen; i++) {
      const c1 = i < rawUser.length ? rawUser[i] : null;
      const c2 = i < rawActual.length ? rawActual[i] : null;
      if (c1 !== c2) {
        diffIdx = i;
        break;
      }
    }

    if (diffIdx === -1) {
      return {
        userHtml: escapeHtml(rawUser) || '<em>(empty)</em>',
        actualHtml: escapeHtml(rawActual) || '<em>(empty)</em>'
      };
    }

    let userHtml = '';
    if (diffIdx < rawUser.length) {
      const before = escapeHtml(rawUser.slice(0, diffIdx));
      const char = rawUser[diffIdx] === ' ' ? '␣' : rawUser[diffIdx];
      const after = escapeHtml(rawUser.slice(diffIdx + 1));
      userHtml = `${before}<span class="diff-char-marker">${escapeHtml(char)}</span>${after}`;
    } else {
      userHtml = `${escapeHtml(rawUser)}<span class="diff-char-marker">[missing end]</span>`;
    }

    let actualHtml = '';
    if (diffIdx < rawActual.length) {
      const before = escapeHtml(rawActual.slice(0, diffIdx));
      const char = rawActual[diffIdx] === ' ' ? '␣' : rawActual[diffIdx];
      const after = escapeHtml(rawActual.slice(diffIdx + 1));
      actualHtml = `${before}<span class="diff-char-actual">${escapeHtml(char)}</span>${after}`;
    } else {
      actualHtml = `${escapeHtml(rawActual)}<span class="diff-char-actual">[extra]</span>`;
    }

    return { userHtml, actualHtml };
  }

  // Simple C Syntax Highlighter
  function highlightCCode(code) {
    return code
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/(#include\s+(&lt;.*?&gt;|\".*?\"))/g, '<span class="token-kw">$1</span>')
      .replace(/\b(int|char|float|double|void)\b/g, '<span class="token-type">$1</span>')
      .replace(/\b(for|if|else|return|sizeof|while)\b/g, '<span class="token-kw">$1</span>')
      .replace(/\b(printf|malloc|free|strcmp)\b/g, '<span class="token-fn">$1</span>')
      .replace(/(".*?")/g, '<span class="token-str">$1</span>')
      .replace(/(\/\/.*$)/gm, '<span class="token-comment">$1</span>');
  }

  function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }
});
