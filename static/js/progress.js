/**
 * Re:Learn - Progress Analytics and Canvas Chart Renderer
 * Custom lightweight canvas visualizations with zero external library overhead.
 */

document.addEventListener('DOMContentLoaded', async () => {
  const user = await window.initRelearnHeader('progress');
  if (!user) return;

  const kpiSolved = document.getElementById('kpiSolved');
  const kpiAccuracy = document.getElementById('kpiAccuracy');
  const kpiAvgFix = document.getElementById('kpiAvgFix');
  const kpiAttempts = document.getElementById('kpiAttempts');
  const topicMasteryContainer = document.getElementById('topicMasteryContainer');
  const errorLegendList = document.getElementById('errorLegendList');
  const badgesGrid = document.getElementById('badgesGrid');

  async function loadProgress() {
    try {
      const [progRes, profRes] = await Promise.all([
        fetch(`/api/progress?student_id=${user.id}`),
        fetch(`/api/user/profile?student_id=${user.id}`)
      ]);

      const prog = await progRes.json();
      const prof = await profRes.json();

      // Render KPIs
      kpiSolved.textContent = `${prog.solved_count} / 10`;
      kpiAccuracy.textContent = `${prog.accuracy_pct}%`;
      const avgSecs = (prog.avg_fix_ms / 1000).toFixed(1);
      kpiAvgFix.textContent = prog.avg_fix_ms > 0 ? `${avgSecs}s` : '—';
      kpiAttempts.textContent = prog.total_attempts;

      // Render Charts
      drawSolveTimeBarChart(prog.solve_times || []);
      renderTopicMastery(prog.topic_mastery || []);
      drawErrorDonutChart(prog.error_types || []);
      renderBadges(prof.badges || []);
    } catch (err) {
      console.error('Error loading progress analytics:', err);
    }
  }

  // 1. Solve Time Canvas Bar Chart
  function drawSolveTimeBarChart(solveTimes) {
    const canvas = document.getElementById('solveTimeCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;

    ctx.clearRect(0, 0, w, h);

    if (solveTimes.length === 0) {
      ctx.fillStyle = '#64748B';
      ctx.font = '14px Plus Jakarta Sans, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('No solved problems yet. Solve problems to see your time curve!', w / 2, h / 2);
      return;
    }

    const padding = 40;
    const chartW = w - padding * 2;
    const chartH = h - padding * 2;

    const maxTimeSec = Math.max(...solveTimes.map(s => s.total_time_ms / 1000), 30);
    const barWidth = Math.min(50, (chartW / solveTimes.length) * 0.6);
    const gap = chartW / solveTimes.length;

    // Draw baseline
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(padding, h - padding);
    ctx.lineTo(w - padding, h - padding);
    ctx.stroke();

    solveTimes.forEach((item, idx) => {
      const timeSec = item.total_time_ms / 1000;
      const barH = (timeSec / maxTimeSec) * chartH;
      const x = padding + idx * gap + (gap - barWidth) / 2;
      const y = h - padding - barH;

      // Bar gradient
      const grad = ctx.createLinearGradient(0, y, 0, h - padding);
      grad.addColorStop(0, '#6366F1');
      grad.addColorStop(1, '#38BDF8');

      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.roundRect(x, y, barWidth, barH, [6, 6, 0, 0]);
      ctx.fill();

      // Top label (Seconds)
      ctx.fillStyle = '#F8FAFC';
      ctx.font = '11px JetBrains Mono, monospace';
      ctx.textAlign = 'center';
      ctx.fillText(`${timeSec.toFixed(1)}s`, x + barWidth / 2, y - 8);

      // Bottom label (Problem Title abbreviation)
      ctx.fillStyle = '#94A3B8';
      ctx.font = '11px Plus Jakarta Sans, sans-serif';
      const label = item.title.length > 8 ? item.title.substring(0, 8) + '..' : item.title;
      ctx.fillText(label, x + barWidth / 2, h - padding + 18);
    });
  }

  // 2. Topic Mastery Progress Bars
  function renderTopicMastery(masteryList) {
    if (!topicMasteryContainer) return;
    if (masteryList.length === 0) {
      topicMasteryContainer.innerHTML = '<div style="color: var(--text-dim);">No topic data available.</div>';
      return;
    }

    topicMasteryContainer.innerHTML = masteryList.map(item => {
      const pct = Math.round((item.solved_in_topic / item.total_in_topic) * 100) || 0;
      return `
        <div style="margin-bottom: 1.25rem;">
          <div style="display: flex; justify-content: space-between; font-size: 0.92rem; font-weight: 700; margin-bottom: 0.4rem;">
            <span>${escapeHtml(item.topic)}</span>
            <span style="color: var(--cyan-accent);">${item.solved_in_topic} / ${item.total_in_topic} (${pct}%)</span>
          </div>
          <div style="height: 10px; background: rgba(255, 255, 255, 0.08); border-radius: 9999px; overflow: hidden;">
            <div style="height: 100%; width: ${pct}%; background: linear-gradient(90deg, #6366F1, #38BDF8); border-radius: 9999px; transition: width 0.6s ease;"></div>
          </div>
        </div>
      `;
    }).join('');
  }

  // 3. Error Types Donut Chart
  function drawErrorDonutChart(errorTypes) {
    const canvas = document.getElementById('errorDonutCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    if (errorTypes.length === 0) {
      ctx.fillStyle = '#64748B';
      ctx.font = '13px Plus Jakarta Sans, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('No error patterns recorded!', w / 2, h / 2);
      return;
    }

    const colors = ['#EF4444', '#F59E0B', '#6366F1', '#38BDF8', '#EC4899', '#8B5CF6'];
    const totalErrors = errorTypes.reduce((acc, curr) => acc + curr.cnt, 0);

    let startAngle = -Math.PI / 2;
    const centerX = w / 2;
    const centerY = h / 2;
    const outerRadius = 100;
    const innerRadius = 60;

    errorTypes.forEach((item, idx) => {
      const sliceAngle = (item.cnt / totalErrors) * 2 * Math.PI;
      const color = colors[idx % colors.length];

      ctx.beginPath();
      ctx.arc(centerX, centerY, outerRadius, startAngle, startAngle + sliceAngle);
      ctx.arc(centerX, centerY, innerRadius, startAngle + sliceAngle, startAngle, true);
      ctx.closePath();
      ctx.fillStyle = color;
      ctx.fill();

      startAngle += sliceAngle;
    });

    // Donut center text
    ctx.fillStyle = '#F8FAFC';
    ctx.font = 'bold 20px Plus Jakarta Sans, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(`${totalErrors}`, centerX, centerY - 6);
    ctx.font = '10px Plus Jakarta Sans, sans-serif';
    ctx.fillStyle = '#94A3B8';
    ctx.fillText('ERRORS', centerX, centerY + 14);

    // Legend
    if (errorLegendList) {
      errorLegendList.innerHTML = errorTypes.map((item, idx) => {
        const color = colors[idx % colors.length];
        const pct = Math.round((item.cnt / totalErrors) * 100);
        return `
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem; font-size: 0.85rem;">
            <div style="display: flex; align-items: center; gap: 0.5rem;">
              <span style="width: 10px; height: 10px; border-radius: 50%; background: ${color}; display: inline-block;"></span>
              <span>${escapeHtml(item.error_type.replace(/_/g, ' '))}</span>
            </div>
            <span style="font-weight: 700; color: var(--text-muted);">${item.cnt} (${pct}%)</span>
          </div>
        `;
      }).join('');
    }
  }

  // 4. Badges List
  function renderBadges(badges) {
    if (!badgesGrid) return;
    if (badges.length === 0) {
      badgesGrid.innerHTML = `
        <div style="grid-column: span 2; padding: 1rem; color: var(--text-dim); text-align: center;">
          Solve problems and fix bugs to earn badges!
        </div>
      `;
      return;
    }

    badgesGrid.innerHTML = badges.map(b => `
      <div style="display: flex; align-items: center; gap: 0.85rem; padding: 0.85rem 1rem; background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: var(--radius-md);">
        <div style="font-size: 1.75rem;">${b.icon || '🏅'}</div>
        <div>
          <div style="font-weight: 800; font-size: 0.92rem; color: #FFFFFF;">${escapeHtml(b.badge_name)}</div>
          <div style="font-size: 0.78rem; color: var(--text-muted);">${escapeHtml(b.badge_desc)}</div>
        </div>
      </div>
    `).join('');
  }

  loadProgress();
});
