document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const form = document.getElementById('upload-form');
    const statusLog = document.getElementById('status-log');
    const csvPreview = document.getElementById('csv-preview');
    const downloadBtn = document.getElementById('download-btn');
    const submitBtn = form.querySelector('button');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    const progressBarOuter = document.querySelector('.progress-bar-outer'); // 取得動畫目標
    const tokenModal = document.getElementById('token-modal');
    const tokenInput = document.getElementById('token-input');
    const tokenSubmit = document.getElementById('token-submit');
    const tokenMessage = document.getElementById('token-message');

    // State
    let websocket;
    let translatedCSVContent = '';

    // --- Token Modal Logic ---
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

    // --- Authenticated Fetch ---
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

    // --- UI & WebSocket Logic ---
    function log(message) {
        const timestamp = new Date().toLocaleTimeString();
        statusLog.innerHTML += `[${timestamp}] ${message}\n`;
        statusLog.scrollTop = statusLog.scrollHeight;
    }

    function resetUI() {
        submitBtn.disabled = false;
        downloadBtn.disabled = true;
        csvPreview.innerHTML = '<p style="color: #888;">翻譯預覽將顯示於此</p>';
        statusLog.innerHTML = '';
        progressBar.style.width = '0%';
        progressText.textContent = '0%';
        progressBarOuter.classList.remove('progress-bar-animated'); // 移除動畫
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
        websocket.onopen = () => log('WebSocket connection established.');
        websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            const payload = data.payload;
            switch (data.type) {
                case 'log':
                    log(payload.message);
                    break;
                case 'error':
                    log(`ERROR: ${payload.message}`);
                    resetUI();
                    break;
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
                        progressBarOuter.classList.remove('progress-bar-animated'); // 完成後移除動畫
                    }
                    break;
            }
        };
        websocket.onclose = () => {
            log('WebSocket connection closed. Please refresh the page to reconnect.');
            submitBtn.disabled = true;
        };
        websocket.onerror = (error) => {
            log('WebSocket error. See console for details.');
            console.error('WebSocket Error:', error);
        };
    }

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        resetUI();
        submitBtn.disabled = true;
        progressBarOuter.classList.add('progress-bar-animated'); // 開始時加入動畫
        log('Starting translation process...');

        const formData = new FormData(form);

        try {
            const response = await authenticatedFetch('/upload', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

            const result = await response.json();
            log(`Backend task started with ID: ${result.task_id}`);
            websocket.send(JSON.stringify({ task_id: result.task_id }));
        } catch (error) {
            log(`Upload failed: ${error.message}`);
            resetUI();
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
    resetUI();
    connectWebSocket();
});
