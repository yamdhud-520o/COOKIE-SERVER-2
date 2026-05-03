from flask import Flask, request, render_template, jsonify, session
import requests
import time
import threading
import os
import json
from datetime import datetime
import signal
import sys

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-this'

# Global variables to control the sending process
sending_active = False
sending_thread = None
current_session_data = {}

headers = {
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8',
    'referer': 'www.google.com'
}

def token_checker(access_token):
    """Check if a token is valid"""
    try:
        url = f"https://graph.facebook.com/v15.0/me?access_token={access_token}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return True, data.get('name', 'Unknown')
        return False, None
    except:
        return False, None

def extract_messages_from_chat(access_token, thread_id, limit=50):
    """Extract messages from a messenger chat"""
    try:
        url = f"https://graph.facebook.com/v15.0/t_{thread_id}/messages"
        params = {
            'access_token': access_token,
            'limit': limit,
            'fields': 'message,created_time,from'
        }
        response = requests.get(url, params=params, timeout=10)
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

def send_message_worker(thread_id, mn, time_interval, access_tokens, messages, haters_name):
    """Background worker for sending messages"""
    global sending_active, current_session_data
    
    num_comments = len(messages)
    max_tokens = len(access_tokens)
    post_url = f'https://graph.facebook.com/v15.0/t_{thread_id}/'
    
    message_index = 0
    
    while sending_active:
        try:
            for message_index in range(num_comments):
                if not sending_active:
                    break
                    
                token_index = message_index % max_tokens
                access_token = access_tokens[token_index]
                message = messages[message_index].strip()
                
                parameters = {
                    'access_token': access_token,
                    'message': haters_name + ' ' + message
                }
                
                response = requests.post(post_url, json=parameters, headers=headers, timeout=30)
                current_time = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
                
                current_session_data['total_sent'] = current_session_data.get('total_sent', 0) + 1
                
                if response.ok:
                    current_session_data['success'] = current_session_data.get('success', 0) + 1
                    print(f"[+] SUCCESS - Message {message_index + 1} | Token {token_index + 1} | Time: {current_time}")
                else:
                    current_session_data['failed'] = current_session_data.get('failed', 0) + 1
                    print(f"[x] FAILED - Message {message_index + 1} | Token {token_index + 1} | Time: {current_time}")
                
                current_session_data['last_message'] = f"{haters_name} {message}"
                current_session_data['last_time'] = current_time
                
                time.sleep(time_interval)
                
        except Exception as e:
            print(f"Error in sending loop: {e}")
            current_session_data['errors'] = current_session_data.get('errors', 0) + 1
            time.sleep(30)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_sending', methods=['POST'])
def start_sending():
    global sending_active, sending_thread, current_session_data
    
    if sending_active:
        return jsonify({'status': 'error', 'message': 'Sending already in progress!'})
    
    thread_id = request.form.get('threadId')
    haters_name = request.form.get('kidx')
    time_interval = int(request.form.get('time'))
    
    txt_file = request.files['txtFile']
    access_tokens = txt_file.read().decode().splitlines()
    
    messages_file = request.files['messagesFile']
    messages = messages_file.read().decode().splitlines()
    
    # Validate tokens
    valid_tokens = []
    for token in access_tokens:
        is_valid, name = token_checker(token)
        if is_valid:
            valid_tokens.append(token)
    
    if len(valid_tokens) == 0:
        return jsonify({'status': 'error', 'message': 'No valid tokens found!'})
    
    current_session_data = {
        'total_sent': 0,
        'success': 0,
        'failed': 0,
        'errors': 0,
        'active': True,
        'thread_id': thread_id,
        'haters_name': haters_name,
        'valid_tokens': len(valid_tokens),
        'messages_count': len(messages)
    }
    
    sending_active = True
    sending_thread = threading.Thread(
        target=send_message_worker,
        args=(thread_id, haters_name, time_interval, valid_tokens, messages, haters_name)
    )
    sending_thread.daemon = True
    sending_thread.start()
    
    return jsonify({'status': 'success', 'message': 'Sending started successfully!'})

@app.route('/stop_sending', methods=['POST'])
def stop_sending():
    global sending_active, current_session_data
    
    if not sending_active:
        return jsonify({'status': 'error', 'message': 'No active sending process!'})
    
    sending_active = False
    current_session_data['active'] = False
    
    return jsonify({'status': 'success', 'message': 'Sending stopped successfully!'})

@app.route('/status', methods=['GET'])
def get_status():
    global sending_active, current_session_data
    
    return jsonify({
        'active': sending_active,
        'stats': current_session_data
    })

@app.route('/check_tokens', methods=['POST'])
def check_tokens():
    """Check validity of Facebook access tokens"""
    if 'txtFile' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file uploaded!'})
    
    txt_file = request.files['txtFile']
    access_tokens = txt_file.read().decode().splitlines()
    
    results = []
    valid_count = 0
    
    for i, token in enumerate(access_tokens[:20]):  # Limit to 20 tokens for performance
        is_valid, name = token_checker(token)
        if is_valid:
            valid_count += 1
            results.append({'index': i+1, 'valid': True, 'name': name})
        else:
            results.append({'index': i+1, 'valid': False, 'name': None})
    
    return jsonify({
        'status': 'success',
        'total': len(access_tokens[:20]),
        'valid': valid_count,
        'results': results
    })

@app.route('/extract_messages', methods=['POST'])
def extract_messages():
    """Extract messages from a messenger chat"""
    thread_id = request.form.get('threadId')
    access_token = request.form.get('accessToken')
    limit = int(request.form.get('limit', 50))
    
    if not thread_id or not access_token:
        return jsonify({'status': 'error', 'message': 'Thread ID and Access Token required!'})
    
    is_valid, name = token_checker(access_token)
    if not is_valid:
        return jsonify({'status': 'error', 'message': 'Invalid access token!'})
    
    success, messages = extract_messages_from_chat(access_token, thread_id, limit)
    
    if success:
        return jsonify({
            'status': 'success',
            'count': len(messages),
            'messages': messages
        })
    else:
        return jsonify({'status': 'error', 'message': 'Failed to extract messages!'})

# HTML Template
with open('templates/index.html', 'w') as f:
    f.write('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Xmarty Ayush King - Complete Facebook Tool</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            background: linear-gradient(135deg, #2d5016 0%, #1a3009 100%);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            color: #ffd700;
            margin-bottom: 30px;
            padding: 20px;
            background: rgba(0,0,0,0.3);
            border-radius: 15px;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header p {
            color: #ffeb3b;
            font-size: 1.1em;
        }
        
        .feature-menu {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .feature-card {
            background: rgba(0,0,0,0.8);
            border-radius: 15px;
            padding: 20px;
            cursor: pointer;
            transition: transform 0.3s, box-shadow 0.3s;
            border: 2px solid #ffd700;
        }
        
        .feature-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(255,215,0,0.3);
        }
        
        .feature-card.active {
            background: rgba(255,215,0,0.2);
            border-color: #ffeb3b;
        }
        
        .feature-card h3 {
            color: #ffd700;
            margin-bottom: 10px;
            font-size: 1.5em;
        }
        
        .feature-card p {
            color: #ddd;
            font-size: 0.9em;
        }
        
        .feature-icon {
            font-size: 2em;
            margin-bottom: 10px;
        }
        
        .panel {
            background: rgba(0,0,0,0.85);
            border-radius: 15px;
            padding: 30px;
            margin-top: 20px;
            border: 1px solid #ffd700;
        }
        
        .panel h2 {
            color: #ffd700;
            margin-bottom: 20px;
            font-size: 1.8em;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        label {
            color: #ffd700;
            display: block;
            margin-bottom: 8px;
            font-weight: bold;
        }
        
        input, select, textarea {
            width: 100%;
            padding: 12px;
            background: rgba(255,255,255,0.1);
            border: 1px solid #ffd700;
            border-radius: 8px;
            color: white;
            font-size: 14px;
        }
        
        input:focus, select:focus, textarea:focus {
            outline: none;
            border-color: #ffeb3b;
            background: rgba(255,255,255,0.15);
        }
        
        button {
            background: linear-gradient(135deg, #ffd700 0%, #ffed4e 100%);
            color: #2d5016;
            padding: 12px 30px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
            transition: transform 0.2s;
        }
        
        button:hover {
            transform: scale(1.05);
        }
        
        button.danger {
            background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
            color: white;
        }
        
        button.success {
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            color: white;
        }
        
        .status-bar {
            background: rgba(0,0,0,0.9);
            padding: 15px;
            border-radius: 10px;
            margin-top: 20px;
            border-left: 4px solid #ffd700;
        }
        
        .status-bar h4 {
            color: #ffd700;
            margin-bottom: 10px;
        }
        
        .status-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 10px;
        }
        
        .stat-card {
            background: rgba(255,215,0,0.1);
            padding: 10px;
            border-radius: 8px;
            text-align: center;
        }
        
        .stat-card .stat-value {
            color: #ffd700;
            font-size: 1.5em;
            font-weight: bold;
        }
        
        .stat-card .stat-label {
            color: #ddd;
            font-size: 0.85em;
            margin-top: 5px;
        }
        
        .results {
            margin-top: 20px;
            max-height: 400px;
            overflow-y: auto;
        }
        
        .message-item {
            background: rgba(255,255,255,0.05);
            padding: 10px;
            margin: 5px 0;
            border-radius: 5px;
            border-left: 3px solid #ffd700;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.7; }
            100% { opacity: 1; }
        }
        
        .sending-active {
            animation: pulse 1s infinite;
            color: #28a745;
        }
        
        @media (max-width: 768px) {
            .feature-menu {
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
            <p>Complete Facebook Automation Suite | 24/7 Operation | 365 Days Uptime</p>
        </div>
        
        <div class="feature-menu">
            <div class="feature-card" onclick="showFeature('sender')">
                <div class="feature-icon">📨</div>
                <h3>Message Sender</h3>
                <p>Send mass messages automatically with multiple tokens</p>
            </div>
            <div class="feature-card" onclick="showFeature('checker')">
                <div class="feature-icon">✅</div>
                <h3>Token Checker</h3>
                <p>Check validity of Facebook access tokens</p>
            </div>
            <div class="feature-card" onclick="showFeature('extractor')">
                <div class="feature-icon">💬</div>
                <h3>Chat Extractor</h3>
                <p>Extract messages from any messenger chat</p>
            </div>
            <div class="feature-card" onclick="showFeature('status')">
                <div class="feature-icon">📊</div>
                <h3>Status Check</h3>
                <p>Monitor sending status and statistics</p>
            </div>
        </div>
        
        <!-- Message Sender Panel -->
        <div id="senderPanel" class="panel" style="display: none;">
            <h2>📨 Mass Message Sender</h2>
            <form id="senderForm" enctype="multipart/form-data">
                <div class="form-group">
                    <label>Conversation ID:</label>
                    <input type="text" name="threadId" required placeholder="Enter thread/conversation ID">
                </div>
                <div class="form-group">
                    <label>Tokens File (.txt):</label>
                    <input type="file" name="txtFile" accept=".txt" required>
                </div>
                <div class="form-group">
                    <label>Messages File (.txt):</label>
                    <input type="file" name="messagesFile" accept=".txt" required>
                </div>
                <div class="form-group">
                    <label>Hater Name/Prefix:</label>
                    <input type="text" name="kidx" required placeholder="Enter prefix for messages">
                </div>
                <div class="form-group">
                    <label>Speed (seconds between messages):</label>
                    <input type="number" name="time" value="60" required>
                </div>
                <button type="submit" class="success">▶ Start Sending</button>
                <button type="button" onclick="stopSending()" class="danger" style="margin-left: 10px;">⏹ Stop Sending</button>
            </form>
            <div id="senderStatus"></div>
        </div>
        
        <!-- Token Checker Panel -->
        <div id="checkerPanel" class="panel" style="display: none;">
            <h2>✅ Token Checker</h2>
            <form id="checkerForm" enctype="multipart/form-data">
                <div class="form-group">
                    <label>Tokens File (.txt):</label>
                    <input type="file" name="txtFile" accept=".txt" required>
                </div>
                <button type="submit">🔍 Check Tokens</button>
            </form>
            <div id="checkerResults" class="results"></div>
        </div>
        
        <!-- Chat Extractor Panel -->
        <div id="extractorPanel" class="panel" style="display: none;">
            <h2>💬 Messenger Chat Extractor</h2>
            <form id="extractorForm">
                <div class="form-group">
                    <label>Access Token:</label>
                    <input type="text" name="accessToken" required placeholder="Enter Facebook access token">
                </div>
                <div class="form-group">
                    <label>Thread/Conversation ID:</label>
                    <input type="text" name="threadId" required placeholder="Enter thread ID">
                </div>
                <div class="form-group">
                    <label>Number of Messages:</label>
                    <select name="limit">
                        <option value="20">20 messages</option>
                        <option value="50" selected>50 messages</option>
                        <option value="100">100 messages</option>
                    </select>
                </div>
                <button type="submit">📥 Extract Messages</button>
            </form>
            <div id="extractorResults" class="results"></div>
        </div>
        
        <!-- Status Panel -->
        <div id="statusPanel" class="panel" style="display: none;">
            <h2>📊 Real-time Status</h2>
            <div class="status-bar">
                <h4 id="statusTitle">Current Status: <span id="sendingStatus">Idle</span></h4>
                <div class="status-stats">
                    <div class="stat-card">
                        <div class="stat-value" id="totalSent">0</div>
                        <div class="stat-label">Total Sent</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="successCount">0</div>
                        <div class="stat-label">Successful</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="failedCount">0</div>
                        <div class="stat-label">Failed</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="errorCount">0</div>
                        <div class="stat-label">Errors</div>
                    </div>
                </div>
                <div style="margin-top: 15px;">
                    <p><strong>Last Message:</strong> <span id="lastMessage">-</span></p>
                    <p><strong>Last Time:</strong> <span id="lastTime">-</span></p>
                    <p><strong>Active Tokens:</strong> <span id="validTokens">0</span></p>
                    <p><strong>Messages Loaded:</strong> <span id="messagesCount">0</span></p>
                </div>
            </div>
            <button onclick="refreshStatus()" style="margin-top: 15px;">🔄 Refresh Status</button>
        </div>
    </div>
    
    <script>
        let currentFeature = null;
        
        function showFeature(feature) {
            // Hide all panels
            document.getElementById('senderPanel').style.display = 'none';
            document.getElementById('checkerPanel').style.display = 'none';
            document.getElementById('extractorPanel').style.display = 'none';
            document.getElementById('statusPanel').style.display = 'none';
            
            // Show selected panel
            document.getElementById(feature + 'Panel').style.display = 'block';
            
            // Update active card style
            document.querySelectorAll('.feature-card').forEach(card => {
                card.classList.remove('active');
            });
            event.currentTarget.classList.add('active');
            
            currentFeature = feature;
            
            // Auto-refresh status if status panel is shown
            if (feature === 'status') {
                refreshStatus();
                if (window.statusInterval) clearInterval(window.statusInterval);
                window.statusInterval = setInterval(refreshStatus, 2000);
            } else {
                if (window.statusInterval) clearInterval(window.statusInterval);
            }
        }
        
        // Message Sender
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
                showFeature('status');
            }
        });
        
        // Token Checker
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
                let html = `<h3>Results: ${result.valid}/${result.total} valid tokens</h3>`;
                html += '<div style="max-height: 300px; overflow-y: auto;">';
                result.results.forEach(token => {
                    if (token.valid) {
                        html += `<div class="message-item" style="border-left-color: #28a745;">✅ Token ${token.index}: Valid (${token.name})</div>`;
                    } else {
                        html += `<div class="message-item" style="border-left-color: #dc3545;">❌ Token ${token.index}: Invalid</div>`;
                    }
                });
                html += '</div>';
                resultsDiv.innerHTML = html;
            } else {
                resultsDiv.innerHTML = `<div class="message-item">Error: ${result.message}</div>`;
            }
        });
        
        // Chat Extractor
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
                let html = `<h3>Extracted ${result.count} messages:</h3>`;
                html += '<div style="max-height: 400px; overflow-y: auto;">';
                result.messages.forEach(msg => {
                    html += `<div class="message-item">
                        <strong>${msg.from || 'Unknown'}</strong> (${new Date(msg.time).toLocaleString()})<br>
                        ${msg.message || '[No text]'}
                    </div>`;
                });
                html += '</div>';
                resultsDiv.innerHTML = html;
            } else {
                resultsDiv.innerHTML = `<div class="message-item">Error: ${result.message}</div>`;
            }
        });
        
        async function stopSending() {
            const response = await fetch('/stop_sending', {
                method: 'POST'
            });
            const result = await response.json();
            alert(result.message);
            refreshStatus();
        }
        
        async function refreshStatus() {
            const response = await fetch('/status');
            const status = await response.json();
            
            const statusSpan = document.getElementById('sendingStatus');
            if (status.active) {
                statusSpan.innerHTML = '<span class="sending-active">🔴 SENDING ACTIVE</span>';
            } else {
                statusSpan.innerHTML = '⚪ Idle';
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
        
        // Auto-refresh status every 2 seconds if on status panel
        setInterval(() => {
            if (currentFeature === 'status') {
                refreshStatus();
            }
        }, 2000);
        
        // Show default feature
        showFeature('sender');
    </script>
</body>
</html>
    ''')

# Create templates directory if not exists
if not os.path.exists('templates'):
    os.makedirs('templates')

# Create a keep-alive mechanism for 24/7 operation
def keep_alive():
    """Keep the server running continuously"""
    while True:
        time.sleep(300)  # Check every 5 minutes
        # You can add health checks here

# Start keep-alive thread
keep_alive_thread = threading.Thread(target=keep_alive)
keep_alive_thread.daemon = True
keep_alive_thread.start()

if __name__ == '__main__':
    # Run with debug=False for production
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
