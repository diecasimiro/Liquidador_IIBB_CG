"""
Lanzador alternativo. Preferir usar iibb.bat o 'streamlit run iibb/main.py'.
"""
import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    app = Path(__file__).parent / "iibb" / "main.py"
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(app)], check=True)
