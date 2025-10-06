// F1 Superfan - Frontend JavaScript

document.addEventListener('DOMContentLoaded', function() {
    const manualCaptureBtn = document.getElementById('manual-capture-btn');
    const statusMessage = document.getElementById('status-message');

    // Manual capture handler
    manualCaptureBtn.addEventListener('click', async function() {
        try {
            manualCaptureBtn.disabled = true;
            statusMessage.textContent = 'Capturing...';

            const response = await fetch('/manual_capture', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();

            if (response.ok) {
                statusMessage.textContent = `✓ ${data.message}`;
                setTimeout(() => {
                    statusMessage.textContent = '';
                }, 3000);
            } else {
                statusMessage.textContent = `✗ Error: ${data.error}`;
                statusMessage.style.color = '#ff4444';
            }

        } catch (error) {
            statusMessage.textContent = `✗ Error: ${error.message}`;
            statusMessage.style.color = '#ff4444';
        } finally {
            manualCaptureBtn.disabled = false;
        }
    });

    // Check system status
    async function checkStatus() {
        try {
            const response = await fetch('/status');
            const data = await response.json();

            if (!data.camera_initialized) {
                console.warn('Camera not initialized');
            }
        } catch (error) {
            console.error('Error checking status:', error);
        }
    }

    // Check status on load
    checkStatus();
});