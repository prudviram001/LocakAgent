import os
import json
import time
import sqlite3
import base64
import glob
import requests
from PIL import Image
import io

# --- 1. CONFIGURATION ---
MEMORY_DIR = "agent_memory"
LOG_FILE = os.path.join(MEMORY_DIR, "behavior_log.json")
DB_NAME = "core_integrator.db"
IMAGE_THRESHOLD = 3

# Llama.cpp Server URL
SERVER_URL = "http://127.0.0.1:8080/v1/chat/completions"

# --- DB & Base64 functions same as before ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS learned_rules
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  app_name TEXT,
                  context_description TEXT,
                  action_taken TEXT,
                  x_coord INTEGER,
                  y_coord INTEGER,
                  timestamp TEXT)''')
    conn.commit()
    return conn

# --- 4. SMART IMAGE COMPRESSOR ---
def image_to_base64(image_path, max_size=(512, 512)):
    with Image.open(image_path) as img:
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Save to memory buffer as JPEG
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')


def process_batch():
    images = glob.glob(os.path.join(MEMORY_DIR, "*.png"))
    
    if len(images) < IMAGE_THRESHOLD:
        print(f"[{time.strftime('%H:%M:%S')}] Waiting for images... ({len(images)}/{IMAGE_THRESHOLD})")
        return

    print(f"\n[*] Threshold reached! Processing up to 3 screenshots...")
    conn = init_db()
    c = conn.cursor()
    
    try:
        with open(LOG_FILE, 'r') as f:
            logs = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        logs = []

    # Process only max 3 logs to avoid lag
    MAX_PROCESS = 3
    logs_to_process = logs[:MAX_PROCESS]
    logs_to_keep = logs[MAX_PROCESS:]

    for log in logs_to_process:
        img_path = os.path.join(MEMORY_DIR, log['screenshot'])
        if not os.path.exists(img_path):
            logs_to_keep.append(log) 
            continue

        base64_image = image_to_base64(img_path)
        app_name = log['window']
        x = log['details'].get('x', 0)
        y = log['details'].get('y', 0)
        timestamp = log['timestamp']
        
        prompt = f"Look at this screenshot of '{app_name}'. The user clicked at X: {x}, Y: {y}. Briefly describe what UI element (button/menu/field) is at that location."
        
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ]
        }

        try:
            print(f"-> Sending {log['screenshot']} to Llama Server...")
            
            # Sending request to the server
            response = requests.post(SERVER_URL, json=payload)
            response.raise_for_status() # Check for HTTP errors
            
            ai_description = response.json()['choices'][0]['message']['content'].strip()
            print(f"   [AI Learned]: {ai_description}")

            # Save to SQLite Database
            c.execute("INSERT INTO learned_rules (app_name, context_description, action_taken, x_coord, y_coord, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                      (app_name, ai_description, log['action'], x, y, timestamp))
            
            # Delete image to save space
            os.remove(img_path)
            
        except Exception as e:
            print(f"[!] Error processing image: {e}")
            # If server fails, keep the log for later
            logs_to_keep.append(log)

    conn.commit()
    conn.close()
    
    with open(LOG_FILE, 'w') as f:
        json.dump(logs_to_keep, f, indent=4)
        
    print("[+] Batch complete! Data saved.\n")

if __name__ == "__main__":
    print("Continuous Brain Processor started... Press Ctrl+C to stop.")
    while True:
        process_batch()
        time.sleep(5) # Check every 5 seconds
