import tkinter as tk
from tkinter import ttk, messagebox
import string

# ═══════════════════════════════════════════════════════════════
#  核心密码机组件
# ═══════════════════════════════════════════════════════════════

ROTOR_SPECS = {
    "I":    ("EKMFLGDQVZNTOWYHXUSPAIBRCJ", "Q"),
    "II":   ("AJDKSIRUXBLHWTMCQGZNPYFVOE", "E"),
    "III":  ("BDFHJLCPRTXVZNYEIWGAKMUSQO", "V"),
    "IV":   ("ESOVPZJAYQUIRHXLNFTGKDCMWB", "J"),
    "V":    ("VZBRGITYUPSDNHLXAWMJQOFECK", "Z"),
}

REFLECTOR_SPECS = {
    "B": "YRUHQSLDPXNGOKMIEBFZCWVJAT",
    "C": "FVPJIAOYEDRZXWGCTKUQSBNMHL",
}

_REV_WIRING_CACHE = {}
for _name, (_wiring, _) in ROTOR_SPECS.items():
    _rev = "".join(chr(65 + _wiring.index(chr(i + 65))) for i in range(26))
    _REV_WIRING_CACHE[_name] = _rev


class Plugboard:
    """插线板 (Steckerbrett)：字母对交换"""

    def __init__(self, pairs=None):
        self.mapping = {c: c for c in string.ascii_uppercase}
        if pairs:
            for a, b in pairs:
                self.mapping[a] = b
                self.mapping[b] = a

    def map(self, char):
        return self.mapping.get(char, char)

    def get_pairs(self):
        seen = set()
        pairs = []
        for a in string.ascii_uppercase:
            b = self.mapping[a]
            if a != b and a not in seen and b not in seen:
                pairs.append((a, b))
                seen.add(a)
                seen.add(b)
        return pairs

    def used_letters(self):
        return {a for a in string.ascii_uppercase if self.mapping[a] != a}


class Rotor:
    """转子：接线、缺口位置、环设置、当前位置"""

    def __init__(self, rotor_type, ring_setting=0, position=0):
        self.rotor_type = rotor_type
        wiring, notch = ROTOR_SPECS[rotor_type]
        self.wiring = wiring
        self.notch = notch
        self.ring_setting = ring_setting
        self.position = position
        self.rev_wiring = _REV_WIRING_CACHE[rotor_type]

    @property
    def notch_index(self):
        return (ord(self.notch) - 65 - self.ring_setting) % 26

    @property
    def is_at_notch(self):
        return self.position == self.notch_index

    def rotate(self):
        self.position = (self.position + 1) % 26
        return self.position

    def forward_map(self, char_in):
        contact = (char_in + self.position - self.ring_setting) % 26
        out_char = self.wiring[contact]
        return (ord(out_char) - 65 - self.position + self.ring_setting) % 26

    def backward_map(self, char_in):
        contact = (char_in + self.position - self.ring_setting) % 26
        out_char = self.rev_wiring[contact]
        return (ord(out_char) - 65 - self.position + self.ring_setting) % 26

    @property
    def position_char(self):
        return chr(self.position + 65)

    @property
    def ring_char(self):
        return chr(self.ring_setting + 65)

    def __repr__(self):
        return (f"Rotor({self.rotor_type}, ring={self.ring_char}, "
                f"pos={self.position_char}, notch={self.notch})")


class Reflector:
    """反射器 (Umkehrwalze)：固定映射"""

    def __init__(self, reflector_type):
        self.reflector_type = reflector_type
        self.wiring = REFLECTOR_SPECS[reflector_type]

    def map(self, char_in):
        return ord(self.wiring[char_in]) - 65


class EnigmaMachine:
    """恩尼格玛机：整合插线板、转子组、反射器"""

    def __init__(self, plugboard_pairs, rotor_types,
                 ring_settings, initial_positions, reflector_type="B"):
        self.plugboard = Plugboard(plugboard_pairs)
        self.rotors = [
            Rotor(rt, rs, pos)
            for rt, rs, pos in zip(rotor_types, ring_settings, initial_positions)
        ]
        self.reflector = Reflector(reflector_type)

        self.initial_rotor_types = list(rotor_types)
        self.initial_positions = list(initial_positions)
        self.initial_ring_settings = list(ring_settings)
        self.initial_reflector = reflector_type

    def _step_rotors(self):
        """模拟转子转动（含双步进机制）"""
        n = len(self.rotors)

        notch_states = [r.is_at_notch for r in self.rotors]
        right_at_notch = n >= 2 and notch_states[-1]
        middle_at_notch = n >= 3 and notch_states[-2]

        if middle_at_notch:
            self.rotors[-3].rotate()

        if n >= 2 and (right_at_notch or middle_at_notch):
            self.rotors[-2].rotate()

        self.rotors[-1].rotate()

    def encrypt_char(self, char):
        """加密单个字符"""
        upper_char = char.upper()
        if upper_char not in string.ascii_uppercase:
            return char

        char = upper_char
        self._step_rotors()

        char = self.plugboard.map(char)
        num = ord(char) - 65

        for rotor in reversed(self.rotors):
            num = rotor.forward_map(num)

        num = self.reflector.map(num)

        for rotor in self.rotors:
            num = rotor.backward_map(num)

        char = chr(num + 65)
        return self.plugboard.map(char)

    def encrypt(self, text):
        return "".join(self.encrypt_char(c) for c in text)

    def decrypt(self, text):
        """解密（恩尼格玛机的加解密对称，重置位置后重新加密即可）"""
        self.reset()
        return self.encrypt(text)

    def reset(self):
        """恢复到配置时的初始状态"""
        for i, rotor in enumerate(self.rotors):
            rotor.position = self.initial_positions[i]
            rotor.ring_setting = self.initial_ring_settings[i]

    @property
    def rotor_positions(self):
        return [r.position_char for r in self.rotors]

    @property
    def rotor_rings(self):
        return [r.ring_char for r in self.rotors]

    @property
    def rotor_info(self):
        return [(r.rotor_type, r.ring_char, r.position_char, r.notch) for r in self.rotors]


# ═══════════════════════════════════════════════════════════════
#  预设配置
# ═══════════════════════════════════════════════════════════════

PRESETS = {
    "默认 (I-II-III, B, AAA-AAA)": {
        "rotors": ["I", "II", "III"],
        "rings": ["A", "A", "A"],
        "positions": ["A", "A", "A"],
        "reflector": "B",
        "plugs": [("A", "B"), ("C", "D"), ("E", "F")],
        "desc": "程序默认配置"
    },
    "历史上的实例 (I-II-III, GXQ-KTK)": {
        "rotors": ["I", "II", "III"],
        "rings": ["G", "X", "Q"],
        "positions": ["K", "T", "K"],
        "reflector": "B",
        "plugs": [],
        "desc": "常见演示配置"
    },
    "海军型 (III-I-II, B, ZZZ)": {
        "rotors": ["III", "I", "II"],
        "rings": ["Z", "Z", "Z"],
        "positions": ["A", "A", "A"],
        "reflector": "B",
        "plugs": [],
        "desc": "海军常用转子顺序变体"
    },
    "C型反射器 (IV-V-III, C, AAA)": {
        "rotors": ["IV", "V", "III"],
        "rings": ["A", "A", "A"],
        "positions": ["A", "A", "A"],
        "reflector": "C",
        "plugs": [],
        "desc": "使用 C 型反射器的配置"
    },
}


# ═══════════════════════════════════════════════════════════════
#  GUI 应用程序
# ═══════════════════════════════════════════════════════════════

class EnigmaApp:
    """恩尼格玛密码机图形界面"""

    COLOR_BG = "#0d1117"
    COLOR_SURFACE = "#161b22"
    COLOR_ACCENT = "#1c2333"
    COLOR_HIGHLIGHT = "#f03c5e"
    COLOR_TEXT = "#e6edf3"
    COLOR_GOLD = "#d29922"
    COLOR_GREEN = "#3fb950"
    COLOR_PURPLE = "#a371f7"
    COLOR_CYAN = "#58a6ff"
    COLOR_BORDER = "#30363d"

    def __init__(self, root):
        self.root = root
        self.root.title("恩尼格玛密码机模拟器  –  Enigma Machine Simulator")
        self.root.geometry("1000x780")
        self.root.minsize(860, 660)
        self.root.configure(bg=self.COLOR_BG)

        self._setup_style()
        self.enigma = self._create_default_enigma()
        self._signal_anim_id = None
        self._build_ui()
        self._refresh_all()

    def _setup_style(self):
        style = ttk.Style()
        style.theme_use("clam")

        bg = self.COLOR_BG
        surface = self.COLOR_SURFACE
        fg = self.COLOR_TEXT
        accent = self.COLOR_ACCENT
        highlight = self.COLOR_HIGHLIGHT
        gold = self.COLOR_GOLD
        border = self.COLOR_BORDER

        style.configure(".", background=bg, foreground=fg, font=("Microsoft YaHei", 9))
        style.configure("TFrame", background=bg)
        style.configure("TLabel", background=bg, foreground=fg)
        style.configure("TButton",
                        background=accent, foreground=fg,
                        borderwidth=1, padding=(14, 7),
                        font=("Microsoft YaHei", 9, "bold"))
        style.map("TButton",
                  background=[("active", highlight), ("!active", accent)],
                  relief=[("pressed", "sunken")])
        style.configure("Accent.TButton",
                        background=highlight, foreground="#fff",
                        font=("Microsoft YaHei", 9, "bold"),
                        borderwidth=0)
        style.map("Accent.TButton",
                  background=[("active", "#ff6b81"), ("!active", highlight)])

        style.configure("TNotebook", background=bg, borderwidth=0)
        style.configure("TNotebook.Tab",
                        background=surface, foreground=fg,
                        padding=(20, 8), font=("Microsoft YaHei", 10))
        style.map("TNotebook.Tab",
                  background=[("selected", highlight)],
                  foreground=[("selected", "#fff")])

        style.configure("TLabelframe", background=bg, foreground=gold,
                        borderwidth=1, relief="solid")
        style.configure("TLabelframe.Label",
                        background=bg, foreground=gold,
                        font=("Microsoft YaHei", 10, "bold"))

        style.configure("TCombobox", fieldbackground=surface, foreground=fg,
                        background=surface, arrowsize=16, borderwidth=1)
        style.map("TCombobox",
                  fieldbackground=[("readonly", surface)],
                  foreground=[("readonly", fg)])
        self.root.option_add("*TCombobox*Listbox.background", accent)
        self.root.option_add("*TCombobox*Listbox.foreground", fg)
        self.root.option_add("*TCombobox*Listbox.selectBackground", highlight)
        self.root.option_add("*TCombobox*Listbox.font", ("Consolas", 11))

        style.configure("Title.TLabel",
                        background=bg, foreground=gold,
                        font=("Microsoft YaHei", 24, "bold"))
        style.configure("Subtitle.TLabel",
                        background=bg, foreground="#8b949e",
                        font=("Microsoft YaHei", 10))

        style.configure("Status.TLabel",
                        background=accent, foreground=fg,
                        font=("Microsoft YaHei", 9))

    def _create_default_enigma(self):
        return EnigmaMachine(
            plugboard_pairs=[("A", "B"), ("C", "D"), ("E", "F")],
            rotor_types=["I", "II", "III"],
            ring_settings=[0, 0, 0],
            initial_positions=[0, 0, 0],
            reflector_type="B"
        )

    def _create_enigma_from_preset(self, name):
        preset = PRESETS[name]
        return EnigmaMachine(
            plugboard_pairs=preset["plugs"],
            rotor_types=preset["rotors"],
            ring_settings=[ord(r) - 65 for r in preset["rings"]],
            initial_positions=[ord(p) - 65 for p in preset["positions"]],
            reflector_type=preset["reflector"]
        )

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=(20, 12))
        main.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(main)
        header.pack(pady=(0, 4))
        ttk.Label(header, text="恩尼格玛密码机", style="Title.TLabel").pack()
        ttk.Label(header, text="Enigma I / M3  ·  仿真模拟器",
                  style="Subtitle.TLabel").pack()

        nb = ttk.Notebook(main)
        nb.pack(fill=tk.BOTH, expand=True, padx=2, pady=6)

        crypto_frame = ttk.Frame(nb, padding=12)
        config_frame = ttk.Frame(nb, padding=12)
        rotor_frame = ttk.Frame(nb, padding=12)

        nb.add(crypto_frame, text="  加密 / 解密  ")
        nb.add(config_frame, text="  机器配置  ")
        nb.add(rotor_frame, text="  转子状态  ")

        self._build_crypto_tab(crypto_frame)
        self._build_config_tab(config_frame)
        self._build_rotor_tab(rotor_frame)

        status_bar = ttk.Frame(self.root)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_var = tk.StringVar(value="就绪 — 请配置机器后开始加解密")
        ttk.Label(status_bar, textvariable=self.status_var,
                  style="Status.TLabel", padding=(16, 6)).pack(fill=tk.X)

    def _build_crypto_tab(self, parent):
        in_frame = ttk.LabelFrame(parent, text=" 输入文本 ", padding=10)
        in_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        text_bg = self.COLOR_SURFACE
        self.input_text = tk.Text(in_frame, height=5, width=60,
                                  font=("Consolas", 12),
                                  bg=text_bg, fg=self.COLOR_TEXT,
                                  insertbackground=self.COLOR_GOLD,
                                  relief="flat", borderwidth=0,
                                  highlightthickness=1,
                                  highlightbackground=self.COLOR_BORDER,
                                  highlightcolor=self.COLOR_CYAN,
                                  padx=10, pady=10)
        self.input_text.pack(fill=tk.BOTH, expand=True)
        self.input_text.insert("1.0", "HELLO WORLD")

        btn_bar = ttk.Frame(parent)
        btn_bar.pack(fill=tk.X, pady=(8, 4))
        inner = ttk.Frame(btn_bar)
        inner.pack(expand=True)

        ttk.Button(inner, text="  Encrypt",
                   style="Accent.TButton",
                   command=self._encrypt).pack(side=tk.LEFT, padx=4)
        ttk.Button(inner, text="  Decrypt",
                   command=self._decrypt).pack(side=tk.LEFT, padx=4)
        ttk.Button(inner, text="  Clear",
                   command=self._clear_input).pack(side=tk.LEFT, padx=4)
        ttk.Button(inner, text="  Copy",
                   command=self._copy_output).pack(side=tk.LEFT, padx=4)

        out_frame = ttk.LabelFrame(parent, text=" 输出结果 ", padding=10)
        out_frame.pack(fill=tk.BOTH, expand=True)

        self.output_text = tk.Text(out_frame, height=5, width=60,
                                   font=("Consolas", 12, "bold"),
                                   bg=text_bg, fg=self.COLOR_GREEN,
                                   insertbackground=self.COLOR_GOLD,
                                   relief="flat", borderwidth=0,
                                   highlightthickness=1,
                                   highlightbackground=self.COLOR_BORDER,
                                   highlightcolor=self.COLOR_CYAN,
                                   padx=10, pady=10)
        self.output_text.pack(fill=tk.BOTH, expand=True)

    def _encrypt(self):
        text = self.input_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("输入为空", "请在输入框中输入要加密的文本。")
            return
        try:
            result = self.enigma.encrypt(text)
            self.output_text.delete("1.0", tk.END)
            self.output_text.insert("1.0", result)
            display_positions = [r.position_char for r in reversed(self.enigma.rotors)]
            self.status_var.set(f"加密完成 — 转子位置(右→左): {' '.join(display_positions)}")
            self._draw_rotors()
            self._animate_signal()
        except Exception as e:
            messagebox.showerror("加密失败", str(e))

    def _decrypt(self):
        text = self.input_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("输入为空", "请在输入框中输入要解密的文本。")
            return
        try:
            result = self.enigma.decrypt(text)
            self.output_text.delete("1.0", tk.END)
            self.output_text.insert("1.0", result)
            self.status_var.set("解密完成 — 机器已重置到初始位置")
            self._draw_rotors()
            self._animate_signal()
        except Exception as e:
            messagebox.showerror("解密失败", str(e))

    def _clear_input(self):
        self.input_text.delete("1.0", tk.END)
        self.output_text.delete("1.0", tk.END)

    def _copy_output(self):
        text = self.output_text.get("1.0", tk.END).strip()
        if text:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.status_var.set("输出已复制到剪贴板")

    def _build_config_tab(self, parent):
        preset_frame = ttk.LabelFrame(parent, text=" 预设配置 ", padding=10)
        preset_frame.pack(fill=tk.X, pady=(0, 10))

        row = ttk.Frame(preset_frame)
        row.pack(fill=tk.X)
        ttk.Label(row, text="选择预设：").pack(side=tk.LEFT, padx=(0, 8))

        self.preset_var = tk.StringVar()
        preset_cb = ttk.Combobox(row, textvariable=self.preset_var,
                                 values=list(PRESETS.keys()),
                                 state="readonly", width=38)
        preset_cb.pack(side=tk.LEFT, padx=(0, 8))
        preset_cb.bind("<<ComboboxSelected>>", self._on_preset_selected)
        ttk.Button(row, text="加载并应用",
                   command=self._load_preset).pack(side=tk.LEFT)

        self.preset_desc_var = tk.StringVar()
        ttk.Label(row, textvariable=self.preset_desc_var,
                  foreground="#8b949e", font=("Microsoft YaHei", 8)).pack(side=tk.LEFT, padx=12)

        rotor_frame = ttk.LabelFrame(parent, text=" 转子配置（右 → 左）", padding=10)
        rotor_frame.pack(fill=tk.X, pady=(0, 10))

        hdr = ttk.Frame(rotor_frame)
        hdr.pack(fill=tk.X, pady=(0, 6))
        for txt, w in [("转子位置", 10), ("类型", 6), ("环设置", 6),
                        ("初始位置", 6), ("缺口", 4)]:
            ttk.Label(hdr, text=txt, width=w,
                      font=("Microsoft YaHei", 8, "bold"),
                      foreground=self.COLOR_GOLD).pack(side=tk.LEFT, padx=4)

        self._rotor_widgets = []
        labels = ["右转子 (快速)", "中转子", "左转子 (慢速)"]
        for i, lbl in enumerate(labels):
            rframe = ttk.Frame(rotor_frame)
            rframe.pack(fill=tk.X, pady=3)

            row_widgets = {}

            ttk.Label(rframe, text=lbl, width=10,
                      font=("Microsoft YaHei", 9, "bold")).pack(side=tk.LEFT, padx=4)

            type_var = tk.StringVar(value=["III", "II", "I"][i])
            cb = ttk.Combobox(rframe, textvariable=type_var,
                              values=["I", "II", "III", "IV", "V"],
                              state="readonly", width=5)
            cb.pack(side=tk.LEFT, padx=4)
            row_widgets["type"] = type_var

            ring_var = tk.StringVar(value="A")
            cb2 = ttk.Combobox(rframe, textvariable=ring_var,
                               values=list(string.ascii_uppercase),
                               state="readonly", width=5)
            cb2.pack(side=tk.LEFT, padx=4)
            row_widgets["ring"] = ring_var

            pos_var = tk.StringVar(value="A")
            cb3 = ttk.Combobox(rframe, textvariable=pos_var,
                               values=list(string.ascii_uppercase),
                               state="readonly", width=5)
            cb3.pack(side=tk.LEFT, padx=4)
            row_widgets["pos"] = pos_var

            notch_var = tk.StringVar(value="─")
            ttk.Label(rframe, textvariable=notch_var, width=4,
                      font=("Consolas", 10, "bold"),
                      foreground=self.COLOR_HIGHLIGHT).pack(side=tk.LEFT, padx=4)
            row_widgets["notch"] = notch_var

            self._rotor_widgets.append(row_widgets)

            type_var.trace_add("write",
                               lambda *_, i=i: self._on_rotor_type_change(i))
            self._on_rotor_type_change(i)

        ref_frame = ttk.Frame(rotor_frame)
        ref_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(ref_frame, text="反射器类型：",
                  font=("Microsoft YaHei", 9, "bold")).pack(side=tk.LEFT, padx=(0, 8))
        self.reflector_var = tk.StringVar(value="B")
        ttk.Combobox(ref_frame, textvariable=self.reflector_var,
                     values=["B", "C"], state="readonly", width=5).pack(side=tk.LEFT)

        pb_frame = ttk.LabelFrame(parent, text=" 插线板 (Steckerbrett) ", padding=10)
        pb_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.pb_canvas = tk.Canvas(pb_frame, height=120,
                                   bg=self.COLOR_SURFACE,
                                   highlightthickness=1,
                                   highlightbackground=self.COLOR_BORDER)
        self.pb_canvas.pack(fill=tk.X, padx=2, pady=2)

        ctrl = ttk.Frame(pb_frame)
        ctrl.pack(fill=tk.X, pady=(6, 4))

        ttk.Label(ctrl, text="添加连接：").pack(side=tk.LEFT, padx=(0, 6))

        self.plug_a_var = tk.StringVar()
        self.plug_a_combo = ttk.Combobox(ctrl, textvariable=self.plug_a_var,
                                         values=list(string.ascii_uppercase),
                                         state="readonly", width=4)
        self.plug_a_combo.pack(side=tk.LEFT, padx=4)
        self.plug_a_combo.bind("<<ComboboxSelected>>", self._on_plug_a_select)

        ttk.Label(ctrl, text="↔", font=("Segoe UI", 14, "bold"),
                  foreground=self.COLOR_HIGHLIGHT).pack(side=tk.LEFT, padx=6)

        self.plug_b_var = tk.StringVar()
        self.plug_b_combo = ttk.Combobox(ctrl, textvariable=self.plug_b_var,
                                         values=list(string.ascii_uppercase),
                                         state="readonly", width=4)
        self.plug_b_combo.pack(side=tk.LEFT, padx=4)

        ttk.Button(ctrl, text="Add", command=self._add_plug).pack(side=tk.LEFT, padx=10)
        ttk.Button(ctrl, text="Clear All",
                   command=self._clear_plugs).pack(side=tk.LEFT, padx=6)

        list_frame = ttk.Frame(pb_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        ttk.Label(list_frame, text="当前连接：",
                  font=("Microsoft YaHei", 9, "bold")).pack(anchor=tk.W)
        self.pb_list_var = tk.StringVar(value="(无)")
        ttk.Label(list_frame, textvariable=self.pb_list_var,
                  font=("Consolas", 11),
                  foreground=self.COLOR_GREEN).pack(anchor=tk.W, pady=2)

        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(btn_frame, text="Apply Configuration", style="Accent.TButton",
                   command=self._apply_config).pack()

    def _build_rotor_tab(self, parent):
        self.rotor_canvas = tk.Canvas(parent, bg=self.COLOR_SURFACE,
                                      height=300, highlightthickness=1,
                                      highlightbackground=self.COLOR_BORDER)
        self.rotor_canvas.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        ctrl = ttk.Frame(parent)
        ctrl.pack(fill=tk.X, pady=(10, 2))
        inner_ctrl = ttk.Frame(ctrl)
        inner_ctrl.pack(expand=True)

        ttk.Label(inner_ctrl, text="手动设置转子位置：",
                  font=("Microsoft YaHei", 9, "bold")).pack(side=tk.LEFT, padx=(0, 10))

        self.manual_pos_vars = []
        self.manual_pos_combos = []
        for i, lbl in enumerate(["右", "中", "左"]):
            ttk.Label(inner_ctrl, text=f"{lbl}：",
                      font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=(6, 2))
            var = tk.StringVar(value="A")
            cb = ttk.Combobox(inner_ctrl, textvariable=var,
                              values=list(string.ascii_uppercase),
                              state="readonly", width=4)
            cb.pack(side=tk.LEFT, padx=2)
            self.manual_pos_vars.append(var)
            self.manual_pos_combos.append(cb)

        ttk.Button(inner_ctrl, text="Set Position",
                   command=self._set_manual_positions).pack(side=tk.LEFT, padx=10)
        ttk.Button(inner_ctrl, text="Reset",
                   command=self._reset_machine).pack(side=tk.LEFT, padx=4)
        ttk.Button(inner_ctrl, text="Step",
                   command=self._single_step).pack(side=tk.LEFT, padx=4)

    def _refresh_all(self):
        self._draw_rotors()
        self._draw_plugboard()
        self._update_pb_list()
        self._update_plug_options()
        self._update_manual_positions()

    def _draw_rounded_rect(self, canvas, x1, y1, x2, y2, r=8, **kwargs):
        """绘制圆角矩形"""
        points = [
            x1 + r, y1,
            x2 - r, y1,
            x2, y1,
            x2, y1 + r,
            x2, y2 - r,
            x2, y2,
            x2 - r, y2,
            x1 + r, y2,
            x1, y2,
            x1, y2 - r,
            x1, y1 + r,
            x1, y1,
        ]
        return canvas.create_polygon(points, smooth=True, **kwargs)

    def _draw_rotors(self):
        canvas = self.rotor_canvas
        canvas.delete("all")
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w < 50 or h < 50:
            return

        rotors = list(reversed(self.enigma.rotors))
        labels = ["右转子", "中转子", "左转子"]

        n = len(rotors)
        padding_x = 44
        gap = 28
        usable = w - 2 * padding_x - (n * gap)
        box_w = usable // (n + 1)
        box_w = min(box_w, 180)
        box_h = min(220, h - 70)
        start_y = 24

        for i, rotor in enumerate(rotors):
            x0 = padding_x + i * (box_w + gap + (gap if i > 0 else 0))
            y0 = start_y
            x1 = x0 + box_w

            shadow_off = 3
            self._draw_rounded_rect(canvas, x0 + shadow_off, y0 + shadow_off,
                                    x1 + shadow_off, start_y + box_h + shadow_off,
                                    r=10, fill="#000", outline="", stipple="gray25")

            self._draw_rounded_rect(canvas, x0, y0, x1, start_y + box_h,
                                    r=10, fill=self.COLOR_ACCENT,
                                    outline=self.COLOR_BORDER, width=1)

            outer_r = 12
            canvas.create_oval(x1 - outer_r, y0 - outer_r,
                               x1 + outer_r, y0 + outer_r,
                               fill=self.COLOR_BG, outline=self.COLOR_BORDER, width=1)
            canvas.create_oval(x0 - outer_r, y0 - outer_r,
                               x0 + outer_r, y0 + outer_r,
                               fill=self.COLOR_BG, outline=self.COLOR_BORDER, width=1)

            canvas.create_text((x0 + x1) // 2, y0 - 14,
                               text=f"{labels[i]} · {rotor.rotor_type}型",
                               font=("Microsoft YaHei", 9, "bold"),
                               fill=self.COLOR_GOLD)

            win_y = y0 + 24
            win_h = 40
            self._draw_rounded_rect(canvas, x0 + 14, win_y, x1 - 14, win_y + win_h,
                                    r=6, fill="#0d1117", outline=self.COLOR_GOLD, width=2)

            canvas.create_text((x0 + x1) // 2, win_y + win_h // 2,
                               text=rotor.position_char,
                               font=("Consolas", 22, "bold"),
                               fill=self.COLOR_GREEN)

            prev_c = chr((rotor.position - 1) % 26 + 65)
            canvas.create_text((x0 + x1) // 2, win_y - 12,
                               text=prev_c, font=("Consolas", 10),
                               fill="#484f58")
            next_c = chr((rotor.position + 1) % 26 + 65)
            canvas.create_text((x0 + x1) // 2, win_y + win_h + 12,
                               text=next_c, font=("Consolas", 10),
                               fill="#484f58")

            info_y = start_y + box_h - 42
            canvas.create_text((x0 + x1) // 2, info_y,
                               text=f"环: {rotor.ring_char}",
                               font=("Microsoft YaHei", 9),
                               fill=self.COLOR_TEXT)
            canvas.create_text((x0 + x1) // 2, info_y + 20,
                               text=f"缺口: {rotor.notch}",
                               font=("Consolas", 9),
                               fill=self.COLOR_HIGHLIGHT)

        rx0 = padding_x + n * (box_w + gap) + gap
        rx1 = rx0 + box_w - 24
        shadow_off = 3
        self._draw_rounded_rect(canvas, rx0 + shadow_off, y0 + shadow_off,
                                rx1 + shadow_off, start_y + box_h + shadow_off,
                                r=10, fill="#000", outline="", stipple="gray25")
        self._draw_rounded_rect(canvas, rx0, y0, rx1, start_y + box_h,
                                r=10, fill="#1a103c", outline=self.COLOR_PURPLE, width=2)
        canvas.create_text((rx0 + rx1) // 2, y0 - 14,
                           text=f"{self.enigma.reflector.reflector_type}型反射器",
                           font=("Microsoft YaHei", 11, "bold"),
                           fill=self.COLOR_PURPLE)

        arrow_y = start_y + box_h + 24
        self._signal_arrows = []
        for i in range(n - 1):
            ax = padding_x + (i + 1) * (box_w + gap) - gap // 2
            aid = canvas.create_line(ax, arrow_y, ax + gap, arrow_y,
                                     arrow=tk.LAST, fill=self.COLOR_GOLD, width=2)
            self._signal_arrows.append(aid)

        arx = padding_x + n * (box_w + gap) + gap // 2 - 4
        aid = canvas.create_line(arx, arrow_y, arx + gap // 2, arrow_y,
                                 arrow=tk.LAST, fill=self.COLOR_PURPLE, width=2)
        self._signal_arrows.append(aid)

        mid_y = start_y + box_h // 2
        label_x = rx1 + 20
        canvas.create_text(label_x, mid_y,
                           text="信\n号\n流\n向",
                           font=("Microsoft YaHei", 9),
                           fill="#8b949e", justify=tk.CENTER)

    def _animate_signal(self):
        if self._signal_anim_id:
            self.root.after_cancel(self._signal_anim_id)

        try:
            arrows = getattr(self, "_signal_arrows", [])
            if not arrows:
                return
            canvas = self.rotor_canvas
            orig_colors = {}
            for aid in arrows:
                try:
                    orig_colors[aid] = canvas.itemcget(aid, "fill")
                    canvas.itemconfig(aid, fill=self.COLOR_CYAN, width=3)
                except:
                    pass

            def restore():
                for aid, color in orig_colors.items():
                    try:
                        canvas.itemconfig(aid, fill=color, width=2)
                    except:
                        pass

            self._signal_anim_id = self.root.after(400, restore)
        except:
            pass

    def _update_manual_positions(self):
        for i, rotor in enumerate(reversed(self.enigma.rotors)):
            self.manual_pos_vars[i].set(rotor.position_char)

    def _set_manual_positions(self):
        try:
            rotor_count = len(self.enigma.rotors)
            for i, var in enumerate(self.manual_pos_vars):
                pos = ord(var.get()) - 65
                rotor_index = rotor_count - 1 - i
                self.enigma.rotors[rotor_index].position = pos
                self.enigma.initial_positions[rotor_index] = pos
            self._draw_rotors()
            self.status_var.set("转子位置已更新")
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def _single_step(self):
        """手动单步转动转子"""
        self.enigma._step_rotors()
        self._update_manual_positions()
        self._draw_rotors()
        display_positions = [r.position_char for r in reversed(self.enigma.rotors)]
        self.status_var.set(f"单步完成 — 位置(右→左): {' '.join(display_positions)}")

    def _reset_machine(self):
        self.enigma.reset()
        self._refresh_all()
        self.status_var.set("机器已重置到初始状态")

    def _on_rotor_type_change(self, index):
        rt = self._rotor_widgets[index]["type"].get()
        if rt in ROTOR_SPECS:
            self._rotor_widgets[index]["notch"].set(ROTOR_SPECS[rt][1])

    def _update_plug_options(self):
        """过滤插线板下拉选项：仅显示未被占用的字母"""
        used = self.enigma.plugboard.used_letters()
        available = [c for c in string.ascii_uppercase if c not in used]

        a_val = self.plug_a_var.get()
        b_val = self.plug_b_var.get()

        opts_a = list(available)
        if a_val and a_val not in opts_a:
            opts_a.append(a_val)
        self.plug_a_combo["values"] = sorted(opts_a)

        opts_b = [c for c in available if c != a_val]
        if b_val and b_val not in opts_b and b_val not in used:
            opts_b.append(b_val)
        self.plug_b_combo["values"] = sorted(opts_b)

    def _on_plug_a_select(self, event=None):
        self._update_plug_options()

    def _add_plug(self):
        a = self.plug_a_var.get().strip().upper()
        b = self.plug_b_var.get().strip().upper()

        if not a or not b:
            messagebox.showerror("输入不完整", "请分别选择两个不同的字母。")
            return
        if a == b:
            messagebox.showerror("无效连接", "不能将字母连接到自身。")
            return

        used = self.enigma.plugboard.used_letters()
        if a in used or b in used:
            messagebox.showerror("冲突",
                                 f"字母 {a} 或 {b} 已在使用中，请先移除相关连接。")
            return

        current = self.enigma.plugboard.get_pairs()
        current.append((a, b))
        self.enigma.plugboard = Plugboard(current)

        self.plug_a_var.set("")
        self.plug_b_var.set("")
        self._draw_plugboard()
        self._update_pb_list()
        self._update_plug_options()
        self.status_var.set(f"插线板已添加连接: {a}↔{b}")

    def _clear_plugs(self):
        self.enigma.plugboard = Plugboard([])
        self.plug_a_var.set("")
        self.plug_b_var.set("")
        self._draw_plugboard()
        self._update_pb_list()
        self._update_plug_options()
        self.status_var.set("插线板已全部清除")

    def _draw_plugboard(self):
        canvas = self.pb_canvas
        canvas.delete("all")
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w < 100 or h < 20:
            return

        pairs = self.enigma.plugboard.get_pairs()
        letters = list(string.ascii_uppercase)
        spacing = w / 26
        y_top, y_bot = 26, h - 26

        bg_color = self.COLOR_SURFACE
        for i, c in enumerate(letters):
            x = (i + 0.5) * spacing
            is_used = self.enigma.plugboard.mapping[c] != c
            color = self.COLOR_GREEN if is_used else "#484f58"

            r = 10 if is_used else 6
            if is_used:
                canvas.create_oval(x - r, y_top - r, x + r, y_top + r,
                                   fill=self.COLOR_GREEN, outline=self.COLOR_GREEN,
                                   stipple="gray25" if False else "")
                canvas.create_oval(x - r, y_top - r, x + r, y_top + r,
                                   fill=bg_color, outline=self.COLOR_GREEN, width=2)

            canvas.create_text(x, y_top, text=c,
                               font=("Consolas", 11, "bold"), fill=color)
            is_used_bot = self.enigma.plugboard.mapping[c] != c
            color_bot = self.COLOR_GREEN if is_used_bot else "#484f58"

            if is_used_bot:
                canvas.create_oval(x - r, y_bot - r, x + r, y_bot + r,
                                   fill=bg_color, outline=self.COLOR_GREEN, width=2)
            canvas.create_text(x, y_bot, text=c,
                               font=("Consolas", 11, "bold"), fill=color_bot)

        for a, b in pairs:
            ia, ib = ord(a) - 65, ord(b) - 65
            xa = (ia + 0.5) * spacing
            xb = (ib + 0.5) * spacing
            mid = (xa + xb) / 2

            canvas.create_line(xa, y_top + 12, mid, h / 2,
                               xb, y_top + 12,
                               fill=self.COLOR_HIGHLIGHT, width=2, smooth=True,
                               splinesteps=32)

            r = 10
            canvas.create_oval(xa - r, y_top + 2, xa + r, y_top + 22,
                               fill=self.COLOR_ACCENT,
                               outline=self.COLOR_HIGHLIGHT, width=2)
            canvas.create_text(xa, y_top + 12, text=a,
                               font=("Consolas", 9, "bold"), fill="#fff")
            canvas.create_oval(xb - r, y_top + 2, xb + r, y_top + 22,
                               fill=self.COLOR_ACCENT,
                               outline=self.COLOR_HIGHLIGHT, width=2)
            canvas.create_text(xb, y_top + 12, text=b,
                               font=("Consolas", 9, "bold"), fill="#fff")

    def _update_pb_list(self):
        pairs = self.enigma.plugboard.get_pairs()
        if not pairs:
            self.pb_list_var.set("(无连接)")
        else:
            self.pb_list_var.set("  ".join(f"{a}↔{b}" for a, b in pairs))

    def _on_preset_selected(self, event=None):
        name = self.preset_var.get()
        if name in PRESETS:
            self.preset_desc_var.set(PRESETS[name]["desc"])

    def _load_preset(self):
        name = self.preset_var.get()
        if not name:
            messagebox.showwarning("未选择", "请先从列表中选一个预设配置。")
            return
        if name not in PRESETS:
            return

        preset = PRESETS[name]

        display_rotors = list(reversed(preset["rotors"]))
        display_rings = list(reversed(preset["rings"]))
        display_positions = list(reversed(preset["positions"]))

        for i, rt in enumerate(display_rotors):
            self._rotor_widgets[i]["type"].set(rt)
            self._rotor_widgets[i]["ring"].set(display_rings[i])
            self._rotor_widgets[i]["pos"].set(display_positions[i])

        self.reflector_var.set(preset["reflector"])

        self.enigma = self._create_enigma_from_preset(name)

        self._refresh_all()
        self.status_var.set(f"已加载预设: {name}  —  {preset['desc']}")

    def _apply_config(self):
        try:
            display_rotor_types = [w["type"].get() for w in self._rotor_widgets]
            display_ring_settings = [ord(w["ring"].get()) - 65 for w in self._rotor_widgets]
            display_positions = [ord(w["pos"].get()) - 65 for w in self._rotor_widgets]
            rotor_types = list(reversed(display_rotor_types))
            ring_settings = list(reversed(display_ring_settings))
            positions = list(reversed(display_positions))
            reflector = self.reflector_var.get()
            plug_pairs = self.enigma.plugboard.get_pairs()

            if len(set(display_rotor_types)) != 3:
                messagebox.showerror("配置错误",
                                     "三个转子不能重复——真实的恩尼格玛机每台只配有一套转子（每种型号一个）。")
                return

            self.enigma = EnigmaMachine(
                plugboard_pairs=plug_pairs,
                rotor_types=rotor_types,
                ring_settings=ring_settings,
                initial_positions=positions,
                reflector_type=reflector
            )

            self._refresh_all()
            self.status_var.set(
                f"配置已应用 — "
                f"转子(右→左): {'-'.join(display_rotor_types)}, "
                f"环: {''.join(chr(r+65) for r in display_ring_settings)}, "
                f"反射器: {reflector}型"
            )
        except Exception as e:
            messagebox.showerror("配置错误", str(e))


# ═══════════════════════════════════════════════════════════════
#  入口
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    root = tk.Tk()
    app = EnigmaApp(root)
    root.mainloop()
