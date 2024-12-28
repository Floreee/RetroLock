import RPi.GPIO as GPIO
from flask import Flask, request, jsonify
import logging
import os
import ssl
from pathlib import Path
import time

# Create Flask-App
app = Flask(__name__)

# Create Logging
LOG_FILE = "/var/log/retrolock.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger()
logger.addHandler(logging.StreamHandler())

# GPIO-Setup
DOOR_PIN = 17  # GPIO-Pin 17
GPIO.setmode(GPIO.BCM)  # Use BCM-Numbering
GPIO.setwarnings(False)  # Suppress warnings 
GPIO.setup(DOOR_PIN, GPIO.OUT, initial=GPIO.HIGH)  # Relais off

# Load Token from File
TOKEN_FILE = Path("/etc/retrolock/token.txt")
if not TOKEN_FILE.exists():
    logger.error("Token file missing: /etc/retrolock/token.txt")
    raise FileNotFoundError("Token File missing: /etc/retrolock/token.txt")
AUTH_TOKEN = TOKEN_FILE.read_text().strip()

# DOOR state
door_state = False  # False = closed, True = open

@app.route("/gpio", methods=["POST"])
def control_gpio():
    global door_state 

    # Authorization
    auth_token = request.headers.get("Authorization")
    if auth_token != f"Bearer {AUTH_TOKEN}":
        logger.warning("Invalid Token: Permission denied")
        return jsonify({"error": "Unauthorized"}), 401

    # Parse request
    data = request.json
    if not data or "state" not in data:
        logger.warning("Invalid request")
        return jsonify({"error": "Invalid request"}), 400

    # Ensure correct GPIO mode
    GPIO.setmode(GPIO.BCM)

    # Open, close door 
    if data["state"] == "on":
        if not door_state: 
            GPIO.output(DOOR_PIN, GPIO.LOW)
            door_state = True
            logger.info("Door open continuously")
            return jsonify({"message": "Door open continuously"})
        else:
            logger.info("Door already open")
            return jsonify({"message": "Door already open"})

    elif data["state"] == "off":
        if door_state: 
            GPIO.output(DOOR_PIN, GPIO.HIGH)
            door_state = False
            logger.info("Door closed")
            return jsonify({"message": "Door closed"})
        else:
            logger.info("Door already closed")
            return jsonify({"message": "Door already closed"})

    elif data["state"] == "open":
        if not door_state:
            GPIO.output(DOOR_PIN, GPIO.LOW)
            time.sleep(1)
            GPIO.output(DOOR_PIN, GPIO.HIGH)
            logger.info("Door opened")
            return jsonify({"message": "Door opened"})
        else:
            logger.info("Door open failed")
            return jsonify({"message": "Door open failed"})
    else:
        logger.warning(f"Unknown state: {data['state']}")
        return jsonify({"error": "Unknown state"}), 400

@app.route("/status", methods=["GET"])
def status():
    state = "on" if door_state else "off"
    logger.info(f"Door state: {state}")
    return jsonify({"Door state": state})

@app.route("/reset", methods=["POST"])
def reset_gpio():
    # Authorization
    auth_token = request.headers.get("Authorization")
    if auth_token != f"Bearer {AUTH_TOKEN}":
        logger.warning("Invalid Token: Permission denied")
        return jsonify({"error": "Unauthorized"}), 401

    # GPIO reset
    GPIO.cleanup()
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(DOOR_PIN, GPIO.OUT)
    global door_state
    door_state = False

    logger.info("GPIO resetted")
    return jsonify({"message": "GPIO resetted"})

if __name__ == "__main__":
    # SSL-Certificates from Let's Encrypt
    CERT_FILE = "/etc/letsencrypt/live/mydomain/fullchain.pem"
    KEY_FILE = "/etc/letsencrypt/live/mydomain/privkey.pem"

    if not Path(CERT_FILE).exists() or not Path(KEY_FILE).exists():
        logger.error("SSL-Certificates missing. Configure Let's Encrypt.")
        raise FileNotFoundError("SSL-Certificates missing.")

    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)

    logger.info("RetroLock Server started on 5000 SSL enabled.")
    app.run(host="0.0.0.0", port=5000, ssl_context=ssl_context)
