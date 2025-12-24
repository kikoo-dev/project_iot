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
        # Simulasi jika tidak ada hardware
        temp = round(random.uniform(24.0, 32.0), 2)
        humidity = round(random.uniform(30.0, 70.0), 1)
        ldr = random.randint(200, 800)
        motion = random.choice([True, False])
        # simulated sensors considered OK
        dht_ok = True
        ldr_ok = True
        pir_ok = True
    else:
        spi = hw.get('spi')
        humidity, temp = read_dht(pin=4)
        if humidity is None:
            humidity = round(random.uniform(40.0, 70.0), 1)
        if temp is None:
            temp = round(random.uniform(24.0, 32.0), 2)

        # Read LDR on MCP channel 1 (or use analog/digital wiring)
        ldr_val = read_mcp(spi, 1)
        ldr_ok = ldr_val is not None
        ldr = ldr_val or 0
        motion = read_pir(hw.get('pir_pin', 17))
        pir_ok = motion is not None
        # DHT read
        dht_ok = not (humidity is None and temp is None)

    # update motion counter in hw (simple sliding counter)
    motion_counter = hw.get('motion_counter', 0)
    if motion:
        motion_counter += 1
    else:
        motion_counter = max(0, motion_counter - 1)
    hw['motion_counter'] = motion_counter

    # compute LED states according to new rules
    led_red = True if temp > TEMP_THRESHOLD else False
    led_blue = True if motion_counter >= MOTION_THRESHOLD else False
    led_yellow = True if (humidity < HUMI_MIN or humidity > HUMI_MAX) else False
    led_white = True if int(ldr) < LDR_NIGHT_THRESHOLD else False

    # if running on RPi, set LED outputs
    if HAS_RPI:
        pins = hw.get('led_pins', {})
        GPIO.output(pins['red'], GPIO.HIGH if led_red else GPIO.LOW)
        GPIO.output(pins['blue'], GPIO.HIGH if led_blue else GPIO.LOW)
        GPIO.output(pins['yellow'], GPIO.HIGH if led_yellow else GPIO.LOW)
        GPIO.output(pins['white'], GPIO.HIGH if led_white else GPIO.LOW)

    payload = {
        "temperature": float(temp),
        "humidity": float(humidity),
        "light_level": int(ldr),
        "ldr": float(ldr),
        "motion_detected": bool(motion),
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
            # Always print payload locally so sensor values (or fallbacks) are visible in terminal
            print(f"[PAYLOAD] {payload}")
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
    send_loop()