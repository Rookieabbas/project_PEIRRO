import os
import shutil
import psutil
import subprocess
from pathlib import Path

class HardwareGuard:
    @staticmethod
    def get_system_vitals() -> dict:
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('C:\\')
        return {
            "ram_used_gb": round((mem.total - mem.available) / (1024**3), 2),
            "ram_total_gb": round(mem.total / (1024**3), 2),
            "ram_percent": mem.percent,
            "disk_free_gb": round(disk.free / (1024**3), 2),
            "disk_total_gb": round(disk.total / (1024**3), 2),
            "disk_percent": disk.percent
        }

    @staticmethod
    def check_thermal_status() -> dict:
        """Inspects CPU package thermal states via Windows WMI/CIM ACPI thermal zones."""
        ps_cmd = (
            'powershell -Command "'
            'Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature '
            '-ErrorAction SilentlyContinue | Select-Object -ExpandProperty CurrentTemperature"'
        )
        try:
            out = subprocess.check_output(ps_cmd, shell=True, text=True).strip()
            if out:
                # WMI returns deci-Kelvin: (temp_k / 10) - 273.15 = Celsius
                deci_kelvin = float(out.splitlines()[0])
                celsius = round((deci_kelvin / 10.0) - 273.15, 1)
                is_throttling = celsius >= 89.0
                return {"temp_c": celsius, "throttling": is_throttling}
        except Exception:
            pass

        # Fallback to CPU load estimation if thermal sensor is OEM-locked
        cpu_load = psutil.cpu_percent(interval=0.5)
        return {"temp_c": None, "cpu_load": cpu_load, "throttling": cpu_load > 92.0}

    @staticmethod
    def check_power_state() -> dict:
        """Monitors AC vs Battery state and flags power-hungry tasks."""
        battery = psutil.sensors_battery()
        if not battery:
            return {"has_battery": False, "ac_plugged": True}

        heavy_procs = []
        if not battery.power_plugged:
            for proc in psutil.process_iter(['name', 'cpu_percent', 'memory_info']):
                try:
                    name = proc.info['name'].lower()
                    if any(target in name for target in ['node', 'chrome', 'docker', 'code', 'python']):
                        if proc.info['cpu_percent'] and proc.info['cpu_percent'] > 12.0:
                            heavy_procs.append(proc.info['name'])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        return {
            "has_battery": True,
            "ac_plugged": battery.power_plugged,
            "percent": battery.percent,
            "secs_left": battery.secsleft,
            "heavy_processes": list(set(heavy_procs))
        }

    @staticmethod
    def enable_battery_saver_plan():
        """Switches Windows power scheme to Power Saver."""
        cmd = "powercfg /setactive a1841308-3541-4fab-bc81-f71556f20b4a"
        subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    @staticmethod
    def scan_dev_junk() -> dict:
        """Identifies recoverable space across npm caches, Docker dangling layers, temp files, and pip cache."""
        recoverable_bytes = 0
        details = {}

        # 1. Windows Temp
        temp_dir = Path(os.getenv("TEMP", "C:\\Windows\\Temp"))
        temp_bytes = sum(f.stat().st_size for f in temp_dir.glob('**/*') if f.is_file())
        recoverable_bytes += temp_bytes
        details["windows_temp_gb"] = round(temp_bytes / (1024**3), 2)

        # 2. Pip Cache
        pip_cache = Path(os.getenv("LOCALAPPDATA", "")) / "pip" / "cache"
        if pip_cache.exists():
            p_bytes = sum(f.stat().st_size for f in pip_cache.glob('**/*') if f.is_file())
            recoverable_bytes += p_bytes
            details["pip_cache_gb"] = round(p_bytes / (1024**3), 2)

        # 3. Npm Cache
        npm_cache = Path(os.getenv("APPDATA", "")) / "npm-cache"
        if npm_cache.exists():
            n_bytes = sum(f.stat().st_size for f in npm_cache.glob('**/*') if f.is_file())
            recoverable_bytes += n_bytes
            details["npm_cache_gb"] = round(n_bytes / (1024**3), 2)

        details["total_recoverable_gb"] = round(recoverable_bytes / (1024**3), 2)
        return details

    @staticmethod
    def execute_deep_vacuum():
        """Cleans temporary files, pip cache, and dangling Docker layers."""
        # Clean Temp
        subprocess.run(
            'powershell -Command "Remove-Item -Path $env:TEMP\\* -Recurse -Force -ErrorAction SilentlyContinue"',
            shell=True
        )
        # Clean pip cache
        subprocess.run("pip cache purge", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Clean Docker dangling containers & volumes if installed
        subprocess.run("docker system prune -f", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)