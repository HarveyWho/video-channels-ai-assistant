"""Install into an app-local environment, then launch. Windows only."""
import importlib.metadata
import os
from pathlib import Path
import struct
import subprocess
import sys
import venv


def main():
    if sys.platform != "win32" or struct.calcsize("P") != 8:
        raise SystemExit("This launcher requires 64-bit Windows 10/11 and Python 3.11-3.13.")
    if not (3,11) <= sys.version_info[:2] <= (3,13):
        raise SystemExit("Please use Python 3.11, 3.12 or 3.13 (64-bit).")
    root=Path(__file__).resolve().parent
    os.chdir(root)
    environment=root/".venv"
    python=environment/"Scripts"/"python.exe"
    if not python.exists():
        print("Creating the local environment (first launch only)...",flush=True)
        venv.EnvBuilder(with_pip=True).create(environment)
    check="import rapidocr,onnxruntime,mss,PIL,tkinter;import importlib.metadata as m;"+";".join(
        "assert m.version(%r)==%r"%tuple(line.split("=="))
        for line in (root/"requirements.txt").read_text().splitlines() if "==" in line)
    result=subprocess.run([str(python),"-c",check],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    if result.returncode:
        print("Installing OCR components. This can take several minutes on first launch.",flush=True)
        command=[str(python),"-m","pip","install","--disable-pip-version-check","--only-binary=:all:","-r","requirements.txt"]
        result=subprocess.run(command+["--index-url","https://pypi.tuna.tsinghua.edu.cn/simple"])
        if result.returncode:
            print("The mirror did not finish. Retrying with the official Python package index.",flush=True)
            subprocess.run(command+["--index-url","https://pypi.org/simple"],check=True)
    return subprocess.call([str(python),"app.py"])


if __name__=="__main__":
    try:
        sys.exit(main())
    except (OSError,subprocess.CalledProcessError) as exc:
        print("Setup failed. Check the network, available disk space, and write permission.")
        sys.exit(1)
