"""Release smoke check. Uses synthetic text; never calls an AI service."""
import json
import sys
from pathlib import Path


def run(report_path):
    report={"status":"failed","platform":sys.platform,"api_called":False}
    try:
        import numpy as np
        from PIL import Image
        from vision import ScreenReader,group_lines
        from core import QuestionTracker
        reader=ScreenReader()
        samples=[]
        for name in ["Light Comments.png","Dark Comments.png"]:
            image=Image.open(Path(__file__).resolve().parent/"assets"/name).convert("RGB")
            result=reader.engine(np.array(image)[:,:,::-1].copy())
            lines=group_lines(zip(result.boxes,result.txts,result.scores))
            questions=QuestionTracker().ingest(lines)
            if len(questions)!=3:
                raise RuntimeError("Synthetic OCR did not find the three expected questions in "+name)
            samples.append({"fixture":name,"questions":questions})
        report["synthetic_ocr"]=samples
        import tkinter as tk
        from app import Assistant,VERSION
        report["app_version"]=VERSION
        root=tk.Tk()
        root.withdraw()
        try:
            app=Assistant(root,demo=True)
            app.show_prompter()
            app.prompter.withdraw()
            app.settings()
            app.settings_window.withdraw()
            root.update_idletasks()
            if not app.prompter.body.get("1.0","end-1c") or not app.settings_window.winfo_exists():
                raise RuntimeError("Demo interface could not be constructed.")
            report["gui_constructed"]=True
        finally:
            root.destroy()
        report["status"]="passed"
    except Exception as exc:
        report["error"]=type(exc).__name__+": "+str(exc)
    Path(report_path).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    return 0 if report["status"]=="passed" else 1
