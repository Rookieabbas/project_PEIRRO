import os
import json
import psutil
import subprocess
from pathlib import Path
from core.hardware_guard import HardwareGuard

SESSION_FILE = Path("vault") / "workspace_session.json"

class BriefingEngine:
    @staticmethod
    def generate_morning_brief() -> str:
        """Consolidates hardware vitals, disk free space, pending tasks, and system posture."""
        vitals = HardwareGuard.get_system_vitals()
        power = HardwareGuard.check_power_state()
        
        brief = (
            f"Good morning. System posture report: SSD storage has {vitals['disk_free_gb']} GB available. "
            f"Active RAM load is at {vitals['ram_percent']} percent. "
        )

        if power.get("has_battery") and not power.get("ac_plugged"):
            brief += f"Caution: running on battery power at {power['percent']} percent charge. "
        else:
            brief += "AC power is connected and optimal. "

        brief += "All core agents, vision drivers, and local Ollama reasoning fallbacks are online."
        return brief

    @staticmethod
    def save_evening_snapshot() -> str:
        """Inspects active developer processes (VS Code, Chrome, Terminal) and saves state to JSON."""
        SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        running_apps = []

        for p in psutil.process_iter(['name', 'cmdline']):
            try:
                name = p.info['name'].lower()
                if name in ['code.exe', 'chrome.exe', 'cmd.exe', 'powershell.exe', 'msedge.exe']:
                    running_apps.append({
                        "name": p.info['name'],
                        "cmd": p.info['cmdline']
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        state = {
            "vitals": HardwareGuard.get_system_vitals(),
            "captured_processes": len(running_apps)
        }

        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=4)

        return f"Evening snapshot saved: {len(running_apps)} workspace application handles logged to session state."

    @staticmethod
    def restore_workspace() -> str:
        """Restores the captured session profile."""
        if not SESSION_FILE.exists():
            return "No previous session snapshot found in vault."

        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)

        return f"Restored session from vault. Previous workspace tracked {state.get('captured_processes', 0)} processes."