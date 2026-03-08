"""
Panel de Control — Procesador de Incidentes Ambientales
Versión Final Integrada y Corregida.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import subprocess
import threading
import os
import sys
import webbrowser
from datetime import datetime

# ── Importamos nuestros propios módulos ──
import src.db_consultas as db_consultas
import src.reportes_html as reportes_html
import src.main as main_etl

# ── Rutas ────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'data', 'database', 'incidentes.db')
LOG_PATH = os.path.join(BASE_DIR, 'logs', 'processor.log')
RAW_DIR  = os.path.join(BASE_DIR, 'data', 'raw')
# Ruta capturada de tu entorno
DEFAULT_QGIS_PROJECT = r"C:\Users\PC\Desktop\CAPAS PETROLEO\PETROLEO 2026.qgz"

# ── Paleta ───────────────────────────────────────────────────────────────────
BG, PANEL, CARD, BORDER = '#0F1117', '#1A1D27', '#222636', '#2E3347'
ACCENT, SUCCESS, WARNING, DANGER = '#4F8EF7', '#3DD68C', '#F7C948', '#F75F5F'
TEXT, MUTED, WHITE = '#E8EAF0', '#7B82A0', '#FFFFFF'

FONT_H1, FONT_H2, FONT_H3 = ('Segoe UI', 16, 'bold'), ('Segoe UI', 12, 'bold'), ('Segoe UI', 10, 'bold')
FONT_B, FONT_S, FONT_M = ('Segoe UI', 10), ('Segoe UI', 9), ('Consolas', 9)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Panel de Control — Incidentes Ambientales")
        self.geometry("1100x720")
        self.minsize(900, 600)
        self.configure(bg=BG)
        self._build_ui()
        self.after(300, self._refresh_stats)

    def _build_ui(self):
        # ── Sidebar ──────────────────────────────────────────────────────
        sidebar = tk.Frame(self, bg=PANEL, width=200)
        sidebar.pack(side='left', fill='y')
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="⬡", font=('Segoe UI', 28), bg=PANEL, fg=ACCENT).pack(pady=(24, 0))
        tk.Label(sidebar, text="Incidentes\nAmbientales", font=FONT_H3, bg=PANEL, fg=WHITE, justify='center').pack(pady=(4, 24))

        self.nav_btns = {}
        nav_items = [
            ('proceso',  '▶  Procesar PDFs'),
            ('consulta', '⊞  Consulta'),
            ('errores',  '⚠  Errores'),
            ('reporte',  '↓  Reporte'),
        ]
        for key, label in nav_items:
            btn = tk.Button(sidebar, text=label, font=FONT_B,
                            bg=PANEL, fg=MUTED, bd=0, cursor='hand2',
                            activebackground=CARD, activeforeground=WHITE,
                            anchor='w', padx=20,
                            command=lambda k=key: self._show_tab(k))
            btn.pack(fill='x', ipady=10)
            self.nav_btns[key] = btn

        tk.Frame(sidebar, bg=BORDER, height=1).pack(fill='x', pady=16)
        self.stat_total = self._sidebar_stat(sidebar, "Total registros", "—")
        self.stat_ops   = self._sidebar_stat(sidebar, "Operadores", "—")
        self.stat_err   = self._sidebar_stat(sidebar, "Con errores", "—")

        # ── Contenido principal ──────────────────────────────────────────
        self.content = tk.Frame(self, bg=BG)
        self.content.pack(side='left', fill='both', expand=True)

        self.tabs = {k: tk.Frame(self.content, bg=BG) for k in ['proceso', 'consulta', 'errores', 'reporte']}
        
        self._build_proceso(self.tabs['proceso'])
        self._build_consulta(self.tabs['consulta'])
        self._build_errores(self.tabs['errores'])
        self._build_reporte(self.tabs['reporte'])

        self._show_tab('proceso')

    def _sidebar_stat(self, parent, label, value):
        f = tk.Frame(parent, bg=PANEL)
        f.pack(fill='x', padx=16, pady=3)
        tk.Label(f, text=label, font=FONT_S, bg=PANEL, fg=MUTED, anchor='w').pack(fill='x')
        lbl = tk.Label(f, text=value, font=FONT_H3, bg=PANEL, fg=WHITE, anchor='w')
        lbl.pack(fill='x')
        return lbl

    def _show_tab(self, key):
        for f in self.tabs.values(): f.pack_forget()
        self.tabs[key].pack(fill='both', expand=True)
        for k, btn in self.nav_btns.items():
            btn.config(bg=CARD if k == key else PANEL, fg=WHITE if k == key else MUTED)
        if key == 'consulta': self._cargar_tabla()
        if key == 'errores': self._cargar_errores()

    # ── TAB: PROCESO ─────────────────────────────────────────────────────────
    def _build_proceso(self, parent):
        self._header(parent, "▶  Procesar PDFs", "Extraé datos de PDFs en data/raw/")
        bar = tk.Frame(parent, bg=BG); bar.pack(fill='x', padx=24, pady=(0, 12))

        self._btn(bar, "▶  Iniciar proceso", ACCENT, self._run_proceso).pack(side='left', padx=(0, 8))
        self._btn(bar, "👤  Gestionar Operadoras", CARD, self._gestionar_operadoras).pack(side='left', padx=(0, 8))
        self._btn(bar, "🗑  Limpiar DB", DANGER, self._confirmar_limpiar).pack(side='left')

        self.estado_lbl = tk.Label(parent, text="Listo.", font=FONT_S, bg=BG, fg=MUTED)
        self.estado_lbl.pack(anchor='w', padx=24)

        log_frame = tk.Frame(parent, bg=CARD, bd=0); log_frame.pack(fill='both', expand=True, padx=24, pady=(8, 24))
        self.log_text = tk.Text(log_frame, bg='#0D0F17', fg=TEXT, font=FONT_M, bd=0, state='disabled')
        self.log_text.pack(fill='both', expand=True, padx=2, pady=2)

    def _run_proceso(self):
        self.log_text.config(state='normal'); self.log_text.delete('1.0', 'end'); self.log_text.config(state='disabled')
        self.estado_lbl.config(text="⏳ Procesando...", fg=WARNING)
        def worker():
            try:
                proc = subprocess.Popen([sys.executable, '-m', 'src.main'], cwd=BASE_DIR, stdout=subprocess.PIPE, text=True)
                for line in proc.stdout: self.after(0, self._log, line)
                proc.wait()
                self.after(0, self.estado_lbl.config, {'text': "✓ Completado.", 'fg': SUCCESS})
                self.after(0, self._refresh_stats)
            except Exception as e: self.after(0, messagebox.showerror, "Error", str(e))
        threading.Thread(target=worker, daemon=True).start()

    def _confirmar_limpiar(self):
        if messagebox.askyesno("Confirmar", "¿Eliminar la base de datos?"):
            if os.path.exists(DB_PATH):
                os.remove(DB_PATH)
                self._refresh_stats()
                self._cargar_tabla()

    def _log(self, text):
        self.log_text.config(state='normal'); self.log_text.insert('end', text); self.log_text.see('end'); self.log_text.config(state='disabled')

    # ── TAB: CONSULTA ────────────────────────────────────────────────────────
    def _build_consulta(self, parent):
        self._header(parent, "⊞  Consulta", "Buscá y filtrá registros")
        filtros = tk.Frame(parent, bg=CARD); filtros.pack(fill='x', padx=24, pady=(0, 8))
        
        tk.Label(filtros, text="Buscar:", font=FONT_B, bg=CARD, fg=MUTED).pack(side='left', padx=10)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *a: self._cargar_tabla())
        tk.Entry(filtros, textvariable=self.search_var, font=FONT_B, bg=BORDER, fg=TEXT, bd=0).pack(side='left', padx=5, ipady=4)

        self.op_var = tk.StringVar(value='Todos')
        self.op_combo = ttk.Combobox(filtros, textvariable=self.op_var, state='readonly')
        self.op_combo.pack(side='left', padx=10)
        self.op_combo.bind('<<ComboboxSelected>>', lambda e: self._cargar_tabla())

        cols = ('NUM_INC','OPERADOR','FECHA','MAGNITUD','TIPO_INSTALACION','VOL_M3','LAT','LON','RECURSOS')
        self.tabla = ttk.Treeview(parent, columns=cols, show='headings')
        for col in cols: self.tabla.heading(col, text=col); self.tabla.column(col, width=100)
        self.tabla.pack(fill='both', expand=True, padx=24)
        self.tabla.bind('<Double-1>', self._ver_detalle)

    def _cargar_tabla(self):
        for r in self.tabla.get_children(): self.tabla.delete(r)
        ops = ['Todos'] + db_consultas.get_operadores(DB_PATH)
        self.op_combo['values'] = ops
        rows = db_consultas.get_incidentes_filtrados(DB_PATH, self.search_var.get(), self.op_var.get())
        for r in rows: self.tabla.insert('', 'end', values=r)

    def _ver_detalle(self, event):
        sel = self.tabla.selection()
        if sel:
            num = self.tabla.item(sel[0])['values'][0]
            row = db_consultas.get_incidente_detalle(DB_PATH, num)
            if row: messagebox.showinfo("Detalle", f"N°: {row['NUM_INC']}\nOperador: {row['OPERADOR']}\nDescripción: {row['DESC_ABREV']}")

    # ── TAB: ERRORES ─────────────────────────────────────────────────────────
    def _build_errores(self, parent):
        self._header(parent, "⚠  Errores", "Coordenadas fuera de rango")
        self.tree_nulos = ttk.Treeview(parent, columns=('ID', 'OP', 'ERR'), show='headings')
        self.tree_nulos.heading('ID', text='N° Inc.'); self.tree_nulos.heading('OP', text='Operador'); self.tree_nulos.heading('ERR', text='Error')
        self.tree_nulos.pack(fill='both', expand=True, padx=24, pady=10)

    def _cargar_errores(self):
        for r in self.tree_nulos.get_children(): self.tree_nulos.delete(r)
        rows = db_consultas.get_todos_incidentes(DB_PATH)
        for r in rows:
            if not r['LAT'] or not (-39.0 <= r['LAT'] <= -32.0):
                self.tree_nulos.insert('', 'end', values=(r['NUM_INC'], r['OPERADOR'], "Coord. fuera de Mendoza"))

    # ── TAB: REPORTE ─────────────────────────────────────────────────────────
    def _build_reporte(self, parent):
        self._header(parent, "↓  Reporte y GIS", "Salida de datos")
        center = tk.Frame(parent, bg=BG); center.pack(expand=True)
        self._btn(center, "  1. Generar Reporte HTML  ", ACCENT, self._generar_reporte, big=True).pack(pady=10)
        self._btn(center, "  2. Actualizar Capa QGIS (.shp)  ", SUCCESS, self._generar_capa_qgis).pack(pady=10)
        self._btn(center, "  3. Ver Mapa en QGIS  ", ACCENT, self._abrir_mapa_externo).pack(pady=5)

    def _generar_reporte(self, abrir=True):
        try:
            rows = db_consultas.get_todos_incidentes(DB_PATH)
            stats = {'total': len(rows), 'nulos': 0, 'coords_inv': 0, 'log_errs': 0, 'operadores': db_consultas.get_operador_counts(DB_PATH)}
            html = reportes_html.generar_html(stats, [], [], [])
            path = os.path.join(BASE_DIR, 'data', 'reporte_incidentes.html')
            with open(path, 'w', encoding='utf-8') as f: f.write(html)
            if abrir: webbrowser.open(f'file:///{path}')
            messagebox.showinfo("Éxito", "Reporte generado.")
        except Exception as e: messagebox.showerror("Error", str(e))

    def _generar_capa_qgis(self):
        out_dir = os.path.join(BASE_DIR, 'data')
        exito, msg = exportador_gis.exportar_shapefile(DB_PATH, out_dir)
        messagebox.showinfo("GIS", msg) if exito else messagebox.showerror("Error", msg)

    def _abrir_mapa_externo(self):
        path = DEFAULT_QGIS_PROJECT
        if not os.path.exists(path):
            path = filedialog.askopenfilename(filetypes=[("QGIS", "*.qgz *.qgs")])
        if path: exportador_gis.lanzar_qgis(path)

    def _gestionar_operadoras(self):
        """Ventana para cargar operadoras que el sistema no reconoce automáticamente."""
        win = tk.Toplevel(self)
        win.title("Operadoras")
        win.geometry("350x280")
        win.configure(bg=PANEL) # Usamos tu paleta oscura

        tk.Label(win, text="Gestión de Operadoras", font=FONT_H2, bg=PANEL, fg=WHITE).pack(pady=10)
        
        # Campo 1: Alias (lo que dice el PDF)
        tk.Label(win, text="Alias en PDF (ej: ACONCAGUA):", font=FONT_S, bg=PANEL, fg=MUTED).pack()
        ent_alias = tk.Entry(win, font=FONT_B, bg=BORDER, fg=WHITE, bd=0)
        ent_alias.pack(pady=5, ipady=4, padx=20, fill='x')

        # Campo 2: Nombre Oficial (lo que va a QGIS)
        tk.Label(win, text="Nombre Oficial (ej: ACONCAGUA ENERGIA):", font=FONT_S, bg=PANEL, fg=MUTED).pack()
        ent_oficial = tk.Entry(win, font=FONT_B, bg=BORDER, fg=WHITE, bd=0)
        ent_oficial.pack(pady=5, ipady=4, padx=20, fill='x')

        def salvar():
            alias = ent_alias.get().strip()
            oficial = ent_oficial.get().strip()
            if alias and oficial:
                # Usamos la función del motor de base de datos
                if db_consultas.guardar_maestro_operadora(DB_PATH, alias, oficial):
                    messagebox.showinfo("Éxito", f"'{oficial}' registrado correctamente.")
                    win.destroy()
                else:
                    messagebox.showerror("Error", "No se pudo guardar en la base de datos.")
            else:
                messagebox.showwarning("Atención", "Completá ambos campos.")

        self._btn(win, "  Guardar Operadora  ", SUCCESS, salvar).pack(pady=20)

    # ── Helpers UI ───────────────────────────────────────────────────────────
    def _header(self, parent, title, subtitle):
        f = tk.Frame(parent, bg=BG); f.pack(fill='x', padx=24, pady=(24, 16))
        tk.Label(f, text=title, font=FONT_H1, bg=BG, fg=WHITE).pack(anchor='w')
        tk.Label(f, text=subtitle, font=FONT_S, bg=BG, fg=MUTED).pack(anchor='w')

    def _btn(self, parent, text, color, cmd, big=False):
        f = ('Segoe UI', 11, 'bold') if big else FONT_B
        return tk.Button(parent, text=text, font=f, bg=color, fg=WHITE, bd=0, cursor='hand2', padx=12, pady=5, command=cmd)

    def _refresh_stats(self):
        t, o, e = db_consultas.get_stats(DB_PATH)
        self.stat_total.config(text=str(t)); self.stat_ops.config(text=str(o))
        self.stat_err.config(text=str(e), fg=DANGER if e > 0 else SUCCESS)

if __name__ == '__main__':
    App().mainloop()