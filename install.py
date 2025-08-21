import subprocess
import sys
import os
import platform

def install():
    print("📦 Creating virtual environment...")
    subprocess.check_call([sys.executable, "-m", "venv", ".venv"])
    
    print("✅ Virtual environment created.")
    
    # Detect OS and set correct paths
    is_windows = platform.system() == "Windows"
    if is_windows:
        python_path = ".venv\\Scripts\\python"
        activate_cmd = ".venv\\Scripts\\activate"
    else:
        python_path = ".venv/bin/python"
        activate_cmd = "source .venv/bin/activate"
    
    print("📍 To activate it:")
    print(f"Run: {activate_cmd}")

    print("⬆️ Upgrading pip...")
    subprocess.check_call([python_path, "-m", "pip", "install", "--upgrade", "pip"])

    print("📥 Installing requirements...")
    subprocess.check_call([python_path, "-m", "pip", "install", "-r", "requirements.txt"])

    print("✅ Setup complete!")
    print(f"🚀 To run the app:")
    print(f"1. {activate_cmd}")
    print("2. streamlit run app.py")

if __name__ == "__main__":
    install()
