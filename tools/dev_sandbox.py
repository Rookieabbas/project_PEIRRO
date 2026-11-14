import os
import sys
import subprocess
from pathlib import Path

class DevSandbox:
    @staticmethod
    def scaffold_virtualenv(target_dir: str = ".venv") -> str:
        """Builds an isolated virtual environment to prevent global dependency pollution."""
        venv_path = Path(target_dir)
        if venv_path.exists():
            return f"Virtual environment '{target_dir}' already exists."

        subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
        return f"Created clean virtual environment in {target_dir}. Ready for pip installations."

    @staticmethod
    def get_git_diff() -> str:
        """Captures local unstaged and staged git changes."""
        try:
            diff = subprocess.check_output("git diff", shell=True, text=True).strip()
            if not diff:
                diff = subprocess.check_output("git diff --staged", shell=True, text=True).strip()
            return diff[:3000] if diff else "No tracked changes detected."
        except Exception:
            return "Not a valid git repository or Git CLI not detected."

    @staticmethod
    def auto_commit_and_push(branch: str = "main", pr: bool = False) -> str:
        """Stages all changes, creates a semantic commit message, and optionally pushes a PR via GitHub CLI."""
        try:
            diff = DevSandbox.get_git_diff()
            commit_msg = "feat: automated workspace synchronization via Peirro co-pilot"
            if "fix" in diff.lower() or "error" in diff.lower():
                commit_msg = "fix: resolve execution discrepancies and handle runtime boundary cases"

            subprocess.run("git add .", shell=True, check=True)
            subprocess.run(f'git commit -m "{commit_msg}"', shell=True, check=True)
            
            if pr:
                subprocess.run(f"gh pr create --title \"{commit_msg}\" --body \"Automated PR from Peirro.\"", shell=True)
                return f"Committed: '{commit_msg}' and created PR via GitHub CLI."

            return f"Successfully staged and committed: '{commit_msg}'."
        except Exception as e:
            return f"Git automation error: {e}"

    @staticmethod
    def execute_and_debug(script_path: str) -> dict:
        """Executes a target script, captures stderr on failure, parses stack trace, and prepares patch analysis."""
        proc = subprocess.run(
            [sys.executable, script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if proc.returncode == 0:
            return {"status": "success", "stdout": proc.stdout}

        # Failure captured
        stderr = proc.stderr
        last_line = stderr.strip().splitlines()[-1] if stderr else "Unknown Runtime Exception"
        return {
            "status": "failed",
            "error_type": last_line,
            "full_stderr": stderr[:2000],
            "script": script_path
        }