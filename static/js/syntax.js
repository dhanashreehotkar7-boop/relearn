/**
 * Re:Learn - Robust Single-Pass C Syntax Tokenizer
 * Escapes HTML first, then tokenizes in ONE pass without multiple overlapping passes.
 */

window.highlightCCode = function(code) {
  if (!code) return '';
  
  // Step 1: Escape HTML entities
  const escaped = code
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // Step 2: Combined single-pass tokenizer regex
  const cTokenRegex = /(\/\/.*$|\/\*[\s\S]*?\*\/)|(#\s*(?:include|define|ifdef|ifndef|endif)\b[^\n]*)|("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')|(\b(?:int|char|float|double|void|struct|long|short|unsigned|signed|bool|const|static|typedef|sizeof)\b)|(\b(?:if|else|for|while|do|switch|case|default|break|continue|return|goto)\b)|(\b[a-zA-Z_]\w*(?=\s*\())|(\b\d+(?:\.\d+)?\b)/gm;

  return escaped.replace(cTokenRegex, (match, comment, preproc, str, typeKw, controlKw, fnCall, num) => {
    if (comment) return `<span class="token-comment">${comment}</span>`;
    if (preproc) return `<span class="token-kw">${preproc}</span>`;
    if (str) return `<span class="token-str">${str}</span>`;
    if (typeKw) return `<span class="token-type">${typeKw}</span>`;
    if (controlKw) return `<span class="token-kw">${controlKw}</span>`;
    if (fnCall) return `<span class="token-fn">${fnCall}</span>`;
    if (num) return `<span class="token-num">${num}</span>`;
    return match;
  });
};

window.escapeHtml = function(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
};
