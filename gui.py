import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import threading
import subprocess
import sys
import os
import secrets
import string
from pathlib import Path
import time
from PIL import Image, ImageTk, ImageSequence

# ====================== Code.gs Template ======================
GOOGLE_SCRIPT_CODE_TEMPLATE = r"""/**
 * BlackLotus - Domain Fronting Relay
 * Developed for https://github.com/Expen1
 */

const AUTH_KEY = "{AUTH_KEY}";

const SKIP_HEADERS = {
  "host": true, "connection": true, "content-length": true,
  "transfer-encoding": true, "proxy-connection": true, "proxy-authorization": true
};

function doPost(e) {
  try {
    const req = JSON.parse(e.postData.contents);
    if (req.k !== AUTH_KEY) return _json({ e: "unauthorized" });
    if (Array.isArray(req.q)) return _doBatch(req.q);
    return _doSingle(req);
  } catch (err) { return _json({ e: String(err) }); }
}

function _doSingle(req) {
  if (!req.u || typeof req.u !== "string" || !req.u.match(/^https?:\/\//i)) return _json({ e: "bad url" });
  const opts = _buildOpts(req);
  const resp = UrlFetchApp.fetch(req.u, opts);
  return _json({ s: resp.getResponseCode(), h: resp.getHeaders(), b: Utilities.base64Encode(resp.getContent()) });
}

function _doBatch(items) {
  const results = [];
  for (let item of items) {
    try { results.push(_doSingle(item)); } 
    catch (err) { results.push({ e: String(err) }); }
  }
  return _json(results);
}

function _buildOpts(req) {
  const opts = { method: req.m || "GET", headers: {} };
  if (req.h) {
    for (let [k, v] of Object.entries(req.h)) {
      if (!SKIP_HEADERS[k.toLowerCase()]) opts.headers[k] = v;
    }
  }
  if (req.b) opts.payload = Utilities.base64Decode(req.b);
  return opts;
}

function doGet(e) {
  return HtmlService.createHtmlOutput("<h1>✅ BlackLotus Relay is Running</h1>");
}

function _json(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
"""

class AnimatedGIF:
    def __init__(self, label, gif_path, width=760, height=420):
        self.label = label
        self.frames = []
        self.delay = 100
        self.is_running = True
        try:
            im = Image.open(gif_path)
            for frame in ImageSequence.Iterator(im):
                resized = frame.copy().convert('RGBA').resize((width, height), Image.LANCZOS)
                self.frames.append(ImageTk.PhotoImage(resized))
            if "duration" in im.info:
                self.delay = im.info["duration"]
        except: pass
        self.index = 0
        if self.frames: self.animate()

    def animate(self):
        if not self.is_running or not self.frames: return
        self.label.config(image=self.frames[self.index])
        self.index = (self.index + 1) % len(self.frames)
        self.label.after(self.delay, self.animate)

    def stop(self): self.is_running = False


class BlackLotusGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("BlackLotus Ver - Domain Fronting")
        self.root.geometry("1160x790")
        self.root.configure(bg="#0a0a0a")
        self.root.resizable(False, False)

        self.config_path = Path("config.json")
        self.proxy_process = None
        self.running = False
        self.gif_animation = None

        self.create_styles()
        self.create_ui()
        self.load_config()
        self.root.after(600, self.draw_traffic_route)

    def create_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TNotebook.Tab", padding=[35, 18], font=("Segoe UI", 13, "bold"))
        style.map("TNotebook.Tab", background=[("selected", "#a855f7")], foreground=[("selected", "white")])
        style.configure("Primary.TButton", font=("Segoe UI", 13, "bold"), padding=(32, 16))
        style.configure("Success.TButton", font=("Segoe UI", 13, "bold"), padding=(32, 16))
        style.configure("Danger.TButton", font=("Segoe UI", 13, "bold"), padding=(32, 16))
        style.configure("Warning.TButton", font=("Segoe UI", 13, "bold"), padding=(32, 16))

    def create_ui(self):
        # Header
        header = tk.Frame(self.root, bg="#111111", height=135)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="BLACK LOTUS", font=("Segoe UI", 32, "bold"), bg="#111111", fg="#a855f7").pack(pady=(25,0))
        tk.Label(header, text="github.com/Expen1 • t.me/NetLotus", 
                font=("Segoe UI", 15), bg="#111111", fg="#e0e0e0").pack()
        tk.Label(header, text="GitHub: Expen1  |  Telegram: @NetLotus", 
                font=("Segoe UI", 11), bg="#111111", fg="#64748b").pack(pady=2)

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=18, pady=13)

        # Tab 1: راهنما
        tab_guide = tk.Frame(notebook, bg="#0a0a0a")
        ttk.Button(tab_guide, text="📋 کپی کد Code.gs (با رمز شما)", command=self.copy_google_script, style="Success.TButton").pack(pady=20)
        notebook.add(tab_guide, text="راهنمای تصویری")
        gif_container = tk.Frame(tab_guide, bg="#1a1a1a", relief="solid", bd=4)
        gif_container.pack(pady=10, padx=10)
        self.gif_lbl = tk.Label(gif_container, bg="#000")
        self.gif_lbl.pack(padx=10, pady=10)
        if Path("gifs/script.gif").exists():
            self.gif_animation = AnimatedGIF(self.gif_lbl, "gifs/script.gif")


        # Tab 2: مسیر ترافیک
        tab_route = tk.Frame(notebook, bg="#0a0a0a")
        notebook.add(tab_route, text="🛣️ مسیر ترافیک")
        tk.Label(tab_route, text="مسیر عبور ترافیک شما", font=("Segoe UI", 24, "bold"), bg="#0a0a0a", fg="#a855f7").pack(pady=15)
        
        self.route_canvas = tk.Canvas(tab_route, bg="#111111", height=265, highlightthickness=0)
        self.route_canvas.pack(fill="x", padx=35, pady=10)
        self.route_canvas.bind("<Configure>", lambda e: self.draw_traffic_route())

        tk.Label(tab_route, text="مرورگر → پروکسی محلی → گوگل → رله Apps Script → سایت مقصد\nفیلتر فقط google.com را می‌بیند • بقیه کاملاً مخفی", 
                font=("Segoe UI", 11), bg="#0a0a0a", fg="#d1d5db", justify="center").pack(pady=8)

        # Tab 3: تنظیمات
        tab_settings = tk.Frame(notebook, bg="#0a0a0a")
        notebook.add(tab_settings, text="تنظیمات")
        container = tk.Frame(tab_settings, bg="#0a0a0a")
        container.pack(expand=True, fill="both", padx=55, pady=35)

        tk.Label(container, text="🔧 Script ID و Auth Key", font=("Segoe UI", 24, "bold"), bg="#0a0a0a", fg="#a855f7").pack(pady=20)

        tk.Label(container, text="Deployment ID:", bg="#0a0a0a", fg="#fff", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        self.script_id_var = tk.StringVar()
        tk.Entry(container, textvariable=self.script_id_var, font=("Consolas", 13), bg="#1f1f1f", fg="#fff").pack(fill="x", pady=8, ipady=9)

        tk.Label(container, text="Auth Key:", bg="#0a0a0a", fg="#fff", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        self.auth_key_var = tk.StringVar()
        tk.Entry(container, textvariable=self.auth_key_var, font=("Consolas", 13), bg="#1f1f1f", fg="#fff", show="•").pack(fill="x", pady=8, ipady=9)

        btn_frame = tk.Frame(container, bg="#0a0a0a")
        btn_frame.pack(pady=12)
        ttk.Button(btn_frame, text="🔑 تولید رمز قوی", command=self.generate_strong_key, style="Warning.TButton").pack(side="left", padx=10)
        ttk.Button(container, text="💾 ذخیره تنظیمات", command=self.save_config, style="Primary.TButton").pack(pady=20)

        # Tab 4: اجرا
        tab_run = tk.Frame(notebook, bg="#0a0a0a")
        notebook.add(tab_run, text="🚀 اجرا")
        run_frame = tk.Frame(tab_run, bg="#0a0a0a")
        run_frame.pack(expand=True, fill="both", padx=40, pady=30)

        self.status_var = tk.StringVar(value="⏸️ آماده")
        tk.Label(run_frame, textvariable=self.status_var, font=("Segoe UI", 20, "bold"), bg="#0a0a0a", fg="#22c55e").pack(pady=15)

        btn_frame = tk.Frame(run_frame, bg="#0a0a0a")
        btn_frame.pack(pady=15)
        self.start_btn = ttk.Button(btn_frame, text="▶️ شروع پروکسی", command=self.start_proxy, style="Primary.TButton")
        self.start_btn.pack(side="left", padx=15)
        self.stop_btn = ttk.Button(btn_frame, text="⏹️ توقف", command=self.stop_proxy, state="disabled", style="Danger.TButton")
        self.stop_btn.pack(side="left", padx=15)

        extra_frame = tk.Frame(run_frame, bg="#0a0a0a")
        extra_frame.pack(pady=15)
        ttk.Button(extra_frame, text="🔍 اسکن بهترین IP", command=self.scan_google_ip, style="Primary.TButton").pack(side="left", padx=8)
        ttk.Button(extra_frame, text="🔐 نصب گواهی CA", command=self.install_cert, style="Primary.TButton").pack(side="left", padx=8)
        ttk.Button(extra_frame, text="🧪 تست اتصال", command=self.test_connection, style="Primary.TButton").pack(side="left", padx=8)
        ttk.Button(extra_frame, text="📁 باز کردن پوشه", command=self.open_folder, style="Primary.TButton").pack(side="left", padx=8)

        tk.Label(run_frame, text="📋 لاگ زنده", font=("Segoe UI", 13), bg="#0a0a0a", fg="#a855f7").pack(anchor="w", padx=40, pady=(25,5))
        self.log_area = scrolledtext.ScrolledText(run_frame, height=13, font=("Consolas", 11), bg="#111111", fg="#67e8f9")
        self.log_area.pack(fill="both", expand=True, padx=40, pady=5)

    def generate_strong_key(self):
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*_-+="
        key = ''.join(secrets.choice(alphabet) for _ in range(32))
        self.auth_key_var.set(key)
        self.log("🔑 رمز قوی ۳۲ کاراکتری تولید شد")
        messagebox.showinfo("✅", "رمز قوی تولید شد!\nحالا ذخیره کنید.")

    def test_connection(self):
        self.log("🧪 تست اتصال...")
        def run_test():
            try:
                result = subprocess.run([sys.executable, "main.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
                output = (result.stdout + result.stderr).lower()
                if "unauthorized" in output:
                    messagebox.showerror("❌", "ارور Auth Key!\nرمز در Code.gs و config.json باید یکی باشد.")
                else:
                    messagebox.showinfo("✅", "اتصال موفق به نظر می‌رسد!")
            except:
                self.log("⚠️ تست انجام شد (ممکن است proxy اجرا نباشد)")
        threading.Thread(target=run_test, daemon=True).start()

    def draw_traffic_route(self, event=None):
        c = self.route_canvas
        c.delete("all")
        w = c.winfo_width() or 1050
        colors = ["#ec4899", "#14b8a6", "#a855f7", "#f43f5e", "#22c55e"]
        labels = ["Browser", "Local Proxy", "Google Front", "Apps Script\nRelay", "Target Website"]
        step = (w - 220) // 5
        x = 65

        for i, (lbl, col) in enumerate(zip(labels, colors)):
            c.create_rectangle(x, 52, x + step - 18, 195, fill=col, outline="#1f2937", width=7)
            c.create_text(x + (step-18)//2, 123, text=lbl, fill="white", font=("Segoe UI", 11, "bold"), justify="center")
            if i > 0:
                c.create_line(x - 42, 123, x, 123, arrow=tk.LAST, fill="#facc15", width=8, arrowshape=(14, 18, 7))
            x += step + 38

        c.create_text(w//2, 235, text="فیلتر فقط google.com را می‌بیند • ترافیک واقعی مخفی است", 
                     fill="#9ca3af", font=("Segoe UI", 10, "bold"))

    def log(self, msg):
        self.log_area.config(state="normal")
        self.log_area.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.log_area.see(tk.END)
        self.log_area.config(state="disabled")

    def copy_google_script(self):
        auth_key = self.auth_key_var.get().strip()
        if not auth_key:
            messagebox.showwarning("⚠️", "ابتدا Auth Key را وارد کنید")
            return
        code = GOOGLE_SCRIPT_CODE_TEMPLATE.replace("{AUTH_KEY}", auth_key)
        self.root.clipboard_clear()
        self.root.clipboard_append(code)
        messagebox.showinfo("✅", "کد Code.gs با رمز شما کپی شد")

    def load_config(self):
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text(encoding="utf-8"))
                self.script_id_var.set(data.get("script_id", ""))
                self.auth_key_var.set(data.get("auth_key", ""))
                self.log("✅ تنظیمات بارگذاری شد")
            except: pass

    def save_config(self):
        if not self.script_id_var.get().strip() or not self.auth_key_var.get().strip():
            messagebox.showwarning("⚠️", "هر دو فیلد را پر کنید")
            return
        config = {
            "mode": "apps_script",
            "google_ip": "216.239.38.120",
            "front_domain": "www.google.com",
            "script_id": self.script_id_var.get().strip(),
            "auth_key": self.auth_key_var.get().strip(),
            "listen_host": "127.0.0.1",
            "listen_port": 8085,
            "socks5_enabled": True,
            "socks5_port": 1080,
            "log_level": "INFO",
            "verify_ssl": True
        }
        try:
            self.config_path.write_text(json.dumps(config, indent=4, ensure_ascii=False), encoding="utf-8")
            self.log("💾 تنظیمات ذخیره شد")
            messagebox.showinfo("✅", "تنظیمات ذخیره شد")
        except Exception as e:
            messagebox.showerror("❌", str(e))

    def start_proxy(self):
        if self.running: return
        self.running = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.status_var.set("● در حال اجرا...")

        def run():
            try:
                self.proxy_process = subprocess.Popen([sys.executable, "main.py"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
                for line in self.proxy_process.stdout:
                    if line.strip(): self.log(line.strip())
            except Exception as e:
                self.log(f"❌ {e}")

        threading.Thread(target=run, daemon=True).start()

    def stop_proxy(self):
        if self.proxy_process:
            self.proxy_process.terminate()
            self.proxy_process = None
        self.running = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.status_var.set("⏸️ متوقف شد")

    def install_cert(self):
        self.log("🔐 نصب گواهی...")
        try:
            result = subprocess.run([sys.executable, "main.py", "--install-cert"], capture_output=True, text=True, timeout=30)
            self.log(result.stdout or "Done")
            messagebox.showinfo("✅", "گواهی نصب شد")
        except Exception as e:
            messagebox.showerror("❌", str(e))

    def scan_google_ip(self):
        self.log("🔍 اسکن Google IP...")
        def run():
            try:
                result = subprocess.run([sys.executable, "main.py", "--scan"], capture_output=True, text=True, timeout=90)
                self.log(result.stdout)
            except Exception as e:
                self.log(f"خطا: {e}")
        threading.Thread(target=run, daemon=True).start()

    def open_folder(self):
        path = Path.cwd()
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.call(["open", path])
        else:
            subprocess.call(["xdg-open", path])

    def on_close(self):
        if self.running: self.stop_proxy()
        if self.gif_animation: self.gif_animation.stop()
        self.root.destroy()

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()


if __name__ == "__main__":
    app = BlackLotusGUI()
    app.run()