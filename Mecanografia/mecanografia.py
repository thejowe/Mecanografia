import tkinter as tk
import random
import time
import math
import winsound
import os

# --- Cargar el WAV una sola vez a memoria (latencia baja) ---
KEY_WAV_BYTES = None
KEY_WAV_PATH = "key.wav"  # tu archivo
try:
    if os.path.exists(KEY_WAV_PATH):
        with open(KEY_WAV_PATH, "rb") as f:
            KEY_WAV_BYTES = f.read()
except Exception:
    KEY_WAV_BYTES = None

# ======== SONIDO ========
def play_key_sound():
    """
    Intenta reproducir key.wav de forma asíncrona.
    Si falla (no existe o error), usa un sonido del sistema como fallback.
    """
    try:
        winsound.PlaySound('key.wav', winsound.SND_FILENAME | winsound.SND_ASYNC)
    except RuntimeError:
        try:
            winsound.PlaySound('SystemAsterisk', winsound.SND_ALIAS | winsound.SND_ASYNC)
        except RuntimeError:
            pass

# ----- Palabras y límites -----
WORDS = [
    "time","year","people","way","day","man","thing","woman","life","child","world","school","state","family","student",
    "group","country","problem","hand","part","place","case","week","company","system","program","question","work","night",
    "point","home","water","room","mother","area","money","story","fact","month","lot","right","study","book","eye",
    "job","word","business","issue","side","kind","head","house","service","friend","father","power","hour","game","line",
    "end","member","law","car","city","community","name","president","team","minute","idea","kid","body","information",
    "back","parent","face","others","level","office","door","health","person","art","war","history","party","result",
    "change","morning","reason","research","girl","guy","moment","air","teacher","force","education","foot","boy","age",
    "policy","process","music","market","sense","area","activity","road","class","care","field","pass","food",
    "love","price","practice","wall","need","effort","window","meeting","phone","data","paper","space","river",
    "stone","light","sound","sleep","energy","color","letter","animal","plant","ocean","cloud","dream","memory",
    "goal","focus","speed","spirit","fire","earth","wind","metal","wood","shadow","noise","value","habit","truth","skill",
    "mind","path","signal","shape","order","pattern","unit","test","flow","form","rule","note","list","card","key","map"
]
MAX_WORDS = 30
AUTO_NEXT_DELAY_MS = 1200  # espera antes de cargar nueva tanda (muestra stats/confeti)

def generate_word_stream(n_words=MAX_WORDS):
    n = min(n_words, MAX_WORDS)
    return " ".join(random.choice(WORDS) for _ in range(n))

def lerp(a, b, t):
    return a + (b - a) * t

class EntrenadorMecanografia:
    def __init__(self, root):
        self.root = root
        self.root.title("🧠 Mecanografía (words + timer)")
        self.root.geometry("920x520")
        self.root.config(bg="#0e0e10")
        self.root.resizable(False, False)

        # ----- Estado -----
        self.texto_objetivo = generate_word_stream(MAX_WORDS)
        self.entrada_usuario = ""
        self.inicio_tiempo = None
        self.finalizado = False

        # Timer
        self.time_limit = 30   # por defecto 30s
        self.time_left = None
        self.timer_running = False
        self._timer_id = None

        # Progreso
        self.progress_target = 0.0
        self.progress_value = 0.0

        # Colores base
        self.bg_base = "#0e0e10"
        self.text_bg_base = "#151518"

        # ===== Header =====
        self.header = tk.Frame(self.root, bg=self.bg_base)
        self.header.pack(fill="x", pady=(12, 6))

        self.titulo = tk.Label(
            self.header, text="monkeytype-ish • english words + timed",
            font=("Helvetica", 16, "bold"), fg="#f5f5f7", bg=self.bg_base
        )
        self.titulo.pack(side="left", padx=16)

        # Selector de tiempo (10/20/30 s)
        self.time_var = tk.IntVar(value=30)
        self.time_box = tk.Frame(self.header, bg=self.bg_base)
        self.time_box.pack(side="right", padx=16)

        tk.Label(self.time_box, text="Tiempo:", fg="#f5f5f7", bg=self.bg_base).pack(side="left", padx=(0,8))
        for t in (10, 20, 30):
            rb = tk.Radiobutton(
                self.time_box, text=f"{t}s", variable=self.time_var, value=t,
                fg="#f5f5f7", bg=self.bg_base, selectcolor="#1f2937",
                activebackground="#1f2937", highlightthickness=0,
                command=self._on_change_time
            )
            rb.pack(side="left")

        # ===== Barra de progreso =====
        self.progress_h = 8
        self.progress = tk.Canvas(self.root, height=self.progress_h, bg=self.bg_base,
                                  highlightthickness=0, bd=0)
        self.progress.pack(fill="x", padx=24, pady=(0, 8))
        self.progress_rect = self.progress.create_rectangle(0, 0, 0, self.progress_h, width=0, fill="#ffd166")

        # ===== Panel superior: cronómetro y botón =====
        self.topbar = tk.Frame(self.root, bg=self.bg_base)
        self.topbar.pack(fill="x", padx=24, pady=(0, 8))

        self.timer_label = tk.Label(self.topbar, text="⏱ 00.0s", font=("Helvetica", 14, "bold"),
                                    fg="#f5f5f7", bg=self.bg_base)
        self.timer_label.pack(side="left")

        self.boton_nueva = tk.Button(self.topbar, text="Nueva tanda", command=self.nueva_frase,
                                     bg="#1f2937", fg="#f5f5f7", activebackground="#374151",
                                     font=("Helvetica", 12, "bold"), relief="flat", padx=14, pady=6)
        self.boton_nueva.pack(side="right")

        # ===== Contenedor principal =====
        self.wrap = tk.Frame(self.root, bg=self.bg_base)
        self.wrap.pack(fill="both", expand=True)

        # Texto objetivo
        self.texto_label = tk.Text(
            self.wrap, height=6, width=88, font=("Consolas", 20),
            wrap="word", bg=self.text_bg_base, fg="#cfcfd2",
            relief="flat", insertwidth=0, padx=18, pady=16
        )
        self.texto_label.pack(pady=(0, 8))
        self.texto_label.insert("1.0", self.texto_objetivo)
        self.texto_label.configure(state="disabled")

        # Tags de color
        self.texto_label.tag_configure("correcto", foreground="#86efac")   # verde
        self.texto_label.tag_configure("incorrecto", foreground="#ef4444") # rojo
        self.texto_label.tag_configure("resto", foreground="#f5f5f7")      # blanco

        # Caret overlay
        self.caret_canvas = tk.Canvas(self.wrap, width=1, height=1, bg=self.text_bg_base, highlightthickness=0, bd=0)
        self.caret_canvas.place(x=0, y=0, width=1, height=1)
        self.caret_id = None
        self.caret_visible = True

        # Resultado
        self.resultado_label = tk.Label(self.wrap, text="", font=("Helvetica", 14, "bold"),
                                        bg=self.bg_base, fg="#f5f5f7")
        self.resultado_label.pack(pady=8)

        # Confeti
        self.confeti = tk.Canvas(self.wrap, bg=self.bg_base, highlightthickness=0, bd=0)
        self.confeti.place(relx=0.5, y=0, anchor="n", relwidth=1, height=0)

        # Teclado
        self.root.bind("<Key>", self.teclear)

        # Inicialización
        self.render_text_colored()
        self.update_progress_anim()
        self.start_caret_blink()
        self._reset_timer_label()

    # ===== Utilidades de color/animación =====
    def start_caret_blink(self):
        if getattr(self, "caret_id", None) is None:
            self.caret_id = self.caret_canvas.create_rectangle(0, 0, 2, 24, fill="#f5f5f7", width=0)
        self._blink_loop()

    def _blink_loop(self):
        self.caret_visible = not getattr(self, "caret_visible", True)
        self.caret_canvas.itemconfigure(self.caret_id, state="normal" if self.caret_visible else "hidden")
        self.root.after(500, self._blink_loop)

    def pulse_text_bg(self, ok=True):
        if hasattr(self, "_pulse_running") and self._pulse_running:
            return
        self._pulse_running = True
        start = time.time()
        duration = 0.18
        color_from = self.text_bg_base
        color_to = "#16351f" if ok else "#3a1616"

        def hex_to_rgb(hx):
            hx = hx.lstrip('#'); return tuple(int(hx[i:i+2], 16) for i in (0, 2, 4))
        def rgb_to_hex(rgb):
            return "#%02x%02x%02x" % rgb

        c0, c1 = hex_to_rgb(color_from), hex_to_rgb(color_to)

        def step():
            t = (time.time() - start) / duration
            if t < 0.5:
                x = t / 0.5; col = tuple(int(lerp(c0[i], c1[i], x)) for i in range(3))
            elif t < 1.0:
                x = (t - 0.5) / 0.5; col = tuple(int(lerp(c1[i], c0[i], x)) for i in range(3))
            else:
                self.texto_label.configure(bg=self.text_bg_base); self._pulse_running = False; return
            self.texto_label.configure(bg=rgb_to_hex(col))
            self.root.after(16, step)
        step()

    def shake_window(self):
        if hasattr(self, "_shaking") and self._shaking:
            return
        self._shaking = True
        ox, oy = self.root.winfo_x(), self.root.winfo_y()
        start = time.time(); duration = 0.25

        def step():
            t = (time.time() - start) / duration
            if t >= 1:
                self.root.geometry(f"+{ox}+{oy}"); self._shaking = False; return
            amp = int(8 * (1 - t))
            dx = int(math.sin(t * 40) * amp)
            self.root.geometry(f"+{ox+dx}+{oy}")
            self.root.after(16, step)
        step()

    def start_confetti(self):
        self.confeti.place(relx=0.5, y=0, anchor="n", relwidth=1, height=240)
        W = self.confeti.winfo_width(); H = 240
        if W <= 0: self.root.after(10, self.start_confetti); return
        parts = []
        for _ in range(60):
            x = random.randint(0, W); y = random.randint(-H, 0); r = random.randint(2, 5)
            pid = self.confeti.create_oval(x-r, y-r, x+r, y+r,
                                           fill=random.choice(["#f59e0b","#10b981","#60a5fa","#f472b6","#f87171","#34d399"]),
                                           width=0)
            vy = random.uniform(2.0, 4.8); parts.append([pid, vy])
        start = time.time(); dur = 1.2
        def step():
            for pid, vy in parts: self.confeti.move(pid, 0, vy)
            if time.time() - start < dur: self.root.after(16, step)
            else: self.confeti.delete("all"); self.confeti.place_forget()
        step()

    # ===== Render y progreso =====
    def render_text_colored(self):
        self.texto_label.configure(state="normal")
        self.texto_label.delete("1.0", "end")

        for i, letra in enumerate(self.texto_objetivo):
            if i < len(self.entrada_usuario):
                if self.entrada_usuario[i] == letra:
                    self.texto_label.insert("end", letra, "correcto")
                else:
                    self.texto_label.insert("end", letra, "incorrecto")
            else:
                self.texto_label.insert("end", letra, "resto")

        self.texto_label.configure(state="disabled")
        self.update_progress_target()
        self.update_caret_position()

    def update_caret_position(self):
        idx = self._index_from_offset(len(self.entrada_usuario))
        bbox = self.texto_label.bbox(idx) or self.texto_label.bbox("end-1c")
        if bbox:
            x, y, w, h = bbox
            absx = self.texto_label.winfo_rootx() - self.wrap.winfo_rootx()
            absy = self.texto_label.winfo_rooty() - self.wrap.winfo_rooty()
            self.caret_canvas.place(x=x + absx + 2, y=y + absy + 4, width=2, height=h - 6)

    def _index_from_offset(self, offset):
        return f"1.0+{offset}c"

    def update_progress_target(self):
        total = len(self.texto_objetivo)
        current = min(len(self.entrada_usuario), total)
        self.progress_target = 0 if total == 0 else current / total

    def update_progress_anim(self):
        self.progress_value = lerp(self.progress_value, self.progress_target, 0.15)
        width = self.progress.winfo_width()
        self.progress.coords(self.progress_rect, 0, 0, width * self.progress_value, self.progress_h)
        self.root.after(16, self.update_progress_anim)

    # ===== Timer =====
    def _on_change_time(self):
        if self.timer_running:
            return  # no cambiar a mitad de test
        self.time_limit = self.time_var.get()
        self._reset_timer_label()

    def _reset_timer_label(self):
        self.timer_label.config(text=f"⏱ {self.time_limit:.1f}s")

    def _start_timer_if_needed(self):
        if self.timer_running:
            return
        self.time_limit = self.time_var.get()
        self.time_left = float(self.time_limit)
        self.inicio_tiempo = time.time()
        self.timer_running = True
        self._schedule_tick()

    def _schedule_tick(self):
        if not self.timer_running:
            return
        now = time.time()
        elapsed = now - self.inicio_tiempo
        self.time_left = max(0.0, self.time_limit - elapsed)
        self.timer_label.config(text=f"⏱ {self.time_left:0.1f}s")
        if self.time_left <= 0.0:
            self.finalizar(time_ran=self.time_limit)  # agotó tiempo
            return
        self._timer_id = self.root.after(100, self._schedule_tick)

    def _stop_timer(self):
        self.timer_running = False
        if self._timer_id is not None:
            try:
                self.root.after_cancel(self._timer_id)
            except Exception:
                pass
            self._timer_id = None

    # ===== Entrada =====
    def teclear(self, event):
        if self.finalizado:
            return

        # Sonido una vez por tecla (incluye Backspace)
        play_key_sound()

        # Backspace
        if event.keysym == "BackSpace":
            if self.entrada_usuario:
                self.entrada_usuario = self.entrada_usuario[:-1]
                self.render_text_colored()
            if not self.timer_running:
                self._start_timer_if_needed()
            return

        # Ignora no imprimibles
        if len(event.char) != 1:
            return

        # Arranca el cronómetro con la primera tecla "real"
        self._start_timer_if_needed()

        i = len(self.entrada_usuario)
        if i < len(self.texto_objetivo):
            correcto = (event.char == self.texto_objetivo[i])
            self.entrada_usuario += event.char
            self.render_text_colored()
            if not correcto:
                self.shake_window()

            # Fin por completar antes de tiempo
            if len(self.entrada_usuario) >= len(self.texto_objetivo):
                elapsed = min(self.time_limit, time.time() - self.inicio_tiempo) if self.inicio_tiempo else 0.0
                self.finalizar(time_ran=elapsed)

    # ===== Final =====
    def finalizar(self, time_ran=None):
        if self.finalizado:
            return
        self.finalizado = True
        self._stop_timer()

        # Tiempo real usado
        if time_ran is None:
            time_ran = (time.time() - self.inicio_tiempo) if self.inicio_tiempo else 0.0
        time_ran = max(0.0001, min(self.time_limit, time_ran))

        # Métricas "hasta donde llegaste"
        typed = len(self.entrada_usuario)
        correctas_chars = sum(1 for o, e in zip(self.texto_objetivo, self.entrada_usuario) if o == e)
        acc = (correctas_chars / typed * 100.0) if typed > 0 else 0.0
        wpm = (correctas_chars / 5.0) / (time_ran / 60.0)
        completion = (typed / len(self.texto_objetivo) * 100.0) if self.texto_objetivo else 0.0

        self.resultado_label.config(
            text=f"WPM: {wpm:.2f}   |   ACC: {acc:.2f}%   |   TIME: {time_ran:.2f}s   |   COMPLETION: {completion:.1f}%"
        )
        self.start_confetti()

        # Auto-siguiente tanda tras breve delay
        self.root.after(AUTO_NEXT_DELAY_MS, self.nueva_frase)

    # ===== Nueva tanda =====
    def nueva_frase(self):
        # reset total
        self._stop_timer()
        self.finalizado = False
        self.entrada_usuario = ""
        self.inicio_tiempo = None
        self.time_limit = self.time_var.get()
        self.time_left = None
        self._reset_timer_label()

        # texto nuevo (máx 30 palabras)
        self.texto_objetivo = generate_word_stream(MAX_WORDS)

        self.progress_target = 0.0
        self.resultado_label.config(text="")

        self.render_text_colored()

    # ===== Helpers =====
    def _index_from_offset(self, offset):
        return f"1.0+{offset}c"

if __name__ == "__main__":
    root = tk.Tk()
    app = EntrenadorMecanografia(root)
    root.mainloop()
