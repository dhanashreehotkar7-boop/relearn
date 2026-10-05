/**
 * Re:Learn - Problems List Controller
 */

document.addEventListener('DOMContentLoaded', async () => {
  const user = await window.initRelearnHeader('problems');
  if (!user) return;

  const problemsContainer = document.getElementById('problemsListContainer');
  const topicTabs = document.querySelectorAll('.topic-tab-btn');
  let currentTopic = 'all';
  let allProblems = [];

  // Fetch Problems
  async function loadProblems() {
    try {
      const res = await fetch(`/api/problems?student_id=${user.id}`);
      if (!res.ok) throw new Error('Failed to load problems.');
      const data = await res.json();
      allProblems = data.problems || [];
      renderProblems();
    } catch (err) {
      problemsContainer.innerHTML = `
        <div style="padding: 2rem; text-align: center; color: var(--error-text);">
          ${err.message || 'Error loading problems list.'}
        </div>
      `;
    }
  }

  function renderProblems() {
    const filtered = currentTopic === 'all' 
      ? allProblems 
      : allProblems.filter(p => p.topic.toLowerCase() === currentTopic.toLowerCase());

    if (filtered.length === 0) {
      problemsContainer.innerHTML = `
        <div style="padding: 2.5rem; text-align: center; color: var(--text-muted);">
          No problems found in this category.
        </div>
      `;
      return;
    }

    problemsContainer.innerHTML = filtered.map(p => {
      const isSolved = p.is_solved;
      const statusIcon = isSolved 
        ? `<span class="status-icon solved" title="Solved">✓</span>` 
        : `<span class="status-icon unsolved" title="Unsolved">○</span>`;

      const diffClass = p.difficulty.toLowerCase() === 'easy' ? 'badge-easy' : (p.difficulty.toLowerCase() === 'medium' ? 'badge-medium' : 'badge-hard');

      let timeFormatted = '—';
      if (p.best_time_ms) {
        const mins = Math.floor(p.best_time_ms / 60000);
        const secs = ((p.best_time_ms % 60000) / 1000).toFixed(1);
        timeFormatted = mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
      }

      return `
        <a href="/problems/${p.id}" class="problem-row">
          <div>${statusIcon}</div>
          <div style="font-weight: 700; color: #F8FAFC;">${p.id}. ${escapeHtml(p.title)}</div>
          <div>
            <span style="font-size: 0.82rem; color: var(--cyan-accent); font-weight: 600;">${escapeHtml(p.topic)}</span>
          </div>
          <div>
            <span class="badge-diff ${diffClass}">${escapeHtml(p.difficulty)}</span>
          </div>
          <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; color: ${isSolved ? '#34D399' : 'var(--text-dim)'};">
            ${timeFormatted}
          </div>
          <div>
            <span class="nav-btn-ghost" style="padding: 0.35rem 0.85rem; font-size: 0.82rem; display: inline-block;">
              ${isSolved ? 'Review' : 'Solve'}
            </span>
          </div>
        </a>
      `;
    }).join('');
  }

  // Topic Tab Handlers
  topicTabs.forEach(btn => {
    btn.addEventListener('click', () => {
      topicTabs.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentTopic = btn.getAttribute('data-topic');
      renderProblems();
    });
  });

  loadProblems();
});
