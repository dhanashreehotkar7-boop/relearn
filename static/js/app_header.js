/**
 * Re:Learn - Global Navigation, Gamification, and AI Tutor Controller
 */

window.initRelearnHeader = async function(activeNavKey = '') {
  const storedUser = localStorage.getItem('relearn_user');
  if (!storedUser) {
    if (window.location.pathname !== '/' && 
        window.location.pathname !== '/login' && 
        window.location.pathname !== '/signup') {
      window.location.href = '/login';
      return null;
    }
    return null;
  }

  let user = null;
  try {
    user = JSON.parse(storedUser);
  } catch (e) {
    window.location.href = '/login';
    return null;
  }

  // Fetch updated profile
  try {
    const res = await fetch(`/api/user/profile?student_id=${user.id}`);
    if (res.ok) {
      const data = await res.json();
      user = data.user;
      localStorage.setItem('relearn_user', JSON.stringify(user));
      renderHeaderGamification(user, activeNavKey);
    } else {
      renderHeaderGamification(user, activeNavKey);
    }
  } catch (err) {
    renderHeaderGamification(user, activeNavKey);
  }

  mountGlobalAiTutor(user);
  return user;
};

function renderHeaderGamification(user, activeNavKey) {
  const headerContainer = document.getElementById('globalAppHeader');
  if (!headerContainer) return;

  const xp = user.xp || 0;
  const level = user.level || 1;
  const streak = user.streak || 1;
  const nextLevelXp = level * 250;
  const currLevelBase = (level - 1) * 250;
  const levelProgress = Math.min(100, Math.max(0, Math.round(((xp - currLevelBase) / 250) * 100)));

  headerContainer.innerHTML = `
    <a href="/problems" class="brand-logo" id="navBrandLogo">
      <div class="logo-icon-wrap">
        <svg class="logo-svg" width="24" height="24" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M12 7C9.5 7 7.5 9 7.5 11.5C7.5 12.5 7.8 13.4 8.4 14.1C6.4 15.2 5 17.4 5 20C5 23.3 7.7 26 11 26C11.6 26 12.2 25.9 12.7 25.7" stroke="#38BDF8" stroke-width="1.8" stroke-linecap="round"/>
          <path d="M20 7C22.5 7 24.5 9 24.5 11.5C24.5 12.5 24.2 13.4 23.6 14.1C25.6 15.2 27 17.4 27 20C27 23.3 24.3 26 21 26C20.4 26 19.8 25.9 19.3 25.7" stroke="#38BDF8" stroke-width="1.8" stroke-linecap="round"/>
          <path d="M11 14L8 16.5L11 19" stroke="#818CF8" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M21 14L24 16.5L21 19" stroke="#818CF8" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M17 13L15 20" stroke="#6366F1" stroke-width="1.8" stroke-linecap="round"/>
        </svg>
      </div>
      <div>
        <span class="brand-name">Re:Learn</span>
        <span class="brand-tag"> [C]</span>
      </div>
    </a>

    <nav class="nav-links">
      <a href="/problems" class="nav-link ${activeNavKey === 'problems' ? 'active-nav' : ''}">Problems</a>
      <a href="/progress" class="nav-link ${activeNavKey === 'progress' ? 'active-nav' : ''}">Progress</a>
      <a href="/cards" class="nav-link ${activeNavKey === 'cards' ? 'active-nav' : ''}">Flashcards</a>
      <button class="nav-btn-tutor" id="globalAiTutorNavBtn" type="button" title="Open AI C Tutor">
        <span>🤖</span>
        <span>AI Tutor</span>
      </button>
    </nav>

    <div class="user-game-stats">
      <!-- Streak Pill -->
      <div class="game-stat-pill" title="${streak} day streak!">
        <span class="stat-icon">🔥</span>
        <span class="stat-val">${streak}d</span>
      </div>

      <!-- XP Pill -->
      <div class="game-stat-pill" title="${xp} total XP">
        <span class="stat-icon">💎</span>
        <span class="stat-val">${xp} XP</span>
      </div>

      <!-- Level Pill -->
      <div class="level-badge-wrap" title="Level ${level} (${levelProgress}% to Level ${level + 1})">
        <span class="level-tag">Lv.${level}</span>
        <div class="level-mini-bar">
          <div class="level-mini-fill" style="width: ${levelProgress}%"></div>
        </div>
      </div>

      <!-- Logout -->
      <button class="nav-btn-ghost" id="logoutBtn" style="padding: 0.4rem 0.85rem; font-size: 0.85rem; cursor: pointer;">
        Sign Out
      </button>
    </div>
  `;

  const logoutBtn = document.getElementById('logoutBtn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', () => {
      localStorage.removeItem('relearn_user');
      window.location.href = '/login';
    });
  }

  const tutorNavBtn = document.getElementById('globalAiTutorNavBtn');
  if (tutorNavBtn) {
    tutorNavBtn.addEventListener('click', () => {
      window.openAiTutorModal();
    });
  }
}

// ==========================================
// GLOBAL AI TUTOR MODAL & FLOATING WIDGET
// ==========================================
function mountGlobalAiTutor(user) {
  if (document.getElementById('globalAiTutorContainer')) return;

  // Floating Action Button
  const fab = document.createElement('button');
  fab.id = 'globalFloatingAiTutorBtn';
  fab.className = 'floating-ai-tutor-fab';
  fab.title = 'Open Re:Learn AI Tutor';
  fab.innerHTML = `<span>🤖</span><span>AI Tutor</span>`;
  document.body.appendChild(fab);

  // Overlay
  const overlay = document.createElement('div');
  overlay.id = 'globalAiTutorOverlay';
  overlay.className = 'ai-tutor-modal-overlay';
  document.body.appendChild(overlay);

  // Modal Container
  const container = document.createElement('div');
  container.id = 'globalAiTutorContainer';
  container.className = 'ai-tutor-modal-container';
  container.innerHTML = `
    <div class="ai-tutor-header">
      <div class="ai-tutor-header-title">
        <div class="ai-tutor-avatar">🤖</div>
        <div>
          <div class="ai-tutor-name">Re:Learn AI Tutor</div>
          <span class="ai-tutor-badge">Adaptive C Coach</span>
        </div>
      </div>
      <div class="ai-tutor-actions">
        <button class="ai-tutor-tool-btn" id="aiTutorReflectBtn" title="Reflect on student learning">💭 Reflect</button>
        <button class="ai-tutor-tool-btn" id="aiTutorStatsBtn" title="View memory stats">📊 Stats</button>
        <button class="ai-tutor-close-btn" id="aiTutorCloseBtn" title="Close AI Tutor">&times;</button>
      </div>
    </div>

    <!-- Quick Starter Chips -->
    <div class="ai-tutor-chips-bar" id="aiTutorChipsBar">
      <button class="ai-tutor-chip" data-query="Explain pointers and memory addresses in C in simple terms.">💡 Pointers & Memory</button>
      <button class="ai-tutor-chip" data-query="What causes a Segmentation Fault in C and how do I prevent it?">🔍 Segfault Causes</button>
      <button class="ai-tutor-chip" data-query="What is the difference between Arrays and Linked Lists in C?">🔗 Arrays vs Lists</button>
      <button class="ai-tutor-chip" data-query="How does malloc() and free() work, and why do memory leaks happen?">📦 malloc & free</button>
      <button class="ai-tutor-chip" data-query="/reflect">💭 Reflect</button>
      <button class="ai-tutor-chip" data-query="/stats">📊 Stats</button>
    </div>

    <!-- Messages Container -->
    <div class="ai-tutor-messages" id="aiTutorMessagesList">
      <div class="ai-msg ai-msg-assistant">
        👋 Hi <strong>${escapeHtml(user?.name || 'Student')}</strong>! I'm your <strong>Re:Learn AI Tutor</strong>.<br><br>
        Ask me anything about C programming, pointers, memory allocation, segmentation faults, or debugging errors!
      </div>
    </div>

    <!-- Input Form -->
    <div class="ai-tutor-input-area">
      <form class="ai-tutor-form" id="aiTutorForm">
        <input 
          type="text" 
          id="aiTutorInputField" 
          class="ai-tutor-input" 
          placeholder="Ask a C question or type /reflect..." 
          autocomplete="off"
        />
        <button type="submit" class="ai-tutor-send-btn" id="aiTutorSendBtn" title="Send message">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <line x1="22" y1="2" x2="11" y2="13"></line>
            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
          </svg>
        </button>
      </form>
    </div>
  `;
  document.body.appendChild(container);

  // Elements
  const closeBtn = document.getElementById('aiTutorCloseBtn');
  const form = document.getElementById('aiTutorForm');
  const input = document.getElementById('aiTutorInputField');
  const messagesList = document.getElementById('aiTutorMessagesList');
  const chipsBar = document.getElementById('aiTutorChipsBar');
  const reflectBtn = document.getElementById('aiTutorReflectBtn');
  const statsBtn = document.getElementById('aiTutorStatsBtn');

  // Toggle helpers
  function openModal() {
    overlay.classList.add('active');
    container.classList.add('active');
    setTimeout(() => input.focus(), 150);
  }

  function closeModal() {
    overlay.classList.remove('active');
    container.classList.remove('active');
  }

  window.openAiTutorModal = function(initialPrompt = null) {
    openModal();
    if (initialPrompt) {
      sendMessage(initialPrompt);
    }
  };

  fab.addEventListener('click', openModal);
  closeBtn.addEventListener('click', closeModal);
  overlay.addEventListener('click', closeModal);

  // Send Message Logic
  async function sendMessage(text) {
    const query = (text || '').trim();
    if (!query) return;

    // User message
    const userBubble = document.createElement('div');
    userBubble.className = 'ai-msg ai-msg-user';
    userBubble.textContent = query;
    messagesList.appendChild(userBubble);
    messagesList.scrollTop = messagesList.scrollHeight;

    // Thinking placeholder
    const assistantBubble = document.createElement('div');
    assistantBubble.className = 'ai-msg ai-msg-assistant';
    assistantBubble.textContent = 'Thinking...';
    messagesList.appendChild(assistantBubble);
    messagesList.scrollTop = messagesList.scrollHeight;

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: query,
          student_id: user?.id || null
        })
      });

      if (!res.ok) throw new Error('Could not reach the AI Tutor.');
      const data = await res.json();
      assistantBubble.innerHTML = formatMarkdown(data.reply || 'No response generated.');
    } catch (err) {
      assistantBubble.innerHTML = `⚠️ <em>${escapeHtml(err.message || 'Error communicating with AI Tutor.')}</em>`;
    } finally {
      messagesList.scrollTop = messagesList.scrollHeight;
    }
  }

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const val = input.value;
    input.value = '';
    sendMessage(val);
  });

  // Chips click handlers
  chipsBar.addEventListener('click', (e) => {
    const chip = e.target.closest('.ai-tutor-chip');
    if (chip) {
      const q = chip.getAttribute('data-query');
      if (q) sendMessage(q);
    }
  });

  reflectBtn.addEventListener('click', () => {
    sendMessage('/reflect');
  });

  statsBtn.addEventListener('click', () => {
    sendMessage('/stats');
  });
}

function formatMarkdown(text) {
  if (!text) return '';
  
  // Format code blocks
  let formatted = text.replace(/```([a-zA-Z]*)\n([\s\S]*?)```/g, (match, lang, code) => {
    return `<pre><code>${escapeHtml(code.trim())}</code></pre>`;
  });

  // Inline code
  formatted = formatted.replace(/`([^`]+)`/g, (match, code) => `<code>${escapeHtml(code)}</code>`);

  // Bold & Italics
  formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  formatted = formatted.replace(/\*([^\*]+)\*/g, '<em>$1</em>');

  // Bullet points
  formatted = formatted.replace(/^\s*[-•]\s+(.*)$/gm, '<li style="margin-left: 1.25rem;">$1</li>');

  // Line breaks
  formatted = formatted.replace(/\n\n/g, '<br><br>');
  formatted = formatted.replace(/\n/g, '<br>');

  return formatted;
}

function escapeHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = String(str);
  return div.innerHTML;
}

window.showToast = function(message, type = 'info', duration = 3500) {
  let toastContainer = document.getElementById('toastContainer');
  if (!toastContainer) {
    toastContainer = document.createElement('div');
    toastContainer.id = 'toastContainer';
    toastContainer.className = 'toast-container';
    document.body.appendChild(toastContainer);
  }

  const toast = document.createElement('div');
  toast.className = `toast-item toast-${type}`;
  toast.innerHTML = `<span>${message}</span>`;
  toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.classList.add('toast-fade');
    setTimeout(() => toast.remove(), 400);
  }, duration);
};
