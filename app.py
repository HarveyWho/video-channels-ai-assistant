"""Windows companion: local OCR -> DeepSeek -> a pinned teleprompter."""
import ctypes
import json
import logging
from logging.handlers import RotatingFileHandler
import os
import queue
import sys
import threading
import time
import webbrowser
from dataclasses import dataclass
from pathlib import Path

if sys.platform == "win32":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        pass

import tkinter as tk
from tkinter import messagebox, ttk
from core import ApiError, Cancelled, DeepSeekClient, OllamaClient, QuestionTracker, local_answer, normalise
from vision import ScreenReader, overlaps, valid_region
from local_runtime import LocalRuntime

PAPER = "#F5F1E8"
INK = "#202B29"
MUTED = "#50615B"
GREEN = "#245E4B"
NIGHT = "#192522"
CREAM = "#F7F1E3"
FONT = "SimSun" if sys.platform == "win32" else "Songti SC"
VERSION = "0.3.0-rc1"
CONFIG = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Live Answer Assistant" / "settings.json"
LOG=logging.getLogger("live.answer")


@dataclass
class Answer:
    question: str
    source: str
    text: str = ""
    state: str = "待生成"
    error: str = ""
    engine: str = ""
    started: float = 0.0
    first_s: float = -1.0
    elapsed_s: float = 0.0


class Prompter(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.title("直播提词 · 仅供主播查看")
        self.geometry("720x540")
        self.minsize(430, 340)
        self.configure(bg=NIGHT)
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self.withdraw)
        top = tk.Frame(self, bg=NIGHT)
        top.pack(fill="x", padx=22, pady=(16, 10))
        tk.Label(top, text="当前回答", bg=NIGHT, fg="#B3C6BD", font=(FONT, 12)).pack(side="left")
        for text, action in [("上一条", lambda: app.step(-1)), ("下一条", lambda: app.step(1)),
                             ("字小", lambda: app.resize_font(-2)), ("字大", lambda: app.resize_font(2))]:
            ttk.Button(top, text=text, command=action, style="Prompt.TButton",width=5).pack(side="right", padx=3)
        self.question = tk.Label(self, text="等待观众提问", bg=NIGHT, fg="#B3C6BD",
                                 font=(FONT, 17), anchor="w", justify="left", wraplength=650)
        self.question.pack(fill="x", padx=24, pady=(6, 14))
        content=tk.Frame(self,bg=NIGHT)
        content.grid_rowconfigure(0,weight=1)
        content.grid_columnconfigure(0,weight=1)
        self.body = tk.Text(content, bg=NIGHT, fg=CREAM, insertbackground=CREAM, height=6,
                            font=(FONT, app.fontsize), relief="flat", wrap="word",
                            padx=24, pady=8, spacing1=5, spacing3=10, borderwidth=0,
                            highlightthickness=0, state="disabled")
        self.body.grid(row=0,column=0,sticky="nsew")
        scroll=ttk.Scrollbar(content,command=self.body.yview)
        scroll.grid(row=0,column=1,sticky="ns")
        self.body.configure(yscrollcommand=scroll.set)
        self.foot = tk.Label(self, text="回答会保留在这里；读完后点击下一条。", bg=NIGHT,
                             fg="#B3C6BD", font=(FONT, 11), anchor="w")
        self.foot.pack(side="bottom",fill="x", padx=24, pady=(10, 16))
        content.pack(fill="both",expand=True)
        self.bind("<Configure>", lambda e: self.question.configure(wraplength=max(250, self.winfo_width()-48)))
        self.bind("<Control-Right>", lambda e: app.step(1))
        self.bind("<Control-Left>", lambda e: app.step(-1))


class Assistant:
    def __init__(self, root, demo=False):
        self.root = root
        self.demo = demo
        self.events = queue.Queue()
        self.records = []
        self.current = None
        self.rendered_current = None
        self.client = DeepSeekClient()
        self.local_runtime = LocalRuntime()
        self.tracker = QuestionTracker()
        self.monitor_stop = threading.Event()
        self.capture_blocked = threading.Event()
        self.cancel = threading.Event()
        self.monitor_thread = None
        self.monitor_epoch = 0
        self.active = None
        self.generating = False
        self.test_busy = False
        self.test_started = 0.0
        self.next_request_at = 0
        self.prompter = None
        self.settings_window = None
        self.last_ocr = []
        self.region = None
        self.fontsize = 28
        self.key = os.environ.get("DEEPSEEK_API_KEY", "")
        self.provider = "ollama"
        self.local_model = "qwen3.5:2b"
        self.process_existing = True
        self.force_current = False
        self.topic = ""
        self.context = ""
        self.only_questions = True
        self.interval = 1.5
        self.config_warning = ""
        if not demo and not LOG.handlers:
            try:
                CONFIG.parent.mkdir(parents=True,exist_ok=True)
                handler=RotatingFileHandler(CONFIG.parent/"diagnostics.log",maxBytes=200000,backupCount=1,encoding="utf-8")
                handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
                LOG.addHandler(handler)
                LOG.setLevel(logging.INFO)
            except OSError:
                pass
        self.load_config()
        self.build()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(80, self.poll)
        if demo:
            self.records = [Answer("孩子五年级，现在开始准备 KET 来得及吗？", "演示",
                "可以先做一次听说读写的基础摸底，再根据结果安排备考。\n\n如果基础比较扎实，就可以进入题型训练；如果词汇和听力还有明显缺口，先补基础会更有效。具体需要多久，要看孩子目前的水平和每周能投入的时间。", "已完成"),
                Answer("一周安排几次课比较合适？", "演示", "建议先结合孩子的基础和每周可以稳定投入的时间安排。具体课次和作业量，还需要主播结合课程设置确认。", "已完成")]
            self.current = 0
            self.refresh()
            self.status("演示模式：使用固定示例，不采集屏幕、不调用 DeepSeek。")
            self.root.after(200, self.show_prompter)

    def load_config(self):
        try:
            if CONFIG.exists() and CONFIG.stat().st_size < 100000:
                data = json.loads(CONFIG.read_text(encoding="utf-8"))
                self.topic = str(data.get("topic", ""))[:300]
                self.context = str(data.get("context", ""))[:12000]
                self.provider = data.get("provider","ollama")
                if self.provider not in ("ollama","deepseek"):
                    self.provider="ollama"
                self.local_model = str(data.get("local_model","qwen3.5:2b"))[:100]
                self.process_existing = bool(data.get("process_existing",True))
                self.only_questions = bool(data.get("only_questions", True))
                self.interval = max(1.0, min(10.0, float(data.get("interval", 1.5))))
                self.fontsize = max(18, min(52, int(data.get("fontsize", 28))))
                if valid_region(data.get("region")):
                    self.region = data["region"]
        except (OSError, ValueError, TypeError, AttributeError):
            self.config_warning = "上次设置未能读取，请重新设置。"

    def save_config(self):
        if self.demo:
            return
        try:
            CONFIG.parent.mkdir(parents=True, exist_ok=True)
            temp = CONFIG.with_suffix(".tmp")
            temp.write_text(json.dumps({"topic": self.topic, "context": self.context,
                "only_questions": self.only_questions, "interval": self.interval,
                "fontsize": self.fontsize, "region": self.region,"provider":self.provider,
                "local_model":self.local_model,"process_existing":self.process_existing}, ensure_ascii=False, indent=2), encoding="utf-8")
            temp.replace(CONFIG)
        except OSError:
            self.status("设置未能保存；本次运行仍然可以使用。", True)

    def build(self):
        root = self.root
        root.title("直播答疑助手 v"+VERSION+" · 本地模型 / DeepSeek")
        root.geometry("1040x720")
        root.minsize(820, 600)
        root.configure(bg=PAPER)
        root.grid_rowconfigure(3,weight=1)
        root.grid_columnconfigure(0,weight=1)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background=PAPER)
        style.configure("TLabel", background=PAPER, foreground=INK, font=(FONT, 12))
        style.configure("TButton", font=(FONT, 12), padding=(11, 8))
        style.configure("Accent.TButton", background=GREEN, foreground="white")
        style.map("Accent.TButton", background=[("active", "#164837"), ("disabled", "#72867B")])
        style.configure("Prompt.TButton", background="#2C4038",foreground=CREAM,
                        font=(FONT,11),padding=(8,5),borderwidth=0)
        style.map("Prompt.TButton",background=[("active",GREEN)],foreground=[("active",CREAM)])
        header = ttk.Frame(root)
        header.grid(row=0,column=0,sticky="ew",padx=24,pady=(20,12))
        ttk.Label(header, text="直播答疑", font=(FONT, 25, "bold")).pack(side="left")
        ttk.Label(header, text="本地优先 · 主播提词", foreground=MUTED).pack(side="left", padx=18)
        tools = ttk.Frame(root)
        tools.grid(row=1,column=0,sticky="ew",padx=24,pady=(0,10))
        ttk.Button(tools, text="模型与资料设置", command=self.settings).pack(side="left", padx=(0, 8))
        ttk.Button(tools, text="选择弹幕区域", command=self.select_region).pack(side="left", padx=(0, 8))
        self.start_button = ttk.Button(tools, text="开始监听", style="Accent.TButton", command=self.start)
        self.start_button.pack(side="left", padx=(0, 8))
        ttk.Button(tools, text="暂停", command=self.pause).pack(side="left")
        ttk.Button(tools,text="重读当前弹幕",command=self.reread).pack(side="left",padx=8)
        ttk.Button(tools, text="打开提词窗口", command=self.show_prompter).pack(side="right")
        self.region_label = ttk.Label(root, text=self.region_description(), foreground=MUTED, font=(FONT, 10))
        self.region_label.grid(row=2,column=0,sticky="ew",padx=26,pady=(0,12))
        body = tk.PanedWindow(root, orient="horizontal", bg=PAPER, sashwidth=12, borderwidth=0,height=320)
        body.grid(row=3,column=0,sticky="nsew",padx=24)
        left = ttk.Frame(body)
        body.add(left, width=290, minsize=230)
        self.count_label = ttk.Label(left, text="问题队列 · 0 条", font=(FONT, 13, "bold"))
        self.count_label.pack(anchor="w", pady=(0, 9))
        listframe = ttk.Frame(left)
        listframe.pack(fill="both", expand=True)
        self.listbox = tk.Listbox(listframe, bg="#E7EBE3", fg=INK, relief="flat", borderwidth=0,
            font=(FONT, 12), activestyle="none", selectbackground=GREEN, selectforeground="white",
            exportselection=False, highlightthickness=1, highlightbackground="#BAC8BD",height=4)
        self.listbox.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(listframe, command=self.listbox.yview)
        scroll.pack(side="right", fill="y")
        self.listbox.configure(yscrollcommand=scroll.set)
        self.listbox.bind("<<ListboxSelect>>", self.choose)
        ttk.Button(left, text="查看识别内容", command=self.inspect_ocr).pack(before=listframe,side="bottom",fill="x", pady=(8, 0))
        right = ttk.Frame(body)
        body.add(right, minsize=340)
        self.question_label = ttk.Label(right, text="等待观众提问", font=(FONT, 16, "bold"), wraplength=570)
        self.question_label.pack(fill="x", pady=(0, 10))
        right.bind("<Configure>", lambda e: self.question_label.configure(wraplength=max(260,e.width-12)))
        self.answer_text = tk.Text(right, bg="#FCFAF4", fg=INK, font=(FONT, 21), wrap="word", relief="flat",height=6,
            padx=18, pady=14, spacing1=4, spacing3=8, highlightthickness=1,
            highlightbackground="#BAC8BD", state="disabled")
        self.answer_text.pack(fill="both", expand=True)
        actions = ttk.Frame(right)
        actions.pack(before=self.answer_text,side="bottom",fill="x", pady=(8, 0))
        for text, action in [("上一条", lambda: self.step(-1)), ("下一条", lambda: self.step(1)),
                             ("重试当前问题", self.retry)]:
            ttk.Button(actions, text=text, command=action).pack(side="left", padx=(0, 7))
        bottom = ttk.Frame(root)
        bottom.grid(row=4,column=0,sticky="ew",padx=24,pady=(14,10))
        self.manual = ttk.Entry(bottom, font=(FONT, 12))
        self.manual.pack(side="left", fill="x", expand=True, ipady=7)
        self.manual.bind("<Return>", lambda e: self.submit())
        ttk.Button(bottom, text="手动补充问题", command=self.submit).pack(side="right", padx=(10,0))
        self.status_label = tk.Label(root, text="", bg=PAPER, fg=MUTED, font=(FONT, 11), anchor="w", justify="left", wraplength=980)
        self.status_label.grid(row=5,column=0,sticky="ew",padx=26,pady=(0,16))
        self.progress_label=ttk.Label(root,text="",foreground=MUTED,font=(FONT,10),wraplength=980)
        self.progress_label.grid(row=6,column=0,sticky="ew",padx=26,pady=(0,8))
        root.bind("<Configure>",lambda e:self.status_label.configure(wraplength=max(600,e.width-52)) if e.widget==root else None)
        self.status(self.config_warning or "先选择本地或云端模型，再选评论区域。默认会处理当前可见问题；无入队时会显示原因。")
        self.refresh()

    def status(self, text, error=False):
        self.status_label.configure(text=text, fg="#9B362D" if error else MUTED)
        if getattr(self,"settings_status",None) and self.settings_status.winfo_exists():
            self.settings_status.configure(text=text,foreground="#9B362D" if error else MUTED)

    def region_description(self):
        if not self.region:
            return "尚未选择弹幕区域；监听时请保持评论列表可见。"
        r = self.region
        return "弹幕区域：%s × %s 像素，位置 (%s, %s)；移动直播伴侣或改变缩放后请重新选择。" % (r["width"],r["height"],r["left"],r["top"])

    def selected_client(self, provider=None, model=None, warm=False):
        provider=provider or self.provider
        if provider=="ollama":
            return OllamaClient(model or self.local_model,endpoint=self.local_runtime.endpoint(),first_timeout=60 if warm else 30,total_timeout=90 if warm else 75)
        return DeepSeekClient()

    def settings(self):
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.lift()
            return
        win=self.settings_window=tk.Toplevel(self.root)
        win.title("模型与直播资料")
        win.geometry("740x730")
        win.minsize(640,640)
        frame=ttk.Frame(win,padding=20)
        frame.pack(fill="both",expand=True)
        frame.grid_columnconfigure(0,weight=1)
        frame.grid_rowconfigure(1,weight=1)
        ttk.Label(frame,text="选择回答方式",font=(FONT,16,"bold")).grid(row=0,column=0,sticky="w",pady=(0,12))
        notebook=ttk.Notebook(frame)
        notebook.grid(row=1,column=0,sticky="nsew")
        model_tab=ttk.Frame(notebook,padding=16)
        data_tab=ttk.Frame(notebook,padding=16)
        notebook.add(model_tab,text="模型连接")
        notebook.add(data_tab,text="直播资料")
        model_tab.grid_columnconfigure(0,weight=1)
        provider=ttk.Combobox(model_tab,values=["本地 Ollama","DeepSeek 云端"],state="readonly",font=(FONT,12))
        provider.set("本地 Ollama" if self.provider=="ollama" else "DeepSeek 云端")
        provider.grid(row=0,column=0,sticky="ew",pady=(0,16))
        ttk.Label(model_tab,text="本地模型名称").grid(row=1,column=0,sticky="w")
        model=ttk.Combobox(model_tab,values=["qwen3.5:2b","qwen3.5:4b","qwen3:1.7b"],font=(FONT,12))
        model.set(self.local_model)
        model.grid(row=2,column=0,sticky="ew",pady=(6,8))
        help_text=("已内置 Qwen3.5 2B 和 4B，选择后点测试连接即可。\n内置服务会自动启动；切换模型时只保留一个模型在内存中。" if self.local_runtime.bundled else
            "当前为轻量包：需安装 Ollama 并下载所选模型。\n完整离线包已包含 2B、4B 和本地运行组件，见 GitHub 下载页。")
        ttk.Label(model_tab,text=help_text+"\n本地模式只连接本机，不自动回退云端。",foreground=MUTED,wraplength=620).grid(row=3,column=0,sticky="w",pady=(0,12))
        ttk.Button(model_tab,text="打开 Ollama Windows 下载页",command=lambda:webbrowser.open("https://ollama.com/download/windows")).grid(row=4,column=0,sticky="w",pady=(0,20))
        ttk.Label(model_tab,text="DeepSeek API Key（只有云端模式需要）").grid(row=5,column=0,sticky="w")
        key=ttk.Entry(model_tab,show="*",font=(FONT,12))
        key.insert(0,self.key)
        key.grid(row=6,column=0,sticky="ew",pady=(6,8),ipady=5)
        ttk.Label(model_tab,text="密钥仅本次运行有效，不写入设置文件。",foreground=MUTED,font=(FONT,10)).grid(row=7,column=0,sticky="w")
        ttk.Button(model_tab,text="打开 DeepSeek 密钥页",command=lambda:webbrowser.open("https://platform.deepseek.com/api_keys")).grid(row=8,column=0,sticky="w",pady=(10,16))
        def chosen():
            return "ollama" if provider.get()=="本地 Ollama" else "deepseek"
        ttk.Button(model_tab,text="测试连接 / 预热本地模型",command=lambda:self.test_connection(key.get().strip(),chosen(),model.get().strip())).grid(row=9,column=0,sticky="ew",pady=(6,10))
        ttk.Label(model_tab,text="首次加载模型可能较慢；测试成功后模型保留在内存 10 分钟。\n云端测试会产生少量 API 用量。",foreground=MUTED,font=(FONT,10),wraplength=620).grid(row=10,column=0,sticky="w")
        local_controls=[widget for row in range(1,5) for widget in model_tab.grid_slaves(row=row)]
        cloud_controls=[widget for row in range(5,9) for widget in model_tab.grid_slaves(row=row)]
        def mode_changed(event=None):
            for widget in local_controls:
                widget.grid() if chosen()=="ollama" else widget.grid_remove()
            for widget in cloud_controls:
                widget.grid() if chosen()=="deepseek" else widget.grid_remove()
        provider.bind("<<ComboboxSelected>>",mode_changed)
        mode_changed()
        data_tab.grid_columnconfigure(0,weight=1)
        data_tab.grid_rowconfigure(3,weight=1)
        ttk.Label(data_tab,text="直播主题").grid(row=0,column=0,sticky="w")
        topic=ttk.Entry(data_tab,font=(FONT,12))
        topic.insert(0,self.topic)
        topic.grid(row=1,column=0,sticky="ew",pady=(6,14),ipady=5)
        ttk.Label(data_tab,text="真实参考资料；固定问答可按“问：问题”换行“答：确认过的答案”填写",wraplength=620).grid(row=2,column=0,sticky="w")
        context=tk.Text(data_tab,height=5,font=(FONT,12),wrap="word",padx=10,pady=10)
        context.insert("1.0",self.context)
        context.grid(row=3,column=0,sticky="nsew",pady=(6,12))
        only=tk.BooleanVar(value=self.only_questions)
        existing=tk.BooleanVar(value=self.process_existing)
        ttk.Checkbutton(data_tab,text="只处理疑问句（陈述式提问可关闭）",variable=only).grid(row=4,column=0,sticky="w")
        ttk.Checkbutton(data_tab,text="启动监听时处理当前可见问题",variable=existing).grid(row=5,column=0,sticky="w",pady=(8,8))
        row=ttk.Frame(data_tab)
        row.grid(row=6,column=0,sticky="ew",pady=(8,0))
        ttk.Label(row,text="识别间隔（秒，1 到 10）").pack(side="left")
        interval=ttk.Spinbox(row,from_=1,to=10,increment=.5,width=6)
        interval.set(self.interval)
        interval.pack(side="left",padx=10)
        self.settings_status=ttk.Label(frame,text="请先测试连接，再应用设置。",foreground=MUTED,wraplength=660,font=(FONT,10))
        self.settings_status.grid(row=2,column=0,sticky="ew",pady=(12,8))
        def save():
            try:
                value=float(interval.get())
                if not 1<=value<=10:
                    raise ValueError()
                if chosen()=="ollama":
                    OllamaClient(model.get().strip())
            except (ValueError,ApiError) as exc:
                messagebox.showerror("设置无效",str(exc) if isinstance(exc,ApiError) else "请输入 1 到 10 之间的识别间隔。",parent=win)
                return
            if len(context.get("1.0","end-1c"))>12000:
                messagebox.showerror("资料过长","参考资料请控制在 12000 字以内；本地生成建议先精简到 3000 字以内。",parent=win)
                return
            self.provider=chosen()
            self.local_model=model.get().strip()
            self.key=key.get().strip()
            self.topic=topic.get()[:300]
            self.context=context.get("1.0","end-1c")
            self.only_questions=only.get()
            self.process_existing=existing.get()
            self.interval=value
            self.save_config()
            win.destroy()
            self.status("设置已应用。先手动输入一个问题测试，再开始监听；本地模式不会自动转发到云端。")
        ttk.Button(frame,text="应用设置",style="Accent.TButton",command=save).grid(row=3,column=0,sticky="e",pady=(6,0))

    def test_connection(self,key,provider=None,model=None):
        if self.demo:
            self.status("演示模式不会连接模型。")
            return
        if self.test_busy or self.active is not None:
            self.status("正在生成回答，请完成后再测试连接。")
            return
        provider=provider or self.provider
        model=model or self.local_model
        if provider=="deepseek" and not key:
            self.status("云端模式需要填写 DeepSeek API Key；本地模式不需要。",True)
            return
        self.test_busy=True
        self.test_started=time.monotonic()
        self.status("正在测试并预热本地模型…" if provider=="ollama" else "正在测试 DeepSeek 连接…")
        def work():
            try:
                client=self.selected_client(provider,model,warm=True)
                parts=[]
                first=-1.0
                for part in client.stream(key,"请只回复：连接成功。","","",threading.Event()):
                    if first<0:
                        first=time.monotonic()-self.test_started
                    parts.append(part)
                text="".join(parts)
                elapsed=time.monotonic()-self.test_started
                self.events.put(("test",True,"连接成功：首字 %.1f 秒，完整回答 %.1f 秒。请应用设置。"%(first,elapsed) if text else "未收到回答。"))
                LOG.info("connection test passed provider=%s seconds=%.1f",provider,elapsed)
            except Exception as exc:
                self.events.put(("test",False,str(exc) if isinstance(exc,ApiError) else "连接失败，请检查模型服务。"))
                LOG.info("connection test failed provider=%s type=%s",provider,type(exc).__name__)
        threading.Thread(target=work,daemon=True).start()

    def select_region(self):
        self.pause()
        self.root.withdraw()
        if self.prompter:
            self.prompter.withdraw()
        self.root.after(400, self.open_region_picker)

    def open_region_picker(self):
        try:
            import mss
            from PIL import Image, ImageTk
            with mss.mss() as capture:
                monitor = dict(capture.monitors[0])
                shot = capture.grab(monitor)
                image = Image.frombytes("RGB", shot.size, shot.rgb)
            scale = min(1000/image.width,600/image.height,1)
            photo = ImageTk.PhotoImage(image.resize((round(image.width*scale),round(image.height*scale))))
        except Exception:
            self.root.deiconify()
            self.status("无法读取屏幕。请检查依赖和屏幕录制权限，再选择弹幕区域。",True)
            return
        picker = tk.Toplevel(self.root)
        picker.title("在截图中框选弹幕文字区域")
        picker.resizable(False,False)
        ttk.Label(picker,text="拖动鼠标框选评论内容。尽量避开人数、礼物、标题和输入框。",padding=12).pack(fill="x")
        canvas = tk.Canvas(picker,width=photo.width(),height=photo.height(),highlightthickness=0,cursor="crosshair")
        canvas.pack()
        canvas.create_image(0,0,image=photo,anchor="nw")
        canvas.photo = photo
        note = ttk.Label(picker,text="在截图中按下鼠标并拖动。",padding=10)
        note.pack(fill="x")
        selection = {"start":None,"rect":None,"region":None}
        def down(e):
            selection["start"] = (max(0,min(e.x,photo.width())),max(0,min(e.y,photo.height())))
            if selection["rect"]:
                canvas.delete(selection["rect"])
            selection["rect"] = canvas.create_rectangle(e.x,e.y,e.x,e.y,outline="#D54B2F",width=3)
            selection["region"] = None
        def drag(e):
            if selection["start"]:
                x,y=selection["start"]
                canvas.coords(selection["rect"],x,y,max(0,min(e.x,photo.width())),max(0,min(e.y,photo.height())))
        def up(e):
            if not selection["start"]:
                return
            drag(e)
            x1,y1,x2,y2=canvas.coords(selection["rect"])
            r={"left":monitor["left"]+round(min(x1,x2)/scale),"top":monitor["top"]+round(min(y1,y2)/scale),
               "width":round(abs(x2-x1)/scale),"height":round(abs(y2-y1)/scale)}
            if valid_region(r):
                selection["region"]=r
                note.configure(text="已选择 %s × %s 像素。"%(r["width"],r["height"]))
            else:
                note.configure(text="区域太小，请重新拖动选择。")
        def finish(apply=False):
            if apply and not selection["region"]:
                return
            if apply:
                self.region=selection["region"]
                self.save_config()
            picker.destroy()
            self.root.deiconify()
            self.region_label.configure(text=self.region_description())
            self.status("区域已更新。请把助手和提词窗口移到弹幕区域之外，再点击开始监听。" if apply else "已取消选择。")
        canvas.bind("<ButtonPress-1>",down)
        canvas.bind("<B1-Motion>",drag)
        canvas.bind("<ButtonRelease-1>",up)
        bar=ttk.Frame(picker,padding=10)
        bar.pack(fill="x")
        ttk.Button(bar,text="使用这块区域",style="Accent.TButton",command=lambda:finish(True)).pack(side="right")
        ttk.Button(bar,text="取消",command=finish).pack(side="right",padx=8)
        picker.protocol("WM_DELETE_WINDOW",finish)
        picker.bind("<Escape>",lambda e:finish())

    def start(self):
        if self.demo:
            self.status("演示模式不会采集屏幕或调用 API。")
            return
        if not self.region:
            self.select_region()
            return
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.status("监听线程仍在运行或停止中，请稍候再试。")
            return
        self.generating=True
        self.monitor_stop=threading.Event()
        self.monitor_epoch+=1
        epoch=self.monitor_epoch
        stop=self.monitor_stop
        region=dict(self.region)
        self.start_button.configure(state="disabled")
        self.status("正在初始化本地文字识别，首次启动可能需要下载识别模型…")
        def work():
            try:
                import mss
                reader=ScreenReader()
                first=True
                blocked=False
                with mss.mss() as capture:
                    while not stop.is_set():
                        if self.capture_blocked.is_set():
                            if not blocked:
                                self.events.put(("monitor_status",epoch,"助手或提词窗口遮住了弹幕区域，请移动窗口；生成队列仍可继续。"))
                            blocked=True
                            stop.wait(0.5)
                            continue
                        if blocked:
                            self.events.put(("monitor_status",epoch,"弹幕区域已恢复可见，继续监听。"))
                        blocked=False
                        lines=reader.read(capture,region)
                        if not stop.is_set():
                            self.events.put(("ocr",epoch,lines,first))
                        first=False
                        stop.wait(self.interval)
            except Exception as exc:
                if not stop.is_set():
                    detail=str(exc) if isinstance(exc,ValueError) else "请检查识别组件是否安装完整，以及模型是否能下载；然后重新选择区域。"
                    self.events.put(("monitor_error",epoch,"文字识别已停止。"+detail))
            finally:
                self.events.put(("monitor_end",epoch))
        self.monitor_thread=threading.Thread(target=work,daemon=True)
        self.monitor_thread.start()

    def reread(self):
        if self.demo:
            self.status("演示模式不读取屏幕。")
            return
        self.tracker=QuestionTracker()
        self.force_current=True
        self.generating=True
        if not self.monitor_thread or not self.monitor_thread.is_alive():
            self.start()
        else:
            self.status("已清除去重记录，下一帧重新读取当前可见问题；队列中已有的问题不会重复加入。")

    def pause(self):
        self.monitor_stop.set()
        self.monitor_epoch+=1
        self.generating=False
        self.cancel.set()
        self.start_button.configure(state="normal")
        self.status("已暂停监听和新回答生成；当前文字保留，未完成的问题可点击重试。")

    def append_question(self, question, source):
        if any(r.state in ("待生成","生成中") and normalise(r.question)==normalise(question) for r in self.records):
            return False
        if sum(r.state in ("待生成","生成中") for r in self.records)>=8:
            self.status("待处理问题已达到 8 条，新问题暂未入队；可稍后手动补充。",True)
            return False
        self.records.append(Answer(question,source))
        if self.current is None:
            self.current=len(self.records)-1
        self.refresh()
        return True

    def submit(self):
        text=self.manual.get().strip()
        if not text:
            return
        if self.demo:
            self.status("演示模式仅展示固定示例。")
            return
        if len(text)>600:
            self.status("问题请控制在 600 字以内。",True)
            return
        if self.append_question(text,"手动"):
            self.current=len(self.records)-1
            self.manual.delete(0,"end")
            self.generating=True
            self.refresh()

    def retry(self):
        if self.current is None or self.demo:
            return
        item=self.records[self.current]
        if item.state=="生成中":
            self.status("当前问题正在生成，请稍候。")
            return
        item.text=""
        item.error=""
        item.state="待生成"
        item.first_s=-1.0
        item.elapsed_s=0.0
        self.generating=True
        self.refresh()

    def choose(self,event=None):
        selection=self.listbox.curselection()
        if selection:
            self.current=selection[0]
            self.refresh_answer()

    def step(self,direction):
        if not self.records:
            return
        self.current=max(0,min(len(self.records)-1,(self.current or 0)+direction))
        self.refresh()

    def resize_font(self,delta):
        self.fontsize=max(18,min(52,self.fontsize+delta))
        if self.prompter:
            self.prompter.body.configure(font=(FONT,self.fontsize))
        self.save_config()

    def show_prompter(self):
        if self.prompter is None or not self.prompter.winfo_exists():
            self.prompter=Prompter(self)
        self.prompter.deiconify()
        self.prompter.lift()
        self.refresh_answer()

    def inspect_ocr(self):
        win=tk.Toplevel(self.root)
        win.title("最近一次屏幕识别内容 · 不会保存到文件")
        win.geometry("640x460")
        text=tk.Text(win,font=(FONT,13),wrap="word",padx=16,pady=16)
        text.pack(fill="both",expand=True)
        text.insert("1.0","\n".join(self.last_ocr) or "尚未识别到文字。请开始监听，并保持弹幕列表可见。")
        text.configure(state="disabled")

    def set_text(self,widget,text):
        if widget.get("1.0","end-1c")==text:
            return
        pos=widget.yview()[0]
        widget.configure(state="normal")
        widget.delete("1.0","end")
        widget.insert("1.0",text)
        widget.configure(state="disabled")
        widget.yview_moveto(pos)

    def refresh(self):
        scroll=self.listbox.yview()[0]
        self.listbox.delete(0,"end")
        for item in self.records:
            self.listbox.insert("end", "[%s] %s"%(item.state,item.question))
        if self.current is not None:
            self.listbox.selection_set(self.current)
        self.listbox.yview_moveto(scroll)
        pending=sum(r.state in ("待生成","生成中") for r in self.records)
        self.count_label.configure(text="问题队列 · %s 条 / 等待 %s 条"%(len(self.records),pending))
        self.refresh_answer()

    def refresh_answer(self):
        changed_selection=self.current!=self.rendered_current
        self.rendered_current=self.current
        item=self.records[self.current] if self.current is not None and self.current<len(self.records) else None
        question=item.question if item else "等待观众提问"
        content=(item.text or ("正在等待模型首字，等待时间见下方状态…" if item.state=="生成中" else "等待生成…")) if item else "先在模型设置中选择本地 Ollama 或 DeepSeek，再选择评论区域。\n\n先手动输入问题验证连接。默认读取当前可见问题，重复测试可点“重读当前弹幕”。"
        if item and item.state=="待生成":
            ahead=sum(r.state in ("待生成","生成中") for r in self.records[:self.current])
            content="前面还有 %s 条问题，请稍候。"%ahead if self.generating else "生成已暂停。点击开始监听或重试当前问题。"
        if item and item.error:
            content+="\n\n【回答未完成】"+item.error
        self.question_label.configure(text=question)
        self.set_text(self.answer_text,content)
        if changed_selection:
            self.answer_text.yview_moveto(0)
        if self.prompter and self.prompter.winfo_exists():
            self.prompter.question.configure(text=question)
            self.set_text(self.prompter.body,content)
            if changed_selection:
                self.prompter.body.yview_moveto(0)
            ready=sum(r.state=="已完成" for r in self.records[(self.current or 0)+1:])
            detail=(item.state+" · "+item.engine) if item else "等待问题"
            if item and item.first_s>=0:
                detail+=" · 首字 %.1f 秒"%item.first_s
            self.prompter.foot.configure(text=detail+" · 后面已完成 %s 条；读完点下一条。"%ready,wraplength=max(300,self.prompter.winfo_width()-48))

    def check_overlap(self):
        blocked=False
        if self.region:
            r=self.region
            target=(r["left"],r["top"],r["left"]+r["width"],r["top"]+r["height"])
            for win in [self.root]+[w for w in self.root.winfo_children() if isinstance(w,tk.Toplevel)]:
                if win and win.winfo_exists() and win.state()=="normal":
                    rect=(win.winfo_rootx()-8,win.winfo_rooty()-30,
                          win.winfo_rootx()+win.winfo_width()+8,win.winfo_rooty()+win.winfo_height()+8)
                    blocked=blocked or overlaps(target,rect)
        self.capture_blocked.set() if blocked else self.capture_blocked.clear()

    def dispatch(self):
        if not self.generating or self.active is not None or self.test_busy or self.demo or time.monotonic()<self.next_request_at:
            return
        index=next((i for i,item in enumerate(self.records) if item.state=="待生成"),None)
        if self.current is not None and self.records[self.current].state=="待生成":
            index=self.current
        if index is None:
            return
        self.active=index
        item=self.records[index]
        item.state="生成中"
        item.text=""
        item.error=""
        item.started=time.monotonic()
        item.first_s=-1.0
        item.elapsed_s=0.0
        preset=local_answer(item.question,self.context)
        if preset is not None:
            item.text=preset
            item.state="已完成"
            item.engine="本地固定问答"
            item.first_s=0.0
            item.elapsed_s=time.monotonic()-item.started
            self.active=None
            self.refresh()
            LOG.info("local preset answered id=%s",index)
            return
        provider,model=self.provider,self.local_model
        item.engine=("Ollama / "+model) if provider=="ollama" else "DeepSeek"
        self.cancel=threading.Event()
        cancel=self.cancel
        key,topic,context=self.key,self.topic,self.context
        self.refresh()
        LOG.info("request started provider=%s id=%s",provider,index)
        def work():
            try:
                client=self.selected_client(provider,model)
                for part in client.stream(key,item.question,topic,context,cancel):
                    self.events.put(("delta",index,part))
                self.events.put(("done",index))
            except Cancelled:
                self.events.put(("cancelled",index))
            except Exception as exc:
                text=str(exc) if isinstance(exc,ApiError) else "回答服务异常，请检查网络后重试。"
                self.events.put(("answer_error",index,text))
        threading.Thread(target=work,daemon=True).start()

    def handle_ocr(self,lines,first=False):
        self.last_ocr=lines
        baseline=first and not self.process_existing and not self.force_current
        fresh=self.tracker.ingest(lines,self.only_questions,baseline=baseline)
        self.force_current=False
        accepted=sum(self.append_question(q,"弹幕") for q in fresh)
        stats=self.tracker.stats
        if baseline:
            hint="已按设置跳过启动画面；需要时点重读当前弹幕。"
        elif not lines:
            hint="没有读到文字，请检查框选区域或窗口遮挡。"
        elif stats["duplicate"]:
            hint="相同问题已去重；重复测试请点重读当前弹幕。"
        elif not fresh:
            hint="没有疑问句；可关闭疑问句筛选或手动补充。"
        else:
            hint="新问题已加入队列。" if accepted else "队列已有相同问题或已满。"
        self.status("识别 %s 条，过滤 %s 条，重复 %s 条，本帧入队 %s 条。%s"%(stats["read"],stats["filtered"],stats["duplicate"],accepted,hint))

    def poll_once(self):
        changed=False
        try:
            for _ in range(300):
                event=self.events.get_nowait()
                kind=event[0]
                if kind in ("ocr","monitor_status","monitor_error","monitor_end") and event[1]!=self.monitor_epoch:
                    continue
                if kind=="ocr":
                    self.handle_ocr(event[2],event[3])
                elif kind=="monitor_status":
                    self.status(event[2])
                elif kind=="monitor_error":
                    self.pause()
                    self.status(event[2],True)
                elif kind=="monitor_end":
                    self.start_button.configure(state="normal")
                elif kind=="delta" and event[1]==self.active:
                    if not self.cancel.is_set():
                        self.records[event[1]].text+=event[2]
                        if self.records[event[1]].first_s<0:
                            self.records[event[1]].first_s=time.monotonic()-self.records[event[1]].started
                        changed=True
                elif kind in ("done","cancelled","answer_error") and event[1]==self.active:
                    item=self.records[event[1]]
                    item.elapsed_s=time.monotonic()-item.started
                    if kind=="done" and not self.cancel.is_set():
                        item.state="已完成"
                    elif kind=="cancelled" or self.cancel.is_set():
                        item.state="待重试"
                        item.error="生成已暂停，点击重试可重新生成。"
                    else:
                        item.state="失败"
                        item.error=event[2]
                        self.pause()
                        self.status(event[2]+" 已暂停，检查后点击重试当前问题。",True)
                    self.active=None
                    LOG.info("request ended id=%s state=%s first=%.2f seconds=%.2f",event[1],item.state,item.first_s,item.elapsed_s)
                    self.next_request_at=time.monotonic()+0.2
                    changed=True
                elif kind=="test":
                    self.test_busy=False
                    self.status(event[2],not event[1])
        except queue.Empty:
            pass
        if changed:
            self.refresh()
        self.check_overlap()
        self.dispatch()

    def refresh_progress(self):
        provider="本地 Ollama / "+self.local_model if self.provider=="ollama" else "DeepSeek 云端"
        if self.test_busy:
            detail="正在测试 / 预热，已等待 %.0f 秒"%(time.monotonic()-self.test_started)
        elif self.active is not None:
            item=self.records[self.active]
            detail=("正在取消请求" if self.cancel.is_set() else "等待首字" if item.first_s<0 else "逐字生成中")+"，已用 %.0f 秒"%(time.monotonic()-item.started)
        else:
            pending=sum(r.state=="待生成" for r in self.records)
            detail=("等待 %s 条"%pending) if self.generating else "生成已暂停"
        self.progress_label.configure(text=provider+" · "+detail)

    def poll(self):
        try:
            self.poll_once()
            self.refresh_progress()
        except Exception:
            LOG.exception("GUI polling failed; generation stopped")
            self.generating=False
            self.monitor_stop.set()
            self.cancel.set()
            self.status("界面处理发生错误，生成已停止。诊断记录位于设置文件旁的 diagnostics.log；请手动重试。",True)
        finally:
            self.root.after(100,self.poll)

    def close(self):
        self.monitor_stop.set()
        self.cancel.set()
        self.save_config()
        self.local_runtime.close()
        self.root.destroy()


def main():
    if "--check-models" in sys.argv:
        from local_runtime import check_models
        index=sys.argv.index("--check-models")
        raise SystemExit(check_models(sys.argv[index+1]))
    if "--self-check" in sys.argv:
        from selfcheck import run
        index=sys.argv.index("--self-check")
        if index+1>=len(sys.argv):
            raise SystemExit(2)
        raise SystemExit(run(sys.argv[index+1]))
    root=tk.Tk()
    Assistant(root,demo="--demo" in sys.argv)
    root.mainloop()


if __name__=="__main__":
    main()
