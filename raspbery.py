import time
import random
import requests
import platform
import argparse
import sys

# --- KONFIGURASI ---
# Pastikan IP ini sesuai dengan IP laptop/server Flask kamu
SERVER_IP = "192.168.1.162"
PORT = "5000"
ENDPOINT = f"http://{SERVER_IP}:{PORT}/api/data"

# DHT data pin (BCM numbering). Physical pin 11 == BCM 17
DHT_PIN = 4

# GPIO / hardware libs will be optional so this script can run on laptop
HAS_RPI = False
try:
    import RPi.GPIO as GPIO
    import spidev
    HAS_RPI = True
except Exception:
    # Running on laptop or missing libs -> we'll use simulated values
    HAS_RPI = False

# DHT backend detection: prefer legacy Adafruit_Python_DHT, fallback to adafruit-circuitpython-dht
USE_ADAFRUIT_DHT_LEGACY = False
USE_ADAFRUIT_DHT_NEW = False
dht_sensor = None
try:
    # try legacy first (may be installed via setup.py)
    import Adafruit_DHT as _Adafruit_DHT
    Adafruit_DHT = _Adafruit_DHT
    USE_ADAFRUIT_DHT_LEGACY = True
except Exception:
    try:
        # try CircuitPython driver
        import board
        import adafruit_dht
        USE_ADAFRUIT_DHT_NEW = True
    except Exception:
        USE_ADAFRUIT_DHT_NEW = False
        USE_ADAFRUIT_DHT_LEGACY = False


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
    # Disable noisy warnings from repeated runs
    GPIO.setwarnings(False)
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

    # LED actuator pins (change to your wiring)
    LED_RED = 5
    LED_BLUE = 6
    LED_YELLOW = 13
    LED_WHITE = 19
    hw['led_pins'] = {
        'red': LED_RED,
        'blue': LED_BLUE,
        'yellow': LED_YELLOW,
        'white': LED_WHITE,
    }

    # setup LED pins
    GPIO.setup(LED_RED, GPIO.OUT)
    GPIO.setup(LED_BLUE, GPIO.OUT)
    GPIO.setup(LED_YELLOW, GPIO.OUT)
    GPIO.setup(LED_WHITE, GPIO.OUT)

    # motion counter used to detect "too much movement"
    hw['motion_counter'] = 0

    return hw


    # NOTE: unreachable while return above for non-RPi; on RPi this function continues


def read_mcp(spi, channel=0):
    # channel 0-7
    if spi is None:
        return None
    adc = spi.xfer2([1, (8 + channel) << 4, 0])
    data = ((adc[1] & 3) << 8) + adc[2]
    return data


def check_sensors():
    """Lakukan pengecekan singkat terhadap sensor dan pin.
    Jika tidak dijalankan di Raspberry Pi (HAS_RPI False) akan tampilkan pesan simulasi.
    """
    hw = init_hardware()

    if not HAS_RPI:
        print("Tidak menemukan environment Raspberry Pi / GPIO library. Menjalankan pengecekan simulasi.")
        print("- DHT22: simulasi OK")
        print("- MCP3008: simulasi OK")
        print("- PIR: simulasi OK")
        return

    print("Hardware ditemukan. Memulai pengecekan sensor/pin...")

    # Cek DHT
    humidity, temp = read_dht(pin=DHT_PIN)
    if temp is None and humidity is None:
        print("DHT22: GAGAL (tidak ada respon)")
    else:
        print(f"DHT22: OK - temperature={temp}, humidity={humidity}")

    # Cek MCP3008 channel 0..2
    spi = hw.get('spi')
    if spi is None:
        print("MCP3008: spi tidak terinisialisasi (cek wiring SPI)")
    else:
        for ch in range(3):
            val = read_mcp(spi, ch)
            print(f"MCP3008 ch{ch}: {val if val is not None else 'NO RESPONSE'}")

    # Cek PIR
    pir_pin = hw.get('pir_pin')
    pir = read_pir(pir_pin)
    if pir is None:
        print(f"PIR (pin {pir_pin}): GAGAL baca")
    else:
        state = 'HIGH' if pir else 'LOW'
        print(f"PIR (pin {pir_pin}): OK - current state={state}")

    # Cek ultrasonic
    trig = hw.get('trig')
    echo = hw.get('echo')
    if trig is None or echo is None:
        print("Ultrasonic: pin trig/echo belum terkonfigurasi")
    else:
        dist = read_ultrasonic(trig, echo)
        print(f"Ultrasonic: distance={dist if dist is not None else 'READ ERROR'} cm")

    # Toggle LED singkat (bila terhubung)
    pins = hw.get('led_pins', {})
    if pins:
        print("Toggle LED singkat untuk verifikasi output pins")
        for name, pin in pins.items():
            try:
                print(f" - {name} (pin {pin}): ON -> OFF")
                GPIO.output(pin, GPIO.HIGH)
                time.sleep(0.3)
                GPIO.output(pin, GPIO.LOW)
            except Exception as e:
                print(f" - {name} (pin {pin}): ERROR toggling -> {e}")
    else:
        print("LED pins: tidak ada konfigurasi pin LED")

    print("Pengecekan selesai. Jangan lupa cek wiring jika ada item gagal.")


def read_dht(pin=None):
    if pin is None:
        pin = DHT_PIN
    # returns (humidity, temperature)
    global dht_sensor

    # Try legacy Adafruit_Python_DHT if available
    if 'Adafruit_DHT' in globals():
        try:
            humidity, temperature = Adafruit_DHT.read_retry(Adafruit_DHT.DHT22, pin)
            return humidity, temperature
        except Exception as e:
            print(f"[DHT DEBUG] legacy read error: {e}")

    # Try CircuitPython driver if available
    try:
        if 'adafruit_dht' not in globals() or 'board' not in globals():
            # try importing on demand
            import board as _board
            import adafruit_dht as _adafruit_dht
            globals()['board'] = _board
            globals()['adafruit_dht'] = _adafruit_dht

        # create sensor instance and try a few times; use use_pulseio=False on Linux
        for attempt in range(3):
            try:
                # recreate sensor if previous instance exists but raised errors
                if dht_sensor is None:
                    try:
                        dht_sensor = adafruit_dht.DHT22(getattr(board, f"D{pin}"), use_pulseio=False)
                    except Exception:
                        dht_sensor = adafruit_dht.DHT22(board.D4, use_pulseio=False)

                humidity = dht_sensor.humidity
                temperature = dht_sensor.temperature
                if humidity is None or temperature is None:
                    raise RuntimeError('no reading')
                return humidity, temperature
            except Exception as e:
                # attempt to clean up sensor instance before retrying
                try:
                    if dht_sensor is not None:
                        dht_sensor.exit()
                except Exception:
                    pass
                dht_sensor = None
                print(f"[DHT DEBUG] circuitpython attempt {attempt+1} error: {e}")
                time.sleep(2)
        return None, None
    except Exception as e:
        print(f"[DHT DEBUG] import/driver error: {e}")
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
        # return None to indicate read failure (distinct from False)
        return None


def build_payload(hw):
    # thresholds and normal ranges
    TEMP_THRESHOLD = 30.0
    MOTION_THRESHOLD = 3  # number of motion events within window to trigger
    HUMI_MIN = 40.0
    HUMI_MAX = 60.0
    LDR_NIGHT_THRESHOLD = 400

    if not HAS_RPI:
        # Simulasi dinonaktifkan — skrip harus dijalankan di Raspberry Pi
        # (baris simulasi sebelumnya dikomentari agar tidak mengirim data random)
        # temp = round(random.uniform(24.0, 32.0), 2)
        # humidity = round(random.uniform(30.0, 70.0), 1)
        # ldr = random.randint(200, 800)
        # motion = random.choice([True, False])
        # dht_ok = True
        # ldr_ok = True
        # pir_ok = True
        print("Error: Simulasi random dinonaktifkan. Jalankan skrip ini di Raspberry Pi dengan sensor terhubung.")
        sys.exit(1)
    else:
        spi = hw.get('spi')
        humidity, temp = read_dht(pin=DHT_PIN)

        # DHT read: do NOT fallback to random values — mark as failed if None
        dht_ok = not (humidity is None or temp is None)

        # Read LDR on MCP channel 1 (or use analog/digital wiring)
        ldr_val = read_mcp(spi, 1)
        ldr_ok = ldr_val is not None
        ldr = int(ldr_val) if ldr_ok else None

        motion = read_pir(hw.get('pir_pin', 17))
        pir_ok = motion is not None

    # update motion counter in hw (simple sliding counter)
    motion_counter = hw.get('motion_counter', 0)
    if motion:
        motion_counter += 1
    else:
        motion_counter = max(0, motion_counter - 1)
    hw['motion_counter'] = motion_counter

    # compute LED states according to new rules only if required sensors ok
    if dht_ok:
        led_red = True if temp > TEMP_THRESHOLD else False
        led_yellow = True if (humidity < HUMI_MIN or humidity > HUMI_MAX) else False
    else:
        led_red = False
        led_yellow = False

    led_blue = True if motion_counter >= MOTION_THRESHOLD else False
    if ldr is not None:
        led_white = True if int(ldr) < LDR_NIGHT_THRESHOLD else False
    else:
        led_white = False

    # if running on RPi, set LED outputs
    if HAS_RPI:
        pins = hw.get('led_pins', {})
        GPIO.output(pins['red'], GPIO.HIGH if led_red else GPIO.LOW)
        GPIO.output(pins['blue'], GPIO.HIGH if led_blue else GPIO.LOW)
        GPIO.output(pins['yellow'], GPIO.HIGH if led_yellow else GPIO.LOW)
        GPIO.output(pins['white'], GPIO.HIGH if led_white else GPIO.LOW)

    payload = {
        "temperature": float(temp) if dht_ok else None,
        "humidity": float(humidity) if dht_ok else None,
        "light_level": int(ldr) if ldr is not None else None,
        "ldr": float(ldr) if ldr is not None else None,
        "motion_detected": bool(motion) if motion is not None else None,
        "motion_count": int(hw.get('motion_counter', 0)),
        # send actuator states so backend + frontend can display
        "led_red": bool(led_red),
        "led_blue": bool(led_blue),
        "led_yellow": bool(led_yellow),
        "led_white": bool(led_white),
        # diagnostic flags (helpful when sensor read fails)
        "dht_ok": bool(dht_ok),
        "ldr_ok": bool(ldr_ok),
        "pir_ok": bool(pir_ok),
    }

    return payload


def send_loop():
    print(f"Mencoba mengirim data ke {ENDPOINT}...")
    hw = init_hardware()

    try:
        while True:
            payload = build_payload(hw)
            # Always print payload locally so sensor values (or diagnostics) are visible in terminal
            print(f"[PAYLOAD] {payload}")

            # Jika sensor inti gagal (DHT/LDR/PIR), jangan kirim data — tunggu sampai sensor tersedia
            core_missing = None in (payload.get('temperature'), payload.get('humidity'), payload.get('light_level'), payload.get('motion_detected'))
            if core_missing or not (payload.get('dht_ok') and payload.get('ldr_ok') and payload.get('pir_ok')):
                reasons = []
                if not payload.get('dht_ok'):
                    reasons.append('DHT')
                if not payload.get('ldr_ok'):
                    reasons.append('LDR')
                if not payload.get('pir_ok'):
                    reasons.append('PIR')
                print(f"[SKIP] Tidak mengirim: sensor bermasalah -> {', '.join(reasons)}. Cek wiring/instalasi.")
                time.sleep(5)
                continue
            try:
                resp = requests.post(ENDPOINT, json=payload, timeout=5)
                if resp.status_code == 201:
                    print(f"[BERHASIL] Data terkirim: {resp.status_code} {resp.text}")
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
    parser = argparse.ArgumentParser(description='Raspberry Pi sensor loop and utilities')
    parser.add_argument('--check', action='store_true', help='Run sensor/pin checks and exit')
    args = parser.parse_args()

    # Selalu jalankan pengecekan sensor/pin sebelum mulai mengirim data.
    check_sensors()

    # Jika user hanya ingin mengecek, keluar setelah pengecekan.
    if not args.check:
        send_loop()