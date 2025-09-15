document.addEventListener('DOMContentLoaded', () => {
    // --- Tab Navigation ---
    const tabLinks = document.querySelectorAll('.tab-link');
    const tabContents = document.querySelectorAll('.tab-content');

    tabLinks.forEach(link => {
        link.addEventListener('click', () => {
            const tabId = link.dataset.tab;

            tabLinks.forEach(innerLink => innerLink.classList.remove('active'));
            link.classList.add('active');

            tabContents.forEach(content => {
                // The IDML panel has a different layout, so use 'block' for it.
                if (content.id === 'idml-tools') {
                    content.style.display = content.id === tabId ? 'block' : 'none';
                } else {
                    content.style.display = content.id === tabId ? 'flex' : 'none';
                }
            });
        });
    });

    // --- CSV Translator Elements ---
    const form = document.getElementById('upload-form');
    const statusLog = document.getElementById('status-log');
    const csvPreview = document.getElementById('csv-preview');
    const downloadBtn = document.getElementById('download-btn');
    const submitBtn = form.querySelector('button');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    const progressBarOuter = document.querySelector('.progress-bar-outer');

    // --- IDML Tools Elements ---
    const idmlExtractForm = document.getElementById('idml-extract-form');
    const idmlRebuildForm = document.getElementById('idml-rebuild-form');
    const idmlToolsLog = document.getElementById('idml-tools-log'); // Shared log for IDML tools

    // --- Shared Logic (Token, Auth, etc.) ---
    const tokenModal = document.getElementById('token-modal');
    const tokenInput = document.getElementById('token-input');
    const tokenSubmit = document.getElementById('token-submit');
    const tokenMessage = document.getElementById('token-message');
    let websocket;
    let translatedCSVContent = '';

    function showTokenModal(message) {
        tokenMessage.textContent = message || "Please enter the API token to use this service.";
        tokenModal.style.display = "flex";
    }

    function hideTokenModal() {
        tokenModal.style.display = "none";
    }

    tokenSubmit.addEventListener('click', () => {
        const token = tokenInput.value;
        if (token) {
            localStorage.setItem('api_token', token);
            hideTokenModal();
        }
    });

    async function authenticatedFetch(url, options) {
        const token = localStorage.getItem('api_token');
        if (!token) {
            showTokenModal();
            throw new Error("API Token not found.");
        }
        const headers = new Headers(options.headers || {});
        headers.append('X-API-Token', token);
        options.headers = headers;
        const response = await fetch(url, options);
        if (response.status === 401) {
            localStorage.removeItem('api_token');
            showTokenModal("Token is invalid or has expired. Please enter a new one.");
            throw new Error("Authentication failed.");
        }
        return response;
    }

    function logTo(logger, message, isError = false) {
        const timestamp = new Date().toLocaleTimeString();
        const color = isError ? '#ff6b6b' : '#eee';
        logger.innerHTML += `<span style="color: ${color}">[${timestamp}] ${message}</span>\n`;
        logger.scrollTop = logger.scrollHeight;
    }

    // --- IDML Tools Event Listeners ---
    idmlExtractForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const btn = idmlExtractForm.querySelector('button');
        btn.disabled = true;
        btn.textContent = 'Extracting...';
        idmlToolsLog.innerHTML = ''; // Clear shared log
        logTo(idmlToolsLog, 'Starting IDML extraction...');

        const formData = new FormData(idmlExtractForm);

        try {
            const response = await authenticatedFetch('/extract_idml', { method: 'POST', body: formData });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }
            const blob = await response.blob();
            const filename = response.headers.get('Content-Disposition').split('filename=')[1].replace(/"/g, '');
            
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            logTo(idmlToolsLog, `Successfully extracted and downloaded ${filename}`);

        } catch (error) {
            logTo(idmlToolsLog, `Extraction failed: ${error.message}`, true);
        } finally {
            btn.disabled = false;
            btn.textContent = 'Extract to CSV';
        }
    });

    idmlRebuildForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const btn = idmlRebuildForm.querySelector('button');
        btn.disabled = true;
        btn.textContent = 'Rebuilding...';
        idmlToolsLog.innerHTML = ''; // Clear shared log
        logTo(idmlToolsLog, 'Starting IDML rebuild...');

        const formData = new FormData(idmlRebuildForm);

        try {
            const response = await authenticatedFetch('/rebuild_idml', { method: 'POST', body: formData });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }
            const blob = await response.blob();
            const filename = response.headers.get('Content-Disposition').split('filename=')[1].replace(/"/g, '');
            
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            logTo(idmlToolsLog, `Successfully rebuilt and downloaded ${filename}`);

        } catch (error) {
            logTo(idmlToolsLog, `Rebuild failed: ${error.message}`, true);
        } finally {
            btn.disabled = false;
            btn.textContent = 'Rebuild IDML';
        }
    });

    // --- CSV Translator Logic ---
    function resetTranslatorUI() {
        submitBtn.disabled = false;
        downloadBtn.disabled = true;
        csvPreview.innerHTML = '<p style="color: #888;">Translation preview will be shown here.</p>';
        statusLog.innerHTML = '';
        progressBar.style.width = '0%';
        progressText.textContent = '0%';
        progressBarOuter.classList.remove('progress-bar-animated');
    }

    function renderTable(jsonData) {
        if (!jsonData || jsonData.length === 0) return;
        const table = document.createElement('table');
        const thead = document.createElement('thead');
        const tbody = document.createElement('tbody');
        const headers = Object.keys(jsonData[0]);
        const headerRow = document.createElement('tr');
        headers.forEach(headerText => {
            const th = document.createElement('th');
            th.textContent = headerText;
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);
        jsonData.forEach(row => {
            const tr = document.createElement('tr');
            headers.forEach(header => {
                const td = document.createElement('td');
                td.textContent = row[header];
                if (header.toLowerCase() === 'target') td.classList.add('target-column');
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });
        table.appendChild(thead);
        table.appendChild(tbody);
        csvPreview.innerHTML = '';
        csvPreview.appendChild(table);
    }

    function connectWebSocket() {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}/ws`;
        websocket = new WebSocket(wsUrl);
        websocket.onopen = () => logTo(statusLog, 'WebSocket connection established.');
        websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            const payload = data.payload;
            switch (data.type) {
                case 'log': logTo(statusLog, payload.message); break;
                case 'error': logTo(statusLog, `ERROR: ${payload.message}`, true); resetTranslatorUI(); break;
                case 'progress':
                    translatedCSVContent = payload.csv_string;
                    renderTable(payload.csv_json);
                    downloadBtn.disabled = false;
                    const { total, processed } = payload;
                    const percentage = total > 0 ? Math.round((processed / total) * 100) : 100;
                    progressBar.style.width = `${percentage}%`;
                    progressText.textContent = `${percentage}%`;
                    if (percentage >= 100) {
                        submitBtn.disabled = false;
                        progressBarOuter.classList.remove('progress-bar-animated');
                    }
                    break;
            }
        };
        websocket.onclose = () => { logTo(statusLog, 'WebSocket connection closed. Please refresh the page to reconnect.', true); submitBtn.disabled = true; };
        websocket.onerror = (error) => { logTo(statusLog, 'WebSocket error. See console for details.', true); console.error('WebSocket Error:', error); };
    }

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        resetTranslatorUI();
        submitBtn.disabled = true;
        progressBarOuter.classList.add('progress-bar-animated');
        logTo(statusLog, 'Starting translation process...');
        const formData = new FormData(form);
        try {
            const response = await authenticatedFetch('/upload', { method: 'POST', body: formData });
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const result = await response.json();
            logTo(statusLog, `Backend task started with ID: ${result.task_id}`);
            websocket.send(JSON.stringify({ task_id: result.task_id }));
        } catch (error) {
            logTo(statusLog, `Upload failed: ${error.message}`, true);
            resetTranslatorUI();
        }
    });

    downloadBtn.addEventListener('click', () => {
        if (translatedCSVContent) {
            const blob = new Blob([translatedCSVContent], { type: 'text/csv;charset=utf-8-sig;' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'translated.csv';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
    });

    // --- Initial Load ---
    if (!localStorage.getItem('api_token')) {
        showTokenModal();
    }
    resetTranslatorUI();
    connectWebSocket();
});
