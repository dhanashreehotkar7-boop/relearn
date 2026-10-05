/**
 * Re:Learn - Authentication Logic (Vanilla JS)
 */

document.addEventListener('DOMContentLoaded', () => {
  // Password Visibility Toggle
  const toggleButtons = document.querySelectorAll('.toggle-password-btn');
  toggleButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const input = btn.parentElement.querySelector('input');
      const isPassword = input.type === 'password';
      input.type = isPassword ? 'text' : 'password';
      
      // Update eye icon SVG
      btn.innerHTML = isPassword 
        ? `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>`
        : `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>`;
    });
  });

  // Handle Signup Form
  const signupForm = document.getElementById('signupForm');
  if (signupForm) {
    signupForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      clearAlert();

      const nameInput = document.getElementById('fullName');
      const emailInput = document.getElementById('email');
      const passwordInput = document.getElementById('password');
      const submitBtn = signupForm.querySelector('.btn-submit');
      const btnText = submitBtn.querySelector('.btn-text');
      const btnSpinner = submitBtn.querySelector('.btn-spinner');

      const name = nameInput.value.trim();
      const email = emailInput.value.trim();
      const password = passwordInput.value;

      // Basic client-side validation
      if (!name || name.length < 2) {
        showAlert('Please enter your full name (at least 2 characters).', 'error');
        nameInput.focus();
        return;
      }

      if (!isValidEmail(email)) {
        showAlert('Please enter a valid email address.', 'error');
        emailInput.focus();
        return;
      }

      if (!password || password.length < 6) {
        showAlert('Password must be at least 6 characters long.', 'error');
        passwordInput.focus();
        return;
      }

      // UI Loading State
      setButtonLoading(submitBtn, btnText, btnSpinner, true, 'Creating Account...');

      try {
        const response = await fetch('/api/signup', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ name, email, password }),
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.detail || 'Sign up failed. Please try again.');
        }

        // Save session locally
        localStorage.setItem('relearn_user', JSON.stringify(data.user));
        
        showAlert('Account created! Welcome to Re:Learn. Redirecting...', 'success');
        
        setTimeout(() => {
          window.location.href = '/dashboard';
        }, 1000);
      } catch (err) {
        showAlert(err.message, 'error');
        setButtonLoading(submitBtn, btnText, btnSpinner, false, 'Create Free Account');
      }
    });
  }

  // Handle Login Form
  const loginForm = document.getElementById('loginForm');
  if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      clearAlert();

      const emailInput = document.getElementById('email');
      const passwordInput = document.getElementById('password');
      const submitBtn = loginForm.querySelector('.btn-submit');
      const btnText = submitBtn.querySelector('.btn-text');
      const btnSpinner = submitBtn.querySelector('.btn-spinner');

      const email = emailInput.value.trim();
      const password = passwordInput.value;

      if (!isValidEmail(email)) {
        showAlert('Please enter a valid email address.', 'error');
        emailInput.focus();
        return;
      }

      if (!password) {
        showAlert('Please enter your password.', 'error');
        passwordInput.focus();
        return;
      }

      setButtonLoading(submitBtn, btnText, btnSpinner, true, 'Signing In...');

      try {
        const response = await fetch('/api/login', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ email, password }),
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.detail || 'Sign in failed. Check your credentials.');
        }

        // Store user in localStorage
        localStorage.setItem('relearn_user', JSON.stringify(data.user));

        showAlert('Welcome back! Redirecting...', 'success');

        setTimeout(() => {
          window.location.href = '/dashboard';
        }, 800);
      } catch (err) {
        showAlert(err.message, 'error');
        setButtonLoading(submitBtn, btnText, btnSpinner, false, 'Sign In');
      }
    });
  }
});

function showAlert(message, type = 'error') {
  const alertBox = document.getElementById('alertBox');
  if (!alertBox) return;

  alertBox.className = `alert-box ${type}`;
  alertBox.innerHTML = `
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      ${type === 'error' 
        ? '<circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line>' 
        : '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline>'}
    </svg>
    <span>${escapeHtml(message)}</span>
  `;
  alertBox.style.display = 'flex';
}

function clearAlert() {
  const alertBox = document.getElementById('alertBox');
  if (alertBox) {
    alertBox.style.display = 'none';
    alertBox.textContent = '';
  }
}

function setButtonLoading(btn, textElement, spinnerElement, isLoading, defaultText) {
  btn.disabled = isLoading;
  if (isLoading) {
    textElement.textContent = defaultText;
    spinnerElement.style.display = 'inline-block';
  } else {
    textElement.textContent = defaultText;
    spinnerElement.style.display = 'none';
  }
}

function isValidEmail(email) {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}
