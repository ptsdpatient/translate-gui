import json
import re
import time
import requests
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import threading

LIBRE_URL = "http://localhost:5000"

ALL_LANGS = {
    "es": "Spanish",
    "pt": "Portuguese",
    "fr": "French",
    "de": "German",
    "ru": "Russian",
    "tr": "Turkish",
    "pl": "Polish",
    "it": "Italian",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "th": "Thai",
    "vi": "Vietnamese",
    "id": "Indonesian",
    "hi": "Hindi",
    "ar": "Arabic",
}

DEFAULT_LANGS = [
    "es","pt","fr","de","ru",
    "tr","pl","it",
    "zh","ja","ko",
    "th","vi","id",
    "hi","ar"
]

SKIP_TOP_KEYS = {"Digits"}
PLACEHOLDER_RE = re.compile(r"\{[^}]+\}")

# ---------- TRANSLATION ----------

def libre_translate(text: str, source="en", target="hi") -> str:
    placeholders = PLACEHOLDER_RE.findall(text)
    temp = text
    mapping = {}

    for i, ph in enumerate(placeholders):
        token = f"__PH_{i}__"
        mapping[token] = ph
        temp = temp.replace(ph, token)

    resp = requests.post(
        f"{LIBRE_URL}/translate",
        json={
            "q": temp,
            "source": source,
            "target": target,
            "format": "text",
        },
        timeout=120,
    )

    resp.raise_for_status()
    out = resp.json()["translatedText"]

    for token, ph in mapping.items():
        out = out.replace(token, ph)

    return out


def translate_values(obj, target_lang: str):
    if isinstance(obj, dict):
        return {
            k: (v if k in SKIP_TOP_KEYS else translate_values(v, target_lang))
            for k, v in obj.items()
        }

    if isinstance(obj, list):
        return [translate_values(x, target_lang) for x in obj]

    if isinstance(obj, str):
        if obj.strip() == "" or obj.isdigit():
            return obj
        time.sleep(0.05)
        return libre_translate(obj, target=target_lang)

    return obj


# ---------- GUI ----------

class TranslatorGUI:
    def __init__(self, root):
        self.root = root
        root.title("JSON Translator")
        root.geometry("900x650")
        root.configure(bg="#2b2d31")

        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()

        self.build_top()
        self.build_languages()
        self.build_bottom()

    # ---------- TOP ----------
    def build_top(self):
        top = tk.Frame(self.root, bg="#2b2d31")
        top.pack(fill="x", padx=12, pady=10)

        # Input
        left = tk.Frame(top, bg="#2b2d31")
        left.pack(side="left", expand=True, fill="x", padx=(0,8))

        tk.Label(left, text="Input JSON", fg="white", bg="#2b2d31").pack(anchor="w")

        tk.Entry(left, textvariable=self.input_path, bg="#1e1f22", fg="white",
                 insertbackground="white").pack(fill="x", pady=4)

        tk.Button(left, text="Browse", command=self.browse_input,
                  bg="#5865F2", fg="white").pack(anchor="w")

        # Output
        right = tk.Frame(top, bg="#2b2d31")
        right.pack(side="left", expand=True, fill="x")

        tk.Label(right, text="Output Folder", fg="white", bg="#2b2d31").pack(anchor="w")

        tk.Entry(right, textvariable=self.output_path, bg="#1e1f22", fg="white",
                 insertbackground="white").pack(fill="x", pady=4)

        tk.Button(right, text="Browse", command=self.browse_output,
                  bg="#5865F2", fg="white").pack(anchor="w")

    # ---------- LANG GRID ----------
    def build_languages(self):
        container = tk.Frame(self.root, bg="#2b2d31")
        container.pack(fill="both", expand=True, padx=12)

        tk.Label(container, text="Languages",
                 fg="white", bg="#2b2d31",
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0,6))

        # scroll
        canvas = tk.Canvas(container, bg="#2b2d31", highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)

        self.lang_frame = tk.Frame(canvas, bg="#2b2d31")

        self.lang_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.lang_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # grid checkboxes
        self.lang_vars = {}
        cols = 4

        for i, (code, name) in enumerate(ALL_LANGS.items()):
            var = tk.BooleanVar(value=code in DEFAULT_LANGS)
            self.lang_vars[code] = var

            cb = tk.Checkbutton(
                self.lang_frame,
                text=f"{name} ({code})",
                variable=var,
                bg="#1e1f22",
                fg="white",
                selectcolor="#5865F2",
                activebackground="#1e1f22",
                activeforeground="white",
                padx=8,
                pady=6
            )

            r = i // cols
            c = i % cols
            cb.grid(row=r, column=c, sticky="ew", padx=6, pady=6)

        for c in range(cols):
            self.lang_frame.grid_columnconfigure(c, weight=1)

    # ---------- BOTTOM ----------
    def build_bottom(self):
        bottom = tk.Frame(self.root, bg="#2b2d31")
        bottom.pack(fill="x", padx=12, pady=10)

        tk.Button(
            bottom,
            text="Translate",
            command=self.start,
            bg="#23a559",
            fg="white",
            font=("Segoe UI", 11, "bold"),
            height=2
        ).pack(fill="x")

        self.log = tk.Text(
            self.root,
            height=8,
            bg="#1e1f22",
            fg="white",
            insertbackground="white"
        )
        self.log.pack(fill="both", expand=False, padx=12, pady=(0,10))

    # ---------- actions ----------
    def browse_input(self):
        file = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if file:
            self.input_path.set(file)

    def browse_output(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_path.set(folder)

    def log_write(self, msg):
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.root.update()

    def start(self):
        threading.Thread(target=self.run).start()

    def run(self):
        try:
            input_file = self.input_path.get()
            out_dir = Path(self.output_path.get())

            langs = [k for k,v in self.lang_vars.items() if v.get()]

            with open(input_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for lang in langs:
                self.log_write(f"Translating {lang}...")
                translated = translate_values(data, lang)

                out_file = out_dir / f"{lang}.json"

                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(translated, f, ensure_ascii=False, indent=2)

                self.log_write(f"Saved {out_file}")

            self.log_write("Done!")

        except Exception as e:
            messagebox.showerror("Error", str(e))


root = tk.Tk()
TranslatorGUI(root)
root.mainloop()