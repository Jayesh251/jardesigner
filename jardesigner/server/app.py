import os
import json
import subprocess
import uuid
import time
import threading
import shutil
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, join_room
from werkzeug.utils import secure_filename

# --- Configuration ---
SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(SERVER_DIR, 'static')

# Create temp directories in user's home
USER_DATA_DIR = os.path.expanduser('~/.jardesigner')
TEMP_CONFIG_DIR = os.path.join(USER_DATA_DIR, 'temp_configs')
USER_UPLOADS_DIR = os.path.join(USER_DATA_DIR, 'user_uploads')

os.makedirs(TEMP_CONFIG_DIR, exist_ok=True)
os.makedirs(USER_UPLOADS_DIR, exist_ok=True)

# --- Flask App Initialization ---
app = Flask(__name__, static_folder=STATIC_DIR, static_url_path='')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# --- Store running process and session info ---
running_processes = {}
client_sim_map = {}
sid_clientid_map = {}

def stream_printer(stream, pid, stream_name):
    """Reads a stream line-by-line and prints it to the console in real-time."""
    try:
        for line in iter(stream.readline, ''):
            if line:
                print(f"[{pid}-{stream_name}] {line.strip()}")
        stream.close()
    except Exception as e:
        print(f"Error in stream printer for PID {pid} ({stream_name}): {e}")

def terminate_process(pid):
    """Safely terminates a running process and cleans up its entry."""
    if pid in running_processes:
        try:
            proc_info = running_processes[pid]
            if proc_info["process"].poll() is None:
                proc_info["process"].terminate()
                proc_info["process"].wait(timeout=5)
            del running_processes[pid]
            return True
        except Exception as e:
            if pid in running_processes:
                del running_processes[pid]
    return False

# --- API Endpoints ---
@app.route('/')
def index():
    """Serve the main frontend application"""
    index_path = os.path.join(STATIC_DIR, 'index.html')
    if os.path.exists(index_path):
        return send_file(index_path)
    else:
        return jsonify({
            "error": "Frontend not built",
            "message": "Please build the frontend with: cd frontend && npm install && npm run build"
        }), 404

@app.route('/health')
def health():
    return jsonify({"status": "ok", "message": "JARDesigner server is running!"})

@app.route('/upload_file', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part"}), 400
    file = request.files['file']
    client_id = request.form.get('clientId')
    if not client_id:
        return jsonify({"status": "error", "message": "No clientId"}), 400
    if file.filename == '':
        return jsonify({"status": "error", "message": "No file selected"}), 400
    if file:
        filename = secure_filename(file.filename)
        session_dir = os.path.join(USER_UPLOADS_DIR, client_id)
        os.makedirs(session_dir, exist_ok=True)
        save_path = os.path.join(session_dir, filename)
        file.save(save_path)
        return jsonify({"status": "success"}), 200
    return jsonify({"status": "error"}), 500

@socketio.on('sim_command')
def handle_sim_command(data):
    pid_str = data.get('pid')
    command = data.get('command')
    if not pid_str or not command:
        return
    try:
        pid = int(pid_str)
    except (ValueError, TypeError):
        return
    if pid in running_processes:
        process = running_processes[pid]["process"]
        if process.poll() is None:
            try:
                command_payload = {"command": command, "params": data.get("params", {})}
                command_string = json.dumps(command_payload) + '\n'
                process.stdin.write(command_string)
                process.stdin.flush()
            except Exception as e:
                print(f"Error writing to PID {pid} stdin: {e}")

@app.route('/launch_simulation', methods=['POST'])
def launch_simulation():
    request_data = request.json
    config_data = request_data.get('config_data')
    client_id = request_data.get('client_id')
    if not config_data or not isinstance(config_data, dict):
        return jsonify({"status": "error", "message": "Invalid config"}), 400
    if not client_id:
        return jsonify({"status": "error", "message": "Missing client_id"}), 400
    if client_id in client_sim_map:
        old_pid = client_sim_map[client_id]
        terminate_process(old_pid)
        client_sim_map.pop(client_id, None)
    try:
        temp_file_name = f"config_{str(uuid.uuid4())}.json"
        temp_file_path = os.path.join(TEMP_CONFIG_DIR, temp_file_name)
        with open(temp_file_path, 'w', encoding='utf-8') as temp_file:
            json.dump(config_data, temp_file, indent=2)
    except Exception as e:
        return jsonify({"status": "error", "message": f"Could not save config: {e}"}), 500
    session_dir = os.path.join(USER_UPLOADS_DIR, client_id)
    os.makedirs(session_dir, exist_ok=True)
    svg_filename = "plot.svg"
    svg_filepath = os.path.abspath(os.path.join(session_dir, svg_filename))
    data_channel_id = str(uuid.uuid4())
    command = [
        "python", "-u", "-m", "jardesigner.jardesigner",
        temp_file_path, "--plotFile", svg_filepath,
        "--data-channel-id", data_channel_id, "--session-path", session_dir
    ]
    try:
        process = subprocess.Popen(
            command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1
        )
        running_processes[process.pid] = {
            "process": process, "svg_filename": svg_filename,
            "temp_config_file_path": temp_file_path, "start_time": time.time(),
            "data_channel_id": data_channel_id, "client_id": client_id,
        }
        client_sim_map[client_id] = process.pid
        threading.Thread(target=stream_printer, args=(process.stdout, process.pid, 'stdout'), daemon=True).start()
        threading.Thread(target=stream_printer, args=(process.stderr, process.pid, 'stderr'), daemon=True).start()
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to launch: {e}"}), 500
    return jsonify({
        "status": "success", "pid": process.pid,
        "svg_filename": svg_filename, "data_channel_id": data_channel_id
    }), 200

@app.route('/internal/push_data', methods=['POST'])
def push_data():
    data = request.json
    channel_id = data.get('data_channel_id')
    payload = data.get('payload')
    if not channel_id or payload is None:
        return jsonify({"status": "error"}), 400
    socketio.emit('simulation_data', payload, room=channel_id)
    return jsonify({"status": "success"}), 200

@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")

@socketio.on('register_client')
def handle_register_client(data):
    client_id = data.get('clientId')
    if client_id:
        sid_clientid_map[request.sid] = client_id

@socketio.on('disconnect')
def handle_disconnect():
    client_id = sid_clientid_map.get(request.sid)
    if client_id:
        session_dir = os.path.join(USER_UPLOADS_DIR, client_id)
        if os.path.exists(session_dir):
            try:
                shutil.rmtree(session_dir)
            except Exception as e:
                pass
        sid_clientid_map.pop(request.sid, None)
        pid = client_sim_map.pop(client_id, None)
        if pid:
            terminate_process(pid)

@socketio.on('join_sim_channel')
def handle_join_sim_channel(data):
    channel_id = data.get('data_channel_id')
    if channel_id:
        join_room(channel_id)

@app.route('/simulation_status/<int:pid>', methods=['GET'])
def simulation_status(pid):
    if pid not in running_processes:
        return jsonify({"status": "error", "message": "PID not found"}), 404
    proc_info = running_processes[pid]
    process = proc_info["process"]
    svg_filename = proc_info["svg_filename"]
    client_id = proc_info["client_id"]
    session_dir = os.path.join(USER_UPLOADS_DIR, client_id)
    svg_filepath = os.path.abspath(os.path.join(session_dir, svg_filename))
    if process.poll() is None:
        return jsonify({"status": "running", "pid": pid}), 200
    else:
        plot_exists = os.path.exists(svg_filepath)
        if plot_exists:
            return jsonify({"status": "completed", "pid": pid, "svg_filename": svg_filename, "plot_ready": True}), 200
        else:
            return jsonify({"status": "completed_error", "pid": pid}), 200

@app.route('/session_file/<client_id>/<filename>')
def get_session_file(client_id, filename):
    if '..' in client_id or '/' in client_id or '..' in filename:
        return jsonify({"status": "error"}), 400
    session_dir = os.path.join(USER_UPLOADS_DIR, client_id)
    return send_from_directory(session_dir, filename)

@app.route('/reset_simulation', methods=['POST'])
def reset_simulation():
    request_data = request.json
    pid_to_reset_str = request_data.get('pid')
    client_id = request_data.get('client_id')
    if not pid_to_reset_str:
        return jsonify({"status": "error"}), 400
    try:
        pid_to_reset = int(pid_to_reset_str)
    except (ValueError, TypeError):
        return jsonify({"status": "error"}), 400
    if terminate_process(pid_to_reset):
        if client_id and client_id in client_sim_map:
            client_sim_map.pop(client_id, None)
        return jsonify({"status": "success"}), 200
    else:
        return jsonify({"status": "error"}), 404
