import time
import random
import requests
import platform

# --- KONFIGURASI ---
# Pastikan IP ini sesuai dengan IP laptop/server Flask kamu
SERVER_IP = "192.168.1.162"
PORT = "5000"
ENDPOINT = f"http://{SERVER_IP}:{PORT}/api/data"

# GPIO / hardware libs will be optional so this script can run on laptop
HAS_RPI = False
try:
    import RPi.GPIO as GPIO
    import spidev
    import Adafruit_DHT
    HAS_RPI = True
except Exception:
    # Running on laptop or missing libs -> we'll use simulated values
    HAS_RPI = False


def init_hardware():
    hw = {}
    if not HAS_RPI:
        return hw

    # MCP3008 SPI
    spi = spidev.SpiDev()
    spi.open(0, 0)
    spi.max_speed_hz = 1350000
    hw['spi'] = spi

    # GPIO setup
    GPIO.setmode(GPIO.BCM)
    # PIR on GPIO17
    PIR_PIN = 17
    GPIO.setup(PIR_PIN, GPIO.IN)
    hw['pir_pin'] = PIR_PIN

    # Ultrasonic pins
    TRIG = 23
    ECHO = 24
    GPIO.setup(TRIG, GPIO.OUT)
    GPIO.setup(ECHO, GPIO.IN)
    hw['trig'] = TRIG
    hw['echo'] = ECHO

    return hw


def read_mcp(spi, channel=0):
    # channel 0-7
    if spi is None:
        return None
    adc = spi.xfer2([1, (8 + channel) << 4, 0])
    data = ((adc[1] & 3) << 8) + adc[2]
    return data


def read_dht(pin=4):
    # returns (humidity, temperature)
    try:
        humidity, temperature = Adafruit_DHT.read_retry(Adafruit_DHT.DHT22, pin)
        return humidity, temperature
    except Exception:
        return None, None


def read_ultrasonic(trig, echo):
    # returns distance in cm
    try:
        GPIO.output(trig, False)
        time.sleep(0.05)
        GPIO.output(trig, True)
        time.sleep(0.00001)
        GPIO.output(trig, False)

        pulse_start = time.time()
        timeout = pulse_start + 0.04
        while GPIO.input(echo) == 0 and time.time() < timeout:
            pulse_start = time.time()

        pulse_end = time.time()
        timeout = pulse_end + 0.04
        while GPIO.input(echo) == 1 and time.time() < timeout:
            pulse_end = time.time()

        pulse_duration = pulse_end - pulse_start
        distance = pulse_duration * 17150
        return round(distance, 2)
    except Exception:
        return None


def read_pir(pin):
    try:
        return bool(GPIO.input(pin))
    except Exception:
        return False


def build_payload(hw):
    if not HAS_RPI:
        # Simulasi jika tidak ada hardware
        temp = round(random.uniform(24.0, 32.0), 2)
        humidity = round(random.uniform(40.0, 70.0), 1)
        mq135 = round(random.uniform(150, 450), 1)
        ldr = random.randint(300, 800)
        mic = random.randint(100, 600)
        motion = random.choice([True, False])
        dist = round(random.uniform(2.0, 200.0), 2)
        airq = mq135  # simple map
        sound = mic
    else:
        spi = hw.get('spi')
        humidity, temp = read_dht(pin=4)
        if humidity is None:
            humidity = round(random.uniform(40.0, 70.0), 1)
        if temp is None:
            temp = round(random.uniform(24.0, 32.0), 2)

        mq135 = read_mcp(spi, 0) or 0
        ldr = read_mcp(spi, 1) or 0
        mic = read_mcp(spi, 2) or 0
        motion = read_pir(hw.get('pir_pin', 17))
        dist = read_ultrasonic(hw.get('trig'), hw.get('echo'))
        airq = mq135
        sound = mic

    payload = {
        "temperature": float(temp),
        "humidity": float(humidity),
        "gas_level": float(mq135),
        "light_level": int(ldr),
        "motion_detected": bool(motion),
        "air_quality": float(airq),
        "distance": float(dist) if dist is not None else None,
        "sound_level": float(sound),
        "mq135": float(mq135),
        "ldr": float(ldr),
        "mic": float(mic)
    }

    return payload


def send_loop():
    print(f"Mencoba mengirim data ke {ENDPOINT}...")
    hw = init_hardware()

    try:
        while True:
            payload = build_payload(hw)
            try:
                resp = requests.post(ENDPOINT, json=payload, timeout=5)
                if resp.status_code == 201:
                    print(f"[BERHASIL] Data terkirim: {payload}")
                else:
                    print(f"[GAGAL] Status {resp.status_code} - {resp.text}")
            except requests.exceptions.ConnectionError:
                print("[ERROR] Tidak bisa terhubung ke server. Pastikan Flask sudah jalan dan IP benar.")
            except Exception as e:
                print(f"[ERROR] Saat mengirim: {e}")

            time.sleep(5)
    finally:
        if HAS_RPI:
            GPIO.cleanup()


if __name__ == "__main__":
    send_loop()