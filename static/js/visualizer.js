/**
 * Re:Learn Visualizer - Plain JS, no libraries.
 * Generates animation steps in-browser from student code analysis.
 * API: RelearnVisualizer.open(code, problemId, testInput) / .close()
 */
(function (G) {
  'use strict';

  function detectMaxInit(code) {
    var c = code.replace(/\/\/.*/g, '').replace(/\/\*[\s\S]*?\*\//g, '');
    return /\b(?:max|maxVal)\s*=\s*0\s*;/.test(c) ? 0 : null;
  }
  function detectLoopStart(code) {
    var c = code.replace(/\/\/.*/g, '');
    var m = c.match(/for\s*\(\s*(?:int\s+)?i\s*=\s*(\d+)\s*;/);
    return m ? parseInt(m[1], 10) : 1;
  }
  function detectSubBug(code) {
    var c = code.replace(/\/\/.*/g, '');
    return /-=/.test(c) || /\-\s*arr\[/.test(c);
  }

  /* ---- Step generators ---- */
  function stepsMax(arr, code) {
    var steps = [], forcedInit = detectMaxInit(code), loopStart = detectLoopStart(code);
    var wrongInit = (forcedInit !== null), maxVal = wrongInit ? 0 : arr[0];
    steps.push({ ptrIdx: wrongInit ? -1 : 0, hlIdx: wrongInit ? -1 : 0, hlKind:'init',
      maxVal: maxVal, isWrong: wrongInit,
      caption: wrongInit
        ? 'Initialize max = 0 \u26a0\ufe0f (fails when all values are negative!)'
        : 'Initialize max = arr[0] = ' + arr[0] });
    for (var i = loopStart; i < arr.length; i++) {
      var curr = arr[i], bigger = curr > maxVal;
      steps.push({ ptrIdx:i, hlIdx:i, hlKind:'comparing', maxVal:maxVal, isWrong:false,
        caption: 'i = ' + i + ': arr[' + i + '] (' + curr + ') vs max (' + maxVal + ') \u2192 '
          + (bigger ? curr + ' > ' + maxVal + ', max updates' : curr + ' \u2264 ' + maxVal + ', no change') });
      if (bigger) {
        maxVal = curr;
        steps.push({ ptrIdx:i, hlIdx:i, hlKind:'updated', maxVal:maxVal, isWrong:false,
          caption: 'i = ' + i + ': ' + curr + ' is bigger \u2014 max becomes ' + maxVal });
      }
    }
    var real = arr.reduce(function(a,b){ return b>a?b:a; }, arr[0]);
    var fw = maxVal !== real;
    steps.push({ ptrIdx:-1, hlIdx:-1, hlKind: fw?'wrong':'done', maxVal:maxVal, isWrong:fw,
      caption: fw
        ? 'Done. Returned max = ' + maxVal + ' \u274c (correct: ' + real + '). Initialize to arr[0], not 0!'
        : 'Done. Returned max = ' + maxVal + ' \u2713 Correct!' });
    return steps;
  }

  function stepsSum(arr, code) {
    var steps = [], isSub = detectSubBug(code), sum = 0;
    steps.push({ ptrIdx:-1, hlIdx:-1, hlKind:'init', varVal:0, varLbl:'sum', isWrong:false,
                 caption:'Initialize sum = 0' });
    for (var i = 0; i < arr.length; i++) {
      var v = arr[i]; if (isSub) sum -= v; else sum += v;
      steps.push({ ptrIdx:i, hlIdx:i, hlKind: isSub?'wrong':'active',
        varVal:sum, varLbl:'sum', isWrong:isSub,
        caption: isSub
          ? 'i=' + i + ': sum -= arr[' + i + '] (' + v + ') \u2192 sum=' + sum + ' \u26a0\ufe0f (bug: -= not +=)'
          : 'i=' + i + ': sum += arr[' + i + '] (' + v + ') \u2192 sum=' + sum });
    }
    steps.push({ ptrIdx:-1, hlIdx:-1, hlKind:'done', varVal:sum, varLbl:'sum', isWrong:false,
                 caption:'Return sum = ' + sum });
    return steps;
  }

  function stepsGeneric(arr) {
    return [{ ptrIdx:-1, hlIdx:-1, hlKind:'done', isWrong:false,
      caption:'Array: [' + arr.join(', ') + '] \u2014 visualizer coming soon for this problem type.' }];
  }

  function makeSteps(pid, code, arr) {
    if (pid === 1) return stepsMax(arr, code);
    if (pid === 2) return stepsSum(arr, code);
    return stepsGeneric(arr);
  }

  /* ---- Input parser ---- */
  function parseInput(s) {
    if (!s) return [];
    var parts = s.trim().replace(/\n/g, ' ').split(/\s+/), nums = [];
    for (var i = 0; i < parts.length; i++) { var n = parseInt(parts[i],10); if (!isNaN(n)) nums.push(n); }
    if (nums.length < 2) return nums;
    return nums.slice(1, 1 + nums[0]);
  }

  /* ---- State ---- */
  var modal=null, steps=[], idx=0, timer=null, speed=900, arr=[], pid=1;

  /* ---- CSS ---- */
  var CSS = [
    '@keyframes rlFade{from{opacity:0}to{opacity:1}}',
    '@keyframes rlPop{0%{transform:scale(.82)}60%{transform:scale(1.1)}100%{transform:scale(1)}}',
    '#rlviz{position:fixed;inset:0;z-index:9999;background:rgba(11,15,25,.88);',
      'backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);',
      'display:flex;align-items:center;justify-content:center;animation:rlFade .2s}',
    '#rl-box{background:#0B0F19;border:1px solid rgba(255,255,255,.1);border-radius:16px;',
      'width:min(740px,96vw);max-height:92vh;display:flex;flex-direction:column;overflow:hidden;',
      'box-shadow:0 0 60px rgba(99,102,241,.3)}',
    '#rl-hdr{display:flex;align-items:center;justify-content:space-between;padding:13px 20px;',
      'border-bottom:1px solid rgba(255,255,255,.08);background:rgba(255,255,255,.03)}',
    '#rl-ttl{font-size:.9rem;font-weight:700;background:linear-gradient(135deg,#6366F1,#38BDF8);',
      '-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}',
    '#rl-cls{background:none;border:none;cursor:pointer;color:#64748B;font-size:1.25rem;',
      'padding:4px 9px;border-radius:6px;line-height:1;transition:color .2s,background .2s}',
    '#rl-cls:hover{color:#fff;background:rgba(255,255,255,.1)}',
    '#rl-body{padding:20px;overflow-y:auto;display:flex;flex-direction:column;gap:18px}',
    '.rl-lbl{font:.67rem/1 inherit;font-weight:700;letter-spacing:.08em;color:#475569;text-transform:uppercase;margin-bottom:5px}',
    '#rl-ptrs{display:flex;gap:6px;min-height:22px}',
    '.rl-pt{width:48px;display:flex;justify-content:center}',
    '.rl-chip{background:#6366F1;color:#fff;font:.7rem/1 "JetBrains Mono",monospace;font-weight:700;',
      'padding:2px 7px;border-radius:99px;box-shadow:0 0 8px rgba(99,102,241,.7);transition:opacity .25s}',
    '#rl-cells{display:flex;gap:6px;flex-wrap:wrap}',
    '.rl-cell{display:flex;flex-direction:column;align-items:center;gap:3px}',
    '.rl-cv{width:48px;height:48px;display:flex;align-items:center;justify-content:center;',
      'font:700 1rem "JetBrains Mono",monospace;border-radius:8px;',
      'border:2px solid rgba(255,255,255,.1);background:rgba(99,102,241,.13);color:#fff;',
      'transition:background .3s,border-color .3s,transform .25s,box-shadow .3s}',
    '.rl-cv.hl-comparing{background:rgba(56,189,248,.3);border-color:#38BDF8;',
      'box-shadow:0 0 14px rgba(56,189,248,.5);transform:scale(1.12)}',
    '.rl-cv.hl-updated{background:rgba(52,211,153,.35);border-color:#34D399;',
      'box-shadow:0 0 14px rgba(52,211,153,.5);animation:rlPop .4s}',
    '.rl-cv.hl-init{background:rgba(99,102,241,.35);border-color:#6366F1}',
    '.rl-cv.hl-wrong{background:rgba(239,68,68,.35);border-color:#EF4444;',
      'box-shadow:0 0 14px rgba(239,68,68,.5);animation:rlPop .4s}',
    '.rl-cv.hl-done{background:rgba(52,211,153,.18);border-color:rgba(52,211,153,.5)}',
    '.rl-cv.hl-active{background:rgba(99,102,241,.35);border-color:#6366F1;box-shadow:0 0 10px rgba(99,102,241,.4)}',
    '.rl-ci{font:.64rem/1 "JetBrains Mono",monospace;color:#475569}',
    '#rl-vbox{display:inline-flex;align-items:center;gap:10px;',
      'background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.1);border-radius:10px;padding:10px 18px}',
    '#rl-vlbl{font:.82rem/1 "JetBrains Mono",monospace;color:#64748B}',
    '#rl-vval{font:800 1.4rem/1 "JetBrains Mono",monospace;color:#38BDF8;transition:color .3s;display:inline-block}',
    '#rl-vval.wrong{color:#EF4444}#rl-vval.good{color:#34D399}',
    '#rl-cap{background:rgba(99,102,241,.08);border:1px solid rgba(99,102,241,.2);border-radius:10px;',
      'padding:12px 16px;font-size:.9rem;line-height:1.55;color:#CBD5E1;min-height:52px}',
    '#rl-cap.wcap{background:rgba(239,68,68,.08);border-color:rgba(239,68,68,.3);color:#FECACA}',
    '#rl-ctrls{display:flex;flex-wrap:wrap;align-items:center;gap:8px;',
      'padding-top:4px;border-top:1px solid rgba(255,255,255,.08)}',
    '.rl-btn{display:inline-flex;align-items:center;gap:5px;background:rgba(255,255,255,.06);',
      'border:1px solid rgba(255,255,255,.1);border-radius:8px;color:#fff;font:.83rem/1 inherit;font-weight:600;',
      'padding:7px 14px;cursor:pointer;transition:background .2s,transform .1s,box-shadow .2s}',
    '.rl-btn:hover{background:rgba(99,102,241,.25);border-color:#6366F1;box-shadow:0 0 8px rgba(99,102,241,.35)}',
    '.rl-btn:active{transform:scale(.96)}',
    '.rl-btn:disabled{opacity:.35;cursor:not-allowed;pointer-events:none}',
    '.rl-btn.pri{background:linear-gradient(135deg,#6366F1,#4F46E5);border-color:transparent;',
      'box-shadow:0 0 12px rgba(99,102,241,.4)}',
    '.rl-btn.pri:hover{filter:brightness(1.15)}',
    '#rl-slbl{font:.77rem/1 "JetBrains Mono",monospace;color:#64748B;margin-left:auto}',
    '#rl-srow{display:flex;align-items:center;gap:8px;width:100%;font:.77rem/1 inherit;color:#64748B}',
    '.rl-range{-webkit-appearance:none;appearance:none;height:4px;border-radius:9999px;',
      'background:rgba(255,255,255,.1);outline:none;cursor:pointer}',
    '.rl-range::-webkit-slider-thumb{-webkit-appearance:none;width:14px;height:14px;border-radius:50%;',
      'background:#6366F1;cursor:pointer;box-shadow:0 0 6px rgba(99,102,241,.7)}',
    '#rl-scrub{flex:1}#rl-spd{width:90px}'
  ].join('');

  /* ---- HTML template ---- */
  function buildHTML() {
    return '<style>' + CSS + '</style>' +
      '<div id="rl-box">' +
        '<div id="rl-hdr">' +
          '<span id="rl-ttl">\u25b6 Code Visualizer</span>' +
          '<button id="rl-cls" aria-label="Close">\u2715</button>' +
        '</div>' +
        '<div id="rl-body">' +
          '<div><div class="rl-lbl">Array</div>' +
            '<div id="rl-ptrs"></div><div id="rl-cells"></div></div>' +
          '<div><div class="rl-lbl">Variable</div>' +
            '<div id="rl-vbox"><span id="rl-vlbl">max =</span><span id="rl-vval">\u2014</span></div></div>' +
          '<div><div class="rl-lbl">Step Caption</div><div id="rl-cap">Ready \u2014 press Play or step manually</div></div>' +
          '<div id="rl-ctrls">' +
            '<button class="rl-btn" id="rl-prev">\u25c4 Prev</button>' +
            '<button class="rl-btn pri" id="rl-play">\u25b6 Play</button>' +
            '<button class="rl-btn" id="rl-next">Next \u25ba</button>' +
            '<span id="rl-slbl">Step 0 of 0</span>' +
          '</div>' +
          '<div id="rl-srow">' +
            '<span>Scrub:</span>' +
            '<input type="range" class="rl-range" id="rl-scrub" min="0" value="0" step="1">' +
            '<span style="margin-left:6px">Speed:</span>' +
            '<input type="range" class="rl-range" id="rl-spd" min="200" max="2000" step="100" value="900">' +
            '<span id="rl-spd-lbl">1.1\xd7</span>' +
          '</div>' +
        '</div>' +
      '</div>';
  }

  /* ---- DOM helpers ---- */
  function buildArrayUI(a) {
    var ptrs = document.getElementById('rl-ptrs');
    var cells = document.getElementById('rl-cells');
    if (!ptrs || !cells) return;
    ptrs.innerHTML = a.map(function(_,i) {
      return '<div class="rl-pt" id="rlp' + i + '"><span class="rl-chip" style="opacity:0">i</span></div>';
    }).join('');
    cells.innerHTML = a.map(function(v,i) {
      return '<div class="rl-cell"><div class="rl-cv" id="rlc' + i + '">' + v + '</div>' +
             '<div class="rl-ci">[' + i + ']</div></div>';
    }).join('');
  }

  function render() {
    if (!steps.length) return;
    var s = steps[idx]; if (!s) return;
    // Pointer
    for (var i = 0; i < arr.length; i++) {
      var p = document.getElementById('rlp' + i);
      if (p) { var ch = p.querySelector('.rl-chip'); if (ch) ch.style.opacity = i === s.ptrIdx ? '1' : '0'; }
    }
    // Cells
    for (var j = 0; j < arr.length; j++) {
      var cv = document.getElementById('rlc' + j); if (!cv) continue;
      cv.className = 'rl-cv';
      if (j === s.hlIdx) cv.classList.add('hl-' + (s.hlKind || 'active'));
    }
    // Variable
    var vv = document.getElementById('rl-vval'), vl = document.getElementById('rl-vlbl');
    var val = (s.maxVal !== undefined) ? s.maxVal : s.varVal;
    var lbl = s.varLbl || (pid === 2 ? 'sum' : 'max');
    if (vl) vl.textContent = lbl + ' =';
    if (vv) { vv.textContent = (val !== null && val !== undefined) ? val : '\u2014';
               vv.className = s.isWrong ? 'wrong' : (s.hlKind === 'done' ? 'good' : ''); }
    // Caption
    var cap = document.getElementById('rl-cap');
    if (cap) { cap.textContent = s.caption || ''; cap.className = s.isWrong ? 'wcap' : ''; }
    // Step label
    var sl = document.getElementById('rl-slbl');
    if (sl) sl.textContent = 'Step ' + (idx + 1) + ' of ' + steps.length;
    // Scrubber
    var sc = document.getElementById('rl-scrub'); if (sc) sc.value = idx;
    // Buttons
    var bp = document.getElementById('rl-prev'), bn = document.getElementById('rl-next');
    if (bp) bp.disabled = (idx === 0); if (bn) bn.disabled = (idx === steps.length - 1);
  }

  function stepPrev() { if (idx > 0) { idx--; render(); } }
  function stepNext() { if (idx < steps.length - 1) { idx++; render(); } }
  function autoStep() { if (idx < steps.length - 1) { idx++; render(); } else pausePlay(); }
  function togglePlay() { if (timer) pausePlay(); else startPlay(); }
  function startPlay() {
    var b = document.getElementById('rl-play'); if (b) b.textContent = '\u23f8 Pause';
    if (idx === steps.length - 1) idx = 0;
    timer = setInterval(autoStep, speed);
  }
  function pausePlay() {
    clearInterval(timer); timer = null;
    var b = document.getElementById('rl-play'); if (b) b.textContent = '\u25b6 Play';
  }
  function closeViz() {
    pausePlay(); if (modal) { modal.remove(); modal = null; }
  }

  /* ---- Open ---- */
  function open(code, problemId, testInput) {
    closeViz();
    pid = problemId || 1;
    arr = parseInput(testInput);
    if (!arr.length && pid === 1) arr = [3, 7, 2, 9, 5];
    if (!arr.length && pid === 2) arr = [1, 2, 3, 4, 5];
    steps = makeSteps(pid, code || '', arr);
    idx = 0; timer = null;

    var ov = document.createElement('div');
    ov.id = 'rlviz';
    ov.setAttribute('role', 'dialog');
    ov.setAttribute('aria-label', 'Code Visualizer');
    ov.innerHTML = buildHTML();
    document.body.appendChild(ov);
    modal = ov;

    document.getElementById('rl-cls').addEventListener('click', closeViz);
    ov.addEventListener('click', function(e){ if (e.target === ov) closeViz(); });
    document.getElementById('rl-prev').addEventListener('click', stepPrev);
    document.getElementById('rl-next').addEventListener('click', stepNext);
    document.getElementById('rl-play').addEventListener('click', togglePlay);
    document.getElementById('rl-scrub').addEventListener('input', function() { idx = parseInt(this.value,10); render(); });
    document.getElementById('rl-spd').addEventListener('input', function() {
      speed = parseInt(this.value,10);
      document.getElementById('rl-spd-lbl').textContent = (1000/speed).toFixed(1) + '\xd7';
      if (timer) { clearInterval(timer); timer = setInterval(autoStep, speed); }
    });

    var sc = document.getElementById('rl-scrub'); if (sc) sc.max = Math.max(0, steps.length - 1);
    buildArrayUI(arr);
    render();
  }

  G.RelearnVisualizer = { open: open, close: closeViz };
})(window);