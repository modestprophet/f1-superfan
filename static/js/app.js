// F1 Superfan - Frontend JavaScript

document.addEventListener('DOMContentLoaded', function() {
    const manualCaptureBtn = document.getElementById('manual-capture-btn');
    const statusMessage = document.getElementById('status-message');
    const liveInferenceBtn = document.getElementById('live-inference-btn');
    const imageInferenceBtn = document.getElementById('image-inference-btn');
    const customPromptTextarea = document.getElementById('custom-prompt');
    const inferenceStatus = document.getElementById('inference-status');
    const inferenceResult = document.getElementById('inference-result');
    const manualImageSelect = document.getElementById('manual-image-select');
    const refreshFilesBtn = document.getElementById('refresh-files-btn');

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

    // Live inference handler (captures from camera)
    liveInferenceBtn.addEventListener('click', async function() {
        try {
            liveInferenceBtn.disabled = true;
            inferenceStatus.textContent = 'Running live inference...';
            inferenceStatus.style.color = '#ffaa00';
            inferenceResult.textContent = 'Processing...';

            const prompt = customPromptTextarea.value.trim();
            if (!prompt) {
                inferenceStatus.textContent = '✗ Please enter a prompt';
                inferenceStatus.style.color = '#ff4444';
                liveInferenceBtn.disabled = false;
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
            liveInferenceBtn.disabled = false;
        }
    });

    // Image inference handler (uses selected image)
    imageInferenceBtn.addEventListener('click', async function() {
        try {
            const selectedFile = manualImageSelect.value;
            if (!selectedFile) {
                inferenceStatus.textContent = '✗ Please select an image';
                inferenceStatus.style.color = '#ff4444';
                return;
            }

            const prompt = customPromptTextarea.value.trim();
            if (!prompt) {
                inferenceStatus.textContent = '✗ Please enter a prompt';
                inferenceStatus.style.color = '#ff4444';
                return;
            }

            imageInferenceBtn.disabled = true;
            inferenceStatus.textContent = 'Processing selected image...';
            inferenceStatus.style.color = '#ffaa00';
            inferenceResult.textContent = 'Processing...';

            const response = await fetch('/manual_images/process_custom', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    filename: selectedFile,
                    prompt: prompt
                })
            });

            const data = await response.json();

            if (response.ok) {
                inferenceStatus.textContent = '✓ Processing complete';
                inferenceStatus.style.color = '#44ff44';
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
            imageInferenceBtn.disabled = false;
        }
    });

    // Load manual images list
    async function loadManualImages() {
        try {
            const response = await fetch('/manual_images/list');
            const data = await response.json();

            if (response.ok && data.files && data.files.length > 0) {
                manualImageSelect.innerHTML = '<option value="">-- Select an image --</option>';
                data.files.forEach(file => {
                    const option = document.createElement('option');
                    option.value = file;
                    option.textContent = file;
                    manualImageSelect.appendChild(option);
                });
                console.log(`Loaded ${data.files.length} manual images`);
            } else {
                manualImageSelect.innerHTML = '<option value="">No images found</option>';
                console.warn('No manual images found');
            }
        } catch (error) {
            console.error('Error loading manual images:', error);
            manualImageSelect.innerHTML = '<option value="">Error loading images</option>';
        }
    }

    // Refresh files button handler
    refreshFilesBtn.addEventListener('click', function() {
        loadManualImages();
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

    // Load manual images on page load
    loadManualImages();

    // Check status on load
    checkStatus();

    // Refresh status periodically
    setInterval(checkStatus, 30000); // Every 30 seconds
});