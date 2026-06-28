/**
 * FutureShield AI - Smart AI Calendar
 * Daily timeline grid plotting Deep Work intervals, scheduled ops, and Risk Zones.
 * Insert container: <div id="ai-calendar" style="width:100%;height:auto"></div>
 */
(function () {
  "use strict";

  var ns = window.FutureShield = window.FutureShield || {};

  ns.createAICalendar = function (containerId) {
    var container = document.getElementById(containerId);
    if (!container) return;

    // ─── Generate today's schedule data ───────────────────────────
    var now = new Date();
    var currentHour = now.getHours() + now.getMinutes() / 60;

    // Sample schedule blocks
    var blocks = [
      { start: 6, end: 7.5, label: "Morning Routine", type: "routine", color: "#323539" },
      { start: 7.5, end: 9, label: "Deep Work: Core Integration", type: "deep", color: "#00d4ff" },
      { start: 9, end: 9.5, label: "Standup Sync", type: "meeting", color: "#571bc1" },
      { start: 9.5, end: 11, label: "Deep Work: AI Pipeline", type: "deep", color: "#00d4ff" },
      { start: 11, end: 12, label: "Code Review", type: "work", color: "#3cd7ff" },
      { start: 12, end: 13, label: "Lunch / Recharge", type: "break", color: "#323539" },
      { start: 13, end: 14.5, label: "Deep Work: Documentation", type: "deep", color: "#00d4ff" },
      { start: 14.5, end: 15, label: "Team Sync", type: "meeting", color: "#571bc1" },
      { start: 15, end: 16.5, label: "Deep Work: Testing", type: "deep", color: "#00d4ff" },
      { start: 16.5, end: 17.5, label: "Buffer / Overflow", type: "buffer", color: "#d0bcff" },
      { start: 17.5, end: 18, label: "Wind Down", type: "routine", color: "#323539" },
    ];

    // Risk zones (low energy / high distraction periods)
    var riskZones = [
      { start: 14, end: 15, label: "Post-Lunch Dip", level: "medium" },
      { start: 3, end: 5, label: "Late Night Degradation", level: "high" },
    ];

    // ─── Build Calendar HTML ──────────────────────────────────────
    var header = document.createElement("div");
    header.style.cssText = "display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;";

    var title = document.createElement("h3");
    title.style.cssText = "font-family:'Space Grotesk',sans-serif;font-size:12px;letter-spacing:0.1em;text-transform:uppercase;color:#bbc9cf;";
    title.textContent = "Today's Timeline — " + now.toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" });
    header.appendChild(title);

    var legend = document.createElement("div");
    legend.style.cssText = "display:flex;gap:12px;align-items:center;";
    var legendItems = [
      { label: "Deep Work", color: "#00d4ff" },
      { label: "Meeting", color: "#571bc1" },
      { label: "Risk Zone", color: "#ffb4ab" },
    ];
    legendItems.forEach(function (item) {
      var dot = document.createElement("span");
      dot.style.cssText = "display:inline-block;width:8px;height:8px;border-radius:2px;background:" + item.color + ";margin-right:4px;";
      var lbl = document.createElement("span");
      lbl.style.cssText = "font-family:'Space Grotesk',sans-serif;font-size:8px;letter-spacing:0.1em;text-transform:uppercase;color:#859398;";
      lbl.textContent = item.label;
      var wrap = document.createElement("span");
      wrap.style.cssText = "display:inline-flex;align-items:center;gap:4px;";
      wrap.appendChild(dot);
      wrap.appendChild(lbl);
      legend.appendChild(wrap);
    });
    header.appendChild(legend);
    container.appendChild(header);

    // ─── Timeline Grid ────────────────────────────────────────────
    var timelineWrap = document.createElement("div");
    timelineWrap.style.cssText = "position:relative;border-radius:12px;overflow:hidden;background:rgba(17,20,23,0.6);border:1px solid rgba(255,255,255,0.05);backdrop-filter:blur(60px);";

    var timeline = document.createElement("div");
    timeline.style.cssText = "position:relative;width:100%;padding:16px 0;";

    // Hour labels + grid lines (0-24)
    for (var h = 0; h <= 24; h++) {
      var isHour = h % 1 === 0;
      var yPos = (h / 24) * 100;

      // Grid line
      var line = document.createElement("div");
      line.style.cssText =
        "position:absolute;left:60px;right:16px;top:" + yPos + "%;" +
        "border-top:" + (isHour ? "1px solid rgba(255,255,255,0.06)" : "1px dashed rgba(255,255,255,0.03)") + ";";
      timeline.appendChild(line);

      // Hour label
      if (isHour) {
        var lbl = document.createElement("div");
        var hourStr = h === 0 ? "12 AM" : h < 12 ? h + " AM" : h === 12 ? "12 PM" : (h - 12) + " PM";
        lbl.textContent = hourStr;
        lbl.style.cssText =
          "position:absolute;left:8px;top:" + yPos + "%;" +
          "font-family:'Space Grotesk',sans-serif;font-size:9px;color:#859398;" +
          "transform:translateY(-50%);width:48px;text-align:right;padding-right:8px;";
        timeline.appendChild(lbl);
      }
    }

    // ─── Risk Zones ───────────────────────────────────────────────
    riskZones.forEach(function (zone) {
      var topPct = (zone.start / 24) * 100;
      var heightPct = ((zone.end - zone.start) / 24) * 100;
      var zoneEl = document.createElement("div");
      var bgColor = zone.level === "high" ? "rgba(255,180,171,0.12)" : "rgba(255,180,171,0.06)";
      var borderColor = zone.level === "high" ? "rgba(255,180,171,0.3)" : "rgba(255,180,171,0.15)";
      zoneEl.style.cssText =
        "position:absolute;left:60px;right:16px;top:" + topPct + "%;height:" + heightPct + "%;" +
        "background:" + bgColor + ";border:1px solid " + borderColor + ";border-radius:4px;" +
        "display:flex;align-items:center;justify-content:center;pointer-events:none;";
      var zoneLabel = document.createElement("span");
      zoneLabel.style.cssText =
        "font-family:'Space Grotesk',sans-serif;font-size:7px;letter-spacing:0.1em;" +
        "text-transform:uppercase;color:rgba(255,180,171,0.5);";
      zoneLabel.textContent = "⚠ " + zone.label;
      zoneEl.appendChild(zoneLabel);
      timeline.appendChild(zoneEl);
    });

    // ─── Schedule Blocks ──────────────────────────────────────────
    blocks.forEach(function (block) {
      var topPct = (block.start / 24) * 100;
      var heightPct = ((block.end - block.start) / 24) * 100;
      var blockEl = document.createElement("div");
      blockEl.style.cssText =
        "position:absolute;left:64px;right:20px;top:" + topPct + "%;height:" + heightPct + "%;" +
        "background:" + block.color + ";border-radius:6px;opacity:0.85;" +
        "display:flex;align-items:center;padding:0 12px;cursor:pointer;" +
        "transition:all 0.3s ease;min-height:20px;overflow:hidden;";
      blockEl.style.boxShadow = block.type === "deep"
        ? "0 0 12px rgba(0,212,255,0.2), inset 0 0 8px rgba(255,255,255,0.1)"
        : "none";

      var label = document.createElement("span");
      label.style.cssText =
        "font-family:'Space Grotesk',sans-serif;font-size:8px;letter-spacing:0.05em;" +
        "color:" + (block.type === "deep" ? "#003642" : "#e1e2e7") + ";" +
        "white-space:nowrap;overflow:hidden;text-overflow:ellipsis;";
      label.textContent = block.label;

      // Time range
      var timeSpan = document.createElement("span");
      var startStr = formatHour(block.start);
      var endStr = formatHour(block.end);
      timeSpan.textContent = startStr + " – " + endStr;
      timeSpan.style.cssText =
        "font-family:'Space Grotesk',sans-serif;font-size:7px;letter-spacing:0.05em;" +
        "color:" + (block.type === "deep" ? "#003642" : "#859398") + ";" +
        "margin-left:auto;opacity:0.7;";

      blockEl.appendChild(label);
      blockEl.appendChild(timeSpan);

      // Hover effect
      blockEl.addEventListener("mouseenter", function () {
        this.style.opacity = "1";
        this.style.transform = "scale(1.02)";
      });
      blockEl.addEventListener("mouseleave", function () {
        this.style.opacity = "0.85";
        this.style.transform = "scale(1)";
      });

      timeline.appendChild(blockEl);
    });

    // ─── Current Time Indicator ───────────────────────────────────
    if (currentHour >= 0 && currentHour <= 24) {
      var nowTop = (currentHour / 24) * 100;
      var nowLine = document.createElement("div");
      nowLine.style.cssText =
        "position:absolute;left:60px;right:16px;top:" + nowTop + "%;" +
        "border-top:2px solid #ffb4ab;z-index:10;box-shadow:0 0 8px rgba(255,180,171,0.5);";
      // Dot
      var dot = document.createElement("div");
      dot.style.cssText =
        "position:absolute;left:56px;top:-4px;width:10px;height:10px;" +
        "border-radius:50%;background:#ffb4ab;box-shadow:0 0 12px rgba(255,180,171,0.8);";
      timeline.appendChild(dot);
      timeline.appendChild(nowLine);
    }

    timelineWrap.appendChild(timeline);
    container.appendChild(timelineWrap);

    // ─── Stats Row ────────────────────────────────────────────────
    var stats = document.createElement("div");
    stats.style.cssText = "display:flex;gap:16px;margin-top:12px;flex-wrap:wrap;";

    var deepBlocks = blocks.filter(function (b) { return b.type === "deep"; });
    var totalDeep = deepBlocks.reduce(function (sum, b) { return sum + (b.end - b.start); }, 0);

    var statItems = [
      { label: "Deep Work", value: totalDeep.toFixed(1) + "h", color: "#00d4ff" },
      { label: "Meetings", value: blocks.filter(function (b) { return b.type === "meeting"; }).length + " blocks", color: "#571bc1" },
      { label: "Risk Zones", value: riskZones.length + " detected", color: "#ffb4ab" },
    ];

    statItems.forEach(function (item) {
      var stat = document.createElement("div");
      stat.style.cssText =
        "display:flex;align-items:center;gap:8px;padding:8px 12px;" +
        "background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.05);" +
        "border-radius:8px;";
      var dot = document.createElement("span");
      dot.style.cssText = "display:inline-block;width:6px;height:6px;border-radius:2px;background:" + item.color + ";";
      var lbl = document.createElement("span");
      lbl.style.cssText = "font-family:'Space Grotesk',sans-serif;font-size:9px;color:#859398;text-transform:uppercase;letter-spacing:0.05em;";
      lbl.textContent = item.label;
      var val = document.createElement("span");
      val.style.cssText = "font-family:'Space Grotesk',sans-serif;font-size:10px;color:#e1e2e7;font-weight:600;";
      val.textContent = item.value;
      stat.appendChild(dot);
      stat.appendChild(lbl);
      stat.appendChild(val);
      stats.appendChild(stat);
    });

    container.appendChild(stats);
  };

  // ─── Helpers ────────────────────────────────────────────────────
  function formatHour(h) {
    var hour = Math.floor(h);
    var min = Math.round((h - hour) * 60);
    var period = hour >= 12 ? "PM" : "AM";
    var h12 = hour % 12 || 12;
    return h12 + ":" + (min < 10 ? "0" : "") + min + " " + period;
  }

})();
