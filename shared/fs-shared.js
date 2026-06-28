/**
 * FutureShield AI - Core Shared Utilities
 *
 * Provides the base namespace, WebGL shader, skeleton loader, parallax,
 * animated counter, and the master init() that wires up all modules.
 *
 * Must be loaded first — other modules (auth.js, ui.js, demo.js) attach
 * to the window.FutureShield namespace created here.
 */
window.FutureShield = window.FutureShield || {};

(function (ns) {
  "use strict";

  // ─── Page Visibility & Interval Management ──────────────────────
  var _pageIntervals = {};
  var _intervalCounter = 0;
  var _pageHidden = false;

  // Track page visibility for throttling animations
  document.addEventListener("visibilitychange", function () {
    _pageHidden = document.hidden;
  });

  // Register an interval that gets cleaned up on navigation/reload
  // Returns the interval ID so callers can still clear it manually
  ns.addInterval = function (key, fn, ms) {
    if (_pageIntervals[key]) {
      clearInterval(_pageIntervals[key]);
    }
    var id = setInterval(fn, ms);
    _pageIntervals[key] = id;
    return id;
  };

  // Remove a registered interval by key
  ns.removeInterval = function (key) {
    if (_pageIntervals[key]) {
      clearInterval(_pageIntervals[key]);
      delete _pageIntervals[key];
    }
  };

  // Clean ALL registered intervals (called on page unload or SPA nav)
  ns.clearAllIntervals = function () {
    Object.keys(_pageIntervals).forEach(function (k) {
      clearInterval(_pageIntervals[k]);
    });
    _pageIntervals = {};
  };

  // On page unload, clear all registered intervals automatically
  window.addEventListener("beforeunload", function () {
    ns.clearAllIntervals();
  });

  // ─── WebGL Neural Network Shader ───────────────────────────────
  ns.initShader = function (canvasId) {
    var canvas = document.getElementById(canvasId);
    if (!canvas) return;

    function syncSize() {
      var w = canvas.clientWidth || 1280;
      var h = canvas.clientHeight || 720;
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w;
        canvas.height = h;
      }
    }
    if (typeof ResizeObserver !== "undefined") {
      new ResizeObserver(syncSize).observe(canvas);
    }
    syncSize();

    var gl =
      canvas.getContext("webgl") ||
      canvas.getContext("experimental-webgl");
    if (!gl) return;

    var vs =
      "attribute vec2 a_position;varying vec2 v_texCoord;void main(){v_texCoord=a_position*0.5+0.5;gl_Position=vec4(a_position,0.0,1.0);}";
    var fs =
      "precision highp float;varying vec2 v_texCoord;uniform float u_time;uniform vec2 u_resolution;" +
      "float hash(vec2 p){p=fract(p*vec2(123.34,456.21));p+=dot(p,p+45.32);return fract(p.x*p.y);}" +
      "void main(){vec2 uv=v_texCoord;vec3 color=vec3(0.02,0.03,0.05);" +
      "vec2 st=uv*15.0;vec2 ipos=floor(st);vec2 fpos=fract(st);float m=0.0;" +
      "for(float y=-1.0;y<=1.0;y++){for(float x=-1.0;x<=1.0;x++){" +
      "vec2 n=vec2(x,y);vec2 p=vec2(hash(ipos+n),hash(ipos+n+12.0));p=0.5+0.5*sin(u_time*0.5+6.2831*p);" +
      "vec2 d=n+p-fpos;float l=length(d);m+=smoothstep(0.1,0.0,l)*hash(ipos+n);}}" +
      "color+=m*vec3(0.0,0.83,1.0)*0.3;" +
      "float sc=smoothstep(0.1,0.0,abs(uv.y-mod(u_time*0.1,1.2)+0.1));color+=sc*vec3(0.5,0.0,1.0)*0.1;" +
      "gl_FragColor=vec4(color,1.0);}";

    function cs(type, src) {
      var s = gl.createShader(type);
      gl.shaderSource(s, src);
      gl.compileShader(s);
      return s;
    }
    var prog = gl.createProgram();
    gl.attachShader(prog, cs(gl.VERTEX_SHADER, vs));
    gl.attachShader(prog, cs(gl.FRAGMENT_SHADER, fs));
    gl.linkProgram(prog);
    gl.useProgram(prog);

    var buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(
      gl.ARRAY_BUFFER,
      new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]),
      gl.STATIC_DRAW
    );
    var pos = gl.getAttribLocation(prog, "a_position");
    gl.enableVertexAttribArray(pos);
    gl.vertexAttribPointer(pos, 2, gl.FLOAT, false, 0, 0);

    var uTime = gl.getUniformLocation(prog, "u_time");
    var uRes = gl.getUniformLocation(prog, "u_resolution");
    var uMouse = gl.getUniformLocation(prog, "u_mouse");

    var mouse = { x: canvas.width / 2, y: canvas.height / 2 };
    window.addEventListener("mousemove", function (event) {
      var rect = canvas.getBoundingClientRect();
      if (rect.width && rect.height) {
        var nx = (event.clientX - rect.left) / rect.width;
        var ny = 1.0 - (event.clientY - rect.top) / rect.height;
        mouse.x = nx * canvas.width;
        mouse.y = ny * canvas.height;
      }
    });

    var _lastRenderTime = 0;
    var _rafId = null;

    function render(t) {
      if (_pageHidden) {
        // Page is hidden — throttle to ~1 fps and skip heavy draw
        if (t - _lastRenderTime < 1000) {
          _rafId = requestAnimationFrame(render);
          return;
        }
        _lastRenderTime = t;
      }
      if (typeof ResizeObserver === "undefined") syncSize();
      gl.viewport(0, 0, canvas.width, canvas.height);
      if (uTime) gl.uniform1f(uTime, t * 0.001);
      if (uRes) gl.uniform2f(uRes, canvas.width, canvas.height);
      if (uMouse) gl.uniform2f(uMouse, mouse.x, mouse.y);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      _rafId = requestAnimationFrame(render);
    }
    _rafId = requestAnimationFrame(render);

    // Stop render loop on page unload to free GPU resources
    window.addEventListener("beforeunload", function () {
      if (_rafId) cancelAnimationFrame(_rafId);
    });
  };

  // ─── Skeleton Loader Helper ────────────────────────────────────
  ns.showSkeleton = function (id, show) {
    var el = document.getElementById(id);
    if (el) {
      show ? el.classList.remove("hidden") : el.classList.add("hidden");
    }
  };

  // ─── Glass Card Mouse Parallax ─────────────────────────────────
  ns.initParallax = function (selector) {
    document.querySelectorAll(selector || ".glass-panel, .glass-card").forEach(function (card) {
      card.addEventListener("mousemove", function (e) {
        var rect = card.getBoundingClientRect();
        var x = e.clientX - rect.left;
        var y = e.clientY - rect.top;
        card.style.setProperty("--mouse-x", x + "px");
        card.style.setProperty("--mouse-y", y + "px");
      });
    });
  };

  // ─── Animated Counter ──────────────────────────────────────────
  ns.animateCounter = function (el, target, duration) {
    if (!el) return;
    duration = duration || 1000;
    var start = parseInt(el.innerText) || 0;
    var startTime = null;

    function step(timestamp) {
      if (!startTime) startTime = timestamp;
      var progress = Math.min((timestamp - startTime) / duration, 1);
      var current = Math.floor(start + (target - start) * progress);
      el.innerText = current;
      if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  };

  // ─── Add page-enter animation class to <main> ────────────────
  function addPageEnterAnimation() {
    var main = document.querySelector("main");
    if (main && !main.classList.contains("page-enter")) {
      main.classList.add("page-enter");
    }
  }

  // ─── Initialize All Modules ────────────────────────────────────
  ns.init = function () {
    addPageEnterAnimation();
    ns.initShader("shader-canvas-ANIMATION_2");
    ns.initParallax();

    // Auth handshake
    if (typeof ns.verifyHandshake === "function") {
      ns.verifyHandshake();
    }

    // Keyboard shortcuts
    if (typeof ns.initKeyboardShortcuts === "function") {
      ns.initKeyboardShortcuts();
    }

    // AI status badge
    if (typeof ns.checkAIStatus === "function") {
      ns.checkAIStatus();
    }

    // Journey breadcrumb on non-landing pages
    var currentPage = window.location.pathname.split("/").pop();
    var journeyPages = ["dashboard.html", "radar.html", "simulation.html", "twin.html", "rescue.html", "rag.html", "timeline.html", "analytics.html"];
    if (journeyPages.indexOf(currentPage) !== -1) {
      if (typeof ns.createJourneyBreadcrumb === "function") {
        var tryBreadcrumb = function () {
          var mainEl = document.querySelector("main");
          if (mainEl && mainEl.parentNode) {
            var bc = ns.createJourneyBreadcrumb();
            if (currentPage === "dashboard.html") {
              var header = document.querySelector("header");
              if (header && header.parentNode) {
                header.parentNode.insertBefore(bc, mainEl);
                bc.style.marginTop = "16px";
                bc.style.marginLeft = "16px";
                bc.style.marginRight = "16px";
              } else {
                mainEl.parentNode.insertBefore(bc, mainEl);
              }
            } else {
              mainEl.parentNode.insertBefore(bc, mainEl);
              bc.style.marginTop = "80px";
            }
            return true;
          }
          return false;
        };
        // Try immediately, fall back to MutationObserver
        if (!tryBreadcrumb()) {
          var observer = new MutationObserver(function () {
            if (tryBreadcrumb()) observer.disconnect();
          });
          observer.observe(document.body, { childList: true, subtree: true });
        }
      }
    }

    // Demo CTA on landing page only
    if ((currentPage === "" || currentPage === "index.html" || currentPage === "/") &&
        typeof ns.addDemoCTA === "function") {
      setTimeout(ns.addDemoCTA, 1000);
    }

    // Periodically check AI status (registered for managed cleanup)
    if (typeof ns.checkAIStatus === "function") {
      ns.addInterval('ai-status', ns.checkAIStatus, 15000);
    }
  };

  // Auto-init on DOM ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", ns.init);
  } else {
    ns.init();
  }
})(window.FutureShield);
