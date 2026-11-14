"""
ResumeGenie - Universal Standalone Agent Runner
"""
import os
from dotenv import load_dotenv

load_dotenv()

with open("system_prompt.txt", "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()

def run_agent(user_query: str) -> str:
    # 1. Try Claude if key is present
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    if anthropic_key:
        try:
            from anthropic import Anthropic
            c = Anthropic(api_key=anthropic_key)
            resp = c.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_query}]
            )
            return resp.content[0].text
        except Exception as e:
            print(f"[!] Claude API error: {e}. Falling back...")

    # 2. Fallback to Gemini
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if gemini_key:
        try:
            from google import genai
            g_client = genai.Client(api_key=gemini_key)
            resp = g_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"{SYSTEM_PROMPT}\n\nUser Task: {user_query}"
            )
            return resp.text.strip()
        except Exception as e:
            print(f"[!] Gemini API error: {e}. Falling back to local core...")

    # 3. Fallback to Local Ollama
    try:
        import ollama
        res = ollama.chat(
            model="llama3.2:3b",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_query}
            ]
        )
        return res.get("message", {}).get("content", "").strip()
    except Exception as e:
        return f"Error: No AI engine was able to respond: {e}"

if __name__ == "__main__":
    print("=" * 50)
    print("  ResumeGenie ACTIVE")
    print("=" * 50)
    while True:
        try:
            query = input("\nAsk ResumeGenie (or 'exit') > ").strip()
            if not query or query.lower() in ["exit", "quit", "q"]:
                break
            print("\nGenerating response...")
            output = run_agent(query)
            print("-" * 50)
            print(output)
            print("-" * 50)
        except (KeyboardInterrupt, EOFError):
            break
