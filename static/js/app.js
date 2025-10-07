// F1 Superfan - Frontend JavaScript

document.addEventListener('DOMContentLoaded', function() {
    const manualCaptureBtn = document.getElementById('manual-capture-btn');
    const statusMessage = document.getElementById('status-message');
    const adhocInferenceBtn = document.getElementById('adhoc-inference-btn');
    const customPromptTextarea = document.getElementById('custom-prompt');
    const inferenceStatus = document.getElementById('inference-status');
    const inferenceResult = document.getElementById('inference-result');

    // Manual capture handler
    manualCaptureBtn.addEventListener('click', async function() {
        try {
            manualCaptureBtn.disabled = true;
            statusMessage.textContent = 'Capturing...';
            statusMessage.style.color = '';

            const response = await fetch('/manual_capture', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();

            if (response.ok) {
                statusMessage.textContent = `✓ ${data.message}`;
                statusMessage.style.color = '#44ff44';
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

    // Ad hoc inference handler
    adhocInferenceBtn.addEventListener('click', async function() {
        try {
            adhocInferenceBtn.disabled = true;
            inferenceStatus.textContent = 'Running inference...';
            inferenceStatus.style.color = '#ffaa00';
            inferenceResult.textContent = 'Processing...';

            const prompt = customPromptTextarea.value.trim();
            if (!prompt) {
                inferenceStatus.textContent = '✗ Please enter a prompt';
                inferenceStatus.style.color = '#ff4444';
                adhocInferenceBtn.disabled = false;
                return;
            }

            const response = await fetch('/adhoc_inference', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ prompt: prompt })
            });

            const data = await response.json();

            if (response.ok) {
                inferenceStatus.textContent = '✓ Inference complete';
                inferenceStatus.style.color = '#44ff44';

                // Display the result
                inferenceResult.textContent = data.response;

                setTimeout(() => {
                    inferenceStatus.textContent = '';
                }, 3000);
            } else {
                inferenceStatus.textContent = `✗ Error: ${data.error}`;
                inferenceStatus.style.color = '#ff4444';
                inferenceResult.textContent = `Error: ${data.error}`;
            }

        } catch (error) {
            inferenceStatus.textContent = `✗ Error: ${error.message}`;
            inferenceStatus.style.color = '#ff4444';
            inferenceResult.textContent = `Error: ${error.message}`;
        } finally {
            adhocInferenceBtn.disabled = false;
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

            if (!data.inference_worker_running) {
                console.warn('Inference worker not running');
            }
        } catch (error) {
            console.error('Error checking status:', error);
        }
    }

    // Check status on load
    checkStatus();

    // Refresh status periodically
    setInterval(checkStatus, 30000); // Every 30 seconds
});