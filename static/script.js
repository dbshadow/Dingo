document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('upload-form');
    const statusLog = document.getElementById('status-log');
    const csvPreview = document.getElementById('csv-preview');
    const downloadBtn = document.getElementById('download-btn');
    const submitBtn = form.querySelector('button');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');

    let websocket;
    let translatedCSVContent = ''; // 用於儲存原始CSV字串以供下載

    function log(message) {
        const timestamp = new Date().toLocaleTimeString();
        statusLog.innerHTML += `[${timestamp}] ${message}
`;
        statusLog.scrollTop = statusLog.scrollHeight;
    }

    function resetUI() {
        submitBtn.disabled = false;
        downloadBtn.disabled = true;
        csvPreview.innerHTML = '<p style="color: #888;">翻譯預覽將顯示於此</p>';
        statusLog.innerHTML = '';
        progressBar.style.width = '0%';
        progressText.textContent = '0%';
    }

    function renderTable(jsonData) {
        if (!jsonData || jsonData.length === 0) {
            return;
        }

        const table = document.createElement('table');
        const thead = document.createElement('thead');
        const tbody = document.createElement('tbody');
        const headers = Object.keys(jsonData[0]);

        // 建立表頭
        const headerRow = document.createElement('tr');
        headers.forEach(headerText => {
            const th = document.createElement('th');
            th.textContent = headerText;
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);

        // 建立表格內容
        jsonData.forEach(row => {
            const tr = document.createElement('tr');
            headers.forEach(header => {
                const td = document.createElement('td');
                td.textContent = row[header];
                if (header.toLowerCase() === 'target') {
                    td.classList.add('target-column');
                }
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });

        table.appendChild(thead);
        table.appendChild(tbody);

        // 清空並渲染
        csvPreview.innerHTML = '';
        csvPreview.appendChild(table);
    }

    function connectWebSocket() {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}/ws`;
        websocket = new WebSocket(wsUrl);

        websocket.onopen = () => {
            log('WebSocket connection established.');
            submitBtn.disabled = false;
        };

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
                    // 儲存原始CSV字串以供下載
                    translatedCSVContent = payload.csv_string;
                    // 渲染表格
                    renderTable(payload.csv_json);
                    downloadBtn.disabled = false;

                    const total = payload.total;
                    const processed = payload.processed;
                    const percentage = total > 0 ? Math.round((processed / total) * 100) : 100;
                    
                    progressBar.style.width = `${percentage}%`;
                    progressText.textContent = `${percentage}%`;

                    if (percentage === 100) {
                        submitBtn.disabled = false;
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
        log('Starting translation process...');

        const formData = new FormData(form);

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

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

    submitBtn.disabled = true;
    resetUI();
    connectWebSocket();
});