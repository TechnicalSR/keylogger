import os
from flask import Flask, request
import datetime
from cryptography.fernet import Fernet, InvalidToken

KEY_FILE = "encryption.key"
DECRYPTED_LOGS_FILE = "decrypted_logs.txt"
FAILED_DECRYPTION_LOG = "failed_decryption_attempts.log"

app = Flask(__name__)

fernet = None

def load_key_and_init_fernet():
    global fernet
    
    if not os.path.exists(KEY_FILE):
        print(f"[FATAL ERROR] Encryption key '{KEY_FILE}' not found!")
        print("The server cannot start without the key to decrypt incoming logs.")
        print("Please place the key file in the same directory as this script.")
        exit()

    with open(KEY_FILE, "rb") as f:
        key = f.read()
    
    fernet = Fernet(key)
    print(f"[INFO] Encryption key '{KEY_FILE}' loaded successfully. Server is ready to decrypt.")


@app.route('/log', methods=['POST'])
def receive_and_decrypt_log():
    global fernet

    encrypted_data = request.get_data()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"\n[{timestamp}] Received an incoming log of {len(encrypted_data)} bytes...")

    try:
        decrypted_data = fernet.decrypt(encrypted_data)
        decrypted_string = decrypted_data.decode()
        
        print(f"[{timestamp}] SUCCESS: Log decrypted!")
        print("--- BEGIN DECRYPTED LOG ---")
        print(decrypted_string)
        print("--- END DECRYPTED LOG ---\n")

        with open(DECRYPTED_LOGS_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n--- Log Received and Decrypted at {timestamp} ---\n")
            f.write(decrypted_string)

    except InvalidToken:
        print(f"[{timestamp}] FAILED: Received data could not be decrypted. It might be corrupted or sent with the wrong key.")
        with open(FAILED_DECRYPTION_LOG, "ab") as f:
            f.write(f"\n--- FAILED DECRYPTION at {timestamp} ---\n".encode())
            f.write(encrypted_data)
    
    except Exception as e:
        print(f"[{timestamp}] An unexpected error occurred: {e}")

    return "Log received", 200


if __name__ == '__main__':
    load_key_and_init_fernet()
    
    print("\nStarting simulated exfiltration server with live decryption.")
    print(f"Listening on http://127.0.0.1:5000/log")
    print(f"Decrypted logs will be saved to '{DECRYPTED_LOGS_FILE}'")
    print("Press CTRL+C to stop the server.")
    
    app.run(host='127.0.0.1', port=5000)
