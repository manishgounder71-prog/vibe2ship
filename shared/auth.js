/**
 * FutureShield AI - JWT Authentication Layer
 *
 * Manages user registration, login, token storage, and automatic
 * Authorization header injection for all /api/* requests.
 *
 * Depends on window.FutureShield namespace (loaded by fs-shared.js).
 */
(function (ns) {
  "use strict";

  // ─── Original fetch reference ──────────────────────────────────
  var originalFetch = window.fetch;

  // ─── Storage keys ────────────────────────────────────────────────
  var TOKEN_KEY = "futureshield_jwt_token";
  var USER_KEY = "futureshield_user";

  // ─── Public API ─────────────────────────────────────────────────
  ns.auth = {};

  /**
   * Get the stored JWT token.
   */
  ns.auth.getToken = function () {
    return localStorage.getItem(TOKEN_KEY);
  };

  /**
   * Get the stored user object.
   */
  ns.auth.getUser = function () {
    try {
      var raw = localStorage.getItem(USER_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  };

  /**
   * Store the JWT token and user info.
   */
  ns.auth.setSession = function (token, user) {
    localStorage.setItem(TOKEN_KEY, token);
    if (user) {
      localStorage.setItem(USER_KEY, JSON.stringify(user));
    }
  };

  /**
   * Clear the stored session (logout).
   */
  ns.auth.clearSession = function () {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  };

  /**
   * Check if the user is currently authenticated.
   */
  ns.auth.isAuthenticated = function () {
    return !!ns.auth.getToken();
  };

  /**
   * Register a new user account.
   * @param {string} username
   * @param {string} email
   * @param {string} password
   * @returns {Promise<object>} Response with token and user
   */
  ns.auth.register = async function (username, email, password) {
    var response = await originalFetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: username, email: email, password: password }),
    });
    var data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Registration failed");
    }
    ns.auth.setSession(data.access_token, data.user);
    return data;
  };

  /**
   * Login with username and password.
   * @param {string} username
   * @param {string} password
   * @returns {Promise<object>} Response with token and user
   */
  ns.auth.login = async function (username, password) {
    var response = await originalFetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: username, password: password }),
    });
    var data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Login failed");
    }
    ns.auth.setSession(data.access_token, data.user);
    return data;
  };

  /**
   * Logout: clear the session and notify the server.
   */
  ns.auth.logout = async function () {
    try {
      await originalFetch("/api/auth/logout", {
        method: "POST",
        headers: { Authorization: "Bearer " + ns.auth.getToken() },
      });
    } catch (e) {
      // Ignore network errors on logout
    }
    ns.auth.clearSession();
    ns.showLoginOverlay();
  };

  /**
   * Verify the current token with the server.
   * @returns {Promise<boolean>} True if the token is valid
   */
  ns.auth.verify = async function () {
    var token = ns.auth.getToken();
    if (!token) return false;
    try {
      var response = await originalFetch("/api/auth/verify", {
        headers: { Authorization: "Bearer " + token },
      });
      return response.ok;
    } catch (e) {
      return false;
    }
  };

  // ─── Custom Fetch Interceptor ───────────────────────────────────
  window.fetch = async function (input, init) {
    init = init || {};
    var url = typeof input === "string" ? input : (input.url || "");

    // Intercept only API requests (skip auth endpoints to avoid loops)
    if (url.indexOf("/api/") !== -1 && url.indexOf("/api/auth/") === -1) {
      init.headers = init.headers || {};
      var token = ns.auth.getToken();
      if (token) {
        if (init.headers instanceof Headers) {
          if (!init.headers.has("Authorization")) {
            init.headers.set("Authorization", "Bearer " + token);
          }
        } else if (Array.isArray(init.headers)) {
          var hasAuth = init.headers.some(function (h) {
            return h[0].toLowerCase() === "authorization";
          });
          if (!hasAuth) {
            init.headers.push(["Authorization", "Bearer " + token]);
          }
        } else {
          if (!init.headers["Authorization"]) {
            init.headers["Authorization"] = "Bearer " + token;
          }
        }
      }
    }

    var response = await originalFetch(input, init);

    // Auto-logout if 401 on API paths (except auth endpoints)
    if (response.status === 401 && url.indexOf("/api/") !== -1 && url.indexOf("/api/auth/") === -1) {
      ns.auth.clearSession();
      ns.showLoginOverlay();
    }

    return response;
  };

  // ─── Login Overlay ──────────────────────────────────────────────
  ns.showLoginOverlay = function () {
    if (document.getElementById("futureshield-auth-overlay")) return;

    var overlay = document.createElement("div");
    overlay.id = "futureshield-auth-overlay";
    overlay.className = "fixed inset-0 z-[9999] flex items-center justify-center bg-background/95 backdrop-blur-md";

    overlay.innerHTML =
      '<div class="glass-panel p-8 rounded-xl max-w-md w-full border border-primary/20 shadow-[0_0_50px_rgba(0,212,255,0.15)] relative">' +
        '<div class="absolute inset-0 scanline pointer-events-none opacity-20"></div>' +
        '<div class="flex flex-col items-center text-center">' +
          '<span class="material-symbols-outlined text-primary text-[48px] animate-pulse mb-4">security</span>' +
          '<h2 class="font-label-caps text-[20px] text-primary-fixed-dim tracking-widest mb-2">FUTURESHIELD ACCESS</h2>' +
          '<p class="text-on-surface-variant text-sm mb-6">Sign in to your account or create a new one.</p>' +
          '<div id="auth-tab-login" class="flex w-full mb-4 border border-white/10 rounded-lg overflow-hidden">' +
            '<button id="auth-tab-login-btn" class="flex-1 py-2 text-xs font-label-caps tracking-wider bg-primary/20 text-primary border-r border-white/10">LOGIN</button>' +
            '<button id="auth-tab-register-btn" class="flex-1 py-2 text-xs font-label-caps tracking-wider bg-transparent text-on-surface-variant">REGISTER</button>' +
          '</div>' +
          '<div id="auth-login-form" class="w-full">' +
            '<div class="w-full space-y-3">' +
              '<input type="text" id="auth-login-username" placeholder="Username" ' +
                     'class="w-full bg-surface-container border border-outline-variant rounded-lg px-4 py-3 text-white focus:outline-none focus:border-primary placeholder-outline transition-colors text-center font-mono" />' +
              '<input type="password" id="auth-login-password" placeholder="Password" ' +
                     'class="w-full bg-surface-container border border-outline-variant rounded-lg px-4 py-3 text-white focus:outline-none focus:border-primary placeholder-outline transition-colors text-center font-mono" />' +
              '<p id="auth-error-msg" class="text-error text-xs mt-2 hidden"></p>' +
            '</div>' +
            '<button id="auth-login-submit" class="w-full primary-glow-button text-black font-semibold py-3 px-6 rounded-lg transition-transform active:scale-95 mt-4">SIGN IN</button>' +
          '</div>' +
          '<div id="auth-register-form" class="w-full hidden">' +
            '<div class="w-full space-y-3">' +
              '<input type="text" id="auth-register-username" placeholder="Username" ' +
                     'class="w-full bg-surface-container border border-outline-variant rounded-lg px-4 py-3 text-white focus:outline-none focus:border-primary placeholder-outline transition-colors text-center font-mono" />' +
              '<input type="email" id="auth-register-email" placeholder="Email" ' +
                     'class="w-full bg-surface-container border border-outline-variant rounded-lg px-4 py-3 text-white focus:outline-none focus:border-primary placeholder-outline transition-colors text-center font-mono" />' +
              '<input type="password" id="auth-register-password" placeholder="Password (min 6 chars)" ' +
                     'class="w-full bg-surface-container border border-outline-variant rounded-lg px-4 py-3 text-white focus:outline-none focus:border-primary placeholder-outline transition-colors text-center font-mono" />' +
              '<p id="auth-register-error-msg" class="text-error text-xs mt-2 hidden"></p>' +
            '</div>' +
            '<button id="auth-register-submit" class="w-full primary-glow-button text-black font-semibold py-3 px-6 rounded-lg transition-transform active:scale-95 mt-4">CREATE ACCOUNT</button>' +
          '</div>' +
        '</div>' +
      '</div>';

    document.body.appendChild(overlay);

    // ─── Tab switching ────────────────────────────────────────────
    var loginForm = overlay.querySelector("#auth-login-form");
    var registerForm = overlay.querySelector("#auth-register-form");
    var loginTab = overlay.querySelector("#auth-tab-login-btn");
    var registerTab = overlay.querySelector("#auth-tab-register-btn");

    function showLoginTab() {
      loginForm.classList.remove("hidden");
      registerForm.classList.add("hidden");
      loginTab.className = "flex-1 py-2 text-xs font-label-caps tracking-wider bg-primary/20 text-primary border-r border-white/10";
      registerTab.className = "flex-1 py-2 text-xs font-label-caps tracking-wider bg-transparent text-on-surface-variant";
      document.getElementById("auth-error-msg").classList.add("hidden");
    }

    function showRegisterTab() {
      loginForm.classList.add("hidden");
      registerForm.classList.remove("hidden");
      loginTab.className = "flex-1 py-2 text-xs font-label-caps tracking-wider bg-transparent text-on-surface-variant border-r border-white/10";
      registerTab.className = "flex-1 py-2 text-xs font-label-caps tracking-wider bg-primary/20 text-primary";
      document.getElementById("auth-register-error-msg").classList.add("hidden");
    }

    loginTab.addEventListener("click", showLoginTab);
    registerTab.addEventListener("click", showRegisterTab);

    // ─── Login handler ───────────────────────────────────────────
    async function handleLogin() {
      var username = document.getElementById("auth-login-username").value.trim();
      var password = document.getElementById("auth-login-password").value;
      var errorMsg = document.getElementById("auth-error-msg");
      var submitBtn = document.getElementById("auth-login-submit");

      if (!username || !password) {
        errorMsg.textContent = "Please enter username and password.";
        errorMsg.classList.remove("hidden");
        return;
      }

      submitBtn.innerText = "AUTHENTICATING...";
      submitBtn.disabled = true;
      errorMsg.classList.add("hidden");

      try {
        var data = await ns.auth.login(username, password);
        overlay.remove();
        window.location.reload();
      } catch (e) {
        errorMsg.textContent = e.message || "Login failed. Check your credentials.";
        errorMsg.classList.remove("hidden");
        submitBtn.innerText = "SIGN IN";
        submitBtn.disabled = false;
      }
    }

    // ─── Register handler ────────────────────────────────────────
    async function handleRegister() {
      var username = document.getElementById("auth-register-username").value.trim();
      var email = document.getElementById("auth-register-email").value.trim();
      var password = document.getElementById("auth-register-password").value;
      var errorMsg = document.getElementById("auth-register-error-msg");
      var submitBtn = document.getElementById("auth-register-submit");

      if (!username || !email || !password) {
        errorMsg.textContent = "Please fill in all fields.";
        errorMsg.classList.remove("hidden");
        return;
      }
      if (password.length < 6) {
        errorMsg.textContent = "Password must be at least 6 characters.";
        errorMsg.classList.remove("hidden");
        return;
      }

      submitBtn.innerText = "CREATING ACCOUNT...";
      submitBtn.disabled = true;
      errorMsg.classList.add("hidden");

      try {
        var data = await ns.auth.register(username, email, password);
        overlay.remove();
        window.location.reload();
      } catch (e) {
        errorMsg.textContent = e.message || "Registration failed.";
        errorMsg.classList.remove("hidden");
        submitBtn.innerText = "CREATE ACCOUNT";
        submitBtn.disabled = false;
      }
    }

    overlay.querySelector("#auth-login-submit").addEventListener("click", handleLogin);
    overlay.querySelector("#auth-register-submit").addEventListener("click", handleRegister);

    // Enter key handling
    document.getElementById("auth-login-password").addEventListener("keypress", function (e) {
      if (e.key === "Enter") handleLogin();
    });
    document.getElementById("auth-register-password").addEventListener("keypress", function (e) {
      if (e.key === "Enter") handleRegister();
    });

    setTimeout(function () { document.getElementById("auth-login-username").focus(); }, 100);
  };

  // ─── Verify Stored Token ───────────────────────────────────────
  ns.verifyHandshake = async function () {
    var token = ns.auth.getToken();
    if (!token) {
      ns.showLoginOverlay();
      return;
    }

    try {
      var response = await originalFetch("/api/auth/verify", {
        headers: { Authorization: "Bearer " + token },
      });
      if (!response.ok) {
        ns.auth.clearSession();
        ns.showLoginOverlay();
      }
    } catch (e) {
      // Offline fallback — don't block if server is unreachable
    }
  };

})(window.FutureShield);
