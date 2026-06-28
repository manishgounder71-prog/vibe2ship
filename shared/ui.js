/**
 * FutureShield AI - UI Components
 *
 * Toast notifications, confirm dialog, keyboard shortcuts, journey
 * breadcrumb navigation, and AI status badge.
 *
 * Depends on window.FutureShield namespace (loaded by fs-shared.js).
 */
(function (ns) {
  "use strict";

  // ─── Toast Notification System ──────────────────────────────────
  var toastContainer = null;

  function ensureToastContainer() {
    if (!toastContainer || !document.body.contains(toastContainer)) {
      toastContainer = document.createElement("div");
      toastContainer.className = "toast-container";
      toastContainer.id = "toast-container";
      document.body.appendChild(toastContainer);
    }
    return toastContainer;
  }

  ns.showToast = function (message, type, duration) {
    type = type || "info";
    duration = duration || 4000;

    var container = ensureToastContainer();

    var toast = document.createElement("div");
    toast.className = "toast " + type;

    var icons = { success: "check_circle", error: "error", info: "info" };
    var iconName = icons[type] || "info";

    toast.innerHTML =
      '<span class="material-symbols-outlined toast-icon">' + iconName + '</span>' +
      '<span class="toast-message">' + message + '</span>';

    toast.addEventListener("click", function () {
      dismissToast(toast);
    });

    container.appendChild(toast);

    requestAnimationFrame(function () {
      toast.classList.add("show");
    });

    toast._timeoutId = setTimeout(function () {
      dismissToast(toast);
    }, duration);

    return toast;
  };

  function dismissToast(toast) {
    if (!toast || !toast.parentNode) return;
    clearTimeout(toast._timeoutId);
    toast.classList.remove("show");
    setTimeout(function () {
      if (toast.parentNode) {
        toast.parentNode.removeChild(toast);
      }
    }, 400);
  }

  ns.dismissToast = dismissToast;

  // ─── Confirm Dialog ────────────────────────────────────────────
  ns.showConfirmDialog = function (options) {
    var title = options.title || "Confirm";
    var message = options.message || "Are you sure?";
    var confirmLabel = options.confirmLabel || "Confirm";
    var cancelLabel = options.cancelLabel || "Cancel";
    var confirmVariant = options.confirmVariant || "primary";
    var sizeInfo = options.size || "";

    return new Promise(function (resolve) {
      var overlay = document.createElement("div");
      overlay.className = "fixed inset-0 z-[9998] flex items-center justify-center bg-background/80 backdrop-blur-sm";
      overlay.style.opacity = "0";
      overlay.style.transition = "opacity 0.25s ease";

      var card = document.createElement("div");
      card.className = "glass-panel p-6 rounded-xl max-w-sm w-full mx-4 border border-white/10 shadow-[0_0_40px_rgba(0,0,0,0.5)]";
      card.style.transform = "scale(0.95) translateY(10px)";
      card.style.transition = "transform 0.3s ease";

      var sizeHtml = sizeInfo
        ? '<div style="display:flex;align-items:center;gap:8px;padding:8px 12px;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.06);border-radius:8px;margin-bottom:16px;">' +
          '<span class="material-symbols-outlined" style="font-size:16px;color:#3cd7ff;">storage</span>' +
          '<span style="font-family:Inter,sans-serif;font-size:12px;color:#859398;">Estimated file size: <strong style="color:#e1e2e7;">' + sizeInfo + '</strong></span>' +
          '</div>'
        : "";

      card.innerHTML =
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">' +
          '<div style="display:flex;align-items:center;gap:8px;">' +
            '<span class="material-symbols-outlined" style="font-size:20px;color:#3cd7ff;">download</span>' +
            '<h3 style="font-family:Space Grotesk,sans-serif;font-size:13px;color:#e1e2e7;letter-spacing:0.05em;margin:0;">' + title + '</h3>' +
          '</div>' +
        '</div>' +
        sizeHtml +
        '<p style="font-family:Inter,sans-serif;font-size:12px;color:#859398;line-height:1.6;margin-bottom:20px;">' + message + '</p>' +
        '<div style="display:flex;gap:8px;justify-content:flex-end;">' +
          '<button id="confirm-cancel-btn" style="padding:8px 20px;border-radius:10px;font-family:Space Grotesk,sans-serif;font-size:10px;letter-spacing:0.1em;text-transform:uppercase;cursor:pointer;background:rgba(255,255,255,0.05);color:#859398;border:1px solid rgba(255,255,255,0.1);transition:all 0.2s ease;">' + cancelLabel + '</button>' +
          '<button id="confirm-ok-btn" style="padding:8px 20px;border-radius:10px;font-family:Space Grotesk,sans-serif;font-size:10px;letter-spacing:0.1em;text-transform:uppercase;cursor:pointer;font-weight:600;transition:all 0.2s ease;">' + confirmLabel + '</button>' +
        '</div>';

      overlay.appendChild(card);
      document.body.appendChild(overlay);

      requestAnimationFrame(function () {
        overlay.style.opacity = "1";
        card.style.transform = "scale(1) translateY(0)";
      });

      function close(result) {
        document.removeEventListener("keydown", onKeydown);
        overlay.style.opacity = "0";
        card.style.transform = "scale(0.95) translateY(10px)";
        setTimeout(function () {
          overlay.remove();
          resolve(result);
        }, 250);
      }

      var cancelBtn = overlay.querySelector("#confirm-cancel-btn");
      var okBtn = overlay.querySelector("#confirm-ok-btn");

      okBtn.style.background = confirmVariant === "danger" ? "#ffb4ab" : "#00d4ff";
      okBtn.style.color = confirmVariant === "danger" ? "#690005" : "#003642";
      okBtn.style.border = "none";

      cancelBtn.addEventListener("mouseenter", function () { this.style.background = "rgba(255,255,255,0.1)"; });
      cancelBtn.addEventListener("mouseleave", function () { this.style.background = "rgba(255,255,255,0.05)"; });
      okBtn.addEventListener("mouseenter", function () { this.style.opacity = "0.85"; });
      okBtn.addEventListener("mouseleave", function () { this.style.opacity = "1"; });
      cancelBtn.addEventListener("click", function () { close(false); });
      okBtn.addEventListener("click", function () { close(true); });

      function onKeydown(e) {
        if (e.key === "Escape") { close(false); }
      }
      document.addEventListener("keydown", onKeydown);

      overlay.addEventListener("click", function (e) {
        if (e.target === overlay) close(false);
      });
    });
  };

  // ─── Keyboard Shortcuts System ─────────────────────────────────
  ns.initKeyboardShortcuts = function () {
    var shortcuts = {
      "?": function () { toggleShortcutsOverlay(); },
      "1": function () { window.location.href = "index.html"; },
      "d": function () { window.location.href = "dashboard.html"; },
      "r": function () { window.location.href = "radar.html"; },
      "s": function () { window.location.href = "simulation.html"; },
      "t": function () { window.location.href = "twin.html"; },
      "g": function () { window.location.href = "rag.html"; },
      "e": function () { window.location.href = "rescue.html"; },
      "l": function () { window.location.href = "timeline.html"; },
      "a": function () { window.location.href = "analytics.html"; },
      "ArrowRight": function () {
        if (ns._demoRunning) { ns.nextDemoStep(); }
      },
      "ArrowLeft": function () {
        if (ns._demoRunning) { ns.prevDemoStep(); }
      },
    };

    document.addEventListener("keydown", function (e) {
      if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA" || e.target.isContentEditable) {
        return;
      }
      var handler = shortcuts[e.key];
      if (handler) {
        e.preventDefault();
        handler();
      }
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        if (ns._demoRunning && typeof ns.stopDemo === "function") {
          ns.stopDemo();
        }
        var existing = document.getElementById("shortcuts-overlay");
        if (existing) existing.remove();
      }
    });
  };

  function toggleShortcutsOverlay() {
    var existing = document.getElementById("shortcuts-overlay");
    if (existing) { existing.remove(); return; }

    var overlay = document.createElement("div");
    overlay.id = "shortcuts-overlay";
    overlay.style.cssText =
      "position:fixed;inset:0;z-index:9998;" +
      "background:rgba(5,7,10,0.85);backdrop-filter:blur(20px);" +
      "display:flex;align-items:center;justify-content:center;" +
      "opacity:0;transition:opacity 0.3s ease;";

    var card = document.createElement("div");
    card.style.cssText =
      "background:rgba(17,20,23,0.95);backdrop-filter:blur(40px);" +
      "border:1px solid rgba(255,255,255,0.08);border-radius:24px;" +
      "padding:32px;max-width:440px;width:90%;" +
      "box-shadow:0 0 60px rgba(0,212,255,0.1);" +
      "transform:translateY(20px);transition:transform 0.4s ease;";

    card.innerHTML =
      '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">' +
        '<h2 style="font-family:Space Grotesk,sans-serif;font-size:12px;letter-spacing:0.15em;color:#3cd7ff;text-transform:uppercase;">KEYBOARD SHORTCUTS</h2>' +
        '<button onclick="this.closest(\'#shortcuts-overlay\').remove()" style="background:none;border:none;cursor:pointer;color:#859398;">' +
          '<span class="material-symbols-outlined" style="font-size:18px;">close</span>' +
        '</button>' +
      '</div>' +
      '<div style="display:grid;grid-template-columns:auto 1fr;gap:8px 16px;font-family:Inter,sans-serif;font-size:12px;">' +
        shortcutRow("?", "Toggle keyboard shortcuts") +
        shortcutRow("1", "Landing / Mission Control") +
        shortcutRow("D", "Dashboard") +
        shortcutRow("R", "Threat Radar") +
        shortcutRow("S", "Future Simulation") +
        shortcutRow("T", "Digital Twin") +
        shortcutRow("G", "RAG Engine Dashboard") +
        shortcutRow("E", "AI Rescue Center") +
        shortcutRow("L", "Timeline") +
        shortcutRow("A", "Focus Analytics") +
        '<div style="grid-column:span 2;height:1px;background:rgba(255,255,255,0.05);margin:4px 0;"></div>' +
        shortcutRow("Esc", "Close overlays / Exit demo") +
        '<div style="grid-column:span 2;height:1px;background:rgba(255,255,255,0.05);margin:4px 0;"></div>' +
        '<div style="grid-column:span 2;text-align:center;font-size:10px;color:#3c494e;margin-top:4px;">Keyboard shortcuts require a stable API connection</div>' +
      '</div>';

    overlay.appendChild(card);
    document.body.appendChild(overlay);

    requestAnimationFrame(function () {
      overlay.style.opacity = "1";
      card.style.transform = "translateY(0)";
    });

    overlay.addEventListener("click", function (e) {
      if (e.target === overlay) overlay.remove();
    });
  }

  function shortcutRow(key, desc) {
    return (
      '<div style="display:flex;align-items:center;gap:8px;">' +
        '<kbd style="background:rgba(0,212,255,0.1);border:1px solid rgba(0,212,255,0.2);' +
        'border-radius:6px;padding:4px 10px;font-family:monospace;font-size:11px;' +
        'color:#00d4ff;min-width:32px;text-align:center;text-transform:uppercase;">' +
        key +
        '</kbd>' +
      '</div>' +
      '<div style="display:flex;align-items:center;color:#859398;">' + desc + '</div>'
    );
  }

  // ─── Journey Timeline Breadcrumb ───────────────────────────────
  ns.createJourneyBreadcrumb = function () {
    var currentPage = window.location.pathname.split("/").pop();

    var journey = [
      { label: "Radar", page: "radar.html", icon: "radar", desc: "Detect threats" },
      { label: "Simulate", page: "simulation.html", icon: "assignment_late", desc: "Branch outcomes" },
      { label: "Rescue", page: "rescue.html", icon: "medical_services", desc: "Auto-recover" },
      { label: "Twin", page: "twin.html", icon: "psychology", desc: "Sync profile" },
      { label: "RAG", page: "rag.html", icon: "folder_open", desc: "Vector search" },
      { label: "Timeline", page: "timeline.html", icon: "timeline", desc: "Activity log" },
      { label: "Analytics", page: "analytics.html", icon: "insights", desc: "Focus metrics" },
    ];

    var container = document.createElement("div");
    container.style.cssText =
      "display:flex;align-items:center;gap:4px;margin-bottom:12px;" +
      "padding:8px 12px;background:rgba(255,255,255,0.03);" +
      "border:1px solid rgba(255,255,255,0.05);border-radius:12px;" +
      "font-family:Space Grotesk,sans-serif;overflow-x:auto;";

    journey.forEach(function (item, i) {
      var isCurrent = currentPage === item.page || currentPage === "/" + item.page;

      var step = document.createElement("a");
      step.href = item.page;
      step.style.cssText =
        "display:flex;align-items:center;gap:6px;padding:4px 10px;" +
        "border-radius:8px;text-decoration:none;transition:all 0.3s ease;" +
        "white-space:nowrap;font-size:10px;letter-spacing:0.05em;" +
        (isCurrent
          ? "background:rgba(0,212,255,0.12);color:#00d4ff;border:1px solid rgba(0,212,255,0.2);"
          : "color:#859398;border:1px solid transparent;");

      step.innerHTML =
        '<span class="material-symbols-outlined" style="font-size:14px;">' + item.icon + "</span>" +
        '<span>' + item.label + "</span>";

      step.addEventListener("mouseenter", function () {
        if (!isCurrent) {
          this.style.background = "rgba(255,255,255,0.05)";
          this.style.color = "#e1e2e7";
        }
      });
      step.addEventListener("mouseleave", function () {
        if (!isCurrent) {
          this.style.background = "none";
          this.style.color = "#859398";
        }
      });

      container.appendChild(step);

      if (i < journey.length - 1) {
        var arrow = document.createElement("span");
        arrow.className = "material-symbols-outlined";
        arrow.textContent = "arrow_forward";
        arrow.style.cssText = "font-size:12px;color:#3c494e;margin:0 2px;flex-shrink:0;";
        container.appendChild(arrow);
      }
    });

    return container;
  };

  // ─── AI Status Checker ─────────────────────────────────────────
  ns.checkAIStatus = function () {
    fetch("/api/ai/status")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var existing = document.getElementById("ai-status-badge");
        if (!existing) {
          var badge = document.createElement("div");
          badge.id = "ai-status-badge";
          badge.style.cssText =
            "position:fixed;top:80px;right:16px;z-index:9980;" +
            "display:flex;align-items:center;gap:6px;" +
            "padding:6px 12px;border-radius:20px;" +
            "font-family:Space Grotesk,sans-serif;font-size:8px;" +
            "letter-spacing:0.1em;text-transform:uppercase;" +
            "backdrop-filter:blur(20px);cursor:help;transition:all 0.3s ease;";
          document.body.appendChild(badge);
          existing = badge;
        }

        var color, bg, border, statusText;
        if (data.status === "ready") {
          color = "#00d4ff";
          bg = "rgba(0,212,255,0.1)";
          border = "rgba(0,212,255,0.2)";
          statusText = data.key_configured ? "AI READY" : "AI OFFLINE";
        } else if (data.status === "limited") {
          color = "#d0bcff";
          bg = "rgba(208,188,255,0.1)";
          border = "rgba(208,188,255,0.2)";
          statusText = "AI: RATE LIMITED (" + (data.cooldown_seconds || 0) + "s)";
        } else {
          color = "#859398";
          bg = "rgba(133,147,152,0.1)";
          border = "rgba(133,147,152,0.2)";
          statusText = "AI OFFLINE";
        }

        existing.style.background = bg;
        existing.style.border = "1px solid " + border;
        existing.style.color = color;
        existing.innerHTML =
          '<span style="width:6px;height:6px;border-radius:50%;background:' + color + ";display:inline-block;\"></span> " + statusText;

        existing.title =
          "Gemini AI Status: " + data.status +
          " | Requests/min: " + (data.requests_this_minute || 0) +
          " | Key: " + (data.key_configured ? "\u2713" : "\u2717");
      })
      .catch(function () {});
  };

})(window.FutureShield);
