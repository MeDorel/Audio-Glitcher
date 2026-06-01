import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import random
import os
import threading

BG       = "#1a1a1a"
SURFACE  = "#242424"
SURFACE2 = "#2e2e2e"
ACCENT   = "#7c6fcd"
ACCENT2  = "#a89de0"
TEXT     = "#e8e8e8"
MUTED    = "#888888"
SUCCESS  = "#4caf7d"
DANGER   = "#e05c5c"
BORDER   = "#3a3a3a"

MODE_DESCS = {
    "random flip": "Randomly flips bits inside selected bytes — classic glitch crunch.",
    "increment":   "Adds a value to each byte (wraps at 255) — warps amplitude & pitch.",
    "zero out":    "Fills selected bytes with a value — creates digital dropouts & silences.",
    "shuffle":     "Randomly swaps byte pairs across the file — full waveform chaos.",
    "reverse":     "Reverses chunks of bytes in place — backward/warped sections.",
    "XOR":         "XORs every selected byte with a mask — deterministic but wild distortion.",
}

EXTRA_CONFIG = {
    "random flip": ("bits to flip per byte",   1,   8, 1,   1),
    "increment":   ("amount to add per byte",   1, 255, 1,  10),
    "zero out":    ("fill value (0=silence)",    0, 255, 1,   0),
    "shuffle":     ("swap window size (bytes)",  2,  64, 1,   8),
    "reverse":     ("reverse chunk length",      2, 512, 2,  16),
    "XOR":         ("XOR mask value (0-255)",    0, 255, 1, 128),
}

def corrupt_audio(data, mode, intensity, header_skip, extra, seed):
    data = bytearray(data)
    if seed != 0:
        random.seed(seed)
    total = len(data) - header_skip
    if total <= 0:
        return data
    num_corrupt = max(1, int(total * (intensity / 100)))
    num_corrupt = min(num_corrupt, total)
    indices = random.sample(range(header_skip, len(data)), num_corrupt)
    for i in indices:
        if mode == "random flip":
            for _ in range(extra):
                data[i] ^= (1 << random.randint(0, 7))
        elif mode == "increment":
            data[i] = (data[i] + extra) % 256
        elif mode == "zero out":
            data[i] = extra
        elif mode == "shuffle":
            j = random.randint(header_skip, len(data) - 1)
            data[i], data[j] = data[j], data[i]
        elif mode == "reverse":
            end = min(i + extra, len(data))
            data[i:end] = data[i:end][::-1]
        elif mode == "XOR":
            data[i] ^= extra
    return bytes(data)

class AudioGlitcher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("audio glitcher")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.geometry("520x740")

        self.input_path  = tk.StringVar()
        self.output_path = tk.StringVar()
        self.mode_var    = tk.StringVar(value="random flip")
        self.intensity   = tk.DoubleVar(value=5.0)
        self.header      = tk.IntVar(value=44)
        self.extra       = tk.IntVar(value=1)
        self.seed        = tk.IntVar(value=0)

        self._mode_btns      = {}
        self.mode_desc_lbl   = None
        self.extra_label_var = tk.StringVar(value="bits to flip per byte")
        self._extra_slider   = None
        self._extra_val_lbl  = None

        self._build_ui()
        self._set_mode("random flip")

    def _divider(self):
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x", padx=16, pady=10)

    def _section(self, text):
        tk.Label(self, text=text, font=("Helvetica", 10, "bold"),
                 bg=BG, fg=MUTED).pack(anchor="w", padx=16, pady=(4, 2))

    def _chaos_color(self, v):
        if v < 5:  return SUCCESS
        if v < 25: return "#e0b84c"
        if v < 60: return "#e07a4c"
        return DANGER

    def _pick_input(self):
        p = filedialog.askopenfilename(
            title="pick audio file",
            filetypes=[("Audio files", "*.wav *.mp3 *.ogg *.flac *.aiff *.raw"),
                       ("All files", "*.*")])
        if p:
            self.input_path.set(p)

    def _pick_output(self):
        p = filedialog.asksaveasfilename(
            title="save glitched file",
            filetypes=[("Audio files", "*.wav *.mp3 *.ogg *.flac"),
                       ("All files", "*.*")])
        if p:
            self.output_path.set(p)

    def _filepicker(self, var, cmd):
        frame = tk.Frame(self, bg=SURFACE, highlightbackground=BORDER,
                         highlightthickness=1)
        frame.pack(fill="x", padx=16, pady=(0, 8))
        tk.Entry(frame, textvariable=var, font=("Helvetica", 10),
                 bg=SURFACE, fg=TEXT, insertbackground=TEXT,
                 relief="flat", bd=6).pack(side="left", fill="x", expand=True)
        tk.Button(frame, text="browse", font=("Helvetica", 10),
                  bg=SURFACE2, fg=MUTED, relief="flat", bd=0,
                  padx=10, cursor="hand2", command=cmd).pack(side="right")

    def _slider(self, label, var, mn, mx, step, fmt, color_fn=None):
        frame = tk.Frame(self, bg=BG)
        frame.pack(fill="x", padx=16, pady=(0, 8))
        tk.Label(frame, text=label, font=("Helvetica", 10),
                 bg=BG, fg=MUTED).pack(anchor="w")
        row = tk.Frame(frame, bg=BG)
        row.pack(fill="x")
        val_lbl = tk.Label(row, text=fmt(var.get()), font=("Helvetica", 10, "bold"),
                           bg=BG, fg=TEXT, width=10, anchor="e")
        val_lbl.pack(side="right")
        sl = ttk.Scale(row, from_=mn, to=mx, variable=var, orient="horizontal")
        sl.pack(side="left", fill="x", expand=True, padx=(0, 8))
        def on_change(v, lbl=val_lbl):
            lbl.config(text=fmt(v))
            if color_fn:
                lbl.config(fg=color_fn(float(v)))
        sl.config(command=on_change)
        return sl, val_lbl

    def _build_ui(self):
        title_frame = tk.Frame(self, bg=BG)
        title_frame.pack(fill="x", padx=16, pady=(18, 4))
        tk.Label(title_frame, text="🎛  audio glitcher", font=("Helvetica", 18, "bold"),
                 bg=BG, fg=ACCENT2).pack(side="left")
        tk.Label(title_frame, text="byte corruption tool", font=("Helvetica", 11),
                 bg=BG, fg=MUTED).pack(side="left", padx=(10, 0), pady=(4, 0))

        self._divider()

        self._section("input file")
        self._filepicker(self.input_path, self._pick_input)
        self._section("output file  (leave blank = auto)")
        self._filepicker(self.output_path, self._pick_output)

        self._divider()

        self._section("corruption mode")
        mode_frame = tk.Frame(self, bg=BG)
        mode_frame.pack(fill="x", padx=16, pady=(0, 6))
        for m in MODE_DESCS:
            b = tk.Button(mode_frame, text=m, font=("Helvetica", 10),
                          bg=SURFACE2, fg=MUTED, relief="flat", bd=0,
                          padx=10, pady=5, cursor="hand2",
                          command=lambda x=m: self._set_mode(x))
            b.pack(side="left", padx=(0, 6), pady=2)
            self._mode_btns[m] = b

        self.mode_desc_lbl = tk.Label(self, text="", font=("Helvetica", 10),
                                      bg=BG, fg=MUTED, wraplength=488, justify="left")
        self.mode_desc_lbl.pack(fill="x", padx=16, pady=(0, 8))

        self._divider()

        self._section("settings")
        self._slider("intensity — % of bytes to corrupt",
                     self.intensity, 0.1, 100, 0.1,
                     lambda v: f"{float(v):.1f}%", self._chaos_color)
        self._slider("header protection — skip first N bytes",
                     self.header, 0, 5000, 10, lambda v: f"{int(float(v))} B")

        frame = tk.Frame(self, bg=BG)
        frame.pack(fill="x", padx=16, pady=(0, 8))
        tk.Label(frame, textvariable=self.extra_label_var, font=("Helvetica", 10),
                 bg=BG, fg=MUTED).pack(anchor="w")
        row = tk.Frame(frame, bg=BG)
        row.pack(fill="x")
        self._extra_val_lbl = tk.Label(row, text="1", font=("Helvetica", 10, "bold"),
                                       bg=BG, fg=TEXT, width=10, anchor="e")
        self._extra_val_lbl.pack(side="right")
        self._extra_slider = ttk.Scale(row, from_=1, to=8, variable=self.extra,
                                       orient="horizontal")
        self._extra_slider.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._extra_slider.config(
            command=lambda v: self._extra_val_lbl.config(text=str(int(float(v)))))

        self._slider("random seed  (0 = truly random)",
                     self.seed, 0, 9999, 1,
                     lambda v: "random" if int(float(v)) == 0 else str(int(float(v))))

        self._divider()

        self.status_var = tk.StringVar(value="ready.")
        self.status_lbl = tk.Label(self, textvariable=self.status_var,
                                   font=("Helvetica", 11), bg=BG, fg=MUTED)
        self.status_lbl.pack(padx=16, pady=(10, 4))

        self.go_btn = tk.Button(self, text="⚡  glitch it!", font=("Helvetica", 14, "bold"),
                                bg=ACCENT, fg="white", relief="flat", bd=0,
                                padx=20, pady=12, cursor="hand2",
                                activebackground=ACCENT2, activeforeground="white",
                                command=self._run)
        self.go_btn.pack(padx=16, pady=(4, 18), fill="x")

    def _set_mode(self, mode):
        self.mode_var.set(mode)
        for m, b in self._mode_btns.items():
            b.config(bg=ACCENT if m == mode else SURFACE2,
                     fg="white" if m == mode else MUTED)
        if self.mode_desc_lbl:
            self.mode_desc_lbl.config(text=MODE_DESCS[mode])
        self._refresh_extra()

    def _refresh_extra(self):
        if self._extra_slider is None:
            return
        mode = self.mode_var.get()
        label, mn, mx, step, default = EXTRA_CONFIG[mode]
        self.extra_label_var.set(label)
        self._extra_slider.config(from_=mn, to=mx)
        self.extra.set(default)
        self._extra_val_lbl.config(text=str(default))

    def _run(self):
        inp = self.input_path.get().strip()
        if not inp or not os.path.isfile(inp):
            messagebox.showerror("no file", "please pick a valid input audio file first.")
            return
        out = self.output_path.get().strip()
        if not out:
            base, ext = os.path.splitext(inp)
            out = f"{base}_glitched{ext}"

        self.go_btn.config(state="disabled", text="glitching…")
        self.status_lbl.config(fg=MUTED)
        self.status_var.set("reading file…")

        def task():
            try:
                with open(inp, "rb") as f:
                    raw = f.read()
                self.status_var.set("corrupting bytes…")
                result = corrupt_audio(
                    raw,
                    mode        = self.mode_var.get(),
                    intensity   = self.intensity.get(),
                    header_skip = self.header.get(),
                    extra       = self.extra.get(),
                    seed        = self.seed.get(),
                )
                with open(out, "wb") as f:
                    f.write(result)
                total   = len(raw)
                body    = total - self.header.get()
                corrupt = max(1, int(body * (self.intensity.get() / 100)))
                self.status_var.set(
                    f"done!  corrupted {corrupt:,} / {total:,} bytes  →  {os.path.basename(out)}")
                self.status_lbl.config(fg=SUCCESS)
            except Exception as e:
                self.status_var.set(f"error: {e}")
                self.status_lbl.config(fg=DANGER)
            finally:
                self.go_btn.config(state="normal", text="⚡  glitch it!")

        threading.Thread(target=task, daemon=True).start()

if __name__ == "__main__":
    app = AudioGlitcher()
    style = ttk.Style(app)
    style.theme_use("clam")
    style.configure("Horizontal.TScale",
                    background=BG,
                    troughcolor=SURFACE2,
                    sliderthickness=16,
                    sliderrelief="flat")
    app.mainloop()