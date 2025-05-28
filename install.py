import subprocess
import sys
import os

def install():
    print("📦 Creating virtual environment...")
    subprocess.check_call([sys.executable, "-m", "venv", ".venv"])
    
    print("✅ Virtual environment created.")
    print("📍 To activate it:")
    print("Windows: .venv\\Scripts\\activate")
    print("macOS/Linux: source .venv/bin/activate")

    print("⬆️ Upgrading pip...")
    subprocess.check_call([f".venv\\Scripts\\python", "-m", "pip", "install", "--upgrade", "pip"])

    print("📥 Installing requirements...")
    subprocess.check_call([f".venv\\Scripts\\python", "-m", "pip", "install", "-r", "requirements.txt"])

    print("✅ Setup complete. You can now run: streamlit run app.py")

if __name__ == "__main__":
    install()
