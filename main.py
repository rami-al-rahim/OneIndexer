import tkinter as tk
from tkinter import filedialog, scrolledtext
import json
import os

from cryptography.fernet import Fernet
import keyring

from google.oauth2 import service_account
from googleapiclient.discovery import build

# ===== CONFIG =====
SERVICE_NAME = "IndexingApp"
KEY_NAME = "encryption_key"
ENC_FILE = "credentials.enc"

SCOPES = ["https://www.googleapis.com/auth/indexing"]


# ===== KEYCHAIN =====
def get_or_create_key():
    key = keyring.get_password(SERVICE_NAME, KEY_NAME)

    if key is None:
        key = Fernet.generate_key().decode()
        keyring.set_password(SERVICE_NAME, KEY_NAME, key)

    return key.encode()


# ===== ENCRYPTION =====
def encrypt_and_store(json_data):
    key = get_or_create_key()
    f = Fernet(key)

    encrypted = f.encrypt(json.dumps(json_data).encode())

    with open(ENC_FILE, "wb") as file:
        file.write(encrypted)


def load_and_decrypt():
    key = get_or_create_key()
    f = Fernet(key)

    with open(ENC_FILE, "rb") as file:
        decrypted = f.decrypt(file.read())

    return json.loads(decrypted.decode())


# ===== GOOGLE SERVICE =====
def get_service():
    creds_json = load_and_decrypt()

    credentials = service_account.Credentials.from_service_account_info(
        creds_json, scopes=SCOPES
    )

    return build("indexing", "v3", credentials=credentials)


# ===== ACTIONS =====
def upload_credentials():
    file_path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
    if not file_path:
        return

    with open(file_path, "r") as f:
        data = json.load(f)

    encrypt_and_store(data)
    result_box.insert(tk.END, "✅ Credentials securely stored (encrypted + keychain)\n")


def submit_urls():
    if not os.path.exists(ENC_FILE):
        result_box.insert(tk.END, "❌ Upload credentials first\n")
        return

    service = get_service()
    urls = input_box.get("1.0", tk.END).strip().split("\n")

    for url in urls:
        if not url.strip():
            continue

        try:
            service.urlNotifications().publish(
                body={"url": url.strip(), "type": "URL_UPDATED"}
            ).execute()

            result_box.insert(tk.END, f"✅ {url}\n")

        except Exception as e:
            result_box.insert(tk.END, f"❌ {url} → {str(e)}\n")


# ===== GUI =====
root = tk.Tk()
root.title("Secure Google Indexing Tool (Keychain)")
root.geometry("700x500")

tk.Button(root, text="Upload Service Account", command=upload_credentials).pack(pady=5)

tk.Label(root, text="Enter URLs:").pack()

input_box = scrolledtext.ScrolledText(root, height=10)
input_box.pack(fill=tk.BOTH, padx=10, pady=5)

tk.Button(root, text="Submit URLs", command=submit_urls).pack(pady=10)

tk.Label(root, text="Results:").pack()

result_box = scrolledtext.ScrolledText(root, height=12)
result_box.pack(fill=tk.BOTH, padx=10, pady=5)

root.mainloop()