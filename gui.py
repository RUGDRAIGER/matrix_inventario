import threading
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

import database as db
from scanner import scan_hardware
from ui_components import (
    ACCENT, ACCENT_DIM, BG, BG_ALT, PAD, PANEL, PANEL_ALT,
    FONT_TITLE, FONT_MONO,
    MatrixLabel, ProgressPanel, ResponsiveModal,
    SectionTitle, StyledButton, StyledCombo, StyledEntry,
    accessory_block, apply_matrix_theme, create_matrix_tree,
    form_field, page_toolbar, unit_selector,
)


def _default_accesorios():
    return [
        {"tipo": "MONITOR", "etiqueta": "Monitor 1", "marca": "", "modelo": "", "serie": ""},
        {"tipo": "WEBCAM", "etiqueta": "Webcam 1", "marca": "", "modelo": "", "serie": ""},
    ]


def _load_unidades_combo(combo, var, ids_dict, reset=False):
    unidades = db.get_unidades()
    names = [u["nombre_unidad"] for u in unidades]
    ids_dict.clear()
    ids_dict.update({u["nombre_unidad"]: u["id"] for u in unidades})
    placeholder = "(Seleccionar unidad)"
    options = [placeholder] + names if names else [placeholder]
    combo.configure(values=options)
    current = var.get()
    if reset:
        var.set(placeholder)
        return None, None
    if current in ids_dict:
        var.set(current)
        return current, ids_dict[current]
    if current == placeholder:
        var.set(placeholder)
        return None, None
    if names:
        var.set(names[0])
        return names[0], ids_dict[names[0]]
    var.set(placeholder)
    return None, None


# --- Modales ---

class FuncionarioModal(ResponsiveModal):
    def __init__(self, parent, on_save, funcionario=None, default_unidad_id=None):
        title = "Editar Funcionario" if funcionario else "Nuevo Funcionario"
        super().__init__(parent, title, min_w=460, min_h=480)
        self.on_save_cb = on_save
        self.fields = {}

        unidades = db.get_unidades()
        self._unidad_map = {u["nombre_unidad"]: u["id"] for u in unidades}
        unidad_names = list(self._unidad_map.keys()) or ["(Sin unidades)"]

        MatrixLabel(self.body, text="Unidad").pack(anchor="w", pady=(8, 2))
        self.unidad_var = tk.StringVar()
        self.unidad_combo = StyledCombo(self.body, variable=self.unidad_var, values=unidad_names)
        self.unidad_combo.pack(fill="x", pady=(0, 4))

        if funcionario and funcionario["unidad_id"]:
            u = db.get_unidad_by_id(funcionario["unidad_id"])
            if u:
                self.unidad_var.set(u["nombre_unidad"])
        elif default_unidad_id:
            u = db.get_unidad_by_id(default_unidad_id)
            if u:
                self.unidad_var.set(u["nombre_unidad"])

        for key, lbl in [
            ("grado", "Grado"), ("nombre", "Nombres"), ("apellido", "Apellidos"),
            ("dotacion", "Dotación"), ("cargo", "Cargo"),
        ]:
            e = form_field(self.body, lbl)
            if funcionario:
                e.insert(0, funcionario[key] or "")
            self.fields[key] = e

        self.btn_save.configure(command=self._save)

    def _save(self):
        data = {k: v.get().strip() for k, v in self.fields.items()}
        if not data["nombre"] or not data["apellido"]:
            messagebox.showwarning("Validación", "Nombres y Apellidos son obligatorios.")
            return
        unidad_name = self.unidad_var.get()
        unidad_id = self._unidad_map.get(unidad_name)
        if not unidad_id:
            messagebox.showwarning("Validación", "Debe seleccionar una Unidad.")
            return
        data["unidad_id"] = unidad_id
        self.on_save_cb(data)
        self.destroy()


class UnidadEditModal(ResponsiveModal):
    def __init__(self, parent, unidad_id, on_save):
        super().__init__(parent, "Editar Unidad", min_w=440, min_h=320)
        self.unidad_id = unidad_id
        self.on_save_cb = on_save
        unidad = db.get_unidad_by_id(unidad_id)
        self.fields = {}
        for key, lbl in [
            ("nombre_unidad", "Unidad"),
            ("centro_costo", "Centro de Costo"),
        ]:
            e = form_field(self.body, lbl)
            e.insert(0, unidad[key] or "")
            self.fields[key] = e
        self.btn_save.configure(command=self._save)

    def _save(self):
        data = {k: v.get().strip() for k, v in self.fields.items()}
        if not data["nombre_unidad"]:
            messagebox.showwarning("Validación", "El nombre de la Unidad es obligatorio.")
            return
        try:
            u = db.get_unidad_by_id(self.unidad_id)
            db.update_unidad(
                self.unidad_id, data["nombre_unidad"], data["centro_costo"],
                u.get("ubicacion") or "", u["sap"] or "",
            )
            self.on_save_cb()
            self.destroy()
        except Exception as ex:
            messagebox.showerror("Error", f"No se pudo actualizar: {ex}")


class UnidadModal(ResponsiveModal):
    def __init__(self, parent, on_save):
        super().__init__(parent, "Nueva Unidad", min_w=440, min_h=320)
        self.on_save_cb = on_save
        self.fields = {}
        for key, lbl in [
            ("nombre_unidad", "Unidad"),
            ("centro_costo", "Centro de Costo"),
        ]:
            self.fields[key] = form_field(self.body, lbl)
        self.btn_save.configure(command=self._save)

    def _save(self):
        data = {k: v.get().strip() for k, v in self.fields.items()}
        if not data["nombre_unidad"]:
            messagebox.showwarning("Validación", "El nombre de la Unidad es obligatorio.")
            return
        try:
            db.insert_unidad(data["nombre_unidad"], data["centro_costo"], "")
            self.on_save_cb()
            self.destroy()
        except Exception as ex:
            messagebox.showerror("Error", f"No se pudo crear la unidad: {ex}")


class PCEditModal(ResponsiveModal):
    def __init__(self, parent, pc_id, on_saved):
        super().__init__(parent, "Editar Equipo", min_w=680, min_h=520, width_ratio=0.5, height_ratio=0.75)
        self.pc_id = pc_id
        self.on_saved_cb = on_saved
        self.acc_blocks = []

        pc = db.get_pc_by_id(pc_id)
        accesorios = db.get_accesorios_by_pc(pc_id)
        funcs = db.get_funcionarios_by_pc(pc_id)
        unidad = db.get_unidad_by_id(pc["unidad_id"])

        SectionTitle(self.body, "Datos del PC").pack(anchor="w", pady=(0, 8))
        self.fields = {}
        for key, lbl in [
            ("marca", "Marca"), ("modelo", "Modelo"), ("serie", "Serie"),
            ("windows_version", "Windows"), ("procesador", "Procesador"),
            ("ram_gb", "RAM (GB)"), ("disco_detalle", "Almacenamiento"),
            ("office_version", "Office"), ("ip_address", "IP"), ("mac_address", "MAC"),
            ("ubicacion", "Ubicación"),
        ]:
            e = form_field(self.body, lbl)
            val = pc[key]
            if val is not None:
                e.insert(0, str(val))
            self.fields[key] = e

        SectionTitle(self.body, "Accesorios").pack(anchor="w", pady=(12, 8))
        self.acc_container = ctk.CTkFrame(self.body, fg_color="transparent")
        self.acc_container.pack(fill="x")
        items = [a for a in (accesorios if accesorios else _default_accesorios())
                 if a["tipo"] in ("MONITOR", "WEBCAM")]
        self._render_accesorios(items)

        SectionTitle(self.body, "Personal a Cargo").pack(anchor="w", pady=(12, 4))
        self.func_var = tk.StringVar()
        funcs_unidad = db.get_funcionarios_by_unidad(pc["unidad_id"]) if unidad else []
        self._func_map = {}
        func_names = []
        for f in funcs_unidad:
            label = f"{f['grado'] or ''} {f['nombre']} {f['apellido']}".strip()
            func_names.append(label)
            self._func_map[label] = f["id"]
        self.func_combo = StyledCombo(self.body, variable=self.func_var, values=func_names or ["(Sin funcionarios)"])
        self.func_combo.pack(fill="x", pady=4)
        if funcs and func_names:
            assigned = funcs[0]
            label = f"{assigned['grado'] or ''} {assigned['nombre']} {assigned['apellido']}".strip()
            if label in self._func_map:
                self.func_var.set(label)

        self.btn_save.configure(command=self._save)

    def _render_accesorios(self, items):
        for w in self.acc_container.winfo_children():
            w.destroy()
        self.acc_blocks = []
        for acc in items:
            title = acc.get("etiqueta") or acc["tipo"]
            fields = accessory_block(self.acc_container, title)
            for fld in ("marca", "modelo", "serie"):
                fields[fld].insert(0, acc.get(fld, "") or "")
            self.acc_blocks.append({
                "tipo": acc["tipo"],
                "etiqueta": acc.get("etiqueta", title),
                "fields": fields,
            })

    def _save(self):
        data = {k: v.get().strip() for k, v in self.fields.items()}
        try:
            data["ram_gb"] = float(data["ram_gb"]) if data["ram_gb"] else 0
        except ValueError:
            data["ram_gb"] = 0
        pc = db.get_pc_by_id(self.pc_id)
        db.update_pc(self.pc_id, pc["unidad_id"], data)
        db.delete_accesorios_by_pc(self.pc_id)
        for acc in self.acc_blocks:
            f = acc["fields"]
            db.insert_accesorio(
                self.pc_id, acc["tipo"],
                f["marca"].get(), f["modelo"].get(), f["serie"].get(),
                etiqueta=acc["etiqueta"],
            )
        fid = self._func_map.get(self.func_var.get())
        db.set_pc_funcionarios(self.pc_id, [fid] if fid else [])
        self.on_saved_cb()
        self.destroy()


# --- Páginas ---

class ScannerPage(ctk.CTkFrame):
    def __init__(self, master, refresh_callbacks=None):
        super().__init__(master, fg_color=BG)
        self.refresh_callbacks = refresh_callbacks or {}
        self._scanning = False
        self.acc_blocks = []
        self._unidad_ids = {}
        self._func_map = {}
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=PAD, pady=(PAD, 4))
        header.grid_columnconfigure(0, weight=1)
        SectionTitle(header, "Escáner y Registro General").grid(row=0, column=0, sticky="w")
        StyledButton(header, text="Escanear", width=120, command=self._scan).grid(row=0, column=1, sticky="e")

        self.progress = ProgressPanel(self)
        self.progress.grid(row=1, column=0, sticky="ew", padx=PAD, pady=(0, 8))
        self.progress.hide()

        scroll = ctk.CTkScrollableFrame(self, fg_color=BG)
        scroll.grid(row=2, column=0, sticky="nsew", padx=PAD, pady=8)

        SectionTitle(scroll, "Datos del PC").pack(anchor="w", pady=(0, 8))
        self.pc_fields = {}
        for key, lbl in [
            ("marca", "Marca"), ("modelo", "Modelo"), ("serie", "Número de Serie"),
            ("windows_version", "Versión Windows"), ("procesador", "Procesador"),
            ("ram_gb", "RAM (GB)"), ("disco_detalle", "Almacenamiento"),
            ("office_version", "Microsoft Office"), ("ip_address", "Dirección IP"),
            ("mac_address", "Dirección MAC"),
        ]:
            self.pc_fields[key] = form_field(scroll, lbl)

        SectionTitle(scroll, "Accesorios").pack(anchor="w", pady=(12, 8))
        self.acc_container = ctk.CTkFrame(scroll, fg_color="transparent")
        self.acc_container.pack(fill="x")
        self._render_accesorios(_default_accesorios())

        SectionTitle(scroll, "Unidad y Asignación").pack(anchor="w", pady=(16, 8))

        unidad_row = ctk.CTkFrame(scroll, fg_color="transparent")
        unidad_row.pack(fill="x", pady=(0, 8))
        unidad_row.grid_columnconfigure(1, weight=1)
        MatrixLabel(unidad_row, text="Unidad").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.unidad_var = tk.StringVar()
        self.unidad_combo = StyledCombo(unidad_row, variable=self.unidad_var, command=self._on_unidad_change)
        self.unidad_combo.grid(row=0, column=1, sticky="ew")
        StyledButton(unidad_row, text="Nueva Unidad", width=130, primary=False,
                      command=self._new_unidad).grid(row=0, column=2, padx=(8, 0))

        func_row = ctk.CTkFrame(scroll, fg_color="transparent")
        func_row.pack(fill="x", pady=(0, 8))
        func_row.grid_columnconfigure(1, weight=1)
        MatrixLabel(func_row, text="Personal a Cargo").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.func_var = tk.StringVar()
        self.func_combo = StyledCombo(func_row, variable=self.func_var)
        self.func_combo.grid(row=0, column=1, sticky="ew")
        StyledButton(func_row, text="+ Nuevo Funcionario", width=160, primary=False,
                      command=self._new_funcionario).grid(row=0, column=2, padx=(8, 0))

        self.ubicacion_entry = form_field(scroll, "Ubicación")

        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(fill="x", pady=16)
        StyledButton(btn_frame, text="Guardar", command=self._save).pack(side="left", padx=(0, 8))
        StyledButton(btn_frame, text="Limpiar", primary=False, command=self._clear).pack(side="left")

        self.refresh_unidades(reset=True)

    def _render_accesorios(self, items):
        for w in self.acc_container.winfo_children():
            w.destroy()
        self.acc_blocks = []
        for acc in items:
            title = acc.get("etiqueta") or acc["tipo"]
            fields = accessory_block(self.acc_container, title)
            for fld in ("marca", "modelo", "serie"):
                val = acc.get(fld, "")
                if val:
                    fields[fld].insert(0, val)
            self.acc_blocks.append({
                "tipo": acc["tipo"],
                "etiqueta": acc.get("etiqueta", title),
                "fields": fields,
            })

    def refresh_unidades(self, reset=False):
        _load_unidades_combo(self.unidad_combo, self.unidad_var, self._unidad_ids, reset=reset)
        if reset:
            self.func_combo.configure(values=["(Sin funcionarios)"])
            self.func_var.set("(Sin funcionarios)")
            self._func_map = {}
        elif self.unidad_var.get() in self._unidad_ids:
            self._refresh_funcionarios()
        else:
            self.func_combo.configure(values=["(Sin funcionarios)"])
            self.func_var.set("(Sin funcionarios)")
            self._func_map = {}

    def _on_unidad_change(self, _=None):
        self._refresh_funcionarios()

    def _refresh_funcionarios(self):
        unidad_id = self._unidad_ids.get(self.unidad_var.get())
        self._func_map = {}
        names = []
        if unidad_id:
            for f in db.get_funcionarios_by_unidad(unidad_id):
                label = f"{f['grado'] or ''} {f['nombre']} {f['apellido']} - {f['cargo'] or ''}".strip()
                names.append(label)
                self._func_map[label] = f["id"]
        self.func_combo.configure(values=names if names else ["(Sin funcionarios)"])
        self.func_var.set(names[0] if names else "(Sin funcionarios)")

    def _new_unidad(self):
        def on_saved():
            self.refresh_unidades(reset=False)
            self.refresh_callbacks.get("unidades", lambda: None)()
        UnidadModal(self.winfo_toplevel(), on_save=on_saved)

    def _new_funcionario(self):
        unidad_id = self._unidad_ids.get(self.unidad_var.get())

        def on_save(data):
            db.insert_funcionario(**data)
            self._refresh_funcionarios()
            self.refresh_callbacks.get("funcionarios", lambda: None)()

        FuncionarioModal(self.winfo_toplevel(), on_save, default_unidad_id=unidad_id)

    def _scan(self):
        if self._scanning:
            return
        self._scanning = True
        self.progress.show()
        self.progress.update_progress(0, "Preparando escaneo...")

        def progress_cb(pct, msg):
            self.after(0, lambda: self.progress.update_progress(pct, msg))

        def run():
            try:
                result = scan_hardware(progress_callback=progress_cb)
                self.after(0, lambda: self._apply_scan(result))
            except Exception as ex:
                self.after(0, lambda: messagebox.showerror("Error", f"Escaneo fallido: {ex}"))
            finally:
                self.after(1500, self._scan_done)

        threading.Thread(target=run, daemon=True).start()

    def _scan_done(self):
        self._scanning = False
        self.progress.hide()

    def _apply_scan(self, result):
        pc = result["pc"]
        for key, entry in self.pc_fields.items():
            entry.delete(0, tk.END)
            val = pc.get(key, "")
            entry.insert(0, str(val) if val is not None else "")
        self._render_accesorios(result["accesorios"])

    def _save(self):
        unidad_id = self._unidad_ids.get(self.unidad_var.get())
        if not unidad_id or self.unidad_var.get() == "(Seleccionar unidad)":
            messagebox.showwarning("Validación", "Debe seleccionar una Unidad.")
            return

        pc_data = {k: v.get().strip() for k, v in self.pc_fields.items()}
        pc_data["ubicacion"] = self.ubicacion_entry.get().strip()
        try:
            pc_data["ram_gb"] = float(pc_data["ram_gb"]) if pc_data["ram_gb"] else 0
        except ValueError:
            pc_data["ram_gb"] = 0

        pc_id = db.insert_pc(unidad_id, pc_data)
        for acc in self.acc_blocks:
            f = acc["fields"]
            db.insert_accesorio(
                pc_id, acc["tipo"],
                f["marca"].get(), f["modelo"].get(), f["serie"].get(),
                etiqueta=acc["etiqueta"],
            )
        fid = self._func_map.get(self.func_var.get())
        db.set_pc_funcionarios(pc_id, [fid] if fid else [])

        messagebox.showinfo("Éxito", "Registro guardado correctamente.")
        for cb in self.refresh_callbacks.values():
            cb()
        self._clear()

    def _clear(self):
        for entry in self.pc_fields.values():
            entry.delete(0, tk.END)
        self.ubicacion_entry.delete(0, tk.END)
        self._render_accesorios(_default_accesorios())
        self.refresh_unidades(reset=True)
        self.progress.update_progress(0, "Listo para escanear")


class UnidadesPage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=BG)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build()

    def _build(self):
        toolbar = page_toolbar(self, "Gestión de Unidades", [
            ("Nueva Unidad", self._new_unidad, True),
            ("Editar", self._edit, False),
            ("Eliminar", self._delete, False),
        ])
        toolbar.grid(row=0, column=0, sticky="ew", padx=PAD, pady=(PAD, 8))

        tree_frame = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=8)
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=PAD, pady=(0, PAD))
        inner = ctk.CTkFrame(tree_frame, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=8, pady=8)
        self.tree = create_matrix_tree(
            inner,
            ("id", "nombre_unidad", "centro_costo"),
            [("ID", 50), ("Unidad", 280), ("Centro de Costo", 200)],
            stretch_col="nombre_unidad",
        )
        self.tree.bind("<Double-1>", lambda e: self._edit())
        self.refresh()

    def _new_unidad(self):
        UnidadModal(self.winfo_toplevel(), on_save=self.refresh)

    def refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for u in db.get_unidades():
            self.tree.insert("", tk.END, values=(
                u["id"], u["nombre_unidad"], u["centro_costo"],
            ))

    def _selected_unidad_id(self):
        sel = self.tree.selection()
        return self.tree.item(sel[0])["values"][0] if sel else None

    def _edit(self):
        uid = self._selected_unidad_id()
        if not uid:
            messagebox.showinfo("Info", "Seleccione una unidad para editar.")
            return
        UnidadEditModal(self.winfo_toplevel(), uid, on_save=self.refresh)

    def _delete(self):
        uid = self._selected_unidad_id()
        if not uid:
            messagebox.showinfo("Info", "Seleccione una unidad para eliminar.")
            return
        u = db.get_unidad_by_id(uid)
        if messagebox.askyesno(
            "Confirmar",
            f"¿Eliminar la unidad '{u['nombre_unidad']}'?\n"
            "Se eliminarán también los PCs asociados.",
        ):
            db.delete_unidad(uid)
            self.refresh()


class EquiposPage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=BG)
        self._unidad_ids = {}
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build()

    def _build(self):
        toolbar = page_toolbar(self, "Gestión de Equipos", [
            ("Editar", self._edit, True),
            ("Eliminar PC", self._delete, False),
        ])
        toolbar.grid(row=0, column=0, sticky="ew", padx=PAD, pady=(PAD, 8))

        sel_frame, self.unidad_var, self.unidad_combo = unit_selector(self)
        sel_frame.grid(row=1, column=0, sticky="ew", padx=PAD, pady=(0, 8))
        self.unidad_combo.configure(command=self._on_unidad_change)

        tree_frame = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=8)
        tree_frame.grid(row=2, column=0, sticky="nsew", padx=PAD, pady=(0, PAD))
        inner = ctk.CTkFrame(tree_frame, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=8, pady=8)
        self.tree = create_matrix_tree(
            inner,
            ("id", "marca", "modelo", "serie", "procesador", "ram_gb", "ip_address", "ubicacion", "accesorios"),
            [("ID", 45), ("Marca", 90), ("Modelo", 110), ("Serie", 100),
             ("Procesador", 120), ("RAM", 50), ("IP", 95), ("Ubicación", 110), ("Accesorios", 150)],
            stretch_col="accesorios",
        )
        self.tree.bind("<Double-1>", lambda e: self._edit())
        self.refresh()

    def refresh(self):
        _load_unidades_combo(self.unidad_combo, self.unidad_var, self._unidad_ids)
        name = self.unidad_var.get()
        if name in self._unidad_ids:
            self._load_pcs(self._unidad_ids[name])
        else:
            self._clear_tree()

    def _on_unidad_change(self, choice):
        if choice in self._unidad_ids:
            self._load_pcs(self._unidad_ids[choice])

    def _clear_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _load_pcs(self, unidad_id):
        self._clear_tree()
        for pc in db.get_pcs_by_unidad(unidad_id):
            accs = db.get_accesorios_by_pc(pc["id"])
            acc_str = ", ".join(
                f"{a.get('etiqueta') or a['tipo']}: {a['marca']}" for a in accs
            )
            self.tree.insert("", tk.END, values=(
                pc["id"], pc["marca"], pc["modelo"], pc["serie"],
                pc["procesador"], pc["ram_gb"], pc["ip_address"],
                pc["ubicacion"] or "", acc_str,
            ))

    def _selected_pc_id(self):
        sel = self.tree.selection()
        return self.tree.item(sel[0])["values"][0] if sel else None

    def _edit(self):
        pc_id = self._selected_pc_id()
        if not pc_id:
            messagebox.showinfo("Info", "Seleccione un equipo para editar.")
            return
        PCEditModal(self.winfo_toplevel(), pc_id, on_saved=self.refresh)

    def _delete(self):
        pc_id = self._selected_pc_id()
        if not pc_id:
            messagebox.showinfo("Info", "Seleccione un equipo para eliminar.")
            return
        if messagebox.askyesno("Confirmar", "¿Eliminar este PC y sus accesorios?"):
            db.delete_pc(pc_id)
            choice = self.unidad_var.get()
            if choice in self._unidad_ids:
                self._load_pcs(self._unidad_ids[choice])


class FuncionariosPage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=BG)
        self._unidad_ids = {}
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build()

    def _build(self):
        toolbar = page_toolbar(self, "Gestión de Funcionarios", [
            ("Nuevo Funcionario", self._new, True),
            ("Editar", self._edit, False),
            ("Eliminar", self._delete, False),
        ])
        toolbar.grid(row=0, column=0, sticky="ew", padx=PAD, pady=(PAD, 8))

        sel_frame, self.unidad_var, self.unidad_combo = unit_selector(self)
        sel_frame.grid(row=1, column=0, sticky="ew", padx=PAD, pady=(0, 8))
        self.unidad_combo.configure(command=self._on_unidad_change)

        tree_frame = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=8)
        tree_frame.grid(row=2, column=0, sticky="nsew", padx=PAD, pady=(0, PAD))
        inner = ctk.CTkFrame(tree_frame, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=8, pady=8)
        self.tree = create_matrix_tree(
            inner,
            ("id", "grado", "nombre", "apellido", "dotacion", "cargo", "unidad"),
            [("ID", 50), ("Grado", 70), ("Nombres", 110), ("Apellidos", 110),
             ("Dotación", 90), ("Cargo", 120), ("Unidad", 140)],
            stretch_col="unidad",
        )
        self.refresh()

    def refresh(self):
        _load_unidades_combo(self.unidad_combo, self.unidad_var, self._unidad_ids)
        self._load_funcionarios()

    def _on_unidad_change(self, _=None):
        self._load_funcionarios()

    def _load_funcionarios(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        unidad_id = self._unidad_ids.get(self.unidad_var.get())
        if not unidad_id:
            return
        for f in db.get_funcionarios_by_unidad(unidad_id):
            self.tree.insert("", tk.END, values=(
                f["id"], f["grado"], f["nombre"], f["apellido"],
                f["dotacion"], f["cargo"], f["nombre_unidad"] or "",
            ))

    def _current_unidad_id(self):
        return self._unidad_ids.get(self.unidad_var.get())

    def _new(self):
        uid = self._current_unidad_id()
        if not uid:
            messagebox.showwarning("Validación", "Seleccione una Unidad primero.")
            return

        def on_save(data):
            db.insert_funcionario(**data)
            self.refresh()
        FuncionarioModal(self.winfo_toplevel(), on_save, default_unidad_id=uid)

    def _selected_id(self):
        sel = self.tree.selection()
        return self.tree.item(sel[0])["values"][0] if sel else None

    def _edit(self):
        fid = self._selected_id()
        if not fid:
            messagebox.showinfo("Info", "Seleccione un funcionario.")
            return
        func = db.get_funcionario_by_id(fid)

        def on_save(data):
            db.update_funcionario(fid, **data)
            self.refresh()
        FuncionarioModal(self.winfo_toplevel(), on_save, funcionario=func)

    def _delete(self):
        fid = self._selected_id()
        if not fid:
            messagebox.showinfo("Info", "Seleccione un funcionario.")
            return
        if messagebox.askyesno("Confirmar", "¿Eliminar este funcionario?"):
            db.delete_funcionario(fid)
            self.refresh()


class StatsPage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=BG)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build()

    def _build(self):
        toolbar = page_toolbar(self, "Estadísticas y Resumen", [
            ("Actualizar", self.refresh, False),
        ])
        toolbar.grid(row=0, column=0, sticky="ew", padx=PAD, pady=(PAD, 8))

        self.stats_frame = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=8)
        self.stats_frame.grid(row=1, column=0, sticky="ew", padx=PAD, pady=8)

        self.units_frame = ctk.CTkScrollableFrame(self, fg_color=PANEL, corner_radius=8)
        self.units_frame.grid(row=2, column=0, sticky="nsew", padx=PAD, pady=(0, PAD))
        self.refresh()

    def refresh(self):
        for w in self.stats_frame.winfo_children():
            w.destroy()
        for w in self.units_frame.winfo_children():
            w.destroy()

        stats = db.get_estadisticas_generales()
        SectionTitle(self.stats_frame, "Dashboard Matrix").pack(anchor="w", padx=PAD, pady=(PAD, 8))

        cards = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
        cards.pack(fill="x", padx=PAD, pady=(0, 8))
        cards.grid_columnconfigure(tuple(range(3)), weight=1)
        for i, (lbl, val) in enumerate([
            ("Total PCs", stats["total_pcs"]),
            ("Monitores", stats["total_monitores"]),
            ("Webcams", stats["total_webcams"]),
        ]):
            card = ctk.CTkFrame(cards, fg_color=BG_ALT, corner_radius=8, border_width=2, border_color=ACCENT)
            card.grid(row=0, column=i, sticky="ew", padx=4, pady=4)
            ctk.CTkLabel(card, text=str(val), font=FONT_TITLE, text_color=ACCENT).pack(pady=(12, 0))
            MatrixLabel(card, text=lbl, dim=True).pack(pady=(0, 12))

        detail = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
        detail.pack(fill="x", padx=PAD, pady=(0, PAD))
        detail.grid_columnconfigure((0, 1), weight=1)
        for col, title, groups in [
            (0, "PCs por RAM", stats["ram_groups"]),
            (1, "PCs por Almacenamiento", stats["disco_groups"]),
        ]:
            frame = ctk.CTkFrame(detail, fg_color=BG_ALT, corner_radius=8, border_width=1, border_color=ACCENT)
            frame.grid(row=0, column=col, sticky="nsew", padx=4)
            MatrixLabel(frame, text=title).pack(pady=8)
            if groups:
                for k, v in groups.items():
                    MatrixLabel(frame, text=f"  {k}: {v}").pack(anchor="w", padx=PAD)
            else:
                MatrixLabel(frame, text="  Sin datos", dim=True).pack(anchor="w", padx=PAD)

        SectionTitle(self.units_frame, "Resumen por Unidades").pack(anchor="w", padx=PAD, pady=(PAD, 8))
        rows = db.get_resumen_por_unidades()
        if not rows:
            MatrixLabel(self.units_frame, text="No hay unidades registradas.", dim=True).pack(pady=20)
            return

        header = ctk.CTkFrame(self.units_frame, fg_color=BG_ALT, corner_radius=4)
        header.pack(fill="x", padx=PAD, pady=4)
        for txt in ("Unidad", "PCs", "Funcionarios", "Monitores", "Webcams"):
            MatrixLabel(header, text=txt, width=110, anchor="w").pack(side="left", padx=6, pady=8)

        for row in rows:
            rf = ctk.CTkFrame(self.units_frame, fg_color="transparent")
            rf.pack(fill="x", padx=PAD, pady=2)
            for val in (row["nombre_unidad"], row["total_pcs"], row["total_funcionarios"] or 0,
                        row["monitores"] or 0, row["webcams"] or 0):
                MatrixLabel(rf, text=str(val), width=110, anchor="w").pack(side="left", padx=6)


class ConfigPage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=BG)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build()

    def _build(self):
        page_toolbar(self, "Configuración", []).grid(row=0, column=0, sticky="ew", padx=PAD, pady=(PAD, 8))

        panel = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=8)
        panel.grid(row=1, column=0, sticky="nsew", padx=PAD, pady=(0, PAD))
        panel.grid_columnconfigure(0, weight=1)

        inner = ctk.CTkFrame(panel, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=PAD, pady=PAD)

        SectionTitle(inner, "Modo Portable").pack(anchor="w", pady=(0, 12))
        MatrixLabel(
            inner,
            text="Copie toda la carpeta del programa a un pendrive o disco portable.\n"
                 "Ejecute Iniciar.bat para abrir la aplicación en cualquier PC con Python.",
            justify="left",
        ).pack(anchor="w", pady=(0, 16))

        info = ctk.CTkFrame(inner, fg_color=BG_ALT, corner_radius=8, border_width=1, border_color=ACCENT)
        info.pack(fill="x", pady=(0, 20))
        MatrixLabel(info, text="Ruta de datos (base de datos):", dim=True).pack(anchor="w", padx=PAD, pady=(12, 4))
        self.path_label = ctk.CTkLabel(
            info, text=str(db.DB_PATH), font=FONT_MONO, text_color=ACCENT,
            wraplength=700, justify="left",
        )
        self.path_label.pack(anchor="w", padx=PAD, pady=(0, 12))

        SectionTitle(inner, "Base de Datos").pack(anchor="w", pady=(0, 12))

        btn_row = ctk.CTkFrame(inner, fg_color="transparent")
        btn_row.pack(fill="x", pady=8)
        StyledButton(
            btn_row, text="Copia de Seguridad", width=200,
            command=self._backup,
        ).pack(side="left", padx=(0, 12))
        StyledButton(
            btn_row, text="Abrir Carpeta de Datos", width=200, primary=False,
            command=self._open_folder,
        ).pack(side="left")

        MatrixLabel(
            inner,
            text="Las copias de seguridad se guardan en la subcarpeta /backups junto al programa.",
            dim=True,
        ).pack(anchor="w", pady=(16, 0))

    def _backup(self):
        try:
            dest = db.backup_database()
            messagebox.showinfo("Copia de seguridad", f"Respaldo creado correctamente:\n{dest}")
        except Exception as ex:
            messagebox.showerror("Error", f"No se pudo crear la copia:\n{ex}")

    def _open_folder(self):
        try:
            db.open_data_folder()
        except Exception as ex:
            messagebox.showerror("Error", f"No se pudo abrir la carpeta:\n{ex}")


class InventarioApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        apply_matrix_theme()
        self.title("Inventario TI — Matrix Edition")
        self.geometry("1200x800")
        self.minsize(960, 640)
        self.configure(fg_color=BG)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        sidebar = ctk.CTkFrame(self, fg_color=PANEL, width=220, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)

        ctk.CTkLabel(
            sidebar, text="INVENTARIO\nTI", font=FONT_TITLE, text_color=ACCENT, justify="center",
        ).pack(pady=(28, 36))

        self._nav_buttons = []
        nav_items = [
            ("scanner", "Escáner / Registro"),
            ("unidades", "Unidades"),
            ("equipos", "Equipos"),
            ("funcionarios", "Funcionarios"),
            ("stats", "Estadísticas"),
            ("config", "Configuración"),
        ]

        content = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        content.grid(row=0, column=1, sticky="nsew")
        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=1)

        self.funcionarios_page = FuncionariosPage(content)
        self.unidades_page = UnidadesPage(content)
        self.equipos_page = EquiposPage(content)
        self.stats_page = StatsPage(content)
        self.config_page = ConfigPage(content)
        callbacks = {
            "funcionarios": self.funcionarios_page.refresh,
            "unidades": self.unidades_page.refresh,
            "equipos": self.equipos_page.refresh,
            "stats": self.stats_page.refresh,
        }
        self.scanner_page = ScannerPage(content, refresh_callbacks=callbacks)

        self.pages = {
            "scanner": self.scanner_page,
            "unidades": self.unidades_page,
            "equipos": self.equipos_page,
            "funcionarios": self.funcionarios_page,
            "stats": self.stats_page,
            "config": self.config_page,
        }

        for key, label in nav_items:
            btn = ctk.CTkButton(
                sidebar, text=label, anchor="w", font=FONT_MONO,
                fg_color="transparent", hover_color=PANEL_ALT,
                text_color=ACCENT, command=lambda k=key: self._show_page(k),
            )
            btn.pack(fill="x", padx=12, pady=4)
            self._nav_buttons.append((key, btn))

        self._current = None
        self._show_page("scanner")

    def _show_page(self, key):
        if self._current:
            self.pages[self._current].grid_forget()
        self.pages[key].grid(row=0, column=0, sticky="nsew")
        self._current = key
        if key == "scanner":
            self.scanner_page.refresh_unidades()
        for k, btn in self._nav_buttons:
            active = k == key
            btn.configure(
                fg_color=ACCENT if active else "transparent",
                text_color=BG if active else ACCENT,
                hover_color=ACCENT_DIM if active else PANEL_ALT,
            )


def run_app():
    db.init_db()
    app = InventarioApp()
    app.mainloop()
