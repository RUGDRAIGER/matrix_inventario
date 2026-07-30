import tkinter as tk
from tkinter import ttk

import customtkinter as ctk

# --- Tema Matrix ---
BG = "#000000"
BG_ALT = "#0D0D0D"
PANEL = "#121212"
PANEL_ALT = "#1A1A1A"
ACCENT = "#00FF66"
ACCENT_DIM = "#00CC52"
ACCENT_HOVER = "#003322"
TEXT = ACCENT
TEXT_DIM = "#00BB55"
FONT_UI = ("Segoe UI", 13)
FONT_TITLE = ("Consolas", 16, "bold")
FONT_HEADING = ("Consolas", 14, "bold")
FONT_MONO = ("Consolas", 12)
PAD = 16


def apply_matrix_theme():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("green")
    style = ttk.Style()
    style.theme_use("clam")
    style.configure(
        "Matrix.Treeview",
        background=PANEL,
        foreground=ACCENT,
        fieldbackground=PANEL,
        bordercolor=ACCENT,
        rowheight=30,
        font=("Consolas", 11),
    )
    style.configure(
        "Matrix.Treeview.Heading",
        background=BG,
        foreground=ACCENT,
        font=("Consolas", 11, "bold"),
        bordercolor=ACCENT,
    )
    style.map(
        "Matrix.Treeview",
        background=[("selected", ACCENT_HOVER)],
        foreground=[("selected", ACCENT)],
    )


class StyledEntry(ctk.CTkEntry):
    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            fg_color=BG_ALT,
            border_color=ACCENT,
            border_width=2,
            text_color=ACCENT,
            placeholder_text_color=TEXT_DIM,
            font=FONT_MONO,
            **kwargs,
        )


class StyledButton(ctk.CTkButton):
    def __init__(self, master, primary=True, **kwargs):
        kwargs.setdefault("font", FONT_UI)
        if primary:
            kwargs.setdefault("fg_color", ACCENT)
            kwargs.setdefault("hover_color", ACCENT_DIM)
            kwargs.setdefault("text_color", BG)
        else:
            kwargs.setdefault("fg_color", PANEL)
            kwargs.setdefault("hover_color", PANEL_ALT)
            kwargs.setdefault("border_color", ACCENT)
            kwargs.setdefault("border_width", 2)
            kwargs.setdefault("text_color", ACCENT)
        super().__init__(master, **kwargs)


class StyledCombo(ctk.CTkComboBox):
    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            fg_color=BG_ALT,
            border_color=ACCENT,
            border_width=2,
            button_color=ACCENT,
            button_hover_color=ACCENT_DIM,
            dropdown_fg_color=PANEL,
            dropdown_text_color=ACCENT,
            dropdown_hover_color=ACCENT_HOVER,
            text_color=ACCENT,
            font=FONT_MONO,
            **kwargs,
        )


class MatrixLabel(ctk.CTkLabel):
    def __init__(self, master, dim=False, **kwargs):
        kwargs.setdefault("text_color", TEXT_DIM if dim else TEXT)
        kwargs.setdefault("font", FONT_UI)
        super().__init__(master, **kwargs)


class SectionTitle(ctk.CTkLabel):
    def __init__(self, master, text, **kwargs):
        super().__init__(
            master,
            text=text,
            font=FONT_TITLE,
            text_color=ACCENT,
            **kwargs,
        )


class ProgressPanel(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=PANEL, corner_radius=8, **kwargs)
        self.label = MatrixLabel(self, text="Listo para escanear", dim=True)
        self.label.pack(fill="x", padx=PAD, pady=(PAD, 4))
        self.bar = ctk.CTkProgressBar(
            self, height=14, progress_color=ACCENT,
            fg_color=BG_ALT, border_color=ACCENT, border_width=1,
        )
        self.bar.pack(fill="x", padx=PAD, pady=(0, 4))
        self.bar.set(0)
        self.pct_label = ctk.CTkLabel(
            self, text="0%", font=FONT_HEADING, text_color=ACCENT,
        )
        self.pct_label.pack(pady=(0, PAD))

    def show(self):
        self.grid(row=1, column=0, sticky="ew", padx=PAD, pady=(0, 8))

    def hide(self):
        self.grid_remove()

    def update_progress(self, percent, message=""):
        pct = max(0, min(100, int(percent)))
        self.bar.set(pct / 100)
        self.pct_label.configure(text=f"{pct}%")
        if message:
            self.label.configure(text=message)


class MatrixListbox(tk.Listbox):
    def __init__(self, master, **kwargs):
        defaults = dict(
            bg=PANEL,
            fg=ACCENT,
            selectbackground=ACCENT_HOVER,
            selectforeground=ACCENT,
            highlightthickness=2,
            highlightcolor=ACCENT,
            highlightbackground=ACCENT,
            font=("Consolas", 11),
            relief="flat",
            bd=0,
        )
        defaults.update(kwargs)
        super().__init__(master, **defaults)


class ResponsiveModal(ctk.CTkToplevel):
    """Modal con footer fijo: botones siempre visibles."""

    def __init__(self, parent, title, min_w=420, min_h=380, width_ratio=0.35, height_ratio=0.55):
        super().__init__(parent)
        self.title(title)
        self.configure(fg_color=BG)
        self.minsize(min_w, min_h)
        self.grab_set()
        self.transient(parent)

        sw = parent.winfo_screenwidth()
        sh = parent.winfo_screenheight()
        w = max(min_w, int(sw * width_ratio))
        h = max(min_h, int(sh * height_ratio))
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.body = ctk.CTkScrollableFrame(self, fg_color=PANEL, corner_radius=8)
        self.body.grid(row=0, column=0, sticky="nsew", padx=PAD, pady=(PAD, 8))

        self.footer = ctk.CTkFrame(self, fg_color=BG_ALT, height=64)
        self.footer.grid(row=1, column=0, sticky="ew", padx=PAD, pady=(0, PAD))
        self.footer.grid_propagate(False)
        self.footer.grid_columnconfigure(0, weight=1)

        btn_row = ctk.CTkFrame(self.footer, fg_color="transparent")
        btn_row.pack(side="right", padx=PAD, pady=12)

        self.btn_cancel = StyledButton(btn_row, text="Cancelar", primary=False, command=self.destroy)
        self.btn_cancel.pack(side="right")
        self.btn_save = StyledButton(btn_row, text="Guardar", command=self._on_save)
        self.btn_save.pack(side="right", padx=(0, 10))

    def _on_save(self):
        pass


def create_matrix_tree(parent, columns, headings, stretch_col=None):
    tree = ttk.Treeview(parent, columns=columns, show="headings", style="Matrix.Treeview")
    for col, (txt, w) in zip(columns, headings):
        tree.heading(col, text=txt)
        anchor = "w" if col == stretch_col else "center"
        tree.column(col, width=w, anchor=anchor, stretch=(col == stretch_col))
    vsb = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    parent.grid_rowconfigure(0, weight=1)
    parent.grid_columnconfigure(0, weight=1)
    return tree


def form_field(parent, label, entry_cls=StyledEntry, **entry_kw):
    MatrixLabel(parent, text=label, anchor="w").pack(fill="x", pady=(8, 2))
    entry = entry_cls(parent, **entry_kw)
    entry.pack(fill="x", pady=(0, 4))
    return entry


def accessory_block(parent, title):
    """Bloque de accesorio con etiquetas Marca / Modelo / Serie."""
    MatrixLabel(parent, text=title).pack(anchor="w", pady=(8, 4))
    frm = ctk.CTkFrame(parent, fg_color=PANEL_ALT, corner_radius=6)
    frm.pack(fill="x", pady=(0, 6))
    frm.grid_columnconfigure((0, 1, 2), weight=1)
    fields = {}
    for i, lbl in enumerate(("Marca", "Modelo", "Serie")):
        col = ctk.CTkFrame(frm, fg_color="transparent")
        col.grid(row=0, column=i, sticky="ew", padx=6, pady=6)
        MatrixLabel(col, text=lbl, dim=True).pack(anchor="w")
        e = StyledEntry(col)
        e.pack(fill="x", pady=(2, 0))
        fields[lbl.lower()] = e
    return fields


def page_toolbar(parent, title, buttons):
    """Barra superior unificada: título + botones alineados a la derecha."""
    frame = ctk.CTkFrame(parent, fg_color=PANEL, corner_radius=8)
    frame.grid_columnconfigure(0, weight=1)
    SectionTitle(frame, title).grid(row=0, column=0, sticky="w", padx=PAD, pady=PAD)
    btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
    btn_frame.grid(row=0, column=1, sticky="e", padx=PAD, pady=PAD)
    for i, (text, cmd, primary) in enumerate(buttons):
        StyledButton(btn_frame, text=text, command=cmd, primary=primary).pack(
            side="left", padx=(8 if i else 0, 0)
        )
    return frame


def unit_selector(parent, label="Seleccionar Unidad:"):
    """Fila con etiqueta + combobox de unidades."""
    frame = ctk.CTkFrame(parent, fg_color=PANEL_ALT, corner_radius=8)
    frame.grid_columnconfigure(1, weight=1)
    MatrixLabel(frame, text=label).grid(row=0, column=0, padx=PAD, pady=PAD, sticky="w")
    var = tk.StringVar()
    combo = StyledCombo(frame, variable=var)
    combo.grid(row=0, column=1, padx=(0, PAD), pady=PAD, sticky="ew")
    return frame, var, combo
