// Sensor Fusion Module for Robust Stress Detection
// Combines multiple sensor inputs to ensure reliability in varying conditions

class SensorFusion {
    constructor() {
        this.weights = {
            webcam: 0.5,
            mouse: 0.3,
            keyboard: 0.2
        };
        this.history = [];
        this.maxHistory = 5; // Keep last 5 readings for smoothing
    }

    // Get stress level from webcam (existing method - to be implemented by existing code)
    async getWebcamStress() {
        // This should call your existing webcam-based stress detection
        // For now, we'll return a placeholder - replace with actual implementation
        try {
            // Example: return await detectStressFromWebcam();
            // Since we don't have the actual function, we'll simulate
            return Math.random() * 0.4; // Simulate low-medium stress
        } catch (e) {
            console.warn('Webcam stress detection failed:', e);
            return 0; // Fail safe
        }
    }

    // Get stress level from mouse movement entropy
    getMouseStress() {
        try {
            // Calculate mouse movement jitter (standard deviation of movement over time)
            // This is a simplified version - in practice, you'd track mouse deltas
            const movement = window.lastMouseMovement || 0;
            // Normalize to 0-1 range (higher movement = higher stress)
            return Math.min(1, movement / 100);
        } catch (e) {
            console.warn('Mouse stress detection failed:', e);
            return 0;
        }
    }

    // Get stress level from keyboard typing rhythm
    getKeyboardStress() {
        try {
            // Calculate irregularity in keypress timing
            // This is a simplified version - in practice, you'd track keypress intervals
            const typingIrregularity = window.lastTypingIrregularity || 0;
            // Normalize to 0-1 range (more irregular = higher stress)
            return Math.min(1, typingIrregularity * 2);
        } catch (e) {
            console.warn('Keyboard stress detection failed:', e);
            return 0;
        }
    }

    // Get fused stress score with smoothing
    async getFusedStress() {
        try {
            // Get readings from all available sensors
            const webcamStress = await this.getWebcamStress();
            const mouseStress = this.getMouseStress();
            const keyboardStress = this.getKeyboardStress();

            // Apply weights
            const weightedSum =
                (webcamStress * this.weights.webcam) +
                (mouseStress * this.weights.mouse) +
                (keyboardStress * this.weights.keyboard);

            // Add to history for smoothing
            this.history.push(weightedSum);
            if (this.history.length > this.maxHistory) {
                this.history.shift();
            }

            // Calculate moving average (reduces noise)
            const smoothed = this.history.reduce((a, b) => a + b, 0) / this.history.length;

            // Ensure value is in [0,1] range
            return Math.max(0, Math.min(1, smoothed));
        } catch (error) {
            console.error('Sensor fusion error:', error);
            // Fallback to middle value if all sensors fail
            return 0.5;
        }
    }
}

// Initialize global sensor fusion instance
window.sensorFusion = new SensorFusion();

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SensorFusion;
}