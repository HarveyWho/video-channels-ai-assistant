"""Build a portable, pinned two-model release, split below GitHub's 2 GiB limit."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(8*1024*1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url, path, expected):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=120) as response, path.open("wb") as target:
                shutil.copyfileobj(response, target, length=8*1024*1024)
            if sha256(path) != expected:
                raise ValueError("Digest mismatch: " + path.name)
            return
        except (OSError, ValueError):
            path.unlink(missing_ok=True)
            if attempt == 2:
                raise


def model_files(manifest):
    """Validate registry-provided blob names before using them as local paths."""
    import re
    files = {}
    for layer in [manifest["config"]] + manifest["layers"]:
        digest = layer["digest"]
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest) or type(layer["size"]) is not int or layer["size"] < 0:
            raise ValueError("Invalid model descriptor")
        files[digest] = layer["size"]
    return files


def main():
    if os.name != "nt":
        raise SystemExit("Run on a Windows build host.")
    bundle = ROOT / "dist/Live Answer Assistant"
    output = ROOT / "release"
    config = json.loads((ROOT / "bundled_models.json").read_text())
    runtime = bundle / "Local Runtime"
    models = bundle / "Models"
    licenses = bundle / "Third Party Licenses"
    runtime.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        archive = Path(temporary) / "ollama.zip"
        version = config["ollama_version"]
        print("Downloading pinned portable Ollama", version, flush=True)
        download("https://github.com/ollama/ollama/releases/download/"+version+"/ollama-windows-amd64.zip",
                 archive, config["ollama_windows_sha256"])
        with zipfile.ZipFile(archive) as source:
            # CPU libraries support Surface's Intel/AMD CPUs without a separate GPU driver install.
            for entry in source.infolist():
                name = entry.filename
                if name == "ollama.exe" or (name.startswith("lib/ollama/") and len(Path(name).parts) == 3 and not entry.is_dir()):
                    source.extract(entry, runtime)
    ollama_license = licenses / "Ollama/LICENSE.txt"
    ollama_license.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen("https://raw.githubusercontent.com/ollama/ollama/"+version+"/LICENSE") as response:
        ollama_license.write_bytes(response.read())
    blobs = models / "blobs"
    manifests = models / "manifests/registry.ollama.ai/library/qwen3.5"
    manifests.mkdir(parents=True, exist_ok=True)
    for tag, expected in config["models"].items():
        print("Downloading and verifying Qwen3.5", tag, flush=True)
        manifest_path = manifests / tag
        source_manifest = ROOT / "Model Manifests" / ("qwen3.5 " + tag + ".json")
        if sha256(source_manifest) != expected:
            raise ValueError("Pinned manifest changed")
        shutil.copy2(source_manifest, manifest_path)
        manifest = json.loads(manifest_path.read_bytes())
        for digest, size in model_files(manifest).items():
            target = blobs / digest.replace(":", "-")
            if not target.exists():
                download("https://registry.ollama.ai/v2/library/qwen3.5/blobs/"+digest, target, digest.split(":")[1])
            if target.stat().st_size != size:
                raise ValueError("Blob size mismatch")
        model_license = licenses / ("Qwen3.5 " + tag)
        model_license.mkdir(exist_ok=True)
        for index, layer in enumerate(manifest["layers"]):
            if layer["mediaType"].endswith(".license"):
                shutil.copy2(blobs / layer["digest"].replace(":", "-"), model_license / ("LICENSE " + str(index) + ".txt"))
    shutil.copy2(ROOT / "bundled_models.json", bundle / "Bundled Models.json")
    report = output / "Bundled Model Check.json"
    print("Checking both models through the packaged EXE", flush=True)
    subprocess.run([str(bundle / "Live Answer Assistant.exe"), "--check-models", str(report)], check=True, timeout=700)
    result = json.loads(report.read_text(encoding="utf-8"))
    if result["status"] != "passed":
        raise RuntimeError(str(result))
    seven = Path(os.environ["ProgramFiles"]) / "7-Zip/7z.exe"
    archive = output / "Live.Answer.Assistant.Offline.7z"
    subprocess.run([str(seven), "a", "-t7z", "-mx=0", "-v1800m", str(archive)] +
        [p.name for p in bundle.iterdir()], cwd=bundle, check=True)
    parts = sorted(output.glob(archive.name+".*"))
    if not parts or any(p.stat().st_size >= 2*1024**3 for p in parts):
        raise RuntimeError("Missing or oversized offline volumes")
    subprocess.run([str(seven), "t", str(parts[0])], check=True)
    import ast
    module = ast.parse((ROOT / "app.py").read_text(encoding="utf-8"))
    version = next(ast.literal_eval(n.value) for n in module.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "VERSION" for t in n.targets))
    metadata = {"version": version, "unpacked_bytes": sum(p.stat().st_size for p in bundle.rglob("*") if p.is_file()),
                "parts": [{"name": p.name, "size": p.stat().st_size, "sha256": sha256(p)} for p in parts]}
    (output / "Offline Package.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    setup = ROOT / "build/Offline Setup"
    setup.mkdir(parents=True, exist_ok=True)
    for name in ["Install Offline.cmd", "Install Offline.ps1"]:
        shutil.copy2(ROOT / name, setup / name)
    shutil.copy2(output / "Offline Package.json", setup)
    for name in ["7z.exe", "7z.dll", "License.txt"]:
        shutil.copy2(seven.parent / name, setup / name)
    with zipfile.ZipFile(output / "Windows.Offline.Setup.zip", "w", zipfile.ZIP_DEFLATED) as zipped:
        for path in setup.iterdir():
            zipped.write(path, path.name)
    with (output / "SHA256.txt").open("w", encoding="utf-8") as target:
        for path in sorted(output.iterdir()):
            if path.is_file() and path.name != "SHA256.txt":
                target.write(sha256(path)+"  "+path.name+"\n")
    print(json.dumps(metadata), flush=True)


if __name__ == "__main__":
    main()
