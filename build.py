"""Build script for the PyQt6 desktop executable via PyInstaller."""

import shutil
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
ICONS_DIR = ASSETS_DIR / "icons"
APP_ICON_PATH = ICONS_DIR / "phishing_tecnologico.png"
RELEASE_NOTICE_FILES = [
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "GPL-3.0.txt",
]


def build():
    """Executa PyInstaller para gerar o executavel desktop."""
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name", "CyberURL_Analyst",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--add-data", f"{BASE_DIR / 'assets'};assets",
        "--add-data", f"{BASE_DIR / 'templates'};templates",
        "--add-data", f"{BASE_DIR / 'locales'};locales",
        "--add-data", f"{BASE_DIR / 'data' / 'scenarios.json'};data",
        "--add-data", f"{BASE_DIR / 'datasets' / 'phishtank_sample.csv'};datasets",
        "--add-data", f"{BASE_DIR / 'datasets' / 'urlhaus_sample.csv'};datasets",
        "--add-data", f"{BASE_DIR / 'datasets' / 'majestic_million_sample.csv'};datasets",
        "--add-data", f"{BASE_DIR / '.env.example'};.",
        "--add-data", f"{BASE_DIR / 'LICENSE'};.",
        "--add-data", f"{BASE_DIR / 'THIRD_PARTY_NOTICES.md'};.",
        "--add-data", f"{BASE_DIR / 'GPL-3.0.txt'};.",
        "--hidden-import", "PyQt6.sip",
        "--hidden-import", "jinja2",
        "--hidden-import", "joblib",
        "--hidden-import", "sklearn",
        "--hidden-import", "tldextract",
        "--hidden-import", "requests",
        "--hidden-import", "dotenv",
        "--hidden-import", "validators",
        "--hidden-import", "whois",
        "--exclude-module", "pytest",
        "--exclude-module", "_pytest",
        "--exclude-module", "pluggy",
        "--exclude-module", "tkinter",
        "--exclude-module", "matplotlib",
        str(BASE_DIR / "app.py"),
    ]

    if APP_ICON_PATH.exists():
        cmd[6:6] = ["--icon", str(APP_ICON_PATH)]

    print("=" * 60)
    print("  CyberURL Analyst — Build (PyQt6)")
    print("=" * 60)
    print("\nExecutando PyInstaller...\n")
    print(f"Entrypoint: {BASE_DIR / 'app.py'}")
    print()

    result = subprocess.run(cmd, cwd=str(BASE_DIR))

    if result.returncode == 0:
        dist_path = BASE_DIR / "dist" / "CyberURL_Analyst"
        for notice_name in RELEASE_NOTICE_FILES:
            shutil.copy2(BASE_DIR / notice_name, dist_path / notice_name)
        print(f"\n{'=' * 60}")
        print("  BUILD CONCLUIDO COM SUCESSO!")
        print(f"  Executavel em: {dist_path}")
        print(f"{'=' * 60}")
    else:
        print(f"\n  ERRO NO BUILD (codigo {result.returncode})")
        sys.exit(1)


if __name__ == "__main__":
    build()
