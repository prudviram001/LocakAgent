import os
import json
import time
from datetime import datetime
from pynput import mouse, keyboard
import pyautogui
import pygetwindow as gw
import cv2
import numpy as np

# --- Configuration ---
MEMORY_DIR = "agent_memory"
LOG_FILE = os.path.join(MEMORY_DIR, "behavior_log.json")
LAST_SAVED_IMG = None # To keep track of the last visually different image

# Create memory folder if it doesn't exist
if not os.path.exists(MEMORY_DIR):
    os.makedirs(MEMORY_DIR)
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, 'w') as f:
        json.dump([], f)

def check_visual_difference(new_img_path, last_img_path, threshold=1.0):
    """Compares two images. Returns True if they are visually different."""
    if not last_img_path or not os.path.exists(last_img_path):
        return True
        
    img1 = cv2.imread(last_img_path)
    img2 = cv2.imread(new_img_path)
    
    if img1 is None or img2 is None:
        return True
        
    # Calculate absolute difference between pixels
    diff = cv2.absdiff(img1, img2)
    non_zero_count = np.count_nonzero(diff)
    total_pixels = img1.size
    change_percentage = (non_zero_count / total_pixels) * 100
    
    # If more than 1% of the screen changed, we consider it a new state
    return change_percentage > threshold

def log_action(action_type, details):
    global LAST_SAVED_IMG
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    temp_screenshot = os.path.join(MEMORY_DIR, f"temp_{timestamp}.png")
    
    # 1. Take a temporary screenshot
    pyautogui.screenshot(temp_screenshot)
    
    # 2. Check if screen actually changed
    is_changed = check_visual_difference(temp_screenshot, LAST_SAVED_IMG)
    
    if is_changed:
        # Screen changed! Keep the new image.
        final_img_name = f"screen_{timestamp}.png"
        final_img_path = os.path.join(MEMORY_DIR, final_img_name)
        os.rename(temp_screenshot, final_img_path)
        LAST_SAVED_IMG = final_img_path
        used_image = final_img_name
        print(f"[+] Screen changed. Saved new image: {used_image}")
    else:
        # Screen didn't change. Discard temp image, use the old one.
        os.remove(temp_screenshot)
        used_image = os.path.basename(LAST_SAVED_IMG)
        print(f"[-] No visual change. Reusing image: {used_image}")

    # 3. Get Active Window Name
    active_window = gw.getActiveWindow()
    window_title = active_window.title if active_window else "Unknown"

    # 4. Save to JSON
    log_entry = {
        "timestamp": timestamp,
        "window": window_title,
        "action": action_type,
        "details": details,
        "screenshot": used_image
    }
    
    with open(LOG_FILE, 'r+') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = []
        data.append(log_entry)
        f.seek(0)
        json.dump(data, f, indent=4)

# --- TRACKERS ---
def on_click(x, y, button, pressed):
    if not pressed: # Log only on mouse release
        log_action("MOUSE_CLICK", {"x": x, "y": y, "button": str(button)})

def on_release(key):
    # Logging key actions (like submitting forms/commands)
    if key in [keyboard.Key.enter, keyboard.Key.tab]:
        log_action("KEY_PRESS", {"key": str(key)})
    
    if key == keyboard.Key.esc:
        print("Stopping Smart Observer...")
        return False 

# --- MAIN ---
if __name__ == "__main__":
    print("Starting Smart Observer... (Press 'Esc' to stop)")
    print(f"Saving data to: {os.path.abspath(MEMORY_DIR)}")
    
    # Listeners run in background threads
    mouse_listener = mouse.Listener(on_click=on_click)
    keyboard_listener = keyboard.Listener(on_release=on_release)
    
    mouse_listener.start()
    keyboard_listener.start()
    
    mouse_listener.join()
    keyboard_listener.join()