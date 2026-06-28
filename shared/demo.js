/**
 * FutureShield AI - Guided Demo Mode
 *
 * 5-step guided tour that seeds demo data and walks users through
 * each feature page with an animated overlay, progress tracking,
 * and keyboard navigation.
 *
 * Depends on window.FutureShield namespace (loaded by fs-shared.js)
 * and ui.js (for toast/confirmDialog).
 */
(function (ns) {
  "use strict";

  // ─── Demo Steps ────────────────────────────────────────────────
  var demoSteps = [
    {
      title: "Step 1: Command Center",
      page: "dashboard.html",
      icon: "dashboard",
      description:
        "Your Mission Control. View real-time success metrics, " +
        "track goal progress, and generate AI-powered productivity summaries. " +
        "The radar centerpiece scans for anomalies across all active projects.",
    },
    {
      title: "Step 2: Threat Radar",
      page: "radar.html",
      icon: "radar",
      description:
        "Real-time threat detection. Each blip represents a risk to your " +
        "deadlines. Critical threats are flagged in red, warnings in purple. " +
        "Hover any blip to inspect — resolve them before they cascade.",
    },
    {
      title: "Step 3: Future Simulation",
      page: "simulation.html",
      icon: "assignment_late",
      description:
        "Test the consequences of your decisions before making them. " +
        "Type 'Skip today's work block' and see three branching timelines " +
        "projected by the AI — from optimal to worst-case rescue intervention.",
    },
    {
      title: "Step 4: Digital Twin",
      page: "twin.html",
      icon: "psychology",
      description:
        "Your holographic behavioral clone. Tracks energy waveforms, " +
        "focus patterns, neural drift, and Success DNA. See your cognitive " +
        "performance mapped in real-time.",
    },
    {
      title: "Step 5: AI Rescue",
      page: "rescue.html",
      icon: "medical_services",
      description:
        "The final safety net. When deadlines are at critical risk, " +
        "the AI Commander launches autonomous rescue missions — generating " +
        "code, documents, and recovery plans. Watch the typing animation " +
        "as AI-generated assets stream into the editor.",
    },
  ];

  var currentDemoStep = 0;
  ns._demoRunning = false;

  // ─── Public API ─────────────────────────────────────────────────
  ns.startDemo = function () {
    currentDemoStep = 0;
    ns._demoRunning = true;

    fetch("/api/demo/seed", { method: "POST" })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        console.log("[Demo] Seeded:", data.status);
        showDemoOverlay();
        navigateToStep(0);
      })
      .catch(function (e) {
        console.error("[Demo] Seed failed:", e);
        showDemoOverlay();
        navigateToStep(0);
      });
  };

  ns.stopDemo = function () {
    ns._demoRunning = false;
    currentDemoStep = 0;
    var overlay = document.getElementById("demo-overlay");
    if (overlay) {
      overlay.style.opacity = "0";
      setTimeout(function () {
        overlay.remove();
      }, 400);
    }
  };

  ns.nextDemoStep = function () {
    if (currentDemoStep < demoSteps.length - 1) {
      currentDemoStep++;
      navigateToStep(currentDemoStep);
    } else {
      showDemoComplete();
    }
  };

  ns.prevDemoStep = function () {
    if (currentDemoStep > 0) {
      currentDemoStep--;
      navigateToStep(currentDemoStep);
    }
  };

  // ─── Landing Page CTA Button ────────────────────────────────────
  ns.addDemoCTA = function () {
    if (document.getElementById("demo-cta-btn")) return;

    var ctaContainer = document.createElement("div");
    ctaContainer.id = "demo-cta-btn";
    ctaContainer.style.cssText =
      "position:fixed;bottom:180px;right:24px;z-index:9996;" +
      "display:flex;flex-direction:column;align-items:center;gap:8px;";

    var tooltip = document.createElement("div");
    tooltip.textContent = "TAKE A GUIDED TOUR";
    tooltip.style.cssText =
      "font-family:Space Grotesk,sans-serif;font-size:8px;" +
      "letter-spacing:0.15em;text-transform:uppercase;" +
      "color:#3cd7ff;text-align:center;white-space:nowrap;" +
      "background:rgba(17,20,23,0.8);backdrop-filter:blur(10px);" +
      "padding:4px 10px;border-radius:6px;border:1px solid rgba(60,215,255,0.2);";

    var btn = document.createElement("button");
    btn.style.cssText =
      "width:64px;height:64px;border-radius:50%;border:none;cursor:pointer;" +
      "background:radial-gradient(circle at 30% 30%, #00d4ff, #571bc1);" +
      "box-shadow:0 0 30px rgba(0,212,255,0.5), inset 0 0 20px rgba(255,255,255,0.3);" +
      "display:flex;align-items:center;justify-content:center;" +
      "transition:all 0.3s ease;position:relative;";
    btn.style.animation = "demoCtaPulse 2s ease-in-out infinite";
    btn.innerHTML =
      '<span class="material-symbols-outlined" style="color:#003642;font-size:28px;">play_circle</span>';

    // Inject pulse keyframe
    if (!document.getElementById("demo-cta-style")) {
      var s = document.createElement("style");
      s.id = "demo-cta-style";
      s.textContent =
        "@keyframes demoCtaPulse { 0%,100% { transform:scale(1);box-shadow:0 0 30px rgba(0,212,255,0.5); } 50% { transform:scale(1.08);box-shadow:0 0 50px rgba(0,212,255,0.8); } }";
      document.head.appendChild(s);
    }

    btn.addEventListener("mouseenter", function () {
      this.style.transform = "scale(1.15)";
      this.style.boxShadow = "0 0 60px rgba(0,212,255,0.7), inset 0 0 30px rgba(255,255,255,0.4)";
    });
    btn.addEventListener("mouseleave", function () {
      this.style.transform = "scale(1)";
      this.style.boxShadow = "0 0 30px rgba(0,212,255,0.5), inset 0 0 20px rgba(255,255,255,0.3)";
    });
    btn.addEventListener("click", function () {
      ctaContainer.remove();
      var voiceOrb = document.getElementById("voice-assistant");
      if (voiceOrb) voiceOrb.style.display = "none";
      var focusBtn = document.getElementById("focus-timer-trigger");
      if (focusBtn) focusBtn.style.display = "none";
      ns.startDemo();
    });

    ctaContainer.appendChild(tooltip);
    ctaContainer.appendChild(btn);
    document.body.appendChild(ctaContainer);
  };

  // ─── Internal Helpers ───────────────────────────────────────────

  function navigateToStep(stepIndex) {
    var step = demoSteps[stepIndex];
    if (!step) return;

    var titleEl = document.getElementById("demo-step-title");
    var descEl = document.getElementById("demo-step-desc");
    var progressEl = document.getElementById("demo-step-progress");
    var stepNumEl = document.getElementById("demo-step-number");

    if (titleEl) titleEl.textContent = step.title;
    if (descEl) descEl.textContent = step.description;
    if (stepNumEl) stepNumEl.textContent = "Step " + (stepIndex + 1) + " of " + demoSteps.length;
    if (progressEl) {
      progressEl.style.width = ((stepIndex + 1) / demoSteps.length * 100) + "%";
    }

    var prevBtn = document.getElementById("demo-prev-btn");
    var nextBtn = document.getElementById("demo-next-btn");
    if (prevBtn) {
      prevBtn.style.display = stepIndex === 0 ? "none" : "flex";
    }
    if (nextBtn) {
      if (stepIndex === demoSteps.length - 1) {
        nextBtn.innerHTML =
          '<span class="material-symbols-outlined" style="font-size:16px;">check_circle</span> COMPLETE TOUR';
      } else {
        nextBtn.innerHTML =
          'NEXT STEP <span class="material-symbols-outlined" style="font-size:16px;">arrow_forward</span>';
      }
    }

    var currentPath = window.location.pathname.split("/").pop();
    if (currentPath !== step.page && currentPath !== "/" + step.page) {
      window.location.href = step.page;
    }
  }

  function showDemoOverlay() {
    if (document.getElementById("demo-overlay")) return;

    var overlay = document.createElement("div");
    overlay.id = "demo-overlay";
    overlay.style.cssText =
      "position:fixed;bottom:80px;left:50%;transform:translateX(-50%);z-index:9995;" +
      "width:90%;max-width:560px;background:rgba(17,20,23,0.95);backdrop-filter:blur(40px);" +
      "border:1px solid rgba(60,215,255,0.3);border-radius:20px;padding:20px 24px;" +
      "box-shadow:0 0 40px rgba(0,212,255,0.2);transition:all 0.4s ease;";

    // Inject slide-up keyframe
    if (!document.getElementById("demo-anim-style")) {
      var style = document.createElement("style");
      style.id = "demo-anim-style";
      style.textContent =
        "@keyframes demoSlideUp { from { opacity:0; transform:translateX(-50%) translateY(20px); } to { opacity:1; transform:translateX(-50%) translateY(0); } }";
      document.head.appendChild(style);
    }
    overlay.style.animation = "demoSlideUp 0.5s ease";

    overlay.innerHTML =
      '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">' +
        '<div style="display:flex;align-items:center;gap:8px;">' +
          '<span class="material-symbols-outlined" style="color:#00d4ff;font-size:20px;">tour</span>' +
          '<span id="demo-step-number" style="font-family:Space Grotesk,sans-serif;font-size:10px;letter-spacing:0.1em;color:#859398;text-transform:uppercase;">Step 1 of 5</span>' +
        '</div>' +
        '<button onclick="FutureShield.stopDemo()" style="background:none;border:none;cursor:pointer;color:#859398;padding:4px;">' +
          '<span class="material-symbols-outlined" style="font-size:18px;">close</span>' +
        '</button>' +
      '</div>' +
      '<div style="margin-bottom:12px;">' +
        '<div style="height:3px;background:rgba(255,255,255,0.06);border-radius:4px;overflow:hidden;">' +
          '<div id="demo-step-progress" style="height:100%;width:20%;background:linear-gradient(90deg,#00d4ff,#571bc1);border-radius:4px;transition:width 0.5s ease;"></div>' +
        '</div>' +
      '</div>' +
      '<h3 id="demo-step-title" style="font-family:Space Grotesk,sans-serif;font-size:14px;color:#e1e2e7;margin-bottom:8px;">Loading...</h3>' +
      '<p id="demo-step-desc" style="font-family:Inter,sans-serif;font-size:12px;color:#859398;line-height:1.6;margin-bottom:16px;"></p>' +
      '<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;">' +
        '<button id="demo-prev-btn" onclick="FutureShield.prevDemoStep()" style="display:none;padding:8px 16px;border-radius:10px;font-family:Space Grotesk,sans-serif;font-size:10px;letter-spacing:0.1em;text-transform:uppercase;cursor:pointer;background:rgba(255,255,255,0.05);color:#859398;border:1px solid rgba(255,255,255,0.1);align-items:center;gap:4px;">' +
          '<span class="material-symbols-outlined" style="font-size:14px;">arrow_back</span> BACK' +
        '</button>' +
        '<button id="demo-next-btn" onclick="FutureShield.nextDemoStep()" style="padding:8px 20px;border-radius:10px;font-family:Space Grotesk,sans-serif;font-size:10px;letter-spacing:0.1em;text-transform:uppercase;cursor:pointer;font-weight:600;background:#00d4ff;color:#003642;border:none;display:flex;align-items:center;gap:4px;">' +
          'NEXT STEP <span class="material-symbols-outlined" style="font-size:14px;">arrow_forward</span>' +
        '</button>' +
      '</div>' +
      '<div style="margin-top:12px;text-align:center;">' +
        '<span style="font-family:Space Grotesk,sans-serif;font-size:8px;color:#3c494e;letter-spacing:0.05em;">Press <kbd style="background:rgba(255,255,255,0.08);padding:1px 6px;border-radius:4px;font-family:monospace;font-size:9px;">\u2192</kbd> to advance \u00B7 <kbd style="background:rgba(255,255,255,0.08);padding:1px 6px;border-radius:4px;font-family:monospace;font-size:9px;">\u2190</kbd> to go back \u00B7 <kbd style="background:rgba(255,255,255,0.08);padding:1px 6px;border-radius:4px;font-family:monospace;font-size:9px;">Esc</kbd> to exit</span>' +
      '</div>';

    document.body.appendChild(overlay);
  }

  function showDemoComplete() {
    var titleEl = document.getElementById("demo-step-title");
    var descEl = document.getElementById("demo-step-desc");
    var stepNumEl = document.getElementById("demo-step-number");
    var progressEl = document.getElementById("demo-step-progress");
    var nextBtn = document.getElementById("demo-next-btn");

    if (titleEl) titleEl.textContent = "\uD83C\uDF89 Tour Complete \u2014 You're Ready!";
    if (descEl) {
      descEl.innerHTML =
        "You've seen the full Failure Prevention lifecycle. FutureShield AI will now " +
        "monitor your goals, detect threats, simulate outcomes, and launch rescues " +
        "automatically. <strong style='color:#3cd7ff;'>Your system is fully operational.</strong>";
    }
    if (stepNumEl) stepNumEl.textContent = "MISSION READY";
    if (progressEl) progressEl.style.width = "100%";
    if (nextBtn) {
      nextBtn.innerHTML =
        '<span class="material-symbols-outlined" style="font-size:16px;">rocket_launch</span> START USING FUTURESHIELD';
      nextBtn.onclick = function () {
        ns.stopDemo();
        window.location.href = "dashboard.html";
      };
    }

    if (typeof confetti !== "undefined") {
      confetti({
        particleCount: 200,
        spread: 100,
        origin: { y: 0.4 },
        colors: ["#00d4ff", "#3cd7ff", "#d0bcff", "#93ecff"],
      });
    }
  }

})(window.FutureShield);
