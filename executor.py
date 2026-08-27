import sqlite3
import pyautogui
import time

DB_NAME = "core_integrator.db"


pyautogui.FAILSAFE = True

def execute_action(command):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Nuvvu icchina text ni DB lo vethukutundi
    search_query = f"%{command}%"
    c.execute("SELECT app_name, context_description, x_coord, y_coord FROM learned_rules WHERE context_description LIKE ?", (search_query,))
    result = c.fetchone()

    if result:
        app, desc, x, y = result
        print(f"\n[*] Memory Match Found!")
        print(f"[*] App: {app}")
        print(f"[*] AI Context: {desc}")
        print(f"[*] Moving mouse to X:{x}, Y:{y}...")
        
        # Mouse ni smooth ga (1 second) ah position ki theeskelli click chestundi
        pyautogui.moveTo(x, y, duration=1.0)
        pyautogui.click()
        print("[+] Action executed successfully! \n")
    else:
        print("\n[-] Sorry bro, nenu inka idi nerchukoledu. First naku training ivvu (Observer + Brain run chey)!\n")
    
    conn.close()

def show_memory():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT app_name, context_description, x_coord, y_coord FROM learned_rules")
    rows = c.fetchall()
    conn.close()
    
    print("\n=======================================")
    print("         🧠 AGENT MEMORY LIST          ")
    print("=======================================")
    if not rows:
        print("[-] Inka em nerchukoledu bro, DB empty ga undi!")
    for idx, row in enumerate(rows, 1):
        print(f"{idx}. [App]: {row[0]}")
        print(f"   [Learned]: {row[1]}  -->  [Coords]: X:{row[2]}, Y:{row[3]}")
        print("-" * 40)
    print("=======================================\n")

if __name__ == "__main__":
    print("=======================================")
    print("   Jarvis Execution Mode is READY!     ")
    print("   (Type 'memory' to see what I know)  ")
    print("=======================================")
    
    while True:
        cmd = input("[You] Em command isthav? (or 'memory' / 'exit'): ").strip()
        if cmd.lower() == 'exit':
            break
        elif cmd.lower() == 'memory':
            show_memory()
        else:
            execute_action(cmd)
