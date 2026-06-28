/**
 * FutureShield AI - Knowledge & Dependency Graph
 * Pannable, zoomable SVG force-directed node map.
 * Insert a container: <div id="knowledge-graph" style="width:100%;height:400px"></div>
 */
(function () {
  "use strict";

  var ns = window.FutureShield = window.FutureShield || {};

  // ─── Sample Data ────────────────────────────────────────────────
  var defaultNodes = [
    { id: "goals", label: "Goals", group: 1, radius: 28, color: "#00d4ff" },
    { id: "phoenix", label: "Phoenix Core", group: 1, radius: 20, color: "#3cd7ff" },
    { id: "twin", label: "Digital Twin", group: 1, radius: 20, color: "#3cd7ff" },
    { id: "crud", label: "CRUD API", group: 1, radius: 20, color: "#3cd7ff" },
    { id: "threats", label: "Threats", group: 2, radius: 24, color: "#ffb4ab" },
    { id: "xr904", label: "XR-904", group: 2, radius: 16, color: "#ffb4ab" },
    { id: "tr421", label: "TR-421", group: 2, radius: 16, color: "#d0bcff" },
    { id: "bv112", label: "BV-112", group: 2, radius: 16, color: "#93ecff" },
    { id: "skills", label: "Skills", group: 3, radius: 24, color: "#d0bcff" },
    { id: "python", label: "Python", group: 3, radius: 16, color: "#d0bcff" },
    { id: "fastapi", label: "FastAPI", group: 3, radius: 16, color: "#d0bcff" },
    { id: "gemini", label: "Gemini AI", group: 3, radius: 16, color: "#d0bcff" },
    { id: "frontend", label: "Frontend", group: 3, radius: 16, color: "#d0bcff" },
    { id: "systems", label: "Systems", group: 4, radius: 20, color: "#93ecff" },
    { id: "radar", label: "Radar", group: 4, radius: 16, color: "#93ecff" },
    { id: "rescue", label: "Rescue", group: 4, radius: 16, color: "#93ecff" },
    { id: "sim", label: "Simulation", group: 4, radius: 16, color: "#93ecff" },
  ];

  var defaultEdges = [
    { source: "goals", target: "phoenix" },
    { source: "goals", target: "twin" },
    { source: "goals", target: "crud" },
    { source: "threats", target: "xr904" },
    { source: "threats", target: "tr421" },
    { source: "threats", target: "bv112" },
    { source: "skills", target: "python" },
    { source: "skills", target: "fastapi" },
    { source: "skills", target: "gemini" },
    { source: "skills", target: "frontend" },
    { source: "systems", target: "radar" },
    { source: "systems", target: "rescue" },
    { source: "systems", target: "sim" },
    { source: "phoenix", target: "python" },
    { source: "phoenix", target: "fastapi" },
    { source: "twin", target: "frontend" },
    { source: "crud", target: "fastapi" },
    { source: "xr904", target: "rescue" },
    { source: "tr421", target: "radar" },
    { source: "bv112", target: "sim" },
    { source: "gemini", target: "rescue" },
    { source: "gemini", target: "sim" },
    { source: "radar", target: "threats" },
  ];

  // ─── Graph Renderer ─────────────────────────────────────────────
  ns.createKnowledgeGraph = function (containerId, customNodes, customEdges) {
    var container = document.getElementById(containerId);
    if (!container) return;

    var nodes = customNodes || defaultNodes;
    var edges = customEdges || defaultEdges;

    // Create SVG
    var svgNS = "http://www.w3.org/2000/svg";
    var svg = document.createElementNS(svgNS, "svg");
    svg.setAttribute("width", "100%");
    svg.setAttribute("height", "100%");
    svg.style.cssText = "display:block;overflow:hidden;";
    container.appendChild(svg);

    // Viewport dimensions
    var width = container.clientWidth || 600;
    var height = container.clientHeight || 400;

    // ─── Force Simulation (simple custom) ─────────────────────────
    // Initialize positions in a circle
    var centerX = width / 2;
    var centerY = height / 2;
    var radius = Math.min(width, height) * 0.3;

    nodes.forEach(function (node, i) {
      var angle = (2 * Math.PI * i) / nodes.length;
      node.x = centerX + radius * Math.cos(angle) + (Math.random() - 0.5) * 50;
      node.y = centerY + radius * Math.sin(angle) + (Math.random() - 0.5) * 50;
      node.vx = 0;
      node.vy = 0;
    });

    // Edge lookup
    var edgeMap = {};
    edges.forEach(function (e) {
      var key = e.source + "-" + e.target;
      edgeMap[key] = true;
    });

    function simulateStep() {
      var repulsion = 8000;
      var attraction = 0.005;
      var damping = 0.85;
      var minDist = 50;

      // Repulsion between all nodes
      for (var i = 0; i < nodes.length; i++) {
        for (var j = i + 1; j < nodes.length; j++) {
          var a = nodes[i];
          var b = nodes[j];
          var dx = b.x - a.x;
          var dy = b.y - a.y;
          var dist = Math.sqrt(dx * dx + dy * dy) || 1;
          var force = repulsion / (dist * dist);
          var fx = (dx / dist) * force;
          var fy = (dy / dist) * force;
          a.vx -= fx;
          a.vy -= fy;
          b.vx += fx;
          b.vy += fy;
        }
      }

      // Attraction along edges
      edges.forEach(function (e) {
        var source = nodes.filter(function (n) { return n.id === e.source; })[0];
        var target = nodes.filter(function (n) { return n.id === e.target; })[0];
        if (!source || !target) return;
        var dx = target.x - source.x;
        var dy = target.y - source.y;
        var dist = Math.sqrt(dx * dx + dy * dy) || 1;
        var force = (dist - minDist) * attraction;
        var fx = (dx / dist) * force;
        var fy = (dy / dist) * force;
        source.vx += fx;
        source.vy += fy;
        target.vx -= fx;
        target.vy -= fy;
      });

      // Center gravity
      nodes.forEach(function (n) {
        n.vx += (centerX - n.x) * 0.001;
        n.vy += (centerY - n.y) * 0.001;
        n.vx *= damping;
        n.vy *= damping;
        n.x += n.vx;
        n.y += n.vy;
        // Clamp
        n.x = Math.max(20, Math.min(width - 20, n.x));
        n.y = Math.max(20, Math.min(height - 20, n.y));
      });
    }

    // ─── Render ───────────────────────────────────────────────────
    var edgeGroup = document.createElementNS(svgNS, "g");
    var nodeGroup = document.createElementNS(svgNS, "g");
    var labelGroup = document.createElementNS(svgNS, "g");
    svg.appendChild(edgeGroup);
    svg.appendChild(nodeGroup);
    svg.appendChild(labelGroup);

    var edgeEls = {};
    edges.forEach(function (e) {
      var line = document.createElementNS(svgNS, "line");
      line.setAttribute("stroke", "rgba(255,255,255,0.08)");
      line.setAttribute("stroke-width", "1.5");
      edgeEls[e.source + "-" + e.target] = line;
      edgeGroup.appendChild(line);
    });

    var nodeEls = {};
    var labelEls = {};
    nodes.forEach(function (n) {
      // Circle
      var circle = document.createElementNS(svgNS, "circle");
      circle.setAttribute("r", n.radius || 16);
      circle.setAttribute("fill", n.color || "#3cd7ff");
      circle.setAttribute("opacity", "0.7");
      circle.style.cursor = "pointer";
      circle.style.transition = "opacity 0.3s, r 0.3s";
      nodeEls[n.id] = circle;
      nodeGroup.appendChild(circle);

      // Label
      var text = document.createElementNS(svgNS, "text");
      text.textContent = n.label;
      text.setAttribute("fill", "#e1e2e7");
      text.setAttribute("font-size", "9");
      text.setAttribute("font-family", "'Space Grotesk', sans-serif");
      text.setAttribute("text-anchor", "middle");
      text.setAttribute("dy", "3");
      text.setAttribute("opacity", "0.8");
      labelEls[n.id] = text;
      labelGroup.appendChild(text);
    });

    function updatePositions() {
      nodes.forEach(function (n) {
        var el = nodeEls[n.id];
        if (el) {
          el.setAttribute("cx", n.x);
          el.setAttribute("cy", n.y);
        }
        var lbl = labelEls[n.id];
        if (lbl) {
          lbl.setAttribute("x", n.x);
          lbl.setAttribute("y", n.y + (n.radius || 16) + 12);
        }
      });
      edges.forEach(function (e) {
        var source = nodes.filter(function (n) { return n.id === e.source; })[0];
        var target = nodes.filter(function (n) { return n.id === e.target; })[0];
        var line = edgeEls[e.source + "-" + e.target];
        if (line && source && target) {
          line.setAttribute("x1", source.x);
          line.setAttribute("y1", source.y);
          line.setAttribute("x2", target.x);
          line.setAttribute("y2", target.y);
        }
      });
    }

    // ─── Simulation Loop ──────────────────────────────────────────
    var steps = 0;
    var maxSteps = 120;
    function tick() {
      if (steps < maxSteps) {
        simulateStep();
        updatePositions();
        steps++;
        requestAnimationFrame(tick);
      } else {
        // Final position lock
        updatePositions();
      }
    }
    tick();

    // ─── Pan & Zoom ───────────────────────────────────────────────
    var panX = 0, panY = 0, scale = 1;
    var isDragging = false;
    var startX, startY;
    var dragNode = null;

    svg.addEventListener("mousedown", function (e) {
      var target = e.target;
      if (target.tagName === "circle") {
        // Node dragging
        var nodeId = null;
        for (var id in nodeEls) {
          if (nodeEls[id] === target) { nodeId = id; break; }
        }
        if (nodeId) {
          dragNode = nodes.filter(function (n) { return n.id === nodeId; })[0];
          if (dragNode) {
            isDragging = true;
            startX = e.clientX;
            startY = e.clientY;
            target.setAttribute("opacity", "1");
            target.setAttribute("r", (dragNode.radius || 16) * 1.5);
            return;
          }
        }
      }
      // Pan
      isDragging = true;
      startX = e.clientX - panX;
      startY = e.clientY - panY;
    });

    window.addEventListener("mousemove", function (e) {
      if (!isDragging) return;
      if (dragNode) {
        var rect = svg.getBoundingClientRect();
        dragNode.x = (e.clientX - rect.left) / scale;
        dragNode.y = (e.clientY - rect.top) / scale;
        updatePositions();
      } else {
        panX = e.clientX - startX;
        panY = e.clientY - startY;
        svg.style.transform = "translate(" + panX + "px, " + panY + "px) scale(" + scale + ")";
        svg.style.transformOrigin = "center center";
      }
    });

    window.addEventListener("mouseup", function () {
      if (dragNode) {
        var el = nodeEls[dragNode.id];
        if (el) {
          el.setAttribute("opacity", "0.7");
          el.setAttribute("r", dragNode.radius || 16);
        }
        dragNode = null;
      }
      isDragging = false;
    });

    // Zoom
    svg.addEventListener("wheel", function (e) {
      e.preventDefault();
      var delta = e.deltaY > 0 ? 0.9 : 1.1;
      scale = Math.max(0.3, Math.min(3, scale * delta));
      svg.style.transform = "translate(" + panX + "px, " + panY + "px) scale(" + scale + ")";
      svg.style.transformOrigin = "center center";
    }, { passive: false });

    // ─── Resize ───────────────────────────────────────────────────
    function resize() {
      width = container.clientWidth || 600;
      height = container.clientHeight || 400;
      centerX = width / 2;
      centerY = height / 2;
      svg.setAttribute("viewBox", "0 0 " + width + " " + height);
    }
    window.addEventListener("resize", resize);
    resize();
  };

})();
