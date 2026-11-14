import os
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
            "whatsapp": "explorer.exe shell:appsFolder\\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App",
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
