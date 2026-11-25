"""Own the portable Ollama process; never change a system Ollama installation."""
import atexit
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
import urllib.request

from core import ApiError

MODELS = ("qwen3.5:2b", "qwen3.5:4b")


class LocalRuntime:
    def __init__(self, root=None):
        self.root = Path(root) if root else (Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent)
        self.executable = self.root / "Local Runtime" / "ollama.exe"
        self.models = self.root / "Models"
        self.process = None
        self.host = None
        self.lock = threading.Lock()
        atexit.register(self.close)

    @property
    def bundled(self):
        return self.executable.is_file()

    def environment(self):
        env = os.environ.copy()
        env.pop("DEEPSEEK_API_KEY", None)
        env.update(OLLAMA_HOST=self.host, OLLAMA_MODELS=str(self.models), OLLAMA_NO_CLOUD="1",
                   OLLAMA_MAX_LOADED_MODELS="1", OLLAMA_NUM_PARALLEL="1", OLLAMA_CONTEXT_LENGTH="8192")
        return env

    def endpoint(self):
        if not self.bundled:
            if self.models.exists():
                raise ApiError("内置运行组件缺失，请重新解压完整离线包。")
            return "http://127.0.0.1:11434/api/chat"
        with self.lock:
            if self.process is not None and self.process.poll() is None:
                return "http://" + self.host + "/api/chat"
            for model in MODELS:
                tag = model.split(":")[1]
                if not (self.models / "manifests/registry.ollama.ai/library/qwen3.5" / tag).is_file():
                    raise ApiError("内置模型不完整，请重新解压所有离线分卷。")
            with socket.socket() as listener:
                listener.bind(("127.0.0.1", 0))
                self.host = "127.0.0.1:" + str(listener.getsockname()[1])
            self.process = subprocess.Popen([str(self.executable), "serve"], cwd=str(self.executable.parent),
                env=self.environment(), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline and self.process.poll() is None:
                try:
                    with opener.open("http://" + self.host + "/api/tags", timeout=1) as response:
                        names = {m["name"] for m in json.load(response)["models"]}
                    if not set(MODELS).issubset(names):
                        raise ApiError("内置服务没有找到 2B 和 4B，请重新解压离线包。")
                    return "http://" + self.host + "/api/chat"
                except (OSError, ValueError, KeyError):
                    time.sleep(.1)
            self.close()
            raise ApiError("内置模型服务启动失败，请检查解压是否完整及安全软件的拦截记录。")

    def close(self):
        process, self.process = self.process, None
        if process is not None and process.poll() is None:
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


def check_models(report_path):
    """Called by the frozen release EXE, using only its own portable runtime."""
    from core import OllamaClient
    report = {"status": "failed", "external_network_used": False, "models": []}
    runtime = LocalRuntime()
    try:
        if not runtime.bundled:
            raise RuntimeError("Portable runtime missing")
        endpoint = runtime.endpoint()
        for model in MODELS:
            start = time.monotonic()
            client = OllamaClient(model, endpoint, first_timeout=240, total_timeout=300)
            result = "".join(client.stream("", "请只回复：连接成功。", "", "", threading.Event()))
            if not result.strip():
                raise RuntimeError("Empty response: " + model)
            report["models"].append({"model": model, "response": result, "seconds": round(time.monotonic()-start, 2)})
        report["status"] = "passed"
    except Exception as exc:
        report["error"] = type(exc).__name__ + ": " + str(exc)
    finally:
        runtime.close()
    Path(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if report["status"] == "passed" else 1
