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
        gas_level = data.get('gas_level')
        light_level = data.get('light_level')
        motion_detected = data.get('motion_detected')
        # Optional/extended fields
        air_quality = data.get('air_quality')
        distance = data.get('distance')
        sound_level = data.get('sound_level')
        mq135 = data.get('mq135')
        ldr = data.get('ldr')
        mic = data.get('mic')

        # Basic validation: required core fields
        if None in [temperature, gas_level, light_level, motion_detected]:
            return jsonify({
                'status': 'error',
                'message': 'Missing core data fields (temperature, gas_level, light_level, motion_detected)'
            }), 400

        db: Session = get_db()

        sensor_data = SensorReading(
            temperature=temperature,
            gas_level=gas_level,
            light_level=light_level,
            motion_detected=motion_detected,
            humidity=humidity,
            air_quality=air_quality,
            distance=distance,
            sound_level=sound_level,
            mq135=mq135,
            ldr=ldr,
            mic=mic
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
            'gas_level': data.gas_level,
            'light_level': data.light_level,
            'motion_detected': data.motion_detected,
            'air_quality': data.air_quality,
            'distance': data.distance,
            'sound_level': data.sound_level,
            'mq135': data.mq135,
            'ldr': data.ldr,
            'mic': data.mic,
            'timestamp': data.created_at.strftime('%H:%M:%S, %d %b')
        })

    return jsonify({'status': 'no_data'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)