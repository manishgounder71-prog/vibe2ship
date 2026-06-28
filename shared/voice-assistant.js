/**
 * FutureShield AI - Voice Pilot Assistant
 * Floating pulsing orb with Web Speech API speech recognition & synthesis.
 * Commands: "start focus", "what is next", "show dashboard", "show radar", "show twin", "show rescue", "stop listening"
 */
(function () {
  "use strict";

  // ─── State ──────────────────────────────────────────────────────
  var isListening = false;
  var isSpeaking = false;
  var recognition = null;
  var synth = window.speechSynthesis;
  var orbEl = null;
  var pulseInterval = null;

  // ─── DOM Creation ───────────────────────────────────────────────
  function createOrb() {
    // Container
    var container = document.createElement("div");
    container.id = "voice-assistant";
    container.style.cssText =
      "position:fixed;bottom:100px;right:24px;z-index:9999;cursor:pointer;" +
      "display:flex;flex-direction:column;align-items:center;gap:8px;";

    // Orb
    orbEl = document.createElement("div");
    orbEl.id = "voice-orb";
    orbEl.style.cssText =
      "width:56px;height:56px;border-radius:50%;" +
      "background:radial-gradient(circle at 30% 30%, #00d4ff, #571bc1);" +
      "box-shadow:0 0 30px rgba(0,212,255,0.4), inset 0 0 15px rgba(255,255,255,0.3);" +
      "display:flex;align-items:center;justify-content:center;" +
      "transition:all 0.3s ease;position:relative;";

    // Inner icon
    var icon = document.createElement("span");
    icon.className = "material-symbols-outlined";
    icon.textContent = "mic";
    icon.style.cssText =
      "color:#003642;font-size:24px;transition:all 0.3s ease;";
    orbEl.appendChild(icon);

    // Status text
    var status = document.createElement("div");
    status.id = "voice-status";
    status.textContent = "TAP TO ACTIVATE";
    status.style.cssText =
      "font-family:'Space Grotesk',sans-serif;font-size:8px;" +
      "letter-spacing:0.15em;text-transform:uppercase;color:#859398;" +
      "text-align:center;white-space:nowrap;transition:all 0.3s ease;";

    container.appendChild(orbEl);
    container.appendChild(status);
    document.body.appendChild(container);

    // Pulse ring (behind)
    var pulse = document.createElement("div");
    pulse.id = "voice-pulse";
    pulse.style.cssText =
      "position:fixed;bottom:calc(100px + 28px);right:calc(24px + 28px);" +
      "width:0;height:0;border-radius:50%;" +
      "border:1.5px solid rgba(0,212,255,0.5);" +
      "transform:translate(-50%,-50%);" +
      "pointer-events:none;z-index:9998;" +
      "opacity:0;transition:all 0.5s ease;";
    document.body.appendChild(pulse);

    // Events
    container.addEventListener("click", toggleListening);
    container.addEventListener("mouseenter", function () {
      orbEl.style.transform = "scale(1.1)";
    });
    container.addEventListener("mouseleave", function () {
      if (!isListening) orbEl.style.transform = "scale(1)";
    });

    return container;
  }

  // ─── Speech Recognition Setup ───────────────────────────────────
  function setupRecognition() {
    var SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setStatus("VOICE NOT SUPPORTED");
      return false;
    }

    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = "en-US";

    recognition.onresult = function (event) {
      for (var i = event.resultIndex; i < event.results.length; i++) {
        if (event.results[i].isFinal) {
          var transcript = event.results[i][0].transcript.trim().toLowerCase();
          processCommand(transcript);
        }
      }
    };

    recognition.onerror = function (event) {
      console.warn("Voice recognition error:", event.error);
      if (event.error === "no-speech") return;
      stopListening();
    };

    recognition.onend = function () {
      // Auto-restart if we're still supposed to be listening
      if (isListening) {
        try {
          recognition.start();
        } catch (e) {
          // ignore
        }
      }
    };

    return true;
  }

  // ─── Commands ───────────────────────────────────────────────────
  var commands = {
    "start focus": function () {
      if (window.FutureShield && window.FutureShield.focusTimer) {
        window.FutureShield.focusTimer.start(25);
        speak("Initiating 25 minute focus protocol. Deep work block activated.");
        setStatus("FOCUS MODE");
        if (orbEl) orbEl.style.boxShadow = "0 0 50px rgba(0,212,255,0.7), inset 0 0 20px rgba(255,255,255,0.4)";
      } else {
        speak("Focus timer not yet loaded. Please wait a moment.");
      }
    },
    "start 5 minute focus": function () {
      if (window.FutureShield && window.FutureShield.focusTimer) {
        window.FutureShield.focusTimer.start(5);
        speak("Starting a 5 minute quick focus session.");
        setStatus("QUICK FOCUS");
        if (orbEl) orbEl.style.boxShadow = "0 0 50px rgba(0,212,255,0.7), inset 0 0 20px rgba(255,255,255,0.4)";
      }
    },
    "stop focus": function () {
      if (window.FutureShield && window.FutureShield.focusTimer) {
        window.FutureShield.focusTimer.stop();
        speak("Focus session ended.");
        setStatus("FOCUS ENDED");
        if (orbEl) orbEl.style.boxShadow = "0 0 30px rgba(0,212,255,0.4), inset 0 0 15px rgba(255,255,255,0.3)";
      }
    },
    "what is next": function () {
      var goals = document.querySelectorAll("#goals-list-container .text-sm");
      if (goals && goals.length > 0) {
        var nextGoal = goals[0].textContent;
        speak("Your next priority is: " + nextGoal);
      } else {
        speak("No active goals detected. Decompose a new goal from the dashboard.");
      }
    },
    "show dashboard": function () {
      speak("Navigating to command center.");
      window.location.href = "dashboard.html";
    },
    "show radar": function () {
      speak("Opening threat radar.");
      window.location.href = "radar.html";
    },
    "show simulation": function () {
      speak("Launching future simulation lab.");
      window.location.href = "simulation.html";
    },
    "show twin": function () {
      speak("Accessing digital twin neural link.");
      window.location.href = "twin.html";
    },
    "show rescue": function () {
      speak("Initiating AI rescue center.");
      window.location.href = "rescue.html";
    },
    "stop listening": function () {
      speak("Voice assistant deactivated.");
      stopListening();
    },
    "show summary": function () {
      speak("Generating productivity summary.");
      // If we're already on the dashboard, trigger the summary button
      var summaryBtn = document.getElementById("summary-btn");
      if (summaryBtn) {
        summaryBtn.click();
      } else {
        // Navigate to dashboard and the summary auto-generates
        window.location.href = "dashboard.html";
      }
    },
    "help": function () {
      speak("Available commands: start focus, what is next, show dashboard, show radar, show simulation, show twin, show rescue, show summary, stop listening, and help.");
    }
  };

  function processCommand(transcript) {
    console.log("[Voice] Heard:", transcript);
    setStatus('"' + transcript + '"');

    // Check for known commands
    for (var key in commands) {
      if (transcript.indexOf(key) !== -1) {
        commands[key]();
        return;
      }
    }

    // Fuzzy match
    if (transcript.indexOf("dash") !== -1) commands["show dashboard"]();
    else if (transcript.indexOf("radar") !== -1 || transcript.indexOf("threat") !== -1) commands["show radar"]();
    else if (transcript.indexOf("sim") !== -1) commands["show simulation"]();
    else if (transcript.indexOf("twin") !== -1 || transcript.indexOf("neural") !== -1) commands["show twin"]();
    else if (transcript.indexOf("rescue") !== -1 || transcript.indexOf("help") !== -1) commands["show rescue"]();
    else if (transcript.indexOf("summary") !== -1 || transcript.indexOf("insight") !== -1 || transcript.indexOf("report") !== -1 || transcript.indexOf("analyze") !== -1) commands["show summary"]();
    else if (transcript.indexOf("focus") !== -1 || transcript.indexOf("deep") !== -1) {
      if (transcript.indexOf("stop") !== -1 || transcript.indexOf("end") !== -1 || transcript.indexOf("cancel") !== -1) {
        commands["stop focus"]();
      } else if (transcript.indexOf("5") !== -1 || transcript.indexOf("quick") !== -1) {
        commands["start 5 minute focus"]();
      } else {
        commands["start focus"]();
      }
    }
    else if (transcript.indexOf("next") !== -1 || transcript.indexOf("priority") !== -1) commands["what is next"]();
    else {
      speak("Command not recognized. Say help for available commands.");
    }
  }

  // ─── Speech Synthesis ───────────────────────────────────────────
  function speak(text) {
    if (!synth) return;
    synth.cancel();
    var utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.1;
    utterance.pitch = 0.9;
    utterance.voice = synth.getVoices().filter(function (v) {
      return v.name.indexOf("Google UK") !== -1 || v.name.indexOf("Female") !== -1;
    })[0] || null;
    isSpeaking = true;
    utterance.onend = function () {
      isSpeaking = false;
    };
    synth.speak(utterance);
  }

  // ─── Toggle ─────────────────────────────────────────────────────
  function toggleListening() {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  }

  function startListening() {
    if (!recognition && !setupRecognition()) return;
    if (!recognition) return;

    try {
      recognition.start();
      isListening = true;
      setStatus("LISTENING...");
      if (orbEl) {
        orbEl.style.transform = "scale(1.15)";
        orbEl.style.boxShadow = "0 0 50px rgba(0,212,255,0.7), 0 0 100px rgba(87,27,193,0.4), inset 0 0 20px rgba(255,255,255,0.4)";
        var icon = orbEl.querySelector(".material-symbols-outlined");
        if (icon) {
          icon.textContent = "mic_off";
          icon.style.color = "#ffb4ab";
        }
      }
      // Pulse animation
      animatePulse(true);
    } catch (e) {
      console.warn("Voice start error:", e);
    }
  }

  function stopListening() {
    if (recognition) {
      try {
        recognition.stop();
      } catch (e) { /* ignore */ }
    }
    isListening = false;
    setStatus("TAP TO ACTIVATE");
    if (orbEl) {
      orbEl.style.transform = "scale(1)";
      orbEl.style.boxShadow = "0 0 30px rgba(0,212,255,0.4), inset 0 0 15px rgba(255,255,255,0.3)";
      var icon = orbEl.querySelector(".material-symbols-outlined");
      if (icon) {
        icon.textContent = "mic";
        icon.style.color = "#003642";
      }
    }
    animatePulse(false);
  }

  function animatePulse(active) {
    var pulse = document.getElementById("voice-pulse");
    if (!pulse) return;
    if (active) {
      pulse.style.opacity = "1";
      pulse.style.transition = "none";
      pulse.style.width = "56px";
      pulse.style.height = "56px";
      pulse.style.bottom = "calc(100px + 28px)";
      pulse.style.right = "calc(24px + 28px)";

      var startTime = null;
      function pulseAnim(timestamp) {
        if (!startTime) startTime = timestamp;
        if (!isListening) {
          pulse.style.opacity = "0";
          return;
        }
        var progress = ((timestamp - startTime) % 2000) / 2000;
        var scale = 1 + progress * 2.5;
        var opacity = 1 - progress;
        pulse.style.width = 56 * scale + "px";
        pulse.style.height = 56 * scale + "px";
        pulse.style.bottom = "calc(100px + 28px - " + (56 * (scale - 1)) / 2 + "px)";
        pulse.style.right = "calc(24px + 28px - " + (56 * (scale - 1)) / 2 + "px)";
        pulse.style.opacity = Math.max(0, opacity * 0.6);
        requestAnimationFrame(pulseAnim);
      }
      requestAnimationFrame(pulseAnim);
    } else {
      pulse.style.opacity = "0";
    }
  }

  // ─── Status Display ─────────────────────────────────────────────
  function setStatus(text) {
    var el = document.getElementById("voice-status");
    if (el) el.textContent = text;
  }

  // ─── Init ───────────────────────────────────────────────────────
  function init() {
    // Check for browser support
    if (!("webkitSpeechRecognition" in window) && !("SpeechRecognition" in window)) {
      // Create disabled orb anyway for aesthetic
      createOrb();
      setStatus("VOICE UNAVAILABLE");
      if (orbEl) orbEl.style.opacity = "0.4";
      return;
    }

    createOrb();
    setupRecognition();

    // Warm up speech synthesis (needs user gesture on some browsers)
    document.addEventListener("click", function warmUp() {
      if (synth) {
        synth.getVoices();
      }
    }, { once: true });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
