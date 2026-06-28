// Demo Mode Controller for Flawless Presentations
// Provides automated, rehearsed demo flow when activated via URL param or keypress

class DemoMode {
    constructor() {
        this.active = false;
        this.startTime = null;
        this.demoLength = 60000; // 60 seconds demo
        this.events = [
            { time: 15000, action: this.triggerStressEvent.bind(this) }, // 15s
            { time: 30000, action: this.triggerThreatEvent.bind(this) }, // 30s
            { time: 45000, action: this.triggerSuccessEvent.bind(this) } // 45s
        ];
        this.keyListener = this.handleKeyPress.bind(this);
        this.bindEvents();
    }

    bindEvents() {
        // Check for demo mode in URL
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('demo') === 'true') {
            this.start();
        }

        // Allow manual activation with 'D' key (hold for 2 seconds to prevent accidental activation)
        let demoKeyPressTime = null;
        document.addEventListener('keydown', (e) => {
            if (e.key.toLowerCase() === 'd') {
                demoKeyPressTime = Date.now();
            }
        });
        document.addEventListener('keyup', (e) => {
            if (e.key.toLowerCase() === 'd' && demoKeyPressTime) {
                const holdTime = Date.now() - demoKeyPressTime;
                if (holdTime >= 2000) { // 2 second hold to activate
                    this.toggle();
                }
                demoKeyPressTime = null;
            }
        });
    }

    start() {
        if (this.active) return;
        this.active = true;
        this.startTime = Date.now();
        console.log('[DEMO MODE] Activated - running automated demo sequence');

        // Show demo mode indicator in UI
        this.showDemoIndicator();

        // Start event loop
        this.runDemoLoop();
    }

    stop() {
        if (!this.active) return;
        this.active = false;
        console.log('[DEMO MODE] Deactivated');
        this.hideDemoIndicator();
    }

    toggle() {
        this.active ? this.stop() : this.start();
    }

    showDemoIndicator() {
        // Create a subtle demo mode indicator in the corner
        let indicator = document.getElementById('demo-mode-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'demo-mode-indicator';
            indicator.innerHTML = 'DEMO MODE • Press and hold D for 2s to exit';
            indicator.style.cssText = `
                position: fixed; bottom: 20px; left: 20px;
                background: rgba(0,0,0,0.7); color: #00ff88;
                padding: 8px 12px; border-radius: 4px; font-size: 12px;
                z-index: 10000; pointer-events: none;
                font-family: monospace;
            `;
            document.body.appendChild(indicator);
        }
    }

    hideDemoIndicator() {
        const indicator = document.getElementById('demo-mode-indicator');
        if (indicator) {
            indicator.remove();
        }
    }

    runDemoLoop() {
        if (!this.active) return;

        const elapsed = Date.now() - this.startTime;

        // Check for upcoming events
        for (const event of this.events) {
            if (!event.triggered && elapsed >= event.time) {
                event.triggered = true;
                event.action();
                console.log(`[DEMO MODE] Triggered event at ${Math.round(elapsed/1000)}s`);
            }
        }

        // End demo after duration
        if (elapsed >= this.demoLength) {
            this.stop();
            this.showDemoComplete();
            return;
        }

        // Continue loop
        requestAnimationFrame(() => this.runDemoLoop());
    }

    triggerStressEvent() {
        // Trigger a stress event via the sensor fusion system
        if (window.sensorFusion) {
            // Temporarily override to return high stress
            const originalGetFused = window.sensorFusion.getFusedStress.bind(window.sensorFusion);
            window.sensorFusion.getFusedStress = async () => {
                // Return high stress value (0.8-0.95) for next 10 seconds
                const elapsed = Date.now() - this.startTime;
                if (elapsed < 25000) { // 10 seconds duration
                    return 0.85 + Math.random() * 0.1;
                }
                // Restore original function after duration
                window.sensorFusion.getFusedStress = originalGetFused;
                return originalGetFused();
            };
        }

        // Show stress alert in UI
        this.showTemporaryAlert('⚠️ STRESS DETECTED: Elevated cognitive load', '#ff9800', 5000);

        // Update focus display if exists
        if (window.updateStressDisplay) {
            window.updateStressDisplay(85 + Math.random()*10); // 85-95%
        }
    }

    triggerThreatEvent() {
        // Simulate a new high-priority threat appearing on the map
        if (window.addThreatMarker) {
            // Add a threatening-looking marker
            const threat = {
                id: `DEMO_THREAT_${Date.now()}`,
                name: 'Chemical Spill',
                type: 'chemical',
                urgency: 'critical',
                probability: 95,
                x_pos: 400 + Math.random()*200, // Randomize slightly
                y_pos: 300 + Math.random()*100
            };
            window.addThreatMarker(threat);
        }

        // Show threat alert
        this.showTemporaryAlert('🚨 HIGH PRIORITY THREAT DETECTED: Chemical Spill', '#f44336', 6000);

        # Auto-trigger mitigation generation after 2 seconds
        setTimeout(() => {
            if (window.generateMitigationForLastThreat) {
                window.generateMitigationForLastThreat();
            }
        }, 2000);
    }

    triggerSuccessEvent() {
        // Show successful mitigation
        this.showTemporaryAlert('✅ THREAT MITIGATED: Casualties prevented', '#4caf50', 5000);

        # Update lives saved counter
        if (window.updateLivesSaved) {
            const current = parseInt(document.getElementById('lives-saved')?.textContent || '0');
            document.getElementById('lives-saved').textContent = current + 12;
        }

        # Show final message
        setTimeout(() => {
            this.showTemporaryAlert('🎉 DEMO COMPLETE: System performed as expected', '#8bc34a', 4000);
        }, 2000);
    }

    showTemporaryAlert(message, color, duration) {
        // Remove any existing alert
        const existing = document.getElementById('demo-alert');
        if (existing) existing.remove();

        const alert = document.createElement('div');
        alert.id = 'demo-alert';
        alert.textContent = message;
        alert.style.cssText = `
            position: fixed; top: 20px; left: 50%; transform: translateX(-50%);
            background: ${color}; color: white; padding: 12px 24px;
            border-radius: 4px; font-weight: bold; z-index: 10000;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            animation: slideDown 0.3s ease-out;
        `;
        document.body.appendChild(alert);

        // Remove after duration
        setTimeout(() => {
            alert.style.animation = 'slideUp 0.3s ease-in';
            setTimeout(() => {
                if (alert.parentNode) alert.parentNode.removeChild(alert);
            }, 300);
        }, duration);

        // Add keyframe animations
        const style = document.createElement('style');
        style.textContent = `
            @keyframes slideDown {
                from { transform: translateX(-50%) translateY(-20px); opacity: 0; }
                to { transform: translateX(-50%) translateY(0); opacity: 1; }
            }
            @keyframes slideUp {
                from { transform: translateX(-50%) translateY(0); opacity: 1; }
                to { transform: translateX(-50%) translateY(-20px); opacity: 0; }
            }
        `;
        document.head.appendChild(style);
    }

    showDemoComplete() {
        this.showTemporaryAlert('🏁 Demo sequence complete. Ready for live interaction.', '#2196f3', 5000);
    }
}

// Initialize demo mode when script loads
window.demoMode = new DemoMode();

// Export for use in other modules if needed
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DemoMode;
}