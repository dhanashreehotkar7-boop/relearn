/**
 * Re:Learn - Dashboard / Welcome Screen Logic
 */

document.addEventListener('DOMContentLoaded', () => {
  const userNameElem = document.getElementById('userNameGreeting');
  const userAvatarElem = document.getElementById('userAvatarInitial');
  const userEmailElem = document.getElementById('userEmailDisplay');
  const logoutBtn = document.getElementById('logoutBtn');

  // Retrieve user session
  const storedUser = localStorage.getItem('relearn_user');
  
  if (!storedUser) {
    window.location.href = '/login';
    return;
  }

  try {
    const user = JSON.parse(storedUser);
    if (!user || !user.name) {
      window.location.href = '/login';
      return;
    }
    if (userNameElem) userNameElem.textContent = user.name;
    if (userAvatarElem) userAvatarElem.textContent = user.name.charAt(0).toUpperCase();
    if (userEmailElem) userEmailElem.textContent = user.email || '';
  } catch (e) {
    console.error('Failed to parse user session', e);
    window.location.href = '/login';
    return;
  }

  // Logout action
  if (logoutBtn) {
    logoutBtn.addEventListener('click', (e) => {
      e.preventDefault();
      localStorage.removeItem('relearn_user');
      window.location.href = '/login';
    });
  }
});
