"""Build a Windows directory bundle and include available dependency licenses."""
import hashlib
import importlib.metadata
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile


def main():
    if sys.platform!="win32":
        raise SystemExit("Build this package on Windows, or use the GitHub Windows release workflow.")
    root=Path(__file__).resolve().parent
    os.chdir(root)
    subprocess.run([sys.executable,"-m","PyInstaller","--noconfirm","--clean","--onedir","--windowed",
        "--name","Live Answer Assistant","--collect-all","rapidocr","--collect-all","onnxruntime",
        "--collect-all","shapely","--copy-metadata","omegaconf","--copy-metadata","certifi",
        "--hidden-import","PIL._tkinter_finder","--add-data","assets:assets","app.py"],check=True)
    bundle=root/"dist"/"Live Answer Assistant"
    licenses=bundle/"Third Party Licenses"
    licenses.mkdir(exist_ok=True)
    installed=[]
    for distribution in importlib.metadata.distributions():
        name=distribution.metadata.get("Name","unknown")
        installed.append(name+"=="+distribution.version)
        for relative in distribution.files or []:
            parts=Path(relative).parts
            if not any(part.endswith((".dist-info",".egg-info")) for part in parts):
                continue
            if not any(any(marker in part.lower() for marker in ("license","notice","copying")) for part in parts):
                continue
            source=Path(distribution.locate_file(relative))
            if source.is_file():
                target=licenses/name/Path(*parts[1:])
                target.parent.mkdir(exist_ok=True,parents=True)
                shutil.copy2(source,target)
    (licenses/"Installed Packages.txt").write_text("\n".join(sorted(installed))+"\n",encoding="utf-8")
    for name in ["README.md","使用说明.md","Windows 下载和测试.txt","LICENSE","PRIVACY.md","THIRD PARTY NOTICES.md"]:
        shutil.copy2(root/name,bundle/name)
    # Retain Tcl/Tk license text from the Python distribution when available.
    tcl=Path(sys.base_prefix)/"tcl"
    if tcl.exists():
        for path in tcl.rglob("license*"):
            if path.is_file():
                target=licenses/"Tcl Tk"/path.relative_to(tcl)
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(path,target)
    output=root/"release"
    output.mkdir(exist_ok=True)
    archive=output/"Live Answer Assistant Windows.zip"
    with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED) as z:
        for path in sorted(bundle.rglob("*")):
            if path.is_file():
                z.write(path,path.relative_to(bundle.parent))
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    (output/"SHA256.txt").write_text(digest+"  "+archive.name+"\n",encoding="utf-8")
    print("Created",archive.name)


if __name__=="__main__":
    main()
