# Skrip Dummy Sensor (Untuk Simulasi)
import requests
import time
import random

# Pastikan ini menunjuk ke alamat yang benar (localhost:5000)
FLASK_SERVER_URL = 'http://127.0.0.1:5000/api/data' 

def send_data_to_flask():
    temperature = random.uniform(20.0, 30.0) 
    humidity = random.uniform(50.0, 70.0)    
    air_quality = random.uniform(100.0, 350.0)

    payload = {
        'temperature': temperature,
        'humidity': humidity,
        'air_quality': air_quality
    }

    try:
        response = requests.post(FLASK_SERVER_URL, json=payload)
        response.raise_for_status() 
        print(f"[{time.strftime('%H:%M:%S')}] Data dikirim: Suhu={temperature:.1f}C, Status: {response.json().get('status')}")
    except requests.exceptions.RequestException as e:
        print(f"Error saat mengirim data: {e}")

if __name__ == '__main__':
    print("Mulai mengirim data dummy setiap 10 detik. Tekan Ctrl+C untuk berhenti.")
    while True:
        send_data_to_flask()
        time.sleep(10)