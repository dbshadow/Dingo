document.addEventListener('DOMContentLoaded', () => {
    // --- Shared State & Elements ---
    const tokenModal = document.getElementById('token-modal');
    const tokenInput = document.getElementById('token-input');
    const tokenSubmit = document.getElementById('token-submit');
    const tokenMessage = document.getElementById('token-message');

    // --- Language Setup ---
    const languages = [
        { value: 'en', text: 'English (en)' },
        { value: 'de', text: 'German (de)' },
        { value: 'fr-FR', text: 'French (fr-FR)' },
        { value: 'es', text: 'Spanish (es)' },
        { value: 'it', text: 'Italian (it)' },
        { value: 'nl', text: 'Dutch (nl)' },
        { value: 'pl', text: 'Polish (pl)' },
        { value: 'cs', text: 'Czech (cs)' },
        { value: 'hu', text: 'Hungarian (hu)' },
        { value: 'nn', text: 'Nynorsk (nn)' },
        { value: 'da', text: 'Danish (da)' },
        { value: 'fi', text: 'Finnish (fi)' },
        { value: 'sv', text: 'Swedish (sv)' },
        { value: 'pt-PT', text: 'Portugal Portuguese (pt-PT)' },
        { value: 'el', text: 'Greek (el)' },
        { value: 'ro', text: 'Romanian (ro)' },
        { value: 'hr', text: 'Croatian (hr)' },
        { value: 'sl', text: 'Slovenian (sl)' },
        { value: 'lt', text: 'Lithuanian (lt)' },
        { value: 'lv', text: 'Latvian (lv)' },
        { value: 'et', text: 'Estonian (et)' },
        { value: 'sk', text: 'Slovak (sk)' },
        { value: 'is', text: 'Icelandic (is)' },
        { value: 'bg', text: 'Bulgarian (bg)' },
        { value: 'mt', text: 'Maltese (mt)' },
        { value: 'ru', text: 'Russian (ru)' },
        { value: 'es-419', text: 'Latin Spanish (es-419)' },   // 419 = Latin America
        { value: 'pt-BR', text: 'Brazil Portuguese (pt-BR)' },
        { value: 'th', text: 'Thai (th)' },
        { value: 'id', text: 'Indonesian (id)' },
        { value: 'ms', text: 'Malay (ms)' },
        { value: 'tr', text: 'Turkish (tr)' },
        { value: 'ja', text: 'Japanese (ja)' },
        { value: 'zh-Hant', text: 'Traditional Chinese (zh-Hant)' },
        { value: 'zh-Hans', text: 'Simplified Chinese (zh-Hans)' },
        { value: 'fr-CA', text: 'Canada French (fr-CA)' }
    ];

    function populateLanguageSelects() {
        document.querySelectorAll('select[id*="lang"]').forEach(select => {
            languages.forEach(lang => {
                const option = document.createElement('option');
                option.value = lang.value;
                option.textContent = lang.text;
                select.appendChild(option);
            });
        });
        document.getElementById('source-lang').value = 'en';
        document.getElementById('target-lang').value = 'zh-Hant';
        document.getElementById('live-source-lang').value = 'en';
        document.getElementById('live-target-lang').value = 'zh-Hant';
    }

    // --- Authentication ---
    function showTokenModal(message) {
        tokenMessage.textContent = message || "Please enter the API token to use this service.";
        tokenModal.style.display = "flex";
    }

    function hideTokenModal() {
        document.getElementById('token-modal').style.display = "none";
    }

    tokenSubmit.addEventListener('click', () => {
        const token = tokenInput.value;
        if (token) {
            localStorage.setItem('api_token', token);
            hideTokenModal();
            fetchDefaultPrompt(); // Fetch prompt after getting token
        }
    });

    async function authenticatedFetch(url, options) {
        const token = localStorage.getItem('api_token');
        if (!token) {
            showTokenModal();
            throw new Error("API Token not found.");
        }
        const headers = new Headers(options.headers || {});
        if (options.body && !(options.body instanceof FormData)) {
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

    // --- Prompt Fetching ---
    async function fetchDefaultPrompt() {
        const displayElement = document.getElementById('default-prompt-display');
        if (!displayElement) return;
        try {
            const response = await authenticatedFetch('/prompt/default', { method: 'GET' });
            if (!response.ok) throw new Error('Failed to fetch default prompt.');
            const data = await response.json();
            displayElement.textContent = data.template;
        } catch (error) {
            console.error(error.message);
            displayElement.textContent = 'Could not load prompt template. Please ensure you are logged in.';
        }
    }

    // --- Tab Navigation ---
    document.querySelector('.tabs').addEventListener('click', (event) => {
        if (!event.target.matches('.tab-link')) return;

        const tabId = event.target.dataset.tab;
        document.querySelectorAll('.tab-link').forEach(link => link.classList.remove('active'));
        event.target.classList.add('active');

        document.querySelectorAll('.tab-content').forEach(content => {
            let displayStyle = 'none';
            if (content.id === tabId) {
                displayStyle = (content.id === 'csv-translator' || content.id === 'live-translator') ? 'flex' : 'block';
            }
            content.style.display = displayStyle;
        });
    });

    // --- Event Delegation for Forms & Actions ---
    document.body.addEventListener('submit', async (event) => {
        // --- CSV Translator Form ---
        if (event.target.id === 'upload-form') {
            event.preventDefault();
            const form = event.target;
            const submitBtn = form.querySelector('button');
            const sourceLangEl = document.getElementById('source-lang');
            const targetLangEl = document.getElementById('target-lang');
            const overwriteEl = document.getElementById('overwrite');

            // Store current settings
            const lastSettings = {
                sourceLang: sourceLangEl.value,
                targetLang: targetLangEl.value,
                overwrite: overwriteEl.checked
            };

            submitBtn.disabled = true;
            submitBtn.textContent = 'Uploading...';
            const formData = new FormData(form);
            try {
                                const response = await authenticatedFetch('/tasks/upload', { method: 'POST', body: formData });
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'Upload failed');
                }
                form.reset();
            } catch (error) {
                alert(`Upload failed: ${error.message}`);
            } finally {
                sourceLangEl.value = lastSettings.sourceLang
                targetLangEl.value = lastSettings.targetLang;
                overwriteEl.checked = lastSettings.overwrite;
                submitBtn.disabled = false;
                submitBtn.textContent = 'Add to Queue';
            }
        }

        // --- IDML Extract Form ---
        if (event.target.id === 'idml-extract-form') {
            event.preventDefault();
            // This logic is now handled by the initializeIdmlTools function
        }

        // --- IDML Rebuild Form ---
        if (event.target.id === 'idml-rebuild-form') {
            event.preventDefault();
            // This logic is now handled by the initializeIdmlTools function
        }
    });

    document.body.addEventListener('click', async (event) => {
        // --- Live Translator Button ---
        if (event.target.id === 'translate-live-btn') {
            // This logic is now handled by the initializeLiveTranslator function
        }

        // --- CSV Task List Buttons ---
        if (event.target.matches('.action-btn')) {
            const btn = event.target.closest('.action-btn');
            const taskId = btn.dataset.taskId;
            if (!taskId) return;

            if (btn.classList.contains('delete-btn')) {
                if (!confirm('Are you sure you want to delete this task and its files?')) return;
                try {
                    await authenticatedFetch(`/tasks/${taskId}`, { method: 'DELETE' });
                } catch (error) {
                    alert(`Failed to delete task: ${error.message}`);
                }
            }

            if (btn.classList.contains('download-btn')) {
                try {
                    const response = await authenticatedFetch(`/tasks/download/${taskId}`, { method: 'GET' });
                    if (!response.ok) throw new Error('Download failed');
                    const blob = await response.blob();
                    const disposition = response.headers.get('Content-Disposition');
                    let filename = 'download'; // Default filename
                    if (disposition) {
                        const filenameRegex = /filename*"=UTF-8''([^;]+)/i;
                        const filenameMatch = disposition.match(filenameRegex);
                        if (filenameMatch && filenameMatch[1]) {
                            filename = decodeURIComponent(filenameMatch[1]);
                        } else {
                            const basicFilenameRegex = /filename="?([^"]+)"?/i;
                            const basicFilenameMatch = disposition.match(basicFilenameRegex);
                            if (basicFilenameMatch && basicFilenameMatch[1]) {
                                filename = basicFilenameMatch[1];
                            }
                        }
                    }
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = filename;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                } catch (error) {
                    alert(`Download failed: ${error.message}`);
                }
            }
        }
        
        // --- Note Toggling ---
        if (event.target.matches('.filename-toggle')) {
            event.preventDefault();
            const taskId = event.target.dataset.taskId;
            const noteRow = document.querySelector(`.note-row[data-task-id="${taskId}"]`);
            if (noteRow) {
                const isVisible = noteRow.style.display !== 'none';
                noteRow.style.display = isVisible ? 'none' : 'table-row';
            }
        }
    });

    // --- WebSocket & CSV Task Rendering ---
    function initCsvTranslatorWebSocket() {
        const taskListBody = document.getElementById('task-list-body');
        if (!taskListBody) return;

        function renderTasks(tasks) {
            taskListBody.innerHTML = '';
            if (!tasks || tasks.length === 0) {
                taskListBody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:#888;">No tasks in the queue.</td></tr>';
                return;
            }

            tasks.forEach(task => {
                const progress = task.progress || { processed: 0, total: 0 };
                const percentage = progress.total > 0 ? Math.round((progress.processed / progress.total) * 100) : 0;
                const isRunning = task.status === 'running';
                const isError = task.status === 'error';
                const hasNote = task.note && task.note.trim() !== '';

                // Main task row
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>
                        ${hasNote 
                            ? `<a href="#" class="filename-toggle filename-link" data-task-id="${task.id}">${task.filename}</a>` 
                            : task.filename
                        }
                    </td>
                    <td>
                        <div class="progress-container">
                            <div class="progress-bar-outer ${isRunning ? 'progress-bar-animated' : ''}">
                                <div class="progress-bar-inner" style="width: ${percentage}%; background-color: ${isError ? '#ff6b6b' : 'var(--md-primary-fg-color)'};"></div>
                            </div>
                            <span class="progress-text">${isError ? 'Error' : percentage + '%'}</span>
                        </div>
                    </td>
                    <td>
                        <button class="action-btn download-btn" data-task-id="${task.id}" title="Download">&#x21E9;</button>
                    </td>
                    <td>
                        <button class="action-btn delete-btn" data-task-id="${task.id}" title="Delete">&#x1F5D1;</button>
                    </td>
                `;
                taskListBody.appendChild(row);

                // Note row (if note exists)
                if (hasNote) {
                    const noteRow = document.createElement('tr');
                    noteRow.className = 'note-row';
                    noteRow.dataset.taskId = task.id;
                    noteRow.style.display = 'none'; // Initially hidden
                    noteRow.innerHTML = `
                        <td colspan="4" class="note-content">
                            ${task.note.replace(/\n/g, '<br>')}
                        </td>
                    `;
                    taskListBody.appendChild(noteRow);
                }
            });
        }

        async function fetchAndRenderTasks() {
            try {
                const response = await authenticatedFetch('/tasks/', { method: 'GET' });
                if (!response.ok) throw new Error('Failed to fetch tasks');
                const tasks = await response.json();
                renderTasks(tasks);
            } catch (error) {
                console.error(error.message);
            }
        }

        function connectWebSocket() {
            const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${wsProtocol}//${window.location.host}/ws`;
            const websocket = new WebSocket(wsUrl);
            websocket.onopen = () => {
                console.log('Task queue connection established.');
                fetchAndRenderTasks();
            };
            websocket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'tasks_update') {
                    renderTasks(data.payload);
                }
            };
            websocket.onclose = () => { console.log('Task queue connection closed. Auto-reconnect in 5s.'); setTimeout(connectWebSocket, 5000); };
            websocket.onerror = () => console.error('WebSocket error.');
        }

        connectWebSocket();
    }
    
    function logTo(logger, message, isError = false) {
        const timestamp = new Date().toLocaleTimeString();
        const color = isError ? '#ff6b6b' : '#eee';
        logger.innerHTML += `<span style="color: ${color}">[${timestamp}] ${message}</span>\n`;
        logger.scrollTop = logger.scrollHeight;
    }

    // --- Initial Load ---
    populateLanguageSelects();
    if (localStorage.getItem('api_token')) {
        fetchDefaultPrompt();
    } else {
        showTokenModal();
    }
    initCsvTranslatorWebSocket();
    initializeIdmlTools(authenticatedFetch, logTo);
    initializeLiveTranslator(authenticatedFetch);
});

function initializeIdmlTools(authenticatedFetch, logTo) {
    const extractForm = document.getElementById('idml-extract-form');
    const rebuildForm = document.getElementById('idml-rebuild-form');
    const logEl = document.getElementById('idml-tools-log');

    if (!extractForm || !rebuildForm || !logEl) return;

    extractForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const btn = extractForm.querySelector('button');
        btn.disabled = true;
        btn.textContent = 'Extracting...';
        logEl.innerHTML = '';
        logTo(logEl, 'Starting IDML extraction...');
        const formData = new FormData(extractForm);
        try {
            const response = await authenticatedFetch('/idml/extract', { method: 'POST', body: formData });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }
            const blob = await response.blob();
            const disposition = response.headers.get('Content-Disposition');
            const match = disposition && disposition.match(/filename="?([^"]+)"?/);
            const filename = match ? match[1] : 'extracted.csv';
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            logTo(logEl, `Successfully extracted and downloaded ${filename}`);
        } catch (error) {
            logTo(logEl, `Extraction failed: ${error.message}`, true);
        } finally {
            btn.disabled = false;
            btn.textContent = 'Extract to CSV';
        }
    });

    rebuildForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const btn = rebuildForm.querySelector('button');
        btn.disabled = true;
        btn.textContent = 'Rebuilding...';
        logEl.innerHTML = '';
        logTo(logEl, 'Starting IDML rebuild...');
        const formData = new FormData(rebuildForm);
        try {
            const response = await authenticatedFetch('/idml/rebuild', { method: 'POST', body: formData });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }
            const blob = await response.blob();
            const disposition = response.headers.get('Content-Disposition');
            const match = disposition && disposition.match(/filename="?([^"]+)"?/);
            const filename = match ? match[1] : 'rebuilt.idml';
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            logTo(logEl, `Successfully rebuilt and downloaded ${filename}`);
        } catch (error) {
            logTo(logEl, `Rebuild failed: ${error.message}`, true);
        } finally {
            btn.disabled = false;
            btn.textContent = 'Rebuild IDML';
        }
    });
}

function initializeLiveTranslator(authenticatedFetch) {
    const translateBtn = document.getElementById('translate-live-btn');
    if (!translateBtn) return;

    translateBtn.addEventListener('click', async () => {
        const sourceText = document.getElementById('source-text');
        const targetText = document.getElementById('target-text');
        const text = sourceText.value.trim();
        if (!text) return;

        translateBtn.disabled = true;
        targetText.value = 'Translating...';

        try {
            const response = await authenticatedFetch('/live_translate', { 
                method: 'POST',
                body: JSON.stringify({
                    text: text,
                    source_lang: document.getElementById('live-source-lang').value,
                    target_lang: document.getElementById('live-target-lang').value,
                }),
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
            translateBtn.disabled = false;
        }
    });
}
