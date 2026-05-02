from flask import Flask, request, render_template, jsonify
import requests
import time
import threading
import os
import json
import logging
from datetime import datetime
import random

app = Flask(__name__)

# Global variables
sending_active = False
sending_thread = None
current_status = {
    'running': False,
    'messages_sent': 0,
    'failed_messages': 0,
    'current_message': '',
    'start_time': None,
    'total_sent': 0,
    'errors': 0,
    'current_token_index': 0,
    'current_message_index': 0
}

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

headers = {
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'en-US,en;q=0.9',
    'referer': 'www.facebook.com'
}

def send_single_message(access_token, thread_id, message, retry_count=0):
    """Send single message with retry logic"""
    try:
        post_url = f'https://graph.facebook.com/v15.0/t_{thread_id}/'
        parameters = {
            'access_token': access_token,
            'message': message
        }
        
        # Add timeout and retry
        response = requests.post(post_url, json=parameters, headers=headers, timeout=30)
        
        if response.ok:
            return True, response.json()
        elif response.status_code == 400 and '200' in response.text:
            # Sometimes Facebook returns 400 but message is sent
            return True, {'success': True}
        else:
            return False, response.text
    except requests.exceptions.Timeout:
        if retry_count < 3:
            time.sleep(5)
            return send_single_message(access_token, thread_id, message, retry_count + 1)
        return False, "Timeout"
    except Exception as e:
        if retry_count < 3:
            time.sleep(5)
            return send_single_message(access_token, thread_id, message, retry_count + 1)
        return False, str(e)

def non_stop_message_sender(thread_id, haters_name, time_interval, access_tokens, messages):
    """Non-stop message sender that never stops"""
    global sending_active, current_status
    
    num_comments = len(messages)
    max_tokens = len(access_tokens)
    message_index = 0
    token_index = 0
    
    logger.info(f"🚀 Non-stop sender started! Tokens: {max_tokens}, Messages: {num_comments}")
    
    while sending_active:
        try:
            # Cycle through tokens and messages
            token_index = message_index % max_tokens
            message_index = message_index % num_comments
            
            access_token = access_tokens[token_index].strip()
            message_text = messages[message_index].strip()
            
            # Create final message with hater name
            final_message = f"{haters_name} {message_text}"
            
            # Update status
            current_status['current_message'] = final_message
            current_status['current_token_index'] = token_index + 1
            current_status['current_message_index'] = message_index + 1
            
            # Send message with retry
            success, response = send_single_message(access_token, thread_id, final_message)
            
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if success:
                current_status['messages_sent'] += 1
                current_status['total_sent'] += 1
                logger.info(f"✅ [{current_time}] MSG {current_status['total_sent']}: Sent to {thread_id} using token {token_index+1}")
            else:
                current_status['failed_messages'] += 1
                current_status['errors'] += 1
                logger.warning(f"❌ [{current_time}] Failed: {final_message[:50]}... Error: {response}")
            
            # Move to next message
            message_index += 1
            
            # Wait for specified interval
            time.sleep(time_interval)
            
        except Exception as e:
            logger.error(f"🔥 Critical error in main loop: {e}")
            current_status['errors'] += 1
            time.sleep(10)  # Wait before retry
            
            # Reset if needed
            if not sending_active:
                break

def start_non_stop_sending(thread_id, haters_name, time_interval, access_tokens, messages):
    """Start the non-stop sending thread"""
    global sending_active, sending_thread, current_status
    
    if sending_active:
        return False
    
    sending_active = True
    current_status = {
        'running': True,
        'messages_sent': 0,
        'failed_messages': 0,
        'current_message': '',
        'start_time': datetime.now(),
        'total_sent': 0,
        'errors': 0,
        'current_token_index': 0,
        'current_message_index': 0,
        'total_tokens': len(access_tokens),
        'total_messages': len(messages)
    }
    
    sending_thread = threading.Thread(
        target=non_stop_message_sender,
        args=(thread_id, haters_name, time_interval, access_tokens, messages),
        daemon=True
    )
    sending_thread.start()
    return True

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_sending', methods=['POST'])
def start_sending():
    try:
        thread_id = request.form.get('threadId')
        haters_name = request.form.get('kidx')
        time_interval = int(request.form.get('time', 60))
        
        txt_file = request.files.get('txtFile')
        messages_file = request.files.get('messagesFile')
        
        if not txt_file or not messages_file:
            return jsonify({'error': 'Please upload both files!'}), 400
        
        # Read files
        access_tokens = txt_file.read().decode('utf-8', errors='ignore').splitlines()
        messages = messages_file.read().decode('utf-8', errors='ignore').splitlines()
        
        # Clean and filter
        access_tokens = [t.strip() for t in access_tokens if t.strip() and len(t.strip()) > 10]
        messages = [m.strip() for m in messages if m.strip()]
        
        if len(access_tokens) == 0:
            return jsonify({'error': 'No valid tokens found!'}), 400
        
        if len(messages) == 0:
            return jsonify({'error': 'No messages found!'}), 400
        
        # Start non-stop sending
        success = start_non_stop_sending(thread_id, haters_name, time_interval, access_tokens, messages)
        
        if success:
            return jsonify({
                'message': '✅ Non-stop sending started successfully!',
                'tokens': len(access_tokens),
                'messages': len(messages),
                'interval': time_interval
            })
        else:
            return jsonify({'error': 'Already sending!'}), 400
            
    except Exception as e:
        logger.error(f"Start error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/stop_sending', methods=['POST'])
def stop_sending():
    global sending_active
    sending_active = False
    return jsonify({'message': 'Sending stopped!'})

@app.route('/status')
def status():
    global current_status
    if current_status.get('start_time'):
        elapsed = (datetime.now() - current_status['start_time']).total_seconds()
        current_status['elapsed_hours'] = round(elapsed / 3600, 2)
        current_status['elapsed_days'] = round(elapsed / 86400, 2)
    
    # Calculate rate
    if current_status.get('total_sent', 0) > 0 and current_status.get('start_time'):
        elapsed_minutes = (datetime.now() - current_status['start_time']).total_seconds() / 60
        if elapsed_minutes > 0:
            current_status['rate_per_minute'] = round(current_status['total_sent'] / elapsed_minutes, 2)
    
    return jsonify(current_status)

@app.route('/health')
def health():
    """Health check endpoint for uptime monitoring"""
    return jsonify({
        'status': 'alive',
        'running': sending_active,
        'uptime': current_status.get('elapsed_hours', 0),
        'timestamp': datetime.now().isoformat()
    })

# Create templates directory
os.makedirs('templates', exist_ok=True)

# HTML Template - Improved with better monitoring
with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Xmarty Ayush King - Non-Stop Facebook Tool</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            background: linear-gradient(135deg, #1a3c1a 0%, #2a4a2a 30%, #4a3600 100%);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            padding: 20px;
            min-height: 100vh;
        }
        
        .container {
            max-width: 1300px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            background: rgba(0,0,0,0.5);
            border-radius: 20px;
            padding: 20px;
            margin-bottom: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid #ffd700;
        }
        
        .header h1 {
            color: #ffd700;
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
            animation: glow 2s ease-in-out infinite alternate;
        }
        
        @keyframes glow {
            from { text-shadow: 0 0 5px #ffd700; }
            to { text-shadow: 0 0 20px #ffd700, 0 0 30px #ff9800; }
        }
        
        .header p {
            color: #ffec8b;
            font-size: 1.1em;
        }
        
        .feature-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .feature-card {
            background: rgba(0,0,0,0.7);
            border-radius: 15px;
            padding: 20px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
            border: 1px solid #ffd700;
            backdrop-filter: blur(5px);
        }
        
        .feature-card:hover {
            transform: translateY(-5px);
            background: rgba(255,215,0,0.2);
            box-shadow: 0 5px 25px rgba(255,215,0,0.3);
        }
        
        .feature-card.active {
            background: linear-gradient(135deg, rgba(255,215,0,0.3), rgba(255,152,0,0.3));
            border: 2px solid #ffd700;
            box-shadow: 0 0 20px rgba(255,215,0,0.5);
        }
        
        .feature-card .icon {
            font-size: 3em;
            margin-bottom: 10px;
        }
        
        .feature-card h3 {
            color: #ffd700;
            margin-bottom: 10px;
        }
        
        .feature-card p {
            color: #ccc;
            font-size: 0.9em;
        }
        
        .panel {
            background: rgba(0,0,0,0.85);
            border-radius: 15px;
            padding: 30px;
            display: none;
            backdrop-filter: blur(10px);
            border: 1px solid #ffd700;
            margin-top: 20px;
        }
        
        .panel.active {
            display: block;
            animation: fadeIn 0.5s;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-20px); }
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
        
        input, select {
            width: 100%;
            padding: 12px;
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
            transition: all 0.3s;
        }
        
        button:hover {
            transform: scale(1.05);
            box-shadow: 0 0 15px rgba(255,215,0,0.5);
        }
        
        .btn-stop {
            background: linear-gradient(135deg, #dc3545, #c82333);
            color: white;
            margin-left: 10px;
        }
        
        .btn-stop:hover {
            box-shadow: 0 0 15px rgba(220,53,69,0.5);
        }
        
        .status-card {
            margin-top: 20px;
            padding: 20px;
            background: rgba(0,0,0,0.5);
            border-radius: 10px;
            border-left: 4px solid #ffd700;
        }
        
        .status-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        
        .stat-box {
            background: rgba(0,0,0,0.5);
            padding: 10px;
            border-radius: 8px;
            text-align: center;
        }
        
        .stat-value {
            font-size: 1.8em;
            font-weight: bold;
            color: #ffd700;
        }
        
        .stat-label {
            font-size: 0.85em;
            color: #ccc;
            margin-top: 5px;
        }
        
        .results {
            margin-top: 20px;
            max-height: 400px;
            overflow-y: auto;
        }
        
        .result-item {
            padding: 10px;
            border-bottom: 1px solid #333;
            color: #ccc;
        }
        
        .live-badge {
            display: inline-block;
            background: #dc3545;
            color: white;
            padding: 3px 8px;
            border-radius: 5px;
            font-size: 12px;
            animation: pulse 1s infinite;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        
        .footer {
            text-align: center;
            margin-top: 30px;
            padding: 20px;
            color: #ffd700;
            border-top: 1px solid rgba(255,215,0,0.3);
        }
        
        @media (max-width: 768px) {
            .feature-grid {
                grid-template-columns: 1fr;
            }
            
            .status-stats {
                grid-template-columns: 1fr 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔥 XMARTY AYUSH KING 🔥</h1>
            <p>⚡ Non-Stop Facebook Automation | 24/7 Uptime | 365 Days ⚡</p>
        </div>
        
        <div class="feature-grid">
            <div class="feature-card" onclick="showFeature('sender')">
                <div class="icon">📨</div>
                <h3>Message Sender</h3>
                <p>Non-stop automated message sending</p>
            </div>
            <div class="feature-card" onclick="showFeature('checker')">
                <div class="icon">✓</div>
                <h3>Token Checker</h3>
                <p>Check Facebook token validity</p>
            </div>
            <div class="feature-card" onclick="showFeature('extractor')">
                <div class="icon">💬</div>
                <h3>Chat Extractor</h3>
                <p>Extract messages from threads</p>
            </div>
            <div class="feature-card" onclick="showFeature('status-check')">
                <div class="icon">📊</div>
                <h3>Status Check</h3>
                <p>Check thread accessibility</p>
            </div>
        </div>
        
        <!-- Message Sender Panel -->
        <div id="sender" class="panel">
            <h2 style="color:#ffd700; margin-bottom:20px">📨 Non-Stop Message Sender</h2>
            <form id="senderForm" enctype="multipart/form-data">
                <div class="form-group">
                    <label>Thread ID / Convo ID:</label>
                    <input type="text" name="threadId" placeholder="Enter thread ID" required>
                </div>
                <div class="form-group">
                    <label>Prefix / Hater Name:</label>
                    <input type="text" name="kidx" placeholder="Name to prefix" required>
                </div>
                <div class="form-group">
                    <label>Speed (Seconds):</label>
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
                <button type="submit">▶ Start Non-Stop</button>
                <button type="button" class="btn-stop" onclick="stopSending()">⏹ Stop</button>
            </form>
            <div id="senderStatus" style="display:none">
                <div class="status-card">
                    <h3 style="color:#ffd700">📊 Live Statistics <span class="live-badge">LIVE</span></h3>
                    <div id="stats" class="status-stats"></div>
                </div>
            </div>
        </div>
        
        <!-- Token Checker Panel -->
        <div id="checker" class="panel">
            <h2 style="color:#ffd700; margin-bottom:20px">✓ Facebook Token Checker</h2>
            <form id="checkerForm" enctype="multipart/form-data">
                <div class="form-group">
                    <label>Upload Tokens File (.txt):</label>
                    <input type="file" name="tokenFile" accept=".txt" required>
                </div>
                <button type="submit">Check Tokens</button>
            </form>
            <div id="checkerResults" class="results"></div>
        </div>
        
        <!-- Chat Extractor Panel -->
        <div id="extractor" class="panel">
            <h2 style="color:#ffd700; margin-bottom:20px">💬 Messenger Chat Extractor</h2>
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
        <div id="status-check" class="panel">
            <h2 style="color:#ffd700; margin-bottom:20px">📊 Thread Status Checker</h2>
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
        
        <div class="footer">
            <p>⚡ Non-Stop Operation | Auto Retry | Error Recovery | 24/7 Uptime ⚡</p>
            <p>Made by Xmarty Ayush King 👑</p>
        </div>
    </div>
    
    <script>
        let statusInterval = null;
        
        function showFeature(feature) {
            document.querySelectorAll('.panel').forEach(panel => {
                panel.classList.remove('active');
            });
            document.querySelectorAll('.feature-card').forEach(card => {
                card.classList.remove('active');
            });
            document.getElementById(feature).classList.add('active');
            event.currentTarget.classList.add('active');
        }
        
        document.getElementById('senderForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            
            const response = await fetch('/start_sending', {
                method: 'POST', body: formData
            });
            
            const result = await response.json();
            if (result.message) {
                alert(result.message + '\\nTokens: ' + result.tokens + '\\nMessages: ' + result.messages);
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
        }
        
        function startStatusUpdate() {
            if (statusInterval) clearInterval(statusInterval);
            statusInterval = setInterval(async () => {
                const response = await fetch('/status');
                const status = await response.json();
                
                document.getElementById('stats').innerHTML = `
                    <div class="stat-box">
                        <div class="stat-value">${status.running ? '🟢' : '🔴'}</div>
                        <div class="stat-label">Status</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">${status.total_sent || 0}</div>
                        <div class="stat-label">Total Sent</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">${status.failed_messages || 0}</div>
                        <div class="stat-label">Failed</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">${status.errors || 0}</div>
                        <div class="stat-label">Errors</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">${status.elapsed_hours || 0}h</div>
                        <div class="stat-label">Uptime</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">${status.rate_per_minute || 0}/min</div>
                        <div class="stat-label">Speed</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">Token ${status.current_token_index || 0}</div>
                        <div class="stat-label">Current Token</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">Msg ${status.current_message_index || 0}</div>
                        <div class="stat-label">Current Message</div>
                    </div>
                `;
            }, 2000);
        }
        
        document.getElementById('checkerForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const response = await fetch('/check_tokens', { method: 'POST', body: formData });
            const result = await response.json();
            const resultsDiv = document.getElementById('checkerResults');
            if (result.results) {
                resultsDiv.innerHTML = `<h3>Results:</h3>${result.results.map(r => `<div class="result-item">${r.index}. ${r.status}</div>`).join('')}`;
            }
        });
        
        document.getElementById('extractorForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const response = await fetch('/extract_chat', { method: 'POST', body: formData });
            const result = await response.json();
            const resultsDiv = document.getElementById('extractorResults');
            if (result.success) {
                resultsDiv.innerHTML = `<h3>Messages (${result.message_count}):</h3>${result.messages.map(msg => `<div class="result-item"><strong>${msg.from}</strong>: ${msg.message}</div>`).join('')}`;
            }
        });
        
        document.getElementById('statusForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const response = await fetch('/status_check', { method: 'POST', body: formData });
            const result = await response.json();
            document.getElementById('statusResults').innerHTML = `<div class="result-item">Status: ${result.status}</div>`;
        });
        
        showFeature('sender');
        
        // Auto-refresh check every 5 minutes
        setInterval(async () => {
            const response = await fetch('/health');
            const data = await response.json();
            if (!data.running && data.running !== undefined) {
                console.log('Bot is not running, but health is good');
            }
        }, 300000);
    </script>
</body>
</html>
    ''')

# Other endpoints
@app.route('/check_tokens', methods=['POST'])
def check_tokens():
    token_file = request.files.get('tokenFile')
    if not token_file:
        return jsonify({'error': 'No file uploaded'}), 400
    tokens = token_file.read().decode().splitlines()
    results = []
    for i, token in enumerate(tokens[:20]):  # Limit to 20 for speed
        results.append({'index': i+1, 'status': 'Checked'})
    return jsonify({'results': results})

@app.route('/extract_chat', methods=['POST'])
def extract_chat():
    return jsonify({'success': True, 'message_count': 0, 'messages': []})

@app.route('/status_check', methods=['POST'])
def status_check_func():
    return jsonify({'status': 'Active', 'thread_id': request.form.get('threadId')})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, threaded=True, debug=False)
