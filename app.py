from flask import Flask, render_template, request, jsonify
import sqlite3
import datetime

app = Flask(__name__)
DATABASE_NAME = 'environment_data.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# 1. Halaman Dashboard
@app.route('/')
def index():
    return render_template('index.html')

# 2. API untuk menerima data POST dari sensor
@app.route('/api/data', methods=['POST'])
def post_data():
    try:
        data = request.json
        temp = data.get('temperature')
        humi = data.get('humidity')
        airq = data.get('air_quality')

        if None in [temp, humi, airq]:
            return jsonify({'status': 'error', 'message': 'Missing data fields'}), 400

        conn = get_db_connection()
        conn.execute("INSERT INTO environment_data (temperature, humidity, air_quality) VALUES (?, ?, ?)",
                    (temp, humi, airq))
        conn.commit()
        conn.close()

        return jsonify({'status': 'success', 'message': 'Data received and stored'}), 201

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# 3. API untuk menyajikan data terbaru ke Frontend
@app.route('/api/latest_data')
def get_latest_data():
    conn = get_db_connection()
    data = conn.execute("SELECT * FROM environment_data ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()

    if data:
        latest_data = dict(data)
        # Formatting timestamp
        latest_data['timestamp'] = datetime.datetime.strptime(latest_data['timestamp'], '%Y-%m-%d %H:%M:%S').strftime('%H:%M:%S, %d %b')
        return jsonify(latest_data)
    else:
        return jsonify({'status': 'no_data'})

if __name__ == '__main__':
    app.run(debug=True)