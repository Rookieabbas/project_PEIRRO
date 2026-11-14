import os
import sys
import io
import time
import math
import queue
import subprocess
import threading
import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav
import keyboard
from dotenv import load_dotenv

# Modular System Engines
from core.vault import Vault
from core.hardware_guard import HardwareGuard
from core.briefing_engine import BriefingEngine
from core.evolution_engine import EvolutionEngine
from drivers.os_operator import OSOperator
from drivers.uia_vision import UIAVisionEngine
from drivers.comms_hub import CommsHub
from tools.data_scientist import DataScientist
from tools.dev_sandbox import DevSandbox
from drivers.voice_engine import VoiceEngine

load_dotenv()

vault = Vault()
voice = VoiceEngine()

# Groq Whisper Client
groq_client = None
groq_api_key = os.getenv("GROQ_API_KEY", "")
if groq_api_key and groq_api_key != "your_groq_key_here":
    try:
        from groq import Groq
        groq_client = Groq(api_key=groq_api_key)
    except Exception as e:
        print(f"[!] Warning: Could not initialize Groq client: {e}")

# Gemini Client
client = None
api_key = os.getenv("GEMINI_API_KEY", "")
if api_key and api_key != "your_api_key_here":
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
    except Exception as e:
        print(f"[!] Warning: Could not initialize Gemini client: {e}")

PRIMARY_CLOUD_MODEL = "gemini-1.5-flash"
HOTKEY_LISTEN = "ctrl+i"
HOTKEY_PAUSE = "ctrl+space"

is_listening_active = False
abort_requested = False

# ----------------- Thread-Safe Dynamic Island Capsule HUD -----------------
class DynamicIslandHUD:
    COLORS = {
        "red": "#ff3344",       # Listening
        "yellow": "#ffcc00",    # Processing / Thinking
        "green": "#00e676",     # Confirmed / Executing
        "abort": "#ff0055"      # Halted / Paused
    }

    def __init__(self):
        self.cmd_queue = queue.Queue()
        self.root = None
        self.canvas = None
        self.fade_job = None
        self.anim_job = None
        self.current_theme = "green"
        self.t = 0.0
        self.bar_count = 6
        self.w = 200
        self.h = 36
        self.is_running = False

    def start(self):
        """Runs the Tkinter HUD in a dedicated background thread."""
        if not self.is_running:
            self.is_running = True
            t = threading.Thread(target=self._run_hud_thread, daemon=True)
            t.start()

    def _run_hud_thread(self):
        import tkinter as tk
        try:
            self.root = tk.Tk()
            self.root.overrideredirect(True)
            self.root.attributes("-topmost", True)
            self.root.attributes("-alpha", 0.0)

            trans_color = "#010101"
            self.root.configure(bg=trans_color)
            self.root.wm_attributes("-transparentcolor", trans_color)

            sw = self.root.winfo_screenwidth()
            x = (sw - self.w) // 2
            y = 12
            self.root.geometry(f"{self.w}x{self.h}+{x}+{y}")

            self.canvas = tk.Canvas(self.root, width=self.w, height=self.h, bg=trans_color, highlightthickness=0)
            self.canvas.pack(fill="both", expand=True)

            self._process_queue()
            self._render_frame()
            self.root.mainloop()
        except Exception as e:
            print(f"[!] HUD Thread Error: {e}")

    def _draw_capsule(self, x1, y1, x2, y2, fill, outline=""):
        if not self.canvas:
            return
        r = (y2 - y1) / 2
        self.canvas.create_arc(x1, y1, x1 + 2 * r, y2, start=90, extent=180, fill=fill, outline=outline)
        self.canvas.create_arc(x2 - 2 * r, y1, x2, y2, start=270, extent=180, fill=fill, outline=outline)
        self.canvas.create_rectangle(x1 + r, y1, x2 - r, y2, fill=fill, outline=outline)

    def _render_frame(self):
        if not self.canvas or not self.root:
            return
        self.canvas.delete("all")
        active_color = self.COLORS.get(self.current_theme, self.COLORS["green"])
        self._draw_capsule(2, 2, self.w - 2, self.h - 2, fill="#0a0c10", outline="#1c2128")

        center_y = self.h // 2
        bar_w = 4
        spacing = 8
        total_width = self.bar_count * bar_w + (self.bar_count - 1) * spacing
        start_x = (self.w - total_width) // 2

        for i in range(self.bar_count):
            phase = i * 0.75
            mod = math.sin(self.t + phase) * 7
            bar_h = max(4, 12 + mod)
            bx = start_x + i * (bar_w + spacing)
            self.canvas.create_rectangle(
                bx, center_y - (bar_h / 2), bx + bar_w, center_y + (bar_h / 2),
                fill=active_color, outline="", width=0
            )

        self.t += 0.14
        try:
            self.anim_job = self.root.after(16, self._render_frame)
        except Exception:
            pass

    def _process_queue(self):
        try:
            while not self.cmd_queue.empty():
                action, payload = self.cmd_queue.get_nowait()
                if action == "state":
                    if self.fade_job:
                        self.root.after_cancel(self.fade_job)
                        self.fade_job = None
                    self.current_theme = payload
                    self.root.attributes("-alpha", 0.98)
                elif action == "fade":
                    self._schedule_fade(payload)
        except Exception:
            pass

        if self.root:
            self.root.after(40, self._process_queue)

    def _schedule_fade(self, delay_ms):
        def _start_fade():
            try:
                alpha = self.root.attributes("-alpha")
                if alpha > 0.05:
                    self.root.attributes("-alpha", alpha - 0.12)
                    self.fade_job = self.root.after(20, _start_fade)
                else:
                    self.root.attributes("-alpha", 0.0)
                    self.fade_job = None
            except Exception:
                pass

        if self.fade_job:
            self.root.after_cancel(self.fade_job)
        self.fade_job = self.root.after(delay_ms, _start_fade)

    def set_state(self, theme: str):
        self.cmd_queue.put(("state", theme))

    def fade_out(self, delay_ms: int = 1500):
        self.cmd_queue.put(("fade", delay_ms))

hud = DynamicIslandHUD()

# ----------- Zero-PyAudio Voice Activity Detection (sounddevice + Groq Whisper) -----------
def listen_to_mic_fast() -> str:
    """Records directly via sounddevice (no PyAudio needed) with dynamic silence detection."""
    global abort_requested
    hud.set_state("red")

    sample_rate = 16000
    chunk_duration = 0.1  # 100ms blocks
    chunk_samples = int(sample_rate * chunk_duration)
    silence_limit = 0.8   # seconds of silence before finishing
    max_duration = 10.0   # max phrase duration
    silence_threshold = 450  # dynamic RMS threshold

    frames = []
    silent_time = 0.0
    speech_started = False
    total_time = 0.0

    try:
        with sd.InputStream(samplerate=sample_rate, channels=1, dtype='int16') as stream:
            while total_time < max_duration:
                if abort_requested:
                    hud.fade_out(200)
                    return ""

                chunk, _ = stream.read(chunk_samples)
                frames.append(chunk)
                total_time += chunk_duration

                # Calculate volume energy (RMS)
                data_sq = chunk.astype(np.float64) ** 2
                rms = np.sqrt(np.mean(data_sq))

                if rms > silence_threshold:
                    speech_started = True
                    silent_time = 0.0
                elif speech_started:
                    silent_time += chunk_duration
                    if silent_time >= silence_limit:
                        break
                elif total_time > 4.0:
                    # No speech detected within 4s timeout
                    break

        if not speech_started or abort_requested:
            hud.fade_out(600)
            return ""

        hud.set_state("yellow")
        audio_data = np.concatenate(frames, axis=0)

        # Convert raw numpy array to in-memory WAV
        wav_buffer = io.BytesIO()
        wav.write(wav_buffer, sample_rate, audio_data)
        wav_bytes = wav_buffer.getvalue()

        # Send to Groq Whisper Large V3
        if groq_client:
            try:
                audio_file = ("input.wav", wav_bytes, "audio/wav")
                transcription = groq_client.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-large-v3",
                    response_format="text",
                    temperature=0.0
                )
                if transcription and isinstance(transcription, str):
                    return transcription.strip()
            except Exception as e:
                print(f"[!] Groq Whisper error: {e}")

        return ""

    except Exception as e:
        print(f"[!] Mic/Recognition Error: {e}")
        hud.fade_out(600)
        return ""

def ask_local_brain(context: str, prompt: str) -> str:
    try:
        import ollama
        res = ollama.chat(
            model="llama3.2:3b",
            messages=[
                {"role": "system", "content": context},
                {"role": "user", "content": prompt}
            ]
        )
        msg = res.get("message", {}).get("content", "")
        if msg:
            return msg.strip()
    except Exception as err:
        print(f"[!] Local brain unreachable: {err}")
    return "All processing cores are currently unreachable."

def ask_brain(prompt: str) -> str:
    global abort_requested
    if abort_requested:
        return ""

    hud.set_state("yellow")
    vitals = HardwareGuard.get_system_vitals()
    evolution_context = EvolutionEngine.get_evolution_context()

    context = (
        f"Live System State -> Free Storage: {vitals['disk_free_gb']} GB, "
        f"RAM Used: {vitals['ram_used_gb']}/{vitals['ram_total_gb']} GB.\n"
        f"{evolution_context}\n"
        f"You are Peirro, an elite autonomous Windows co-pilot. Keep voice responses direct and under 2 sentences."
    )

    if client:
        result = [None]
        def _cloud_call():
            try:
                resp = client.models.generate_content(
                    model=PRIMARY_CLOUD_MODEL,
                    contents=f"{context}\n\nUser Question: {prompt}"
                )
                if resp and resp.text:
                    result[0] = resp.text.strip()
            except Exception:
                pass

        t = threading.Thread(target=_cloud_call, daemon=True)
        t.start()
        t.join(timeout=4.5)
        if result[0]:
            return result[0]

    return ask_local_brain(context, prompt)

def proactive_hardware_guard():
    """Background Watchdog: Proactive thermal and battery discharge monitoring."""
    while True:
        try:
            status = HardwareGuard.check_thermal_status()
            if status.get("throttling"):
                hud.set_state("abort")
                voice.speak("CPU thermal threshold reached. Pausing non-critical background jobs.")
                time.sleep(30)

            p = HardwareGuard.check_power_state()
            if p.get("has_battery") and not p.get("ac_plugged") and p.get("heavy_processes"):
                procs = ", ".join(p["heavy_processes"][:2])
                hud.set_state("yellow")
                voice.speak(f"Running on battery. High discharge detected from {procs}. Switching to power saver.")
                HardwareGuard.enable_battery_saver_plan()
                time.sleep(60)
        except Exception:
            pass
        time.sleep(10)

def open_windows_app(app_target: str) -> str:
    """Instant native Windows application launcher with zero CMD/shell hanging."""
    app_lower = app_target.lower().strip()
    
    try:
        if "whatsapp" in app_lower:
            os.startfile("whatsapp:")
            return "Launching WhatsApp Desktop."
        elif "chrome" in app_lower:
            subprocess.Popen("cmd /c start chrome", shell=True)
            return "Launching Google Chrome."
        elif "code" in app_lower or "vscode" in app_lower:
            subprocess.Popen("cmd /c code", shell=True)
            return "Launching Visual Studio Code."
        elif "notepad" in app_lower:
            subprocess.Popen("notepad", shell=True)
            return "Opening Notepad."
        else:
            subprocess.Popen(f"cmd /c start {app_target}", shell=True)
            return f"Opening {app_target}."
    except Exception as e:
        print(f"[!] App Launch Warning: {e}")
        try:
            subprocess.Popen(f"cmd /c start {app_target}", shell=True)
            return f"Opening {app_target}."
        except Exception:
            return f"Could not launch {app_target}."

def close_windows_app(target: str) -> str:
    """Bulletproof process termination handling UWP store apps and standard Win32."""
    t_clean = target.lower().strip()
    for w in ["close", "closing", "kill", "terminate", "band kar"]:
        t_clean = t_clean.replace(w, "").strip()

    if "whatsapp" in t_clean:
        subprocess.run('taskkill /F /IM WhatsApp.exe /T', shell=True, capture_output=True)
        subprocess.run('powershell -Command "Get-Process -Name *WhatsApp* | Stop-Process -Force -ErrorAction SilentlyContinue"', shell=True)
        return "Terminated WhatsApp."
    else:
        subprocess.run(f'powershell -Command "Get-Process -Name *{t_clean}* | Stop-Process -Force -ErrorAction SilentlyContinue"', shell=True)
        return f"Terminated {t_clean}."

def create_claude_agent_project(agent_name: str, raw_query: str) -> str:
    """Intelligently generates agent instructions and creates an executable runner."""
    clean_folder_name = agent_name.lower().replace(" ", "_")
    workspace_dir = os.path.join("workspace", "agents", clean_folder_name)
    os.makedirs(workspace_dir, exist_ok=True)

    system_synthesis_prompt = (
        f"You are a master AI architect. Write a concise, professional system prompt for an autonomous AI agent named '{agent_name}'.\n"
        f"The user's goal: '{raw_query}'.\n"
        f"Include:\n"
        f"- Role and identity\n"
        f"- Core operational directives (numbered)\n"
        f"- Required output formatting standards\n"
        f"Output ONLY the text of the system prompt (no markdown wrapper ticks, no chat preamble)."
    )

    system_prompt_content = None
    if client:
        try:
            resp = client.models.generate_content(
                model=PRIMARY_CLOUD_MODEL,
                contents=system_synthesis_prompt
            )
            if resp and resp.text:
                system_prompt_content = resp.text.strip()
        except Exception:
            pass

    if not system_prompt_content:
        system_prompt_content = (
            f"# {agent_name} - System Instructions\n\n"
            f"You are {agent_name}, an elite AI resume and career strategist.\n\n"
            f"## Core Directives:\n"
            f"1. Transform raw career history into high-impact, ATS-optimized resume sections.\n"
            f"2. Use strong action verbs and quantify achievements with metrics (e.g., %, $, scale).\n"
            f"3. Maintain strict standard formatting (Summary, Experience, Skills, Education).\n"
            f"4. Eliminate generic buzzwords and ensure concise, executive-level phrasing."
        )

    agent_code = f'''"""
{agent_name} - Universal Standalone Agent Runner
"""
import os
from dotenv import load_dotenv

load_dotenv()

with open("system_prompt.txt", "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()

def run_agent(user_query: str) -> str:
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    if anthropic_key:
        try:
            from anthropic import Anthropic
            c = Anthropic(api_key=anthropic_key)
            resp = c.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                messages=[{{"role": "user", "content": user_query}}]
            )
            return resp.content[0].text
        except Exception as e:
            pass

    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if gemini_key:
        try:
            from google import genai
            g_client = genai.Client(api_key=gemini_key)
            resp = g_client.models.generate_content(
                model="{PRIMARY_CLOUD_MODEL}",
                contents=f"{{SYSTEM_PROMPT}}\\n\\nUser Task: {{user_query}}"
            )
            if resp and resp.text:
                return resp.text.strip()
        except Exception as e:
            pass

    try:
        import ollama
        res = ollama.chat(
            model="llama3.2:3b",
            messages=[
                {{"role": "system", "content": SYSTEM_PROMPT}},
                {{"role": "user", "content": user_query}}
            ]
        )
        return res.get("message", {{}}).get("content", "").strip()
    except Exception as e:
        return f"Error: No AI engine was able to respond: {{e}}"

if __name__ == "__main__":
    print("=" * 50)
    print("  {agent_name} ACTIVE")
    print("=" * 50)
    while True:
        try:
            query = input("\\nAsk {agent_name} (or 'exit') > ").strip()
            if not query or query.lower() in ["exit", "quit", "q"]:
                break
            print("\\nGenerating response...")
            output = run_agent(query)
            print("-" * 50)
            print(output)
            print("-" * 50)
        except (KeyboardInterrupt, EOFError):
            break
'''

    with open(os.path.join(workspace_dir, "system_prompt.txt"), "w", encoding="utf-8") as f:
        f.write(system_prompt_content)

    with open(os.path.join(workspace_dir, "agent.py"), "w", encoding="utf-8") as f:
        f.write(agent_code)

    return f"Created agent '{agent_name}' in '{workspace_dir}' with synthesized prompt and fallback-ready runner."

def dispatch_command(cmd: str) -> str:
    global abort_requested
    if abort_requested:
        return ""

    vault.log("user", cmd)
    lower = cmd.lower().strip()

    # 1. Vernacular & Slang Engine Adaptation
    if any(k in lower for k in ["learn hindi", "learn slang", "hinglish", "speak in hindi", "hindi me baat kar"]):
        hud.set_state("green")
        msg = EvolutionEngine.set_vernacular_mode(True)
        voice.speak(msg)
        return msg

    # 2. Run / Launch Sub-Agent
    if lower.startswith("run ") or lower.startswith("start agent "):
        target_agent = lower.replace("start agent ", "").replace("run ", "").strip().replace(" ", "_")
        agent_dir = os.path.join("workspace", "agents", target_agent)
        agent_script = os.path.join(agent_dir, "agent.py")

        if os.path.exists(agent_script):
            hud.set_state("green")
            voice.speak(f"Launching {target_agent} agent in a dedicated console.")
            subprocess.Popen(f'start cmd /k "cd /d {os.path.abspath(agent_dir)} && python agent.py"', shell=True)
            return f"Agent {target_agent} launched."
        else:
            voice.speak(f"Agent {target_agent} not found in workspace.")
            return f"No agent named {target_agent} located."

    # 3. Concrete Agent Builder
    if "create" in lower and "agent" in lower:
        hud.set_state("yellow")
        agent_name = "ResumeGenie" if "resume" in lower else "CustomAgent"
        res = create_claude_agent_project(agent_name, cmd)
        hud.set_state("green")
        voice.speak(f"Agent {agent_name} has been built and saved in your workspace folder.")
        return res

    # 4. Autonomous Background Skill Synthesis
    if "learn" in lower or "master" in lower:
        target_topic = cmd
        for trigger in ["learn how to use", "learn to use", "learn how to", "learn", "master"]:
            if trigger in lower:
                target_topic = cmd[lower.find(trigger) + len(trigger):].strip()
                break

        hud.set_state("yellow")
        msg = f"Initiating autonomous research on {target_topic}. Synthesizing playbooks in background."
        voice.speak(msg)
        EvolutionEngine.start_background_research(target_topic, client, voice)
        hud.set_state("green")
        return msg

    # 5. System Briefings & Telemetry (Pillar 6)
    briefing_triggers = [
        "morning brief", "morning report", "system status", "status",
        "how are you doing", "how you doing", "how u doing",
        "how is the system", "how's the system", "what's the status"
    ]
    if any(k in lower for k in briefing_triggers):
        hud.set_state("green")
        brief = BriefingEngine.generate_morning_brief()
        voice.speak(brief)
        return brief

    if "evening debrief" in lower or "save workspace" in lower:
        hud.set_state("green")
        res = BriefingEngine.save_evening_snapshot()
        voice.speak(res)
        return res

    if "restore workspace" in lower:
        hud.set_state("green")
        res = BriefingEngine.restore_workspace()
        voice.speak(res)
        return res

    # 6. Storage & Developer Junk Purge (Pillar 1)
    if any(k in lower for k in ["clean junk", "vacuum", "scan disk", "clean temp", "saaf kar"]):
        hud.set_state("yellow")
        stats = HardwareGuard.scan_dev_junk()
        HardwareGuard.execute_deep_vacuum()
        hud.set_state("green")
        msg = f"Purged {stats['total_recoverable_gb']} GB of developer caches and temporary directories."
        voice.speak(msg)
        return msg

    # 7. Native Windows Application Closer
    if any(k in lower for k in ["close", "closing", "kill", "terminate", "band kar"]):
        hud.set_state("green")
        res = close_windows_app(lower)
        voice.speak(res)
        return res

    # 8. Native Windows Application Opener
    if lower.startswith("open ") or lower.startswith("opening ") or "launch " in lower:
        app_target = lower.replace("opening ", "").replace("open ", "").replace("launch ", "").strip()
        hud.set_state("green")
        res = open_windows_app(app_target)
        voice.speak(res)
        return res

    # 9. Comms & Messaging Hub (Pillar 5)
    if any(k in lower for k in ["send message", "message to", "text to", "msg to", "send hi", "bol de"]):
        contact = "Fazal"
        msg = "Hi"
        
        if "to " in lower:
            after_to = lower.split("to ", 1)[1].strip()
            if "that " in after_to:
                contact_part, msg_part = after_to.split("that ", 1)
                contact = contact_part.strip().capitalize()
                msg = msg_part.strip()
            else:
                contact = after_to.strip().capitalize()
                before_to = lower.split("to ")[0]
                for prefix in ["send ", "message ", "text ", "msg "]:
                    if prefix in before_to:
                        msg = before_to.replace(prefix, "").strip()
                        break

        hud.set_state("yellow")
        voice.speak(f"Transmitting to {contact}.")
        success = CommsHub.send_whatsapp(contact, msg)
        hud.set_state("green" if success else "abort")
        res = f"Dispatched message to {contact}." if success else "Failed to dispatch message."
        voice.speak(res)
        return res

    # 10. Data Science & DAX Synthesis (Pillar 3)
    if any(k in lower for k in ["calculate", "dax", "formula"]):
        hud.set_state("yellow")
        dax = DataScientist.generate_dax_measure(cmd)
        hud.set_state("green")
        voice.speak("Validated DAX expression copied directly to your clipboard.")
        return dax

    if "profile data" in lower or "analyze dataset" in lower:
        hud.set_state("yellow")
        target = cmd.split("in")[-1].strip() if "in" in cmd else "."
        csv_files = [f for f in os.listdir(target) if f.endswith(".csv")]
        if csv_files:
            profile = DataScientist.profile_dataset(os.path.join(target, csv_files[0]))
            hud.set_state("green")
            msg = f"Inspected {profile['total_rows']} rows. Anomaly statistics ready."
            voice.speak(msg)
            return msg
        else:
            msg = f"No CSV datasets located in {target}."
            voice.speak(msg)
            return msg

    # 11. Dev Sandbox & Git Automation (Pillar 4)
    if any(k in lower for k in ["scaffold", "create venv", "new project"]):
        hud.set_state("yellow")
        res = DevSandbox.scaffold_virtualenv()
        hud.set_state("green")
        voice.speak(res)
        return res

    if "commit" in lower or "git push" in lower:
        hud.set_state("yellow")
        res = DevSandbox.auto_commit_and_push(pr=("pr" in lower))
        hud.set_state("green")
        voice.speak(res)
        return res

    # 12. Fallback Cloud / Local Intelligence
    ans = ask_brain(cmd)
    if not abort_requested and ans:
        hud.set_state("green")
        voice.speak(ans)
        vault.log("assistant", ans)
    return ans

def trigger_voice():
    global is_listening_active, abort_requested
    if is_listening_active:
        return
    abort_requested = False
    is_listening_active = True
    try:
        text = listen_to_mic_fast()
        if text and not abort_requested:
            print(f"\n[Heard]: {text}")
            dispatch_command(text)
    except Exception as err:
        print(f"[!] Error during voice dispatch: {err}")
    finally:
        is_listening_active = False
        hud.fade_out(1500)

def trigger_abort():
    global abort_requested, is_listening_active
    print("\n[!] Ctrl+Space Triggered: Task Halted.")
    abort_requested = True
    is_listening_active = False
    try:
        voice.engine.stop()
    except Exception:
        pass
    hud.set_state("abort")
    hud.fade_out(800)

def main():
    hud.start()
    threading.Thread(target=proactive_hardware_guard, daemon=True).start()

    keyboard.add_hotkey(HOTKEY_LISTEN, lambda: threading.Thread(target=trigger_voice, daemon=True).start())
    keyboard.add_hotkey(HOTKEY_PAUSE, trigger_abort)

    threading.Thread(target=lambda: voice.speak("Peirro co-pilot online. Systems synchronized."), daemon=True).start()

    hud.set_state("green")
    hud.fade_out(2000)

    print("\n" + "=" * 50)
    print("  PEIRRO CO-PILOT ONLINE (Groq Whisper Powered)")
    print("  - Speak: Press [Ctrl + I] anywhere")
    print("  - Stop:  Press [Ctrl + Space]")
    print("  - Type:  Type any command below and hit Enter")
    print("=" * 50 + "\n")

    while True:
        try:
            user_input = input("Peirro > ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit", "q"]:
                print("[Peirro]: Shutting down.")
                break
            
            dispatch_command(user_input)
            hud.fade_out(1500)
        except (KeyboardInterrupt, EOFError):
            print("\n[Peirro]: Session ended.")
            break

if __name__ == "__main__":
    main()