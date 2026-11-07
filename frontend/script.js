/* MeetMind AI authentication, wired to the FastAPI backend. */
function showMessage(element, message, type = "error") {
  if (!element) return;
  element.textContent = message;
  element.className = `form-message ${type}`;
  element.setAttribute("role", "status");
}
function setupPasswordToggle(inputId, buttonId) {
  const input = document.getElementById(inputId), button = document.getElementById(buttonId);
  if (!input || !button) return;
  button.addEventListener("click", () => {
    const showing = input.type === "password";
    input.type = showing ? "text" : "password";
    button.textContent = showing ? "Hide" : "Show";
    button.setAttribute("aria-label", showing ? "Hide password" : "Show password");
  });
}
setupPasswordToggle("password", "togglePassword");
setupPasswordToggle("newPassword", "toggleSignupPassword");

async function postJSON(url, data) {
  const response = await fetch(url, {
    method: "POST", credentials: "same-origin",
    headers: { "Content-Type": "application/json" }, body: JSON.stringify(data)
  });
  let payload = {};
  try { payload = await response.json(); } catch (_) {}
  if (!response.ok) throw new Error(payload.detail || payload.message || `Request failed (${response.status})`);
  return payload;
}
const loginForm = document.getElementById("loginForm");
if (loginForm) {
  const msg = document.getElementById("loginMessage");
  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const email = document.getElementById("username")?.value.trim() || "";
    const password = document.getElementById("password")?.value || "";
    if (!email || !password) return showMessage(msg, "Enter your email/username and password.");
    const submit = loginForm.querySelector('[type="submit"]');
    if (submit) { submit.disabled = true; submit.dataset.oldText = submit.textContent; submit.textContent = "Signing in…"; }
    try {
      await postJSON("/api/auth/login", { email, password });
      console.log("LOGIN SUCCESSFUL");
      console.log("Redirecting to /home");
      showMessage(msg, "Login successful. Opening your dashboard…", "success");
      window.location.replace("/home");
    } catch (error) { showMessage(msg, error.message || "Unable to sign in."); }
    finally { if (submit) { submit.disabled = false; submit.textContent = submit.dataset.oldText || "Login"; } }
  });
  document.getElementById("forgotPassword")?.addEventListener("click", (event) => {
    event.preventDefault(); showMessage(msg, "Password reset is not configured yet. Please contact the administrator.");
  });
  document.getElementById("googleLogin")?.addEventListener("click", () => { window.location.href = "/api/auth/google?mode=login"; });
}
const signupForm = document.getElementById("signupForm");
if (signupForm) {
  const msg = document.getElementById("signupMessage");
  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const username = document.getElementById("newUsername")?.value.trim() || "";
    const email = document.getElementById("email")?.value.trim() || "";
    const password = document.getElementById("newPassword")?.value || "";
    if (!username || !email || !password) return showMessage(msg, "Complete all required fields.");
    if (username.length < 3) return showMessage(msg, "Username must contain at least 3 characters.");
    if (password.length < 8) return showMessage(msg, "Password must contain at least 8 characters.");
    const submit = signupForm.querySelector('[type="submit"]');
    if (submit) { submit.disabled = true; submit.dataset.oldText = submit.textContent; submit.textContent = "Creating account…"; }
    try {
      await postJSON("/api/auth/register", { username, email, password });
      showMessage(msg, "Account created. Redirecting to login…", "success");
      window.setTimeout(() => { window.location.href = "/static/login.html"; }, 700);
    } catch (error) { showMessage(msg, error.message || "Unable to create account."); }
    finally { if (submit) { submit.disabled = false; submit.textContent = submit.dataset.oldText || "Create account"; } }
  });
  document.getElementById("googleSignup")?.addEventListener("click", () => { window.location.href = "/api/auth/google?mode=register"; });
}
/* Share the same theme key across pages to avoid theme flashing/mismatch. */
(function () {
  if (document.body.classList.contains("login-page")) {
    return;
  }
  const toggle = document.getElementById("authThemeToggle"), icon = document.getElementById("authThemeIcon");
  const key = "meetMindTheme";
  function apply(dark) {
    document.body.classList.toggle("auth-dark", dark);
    document.body.classList.toggle("dark-mode", dark);
    if (icon) icon.textContent = dark ? "☀" : "☾";
    if (toggle) toggle.setAttribute("aria-label", dark ? "Switch to light mode" : "Switch to dark mode");
  }
  let saved = "light";
  try { saved = localStorage.getItem(key) || localStorage.getItem("meetmind-auth-theme") || localStorage.getItem("meetingAITheme") || "light"; } catch (_) {}
  apply(saved === "dark");
  toggle?.addEventListener("click", () => {
    const dark = !document.body.classList.contains("auth-dark"); apply(dark);
    try { localStorage.setItem(key, dark ? "dark" : "light"); localStorage.setItem("meetmind-auth-theme", dark ? "dark" : "light"); } catch (_) {}
  });
})();
