import os
import json
import time
import sqlite3
import base64
import glob
from llama_cpp import Llama
from llama_cpp.llama_chat_format import Llava15ChatHandler

# --- 1. CONFIGURATION ---
MEMORY_DIR = "agent_memory"
LOG_FILE = os.path.join(MEMORY_DIR, "behavior_log.json")
DB_NAME = "core_integrator.db"

# Nuvvu download chesina Qwen Models Paths
MAIN_MODEL = "models/qwen2-vl-2b-instruct-q4_k_m.gguf"
VISION_PROJECTOR = "models/mmproj-qwen2-vl-2b-instruct-f16.gguf"

# Enni images vachaka AI process cheyali? (Testing kosam 3 peduthunna)
IMAGE_THRESHOLD = 3  

# --- 2. LOAD QWEN-VL AI ---
print("[*] Loading Qwen2-VL Brain... This might take a minute...")
chat_handler = Llava15ChatHandler(clip_model_path=VISION_PROJECTOR)
llm = Llama(
    model_path=MAIN_MODEL,
    chat_handler=chat_handler,
    n_ctx=4096, # Memory for understanding the image
    verbose=False
)
print("[+] AI Brain Loaded Successfully!")

# --- 3. DATABASE SETUP ---
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

# --- 4. IMAGE TO TEXT CONVERTER ---
def image_to_base64(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

# --- 5. CORE PROCESSING ENGINE ---
def process_batch():
    images = glob.glob(os.path.join(MEMORY_DIR, "*.png"))
    
    if len(images) < IMAGE_THRESHOLD:
        print(f"[{time.strftime('%H:%M:%S')}] Waiting for images... ({len(images)}/{IMAGE_THRESHOLD})")
        return

    print(f"\n[*] Threshold reached! Processing {len(images)} screenshots...")
    conn = init_db()
    c = conn.cursor()
    
    try:
        with open(LOG_FILE, 'r') as f:
            logs = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        logs = []

    logs_to_keep = []

    for log in logs:
        img_path = os.path.join(MEMORY_DIR, log['screenshot'])
        if not os.path.exists(img_path):
            logs_to_keep.append(log) 
            continue

        base64_image = image_to_base64(img_path)
        app_name = log['window']
        x = log['details'].get('x', 0)
        y = log['details'].get('y', 0)
        timestamp = log['timestamp']
        
        # PROMPT to Qwen-VL
        prompt = f"Look at this screenshot of '{app_name}'. The user clicked at X: {x}, Y: {y}. Briefly describe what UI element (button/menu/field) is at that location."
        
        try:
            print(f"-> Asking AI about {log['screenshot']}...")
            response = llm.create_chat_completion(
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                        ]
                    }
                ]
            )
            ai_description = response['choices'][0]['message']['content'].strip()
            print(f"   [AI Learned]: {ai_description}")

            # Save to SQLite Database
            c.execute("INSERT INTO learned_rules (app_name, context_description, action_taken, x_coord, y_coord, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                      (app_name, ai_description, log['action'], x, y, timestamp))
            
            # Delete image to save space
            os.remove(img_path)
            
        except Exception as e:
            print(f"[!] Error processing image: {e}")
            logs_to_keep.append(log)

    conn.commit()
    conn.close()
    
    with open(LOG_FILE, 'w') as f:
        json.dump(logs_to_keep, f, indent=4)
        
    print("[+] Batch complete! Data saved and images deleted.\n")

# --- 6. MAIN LOOP ---
if __name__ == "__main__":
    print("Continuous Brain Processor started... Press Ctrl+C to stop.")
    while True:
        process_batch()
        time.sleep(10) # Check every 10 seconds
