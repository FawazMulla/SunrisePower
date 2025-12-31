#!/usr/bin/env python3
"""
Simple deployment helper for Solar CRM Platform
"""

import os
import subprocess
import sys
from pathlib import Path

def run_command(command, cwd=None):
    """Run a command and return the result"""
    try:
        result = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error running command: {command}")
            print(f"Error: {result.stderr}")
            return False
        return True
    except Exception as e:
        print(f"Exception running command: {command}")
        print(f"Exception: {e}")
        return False

def main():
    print("=" * 60)
    print("SOLAR CRM PLATFORM - DEPLOYMENT HELPER")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not Path("backend/manage.py").exists():
        print("❌ Error: Please run this script from the project root directory")
        print("   (The directory containing backend/ and frontend/ folders)")
        sys.exit(1)
    
    print("✅ Project structure verified")
    
    # Generate secret key
    print("\n📝 Generating Django secret key...")
    os.chdir("backend")
    
    # Check if virtual environment exists
    venv_path = Path("venv")
    if venv_path.exists():
        if os.name == 'nt':  # Windows
            python_cmd = "venv\\Scripts\\python.exe"
        else:  # Unix/Linux/Mac
            python_cmd = "venv/bin/python"
    else:
        python_cmd = "python"
    
    # Generate secret key
    secret_key_cmd = f'{python_cmd} -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"'
    result = subprocess.run(secret_key_cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        secret_key = result.stdout.strip()
        print(f"✅ Secret key generated: {secret_key[:20]}...")
    else:
        print("❌ Error generating secret key. Please run manually:")
        print("   python generate_secret_key.py")
        secret_key = "GENERATE_MANUALLY"
    
    # Create deployment info
    print("\n🚀 DEPLOYMENT INFORMATION")
    print("=" * 40)
    print("1. RENDER DEPLOYMENT:")
    print("   - Go to render.com")
    print("   - Create Web Service from GitHub")
    print("   - Build Command: ./build.sh")
    print("   - Start Command: cd backend && gunicorn solar_crm.wsgi:application")
    print("\n2. ENVIRONMENT VARIABLES:")
    print(f"   SECRET_KEY={secret_key}")
    print("   ALLOWED_HOSTS=your-app-name.onrender.com")
    print("   DJANGO_SETTINGS_MODULE=solar_crm.settings.production")
    print("   COHERE_API_KEY=your-cohere-api-key")
    print("   EMAILJS_WEBHOOK_SECRET=your-emailjs-webhook-secret")
    
    print("\n3. POST-DEPLOYMENT:")
    print("   - Create superuser in Render console:")
    print("   - python backend/manage.py createsuperuser")
    
    print("\n✅ Your Solar CRM Platform is ready for deployment!")
    print("📖 See README.md for detailed instructions")
    
    # Go back to root directory
    os.chdir("..")

if __name__ == "__main__":
    main()