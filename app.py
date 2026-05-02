from flask import Flask, request, render_template, jsonify, Response
import requests
import time
import threading
import re
import json

app = Flask(__name__)

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

# Global variable to control message sending
sending_active = False
sending_thread = None

@app.route('/')
def index():
    return '''
    <html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Facebook Tool Suite - Xmarty Ayush King</title>
    <style>
        @keyframes gradientBG {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            padding: 20px;
            min-height: 100vh;
        }
        
        .main-container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        /* Header Styles */
        .header {
            text-align: center;
            margin-bottom: 40px;
            padding: 20px;
            background: rgba(0,0,0,0.5);
            border-radius: 20px;
            backdrop-filter: blur(10px);
        }
        
        .header h1 {
            font-size: 2.5em;
            background: linear-gradient(45deg, #ff6b6b, #ffe66d, #ff6b6b);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            animation: gradientBG 3s ease infinite;
            background-size: 200% 200%;
        }
        
        /* Feature Menu */
        .feature-menu {
            display: flex;
            gap: 15px;
            margin-bottom: 30px;
            flex-wrap: wrap;
            justify-content: center;
        }
        
        .feature-btn {
            padding: 12px 24px;
            border: none;
            border-radius: 50px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
            transition: all 0.3s ease;
            background: rgba(255,255,255,0.1);
            color: white;
            backdrop-filter: blur(5px);
        }
        
        .feature-btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 5px 20px rgba(0,0,0,0.3);
        }
        
        .feature-btn.active {
            background: linear-gradient(45deg, #ff6b6b, #ffe66d);
            color: #1a1a2e;
        }
        
        /* Feature Container */
        .feature-container {
            background: rgba(0,0,0,0.7);
            border-radius: 20px;
            padding: 30px;
            backdrop-filter: blur(10px);
            margin-bottom: 30px;
            display: none;
        }
        
        .feature-container.active {
            display: block;
            animation: fadeIn 0.5s ease;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        /* Form Styles */
        .form-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            color: #ffe66d;
            font-weight: bold;
        }
        
        input, select, textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #ffe66d;
            background: rgba(0,0,0,0.5);
            color: white;
            border-radius: 10px;
            font-size: 14px;
            transition: all 0.3s ease;
        }
        
        input:focus, select:focus, textarea:focus {
            outline: none;
            border-color: #ff6b6b;
            box-shadow: 0 0 10px rgba(255,107,107,0.3);
        }
        
        button {
            background: linear-gradient(45deg, #ff6b6b, #ffe66d);
            color: #1a1a2e;
            padding: 12px 30px;
            border: none;
            border-radius: 50px;
            cursor: pointer;
            font-weight: bold;
            font-size: 16px;
            transition: all 0.3s ease;
        }
        
        button:hover {
            transform: scale(1.05);
            box-shadow: 0 5px 20px rgba(0,0,0,0.3);
        }
        
        .stop-btn {
            background: linear-gradient(45deg, #ff4444, #cc0000);
            margin-left: 10px;
        }
        
        /* Output Area */
        .output-area {
            background: rgba(0,0,0,0.5);
            border-radius: 10px;
            padding: 20px;
            margin-top: 20px;
            max-height: 400px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
        }
        
        .output-line {
            padding: 5px;
            margin: 5px 0;
            border-left: 3px solid;
            animation: slideIn 0.3s ease;
        }
        
        @keyframes slideIn {
            from { opacity: 0; transform: translateX(-20px); }
            to { opacity: 1; transform: translateX(0); }
        }
        
        .output-success {
            border-left-color: #00ff00;
            color: #00ff00;
        }
        
        .output-error {
            border-left-color: #ff0000;
            color: #ff9999;
        }
        
        .output-info {
            border-left-color: #ffe66d;
            color: #ffe66d;
        }
        
        /* Scrollbar */
        .output-area::-webkit-scrollbar {
            width: 8px;
        }
        
        .output-area::-webkit-scrollbar-track {
            background: rgba(255,255,255,0.1);
            border-radius: 10px;
        }
        
        .output-area::-webkit-scrollbar-thumb {
            background: #ffe66d;
            border-radius: 10px;
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .feature-menu {
                flex-direction: column;
            }
            
            .feature-btn {
                width: 100%;
            }
        }
        
        .footer {
            text-align: center;
            padding: 20px;
            color: #ffe66d;
            margin-top: 30px;
        }
    </style>
</head>
<body>
    <div class="main-container">
        <div class="header">
            <h1>𝐗𝐌𝐀𝐑𝐓𝐘 𝐀𝐘𝐔𝐒𝐇 𝐊𝐈𝐍𝐆 - 𝐅𝐀𝐂𝐄𝐁𝐎𝐎𝐊 𝐓𝐎𝐎𝐋 𝐒𝐔𝐈𝐓𝐄</h1>
            <p style="color: #ffe66d; margin-top: 10px;">Advanced Facebook Automation Toolkit</p>
        </div>
        
        <div class="feature-menu">
            <button class="feature-btn active" onclick="showFeature('sender')">📨 Message Sender</button>
            <button class="feature-btn" onclick="showFeature('checker')">✓ Token Checker</button>
            <button class="feature-btn" onclick="showFeature('extractor')">💬 Messenger Chat Extractor</button>
            <button class="feature-btn" onclick="showFeature('status')">📊 Status Check</button>
        </div>
        
        <!-- Message Sender Feature -->
        <div id="sender" class="feature-container active">
            <h2 style="color: #ffe66d; margin-bottom: 20px;">📨 Message Sender</h2>
            <form id="senderForm">
                <div class="form-group">
                    <label>Convo ID:</label>
                    <input type="text" id="threadId" name="threadId" required>
                </div>
                <div class="form-group">
                    <label>Tokens File (.txt):</label>
                    <input type="file" id="txtFile" accept=".txt" required>
                </div>
                <div class="form-group">
                    <label>Messages File (.txt):</label>
                    <input type="file" id="messagesFile" accept=".txt" required>
                </div>
                <div class="form-group">
                    <label>Hater Name:</label>
                    <input type="text" id="kidx" required>
                </div>
                <div class="form-group">
                    <label>Speed (seconds):</label>
                    <input type="number" id="time" value="60" required>
                </div>
                <div>
                    <button type="button" onclick="startSending()">▶ Start Sending</button>
                    <button type="button" class="stop-btn" onclick="stopSending()">⏹ Stop Sending</button>
                </div>
            </form>
            <div id="senderOutput" class="output-area"></div>
        </div>
        
        <!-- Token Checker Feature -->
        <div id="checker" class="feature-container">
            <h2 style="color: #ffe66d; margin-bottom: 20px;">✓ Token Checker</h2>
            <div class="form-group">
                <label>Enter Tokens (one per line):</label>
                <textarea id="tokensToCheck" rows="5" placeholder="EAAxxxxx...&#10;EAAyyyyy..."></textarea>
            </div>
            <div class="form-group">
                <label>Or Upload File:</label>
                <input type="file" id="tokenFile" accept=".txt">
            </div>
            <button onclick="checkTokens()">Check Tokens</button>
            <div id="checkerOutput" class="output-area"></div>
        </div>
        
        <!-- Messenger Chat Extractor -->
        <div id="extractor" class="feature-container">
            <h2 style="color: #ffe66d; margin-bottom: 20px;">💬 Messenger Chat Extractor</h2>
            <div class="form-group">
                <label>Access Token:</label>
                <input type="text" id="extractToken" required>
            </div>
            <div class="form-group">
                <label>Thread ID:</label>
                <input type="text" id="extractThread" required>
            </div>
            <div class="form-group">
                <label>Limit (messages to fetch):</label>
                <input type="number" id="messageLimit" value="50">
            </div>
            <button onclick="extractMessages()">Extract Messages</button>
            <div id="extractorOutput" class="output-area"></div>
        </div>
        
        <!-- Status Check -->
        <div id="status" class="feature-container">
            <h2 style="color: #ffe66d; margin-bottom: 20px;">📊 Status Check</h2>
            <div class="form-group">
                <label>Access Token:</label>
                <input type="text" id="statusToken" required>
            </div>
            <button onclick="checkStatus()">Check Status</button>
            <div id="statusOutput" class="output-area"></div>
        </div>
        
        <div class="footer">
            <p>Made with ❤️ by Xmarty Ayush King</p>
        </div>
    </div>
    
    <script>
        let eventSource = null;
        
        function showFeature(feature) {
            // Hide all containers
            document.querySelectorAll('.feature-container').forEach(container => {
                container.classList.remove('active');
            });
            
            // Remove active class from all buttons
            document.querySelectorAll('.feature-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            
            // Show selected feature
            document.getElementById(feature).classList.add('active');
            event.target.classList.add('active');
        }
        
        function addOutput(outputId, message, type) {
            const output = document.getElementById(outputId);
            const div = document.createElement('div');
            div.className = `output-line output-${type}`;
            div.innerHTML = `[${new Date().toLocaleTimeString()}] ${message}`;
            output.appendChild(div);
            output.scrollTop = output.scrollHeight;
        }
        
        function startSending() {
            const threadId = document.getElementById('threadId').value;
            const kidx = document.getElementById('kidx').value;
            const time = document.getElementById('time').value;
            const txtFile = document.getElementById('txtFile').files[0];
            const messagesFile = document.getElementById('messagesFile').files[0];
            
            if (!threadId || !kidx || !time || !txtFile || !messagesFile) {
                alert('Please fill all fields and select both files');
                return;
            }
            
            const formData = new FormData();
            formData.append('threadId', threadId);
            formData.append('kidx', kidx);
            formData.append('time', time);
            formData.append('txtFile', txtFile);
            formData.append('messagesFile', messagesFile);
            
            addOutput('senderOutput', 'Starting message sender...', 'info');
            
            fetch('/start_sending', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'started') {
                    addOutput('senderOutput', 'Message sender started successfully!', 'success');
                    startPolling();
                } else {
                    addOutput('senderOutput', 'Failed to start: ' + data.message, 'error');
                }
            });
        }
        
        function stopSending() {
            fetch('/stop_sending', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                addOutput('senderOutput', 'Message sender stopped!', 'info');
                if (eventSource) {
                    eventSource.close();
                }
            });
        }
        
        function startPolling() {
            if (eventSource) {
                eventSource.close();
            }
            
            eventSource = new EventSource('/stream_logs');
            eventSource.onmessage = function(event) {
                const data = JSON.parse(event.data);
                addOutput('senderOutput', data.message, data.type);
            };
        }
        
        function checkTokens() {
            const tokens = document.getElementById('tokensToCheck').value;
            const tokenFile = document.getElementById('tokenFile').files[0];
            
            let tokenList = [];
            
            if (tokenFile) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    tokenList = e.target.result.split('\\n');
                    processTokens(tokenList);
                };
                reader.readAsText(tokenFile);
            } else if (tokens) {
                tokenList = tokens.split('\\n');
                processTokens(tokenList);
            } else {
                alert('Please enter tokens or upload a file');
            }
        }
        
        function processTokens(tokenList) {
            const output = document.getElementById('checkerOutput');
            output.innerHTML = '';
            
            tokenList.forEach(token => {
                if (token.trim()) {
                    fetch('/check_token', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ token: token.trim() })
                    })
                    .then(response => response.json())
                    .then(data => {
                        addOutput('checkerOutput', data.message, data.valid ? 'success' : 'error');
                    });
                }
            });
        }
        
        function extractMessages() {
            const token = document.getElementById('extractToken').value;
            const threadId = document.getElementById('extractThread').value;
            const limit = document.getElementById('messageLimit').value;
            
            if (!token || !threadId) {
                alert('Please enter token and thread ID');
                return;
            }
            
            document.getElementById('extractorOutput').innerHTML = '';
            addOutput('extractorOutput', 'Extracting messages...', 'info');
            
            fetch('/extract_messages', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: token, threadId: threadId, limit: limit })
            })
            .then(response => response.json())
            .then(data => {
                if (data.messages) {
                    data.messages.forEach(msg => {
                        addOutput('extractorOutput', `${msg.sender}: ${msg.message}`, 'info');
                    });
                    addOutput('extractorOutput', `Total messages: ${data.messages.length}`, 'success');
                } else {
                    addOutput('extractorOutput', data.error || 'Failed to extract messages', 'error');
                }
            });
        }
        
        function checkStatus() {
            const token = document.getElementById('statusToken').value;
            
            if (!token) {
                alert('Please enter access token');
                return;
            }
            
            document.getElementById('statusOutput').innerHTML = '';
            addOutput('statusOutput', 'Checking token status...', 'info');
            
            fetch('/check_status', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: token })
            })
            .then(response => response.json())
            .then(data => {
                addOutput('statusOutput', data.message, data.valid ? 'success' : 'error');
                if (data.user_info) {
                    addOutput('statusOutput', `User: ${data.user_info.name || 'N/A'}`, 'info');
                    addOutput('statusOutput', `ID: ${data.user_info.id || 'N/A'}`, 'info');
                }
            });
        }
    </script>
</body>
</html>'''

# Message sending logic
sending_active = False
current_logs = []

def add_log(message, type='info'):
    current_logs.append({'message': message, 'type': type, 'time': time.time()})
    if len(current_logs) > 100:
        current_logs.pop(0)

def send_messages_thread(thread_id, kidx, time_interval, access_tokens, messages):
    global sending_active
    num_comments = len(messages)
    max_tokens = len(access_tokens)
    post_url = f'https://graph.facebook.com/v15.0/t_{thread_id}/'
    haters_name = kidx
    speed = time_interval
    
    message_index = 0
    
    while sending_active:
        try:
            token_index = message_index % max_tokens
            access_token = access_tokens[token_index].strip()
            message = messages[message_index % num_comments].strip()
            
            parameters = {'access_token': access_token,
                         'message': haters_name + ' ' + message}
            response = requests.post(post_url, json=parameters, headers=headers)
            
            current_time = time.strftime("%Y-%m-%d %I:%M:%S %p")
            if response.ok:
                log_msg = f"[+] SEND SUCCESSFUL - Msg {message_index + 1} - Token {token_index + 1}: {haters_name} {message}"
                add_log(log_msg, 'success')
                print(log_msg)
            else:
                log_msg = f"[x] Failed - Msg {message_index + 1}: {haters_name} {message} - Status: {response.status_code}"
                add_log(log_msg, 'error')
                print(log_msg)
            
            message_index += 1
            time.sleep(speed)
            
        except Exception as e:
            log_msg = f"[!] Error: {str(e)}"
            add_log(log_msg, 'error')
            print(log_msg)
            time.sleep(30)

@app.route('/start_sending', methods=['POST'])
def start_sending():
    global sending_active, sending_thread
    
    if sending_active:
        return jsonify({'status': 'error', 'message': 'Already sending messages'})
    
    thread_id = request.form.get('threadId')
    kidx = request.form.get('kidx')
    time_interval = int(request.form.get('time'))
    
    txt_file = request.files['txtFile']
    access_tokens = txt_file.read().decode().splitlines()
    
    messages_file = request.files['messagesFile']
    messages = messages_file.read().decode().splitlines()
    
    sending_active = True
    current_logs.clear()
    
    sending_thread = threading.Thread(
        target=send_messages_thread,
        args=(thread_id, kidx, time_interval, access_tokens, messages)
    )
    sending_thread.daemon = True
    sending_thread.start()
    
    return jsonify({'status': 'started'})

@app.route('/stop_sending', methods=['POST'])
def stop_sending():
    global sending_active
    sending_active = False
    return jsonify({'status': 'stopped'})

@app.route('/stream_logs')
def stream_logs():
    def generate():
        last_index = 0
        while sending_active:
            if len(current_logs) > last_index:
                for i in range(last_index, len(current_logs)):
                    yield f"data: {json.dumps(current_logs[i])}\\n\\n"
                last_index = len(current_logs)
            time.sleep(1)
        
        # Send remaining logs
        for i in range(last_index, len(current_logs)):
            yield f"data: {json.dumps(current_logs[i])}\\n\\n"
    
    return Response(generate(), mimetype="text/event-stream")

@app.route('/check_token', methods=['POST'])
def check_token():
    data = request.json
    token = data.get('token')
    
    try:
        # Check token by getting user info
        url = f'https://graph.facebook.com/v15.0/me?access_token={token}'
        response = requests.get(url, headers=headers)
        
        if response.ok:
            user_info = response.json()
            return jsonify({
                'valid': True,
                'message': f"✓ Valid Token - User: {user_info.get('name', 'Unknown')}"
            })
        else:
            return jsonify({
                'valid': False,
                'message': f"✗ Invalid Token - {response.json().get('error', {}).get('message', 'Unknown error')}"
            })
    except Exception as e:
        return jsonify({'valid': False, 'message': f"✗ Error: {str(e)}"})

@app.route('/extract_messages', methods=['POST'])
def extract_messages():
    data = request.json
    token = data.get('token')
    thread_id = data.get('threadId')
    limit = data.get('limit', 50)
    
    try:
        url = f'https://graph.facebook.com/v15.0/t_{thread_id}/messages'
        params = {
            'access_token': token,
            'limit': limit,
            'fields': 'message,from'
        }
        
        response = requests.get(url, params=params, headers=headers)
        
        if response.ok:
            messages_data = response.json()
            messages = []
            
            for msg in messages_data.get('data', []):
                sender = msg.get('from', {}).get('name', 'Unknown')
                message_text = msg.get('message', '[No Text]')
                messages.append({'sender': sender, 'message': message_text})
            
            return jsonify({'messages': messages})
        else:
            return jsonify({'error': response.json().get('error', {}).get('message', 'Failed to extract')})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/check_status', methods=['POST'])
def check_status():
    data = request.json
    token = data.get('token')
    
    try:
        # Check token status
        url = f'https://graph.facebook.com/v15.0/me?access_token={token}'
        response = requests.get(url, headers=headers)
        
        if response.ok:
            user_info = response.json()
            return jsonify({
                'valid': True,
                'message': '✓ Token is valid and active',
                'user_info': user_info
            })
        else:
            error_msg = response.json().get('error', {}).get('message', 'Invalid token')
            return jsonify({
                'valid': False,
                'message': f'✗ Token is invalid or expired: {error_msg}'
            })
    except Exception as e:
        return jsonify({'valid': False, 'message': f'✗ Error: {str(e)}'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
