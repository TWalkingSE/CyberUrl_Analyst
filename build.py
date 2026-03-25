"""
Script de empacotamento do CyberURL Analyst com PyInstaller.

AVISO: Streamlit não tem suporte oficial ao PyInstaller.
Este script é experimental e pode não gerar um executável funcional.
Para deploy, prefira Docker (docker-compose up) ou execução direta
(streamlit run app.py).

Uso:
    pip install pyinstaller
    python build.py

Gera executável standalone em dist/CyberURL_Analyst/
"""

import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def build():
    """Executa PyInstaller para gerar o executável."""
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "CyberURL_Analyst",
        "--noconfirm",
        "--clean",
        "--add-data", f"{BASE_DIR / 'assets'};assets",
        "--add-data", f"{BASE_DIR / '.streamlit'};.streamlit",
        "--add-data", f"{BASE_DIR / 'datasets' / 'phishtank_sample.csv'};datasets",
        "--add-data", f"{BASE_DIR / 'datasets' / 'urlhaus_sample.csv'};datasets",
        "--add-data", f"{BASE_DIR / 'datasets' / 'majestic_million_sample.csv'};datasets",
        "--add-data", f"{BASE_DIR / '.env.example'};.",
        "--add-data", f"{BASE_DIR / 'app.py'};.",
        "--hidden-import", "streamlit",
        "--hidden-import", "tldextract",
        "--hidden-import", "requests",
        "--hidden-import", "dotenv",
        "--hidden-import", "validators",
        "--exclude-module", "tkinter",
        "--exclude-module", "matplotlib",
        str(BASE_DIR / "app.py"),
    ]

    print("=" * 60)
    print("  CyberURL Analyst — Build (Streamlit)")
    print("=" * 60)
    print("\nExecutando PyInstaller...\n")
    print(f"Comando: {' '.join(cmd[-5:])}")
    print()

    result = subprocess.run(cmd, cwd=str(BASE_DIR))

    if result.returncode == 0:
        dist_path = BASE_DIR / "dist" / "CyberURL_Analyst"
        print(f"\n{'=' * 60}")
        print("  BUILD CONCLUÍDO COM SUCESSO!")
        print(f"  Executável em: {dist_path}")
        print(f"{'=' * 60}")
    else:
        print(f"\n  ERRO NO BUILD (código {result.returncode})")
        sys.exit(1)


if __name__ == "__main__":
    build()
