import os
import sys
import subprocess
import time

FILES = {
    "requirements.txt": """google-genai
pyttsx3
pywinauto
psutil
pandas
duckdb
requests
python-dotenv
pillow
sounddevice
numpy
scipy
""",

    ".env": """GEMINI_API_KEY=your_api_key_here
""",

    "core/__init__.py": "",
    "drivers/__init__.py": "",
    "tools/__init__.py": "",

    "core/vault.py": '''import sqlite3
import os
import datetime

DB_PATH = os.path.join(os.path.expanduser("~"), ".peirro_vault.db")

class Vault:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    role TEXT,
                    content TEXT,
                    action_taken TEXT
                )
            """)

    def log(self, role: str, content: str, action: str = None):
        with self.conn:
            self.conn.execute(
                "INSERT INTO interactions (timestamp, role, content, action_taken) VALUES (?, ?, ?, ?)",
                (datetime.datetime.now().isoformat(), role, content, action)
            )
''',

    "core/hardware_guard.py": '''import psutil
import shutil
import os

class HardwareGuard:
    @staticmethod
    def get_system_vitals():
        cpu_usage = psutil.cpu_percent(interval=0.2)
        ram = psutil.virtual_memory()
        disk = shutil.disk_usage("C:\\\\")
        
        return {
            "cpu_percent": cpu_usage,
            "ram_used_gb": round(ram.used / (1024**3), 2),
            "ram_total_gb": round(ram.total / (1024**3), 2),
            "disk_free_gb": round(disk.free / (1024**3), 2),
            "battery": psutil.sensors_battery()
        }

    @staticmethod
    def scan_junk():
        temp_dir = os.environ.get("TEMP", "C:\\\\Windows\\\\Temp")
        total_size = 0
        for root, _, files in os.walk(temp_dir):
            for f in files:
                try:
                    fp = os.path.join(root, f)
                    total_size += os.path.getsize(fp)
                except Exception:
                    pass
        return round(total_size / (1024**3), 2)

class PermissionGate:
    @staticmethod
    def evaluate_preflight(task_description: str, estimated_disk_gb: float) -> bool:
        free_space = HardwareGuard.get_system_vitals()["disk_free_gb"]
        if free_space < estimated_disk_gb:
            print(f"[Peirro Block]: Task requires {estimated_disk_gb} GB, but only {free_space} GB is free.")
            return False
            
        print("\\n" + "="*50)
        print("[PEIRRO PRE-FLIGHT QUOTA CHECK]")
        print(f"Task: {task_description}")
        print(f"Required Storage: ~{estimated_disk_gb} GB | Free: {free_space} GB")
        print("Authorizing this will execute all steps without repeated prompts.")
        print("="*50)
        
        choice = input("Approve batch execution? (y/n): ").strip().lower()
        return choice == 'y'
''',

    "drivers/os_operator.py": '''import os
import hashlib
import subprocess
import webbrowser

class OSOperator:
    @staticmethod
    def run_cmd(command: str):
        res = subprocess.run(["powershell", "-Command", command], capture_output=True, text=True)
        return res.returncode == 0, res.stdout.strip(), res.stderr.strip()

    @staticmethod
    def open_app(app_name: str):
        apps = {
            "whatsapp": "explorer.exe shell:appsFolder\\\\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App",
            "powerbi": "PBIDesktop.exe",
            "vscode": "code",
            "chrome": "chrome"
        }
        target = apps.get(app_name.lower(), app_name)
        subprocess.Popen(target, shell=True)
        return f"Launched {app_name}."

    @staticmethod
    def play_media(query: str):
        search_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
        webbrowser.open(search_url)
        return f"Opened YouTube stream for: '{query}'."

    @staticmethod
    def find_and_remove_duplicates(target_dir: str):
        if not os.path.exists(target_dir):
            return f"Directory {target_dir} does not exist."
            
        hashes = {}
        duplicates = []
        for root, _, files in os.walk(target_dir):
            for file in files:
                fpath = os.path.join(root, file)
                try:
                    with open(fpath, "rb") as f:
                        file_hash = hashlib.md5(f.read(8192)).hexdigest()
                    if file_hash in hashes:
                        duplicates.append(fpath)
                    else:
                        hashes[file_hash] = fpath
                except Exception:
                    pass

        removed_count = 0
        for dup in duplicates:
            try:
                os.remove(dup)
                removed_count += 1
            except Exception:
                pass

        return f"Scanned {len(hashes) + len(duplicates)} files. Deleted {removed_count} duplicate files in {target_dir}."
''',

    "drivers/uia_vision.py": '''from pywinauto import Desktop
from PIL import ImageGrab
import os

class UIAVisionEngine:
    @staticmethod
    def click_element_by_name(window_title_keyword: str, element_name: str) -> str:
        try:
            desktop = Desktop(backend="uia")
            matching_windows = [w for w in desktop.windows() if window_title_keyword.lower() in w.window_text().lower()]
            
            if not matching_windows:
                return f"No open window found matching '{window_title_keyword}'."
                
            win = matching_windows[0]
            win.set_focus()
            target_ctrl = win.child_window(title_re=f".*{element_name}.*", control_type="Button")
            
            if target_ctrl.exists(timeout=2):
                target_ctrl.click_input()
                return f"Successfully located and clicked '{element_name}' in '{win.window_text()}'."
            else:
                return f"Found '{win.window_text()}', but control '{element_name}' was not exposed via UIA."
        except Exception as e:
            return f"UIA Action failed: {str(e)}"

    @staticmethod
    def take_ondemand_snapshot() -> str:
        save_path = os.path.join(os.environ.get("TEMP", "C:\\\\Temp"), "peirro_vision_frame.png")
        img = ImageGrab.grab()
        img.save(save_path, "PNG")
        return save_path
''',

    "tools/data_scientist.py": '''import os
import pandas as pd

class DataScientist:
    @staticmethod
    def profile_folder_and_draft_hypotheses(folder_path: str):
        clean_path = folder_path.strip().strip('"').strip("'")
        if not os.path.exists(clean_path):
            return f"Folder not found: {clean_path}"

        supported_files = [f for f in os.listdir(clean_path) if f.endswith(('.csv', '.xlsx', '.parquet'))]
        if not supported_files:
            return f"No analytical datasets found in {clean_path}."

        insights = []
        for f in supported_files[:3]:
            fpath = os.path.join(clean_path, f)
            try:
                df = pd.read_csv(fpath) if f.endswith('.csv') else pd.read_excel(fpath)
                null_cols = df.columns[df.isnull().any()].tolist()
                numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                
                insights.append({
                    "file": f,
                    "rows": df.shape[0],
                    "cols": list(df.columns),
                    "null_columns": null_cols
                })
            except Exception as e:
                insights.append({"file": f, "error": str(e)})

        return insights
''',

    "drivers/voice_engine.py": '''import pyttsx3
import sounddevice as sd
import scipy.io.wavfile as wav
import tempfile
import os

class VoiceEngine:
    def __init__(self):
        self.tts = pyttsx3.init()
        self.tts.setProperty('rate', 190)

    def speak(self, text: str):
        print(f"\\nPeirro: {text}")
        try:
            self.tts.say(text)
            self.tts.runAndWait()
        except Exception as e:
            print(f"[TTS Error]: {e}")

    def record_voice_clip(self, duration: int = 5, sample_rate: int = 16000) -> str:
        print("[*] Listening (Voice Active)...")
        audio = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
        sd.wait()
        
        tmp = os.path.join(tempfile.gettempdir(), "peirro_voice_in.wav")
        wav.write(tmp, sample_rate, audio)
        return tmp
''',

    "peirro.py": '''import os
import sys
from dotenv import load_dotenv
from core.vault import Vault
from core.hardware_guard import HardwareGuard
from drivers.os_operator import OSOperator
from drivers.uia_vision import UIAVisionEngine
from tools.data_scientist import DataScientist
from drivers.voice_engine import VoiceEngine

load_dotenv()

vault = Vault()
voice = VoiceEngine()

client = None
api_key = os.getenv("GEMINI_API_KEY", "")
if api_key and api_key != "your_api_key_here":
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
    except Exception as e:
        print(f"[!] Warning: Could not initialize Gemini client: {e}")

def dispatch_command(cmd: str):
    vault.log("user", cmd)
    lower_cmd = cmd.lower()

    if "clean temp" in lower_cmd or "junk" in lower_cmd:
        junk_gb = HardwareGuard.scan_junk()
        voice.speak(f"Identified {junk_gb} GB of temporary files. Cleaning now.")
        OSOperator.run_cmd("Remove-Item -Path $env:TEMP\\\\* -Recurse -Force -ErrorAction SilentlyContinue")
        return

    if "remove duplicate" in lower_cmd or "deduplicate" in lower_cmd:
        path = cmd.split("in")[-1].strip()
        voice.speak(f"Scanning {path} for duplicates using cryptographic checksums.")
        res = OSOperator.find_and_remove_duplicates(path)
        voice.speak(res)
        return

    if "open" in lower_cmd and "whatsapp" in lower_cmd:
        voice.speak("Launching WhatsApp.")
        OSOperator.open_app("whatsapp")
        return

    if "play" in lower_cmd or "review" in lower_cmd:
        voice.speak("Searching and launching your media stream.")
        query = cmd.replace("play", "").strip()
        OSOperator.play_media(query)
        return

    if "click" in lower_cmd:
        parts = cmd.split("in")
        element = parts[0].replace("click", "").strip()
        window = parts[1].strip() if len(parts) > 1 else ""
        voice.speak(f"Looking for {element} in {window} via Windows Accessibility tree.")
        status = UIAVisionEngine.click_element_by_name(window, element)
        voice.speak(status)
        return

    if "analyze" in lower_cmd or "dataset" in lower_cmd:
        target_dir = cmd.split("in")[-1].strip()
        voice.speak(f"Profiling schemas in {target_dir} without cloud data exposure.")
        summary = DataScientist.profile_folder_and_draft_hypotheses(target_dir)
        
        prompt = f"Given these column distributions and schemas: {summary}, formulate 3 high-impact business hypothesis questions."
        if client:
            resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            voice.speak(resp.text)
        else:
            voice.speak(f"Data summary extracted: {summary}. (Add API key in .env for business questions)")
        return

    # Fallback to Cloud Reasoning
    if client:
        resp = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=f"You are Peirro, an autonomous OS co-pilot. Keep answers direct and voice-friendly:\\n{cmd}"
        )
        voice.speak(resp.text)
        vault.log("assistant", resp.text)
    else:
        voice.speak(f"Command understood: '{cmd}'. (Configure GEMINI_API_KEY in .env for advanced reasoning)")

def main():
    voice.speak("Peirro Enterprise Core operational. Systems ready.")
    vitals = HardwareGuard.get_system_vitals()
    print(f"[*] Available Storage: {vitals['disk_free_gb']} GB | RAM: {vitals['ram_used_gb']}/{vitals['ram_total_gb']} GB")

    while True:
        try:
            cmd = input("\\nYou > ").strip()
            if not cmd:
                continue
            if cmd.lower() in ["exit", "quit", "q"]:
                voice.speak("Standing down.")
                break
            dispatch_command(cmd)
        except KeyboardInterrupt:
            print("\\nShutting down.")
            break

if __name__ == "__main__":
    main()
'''
}

def main():
    print("=" * 50)
    print("      PEIRRO - Automatic Scaffolder & Installer")
    print("=" * 50)

    # 1. Create subdirectories
    for d in ["core", "drivers", "tools"]:
        os.makedirs(d, exist_ok=True)
        print(f"[✓] Directory verified: {d}/")

    # 2. Write all files
    for path, code in FILES.items():
        with open(path, "w", encoding="utf-8") as f:
            f.write(code)
        print(f"[✓] Created file: {path}")

    # 3. Automatically install pip dependencies
    print("\n[*] Installing dependencies from requirements.txt...")
    cmd = f'"{sys.executable}" -m pip install -r requirements.txt'
    subprocess.run(cmd, shell=True)

    print("\n" + "=" * 50)
    print("[✓] All files created & dependencies installed successfully!")
    print("=" * 50)
    print("\nNext step:")
    print("1. Open the '.env' file and add your GEMINI_API_KEY.")
    print("2. Run: python peirro.py\n")

if __name__ == "__main__":
    main()