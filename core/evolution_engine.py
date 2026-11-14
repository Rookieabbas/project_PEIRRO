import os
import json
import threading

class EvolutionEngine:
    VAULT_DIR = "vault"
    PLAYBOOK_DIR = os.path.join(VAULT_DIR, "playbooks")
    SETTINGS_FILE = os.path.join(VAULT_DIR, "settings.json")

    @classmethod
    def ensure_dirs(cls):
        os.makedirs(cls.PLAYBOOK_DIR, exist_ok=True)
        if not os.path.exists(cls.SETTINGS_FILE):
            with open(cls.SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump({"vernacular_mode": False}, f)

    @classmethod
    def set_vernacular_mode(cls, enabled: bool) -> str:
        cls.ensure_dirs()
        with open(cls.SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump({"vernacular_mode": enabled}, f)
        return "Vernacular Hinglish mode activated. Baat cheet desi style me hogi." if enabled else "Standard technical English restored."

    @classmethod
    def get_evolution_context(cls) -> str:
        cls.ensure_dirs()
        context_parts = []

        try:
            with open(cls.SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings = json.load(f)
                if settings.get("vernacular_mode"):
                    context_parts.append(
                        "Tone: Casual Hinglish slang. Use natural Hindi words like 'bhai', 'yaar', 'tension mat le', 'sorted hai'."
                    )
        except Exception:
            pass

        # Load learned playbooks
        if os.path.exists(cls.PLAYBOOK_DIR):
            playbooks = [f for f in os.listdir(cls.PLAYBOOK_DIR) if f.endswith(".md")]
            if playbooks:
                context_parts.append(f"Mastered Skills Available: {', '.join([p.replace('.md', '') for p in playbooks])}.")

        return "\n".join(context_parts)

    @classmethod
    def start_background_research(cls, topic: str, client, voice_engine):
        cls.ensure_dirs()
        t = threading.Thread(target=cls._research_worker, args=(topic, client, voice_engine), daemon=True)
        t.start()

    @classmethod
    def _research_worker(cls, topic: str, client, voice_engine):
        clean_name = "".join([c if c.isalnum() or c in (" ", "_") else "" for c in topic]).strip().replace(" ", "_").lower()
        filepath = os.path.join(cls.PLAYBOOK_DIR, f"{clean_name}.md")
        content = None

        prompt = (
            f"You are a technical researcher. Create an exhaustive, production-ready operational playbook on: '{topic}'.\n"
            f"Include exact architecture, system prompts, code implementations, and operational steps.\n"
            f"Output clean Markdown only."
        )

        # 1. Attempt Cloud Generation via stable gemini-2.5-flash
        if client:
            try:
                print(f"[*] [Evolution Engine] Initiating Research via Cloud: '{topic}'...")
                resp = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                if resp and resp.text:
                    content = resp.text.strip()
            except Exception as e:
                print(f"[!] Cloud API limit or error: {e}. Falling back to local Ollama core...")

        # 2. Local Ollama Fallback if Cloud Quota is Exhausted
        if not content:
            try:
                import ollama
                print(f"[*] [Evolution Engine] Running Local Ollama Synthesis for: '{topic}'...")
                res = ollama.chat(
                    model="llama3.2:3b",
                    messages=[
                        {"role": "system", "content": "You are an expert technical researcher. Produce detailed Markdown playbooks."},
                        {"role": "user", "content": prompt}
                    ]
                )
                content = res.get("message", {}).get("content", "").strip()
            except Exception as err:
                print(f"[!] Local Ollama also failed: {err}")

        # 3. Save only if genuine content was produced
        if content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"[*] [Evolution Engine] Playbook saved to: {filepath}")
            voice_engine.speak(f"Evolution complete. I have synthesized the operational playbook for {topic} and saved it to the vault.")
        else:
            voice_engine.speak(f"Could not synthesize playbook for {topic}. Both cloud and local engines were unavailable.")