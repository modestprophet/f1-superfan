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
    const confYear = document.getElementById('conf-year');
    const confRaceNum = document.getElementById('conf-race-num');
    const confCircuit = document.getElementById('conf-circuit');
    const confRaceId = document.getElementById('conf-race-id');
    const saveConfigBtn = document.getElementById('save-config-btn');
    const configStatus = document.getElementById('config-status');

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

    // Load Race Configuration
    async function loadRaceConfig() {
        try {
            const response = await fetch('/api/race_config');
            const data = await response.json();

            if (response.ok && !data.error) {
                confYear.value = data.year || '';
                confRaceNum.value = data.race_number || '';
                confCircuit.value = data.circuit_name || '';
                confRaceId.value = data.race_id || '';
            }
        } catch (error) {
            console.error('Error loading config:', error);
        }
    }

    // Save Race Configuration
saveConfigBtn.addEventListener('click', async function() {
        try {
            saveConfigBtn.disabled = true;
            configStatus.textContent = 'Saving...';
            configStatus.style.color = '#ffaa00';

            const payload = {};

            // Only include non-empty values
            if (confYear.value.trim()) payload.year = confYear.value.trim();
            if (confRaceNum.value.trim()) payload.race_number = confRaceNum.value.trim();
            if (confCircuit.value.trim()) payload.circuit_name = confCircuit.value.trim();
            if (confRaceId.value.trim()) payload.race_id = confRaceId.value.trim();

            const response = await fetch('/api/race_config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (response.ok) {
                configStatus.textContent = '✓ Saved';
                configStatus.style.color = '#44ff44';
                setTimeout(() => {
                    configStatus.textContent = '';
                }, 3000);
            } else {
                configStatus.textContent = `✗ Error: ${data.error}`;
                configStatus.style.color = '#ff4444';
            }

        } catch (error) {
            configStatus.textContent = `✗ Error: ${error.message}`;
            configStatus.style.color = '#ff4444';
        } finally {
            saveConfigBtn.disabled = false;
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


    // Load Race Config on load
    loadRaceConfig();

    // Refresh status periodically
    setInterval(checkStatus, 30000); // Every 30 seconds
});