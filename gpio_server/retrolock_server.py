import RPi.GPIO as GPIO
from flask import Flask, request, jsonify
import logging
import os
import ssl
from pathlib import Path
import time

# Flask-App erstellen
app = Flask(__name__)

# Logging einrichten
LOG_FILE = "/var/log/retrolock.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger()
logger.addHandler(logging.StreamHandler())  # Ausgabe auf Konsole

# GPIO-Setup
LED_PIN = 17  # GPIO-Pin 17
GPIO.setmode(GPIO.BCM)  # BCM-Nummerierung verwenden
GPIO.setwarnings(False)  # Warnungen unterdrücken
GPIO.setup(LED_PIN, GPIO.OUT, initial=GPIO.HIGH)  # Relais deaktiviert

# Token aus Datei laden
TOKEN_FILE = Path("/etc/retrolock/token")
if not TOKEN_FILE.exists():
    logger.error("Token-Datei fehlt: /etc/retrolock/token")
    raise FileNotFoundError("Token-Datei fehlt: /etc/retrolock/token")
AUTH_TOKEN = TOKEN_FILE.read_text().strip()

# LED-Zustand verfolgen
led_state = False  # False = aus, True = an

@app.route("/gpio", methods=["POST"])
def control_gpio():
    global led_state  # Zugriff auf den globalen LED-Zustand

    # Authentifizierung
    auth_token = request.headers.get("Authorization")
    if auth_token != f"Bearer {AUTH_TOKEN}":
        logger.warning("Ungültiger Token: Zugriff verweigert")
        return jsonify({"error": "Unauthorized"}), 401

    # Daten aus der Anfrage lesen
    data = request.json
    if not data or "state" not in data:
        logger.warning("Ungültige Anfrage erhalten")
        return jsonify({"error": "Invalid request"}), 400

    # Sicherstellen, dass GPIO-Modus gesetzt ist
    GPIO.setmode(GPIO.BCM)

    # LED ein- oder ausschalten basierend auf dem Zustand
    if data["state"] == "on":
        if not led_state:  # LED ist noch aus
            GPIO.output(LED_PIN, GPIO.LOW)
            led_state = True
            logger.info("LED eingeschaltet")
            return jsonify({"message": "LED eingeschaltet"})
        else:
            logger.info("LED war bereits eingeschaltet")
            return jsonify({"message": "LED war bereits eingeschaltet"})

    elif data["state"] == "off":
        if led_state:  # LED ist noch an
            GPIO.output(LED_PIN, GPIO.HIGH)
            led_state = False
            logger.info("LED ausgeschaltet")
            return jsonify({"message": "LED ausgeschaltet"})
        else:
            logger.info("LED war bereits ausgeschaltet")
            return jsonify({"message": "LED war bereits ausgeschaltet"})

    elif data["state"] == "open":
        if not led_state: # LED ist aus 
            GPIO.output(LED_PIN, GPIO.LOW)
            time.sleep(1)
            GPIO.output(LED_PIN, GPIO.HIGH)
            logger.info("Door opened")
            return jsonify({"message": "Door open"})
        else:
            logger.info("Door open failed")
            return jsonify({"message": "Door opener failed"})
    else:
        logger.warning(f"Unbekannter Zustand: {data['state']}")
        return jsonify({"error": "Unknown state"}), 400

@app.route("/status", methods=["GET"])
def status():
    """
    Endpoint, um den aktuellen Status der LED abzufragen.
    """
    # Authentifizierung
    auth_token = request.headers.get("Authorization")
    if auth_token != f"Bearer {AUTH_TOKEN}":
        logger.warning("Ungültiger Token bei Reset: Zugriff verweigert")
        return jsonify({"error": "Unauthorized"}), 401

    state = "on" if led_state else "off"
    logger.info(f"Status abgefragt: {state}")
    return jsonify({"led_state": state})

@app.route("/reset", methods=["POST"])
def reset_gpio():
    """
    Endpoint, um den GPIO zurückzusetzen, ohne den Server zu stoppen.
    """
    # Authentifizierung
    auth_token = request.headers.get("Authorization")
    if auth_token != f"Bearer {AUTH_TOKEN}":
        logger.warning("Ungültiger Token bei Reset: Zugriff verweigert")
        return jsonify({"error": "Unauthorized"}), 401

    # GPIO zurücksetzen und wieder konfigurieren
    GPIO.cleanup()
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LED_PIN, GPIO.OUT)
    global led_state
    led_state = False

    logger.info("GPIO zurückgesetzt und LED ausgeschaltet")
    return jsonify({"message": "GPIO zurückgesetzt und LED ausgeschaltet"})

if __name__ == "__main__":
    # SSL-Zertifikate von Let's Encrypt verwenden
    '''
    CERT_FILE = "/etc/letsencrypt/live/nmzkqrg76pkkdaeb.myfritz.net/fullchain.pem"
    KEY_FILE = "/etc/letsencrypt/live/nmzkqrg76pkkdaeb.myfritz.net/privkey.pem"

    if not Path(CERT_FILE).exists() or not Path(KEY_FILE).exists():
        logger.error("SSL-Zertifikate fehlen. Bitte Let's Encrypt einrichten.")
        raise FileNotFoundError("SSL-Zertifikate fehlen.")

    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
    '''

    logger.info("Webserver gestartet auf Port 5001.")
    app.run(host="127.0.0.1", port=5001) #, ssl_context=ssl_context)

