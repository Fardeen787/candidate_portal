#!/usr/bin/env python3
"""
complete_server.py - Complete Hiring Bot Server
Combines: Chat Bot + All API Endpoints + Resume Management + Cloudflare Tunnel
"""

from flask import Flask, jsonify, request, send_file, render_template_string
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import json
from functools import wraps
import logging
import re
import subprocess
import threading
import time
import os
import signal
import sys
import shutil
from werkzeug.utils import secure_filename
import base64
from pathlib import Path
import uuid
import socket

# Import AI bot handler
from ai_bot3 import ChatBotHandler, Config

# ============================================
# CONFIGURATION - HARDCODED
# ============================================

# MySQL Database Configuration
MYSQL_CONFIG = {
    'host': Config.MYSQL_HOST,
    'user': Config.MYSQL_USER,
    'password': Config.MYSQL_PASSWORD,
    'database': Config.MYSQL_DATABASE,
}

# API Configuration
API_KEY = "sk-hiring-bot-2024-secret-key-xyz789"  # Your secret API key
API_PORT = 5000  # Port number for the server

# Cloudflare Tunnel Configuration
CLOUDFLARE_TUNNEL_NAME = "hiring-bot-complete"  # Name for your tunnel
CLOUDFLARE_TUNNEL_URL = None  # Will be set after tunnel starts

# File Storage Configuration
BASE_STORAGE_PATH = "approved_tickets"  # Base folder for storing approved tickets
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'rtf'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB max file size

# ============================================
# Flask App Initialization
# ============================================

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE
CORS(app, origins="*")  # Configure appropriately for production

# Initialize SocketIO for real-time chat
socketio = SocketIO(app, cors_allowed_origins="*")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create base storage directory if it doesn't exist
if not os.path.exists(BASE_STORAGE_PATH):
    os.makedirs(BASE_STORAGE_PATH)
    logger.info(f"Created base storage directory: {BASE_STORAGE_PATH}")

# Initialize chat bot handler
chat_bot = ChatBotHandler()
logger.info("Chat bot handler initialized successfully")

# ============================================
# Database Helper Functions
# ============================================

def get_db_connection():
    """Create and return database connection"""
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        return conn
    except Error as e:
        logger.error(f"Database connection failed: {e}")
        return None

def serialize_datetime(obj):
    """Convert datetime objects to ISO format strings"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj

# ============================================
# Authentication Decorator
# ============================================

def require_api_key(f):
    """Decorator to require API key for endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        
        # Also check URL parameter as fallback
        if not api_key:
            api_key = request.args.get('api_key')
        
        if api_key != API_KEY:
            return jsonify({
                'success': False,
                'error': 'Invalid or missing API key'
            }), 401
        
        return f(*args, **kwargs)
    return decorated_function

# ============================================
# Cloudflare Tunnel Functions
# ============================================

def check_cloudflared_installed():
    """Check if cloudflared is installed"""
    try:
        result = subprocess.run(['cloudflared', 'version'], 
                              capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def install_cloudflared():
    """Install cloudflared if not present"""
    print("\n" + "="*60)
    print("📦 Installing Cloudflare Tunnel (cloudflared)...")
    print("="*60)
    
    system = sys.platform
    
    try:
        if system == "linux" or system == "linux2":
            # Linux installation
            commands = [
                "wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb",
                "sudo dpkg -i cloudflared-linux-amd64.deb",
                "rm cloudflared-linux-amd64.deb"
            ]
            for cmd in commands:
                subprocess.run(cmd, shell=True, check=True)
                
        elif system == "darwin":
            # macOS installation
            subprocess.run("brew install cloudflare/cloudflare/cloudflared", 
                         shell=True, check=True)
                         
        elif system == "win32":
            # Windows installation
            print("Please download cloudflared from:")
            print("https://github.com/cloudflare/cloudflared/releases")
            print("Add it to your PATH and restart the script.")
            return False
            
        print("✅ Cloudflared installed successfully!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install cloudflared: {e}")
        print("\nPlease install manually:")
        print("https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation")
        return False

def start_cloudflare_tunnel():
    """Start Cloudflare tunnel and return public URL"""
    global CLOUDFLARE_TUNNEL_URL
    
    if not check_cloudflared_installed():
        if not install_cloudflared():
            return None
    
    print("\n" + "="*60)
    print("🌐 Starting Cloudflare Tunnel...")
    print("="*60)
    
    try:
        # Check if user is logged in
        login_check = subprocess.run(['cloudflared', 'tunnel', 'list'], 
                                   capture_output=True, text=True)
        
        if login_check.returncode != 0 or "You need to login" in login_check.stderr:
            print("📝 First time setup - Please login to Cloudflare")
            print("This will open your browser for authentication...")
            subprocess.run(['cloudflared', 'tunnel', 'login'])
            print("✅ Login successful!")
        
        # Try to create tunnel (will fail if exists, which is fine)
        create_result = subprocess.run(
            ['cloudflared', 'tunnel', 'create', CLOUDFLARE_TUNNEL_NAME],
            capture_output=True, text=True
        )
        
        if "already exists" in create_result.stderr:
            print(f"ℹ️  Tunnel '{CLOUDFLARE_TUNNEL_NAME}' already exists")
        elif create_result.returncode == 0:
            print(f"✅ Created tunnel '{CLOUDFLARE_TUNNEL_NAME}'")
        else:
            print(f"⚠️  Tunnel creation: {create_result.stderr}")
        
        # Start the tunnel with try.cloudflare.com for quick testing
        tunnel_process = subprocess.Popen(
            ['cloudflared', 'tunnel', '--url', f'http://localhost:{API_PORT}'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for tunnel to establish and capture URL
        print("⏳ Establishing tunnel connection...")
        
        start_time = time.time()
        while time.time() - start_time < 30:  # 30 second timeout
            line = tunnel_process.stderr.readline()
            
            # Look for the public URL in the output
            if "https://" in line and ".trycloudflare.com" in line:
                # Extract URL from the line
                url_match = re.search(r'https://[^\s]+\.trycloudflare\.com', line)
                if url_match:
                    CLOUDFLARE_TUNNEL_URL = url_match.group(0)
                    break
        
        if CLOUDFLARE_TUNNEL_URL:
            print("\n" + "="*60)
            print("🎉 CLOUDFLARE TUNNEL ACTIVE")
            print("="*60)
            print(f"📱 Public URL: {CLOUDFLARE_TUNNEL_URL}")
            print(f"🔗 Share this URL to access your complete system from anywhere")
            print(f"🔐 API Key: {API_KEY}")
            print("="*60 + "\n")
            
            # Keep tunnel process running in background
            tunnel_thread = threading.Thread(
                target=monitor_tunnel_process, 
                args=(tunnel_process,),
                daemon=True
            )
            tunnel_thread.start()
            
            return CLOUDFLARE_TUNNEL_URL
        else:
            print("❌ Failed to establish tunnel - timeout")
            tunnel_process.terminate()
            return None
            
    except Exception as e:
        print(f"❌ Error starting tunnel: {e}")
        return None

def monitor_tunnel_process(process):
    """Monitor tunnel process and restart if needed"""
    while True:
        output = process.stderr.readline()
        if output:
            # Log tunnel output for debugging (optional)
            if "error" in output.lower():
                logger.error(f"Tunnel error: {output.strip()}")
        
        # Check if process is still running
        if process.poll() is not None:
            logger.error("Tunnel process died! Restarting...")
            # Could implement restart logic here
            break
        
        time.sleep(1)

def stop_cloudflare_tunnel():
    """Stop all cloudflared processes"""
    try:
        if sys.platform == "win32":
            subprocess.run("taskkill /F /IM cloudflared.exe", shell=True)
        else:
            subprocess.run("pkill cloudflared", shell=True)
        print("✅ Cloudflare tunnel stopped")
    except:
        pass

# ============================================
# File Storage Helper Functions
# ============================================

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_ticket_folder(ticket_id, ticket_subject=None):
    """Create a folder for approved ticket"""
    try:
        # Clean ticket subject for folder name
        if ticket_subject:
            # Remove special characters and limit length
            clean_subject = re.sub(r'[^\w\s-]', '', ticket_subject)
            clean_subject = re.sub(r'[-\s]+', '-', clean_subject)
            clean_subject = clean_subject[:50].strip('-')
            folder_name = f"{ticket_id}_{clean_subject}"
        else:
            folder_name = str(ticket_id)
        
        folder_path = os.path.join(BASE_STORAGE_PATH, folder_name)
        
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            logger.info(f"Created folder for ticket {ticket_id}: {folder_path}")
            
            # Create a metadata file
            metadata = {
                'ticket_id': ticket_id,
                'created_at': datetime.now().isoformat(),
                'folder_name': folder_name,
                'resumes': []
            }
            
            metadata_path = os.path.join(folder_path, 'metadata.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Also save job details
            save_job_details_to_folder(ticket_id, folder_path)
        
        return folder_path
        
    except Exception as e:
        logger.error(f"Error creating folder for ticket {ticket_id}: {e}")
        return None

def save_job_details_to_folder(ticket_id, folder_path):
    """Save job details to a JSON file in the ticket folder"""
    try:
        conn = get_db_connection()
        if not conn:
            logger.error("Failed to connect to database for job details")
            return False
        
        cursor = conn.cursor(dictionary=True)
        
        # Get ticket information
        cursor.execute("""
            SELECT * FROM tickets 
            WHERE ticket_id = %s
        """, (ticket_id,))
        
        ticket = cursor.fetchone()
        if not ticket:
            cursor.close()
            conn.close()
            return False
        
        # Get the LATEST value for each field
        cursor.execute("""
            SELECT 
                td1.field_name,
                td1.field_value
            FROM ticket_details td1
            INNER JOIN (
                SELECT field_name, MAX(created_at) as max_created_at
                FROM ticket_details
                WHERE ticket_id = %s
                GROUP BY field_name
            ) td2 ON td1.field_name = td2.field_name 
                 AND td1.created_at = td2.max_created_at
            WHERE td1.ticket_id = %s
        """, (ticket_id, ticket_id))
        
        job_details = {}
        for row in cursor.fetchall():
            job_details[row['field_name']] = row['field_value']
        
        # Convert datetime objects to string
        for key, value in ticket.items():
            if isinstance(value, datetime):
                ticket[key] = value.isoformat()
        
        # Combine ticket info with job details
        complete_job_info = {
            'ticket_info': ticket,
            'job_details': job_details,
            'saved_at': datetime.now().isoformat()
        }
        
        # Save to job_details.json
        job_details_path = os.path.join(folder_path, 'job_details.json')
        with open(job_details_path, 'w', encoding='utf-8') as f:
            json.dump(complete_job_info, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved job details for ticket {ticket_id}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error saving job details for ticket {ticket_id}: {e}")
        return False

def update_job_details_in_folder(ticket_id):
    """Update job details file when ticket information changes"""
    try:
        # Find the ticket folder
        ticket_folders = [f for f in os.listdir(BASE_STORAGE_PATH) 
                         if f.startswith(f"{ticket_id}_")]
        
        if not ticket_folders:
            logger.error(f"No folder found for ticket {ticket_id}")
            return False
        
        folder_path = os.path.join(BASE_STORAGE_PATH, ticket_folders[0])
        return save_job_details_to_folder(ticket_id, folder_path)
        
    except Exception as e:
        logger.error(f"Error updating job details for ticket {ticket_id}: {e}")
        return False

def save_resume_to_ticket(ticket_id, file, applicant_name=None, applicant_email=None):
    """Save resume to ticket folder"""
    try:
        # Get ticket folder path
        ticket_folders = [f for f in os.listdir(BASE_STORAGE_PATH) 
                         if f.startswith(f"{ticket_id}_")]
        
        if not ticket_folders:
            logger.error(f"No folder found for ticket {ticket_id}")
            return None
        
        folder_path = os.path.join(BASE_STORAGE_PATH, ticket_folders[0])
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        original_filename = secure_filename(file.filename)
        base_name, ext = os.path.splitext(original_filename)
        
        if applicant_name:
            clean_name = re.sub(r'[^\w\s-]', '', applicant_name)
            clean_name = re.sub(r'[-\s]+', '_', clean_name)
            filename = f"{clean_name}_{timestamp}{ext}"
        else:
            filename = f"resume_{timestamp}{ext}"
        
        file_path = os.path.join(folder_path, filename)
        
        # Save file
        file.save(file_path)
        
        # Update metadata
        metadata_path = os.path.join(folder_path, 'metadata.json')
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            resume_info = {
                'filename': filename,
                'original_filename': original_filename,
                'uploaded_at': datetime.now().isoformat(),
                'applicant_name': applicant_name,
                'applicant_email': applicant_email,
                'file_size': os.path.getsize(file_path)
            }
            
            metadata['resumes'].append(resume_info)
            
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
        
        logger.info(f"Saved resume {filename} for ticket {ticket_id}")
        return file_path
        
    except Exception as e:
        logger.error(f"Error saving resume for ticket {ticket_id}: {e}")
        return None

def get_ticket_resumes(ticket_id):
    """Get list of resumes for a ticket"""
    try:
        ticket_folders = [f for f in os.listdir(BASE_STORAGE_PATH) 
                         if f.startswith(f"{ticket_id}_")]
        
        if not ticket_folders:
            return []
        
        folder_path = os.path.join(BASE_STORAGE_PATH, ticket_folders[0])
        metadata_path = os.path.join(folder_path, 'metadata.json')
        
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
                return metadata.get('resumes', [])
        
        return []
        
    except Exception as e:
        logger.error(f"Error getting resumes for ticket {ticket_id}: {e}")
        return []

def create_folders_for_existing_approved_tickets():
    """Create folders for all existing approved tickets"""
    try:
        conn = get_db_connection()
        if not conn:
            logger.error("Failed to connect to database")
            return
        
        cursor = conn.cursor(dictionary=True)
        
        # Get all approved tickets
        cursor.execute("""
            SELECT ticket_id, subject
            FROM tickets
            WHERE approval_status = 'approved'
        """)
        
        approved_tickets = cursor.fetchall()
        created_count = 0
        existing_count = 0
        
        print(f"\n📁 Checking {len(approved_tickets)} approved tickets for folders...")
        
        for ticket in approved_tickets:
            ticket_id = ticket['ticket_id']
            
            # Check if folder already exists
            ticket_folders = [f for f in os.listdir(BASE_STORAGE_PATH) 
                            if f.startswith(f"{ticket_id}_")]
            
            if ticket_folders:
                existing_count += 1
                print(f"   ✓ Folder already exists for ticket {ticket_id}")
                # Update job details in existing folder
                folder_path = os.path.join(BASE_STORAGE_PATH, ticket_folders[0])
                save_job_details_to_folder(ticket_id, folder_path)
                print(f"   📄 Updated job details for ticket {ticket_id}")
            else:
                # Create folder (which will also save job details)
                folder_path = create_ticket_folder(ticket_id, ticket['subject'])
                if folder_path:
                    created_count += 1
                    print(f"   ✅ Created folder for ticket {ticket_id}: {os.path.basename(folder_path)}")
                    print(f"   📄 Saved job details for ticket {ticket_id}")
                else:
                    print(f"   ❌ Failed to create folder for ticket {ticket_id}")
        
        cursor.close()
        conn.close()
        
        print(f"\n📊 Summary:")
        print(f"   - New folders created: {created_count}")
        print(f"   - Existing folders: {existing_count}")
        print(f"   - Total approved tickets: {len(approved_tickets)}")
        
    except Exception as e:
        logger.error(f"Error creating folders for existing tickets: {e}")
        print(f"❌ Error: {e}")

# ============================================
# CHAT INTERFACE AND ENDPOINTS
# ============================================

@app.route('/')
def index():
    """Serve the main interface with both chat and API info"""
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Hiring Bot - Complete System</title>
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 1200px; 
                margin: 0 auto; 
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin-top: 20px;
            }
            .section {
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .chat-section {
                grid-column: span 2;
            }
            h1, h2 { color: #333; }
            #chat-container { 
                border: 1px solid #ddd; 
                height: 400px; 
                overflow-y: auto; 
                padding: 15px; 
                margin-bottom: 10px;
                background: #fafafa;
                border-radius: 4px;
            }
            .message { 
                margin: 10px 0; 
                padding: 10px;
                border-radius: 8px;
                max-width: 70%;
            }
            .user { 
                background: #007bff;
                color: white;
                margin-left: auto;
                text-align: right;
            }
            .bot { 
                background: #e9ecef;
                color: #333;
            }
            #input-container { 
                display: flex; 
                gap: 10px;
            }
            #message-input { 
                flex: 1; 
                padding: 12px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
            }
            #send-button { 
                padding: 12px 24px;
                background: #007bff;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
            }
            #send-button:hover {
                background: #0056b3;
            }
            .api-info {
                background: #f8f9fa;
                padding: 15px;
                border-radius: 4px;
                margin-top: 10px;
            }
            .api-info code {
                background: #e9ecef;
                padding: 2px 6px;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
            }
            .status-indicator {
                display: inline-block;
                width: 10px;
                height: 10px;
                border-radius: 50%;
                margin-right: 5px;
            }
            .status-active { background: #28a745; }
            .status-inactive { background: #dc3545; }
            .endpoint-list {
                max-height: 300px;
                overflow-y: auto;
                font-size: 13px;
            }
        </style>
    </head>
    <body>
        <h1>🤖 Hiring Bot - Complete System</h1>
        
        <div class="container">
            <div class="section">
                <h2>📊 System Status</h2>
                <p><span class="status-indicator status-active"></span> Server: Active</p>
                <p><span class="status-indicator {% if tunnel_url %}status-active{% else %}status-inactive{% endif %}"></span> 
                   Cloudflare Tunnel: {% if tunnel_url %}Active{% else %}Local Only{% endif %}</p>
                <p>🔐 API Key: <code>{{ api_key[:20] }}...</code></p>
                {% if tunnel_url %}
                <p>🌐 Public URL: <code>{{ tunnel_url }}</code></p>
                {% endif %}
            </div>
            
            <div class="section">
                <h2>🔗 Quick Links</h2>
                <p>📚 <a href="/api/health">Health Check</a></p>
                <p>💼 <a href="/api/jobs/approved?api_key={{ api_key }}">View Approved Jobs</a></p>
                <p>📊 <a href="/api/stats?api_key={{ api_key }}">Statistics</a></p>
                <p>📍 <a href="/api/locations?api_key={{ api_key }}">Locations</a></p>
                <p>🛠️ <a href="/api/skills?api_key={{ api_key }}">Skills</a></p>
            </div>
        </div>
        
        <div class="section chat-section">
            <h2>💬 Chat with Hiring Bot</h2>
            <div id="chat-container"></div>
            <div id="input-container">
                <input type="text" id="message-input" placeholder="Type your message... (try 'I want to post a job' or 'help')" />
                <button id="send-button">Send</button>
            </div>
        </div>
        
        <div class="section api-info">
            <h3>API Endpoints</h3>
            <div class="endpoint-list">
                <p><strong>Chat Endpoints:</strong></p>
                <ul>
                    <li>POST /api/chat/start - Start new chat session</li>
                    <li>POST /api/chat/message - Send message</li>
                    <li>GET /api/chat/history/&lt;id&gt; - Get chat history</li>
                </ul>
                <p><strong>Job Management:</strong></p>
                <ul>
                    <li>GET /api/jobs/approved - Get approved jobs</li>
                    <li>GET /api/jobs/&lt;id&gt; - Get job details</li>
                    <li>GET /api/jobs/search?q=python - Search jobs</li>
                    <li>POST /api/tickets/&lt;id&gt;/approve - Approve ticket</li>
                </ul>
                <p><strong>Resume Management:</strong></p>
                <ul>
                    <li>POST /api/tickets/&lt;id&gt;/resumes - Upload resume</li>
                    <li>GET /api/tickets/&lt;id&gt;/resumes - List resumes</li>
                    <li>GET /api/tickets/&lt;id&gt;/resumes/&lt;filename&gt; - Download resume</li>
                </ul>
                <p><strong>Resume Filtering:</strong></p>
                <ul>
                    <li>POST /api/tickets/&lt;id&gt;/filter-resumes - Trigger filtering</li>
                    <li>GET /api/tickets/&lt;id&gt;/top-resumes - Get top candidates</li>
                    <li>GET /api/tickets/&lt;id&gt;/filtering-report - Get report</li>
                    <li>GET /api/tickets/&lt;id&gt;/filtering-status - Check status</li>
                    <li>POST /api/tickets/&lt;id&gt;/send-top-resumes - Send via webhook</li>
                </ul>
            </div>
        </div>
        
        <script>
            let sessionId = null;
            let userId = 'user_' + Math.random().toString(36).substr(2, 9);
            
            // Start chat session
            async function startChat() {
                const response = await fetch('/api/chat/start', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({user_id: userId})
                });
                const data = await response.json();
                sessionId = data.session_id;
                addMessage('bot', data.message);
            }
            
            // Send message
            async function sendMessage() {
                const input = document.getElementById('message-input');
                const message = input.value.trim();
                if (!message || !sessionId) return;
                
                addMessage('user', message);
                input.value = '';
                
                const response = await fetch('/api/chat/message', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        session_id: sessionId,
                        user_id: userId,
                        message: message
                    })
                });
                const data = await response.json();
                addMessage('bot', data.response || data.message);
            }
            
            // Add message to chat
            function addMessage(sender, message) {
                const chatContainer = document.getElementById('chat-container');
                const messageDiv = document.createElement('div');
                messageDiv.className = 'message ' + sender;
                
                // Convert markdown-style bold to HTML
                const formattedMessage = message
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/\n/g, '<br>');
                
                messageDiv.innerHTML = formattedMessage;
                chatContainer.appendChild(messageDiv);
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
            
            // Event listeners
            document.getElementById('send-button').onclick = sendMessage;
            document.getElementById('message-input').onkeypress = (e) => {
                if (e.key === 'Enter') sendMessage();
            };
            
            // Start chat on load
            startChat();
        </script>
    </body>
    </html>
    ''', tunnel_url=CLOUDFLARE_TUNNEL_URL, api_key=API_KEY)

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    conn = get_db_connection()
    db_status = "connected" if conn else "disconnected"
    
    if conn:
        conn.close()
    
    # Check storage directory
    storage_status = "accessible" if os.path.exists(BASE_STORAGE_PATH) else "not_found"
    
    return jsonify({
        'status': 'ok' if db_status == "connected" else 'error',
        'database': db_status,
        'tunnel': 'active' if CLOUDFLARE_TUNNEL_URL else 'inactive',
        'public_url': CLOUDFLARE_TUNNEL_URL,
        'storage': storage_status,
        'chat_enabled': True,
        'api_enabled': True,
        'timestamp': datetime.now().isoformat()
    })

# ============================================
# CHAT API ENDPOINTS
# ============================================

@app.route('/api/chat/start', methods=['POST'])
def start_chat():
    """Start a new chat session"""
    try:
        data = request.json or {}
        user_id = data.get('user_id')
        
        result = chat_bot.start_session(user_id)
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error starting chat: {e}")
        return jsonify({
            'error': 'Failed to start chat session',
            'message': str(e)
        }), 500

@app.route('/api/chat/message', methods=['POST'])
def send_message():
    """Send a message to the chat bot"""
    try:
        data = request.json
        
        session_id = data.get('session_id')
        user_id = data.get('user_id')
        message = data.get('message')
        
        if not all([session_id, user_id, message]):
            return jsonify({
                'error': 'Missing required fields',
                'required': ['session_id', 'user_id', 'message']
            }), 400
        
        bot_response = chat_bot.process_message(session_id, user_id, message)
        
        # Fix the response format for React frontend compatibility
        formatted_response = {
            'success': True,
            'response': bot_response.get('message', ''),  # Map 'message' to 'response'
            'message': bot_response.get('message', ''),   # Also keep as 'message'
            'metadata': bot_response.get('metadata', {}),
            'session_id': session_id,
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(formatted_response)
    
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        return jsonify({
            'error': 'Failed to process message',
            'message': str(e)
        }), 500

@app.route('/api/chat/history/<session_id>', methods=['GET'])
def get_chat_history(session_id):
    """Get chat history for a session"""
    try:
        limit = request.args.get('limit', 50, type=int)
        messages = chat_bot.session_manager.get_messages(session_id, limit)
        
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                'id': msg.get('message_id'),
                'sender': msg['sender_type'],
                'message': msg['message_content'],
                'metadata': msg.get('message_metadata'),
                'timestamp': msg['timestamp'].isoformat() if msg.get('timestamp') else None
            })
        
        return jsonify({
            'session_id': session_id,
            'messages': formatted_messages,
            'count': len(formatted_messages)
        })
    
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        return jsonify({
            'error': 'Failed to fetch chat history',
            'message': str(e)
        }), 500

# ============================================
# RESUME MANAGEMENT ENDPOINTS
# ============================================

@app.route('/api/tickets/<ticket_id>/approve', methods=['POST'])
@require_api_key
def approve_ticket_and_create_folder(ticket_id):
    """Approve a ticket and create its folder"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Get ticket details
        cursor.execute("""
            SELECT ticket_id, subject, approval_status
            FROM tickets
            WHERE ticket_id = %s
        """, (ticket_id,))
        
        ticket = cursor.fetchone()
        
        if not ticket:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Ticket not found'
            }), 404
        
        # Update approval status if not already approved
        if ticket['approval_status'] != 'approved':
            cursor.execute("""
                UPDATE tickets 
                SET approval_status = 'approved', 
                    approved_at = NOW()
                WHERE ticket_id = %s
            """, (ticket_id,))
            conn.commit()
        
        cursor.close()
        conn.close()
        
        # Create folder for the ticket (which will also save job details)
        folder_path = create_ticket_folder(ticket_id, ticket['subject'])
        
        if folder_path:
            return jsonify({
                'success': True,
                'message': f'Ticket {ticket_id} approved, folder created, and job details saved',
                'folder_path': folder_path
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to create folder'
            }), 500
            
    except Exception as e:
        logger.error(f"Error approving ticket: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/tickets/<ticket_id>/update-job-details', methods=['POST'])
@require_api_key
def update_job_details_endpoint(ticket_id):
    """Update job details file when ticket information changes"""
    try:
        success = update_job_details_in_folder(ticket_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Job details updated for ticket {ticket_id}'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to update job details'
            }), 500
            
    except Exception as e:
        logger.error(f"Error updating job details: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/tickets/<ticket_id>/resumes', methods=['POST'])
@require_api_key
def upload_resume(ticket_id):
    """Upload a resume for a specific ticket"""
    try:
        # Check if the ticket exists and is approved
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT ticket_id, subject, approval_status
            FROM tickets
            WHERE ticket_id = %s
        """, (ticket_id,))
        
        ticket = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not ticket:
            return jsonify({
                'success': False,
                'error': 'Ticket not found'
            }), 404
        
        if ticket['approval_status'] != 'approved':
            return jsonify({
                'success': False,
                'error': 'Ticket must be approved before uploading resumes'
            }), 400
        
        # Check if file is in request
        if 'resume' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file uploaded'
            }), 400
        
        file = request.files['resume']
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': f'Invalid file type. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
        
        # Get applicant details from form data
        applicant_name = request.form.get('applicant_name')
        applicant_email = request.form.get('applicant_email')
        
        # Ensure folder exists
        folder_path = create_ticket_folder(ticket_id, ticket['subject'])
        if not folder_path:
            return jsonify({
                'success': False,
                'error': 'Failed to create ticket folder'
            }), 500
        
        # Save the resume
        saved_path = save_resume_to_ticket(
            ticket_id, 
            file, 
            applicant_name, 
            applicant_email
        )
        
        if saved_path:
            return jsonify({
                'success': True,
                'message': 'Resume uploaded successfully',
                'file_path': saved_path
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to save resume'
            }), 500
            
    except Exception as e:
        logger.error(f"Error uploading resume: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/tickets/<ticket_id>/resumes', methods=['GET'])
@require_api_key
def get_resumes(ticket_id):
    """Get list of all resumes for a ticket"""
    try:
        resumes = get_ticket_resumes(ticket_id)
        
        return jsonify({
            'success': True,
            'data': {
                'ticket_id': ticket_id,
                'resume_count': len(resumes),
                'resumes': resumes
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting resumes: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/tickets/<ticket_id>/resumes/<filename>', methods=['GET'])
@require_api_key
def download_resume(ticket_id, filename):
    """Download a specific resume"""
    try:
        # Find the ticket folder
        ticket_folders = [f for f in os.listdir(BASE_STORAGE_PATH) 
                         if f.startswith(f"{ticket_id}_")]
        
        if not ticket_folders:
            return jsonify({
                'success': False,
                'error': 'Ticket folder not found'
            }), 404
        
        folder_path = os.path.join(BASE_STORAGE_PATH, ticket_folders[0])
        file_path = os.path.join(folder_path, secure_filename(filename))
        
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': 'Resume not found'
            }), 404
        
        return send_file(file_path, as_attachment=True)
        
    except Exception as e:
        logger.error(f"Error downloading resume: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/maintenance/create-folders', methods=['POST'])
@require_api_key
def create_existing_folders_endpoint():
    """Endpoint to create folders for all existing approved tickets"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Get all approved tickets
        cursor.execute("""
            SELECT ticket_id, subject
            FROM tickets
            WHERE approval_status = 'approved'
        """)
        
        approved_tickets = cursor.fetchall()
        results = {
            'created': [],
            'existing': [],
            'failed': []
        }
        
        for ticket in approved_tickets:
            ticket_id = ticket['ticket_id']
            
            # Check if folder already exists
            ticket_folders = [f for f in os.listdir(BASE_STORAGE_PATH) 
                            if f.startswith(f"{ticket_id}_")]
            
            if ticket_folders:
                results['existing'].append({
                    'ticket_id': ticket_id,
                    'folder': ticket_folders[0]
                })
            else:
                # Create folder
                folder_path = create_ticket_folder(ticket_id, ticket['subject'])
                if folder_path:
                    results['created'].append({
                        'ticket_id': ticket_id,
                        'folder': os.path.basename(folder_path)
                    })
                else:
                    results['failed'].append({
                        'ticket_id': ticket_id,
                        'reason': 'Failed to create folder'
                    })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'total_approved': len(approved_tickets),
                'folders_created': len(results['created']),
                'folders_existing': len(results['existing']),
                'folders_failed': len(results['failed']),
                'details': results
            }
        })
        
    except Exception as e:
        logger.error(f"Error in create_existing_folders_endpoint: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================
# RESUME FILTERING ENDPOINTS
# ============================================

@app.route('/api/tickets/<ticket_id>/filter-resumes', methods=['POST'])
@require_api_key
def trigger_resume_filtering(ticket_id):
    """Trigger resume filtering for a specific ticket"""
    try:
        # Check if ticket exists and has resumes
        ticket_folders = [f for f in os.listdir(BASE_STORAGE_PATH) 
                         if f.startswith(f"{ticket_id}_")]
        
        if not ticket_folders:
            return jsonify({
                'success': False,
                'error': 'Ticket folder not found'
            }), 404
        
        folder_path = os.path.join(BASE_STORAGE_PATH, ticket_folders[0])
        
        # Check if filtering results already exist
        filtering_results_path = os.path.join(folder_path, 'filtering_results')
        
        # Get the latest filtering results if they exist
        if os.path.exists(filtering_results_path):
            result_files = list(Path(filtering_results_path).glob('final_results_*.json'))
            if result_files:
                # Sort by modification time and get the latest
                latest_result = max(result_files, key=lambda x: x.stat().st_mtime)
                
                with open(latest_result, 'r') as f:
                    filtering_data = json.load(f)
                
                return jsonify({
                    'success': True,
                    'message': 'Filtering results already exist',
                    'data': {
                        'filtered_at': filtering_data.get('timestamp'),
                        'total_resumes': filtering_data.get('summary', {}).get('total_resumes', 0),
                        'top_candidates_count': len(filtering_data.get('final_top_5', []))
                    }
                })
        
        # If no results exist, you would trigger the filtering here
        # For now, return a message indicating manual filtering is needed
        return jsonify({
            'success': True,
            'message': 'Please run the filtering script manually for this ticket',
            'command': f'python resume_filter.py {folder_path}'
        })
        
    except Exception as e:
        logger.error(f"Error triggering resume filtering: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/tickets/<ticket_id>/top-resumes', methods=['GET'])
@require_api_key
def get_top_resumes(ticket_id):
    """Get top-ranked resumes with their details and scores"""
    try:
        # Get parameters
        include_content = request.args.get('include_content', 'false').lower() == 'true'
        top_n = min(int(request.args.get('top', 5)), 10)  # Max 10 resumes
        
        # Find the ticket folder
        ticket_folders = [f for f in os.listdir(BASE_STORAGE_PATH) 
                         if f.startswith(f"{ticket_id}_")]
        
        if not ticket_folders:
            return jsonify({
                'success': False,
                'error': 'Ticket folder not found'
            }), 404
        
        folder_path = os.path.join(BASE_STORAGE_PATH, ticket_folders[0])
        filtering_results_path = os.path.join(folder_path, 'filtering_results')
        
        if not os.path.exists(filtering_results_path):
            return jsonify({
                'success': False,
                'error': 'No filtering results found. Please run resume filtering first.'
            }), 404
        
        # Get the latest filtering results
        result_files = list(Path(filtering_results_path).glob('final_results_*.json'))
        if not result_files:
            return jsonify({
                'success': False,
                'error': 'No filtering results found'
            }), 404
        
        latest_result = max(result_files, key=lambda x: x.stat().st_mtime)
        
        with open(latest_result, 'r') as f:
            filtering_data = json.load(f)
        
        # Get top candidates
        top_candidates = filtering_data.get('final_top_5', [])[:top_n]
        
        # Get job requirements used
        job_requirements = filtering_data.get('latest_requirements', {})
        
        # Check if any candidates meet minimum requirements
        warnings = []
        min_experience = 5  # From "5-8 years"
        
        if top_candidates:
            # Check experience requirement
            if all(c.get('detected_experience_years', 0) < min_experience for c in top_candidates):
                warnings.append(f"No candidates meet the minimum experience requirement of {min_experience} years")
            
            # Check location requirement
            if all(c.get('location_score', 0) == 0 for c in top_candidates):
                warnings.append(f"No candidates match the required location: {job_requirements.get('location', 'Unknown')}")
            
            # Check if scores are too low
            if all(c.get('final_score', 0) < 0.6 for c in top_candidates):
                warnings.append("All candidates scored below 60% match")
        
        # Prepare response with resume details
        candidates_with_details = []
        
        for i, candidate in enumerate(top_candidates):
            candidate_data = {
                'rank': i + 1,
                'filename': candidate['filename'],
                'scores': {
                    'overall': f"{candidate['final_score']:.1%}",
                    'skills': f"{candidate['skill_score']:.1%}",
                    'experience': f"{candidate['experience_score']:.1%}",
                    'location': f"{candidate['location_score']:.1%}",
                    'professional_development': f"{candidate.get('professional_development_score', 0):.1%}"
                },
                'matched_skills': candidate.get('matched_skills', []),
                'missing_skills': [s for s in job_requirements.get('tech_stack', []) 
                                 if s not in candidate.get('matched_skills', [])],
                'experience_years': candidate.get('detected_experience_years', 0),
                'skill_match_ratio': f"{len(candidate.get('matched_skills', []))}/{len(job_requirements.get('tech_stack', []))}",
                'file_path': candidate.get('file_path'),
                
                # Add professional development details
                'professional_development': {
                    'score': f"{candidate.get('professional_development_score', 0):.1%}",
                    'level': candidate.get('professional_development', {}).get('professional_development_level', 'Unknown'),
                    'summary': candidate.get('professional_development', {}).get('summary', {}),
                    'key_highlights': candidate.get('professional_development', {}).get('summary', {}).get('key_highlights', []),
                    'details': {
                        'certifications': {
                            'count': candidate.get('professional_development', {}).get('summary', {}).get('total_certifications', 0),
                            'list': candidate.get('professional_development', {}).get('component_scores', {}).get('certifications', {}).get('certifications_found', []),
                            'categories': candidate.get('professional_development', {}).get('summary', {}).get('certification_categories', [])
                        },
                        'learning_platforms': {
                            'count': candidate.get('professional_development', {}).get('summary', {}).get('learning_platforms_used', 0),
                            'platforms': candidate.get('professional_development', {}).get('component_scores', {}).get('online_learning', {}).get('platforms_found', []),
                            'estimated_courses': candidate.get('professional_development', {}).get('summary', {}).get('estimated_courses_completed', 0)
                        },
                        'conferences': {
                            'attended': candidate.get('professional_development', {}).get('summary', {}).get('conferences_attended', 0),
                            'speaker': candidate.get('professional_development', {}).get('summary', {}).get('conference_speaker', False),
                            'events': candidate.get('professional_development', {}).get('component_scores', {}).get('conferences', {}).get('events_found', [])
                        },
                        'content_creation': {
                            'is_creator': candidate.get('professional_development', {}).get('summary', {}).get('content_creator', False),
                            'types': candidate.get('professional_development', {}).get('summary', {}).get('content_types', []),
                            'platforms': candidate.get('professional_development', {}).get('component_scores', {}).get('content_creation', {}).get('content_platforms', [])
                        }
                    }
                }
            }
            
            # Get metadata from metadata.json
            metadata_path = os.path.join(folder_path, 'metadata.json')
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                
                # Find matching resume metadata
                for resume_info in metadata.get('resumes', []):
                    if resume_info['filename'] == candidate['filename']:
                        candidate_data['applicant_name'] = resume_info.get('applicant_name', 'Unknown')
                        candidate_data['applicant_email'] = resume_info.get('applicant_email', 'Not provided')
                        candidate_data['uploaded_at'] = resume_info.get('uploaded_at')
                        break
            
            # Add download URL if tunnel is active
            if CLOUDFLARE_TUNNEL_URL:
                candidate_data['download_url'] = f"{CLOUDFLARE_TUNNEL_URL}/api/tickets/{ticket_id}/resumes/{candidate['filename']}?api_key={API_KEY}"
            
            # Include resume content if requested
            if include_content:
                resume_path = os.path.join(folder_path, candidate['filename'])
                if os.path.exists(resume_path):
                    try:
                        with open(resume_path, 'rb') as f:
                            resume_content = f.read()
                            candidate_data['resume_base64'] = base64.b64encode(resume_content).decode('utf-8')
                            candidate_data['resume_size'] = len(resume_content)
                    except Exception as e:
                        logger.error(f"Error reading resume {candidate['filename']}: {e}")
            
            candidates_with_details.append(candidate_data)
        
        # Get AI analysis if available
        ai_analysis = {
            'stage1_review': filtering_data.get('stage1_results', {}).get('agent_review', ''),
            'stage2_analysis': filtering_data.get('stage2_results', {}).get('detailed_analysis', ''),
            'qa_assessment': filtering_data.get('qa_review', {}).get('qa_assessment', '')
        }
        
        # Get scoring weights used
        scoring_weights = {}
        if top_candidates:
            scoring_weights = top_candidates[0].get('scoring_weights', {})
        
        return jsonify({
            'success': True,
            'warnings': warnings,  # Add warnings about candidate quality
            'data': {
                'ticket_id': ticket_id,
                'filtered_at': filtering_data.get('timestamp'),
                'job_position': filtering_data.get('position'),
                'job_requirements': job_requirements,
                'scoring_weights': {
                    'skills': f"{scoring_weights.get('skills', 0.4):.0%}",
                    'experience': f"{scoring_weights.get('experience', 0.3):.0%}",
                    'location': f"{scoring_weights.get('location', 0.1):.0%}",
                    'professional_development': f"{scoring_weights.get('professional_dev', 0.2):.0%}"
                },
                'summary': {
                    'total_resumes_processed': filtering_data.get('summary', {}).get('total_resumes', 0),
                    'top_candidates_returned': len(candidates_with_details)
                },
                'top_candidates': candidates_with_details,
                'ai_analysis': ai_analysis
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting top resumes: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/tickets/<ticket_id>/filtering-report', methods=['GET'])
@require_api_key
def get_filtering_report(ticket_id):
    """Get the complete filtering report for a ticket"""
    try:
        # Find the ticket folder
        ticket_folders = [f for f in os.listdir(BASE_STORAGE_PATH) 
                         if f.startswith(f"{ticket_id}_")]
        
        if not ticket_folders:
            return jsonify({
                'success': False,
                'error': 'Ticket folder not found'
            }), 404
        
        folder_path = os.path.join(BASE_STORAGE_PATH, ticket_folders[0])
        filtering_results_path = os.path.join(folder_path, 'filtering_results')
        
        if not os.path.exists(filtering_results_path):
            return jsonify({
                'success': False,
                'error': 'No filtering results found'
            }), 404
        
        # Get the latest summary report
        report_files = list(Path(filtering_results_path).glob('summary_report_*.txt'))
        if not report_files:
            return jsonify({
                'success': False,
                'error': 'No summary report found'
            }), 404
        
        latest_report = max(report_files, key=lambda x: x.stat().st_mtime)
        
        with open(latest_report, 'r') as f:
            report_content = f.read()
        
        # Also get the JSON results
        result_files = list(Path(filtering_results_path).glob('final_results_*.json'))
        if result_files:
            latest_result = max(result_files, key=lambda x: x.stat().st_mtime)
            with open(latest_result, 'r') as f:
                json_results = json.load(f)
        else:
            json_results = {}
        
        return jsonify({
            'success': True,
            'data': {
                'ticket_id': ticket_id,
                'report_text': report_content,
                'report_filename': latest_report.name,
                'generated_at': json_results.get('timestamp'),
                'summary_stats': json_results.get('summary', {}),
                'files': {
                    'report': str(latest_report),
                    'json_results': str(latest_result) if result_files else None
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting filtering report: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/tickets/<ticket_id>/send-top-resumes', methods=['POST'])
@require_api_key
def send_top_resumes_email(ticket_id):
    """Send top resumes via email or webhook"""
    try:
        # Get request data
        data = request.get_json()
        recipient_email = data.get('email')
        webhook_url = data.get('webhook_url')
        include_resumes = data.get('include_resumes', True)
        top_n = min(data.get('top_n', 5), 10)
        
        if not recipient_email and not webhook_url:
            return jsonify({
                'success': False,
                'error': 'Either email or webhook_url is required'
            }), 400
        
        # Get top resumes data
        response = get_top_resumes(ticket_id)
        resume_data = response.get_json()
        
        if not resume_data['success']:
            return response
        
        top_candidates = resume_data['data']['top_candidates'][:top_n]
        
        # Prepare email/webhook payload
        payload = {
            'ticket_id': ticket_id,
            'job_position': resume_data['data']['job_position'],
            'filtered_at': resume_data['data']['filtered_at'],
            'top_candidates': []
        }
        
        # Add candidate details
        for candidate in top_candidates:
            candidate_info = {
                'rank': candidate['rank'],
                'name': candidate.get('applicant_name', 'Unknown'),
                'email': candidate.get('applicant_email', ''),
                'filename': candidate['filename'],
                'scores': candidate['scores'],
                'matched_skills': candidate['matched_skills'],
                'experience_years': candidate['experience_years']
            }
            
            # Add download link
            if CLOUDFLARE_TUNNEL_URL:
                candidate_info['download_url'] = f"{CLOUDFLARE_TUNNEL_URL}/api/tickets/{ticket_id}/resumes/{candidate['filename']}"
            
            payload['top_candidates'].append(candidate_info)
        
        # If webhook URL provided, send to webhook
        if webhook_url:
            import requests
            try:
                webhook_response = requests.post(webhook_url, json=payload, timeout=30)
                if webhook_response.status_code == 200:
                    return jsonify({
                        'success': True,
                        'message': 'Top resumes sent to webhook successfully'
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': f'Webhook returned status {webhook_response.status_code}'
                    }), 500
            except Exception as webhook_error:
                logger.error(f"Webhook error: {webhook_error}")
                return jsonify({
                    'success': False,
                    'error': f'Failed to send to webhook: {str(webhook_error)}'
                }), 500
        
        # If email provided, you would implement email sending here
        if recipient_email:
            # This is a placeholder - you would implement actual email sending
            # using a service like SendGrid, AWS SES, or SMTP
            return jsonify({
                'success': True,
                'message': f'Email functionality not implemented. Would send to: {recipient_email}',
                'payload': payload
            })
        
    except Exception as e:
        logger.error(f"Error sending top resumes: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/tickets/<ticket_id>/filtering-status', methods=['GET'])
@require_api_key
def get_filtering_status(ticket_id):
    """Check if filtering has been done for a ticket"""
    try:
        # Find the ticket folder
        ticket_folders = [f for f in os.listdir(BASE_STORAGE_PATH) 
                         if f.startswith(f"{ticket_id}_")]
        
        if not ticket_folders:
            return jsonify({
                'success': False,
                'status': 'no_folder',
                'message': 'Ticket folder not found'
            })
        
        folder_path = os.path.join(BASE_STORAGE_PATH, ticket_folders[0])
        
        # Check for resumes
        resume_count = len([f for f in os.listdir(folder_path) 
                           if f.endswith(('.pdf', '.doc', '.docx'))])
        
        # Check for filtering results
        filtering_results_path = os.path.join(folder_path, 'filtering_results')
        has_filtering_results = os.path.exists(filtering_results_path)
        
        filtering_info = {}
        if has_filtering_results:
            result_files = list(Path(filtering_results_path).glob('final_results_*.json'))
            if result_files:
                latest_result = max(result_files, key=lambda x: x.stat().st_mtime)
                with open(latest_result, 'r') as f:
                    filtering_data = json.load(f)
                
                filtering_info = {
                    'filtered_at': filtering_data.get('timestamp'),
                    'total_processed': filtering_data.get('summary', {}).get('total_resumes', 0),
                    'top_candidates': len(filtering_data.get('final_top_5', [])),
                    'last_updated': datetime.fromtimestamp(latest_result.stat().st_mtime).isoformat()
                }
        
        return jsonify({
            'success': True,
            'data': {
                'ticket_id': ticket_id,
                'folder_exists': True,
                'resume_count': resume_count,
                'has_filtering_results': has_filtering_results,
                'filtering_info': filtering_info,
                'ready_for_filtering': resume_count > 0 and not has_filtering_results,
                'status': 'filtered' if has_filtering_results else ('ready' if resume_count > 0 else 'no_resumes')
            }
        })
        
    except Exception as e:
        logger.error(f"Error checking filtering status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================
# JOB MANAGEMENT ENDPOINTS
# ============================================

@app.route('/api/jobs/approved', methods=['GET'])
@require_api_key
def get_approved_jobs():
    """Get all approved jobs with pagination and filtering"""
    try:
        # Get query parameters
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 10)), 50)
        location_filter = request.args.get('location', '')
        skills_filter = request.args.get('skills', '')
        sort_by = request.args.get('sort', 'approved_at')
        order = request.args.get('order', 'desc')
        
        # Validate sort parameters
        allowed_sorts = ['created_at', 'approved_at', 'last_updated']
        if sort_by not in allowed_sorts:
            sort_by = 'approved_at'
        
        if order not in ['asc', 'desc']:
            order = 'desc'
        
        offset = (page - 1) * per_page
        
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # First, get all approved tickets
        cursor.execute("""
            SELECT 
                ticket_id,
                sender,
                subject,
                created_at,
                last_updated,
                approved_at,
                status
            FROM tickets
            WHERE approval_status = 'approved' 
                AND status != 'terminated'
            ORDER BY {} {}
            LIMIT %s OFFSET %s
        """.format(sort_by, order), (per_page, offset))
        
        tickets = cursor.fetchall()
        
        # For each ticket, get the LATEST value for each field
        jobs = []
        for ticket in tickets:
            ticket_id = ticket['ticket_id']
            
            # Get the latest value for each field using a subquery
            cursor.execute("""
                SELECT 
                    td1.field_name,
                    td1.field_value
                FROM ticket_details td1
                INNER JOIN (
                    SELECT field_name, MAX(created_at) as max_created_at
                    FROM ticket_details
                    WHERE ticket_id = %s
                    GROUP BY field_name
                ) td2 ON td1.field_name = td2.field_name 
                     AND td1.created_at = td2.max_created_at
                WHERE td1.ticket_id = %s
            """, (ticket_id, ticket_id))
            
            # Build the job details
            job_details = {}
            for row in cursor.fetchall():
                job_details[row['field_name']] = row['field_value']
            
            # Apply location filter if specified
            if location_filter and job_details.get('location', '').lower() != location_filter.lower():
                continue
            
            # Apply skills filter if specified
            if skills_filter:
                skill_list = [s.strip().lower() for s in skills_filter.split(',')]
                job_skills = job_details.get('required_skills', '').lower()
                if not any(skill in job_skills for skill in skill_list):
                    continue
            
            # Check if this job was updated after approval
            cursor.execute("""
                SELECT COUNT(*) as update_count
                FROM ticket_updates
                WHERE ticket_id = %s AND update_timestamp > %s
            """, (ticket_id, ticket['approved_at']))
            
            update_info = cursor.fetchone()
            updated_after_approval = update_info['update_count'] > 0
            
            # Check if folder exists and get resume count
            resumes = get_ticket_resumes(ticket_id)
            
            # Combine ticket info with job details
            job = {
                'ticket_id': ticket['ticket_id'],
                'sender': ticket['sender'],
                'subject': ticket['subject'],
                'created_at': serialize_datetime(ticket['created_at']),
                'last_updated': serialize_datetime(ticket['last_updated']),
                'approved_at': serialize_datetime(ticket['approved_at']),
                'status': ticket['status'],
                'job_title': job_details.get('job_title', 'NOT_FOUND'),
                'location': job_details.get('location', 'NOT_FOUND'),
                'experience_required': job_details.get('experience_required', 'NOT_FOUND'),
                'salary_range': job_details.get('salary_range', 'NOT_FOUND'),
                'job_description': job_details.get('job_description', 'NOT_FOUND'),
                'required_skills': job_details.get('required_skills', 'NOT_FOUND'),
                'employment_type': job_details.get('employment_type', 'NOT_FOUND'),
                'deadline': job_details.get('deadline', 'NOT_FOUND'),
                'updated_after_approval': updated_after_approval,
                'resume_count': len(resumes),
                'has_folder': len([f for f in os.listdir(BASE_STORAGE_PATH) if f.startswith(f"{ticket_id}_")]) > 0
            }
            
            jobs.append(job)
        
        # Get total count for pagination
        count_query = """
            SELECT COUNT(*) as total
            FROM tickets
            WHERE approval_status = 'approved' 
                AND status != 'terminated'
        """
        cursor.execute(count_query)
        total_count = cursor.fetchone()['total']
        
        cursor.close()
        conn.close()
        
        # Calculate pagination info
        total_pages = (total_count + per_page - 1) // per_page
        
        return jsonify({
            'success': True,
            'data': {
                'jobs': jobs,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total_count,
                    'total_pages': total_pages,
                    'has_next': page < total_pages,
                    'has_prev': page > 1
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error in get_approved_jobs: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/jobs/<ticket_id>', methods=['GET'])
@require_api_key
def get_job_details(ticket_id):
    """Get detailed information about a specific job"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Get ticket information
        cursor.execute("""
            SELECT * FROM tickets 
            WHERE ticket_id = %s
        """, (ticket_id,))
        
        ticket = cursor.fetchone()
        
        if not ticket:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Job not found'
            }), 404
        
        # Get the LATEST value for each field
        cursor.execute("""
            SELECT 
                td1.field_name,
                td1.field_value,
                td1.created_at,
                td1.is_initial
            FROM ticket_details td1
            INNER JOIN (
                SELECT field_name, MAX(created_at) as max_created_at
                FROM ticket_details
                WHERE ticket_id = %s
                GROUP BY field_name
            ) td2 ON td1.field_name = td2.field_name 
                 AND td1.created_at = td2.max_created_at
            WHERE td1.ticket_id = %s
        """, (ticket_id, ticket_id))
        
        current_details = {}
        for row in cursor.fetchall():
            current_details[row['field_name']] = row['field_value']
        
        # Get complete history
        cursor.execute("""
            SELECT field_name, field_value, created_at, is_initial
            FROM ticket_details 
            WHERE ticket_id = %s
            ORDER BY field_name, created_at DESC
        """, (ticket_id,))
        
        all_details = cursor.fetchall()
        
        # Organize history by field
        detail_history = {}
        for row in all_details:
            field_name = row['field_name']
            if field_name not in detail_history:
                detail_history[field_name] = []
            
            detail_history[field_name].append({
                'value': row['field_value'],
                'updated_at': serialize_datetime(row['created_at']),
                'is_initial': row['is_initial']
            })
        
        # Get update history
        cursor.execute("""
            SELECT update_timestamp, updated_fields
            FROM ticket_updates
            WHERE ticket_id = %s
            ORDER BY update_timestamp DESC
        """, (ticket_id,))
        
        updates = []
        for row in cursor.fetchall():
            updates.append({
                'timestamp': serialize_datetime(row['update_timestamp']),
                'fields': json.loads(row['updated_fields']) if row['updated_fields'] else {}
            })
        
        # Convert datetime objects in ticket
        for key, value in ticket.items():
            ticket[key] = serialize_datetime(value)
        
        # Get resume information
        resumes = get_ticket_resumes(ticket_id)
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'ticket': ticket,
                'current_details': current_details,
                'history': detail_history,
                'updates': updates,
                'is_approved': ticket['approval_status'] == 'approved',
                'updated_after_approval': len([u for u in updates if u['timestamp'] > ticket['approved_at']]) > 0 if ticket['approved_at'] else False,
                'resumes': resumes,
                'resume_count': len(resumes)
            }
        })
        
    except Exception as e:
        logger.error(f"Error in get_job_details: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/jobs/search', methods=['GET'])
@require_api_key
def search_jobs():
    """Search jobs by keyword"""
    try:
        query = request.args.get('q', '').strip()
        
        if not query:
            return jsonify({
                'success': False,
                'error': 'Search query is required'
            }), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # First, get all approved tickets
        cursor.execute("""
            SELECT DISTINCT
                t.ticket_id,
                t.subject,
                t.created_at,
                t.approved_at,
                t.last_updated
            FROM tickets t
            WHERE t.approval_status = 'approved' 
                AND t.status != 'terminated'
            ORDER BY t.approved_at DESC
        """)
        
        tickets = cursor.fetchall()
        jobs = []
        
        for ticket in tickets:
            ticket_id = ticket['ticket_id']
            
            # Get latest values for this ticket
            cursor.execute("""
                SELECT 
                    td1.field_name,
                    td1.field_value
                FROM ticket_details td1
                INNER JOIN (
                    SELECT field_name, MAX(created_at) as max_created_at
                    FROM ticket_details
                    WHERE ticket_id = %s
                    GROUP BY field_name
                ) td2 ON td1.field_name = td2.field_name 
                     AND td1.created_at = td2.max_created_at
                WHERE td1.ticket_id = %s
            """, (ticket_id, ticket_id))
            
            job_details = {}
            for row in cursor.fetchall():
                job_details[row['field_name']] = row['field_value']
            
            # Check if search query matches any field
            search_text = query.lower()
            if (search_text in ticket['subject'].lower() or
                search_text in job_details.get('job_title', '').lower() or
                search_text in job_details.get('job_description', '').lower() or
                search_text in job_details.get('required_skills', '').lower() or
                search_text in job_details.get('location', '').lower()):
                
                job = {
                    'ticket_id': ticket['ticket_id'],
                    'subject': ticket['subject'],
                    'created_at': serialize_datetime(ticket['created_at']),
                    'approved_at': serialize_datetime(ticket['approved_at']),
                    'last_updated': serialize_datetime(ticket['last_updated']),
                    'job_title': job_details.get('job_title', 'NOT_FOUND'),
                    'location': job_details.get('location', 'NOT_FOUND'),
                    'experience_required': job_details.get('experience_required', 'NOT_FOUND'),
                    'salary_range': job_details.get('salary_range', 'NOT_FOUND'),
                    'job_description': job_details.get('job_description', 'NOT_FOUND'),
                    'required_skills': job_details.get('required_skills', 'NOT_FOUND'),
                    'employment_type': job_details.get('employment_type', 'NOT_FOUND'),
                    'deadline': job_details.get('deadline', 'NOT_FOUND')
                }
                jobs.append(job)
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'query': query,
                'count': len(jobs),
                'jobs': jobs
            }
        })
        
    except Exception as e:
        logger.error(f"Error in search_jobs: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/stats', methods=['GET'])
@require_api_key
def get_statistics():
    """Get hiring statistics and analytics"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Overall statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_tickets,
                SUM(CASE WHEN approval_status = 'approved' THEN 1 ELSE 0 END) as approved_jobs,
                SUM(CASE WHEN approval_status = 'pending' THEN 1 ELSE 0 END) as pending_approval,
                SUM(CASE WHEN approval_status = 'rejected' THEN 1 ELSE 0 END) as rejected_jobs,
                SUM(CASE WHEN status = 'terminated' THEN 1 ELSE 0 END) as terminated_jobs
            FROM tickets
        """)
        
        overall_stats = cursor.fetchone()
        
        # Jobs by location - using latest values
        cursor.execute("""
            SELECT 
                latest.location,
                COUNT(*) as count
            FROM (
                SELECT 
                    t.ticket_id,
                    td1.field_value as location
                FROM tickets t
                JOIN ticket_details td1 ON t.ticket_id = td1.ticket_id
                INNER JOIN (
                    SELECT ticket_id, MAX(created_at) as max_created_at
                    FROM ticket_details
                    WHERE field_name = 'location'
                    GROUP BY ticket_id
                ) td2 ON td1.ticket_id = td2.ticket_id 
                     AND td1.created_at = td2.max_created_at
                WHERE td1.field_name = 'location'
                    AND t.approval_status = 'approved'
                    AND t.status != 'terminated'
            ) latest
            GROUP BY latest.location
            ORDER BY count DESC
        """)
        
        locations = cursor.fetchall()
        
        # Recent activity (last 7 days)
        cursor.execute("""
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as new_jobs
            FROM tickets
            WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """)
        
        recent_activity = cursor.fetchall()
        
        # Convert dates
        for activity in recent_activity:
            activity['date'] = activity['date'].isoformat()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'overall': overall_stats,
                'by_location': locations,
                'recent_activity': recent_activity
            }
        })
        
    except Exception as e:
        logger.error(f"Error in get_statistics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/locations', methods=['GET'])
@require_api_key
def get_locations():
    """Get list of all unique locations using latest values"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT td1.field_value
            FROM ticket_details td1
            INNER JOIN (
                SELECT ticket_id, MAX(created_at) as max_created_at
                FROM ticket_details
                WHERE field_name = 'location'
                GROUP BY ticket_id
            ) td2 ON td1.ticket_id = td2.ticket_id 
                 AND td1.created_at = td2.max_created_at
            JOIN tickets t ON td1.ticket_id = t.ticket_id
            WHERE td1.field_name = 'location'
                AND td1.field_value IS NOT NULL
                AND td1.field_value != 'NOT_FOUND'
                AND t.approval_status = 'approved'
            ORDER BY td1.field_value
        """)
        
        locations = [row[0] for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'locations': locations
            }
        })
        
    except Exception as e:
        logger.error(f"Error in get_locations: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/skills', methods=['GET'])
@require_api_key
def get_skills():
    """Get list of all unique skills using latest values"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT td1.field_value
            FROM ticket_details td1
            INNER JOIN (
                SELECT ticket_id, MAX(created_at) as max_created_at
                FROM ticket_details
                WHERE field_name = 'required_skills'
                GROUP BY ticket_id
            ) td2 ON td1.ticket_id = td2.ticket_id 
                 AND td1.created_at = td2.max_created_at
            JOIN tickets t ON td1.ticket_id = t.ticket_id
            WHERE td1.field_name = 'required_skills'
                AND td1.field_value IS NOT NULL
                AND td1.field_value != 'NOT_FOUND'
                AND t.approval_status = 'approved'
        """)
        
        # Extract unique skills
        all_skills = set()
        for row in cursor.fetchall():
            skills_text = row[0]
            # Split by common delimiters
            skills = re.split(r'[,;|\n]', skills_text)
            for skill in skills:
                skill = skill.strip()
                if skill:
                    all_skills.add(skill)
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'skills': sorted(list(all_skills))
            }
        })
        
    except Exception as e:
        logger.error(f"Error in get_skills: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================
# TICKET MANAGEMENT ENDPOINTS (for chat bot)
# ============================================

@app.route('/api/tickets/<user_id>', methods=['GET'])
def get_user_tickets(user_id):
    """Get all tickets for a user"""
    try:
        tickets = chat_bot.ticket_manager.get_user_tickets(user_id)
        
        # Format tickets for response
        formatted_tickets = []
        for ticket in tickets:
            formatted_tickets.append({
                'ticket_id': ticket['ticket_id'],
                'job_title': ticket.get('job_title', 'Untitled'),
                'status': ticket['status'],
                'approval_status': ticket['approval_status'],
                'created_at': ticket['created_at'].isoformat() if ticket.get('created_at') else None,
                'updated_at': ticket['last_updated'].isoformat() if ticket.get('last_updated') else None
            })
        
        return jsonify({
            'user_id': user_id,
            'tickets': formatted_tickets,
            'count': len(formatted_tickets)
        })
    
    except Exception as e:
        logger.error(f"Error fetching tickets: {e}")
        return jsonify({
            'error': 'Failed to fetch tickets',
            'message': str(e)
        }), 500

@app.route('/api/tickets/<ticket_id>/details', methods=['GET'])
def get_ticket_details(ticket_id):
    """Get detailed information about a specific ticket"""
    try:
        ticket = chat_bot.ticket_manager.get_ticket_details(ticket_id)
        
        if not ticket:
            return jsonify({
                'error': 'Ticket not found',
                'ticket_id': ticket_id
            }), 404
        
        # Format response
        response = {
            'ticket_id': ticket['ticket_id'],
            'status': ticket['status'],
            'approval_status': ticket['approval_status'],
            'created_at': ticket['created_at'].isoformat() if ticket.get('created_at') else None,
            'details': ticket.get('details', {})
        }
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error fetching ticket details: {e}")
        return jsonify({
            'error': 'Failed to fetch ticket details',
            'message': str(e)
        }), 500

# ============================================
# WEBSOCKET EVENTS
# ============================================

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    logger.info(f"Client connected: {request.sid}")
    emit('connected', {
        'message': 'Connected to hiring bot server',
        'features': ['chat', 'api', 'file_upload', 'resume_filtering'],
        'timestamp': datetime.now().isoformat(),
        'tunnel_url': CLOUDFLARE_TUNNEL_URL
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('start_session')
def handle_start_session(data):
    """Start a new chat session via WebSocket"""
    try:
        user_id = data.get('user_id')
        result = chat_bot.start_session(user_id)
        emit('session_started', result)
    except Exception as e:
        logger.error(f"WebSocket error starting session: {e}")
        emit('error', {'error': str(e)})

@socketio.on('send_message')
def handle_websocket_message(data):
    """Handle incoming message via WebSocket"""
    try:
        session_id = data.get('session_id')
        user_id = data.get('user_id')
        message = data.get('message')
        
        if not all([session_id, user_id, message]):
            emit('error', {'error': 'Missing required fields'})
            return
        
        # Process message
        bot_response = chat_bot.process_message(session_id, user_id, message)
        
        # Format response for WebSocket
        formatted_response = {
            'response': bot_response.get('message', ''),
            'metadata': bot_response.get('metadata', {}),
            'session_id': session_id,
            'timestamp': datetime.now().isoformat()
        }
        
        emit('message_response', formatted_response)
    
    except Exception as e:
        logger.error(f"WebSocket error processing message: {e}")
        emit('error', {'error': str(e)})

# ============================================
# ERROR HANDLERS
# ============================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'error': 'Not found',
        'message': 'The requested resource was not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred'
    }), 500

# ============================================
# CLEANUP HANDLER
# ============================================

def cleanup_on_exit(signum=None, frame=None):
    """Cleanup function to stop tunnel on exit"""
    print("\n🛑 Shutting down...")
    stop_cloudflare_tunnel()
    sys.exit(0)

# Register cleanup handlers
signal.signal(signal.SIGINT, cleanup_on_exit)
signal.signal(signal.SIGTERM, cleanup_on_exit)

# ============================================
# MAIN EXECUTION
# ============================================

def main():
    """Run the complete server"""
    # Get local IP address
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    print("="*80)
    print("🚀 COMPLETE HIRING BOT SERVER - CHAT + API + CLOUDFLARE TUNNEL")
    print("="*80)
    print(f"Database: {MYSQL_CONFIG['database']}@{MYSQL_CONFIG['host']}")
    print(f"Local URL: http://localhost:{API_PORT}")
    print(f"Network URL: http://{local_ip}:{API_PORT}")
    print(f"API Key: {API_KEY}")
    print(f"Storage Path: {BASE_STORAGE_PATH}")
    print("="*80)
    
    # Create folders for existing approved tickets
    create_folders_for_existing_approved_tickets()
    
    # Start Cloudflare tunnel
    tunnel_url = start_cloudflare_tunnel()
    
    if tunnel_url:
        print("\n📱 Your complete system is accessible globally!")
        print(f"   Public URL: {tunnel_url}")
        print(f"\n🔗 For React Frontend:")
        print(f"   const API_BASE_URL = '{tunnel_url}';")
        print(f"\n🔐 Example API calls:")
        print(f"   # Chat Interface:")
        print(f"   {tunnel_url}")
        print(f"\n   # Get approved jobs:")
        print(f"   curl -H 'X-API-Key: {API_KEY}' {tunnel_url}/api/jobs/approved")
        print(f"\n   # Get top resumes:")
        print(f"   curl -H 'X-API-Key: {API_KEY}' {tunnel_url}/api/tickets/TICKET_ID/top-resumes")
        print(f"\n   # Upload resume:")
        print(f"   curl -X POST -H 'X-API-Key: {API_KEY}' \\")
        print(f"        -F 'resume=@resume.pdf' \\")
        print(f"        -F 'applicant_name=John Doe' \\")
        print(f"        -F 'applicant_email=john@example.com' \\")
        print(f"        {tunnel_url}/api/tickets/TICKET_ID/resumes")
    else:
        print("\n⚠️  Running in local mode only")
        print("   Install cloudflared for public access")
    
    print("\n📚 Features:")
    print("  ✅ Chat Bot - AI-powered job posting assistant")
    print("  ✅ Job Management API - Full REST API")
    print("  ✅ Resume Management - Upload and organize resumes")
    print("  ✅ Resume Filtering - AI-powered candidate ranking")
    print("  ✅ WebSocket Support - Real-time communication")
    print("  ✅ Cloudflare Tunnel - Global accessibility")
    
    print("\n📚 API Endpoints:")
    print("\n🔹 Chat:")
    print("  POST /api/chat/start")
    print("  POST /api/chat/message")
    print("  GET  /api/chat/history/<id>")
    
    print("\n🔹 Job Management:")
    print("  GET  /api/jobs/approved")
    print("  GET  /api/jobs/<id>")
    print("  GET  /api/jobs/search?q=<query>")
    print("  GET  /api/stats")
    print("  GET  /api/locations")
    print("  GET  /api/skills")
    
    print("\n🔹 Resume Management:")
    print("  POST /api/tickets/<id>/approve")
    print("  POST /api/tickets/<id>/resumes")
    print("  GET  /api/tickets/<id>/resumes")
    print("  GET  /api/tickets/<id>/resumes/<filename>")
    
    print("\n🔹 Resume Filtering:")
    print("  GET  /api/tickets/<id>/filtering-status")
    print("  POST /api/tickets/<id>/filter-resumes")
    print("  GET  /api/tickets/<id>/top-resumes")
    print("  GET  /api/tickets/<id>/filtering-report")
    print("  POST /api/tickets/<id>/send-top-resumes")
    
    print("\n✋ Press CTRL+C to stop the server")
    print("="*80 + "\n")
    
    try:
        # Run with SocketIO for WebSocket support
        socketio.run(app, host='0.0.0.0', port=API_PORT, debug=False)
    except KeyboardInterrupt:
        cleanup_on_exit()
    except Exception as e:
        print(f"❌ Server error: {e}")
        cleanup_on_exit()

if __name__ == '__main__':
    main()