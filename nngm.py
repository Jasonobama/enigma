import tkinter as tk
from tkinter import ttk, messagebox
import string

# ═══════════════════════════════════════════════════════════════
#  核心密码机组件
# ═══════════════════════════════════════════════════════════════

# 转子规格表（接线 + 缺口位置）
ROTOR_SPECS = {
    "I":    ("EKMFLGDQVZNTOWYHXUSPAIBRCJ", "Q"),
    "II":   ("AJDKSIRUXBLHWTMCQGZNPYFVOE", "E"),
    "III":  ("BDFHJLCPRTXVZNYEIWGAKMUSQO", "V"),
    "IV":   ("ESOVPZJAYQUIRHXLNFTGKDCMWB", "J"),
    "V":    ("VZBRGITYUPSDNHLXAWMJQOFECK", "Z"),
}

# 反射器规格表
REFLECTOR_SPECS = {
    "B": "YRUHQSLDPXNGOKMIEBFZCWVJAT",
    "C": "FVPJIAOYEDRZXWGCTKUQSBNMHL",
}

# 转子接线对应的反转接线（预计算，避免每实例重复）
_REV_WIRING_CACHE = {}
for _name, (_wiring, _) in ROTOR_SPECS.items():
    _rev = "".join(chr(65 + _wiring.index(chr(i + 65))) for i in range(26))
    _REV_WIRING_CACHE[_name] = _rev


class Plugboard:
    """插线板 (Steckerbrett)：字母对交换"""

    def __init__(self, pairs=None):
        # A-Z 默认自映射
        self.mapping = {c: c for c in string.ascii_uppercase}
        if pairs:
            for a, b in pairs:
                self.mapping[a] = b
                self.mapping[b] = a

    def map(self, char):
        return self.mapping.get(char, char)

    def get_pairs(self):
        """返回当前所有交换对列表"""
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
        """返回已被占用（即参与交换）的字母集合"""
        return {a for a in string.ascii_uppercase if self.mapping[a] != a}


class Rotor:
    """转子：接线、缺口位置、环设置、当前位置"""

    def __init__(self, rotor_type, ring_setting=0, position=0):
        self.rotor_type = rotor_type
        wiring, notch = ROTOR_SPECS[rotor_type]
        self.wiring = wiring
        self.notch = notch           # 缺口字母
        self.ring_setting = ring_setting
        self.position = position
        self.rev_wiring = _REV_WIRING_CACHE[rotor_type]

    @property
    def notch_index(self):
        """缺口在字母表中的索引（考虑环偏移）"""
        return (ord(self.notch) - 65 - self.ring_setting) % 26

    @property
    def is_at_notch(self):
        return self.position == self.notch_index

    def rotate(self):
        self.position = (self.position + 1) % 26
        return self.position

    def forward_map(self, char_in):
        """正向映射：键盘→反射器"""
        contact = (char_in + self.position - self.ring_setting) % 26
        out_char = self.wiring[contact]
        return (ord(out_char) - 65 - self.position + self.ring_setting) % 26

    def backward_map(self, char_in):
        """反向映射：反射器→键盘"""
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

        # 保存初始状态，用于 reset()
        self.initial_rotor_types = list(rotor_types)
        self.initial_positions = list(initial_positions)
        self.initial_ring_settings = list(ring_settings)
        self.initial_reflector = reflector_type

        # 双步进标志
        self.next_turn = [False] * (len(rotor_types) - 1)

    def _step_rotors(self):
        """模拟转子转动（含双步进机制）"""
        # 最右转子总是转动
        self.rotors[-1].rotate()

        # 检查此前传递的转动信号（从左→右）
        for i in range(len(self.rotors) - 2, -1, -1):
            if self.next_turn[i]:
                self.rotors[i].rotate()

        # 生成本次转动信号（下一次使用）
        for i in range(len(self.rotors) - 1):
            self.next_turn[i] = self.rotors[i + 1].is_at_notch

    def encrypt_char(self, char):
        """加密单个字符"""
        if not char.isalpha():
            return char

        self._step_rotors()
        char = char.upper()

        # 插线板 → 转子组(正向) → 反射器 → 转子组(反向) → 插线板
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
        self.next_turn = [False] * (len(self.rotors) - 1)

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

    # ── 配色方案 ──
    COLOR_BG = "#1a1a2e"
    COLOR_SURFACE = "#16213e"
    COLOR_ACCENT = "#0f3460"
    COLOR_HIGHLIGHT = "#e94560"
    COLOR_TEXT = "#eee"
    COLOR_GOLD = "#f0a500"
    COLOR_GREEN = "#00b894"

    def __init__(self, root):
        self.root = root
        self.root.title("恩尼格玛密码机模拟器  –  Enigma Machine Simulator")
        self.root.geometry("960x720")
        self.root.minsize(800, 600)
        self.root.configure(bg=self.COLOR_BG)

        self._setup_style()
        self.enigma = self._create_default_enigma()
        self._build_ui()
        self._refresh_all()

    # ── 样式 ────────────────────────────────────────────────

    def _setup_style(self):
        style = ttk.Style()
        style.theme_use("clam")

        bg = self.COLOR_BG
        fg = self.COLOR_TEXT
        accent = self.COLOR_ACCENT
        highlight = self.COLOR_HIGHLIGHT

        style.configure(".", background=bg, foreground=fg, font=("Microsoft YaHei", 9))
        style.configure("TFrame", background=bg)
        style.configure("TLabel", background=bg, foreground=fg)
        style.configure("TButton",
                        background=accent, foreground=fg,
                        borderwidth=0, padding=(12, 6),
                        font=("Microsoft YaHei", 9, "bold"))
        style.map("TButton",
                  background=[("active", highlight), ("!active", accent)])
        style.configure("Accent.TButton",
                        background=highlight, foreground="white",
                        font=("Microsoft YaHei", 9, "bold"))
        style.map("Accent.TButton",
                  background=[("active", "#ff6b81"), ("!active", highlight)])

        style.configure("TNotebook", background=bg, borderwidth=0)
        style.configure("TNotebook.Tab",
                        background=accent, foreground=fg,
                        padding=(16, 6), font=("Microsoft YaHei", 10))
        style.map("TNotebook.Tab",
                  background=[("selected", highlight)],
                  foreground=[("selected", "white")])

        style.configure("TLabelframe", background=bg, foreground=self.COLOR_GOLD,
                        borderwidth=1, relief="solid")
        style.configure("TLabelframe.Label",
                        background=bg, foreground=self.COLOR_GOLD,
                        font=("Microsoft YaHei", 10, "bold"))

        style.configure("TCombobox", fieldbackground=accent, foreground=fg,
                        background=accent, arrowsize=16)
        style.map("TCombobox",
                  fieldbackground=[("readonly", accent)],
                  foreground=[("readonly", fg)])
        self.root.option_add("*TCombobox*Listbox.background", accent)
        self.root.option_add("*TCombobox*Listbox.foreground", fg)
        self.root.option_add("*TCombobox*Listbox.selectBackground", highlight)
        self.root.option_add("*TCombobox*Listbox.font", ("Consolas", 11))

        # 标题样式
        style.configure("Title.TLabel",
                        background=bg, foreground=self.COLOR_GOLD,
                        font=("Microsoft YaHei", 22, "bold"))
        style.configure("Subtitle.TLabel",
                        background=bg, foreground="#999",
                        font=("Microsoft YaHei", 10))

    # ── 默认机器 ───────────────────────────────────────────

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

    # ── 主界面搭建 ─────────────────────────────────────────

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=(16, 10))
        main.pack(fill=tk.BOTH, expand=True)

        # 标题
        ttk.Label(main, text="恩尼格玛密码机", style="Title.TLabel").pack(pady=(0, 0))
        ttk.Label(main, text="Enigma I / M3  ·  仿真模拟器",
                  style="Subtitle.TLabel").pack(pady=(0, 12))

        # 标签页
        nb = ttk.Notebook(main)
        nb.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        crypto_frame = ttk.Frame(nb, padding=8)
        config_frame = ttk.Frame(nb, padding=8)
        rotor_frame = ttk.Frame(nb, padding=8)

        nb.add(crypto_frame, text="  加密 / 解密  ")
        nb.add(config_frame, text="  机器配置  ")
        nb.add(rotor_frame, text="  转子状态  ")

        self._build_crypto_tab(crypto_frame)
        self._build_config_tab(config_frame)
        self._build_rotor_tab(rotor_frame)

        # 底部状态栏
        status_bar = ttk.Frame(self.root)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_var = tk.StringVar(value="就绪 — 请配置机器后开始加解密")
        ttk.Label(status_bar, textvariable=self.status_var,
                  background=self.COLOR_ACCENT, foreground=self.COLOR_TEXT,
                  font=("Microsoft YaHei", 9), padding=(12, 4)).pack(fill=tk.X)

    # ── 加密/解密标签页 ───────────────────────────────────

    def _build_crypto_tab(self, parent):
        # 输入区
        in_frame = ttk.LabelFrame(parent, text=" 输入文本 ", padding=8)
        in_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        self.input_text = tk.Text(in_frame, height=5, width=60,
                                  font=("Consolas", 12),
                                  bg=self.COLOR_SURFACE, fg=self.COLOR_TEXT,
                                  insertbackground=self.COLOR_GOLD,
                                  relief="flat", borderwidth=4,
                                  highlightthickness=0, padx=8, pady=8)
        self.input_text.pack(fill=tk.BOTH, expand=True)
        self.input_text.insert("1.0", "HELLO WORLD")

        # 按钮栏（居中）
        btn_bar = ttk.Frame(parent)
        btn_bar.pack(fill=tk.X, pady=8)
        inner = ttk.Frame(btn_bar)
        inner.pack(expand=True)

        ttk.Button(inner, text="🔒  加密", style="Accent.TButton",
                   command=self._encrypt).pack(side=tk.LEFT, padx=6)
        ttk.Button(inner, text="🔓  解密",
                   command=self._decrypt).pack(side=tk.LEFT, padx=6)
        ttk.Button(inner, text="🗑  清空输入",
                   command=self._clear_input).pack(side=tk.LEFT, padx=6)
        ttk.Button(inner, text="📋  复制输出",
                   command=self._copy_output).pack(side=tk.LEFT, padx=6)

        # 输出区
        out_frame = ttk.LabelFrame(parent, text=" 输出结果 ", padding=8)
        out_frame.pack(fill=tk.BOTH, expand=True)

        self.output_text = tk.Text(out_frame, height=5, width=60,
                                   font=("Consolas", 12, "bold"),
                                   bg=self.COLOR_SURFACE, fg=self.COLOR_GREEN,
                                   insertbackground=self.COLOR_GOLD,
                                   relief="flat", borderwidth=4,
                                   highlightthickness=0, padx=8, pady=8)
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
            self.status_var.set(f"加密完成 — 转子位置: {' '.join(self.enigma.rotor_positions)}")
            self._draw_rotors()
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

    # ── 配置标签页 ─────────────────────────────────────────

    def _build_config_tab(self, parent):
        # 预设配置
        preset_frame = ttk.LabelFrame(parent, text=" 预设配置 ", padding=8)
        preset_frame.pack(fill=tk.X, pady=(0, 8))

        row = ttk.Frame(preset_frame)
        row.pack(fill=tk.X)
        ttk.Label(row, text="选择预设：").pack(side=tk.LEFT, padx=(0, 8))

        self.preset_var = tk.StringVar()
        preset_cb = ttk.Combobox(row, textvariable=self.preset_var,
                                 values=list(PRESETS.keys()),
                                 state="readonly", width=36)
        preset_cb.pack(side=tk.LEFT, padx=(0, 8))
        preset_cb.bind("<<ComboboxSelected>>", self._on_preset_selected)
        ttk.Button(row, text="加载预设",
                   command=self._load_preset).pack(side=tk.LEFT)

        # 预设描述
        self.preset_desc_var = tk.StringVar()
        ttk.Label(row, textvariable=self.preset_desc_var,
                  foreground="#999", font=("Microsoft YaHei", 8)).pack(side=tk.LEFT, padx=12)

        # ── 转子配置 ──
        rotor_frame = ttk.LabelFrame(parent, text=" 转子配置（右 → 左）", padding=8)
        rotor_frame.pack(fill=tk.X, pady=(0, 8))

        # 表头
        hdr = ttk.Frame(rotor_frame)
        hdr.pack(fill=tk.X, pady=(0, 4))
        for txt, w in [("转子位置", 10), ("类型", 7), ("环设置", 7),
                        ("初始位置", 7), ("缺口", 4)]:
            ttk.Label(hdr, text=txt, width=w,
                      font=("Microsoft YaHei", 8, "bold"),
                      foreground=self.COLOR_GOLD).pack(side=tk.LEFT, padx=4)

        # 三行转子
        self._rotor_widgets = []
        labels = ["右转子 (快速)", "中转子", "左转子 (慢速)"]
        for i, lbl in enumerate(labels):
            rframe = ttk.Frame(rotor_frame)
            rframe.pack(fill=tk.X, pady=2)

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

            # 自动更新缺口显示
            type_var.trace_add("write",
                               lambda *_, i=i: self._on_rotor_type_change(i))
            self._on_rotor_type_change(i)

        # ── 反射器 ──
        ref_frame = ttk.Frame(rotor_frame)
        ref_frame.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(ref_frame, text="反射器类型：",
                  font=("Microsoft YaHei", 9, "bold")).pack(side=tk.LEFT, padx=(0, 8))
        self.reflector_var = tk.StringVar(value="B")
        ttk.Combobox(ref_frame, textvariable=self.reflector_var,
                     values=["B", "C"], state="readonly", width=5).pack(side=tk.LEFT)

        # ── 插线板配置 ──
        pb_frame = ttk.LabelFrame(parent, text=" 插线板 (Steckerbrett) ", padding=8)
        pb_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        # 插线板可视化画布
        self.pb_canvas = tk.Canvas(pb_frame, height=110,
                                   bg=self.COLOR_SURFACE,
                                   highlightthickness=0)
        self.pb_canvas.pack(fill=tk.X, padx=4, pady=4)

        # 控制行
        ctrl = ttk.Frame(pb_frame)
        ctrl.pack(fill=tk.X, pady=4)

        ttk.Label(ctrl, text="添加连接：").pack(side=tk.LEFT, padx=(0, 6))

        self.plug_a_var = tk.StringVar()
        self.plug_a_combo = ttk.Combobox(ctrl, textvariable=self.plug_a_var,
                                         values=list(string.ascii_uppercase),
                                         state="readonly", width=4)
        self.plug_a_combo.pack(side=tk.LEFT, padx=4)
        self.plug_a_combo.bind("<<ComboboxSelected>>", self._on_plug_a_select)

        ttk.Label(ctrl, text="↔", font=("Arial", 12, "bold"),
                  foreground=self.COLOR_HIGHLIGHT).pack(side=tk.LEFT, padx=4)

        self.plug_b_var = tk.StringVar()
        self.plug_b_combo = ttk.Combobox(ctrl, textvariable=self.plug_b_var,
                                         values=list(string.ascii_uppercase),
                                         state="readonly", width=4)
        self.plug_b_combo.pack(side=tk.LEFT, padx=4)

        ttk.Button(ctrl, text="➕ 添加", command=self._add_plug).pack(side=tk.LEFT, padx=10)
        ttk.Button(ctrl, text="🗑 清除全部",
                   command=self._clear_plugs).pack(side=tk.LEFT, padx=6)

        # 当前连接列表
        list_frame = ttk.Frame(pb_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        ttk.Label(list_frame, text="当前连接：",
                  font=("Microsoft YaHei", 9, "bold")).pack(anchor=tk.W)
        self.pb_list_var = tk.StringVar(value="(无)")
        ttk.Label(list_frame, textvariable=self.pb_list_var,
                  font=("Consolas", 11),
                  foreground=self.COLOR_GREEN).pack(anchor=tk.W, pady=2)

        # ── 应用按钮 ──
        ttk.Button(parent, text="✔  应用配置", style="Accent.TButton",
                   command=self._apply_config).pack(pady=12)

    # ── 转子状态标签页 ─────────────────────────────────────

    def _build_rotor_tab(self, parent):
        # 可视化画布
        self.rotor_canvas = tk.Canvas(parent, bg=self.COLOR_SURFACE,
                                      height=280, highlightthickness=0)
        self.rotor_canvas.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # 控制区
        ctrl = ttk.Frame(parent)
        ctrl.pack(fill=tk.X, pady=8)
        inner_ctrl = ttk.Frame(ctrl)
        inner_ctrl.pack(expand=True)

        ttk.Label(inner_ctrl, text="手动设置转子位置：",
                  font=("Microsoft YaHei", 9, "bold")).pack(side=tk.LEFT, padx=(0, 10))

        self.manual_pos_vars = []
        self.manual_pos_combos = []
        for i, lbl in enumerate(["右", "中", "左"]):
            ttk.Label(inner_ctrl, text=f"{lbl}：").pack(side=tk.LEFT, padx=(8, 2))
            var = tk.StringVar(value="A")
            cb = ttk.Combobox(inner_ctrl, textvariable=var,
                              values=list(string.ascii_uppercase),
                              state="readonly", width=4)
            cb.pack(side=tk.LEFT, padx=2)
            self.manual_pos_vars.append(var)
            self.manual_pos_combos.append(cb)

        ttk.Button(inner_ctrl, text="设置位置",
                   command=self._set_manual_positions).pack(side=tk.LEFT, padx=12)
        ttk.Button(inner_ctrl, text="🔄 重置",
                   command=self._reset_machine).pack(side=tk.LEFT, padx=6)
        ttk.Button(inner_ctrl, text="▶ 单步",
                   command=self._single_step).pack(side=tk.LEFT, padx=6)

    # ── 刷新全部显示 ───────────────────────────────────────

    def _refresh_all(self):
        self._draw_rotors()
        self._draw_plugboard()
        self._update_pb_list()
        self._update_plug_options()
        self._update_manual_positions()

    # ── 转子显示 ───────────────────────────────────────────

    def _draw_rotors(self):
        canvas = self.rotor_canvas
        canvas.delete("all")
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w < 50 or h < 50:
            return

        rotors = self.enigma.rotors   # 右→左: [III, II, I]
        labels = ["右转子 (快速)", "中转子", "左转子 (慢速)",
                  f"{self.enigma.reflector.reflector_type}型反射器"]

        n = len(rotors)
        padding_x = 40
        gap = 24
        usable = w - 2 * padding_x - (n * gap)
        box_w = usable // (n + 1)
        box_h = min(200, h - 60)
        start_y = 20

        for i, rotor in enumerate(rotors):
            x0 = padding_x + i * (box_w + gap + (gap if i > 0 else 0))
            y0 = start_y
            x1 = x0 + box_w

            # 转子主体
            canvas.create_rectangle(x0, y0, x1, start_y + box_h,
                                    fill=self.COLOR_ACCENT,
                                    outline=self.COLOR_HIGHLIGHT, width=2)
            # 转子标签
            canvas.create_text((x0 + x1) // 2, y0 - 12,
                               text=f"{rotor.rotor_type}型",
                               font=("Microsoft YaHei", 10, "bold"),
                               fill=self.COLOR_GOLD)

            # 转子窗口（显示当前位置）
            win_y = y0 + 20
            win_h = 36
            canvas.create_rectangle(x0 + 12, win_y, x1 - 12, win_y + win_h,
                                    fill="#111", outline=self.COLOR_GOLD, width=2)
            canvas.create_text((x0 + x1) // 2, win_y + win_h // 2,
                               text=rotor.position_char,
                               font=("Consolas", 20, "bold"),
                               fill=self.COLOR_GREEN)

            # 上一字母
            prev_c = chr((rotor.position - 1) % 26 + 65)
            canvas.create_text((x0 + x1) // 2, win_y - 10,
                               text=prev_c, font=("Consolas", 10),
                               fill="#666")
            # 下一字母
            next_c = chr((rotor.position + 1) % 26 + 65)
            canvas.create_text((x0 + x1) // 2, win_y + win_h + 10,
                               text=next_c, font=("Consolas", 10),
                               fill="#666")

            # 环设置
            canvas.create_text((x0 + x1) // 2, start_y + box_h - 36,
                               text=f"环: {rotor.ring_char}",
                               font=("Microsoft YaHei", 9),
                               fill=self.COLOR_TEXT)
            # 缺口
            canvas.create_text((x0 + x1) // 2, start_y + box_h - 18,
                               text=f"缺口: {rotor.notch}",
                               font=("Consolas", 9),
                               fill=self.COLOR_HIGHLIGHT)

        # 反射器
        rx0 = padding_x + n * (box_w + gap) + gap
        rx1 = rx0 + box_w - 20
        canvas.create_rectangle(rx0, y0, rx1, start_y + box_h,
                                fill="#2d1b69", outline="#9b59b6", width=2)
        canvas.create_text((rx0 + rx1) // 2, y0 - 12,
                           text=f"{self.enigma.reflector.reflector_type}型反射器",
                           font=("Microsoft YaHei", 10, "bold"),
                           fill="#9b59b6")

        # 信号流向箭头
        arrow_y = start_y + box_h + 20
        for i in range(n - 1):
            ax = padding_x + (i + 1) * (box_w + gap)
            canvas.create_line(ax, arrow_y, ax + gap, arrow_y,
                               arrow=tk.LAST, fill=self.COLOR_GOLD, width=2)
        # 反射器方向
        arx = padding_x + n * (box_w + gap) + gap // 2
        canvas.create_line(arx, arrow_y, arx + gap // 2, arrow_y,
                           arrow=tk.LAST, fill="#9b59b6", width=2)

    def _update_manual_positions(self):
        for i, rotor in enumerate(self.enigma.rotors):
            self.manual_pos_vars[i].set(rotor.position_char)

    def _set_manual_positions(self):
        try:
            for i, var in enumerate(self.manual_pos_vars):
                pos = ord(var.get()) - 65
                self.enigma.rotors[i].position = pos
                self.enigma.initial_positions[i] = pos
            self._draw_rotors()
            self.status_var.set("转子位置已更新")
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def _single_step(self):
        """手动单步转动转子"""
        self.enigma._step_rotors()
        self._update_manual_positions()
        self._draw_rotors()
        self.status_var.set(f"单步完成 — 位置: {' '.join(self.enigma.rotor_positions)}")

    def _reset_machine(self):
        self.enigma.reset()
        self._refresh_all()
        self.status_var.set("机器已重置到初始状态")

    # ── 转子类型变更 ───────────────────────────────────────

    def _on_rotor_type_change(self, index):
        rt = self._rotor_widgets[index]["type"].get()
        if rt in ROTOR_SPECS:
            self._rotor_widgets[index]["notch"].set(ROTOR_SPECS[rt][1])

    # ── 插线板 ─────────────────────────────────────────────

    def _update_plug_options(self):
        """过滤插线板下拉选项：仅显示未被占用的字母"""
        used = self.enigma.plugboard.used_letters()
        available = [c for c in string.ascii_uppercase if c not in used]

        a_val = self.plug_a_var.get()
        b_val = self.plug_b_var.get()

        # A 组合框：排除所有已用字母，但保留当前选中值
        opts_a = list(available)
        if a_val and a_val not in opts_a:
            opts_a.append(a_val)
        self.plug_a_combo["values"] = sorted(opts_a)

        # B 组合框：排除已用字母 + A 已选择的字母
        opts_b = [c for c in available if c != a_val]
        if b_val and b_val not in opts_b and b_val not in used:
            opts_b.append(b_val)
        self.plug_b_combo["values"] = sorted(opts_b)

    def _on_plug_a_select(self, event=None):
        """当用户在 A 组合框选择字母后，更新 B 组合框选项"""
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

        # 添加新连接
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
        y_top, y_bot = 22, h - 22

        # 绘制 A-Z 标签
        for i, c in enumerate(letters):
            x = (i + 0.5) * spacing
            is_used = self.enigma.plugboard.mapping[c] != c
            color = self.COLOR_GREEN if is_used else "#555"
            canvas.create_text(x, y_top, text=c,
                               font=("Consolas", 12, "bold"), fill=color)
            canvas.create_text(x, y_bot, text=c,
                               font=("Consolas", 12, "bold"), fill=color)

        # 绘制连线
        for a, b in pairs:
            ia, ib = ord(a) - 65, ord(b) - 65
            xa = (ia + 0.5) * spacing
            xb = (ib + 0.5) * spacing
            mid = (xa + xb) / 2
            # 平滑贝塞尔曲线
            canvas.create_line(xa, y_top + 10, mid, h / 2,
                               xb, y_top + 10,
                               fill=self.COLOR_HIGHLIGHT, width=2, smooth=True)
            # 端点圆圈
            r = 8
            canvas.create_oval(xa - r, y_top + 2, xa + r, y_top + 18,
                               fill=self.COLOR_ACCENT, outline=self.COLOR_HIGHLIGHT, width=2)
            canvas.create_text(xa, y_top + 10, text=a,
                               font=("Consolas", 9, "bold"), fill="white")
            canvas.create_oval(xb - r, y_top + 2, xb + r, y_top + 18,
                               fill=self.COLOR_ACCENT, outline=self.COLOR_HIGHLIGHT, width=2)
            canvas.create_text(xb, y_top + 10, text=b,
                               font=("Consolas", 9, "bold"), fill="white")

    def _update_pb_list(self):
        pairs = self.enigma.plugboard.get_pairs()
        if not pairs:
            self.pb_list_var.set("(无连接)")
        else:
            self.pb_list_var.set("  ".join(f"{a}↔{b}" for a, b in pairs))

    # ── 预设配置 ───────────────────────────────────────────

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

        # 更新转子 UI
        for i, rt in enumerate(preset["rotors"]):
            self._rotor_widgets[i]["type"].set(rt)
            self._rotor_widgets[i]["ring"].set(preset["rings"][i])
            self._rotor_widgets[i]["pos"].set(preset["positions"][i])

        # 更新反射器
        self.reflector_var.set(preset["reflector"])

        # 更新插线板
        self.enigma.plugboard = Plugboard(preset["plugs"])

        # 同步按钮位置
        for i, pos_char in enumerate(preset["positions"]):
            self.manual_pos_vars[i].set(pos_char)

        self._refresh_all()
        self.status_var.set(f"已加载预设: {name}  —  {preset['desc']}")

    # ── 应用配置 ───────────────────────────────────────────

    def _apply_config(self):
        try:
            # 从 UI 读取配置
            rotor_types = [w["type"].get() for w in self._rotor_widgets]
            ring_settings = [ord(w["ring"].get()) - 65 for w in self._rotor_widgets]
            positions = [ord(w["pos"].get()) - 65 for w in self._rotor_widgets]
            reflector = self.reflector_var.get()
            plug_pairs = self.enigma.plugboard.get_pairs()

            # 验证转子不重复
            if len(set(rotor_types)) != 3:
                messagebox.showerror("配置错误",
                                     "三个转子不能重复——真实的恩尼格玛机每台只配有一套转子（每种型号一个）。")
                return

            # 创建新机器
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
                f"转子: {'-'.join(rotor_types)}, "
                f"环: {''.join(chr(r+65) for r in ring_settings)}, "
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
