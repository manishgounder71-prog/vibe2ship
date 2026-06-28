/**
 * FutureShield AI - Focus/Pomodoro Timer
 * Real-time focus session tracker with floating UI, energy rating,
 * and full integration with the Digital Twin backend.
 *
 * Features:
 * - Floating timer button on all pages (bottom-left)
 * - Modal overlay with circular countdown progress
 * - Configurable duration (5-120 min)
 * - Start, stop, pause/resume controls
 * - Post-session energy rating (1-10)
 * - Session history display
 * - Voice Assistant integration
 * - Auto-writes to focus_sessions table via API
 */

(function () {
  "use strict";

  var ns = window.FutureShield = window.FutureShield || {};

  // ─── State ──────────────────────────────────────────────────────
  var state = {
    active: false,
    paused: false,
    duration: 25 * 60,      // default 25 min in seconds
    remaining: 25 * 60,
    startTime: null,
    pauseStartTime: null,
    totalPausedSeconds: 0,
    intervalId: null,
    sessionId: null,
    isModalOpen: false,
    isRatingOpen: false,
  };

  // ─── DOM References ─────────────────────────────────────────────
  var dom = {};

  // ─── Constants ──────────────────────────────────────────────────
  var STORAGE_KEY = "futureshield_focus_state";

  // ─── Create Widget DOM ──────────────────────────────────────────
  function createWidget() {
    // ─── Floating Trigger Button ──────────────────────────────────
    var trigger = document.createElement("button");
    trigger.id = "focus-timer-trigger";
    trigger.setAttribute("aria-label", "Open Focus Timer");
    trigger.innerHTML = `<span class="material-symbols-outlined" style="font-size:22px;">timelapse</span>`;
    trigger.style.cssText =
      "position:fixed;bottom:100px;left:24px;z-index:9997;" +
      "width:48px;height:48px;border-radius:50%;" +
      "background:radial-gradient(circle at 30% 30%, #00d4ff, #00586b);" +
      "border:2px solid rgba(0,212,255,0.4);" +
      "box-shadow:0 0 20px rgba(0,212,255,0.3);" +
      "display:flex;align-items:center;justify-content:center;" +
      "cursor:pointer;transition:all 0.3s ease;color:#fff;" +
      "font-family:'Space Grotesk',sans-serif;";

    // Session indicator dot
    var dot = document.createElement("span");
    dot.id = "focus-timer-dot";
    dot.style.cssText =
      "position:absolute;top:-2px;right:-2px;" +
      "width:14px;height:14px;border-radius:50%;" +
      "background:#00d4ff;border:2px solid #111417;" +
      "display:none;";
    trigger.appendChild(dot);

    // Pulse ring for active sessions
    var pulse = document.createElement("div");
    pulse.id = "focus-trigger-pulse";
    pulse.style.cssText =
      "position:fixed;bottom:124px;left:48px;" +
      "width:0;height:0;border-radius:50%;" +
      "border:1.5px solid rgba(0,212,255,0.4);" +
      "pointer-events:none;z-index:9996;" +
      "opacity:0;transition:none;";
    document.body.appendChild(pulse);
    document.body.appendChild(trigger);

    // Tooltip label
    var tooltip = document.createElement("div");
    tooltip.id = "focus-timer-tooltip";
    tooltip.textContent = "FOCUS TIMER";
    tooltip.style.cssText =
      "position:fixed;bottom:108px;left:80px;z-index:9996;" +
      "font-family:'Space Grotesk',sans-serif;font-size:8px;" +
      "letter-spacing:0.15em;text-transform:uppercase;color:#859398;" +
      "background:rgba(17,20,23,0.8);backdrop-filter:blur(20px);" +
      "padding:4px 10px;border-radius:6px;border:1px solid rgba(255,255,255,0.1);" +
      "white-space:nowrap;pointer-events:none;opacity:0;" +
      "transition:opacity 0.3s ease;";
    document.body.appendChild(tooltip);

    trigger.addEventListener("mouseenter", function () {
      tooltip.style.opacity = "1";
      trigger.style.transform = "scale(1.1)";
    });
    trigger.addEventListener("mouseleave", function () {
      tooltip.style.opacity = "0";
      if (!state.active) trigger.style.transform = "scale(1)";
    });
    trigger.addEventListener("click", function () {
      openModal();
    });

    // ─── Main Modal ───────────────────────────────────────────────
    var overlay = document.createElement("div");
    overlay.id = "focus-timer-overlay";
    overlay.style.cssText =
      "position:fixed;inset:0;z-index:9999;" +
      "background:rgba(5,7,10,0.85);backdrop-filter:blur(30px);" +
      "display:none;align-items:center;justify-content:center;" +
      "opacity:0;transition:opacity 0.4s ease;";

    var modal = document.createElement("div");
    modal.id = "focus-timer-modal";
    modal.style.cssText =
      "background:rgba(17,20,23,0.9);backdrop-filter:blur(60px);" +
      "border:1px solid rgba(255,255,255,0.08);" +
      "border-radius:24px;padding:32px;max-width:420px;width:90%;" +
      "box-shadow:0 0 60px rgba(0,212,255,0.15),inset 0 1px 0 rgba(255,255,255,0.1);" +
      "transform:translateY(20px) scale(0.95);transition:transform 0.4s ease;" +
      "position:relative;overflow:hidden;";

    // Modal header
    var header = document.createElement("div");
    header.style.cssText =
      "display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;";

    var title = document.createElement("h2");
    title.textContent = "FOCUS TIMER";
    title.style.cssText =
      "font-family:'Space Grotesk',sans-serif;font-size:12px;" +
      "letter-spacing:0.15em;color:#3cd7ff;text-transform:uppercase;";

    var closeBtn = document.createElement("button");
    closeBtn.innerHTML = `<span class="material-symbols-outlined" style="font-size:20px;color:#859398;">close</span>`;
    closeBtn.style.cssText =
      "background:none;border:none;cursor:pointer;padding:4px;" +
      "border-radius:8px;transition:all 0.2s;display:flex;align-items:center;justify-content:center;";
    closeBtn.addEventListener("mouseenter", function () { this.style.background = "rgba(255,255,255,0.1)"; });
    closeBtn.addEventListener("mouseleave", function () { this.style.background = "none"; });
    closeBtn.addEventListener("click", closeModal);

    header.appendChild(title);
    header.appendChild(closeBtn);
    modal.appendChild(header);

    // ─── Timer Display (Circular) ─────────────────────────────────
    var timerCircle = document.createElement("div");
    timerCircle.style.cssText =
      "display:flex;flex-direction:column;align-items:center;margin-bottom:24px;";

    var svgContainer = document.createElement("div");
    svgContainer.style.cssText =
      "position:relative;width:200px;height:200px;margin-bottom:16px;";

    var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 200 200");
    svg.setAttribute("width", "200");
    svg.setAttribute("height", "200");
    svg.style.transform = "rotate(-90deg)";

    // Background circle
    var bgCircle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    bgCircle.setAttribute("cx", "100");
    bgCircle.setAttribute("cy", "100");
    bgCircle.setAttribute("r", "85");
    bgCircle.setAttribute("fill", "none");
    bgCircle.setAttribute("stroke", "rgba(255,255,255,0.05)");
    bgCircle.setAttribute("stroke-width", "6");
    svg.appendChild(bgCircle);

    // Progress circle
    var progressCircle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    progressCircle.setAttribute("id", "focus-progress-ring");
    progressCircle.setAttribute("cx", "100");
    progressCircle.setAttribute("cy", "100");
    progressCircle.setAttribute("r", "85");
    progressCircle.setAttribute("fill", "none");
    progressCircle.setAttribute("stroke", "#00d4ff");
    progressCircle.setAttribute("stroke-width", "6");
    progressCircle.setAttribute("stroke-linecap", "round");
    progressCircle.setAttribute("stroke-dasharray", "534");
    progressCircle.setAttribute("stroke-dashoffset", "534");
    progressCircle.style.filter = "drop-shadow(0 0 8px rgba(0,212,255,0.5))";
    progressCircle.style.transition = "stroke-dashoffset 0.5s ease";
    svg.appendChild(progressCircle);

    svgContainer.appendChild(svg);

    // Center time display
    var timeDisplay = document.createElement("div");
    timeDisplay.id = "focus-time-display";
    timeDisplay.textContent = formatTime(state.remaining);
    timeDisplay.style.cssText =
      "position:absolute;inset:0;display:flex;flex-direction:column;" +
      "align-items:center;justify-content:center;";

    var timeValue = document.createElement("span");
    timeValue.id = "focus-time-value";
    timeValue.textContent = formatTime(state.remaining);
    timeValue.style.cssText =
      "font-family:'IBM Plex Sans',sans-serif;font-size:48px;" +
      "font-weight:500;color:#e1e2e7;letter-spacing:-0.03em;" +
      "line-height:1;";

    var timeLabel = document.createElement("span");
    timeLabel.id = "focus-time-label";
    timeLabel.textContent = "FOCUS";
    timeLabel.style.cssText =
      "font-family:'Space Grotesk',sans-serif;font-size:10px;" +
      "letter-spacing:0.15em;color:#859398;margin-top:4px;text-transform:uppercase;";

    timeDisplay.appendChild(timeValue);
    timeDisplay.appendChild(timeLabel);
    svgContainer.appendChild(timeDisplay);
    timerCircle.appendChild(svgContainer);
    modal.appendChild(timerCircle);

    // ─── Session Type / Status Badge ──────────────────────────────
    var statusBadge = document.createElement("div");
    statusBadge.id = "focus-status-badge";
    statusBadge.style.cssText =
      "display:inline-flex;align-items:center;gap:6px;" +
      "font-family:'Space Grotesk',sans-serif;font-size:9px;" +
      "letter-spacing:0.1em;color:#859398;text-transform:uppercase;" +
      "margin-bottom:16px;padding:4px 12px;border-radius:20px;" +
      "border:1px solid rgba(255,255,255,0.06);background:rgba(255,255,255,0.03);";
    statusBadge.innerHTML = `<span class="w-2 h-2 rounded-full bg-primary animate-pulse" style="display:inline-block;"></span> READY`;
    modal.appendChild(statusBadge);

    // ─── Duration Selector ────────────────────────────────────────
    var durationRow = document.createElement("div");
    durationRow.id = "focus-duration-row";
    durationRow.style.cssText =
      "display:flex;gap:8px;margin-bottom:20px;justify-content:center;flex-wrap:wrap;";

    var durations = [5, 15, 25, 45, 60];
    durations.forEach(function (min) {
      var btn = document.createElement("button");
      btn.textContent = min + "m";
      btn.dataset.minutes = min;
      btn.style.cssText =
        "padding:6px 14px;border-radius:12px;font-family:'Space Grotesk',sans-serif;" +
        "font-size:11px;letter-spacing:0.05em;cursor:pointer;" +
        "transition:all 0.2s ease;border:1px solid rgba(255,255,255,0.1);" +
        "background:rgba(255,255,255,0.03);color:#859398;";

      if (min === 25) {
        btn.style.background = "rgba(0,212,255,0.15)";
        btn.style.borderColor = "rgba(0,212,255,0.3)";
        btn.style.color = "#3cd7ff";
      }

      btn.addEventListener("mouseenter", function () {
        this.style.background = "rgba(0,212,255,0.1)";
        this.style.borderColor = "rgba(0,212,255,0.2)";
        this.style.color = "#3cd7ff";
      });
      btn.addEventListener("mouseleave", function () {
        if (!this.classList.contains("active")) {
          this.style.background = "rgba(255,255,255,0.03)";
          this.style.borderColor = "rgba(255,255,255,0.1)";
          this.style.color = "#859398";
        }
      });
      btn.addEventListener("click", function () {
        if (state.active) return;
        // Remove active from all
        durationRow.querySelectorAll("button").forEach(function (b) {
          b.classList.remove("active");
          b.style.background = "rgba(255,255,255,0.03)";
          b.style.borderColor = "rgba(255,255,255,0.1)";
          b.style.color = "#859398";
        });
        this.classList.add("active");
        this.style.background = "rgba(0,212,255,0.15)";
        this.style.borderColor = "rgba(0,212,255,0.3)";
        this.style.color = "#3cd7ff";
        state.duration = parseInt(this.dataset.minutes) * 60;
        state.remaining = state.duration;
        updateTimerDisplay();
      });
      durationRow.appendChild(btn);
    });
    modal.appendChild(durationRow);

    // ─── Control Buttons ──────────────────────────────────────────
    var controls = document.createElement("div");
    controls.style.cssText =
      "display:flex;gap:12px;justify-content:center;margin-bottom:16px;";

    // Start Button
    var startBtn = document.createElement("button");
    startBtn.id = "focus-start-btn";
    startBtn.innerHTML =
      '<span class="material-symbols-outlined" style="font-size:20px;">play_arrow</span> START';
    startBtn.style.cssText =
      "padding:12px 28px;border-radius:14px;font-family:'Space Grotesk',sans-serif;" +
      "font-size:11px;letter-spacing:0.1em;text-transform:uppercase;cursor:pointer;" +
      "transition:all 0.3s ease;border:none;" +
      "background:#00d4ff;color:#003642;font-weight:600;" +
      "box-shadow:0 0 20px rgba(0,212,255,0.3);" +
      "display:flex;align-items:center;gap:8px;";
    startBtn.addEventListener("mouseenter", function () {
      this.style.boxShadow = "0 0 30px rgba(0,212,255,0.5)";
      this.style.transform = "translateY(-1px)";
    });
    startBtn.addEventListener("mouseleave", function () {
      this.style.boxShadow = "0 0 20px rgba(0,212,255,0.3)";
      this.style.transform = "translateY(0)";
    });
    startBtn.addEventListener("click", startTimer);

    // Reset Button
    var resetBtn = document.createElement("button");
    resetBtn.id = "focus-reset-btn";
    resetBtn.innerHTML =
      '<span class="material-symbols-outlined" style="font-size:18px;">refresh</span>';
    resetBtn.style.cssText =
      "padding:12px 16px;border-radius:14px;font-family:'Space Grotesk',sans-serif;" +
      "font-size:11px;letter-spacing:0.1em;text-transform:uppercase;cursor:pointer;" +
      "transition:all 0.3s ease;" +
      "background:rgba(255,255,255,0.05);color:#859398;border:1px solid rgba(255,255,255,0.1);" +
      "display:flex;align-items:center;justify-content:center;";
    resetBtn.addEventListener("click", resetTimer);

    controls.appendChild(startBtn);
    controls.appendChild(resetBtn);
    modal.appendChild(controls);

    // ─── Session Info ─────────────────────────────────────────────
    var sessionInfo = document.createElement("div");
    sessionInfo.id = "focus-session-info";
    sessionInfo.style.cssText =
      "text-align:center;font-family:'Space Grotesk',sans-serif;" +
      "font-size:10px;color:#859398;margin-top:4px;min-height:20px;";
    modal.appendChild(sessionInfo);

    // ─── Recent Sessions (collapsible) ────────────────────────────
    var historySection = document.createElement("div");
    historySection.style.cssText = "margin-top:16px;border-top:1px solid rgba(255,255,255,0.05);padding-top:12px;";

    var historyToggle = document.createElement("button");
    historyToggle.id = "focus-history-toggle";
    historyToggle.textContent = "▼ RECENT SESSIONS";
    historyToggle.style.cssText =
      "width:100%;background:none;border:none;cursor:pointer;" +
      "font-family:'Space Grotesk',sans-serif;font-size:9px;" +
      "letter-spacing:0.1em;color:#859398;text-align:left;padding:4px 0;" +
      "display:flex;justify-content:space-between;align-items:center;";

    var historyContent = document.createElement("div");
    historyContent.id = "focus-history-content";
    historyContent.style.cssText =
      "max-height:0;overflow:hidden;transition:max-height 0.3s ease;";

    var historyList = document.createElement("div");
    historyList.id = "focus-history-list";
    historyList.style.cssText = "margin-top:8px;space-y:4px;";

    historyToggle.addEventListener("click", function () {
      var isOpen = historyContent.style.maxHeight !== "0px" && historyContent.style.maxHeight !== "";
      if (isOpen) {
        historyContent.style.maxHeight = "0";
        historyToggle.textContent = "▶ RECENT SESSIONS";
      } else {
        historyContent.style.maxHeight = "300px";
        historyToggle.textContent = "▼ RECENT SESSIONS";
        fetchSessionHistory();
      }
    });

    historyContent.appendChild(historyList);
    historySection.appendChild(historyToggle);
    historySection.appendChild(historyContent);
    modal.appendChild(historySection);

    overlay.appendChild(modal);
    document.body.appendChild(overlay);

    // Store DOM references
    dom.overlay = overlay;
    dom.modal = modal;
    dom.trigger = trigger;
    dom.dot = dot;
    dom.pulse = pulse;
    dom.tooltip = tooltip;
    dom.timeValue = timeValue;
    dom.timeLabel = timeLabel;
    dom.progressCircle = progressCircle;
    dom.statusBadge = statusBadge;
    dom.startBtn = startBtn;
    dom.resetBtn = resetBtn;
    dom.sessionInfo = sessionInfo;
    dom.durationRow = durationRow;
    dom.historyList = historyList;

    // ─── Energy Rating Modal ──────────────────────────────────────
    createRatingModal();
  }

  // ─── Post-Session Energy Rating Modal ────────────────────────────
  function createRatingModal() {
    var ratingOverlay = document.createElement("div");
    ratingOverlay.id = "focus-rating-overlay";
    ratingOverlay.style.cssText =
      "position:fixed;inset:0;z-index:10000;" +
      "background:rgba(5,7,10,0.9);backdrop-filter:blur(40px);" +
      "display:none;align-items:center;justify-content:center;" +
      "opacity:0;transition:opacity 0.4s ease;";

    var card = document.createElement("div");
    card.id = "focus-rating-card";
    card.style.cssText =
      "background:rgba(17,20,23,0.95);backdrop-filter:blur(60px);" +
      "border:1px solid rgba(255,255,255,0.08);" +
      "border-radius:24px;padding:32px;max-width:360px;width:90%;" +
      "text-align:center;box-shadow:0 0 60px rgba(0,212,255,0.15);" +
      "transform:translateY(20px) scale(0.95);transition:transform 0.4s ease;";

    var icon = document.createElement("div");
    icon.innerHTML = `<span class="material-symbols-outlined" style="font-size:48px;color:#00d4ff;">self_improvement</span>`;
    icon.style.cssText = "margin-bottom:16px;";

    var title = document.createElement("h3");
    title.textContent = "Session Complete!";
    title.style.cssText =
      "font-family:'Space Grotesk',sans-serif;font-size:16px;" +
      "letter-spacing:0.05em;color:#e1e2e7;margin-bottom:8px;";

    var subtitle = document.createElement("p");
    subtitle.id = "focus-rating-subtitle";
    subtitle.textContent = "How was your focus energy?";
    subtitle.style.cssText =
      "font-family:'Inter',sans-serif;font-size:13px;color:#859398;margin-bottom:24px;";

    // Energy rating buttons (1-10)
    var ratingGrid = document.createElement("div");
    ratingGrid.style.cssText =
      "display:flex;gap:6px;justify-content:center;flex-wrap:wrap;margin-bottom:24px;";

    for (var i = 1; i <= 10; i++) {
      var btn = document.createElement("button");
      btn.textContent = i;
      btn.dataset.rating = i;
      btn.style.cssText =
        "width:36px;height:36px;border-radius:50%;font-family:'IBM Plex Sans',sans-serif;" +
        "font-size:14px;font-weight:500;cursor:pointer;transition:all 0.2s ease;" +
        "border:1px solid rgba(255,255,255,0.1);background:rgba(255,255,255,0.03);color:#859398;";

      btn.addEventListener("mouseenter", function () {
        this.style.background = "rgba(0,212,255,0.15)";
        this.style.borderColor = "rgba(0,212,255,0.3)";
        this.style.color = "#3cd7ff";
      });
      btn.addEventListener("mouseleave", function () {
        if (!this.classList.contains("selected")) {
          this.style.background = "rgba(255,255,255,0.03)";
          this.style.borderColor = "rgba(255,255,255,0.1)";
          this.style.color = "#859398";
        }
      });
      btn.addEventListener("click", function () {
        // Remove selected from all
        ratingGrid.querySelectorAll("button").forEach(function (b) {
          b.classList.remove("selected");
          b.style.background = "rgba(255,255,255,0.03)";
          b.style.borderColor = "rgba(255,255,255,0.1)";
          b.style.color = "#859398";
        });
        this.classList.add("selected");
        this.style.background = "rgba(0,212,255,0.25)";
        this.style.borderColor = "rgba(0,212,255,0.5)";
        this.style.color = "#00d4ff";
        this.style.boxShadow = "0 0 12px rgba(0,212,255,0.3)";
      });
      ratingGrid.appendChild(btn);
    }
    card.appendChild(icon);
    card.appendChild(title);
    card.appendChild(subtitle);
    card.appendChild(ratingGrid);

    // Labels
    var labelRow = document.createElement("div");
    labelRow.style.cssText =
      "display:flex;justify-content:space-between;font-family:'Space Grotesk',sans-serif;" +
      "font-size:8px;letter-spacing:0.1em;color:#859398;margin-bottom:20px;";
    labelRow.innerHTML = "<span>Low</span><span>High</span>";
    card.appendChild(labelRow);

    var submitBtn = document.createElement("button");
    submitBtn.id = "focus-rating-submit";
    submitBtn.textContent = "SUBMIT & SAVE TO DIGITAL TWIN";
    submitBtn.style.cssText =
      "width:100%;padding:12px;border-radius:14px;font-family:'Space Grotesk',sans-serif;" +
      "font-size:10px;letter-spacing:0.1em;text-transform:uppercase;cursor:pointer;" +
      "transition:all 0.3s ease;border:none;" +
      "background:#00d4ff;color:#003642;font-weight:600;" +
      "box-shadow:0 0 20px rgba(0,212,255,0.3);";
    submitBtn.addEventListener("mouseenter", function () {
      this.style.boxShadow = "0 0 30px rgba(0,212,255,0.5)";
    });
    submitBtn.addEventListener("mouseleave", function () {
      this.style.boxShadow = "0 0 20px rgba(0,212,255,0.3)";
    });
    submitBtn.addEventListener("click", submitRating);

    card.appendChild(submitBtn);

    var skipBtn = document.createElement("button");
    skipBtn.textContent = "Skip";
    skipBtn.style.cssText =
      "margin-top:12px;background:none;border:none;cursor:pointer;" +
      "font-family:'Space Grotesk',sans-serif;font-size:10px;color:#859398;" +
      "text-transform:uppercase;letter-spacing:0.1em;padding:4px 12px;";
    skipBtn.addEventListener("click", function () {
      // Submit with default rating 5
      submitRatingWithValue(5);
    });
    card.appendChild(skipBtn);

    ratingOverlay.appendChild(card);
    document.body.appendChild(ratingOverlay);

    dom.ratingOverlay = ratingOverlay;
    dom.ratingCard = card;
    dom.ratingGrid = ratingGrid;
  }

  // ─── Holds the session ID for rating submission ────────────────
  var pendingSessionId = null;

  // ─── Timer Logic ────────────────────────────────────────────────
  function startTimer() {
    if (state.active && state.paused) {
      resumeTimer();
      return;
    }
    if (state.active) return;

    state.active = true;
    state.paused = false;
    state.remaining = state.duration;
    state.totalPausedSeconds = 0;

    // Sync with backend
    fetch("/api/focus/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ duration_minutes: Math.round(state.duration / 60), session_type: "focus" })
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data.session) state.sessionId = data.session.id;
    })
    .catch(function (e) { console.error("Focus start error:", e); });

    state.startTime = Date.now();
    updateUIForActive();
    state.intervalId = setInterval(tick, 1000);
    tick();
  }

  function pauseTimer() {
    if (!state.active || state.paused) return;
    state.paused = true;
    state.pauseStartTime = Date.now();
    clearInterval(state.intervalId);
    updateUIForPaused();
  }

  function resumeTimer() {
    if (!state.paused) return;
    state.totalPausedSeconds += (Date.now() - state.pauseStartTime) / 1000;
    state.paused = false;
    state.pauseStartTime = null;
    updateUIForActive();
    state.intervalId = setInterval(tick, 1000);
  }

  function stopTimer(completed) {
    clearInterval(state.intervalId);
    state.intervalId = null;

    // Save session ID before it gets cleared — needed for rating submission
    pendingSessionId = completed ? state.sessionId : null;

    if (completed && state.sessionId) {
      // Don't call API yet — wait for user's energy rating via the modal.
      showRatingModal();
      // Timer stays visually stopped; session remains 'active' in DB
      // until rating is submitted via submitRatingWithValue().
    }
    // Abandoned sessions stay 'active' in DB until auto-closed
    // by the next start_focus_session call.

    state.active = false;
    state.paused = false;
    state.sessionId = null;
    state.remaining = state.duration;
    resetTimerDisplay();
    updateUIForInactive();
    updateTriggerAnimation(false);
  }

  function resetTimer() {
    if (state.active && !state.paused) {
      // If running, stop without completing
      stopTimer(false);
    }
    state.remaining = state.duration;
    state.active = false;
    state.paused = false;
    state.sessionId = null;
    clearInterval(state.intervalId);
    state.intervalId = null;
    resetTimerDisplay();
    updateUIForInactive();
    updateTriggerAnimation(false);
    dom.sessionInfo.textContent = "";
  }

  function tick() {
    if (state.paused) return;
    var elapsed = (Date.now() - state.startTime) / 1000 - state.totalPausedSeconds;
    state.remaining = Math.max(0, state.duration - elapsed);
    updateTimerDisplay();

    if (state.remaining <= 0) {
      stopTimer(true);
    }
  }

  // ─── Rating Submission ───────────────────────────────────────────
  function submitRating() {
    var selected = dom.ratingGrid.querySelector(".selected");
    var rating = selected ? parseInt(selected.dataset.rating) : 5;
    submitRatingWithValue(rating);
  }

  function submitRatingWithValue(rating) {
    hideRatingModal();

    // Update the session with the actual energy rating
    // Use pendingSessionId saved in stopTimer() before sessionId was cleared
    if (pendingSessionId) {
      fetch("/api/focus/stop", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ energy_rating: rating })
      }).catch(function (e) { console.error("Rating update error:", e); });
    }

    // Confetti celebration
    if (typeof confetti !== "undefined") {
      confetti({
        particleCount: 120,
        spread: 70,
        origin: { y: 0.6 },
        colors: ["#00d4ff", "#3cd7ff", "#d0bcff", "#93ecff"]
      });
    }

    pendingSessionId = null;
    state.sessionId = null;
    updateSessionStats();
  }

  // ─── UI Updates ─────────────────────────────────────────────────
  function formatTime(seconds) {
    var m = Math.floor(seconds / 60);
    var s = Math.floor(seconds % 60);
    return (m < 10 ? "0" : "") + m + ":" + (s < 10 ? "0" : "") + s;
  }

  function updateTimerDisplay() {
    if (dom.timeValue) {
      dom.timeValue.textContent = formatTime(state.remaining);
    }
    // Update progress ring
    if (dom.progressCircle) {
      var circumference = 2 * Math.PI * 85; // r=85
      var offset = circumference * (1 - state.remaining / state.duration);
      dom.progressCircle.setAttribute("stroke-dashoffset", circumference - (state.remaining / state.duration) * circumference);
    }
    // Update document title
    if (state.active && !state.paused && state.remaining > 0) {
      document.title = "⏱ " + formatTime(state.remaining) + " - FutureShield AI";
    } else if (!state.active) {
      // Reset title only if it's our timer
      if (document.title.indexOf("⏱") === 0) {
        // Get original title from the page
        var orig = document.querySelector("title");
        if (orig) {
          // Don't override, just set back
        }
      }
    }
  }

  function resetTimerDisplay() {
    if (dom.timeValue) dom.timeValue.textContent = formatTime(state.duration);
    if (dom.progressCircle) {
      dom.progressCircle.setAttribute("stroke-dashoffset", "534");
    }
    if (dom.timeLabel) dom.timeLabel.textContent = "FOCUS";
  }

  function updateUIForActive() {
    dom.startBtn.innerHTML =
      '<span class="material-symbols-outlined" style="font-size:20px;">pause</span> PAUSE';
    dom.startBtn.style.background = "rgba(255,180,171,0.2)";
    dom.startBtn.style.color = "#ffb4ab";
    dom.startBtn.style.boxShadow = "0 0 20px rgba(255,180,171,0.2)";
    dom.startBtn.onclick = pauseTimer;

    dom.statusBadge.innerHTML =
      '<span class="w-2 h-2 rounded-full bg-error animate-pulse" style="display:inline-block;"></span> FOCUS ACTIVE';
    dom.statusBadge.style.borderColor = "rgba(255,180,171,0.2)";
    dom.statusBadge.style.color = "#ffb4ab";

    dom.timeLabel.textContent = "FOCUS";

    dom.durationRow.style.opacity = "0.4";
    dom.durationRow.style.pointerEvents = "none";

    dom.sessionInfo.textContent = "Focus session in progress";
    dom.sessionInfo.style.color = "#00d4ff";

    updateTriggerAnimation(true);
  }

  function updateUIForPaused() {
    dom.startBtn.innerHTML =
      '<span class="material-symbols-outlined" style="font-size:20px;">play_arrow</span> RESUME';
    dom.startBtn.style.background = "rgba(212,188,255,0.2)";
    dom.startBtn.style.color = "#d0bcff";
    dom.startBtn.style.boxShadow = "0 0 20px rgba(212,188,255,0.2)";
    dom.startBtn.onclick = resumeTimer;

    dom.statusBadge.innerHTML =
      '<span class="w-2 h-2 rounded-full bg-secondary animate-pulse" style="display:inline-block;"></span> PAUSED';
    dom.statusBadge.style.borderColor = "rgba(212,188,255,0.2)";
    dom.statusBadge.style.color = "#d0bcff";

    dom.timeLabel.textContent = "PAUSED";
    dom.sessionInfo.textContent = "Session paused";
    dom.sessionInfo.style.color = "#d0bcff";
  }

  function updateUIForInactive() {
    dom.startBtn.innerHTML =
      '<span class="material-symbols-outlined" style="font-size:20px;">play_arrow</span> START';
    dom.startBtn.style.background = "#00d4ff";
    dom.startBtn.style.color = "#003642";
    dom.startBtn.style.boxShadow = "0 0 20px rgba(0,212,255,0.3)";
    dom.startBtn.onclick = startTimer;

    dom.statusBadge.innerHTML =
      '<span class="w-2 h-2 rounded-full bg-primary animate-pulse" style="display:inline-block;"></span> READY';
    dom.statusBadge.style.borderColor = "rgba(255,255,255,0.06)";
    dom.statusBadge.style.color = "#859398";

    dom.timeLabel.textContent = "FOCUS";

    dom.durationRow.style.opacity = "1";
    dom.durationRow.style.pointerEvents = "auto";

    dom.sessionInfo.textContent = "";
  }

  function updateTriggerAnimation(active) {
    if (active) {
      dom.dot.style.display = "block";
      dom.dot.style.background = "#ffb4ab";
      dom.trigger.style.borderColor = "rgba(255,180,171,0.6)";
      dom.trigger.style.boxShadow = "0 0 30px rgba(255,180,171,0.3)";
      dom.tooltip.textContent = "FOCUS ACTIVE";

      // Pulse animation
      var startTime = null;
      function pulseAnim(timestamp) {
        if (!startTime) startTime = timestamp;
        if (!state.active || state.paused) {
          dom.pulse.style.opacity = "0";
          return;
        }
        var progress = ((timestamp - startTime) % 2000) / 2000;
        var scale = 1 + progress * 2;
        var opacity = 1 - progress;
        dom.pulse.style.width = 48 * scale + "px";
        dom.pulse.style.height = 48 * scale + "px";
        dom.pulse.style.bottom = "calc(100px + 24px - " + (48 * (scale - 1)) / 2 + "px)";
        dom.pulse.style.left = "calc(48px - " + (48 * (scale - 1)) / 2 + "px)";
        dom.pulse.style.opacity = Math.max(0, opacity * 0.5);
        requestAnimationFrame(pulseAnim);
      }
      requestAnimationFrame(pulseAnim);
    } else {
      dom.dot.style.display = "none";
      dom.trigger.style.borderColor = "rgba(0,212,255,0.4)";
      dom.trigger.style.boxShadow = "0 0 20px rgba(0,212,255,0.3)";
      dom.pulse.style.opacity = "0";
      dom.tooltip.textContent = "FOCUS TIMER";
    }
  }

  // ─── Modal Control ──────────────────────────────────────────────
  function openModal() {
    dom.isModalOpen = true;
    dom.overlay.style.display = "flex";

    requestAnimationFrame(function () {
      dom.overlay.style.opacity = "1";
      dom.modal.style.transform = "translateY(0) scale(1)";
    });

    // Fetch session stats
    updateSessionStats();
  }

  function closeModal() {
    dom.isModalOpen = false;
    dom.overlay.style.opacity = "0";
    dom.modal.style.transform = "translateY(20px) scale(0.95)";

    setTimeout(function () {
      dom.overlay.style.display = "none";
    }, 400);
  }

  function showRatingModal() {
    dom.isRatingOpen = true;
    dom.ratingOverlay.style.display = "flex";

    // Update subtitle with session duration
    var elapsed = Math.round((state.duration - state.remaining) / 60);
    dom.subtitle = document.getElementById("focus-rating-subtitle");
    if (dom.subtitle) {
      dom.subtitle.textContent = "You focused for " + elapsed + " minutes. How was your energy?";
    }

    // Clear previous selection
    dom.ratingGrid.querySelectorAll("button").forEach(function (b) {
      b.classList.remove("selected");
      b.style.background = "rgba(255,255,255,0.03)";
      b.style.borderColor = "rgba(255,255,255,0.1)";
      b.style.color = "#859398";
    });

    requestAnimationFrame(function () {
      dom.ratingOverlay.style.opacity = "1";
      dom.ratingCard.style.transform = "translateY(0) scale(1)";
    });

    // Auto-select 7 as default (good session)
    var defaultBtn = dom.ratingGrid.querySelector('[data-rating="7"]');
    if (defaultBtn) {
      defaultBtn.classList.add("selected");
      defaultBtn.style.background = "rgba(0,212,255,0.25)";
      defaultBtn.style.borderColor = "rgba(0,212,255,0.5)";
      defaultBtn.style.color = "#00d4ff";
      defaultBtn.style.boxShadow = "0 0 12px rgba(0,212,255,0.3)";
    }
  }

  function hideRatingModal() {
    dom.isRatingOpen = false;
    dom.ratingOverlay.style.opacity = "0";
    dom.ratingCard.style.transform = "translateY(20px) scale(0.95)";

    setTimeout(function () {
      dom.ratingOverlay.style.display = "none";
    }, 400);
  }

  // ─── Session History ────────────────────────────────────────────
  function fetchSessionHistory() {
    fetch("/api/focus/sessions?limit=10")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        renderSessionHistory(data);
      })
      .catch(function (e) { console.error("History fetch error:", e); });
  }

  function renderSessionHistory(data) {
    var list = dom.historyList;
    if (!list) return;
    list.innerHTML = "";

    var sessions = data.sessions || [];
    var stats = data.stats || {};

    // Stats summary
    var statsEl = document.createElement("div");
    statsEl.style.cssText =
      "display:flex;justify-content:space-around;margin-bottom:12px;" +
      "padding:8px;background:rgba(255,255,255,0.03);border-radius:8px;";

    var statItems = [
      { label: "Sessions", value: stats.total_sessions || 0 },
      { label: "Total Min", value: stats.total_focus_minutes || 0 },
      { label: "Avg Energy", value: stats.average_energy_rating || "—" },
    ];
    statItems.forEach(function (item) {
      var el = document.createElement("div");
      el.style.cssText = "text-align:center;";
      el.innerHTML =
        '<div style="font-size:14px;font-weight:600;color:#e1e2e7;">' + item.value + '</div>' +
        '<div style="font-size:7px;color:#859398;letter-spacing:0.1em;text-transform:uppercase;">' + item.label + '</div>';
      statsEl.appendChild(el);
    });
    list.appendChild(statsEl);

    if (sessions.length === 0) {
      var empty = document.createElement("div");
      empty.style.cssText = "text-align:center;padding:16px;color:#859398;font-size:10px;";
      empty.textContent = "No completed sessions yet. Start your first focus session!";
      list.appendChild(empty);
      return;
    }

    sessions.slice(0, 5).forEach(function (s) {
      if (s.status !== "completed") return;
      var el = document.createElement("div");
      el.style.cssText =
        "display:flex;justify-content:space-between;align-items:center;" +
        "padding:6px 8px;border-radius:8px;background:rgba(255,255,255,0.02);" +
        "margin-bottom:4px;font-size:10px;";

      var duration = s.actual_duration_seconds
        ? Math.round(s.actual_duration_seconds / 60) + "m"
        : s.duration_minutes + "m";

      // Energy stars
      var rating = s.energy_rating || "—";
      var ratingColor = rating >= 7 ? "#00d4ff" : rating >= 4 ? "#d0bcff" : "#ffb4ab";

      el.innerHTML =
        '<span style="color:#859398;">' + duration + '</span>' +
        '<span style="color:#e1e2e7;">' + (s.session_type || "focus") + '</span>' +
        '<span style="color:' + ratingColor + ';">' + rating + '/10</span>';

      list.appendChild(el);
    });
  }

  function updateSessionStats() {
    fetch("/api/focus/sessions?limit=1")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var stats = data.stats || {};
        if (stats.total_sessions > 0 && dom.sessionInfo && !state.active) {
          dom.sessionInfo.textContent =
            stats.total_sessions + " sessions · " + stats.total_focus_minutes + " total min · " +
            (stats.average_energy_rating || "—") + " avg energy";
          dom.sessionInfo.style.color = "#859398";
        }
      })
      .catch(function () {});
  }

  // ─── Click-outside handling ─────────────────────────────────────
  function handleOverlayClick(e) {
    if (e.target === dom.overlay) {
      closeModal();
    }
    if (e.target === dom.ratingOverlay) {
      // Don't close rating modal on click outside
    }
  }

  // ─── Keyboard shortcuts ─────────────────────────────────────────
  function handleKeydown(e) {
    // Escape closes modals
    if (e.key === "Escape") {
      if (dom.isRatingOpen) {
        submitRatingWithValue(5);
      } else if (dom.isModalOpen) {
        closeModal();
      }
    }
    // Space toggles timer when modal is open
    if (e.key === " " && dom.isModalOpen) {
      e.preventDefault();
      if (state.active && !state.paused) {
        pauseTimer();
      } else if (state.paused) {
        resumeTimer();
      } else if (!state.active) {
        startTimer();
      }
    }
  }

  // ─── Voice Assistant Integration ────────────────────────────────
  // Commands the voice assistant can use
  ns.startFocusTimer = function (minutes) {
    if (minutes) {
      state.duration = minutes * 60;
      state.remaining = state.duration;
    }
    openModal();
    setTimeout(startTimer, 300);
  };

  ns.stopFocusTimer = function () {
    if (state.active) {
      stopTimer(false);
    }
  };

  ns.getFocusState = function () {
    return {
      active: state.active,
      paused: state.paused,
      remaining: state.remaining,
      duration: state.duration
    };
  };

  // ─── Init ───────────────────────────────────────────────────────
  function init() {
    createWidget();

    // Event listeners
    dom.overlay.addEventListener("click", handleOverlayClick);
    document.addEventListener("keydown", handleKeydown);

    // Check if there's an active session on page load
    fetch("/api/focus/current")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.active && data.session) {
          // Restore timer state from server
          var startTime = new Date(data.session.start_time).getTime();
          var elapsed = (Date.now() - startTime) / 1000;
          state.duration = data.session.duration_minutes * 60;
          state.remaining = Math.max(0, state.duration - elapsed);
          state.sessionId = data.session.id;
          state.active = true;
          state.startTime = Date.now() - elapsed * 1000;
          state.totalPausedSeconds = 0;

          updateTimerDisplay();
          updateUIForActive();
          updateTriggerAnimation(true);

          if (state.remaining > 0) {
            state.intervalId = setInterval(tick, 1000);
          } else {
            stopTimer(true);
          }
        }
      })
      .catch(function () {});

    // Expose focus timer namespace
    ns.focusTimer = {
      start: function (m) { ns.startFocusTimer(m); },
      stop: function () { ns.stopFocusTimer(); },
      getState: function () { return ns.getFocusState(); },
      openModal: openModal,
      closeModal: closeModal,
    };

    // Override voice assistant commands for focus
    // Intercept the voice assistant's command list
    var originalProcessCommand = window.processVoiceCommand;
    if (typeof window.processVoiceCommand === "function") {
      // Already set up by voice-assistant.js — we'll add commands later
    }

    console.log("[FocusTimer] Initialized");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

})();
