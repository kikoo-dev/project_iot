from flask import Flask, render_template, request, jsonify
from sqlalchemy.orm import Session
import datetime

# import dari file database kamu
from database import SessionLocal, SensorReading

app = Flask(__name__)

# Dependency DB session
def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        pass

#yang arif kerjain

# 1️⃣ Halaman Dashboard
@app.route('/')
def index():
    return render_template('index.html')


# 2️⃣ API menerima data dari sensor (POST)
@app.route('/api/data', methods=['POST'])
def post_data():
    try:
        data = request.json

        temperature = data.get('temperature')
        humidity = data.get('humidity')
        # Only accept sensors for this setup: DHT, LDR, PIR and LED states
        light_level = data.get('light_level')
        ldr = data.get('ldr')
        motion_detected = data.get('motion_detected')
        motion_count = data.get('motion_count')
        # incoming actuator states (raspberry can compute and send)
        led_red = data.get('led_red')
        led_blue = data.get('led_blue')
        led_yellow = data.get('led_yellow')
        led_white = data.get('led_white')

        # Basic validation: required core fields for this setup
        if None in [temperature, humidity, light_level, motion_detected]:
            return jsonify({
                'status': 'error',
                'message': 'Missing core data fields (temperature, humidity, light_level, motion_detected)'
            }), 400

        db: Session = get_db()

        sensor_data = SensorReading(
            temperature=temperature,
            humidity=humidity,
            light_level=light_level,
            ldr=ldr,
            motion_detected=motion_detected,
            motion_count=motion_count,
            led_red=led_red,
            led_blue=led_blue,
            led_yellow=led_yellow,
            led_white=led_white
        )

        db.add(sensor_data)
        db.commit()
        db.refresh(sensor_data)
        db.close()

        return jsonify({
            'status': 'success',
            'message': 'Data stored successfully'
        }), 201

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# 3️⃣ API ambil data terbaru (GET)
@app.route('/api/latest_data')
def get_latest_data():
    db: Session = get_db()

    data = db.query(SensorReading)\
             .order_by(SensorReading.id.desc())\
             .first()

    db.close()

    if data:
        return jsonify({
            'id': data.id,
            'temperature': data.temperature,
            'humidity': data.humidity,
            'light_level': data.light_level,
            'ldr': data.ldr,
            'motion_detected': data.motion_detected,
            'motion_count': data.motion_count,
            'led_red': bool(data.led_red),
            'led_blue': bool(data.led_blue),
            'led_yellow': bool(data.led_yellow),
            'led_white': bool(data.led_white),
            'timestamp': data.created_at.strftime('%H:%M:%S, %d %b')
        })

    return jsonify({'status': 'no_data'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)