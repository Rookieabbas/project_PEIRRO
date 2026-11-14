# Project Peirro 🤖🎙️

Peirro is a custom, voice-controlled Python assistant designed for seamless desktop interaction. Powered by the **Groq Whisper API**, it features quick hotkey triggers and visual state indicators to make voice commands fast and responsive.

## ✨ Features
* **Lightning-Fast Speech Recognition:** Integrated with the Groq Whisper API for quick, accurate audio transcription.
* **Global Hotkey Triggers:** Easily activate the assistant using keyboard shortcuts (`Ctrl + I` and `Ctrl + Space`).
* **Visual State Indicators:** Real-time visual feedback reflecting the assistant's current operational state.
* **Modular Architecture:** Clean separation of drivers, tools, and workspace agents.


## 🚀 Getting Started

* **1. Clone the Repository**
git clone [https://github.com/Rookieabbas/project_PEIRRO.git](https://github.com/Rookieabbas/project_PEIRRO.git)
cd project_PEIRRO

* **2. Install Dependencies**
Make sure you have Python installed, then run:
pip install -r requirements.txt

* **3. Configure Your Environment Variables**
Create a .env file in the root directory of your project and add your Groq API key:
Code snippet
GROQ_API_KEY=your_actual_groq_api_key_here

* **4. Run Peirro**
Start the assistant by running the main script:
python peirro.py

* **⌨️ Usage**
Press Ctrl + I or Ctrl + Space to trigger listening mode.
Speak your command, and let Peirro handle the rest!

---

## 📂 Project Structure
```text
ProjectPeirro/
├── drivers/
│   ├── os_operator.py      # OS-level control scripts
│   ├── uia_vision.py       # UI automation / vision support
│   └── voice_engine.py     # Core audio capture & processing
├── tools/
│   ├── data_scientist.py   # Data processing utilities
│   └── dev_sandbox.py      # Execution sandbox
├── vault/                  # Local config and settings
│   ├── personality_profile.json
│   └── settings.json
├── workspace/              # Custom workspace agents
├── peirro.py               # Main entry point script
├── requirements.txt        # Python dependencies
└── .env                    # Environment variables (API keys - DO NOT COMMIT)
---
