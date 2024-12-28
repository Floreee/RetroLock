# RetroLock

**RetroLock** is the smart solution to make your existing door smart and open it using your phone. No need to replace keys or install expensive hardware! The only requirement is that your door has an opener, typically controlled via an intercom system or similar.

## Features

- **Convenient Access:** Open your door effortlessly using your smartphone.
- **Key Management:**
  - Create time-limited keys for temporary access.
  - Share keys securely with other users of the app.
  - Full control over all keys using an admin key.
- **Secure and Flexible:** Grant temporary access to guests, friends, or delivery services.

## Technical Overview

RetroLock is a lightweight server script that runs on a Raspberry Pi. Upon successful authentication, the server controls a GPIO pin, which is connected to a relay. The relay then activates the control line of the door opener.

### Server Code Functionality

The RetroLock server is written in Python and uses Flask to create a RESTful API. Key functionalities include:

1. **GPIO Control:**
   - Door state (`on`, `off`, `open`) is controlled via GPIO pin 17.
   - The `open` state triggers a momentary activation (1 second) to simulate a button press.

2. **Authentication:**
   - Authentication is performed using a token stored in `/etc/retrolock/token.txt`.
   - Requests must include a valid `Authorization` header in the format `Bearer <TOKEN>`.

3. **SSL Support:**
   - SSL certificates are loaded from `/etc/letsencrypt/live/mydomain/` to enable secure communication.

4. **Logging:**
   - Logs are written to `/var/log/retrolock.log` for monitoring and debugging.

### API Endpoints

- **POST /gpio**: Control the GPIO pin state
  - **Headers:** `Authorization: Bearer <TOKEN>`
  - **Body:** `{ "state": "on" | "off" | "open" }`
  - **Responses:**
    - 200: Success
    - 400: Invalid request
    - 401: Unauthorized

- **GET /status**: Get the current door state
  - **Headers:** `Authorization: Bearer <TOKEN>`
  - **Responses:**
    - 200: `{ "Door state": "on" | "off" }`

- **POST /reset**: Reset GPIO configuration
  - **Headers:** `Authorization: Bearer <TOKEN>`
  - **Responses:**
    - 200: `{ "message": "GPIO resetted" }`

An example server log entry looks like:
```log
2024-12-28 12:34:56 [INFO] Door opened
```

### Hardware Setup
Below is a schematic representation of the hardware integration:

- **Raspberry Pi** → **GPIO Pin 17** → **Relay Module** → **Door Opener Control Line**

![RetroLock Schema](schema_placeholder.png) *(Replace this placeholder with an actual image or diagram)*

## Installation Guide

### Prerequisites

#### Hardware Requirements:
- Raspberry Pi
- Relay Module
- Wires to connect the Raspberry Pi to the relay and the door opener

#### Software Requirements:
- Python 3
- Flask Library (`pip install flask`)
- RPi.GPIO Library (`pip install RPi.GPIO`)
- SSL Certificates (configured using [Let's Encrypt](https://letsencrypt.org/))

### Step-by-Step Installation:

1. **Install Required Libraries:**
   ```bash
   pip install flask RPi.GPIO
   ```

2. **Create Necessary Directories:**
   ```bash
   sudo mkdir -p /var/log
   sudo touch /var/log/retrolock.log
   sudo mkdir -p /etc/retrolock
   sudo touch /etc/retrolock/token.txt
   ```

3. **Adjust Permissions:**
   ```bash
   sudo chmod 640 /var/log/retrolock.log
   sudo chmod 750 /etc/retrolock
   sudo chmod 640 /etc/retrolock/token.txt
   sudo chown pi:pi /var/log/retrolock.log
   sudo chown -R pi:pi /etc/retrolock
   ```

4. **Set Up SSL Certificates:**
   Ensure SSL certificates are located in `/etc/letsencrypt/live/mydomain/`.
   - Use the following command to generate certificates:
     ```bash
     sudo certbot certonly --standalone -d mydomain
     ```

5. **Set Up RetroLock as a System Service (Recommended):**
   - Create a service file named `retrolock.service` in `/etc/systemd/system/`:
     ```ini
     [Unit]
     Description=RetroLock Service
     After=network.target

     [Service]
     ExecStart=/usr/bin/python3 /path/to/retrolock_server.py
     WorkingDirectory=/path/to/
     Restart=always
     User=pi

     [Install]
     WantedBy=multi-user.target
     ```
   - Enable and start the service:
     ```bash
     sudo systemctl enable retrolock.service
     sudo systemctl start retrolock.service
     ```

6. **Set Up Security Measures:**
   - Ensure the token file at `/etc/retrolock/token.txt` is secure and only accessible to the necessary processes.
   - Regularly rotate the token for added security.

### Testing the Setup
After installation, test the functionality by sending authenticated requests to the server. Verify that the relay is triggered correctly and activates the door opener.

## Security Considerations

- **Authentication Tokens:** The initial token file (`/etc/retrolock/token.txt`) is used for server authentication. Keep this file secure and update it periodically.
- **Log Monitoring:** Regularly check the log file at `/var/log/retrolock.log` for unauthorized access attempts or errors.
- **Network Security:** Use a secure network and consider restricting access to trusted IP addresses.

## Planned Features

- **Android App:** A dedicated app for easier control and key management.
- **Advanced Security:** Features like IP whitelisting, two-factor authentication, and detailed activity logs.
- **Cloud Integration:** Optional cloud support for remote management and notifications.

## License
This project is licensed under the GNU General Public License v3.0. For more details, refer to the `LICENSE` file.

## Contributing
Contributions are welcome! If you have ideas or improvements, feel free to submit a pull request or open an issue in the GitHub repository.

---
**Build your own RetroLock system and experience the convenience of a smart door today!**
