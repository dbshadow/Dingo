document.addEventListener('DOMContentLoaded', () => {
    // --- Language Options ---
    const languages = [
        { value: 'Arabic', text: 'Arabic' },
        { value: 'Chinese (Simplified)', text: 'Chinese (Simplified)' },
        { value: 'Chinese (Traditional)', text: 'Chinese (Traditional)' },
        { value: 'Dutch', text: 'Dutch' },
        { value: 'English', text: 'English' },
        { value: 'French', text: 'French' },
        { value: 'German', text: 'German' },
        { value: 'Hindi', text: 'Hindi' },
        { value: 'Indonesian', text: 'Indonesian' },
        { value: 'Italian', text: 'Italian' },
        { value: 'Japanese', text: 'Japanese' },
        { value: 'Korean', text: 'Korean' },
        { value: 'Polish', text: 'Polish' },
        { value: 'Portuguese', text: 'Portuguese' },
        { value: 'Russian', text: 'Russian' },
        { value: 'Spanish', text: 'Spanish' },
        { value: 'Swedish', text: 'Swedish' },
        { value: 'Thai', text: 'Thai' },
        { value: 'Turkish', text: 'Turkish' },
        { value: 'Vietnamese', text: 'Vietnamese' },
    ];

    // --- DOM Elements ---
    const tabLinks = document.querySelectorAll('.tab-link');
    const tabContents = document.querySelectorAll('.tab-content');
    const tokenModal = document.getElementById('token-modal');
    const tokenInput = document.getElementById('token-input');
    const tokenSubmit = document.getElementById('token-submit');
    const tokenMessage = document.getElementById('token-message');

    // CSV Translator Elements
    const form = document.getElementById('upload-form');
    const statusLog = document.getElementById('status-log');
    const csvPreview = document.getElementById('csv-preview');
    const downloadBtn = document.getElementById('download-btn');
    const submitBtn = form.querySelector('button');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    const progressBarOuter = document.querySelector('.progress-bar-outer');

    // IDML Tools Elements
    const idmlExtractForm = document.getElementById('idml-extract-form');
    const idmlRebuildForm = document.getElementById('idml-rebuild-form');
    const idmlToolsLog = document.getElementById('idml-tools-log');

    // Live Translator Elements
    const liveSourceLang = document.getElementById('live-source-lang');
    const liveTargetLang = document.getElementById('live-target-lang');
    const sourceText = document.getElementById('source-text');
    const targetText = document.getElementById('target-text');
    const translateLiveBtn = document.getElementById('translate-live-btn');

    // --- State ---
    let websocket;
    let translatedCSVContent = '';

    // --- Initialization ---
    function populateLanguageSelects() {
        const selects = document.querySelectorAll('select[id*="lang"]');
        selects.forEach(select => {
            // Clear existing options except for placeholders if any
            while (select.firstChild) {
                select.removeChild(select.firstChild);
            }
            languages.forEach(lang => {
                const option = document.createElement('option');
                option.value = lang.value;
                option.textContent = lang.text;
                select.appendChild(option);
            });
        });
        // Set defaults
        document.getElementById('source-lang').value = 'English';
        document.getElementById('target-lang').value = 'Chinese (Traditional)';
        liveSourceLang.value = 'English';
        liveTargetLang.value = 'Chinese (Traditional)';
    }

    // --- Event Listeners ---
    tabLinks.forEach(link => {
        link.addEventListener('click', () => {
            const tabId = link.dataset.tab;
            tabLinks.forEach(innerLink => innerLink.classList.remove('active'));
            link.classList.add('active');
            tabContents.forEach(content => {
                let displayStyle = 'none';
                if (content.id === tabId) {
                    displayStyle = (content.id === 'csv-translator' || content.id === 'live-translator') ? 'flex' : 'block';
                }
                content.style.display = displayStyle;
            });
        });
    });

    tokenSubmit.addEventListener('click', () => {
        const token = tokenInput.value;
        if (token) {
            localStorage.setItem('api_token', token);
            hideTokenModal();
        }
    });

    // --- Main Logic ---
    function showTokenModal(message) {
        tokenMessage.textContent = message || "Please enter the API token to use this service.";
        tokenModal.style.display = "flex";
    }

    function hideTokenModal() {
        tokenModal.style.display = "none";
    }

    async function authenticatedFetch(url, options) {
        const token = localStorage.getItem('api_token');
        if (!token) {
            showTokenModal();
            throw new Error("API Token not found.");
        }
        const headers = new Headers(options.headers || {});
        if (!options.body || !(options.body instanceof FormData)) {
            headers.append('Content-Type', 'application/json');
        }
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

    // IDML Tools Logic
    idmlExtractForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const btn = idmlExtractForm.querySelector('button');
        btn.disabled = true;
        btn.textContent = 'Extracting...';
        idmlToolsLog.innerHTML = '';
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
        idmlToolsLog.innerHTML = '';
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

    // Live Translator Logic
    translateLiveBtn.addEventListener('click', async () => {
        const text = sourceText.value.trim();
        if (!text) return;

        translateLiveBtn.disabled = true;
        targetText.value = 'Translating...';

        const payload = {
            text: text,
            source_lang: liveSourceLang.value,
            target_lang: liveTargetLang.value,
        };

        try {
            const response = await authenticatedFetch('/live_translate', {
                method: 'POST',
                body: JSON.stringify(payload),
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }
            const result = await response.json();
            targetText.value = result.translated_text;
        } catch (error) {
            targetText.value = `Error: ${error.message}`;
        } finally {
            translateLiveBtn.disabled = false;
        }
    });

    // CSV Translator Logic
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
    populateLanguageSelects();
    if (!localStorage.getItem('api_token')) {
        showTokenModal();
    }
    resetTranslatorUI();
    connectWebSocket();
});