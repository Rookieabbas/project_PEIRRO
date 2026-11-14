import time
import subprocess
import pyautogui
import pyperclip
from drivers.os_operator import OSOperator

class CommsHub:
    @staticmethod
    def send_whatsapp(contact: str, message: str) -> bool:
        """Automates WhatsApp Desktop to deliver messages directly to contacts."""
        try:
            OSOperator.open_app("whatsapp")
            time.sleep(1.2)
            
            # Select search bar
            pyautogui.hotkey('ctrl', 'f')
            time.sleep(0.3)
            
            # Search contact
            pyperclip.copy(contact)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.7)
            pyautogui.press('enter')
            time.sleep(0.5)

            # Paste and send message
            pyperclip.copy(message)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.2)
            pyautogui.press('enter')
            return True
        except Exception as e:
            print(f"[!] Comms Hub Error: {e}")
            return False

    @staticmethod
    def get_latest_notifications() -> list:
        """Polls Windows Action Center / PowerShell diagnostic events for notification interception."""
        ps_cmd = (
            'powershell -Command "'
            'Get-WinEvent -ListProvider Microsoft-Windows-PushNotifications-Platform '
            '-ErrorAction SilentlyContinue | Select-Object -First 3"'
        )
        try:
            out = subprocess.check_output(ps_cmd, shell=True, text=True).strip()
            if out:
                return [out]
        except Exception:
            pass
        return []