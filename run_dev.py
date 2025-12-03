import subprocess
import sys
import time
import os
import signal

def run_services():
    # Use the current python executable
    python_exe = sys.executable
    
    # Start Backend
    print("Starting Backend on http://localhost:8000...")
    backend_process = subprocess.Popen(
        [python_exe, "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
        cwd=os.getcwd(),
        env=os.environ.copy()
    )
    
    # Wait a bit for backend to initialize
    time.sleep(5)
    
    # Start Frontend
    print("Starting Frontend on http://localhost:8501...")
    # Streamlit requires running as a module or script
    frontend_process = subprocess.Popen(
        [python_exe, "-m", "streamlit", "run", "frontend/app.py"],
        cwd=os.getcwd(),
        env=os.environ.copy()
    )
    
    try:
        while True:
            time.sleep(1)
            if backend_process.poll() is not None:
                print("Backend crashed!")
                break
            if frontend_process.poll() is not None:
                print("Frontend crashed!")
                break
    except KeyboardInterrupt:
        print("\nStopping services...")
    finally:
        backend_process.terminate()
        frontend_process.terminate()
        print("Services stopped.")

if __name__ == "__main__":
    run_services()
