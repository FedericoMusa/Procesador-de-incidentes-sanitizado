"""
Panel de Control — Procesador de Incidentes Ambientales
Interfaz gráfica para operadores sin formación en programación.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import subprocess
import threading
import os
import sys
import webbrowser
import tempfile
from datetime import datetime

# ── Rutas ────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'data', 'database', 'incidentes.db')
LOG_PATH = os.path.join(BASE_DIR, 'logs', 'processor.log')
RAW_DIR  = os.path.join(BASE_DIR, 'data', 'raw')

# ── Paleta ───────────────────────────────────────────────────────────────────
BG       = '#0F1117'
PANEL    = '#1A1D27'
CARD     = '#222636'
BORDER   = '#2E3347'
ACCENT   = '#4F8EF7'
SUCCESS  = '#3DD68C'
WARNING  = '#F7C948'
DANGER   = '#F75F5F'
TEXT     = '#E8EAF0'
MUTED    = '#7B82A0'
WHITE    = '#FFFFFF'

FONT_H1  = ('Segoe UI', 16, 'bold')
FONT_H2  = ('Segoe UI', 12, 'bold')
FONT_H3  = ('Segoe UI', 10, 'bold')
FONT_B   = ('Segoe UI', 10)
FONT_S   = ('Segoe UI', 9)
FONT_M   = ('Consolas', 9)

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

        tk.Label(sidebar, text="⬡", font=('Segoe UI', 28), bg=PANEL,
                 fg=ACCENT).pack(pady=(24, 0))
        tk.Label(sidebar, text="Incidentes\nAmbientales", font=FONT_H3,
                 bg=PANEL, fg=WHITE, justify='center').pack(pady=(4, 24))

        self.nav_btns = {}
        self.current_tab = tk.StringVar(value='proceso')
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

        # Stats en sidebar
        tk.Frame(sidebar, bg=BORDER, height=1).pack(fill='x', pady=16)
        self.stat_total = self._sidebar_stat(sidebar, "Total registros", "—")
        self.stat_ops   = self._sidebar_stat(sidebar, "Operadores", "—")
        self.stat_err   = self._sidebar_stat(sidebar, "Con errores", "—")

        # ── Contenido principal ──────────────────────────────────────────
        self.content = tk.Frame(self, bg=BG)
        self.content.pack(side='left', fill='both', expand=True)

        self.tabs = {}
        for key in ['proceso', 'consulta', 'errores', 'reporte']:
            f = tk.Frame(self.content, bg=BG)
            self.tabs[key] = f

        self._build_proceso(self.tabs['proceso'])
        self._build_consulta(self.tabs['consulta'])
        self._build_errores(self.tabs['errores'])
        self._build_reporte(self.tabs['reporte'])

        self._show_tab('proceso')

    def _sidebar_stat(self, parent, label, value):
        f = tk.Frame(parent, bg=PANEL)
        f.pack(fill='x', padx=16, pady=3)
        tk.Label(f, text=label, font=FONT_S, bg=PANEL, fg=MUTED,
                 anchor='w').pack(fill='x')
        lbl = tk.Label(f, text=value, font=FONT_H3, bg=PANEL,
                       fg=WHITE, anchor='w')
        lbl.pack(fill='x')
        return lbl

    def _show_tab(self, key):
        for k, f in self.tabs.items():
            f.pack_forget()
        self.tabs[key].pack(fill='both', expand=True)
        for k, btn in self.nav_btns.items():
            btn.config(bg=CARD if k == key else PANEL,
                       fg=WHITE if k == key else MUTED)
        self.current_tab.set(key)
        if key == 'consulta':
            self._cargar_tabla()
        if key == 'errores':
            self._cargar_errores()

    # ── TAB: PROCESO ─────────────────────────────────────────────────────────
    def _build_proceso(self, parent):
        self._header(parent, "▶  Procesar PDFs",
                     "Ejecutá el procesador sobre los PDFs en data/raw/")

        # Botones de acción
        bar = tk.Frame(parent, bg=BG)
        bar.pack(fill='x', padx=24, pady=(0, 12))

        self._btn(bar, "▶  Iniciar proceso", ACCENT,
                  self._run_proceso).pack(side='left', padx=(0, 8))
        self._btn(bar, "🗑  Limpiar base de datos", DANGER,
                  self._confirmar_limpiar).pack(side='left', padx=(0, 8))
        self._btn(bar, "📂  Abrir carpeta raw", CARD,
                  lambda: os.startfile(RAW_DIR) if os.path.exists(RAW_DIR)
                  else messagebox.showerror("Error", f"No existe:\n{RAW_DIR}")
                  ).pack(side='left')

        # Estado
        self.estado_lbl = tk.Label(parent, text="Listo para procesar.",
                                   font=FONT_S, bg=BG, fg=MUTED)
        self.estado_lbl.pack(anchor='w', padx=24)

        # Log en tiempo real
        log_frame = tk.Frame(parent, bg=CARD, bd=0)
        log_frame.pack(fill='both', expand=True, padx=24, pady=(8, 24))

        tk.Label(log_frame, text="Log del proceso", font=FONT_H3,
                 bg=CARD, fg=MUTED).pack(anchor='w', padx=12, pady=(10, 0))

        self.log_text = tk.Text(log_frame, bg='#0D0F17', fg=TEXT,
                                font=FONT_M, bd=0, wrap='none',
                                state='disabled', insertbackground=WHITE)
        sb = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.config(yscrollcommand=sb.set)
        sb.pack(side='right', fill='y')
        self.log_text.pack(fill='both', expand=True, padx=2, pady=2)

        # Tags de color para el log
        self.log_text.tag_config('INFO',    foreground=TEXT)
        self.log_text.tag_config('ERROR',   foreground=DANGER)
        self.log_text.tag_config('WARNING', foreground=WARNING)
        self.log_text.tag_config('SUCCESS', foreground=SUCCESS)

    def _run_proceso(self):
        self._log_clear()
        self._log("Iniciando proceso...\n", 'INFO')
        self.estado_lbl.config(text="⏳ Procesando...", fg=WARNING)

        def worker():
            try:
                proc = subprocess.Popen(
                    [sys.executable, '-m', 'src.main'],
                    cwd=BASE_DIR,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True, encoding='utf-8', errors='replace'
                )
                for line in proc.stdout:
                    tag = 'ERROR' if '[ERROR]' in line else \
                          'WARNING' if '[WARNING]' in line else \
                          'SUCCESS' if 'finalizado' in line.lower() else 'INFO'
                    self.after(0, self._log, line, tag)
                proc.wait()
                status = "✓ Proceso completado." if proc.returncode == 0 \
                         else f"✗ Error (código {proc.returncode})"
                color  = SUCCESS if proc.returncode == 0 else DANGER
                self.after(0, self.estado_lbl.config,
                           {'text': status, 'fg': color})
                self.after(0, self._refresh_stats)
            except Exception as e:
                self.after(0, self._log, f"Error al ejecutar: {e}\n", 'ERROR')

        threading.Thread(target=worker, daemon=True).start()

    def _confirmar_limpiar(self):
        if messagebox.askyesno("Confirmar",
                               "¿Eliminar la base de datos y empezar de cero?"):
            if os.path.exists(DB_PATH):
                os.remove(DB_PATH)
                self._log("Base de datos eliminada.\n", 'WARNING')
                self._refresh_stats()

    def _log(self, text, tag='INFO'):
        self.log_text.config(state='normal')
        self.log_text.insert('end', text, tag)
        self.log_text.see('end')
        self.log_text.config(state='disabled')

    def _log_clear(self):
        self.log_text.config(state='normal')
        self.log_text.delete('1.0', 'end')
        self.log_text.config(state='disabled')

    # ── TAB: CONSULTA ────────────────────────────────────────────────────────
    def _build_consulta(self, parent):
        self._header(parent, "⊞  Consulta de Incidentes",
                     "Buscá y filtrá registros de la base de datos")

        # Barra de filtros
        filtros = tk.Frame(parent, bg=CARD)
        filtros.pack(fill='x', padx=24, pady=(0, 8))

        tk.Label(filtros, text="Buscar:", font=FONT_B, bg=CARD,
                 fg=MUTED).pack(side='left', padx=(12, 4), pady=10)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *a: self._cargar_tabla())
        tk.Entry(filtros, textvariable=self.search_var, font=FONT_B,
                 bg=BORDER, fg=TEXT, insertbackground=WHITE, bd=0,
                 width=30).pack(side='left', padx=4, ipady=4)

        tk.Label(filtros, text="Operador:", font=FONT_B, bg=CARD,
                 fg=MUTED).pack(side='left', padx=(16, 4))
        self.op_var = tk.StringVar(value='Todos')
        self.op_combo = ttk.Combobox(filtros, textvariable=self.op_var,
                                     state='readonly', width=22, font=FONT_B)
        self.op_combo.pack(side='left', padx=4)
        self.op_combo.bind('<<ComboboxSelected>>', lambda e: self._cargar_tabla())

        self._btn(filtros, "✕ Limpiar", CARD,
                  self._limpiar_filtros).pack(side='right', padx=12)

        # Tabla
        cols = ('NUM_INC','OPERADOR','FECHA','MAGNITUD','TIPO_INSTALACION',
                'VOL_M3','LAT','LON','RECURSOS_AFECTADOS')
        heads = ('N° Inc.','Operador','Fecha','Magnitud','Instalación',
                 'Vol m³','LAT','LON','Recursos')

        tabla_frame = tk.Frame(parent, bg=BG)
        tabla_frame.pack(fill='both', expand=True, padx=24, pady=(0, 16))

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Inc.Treeview', background=CARD, foreground=TEXT,
                        fieldbackground=CARD, rowheight=26,
                        font=FONT_S, borderwidth=0)
        style.configure('Inc.Treeview.Heading', background=BORDER,
                        foreground=MUTED, font=FONT_H3, relief='flat')
        style.map('Inc.Treeview', background=[('selected', ACCENT)],
                  foreground=[('selected', WHITE)])

        self.tabla = ttk.Treeview(tabla_frame, columns=cols,
                                  show='headings', style='Inc.Treeview')
        widths = [90,160,90,80,160,60,100,100,140]
        for col, head, w in zip(cols, heads, widths):
            self.tabla.heading(col, text=head,
                               command=lambda c=col: self._sort_tabla(c))
            self.tabla.column(col, width=w, minwidth=40)

        vsb = ttk.Scrollbar(tabla_frame, orient='vertical',
                            command=self.tabla.yview)
        hsb = ttk.Scrollbar(tabla_frame, orient='horizontal',
                            command=self.tabla.xview)
        self.tabla.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side='right', fill='y')
        hsb.pack(side='bottom', fill='x')
        self.tabla.pack(fill='both', expand=True)

        self.tabla.bind('<Double-1>', self._ver_detalle)
        self.count_lbl = tk.Label(parent, text="", font=FONT_S,
                                  bg=BG, fg=MUTED)
        self.count_lbl.pack(anchor='e', padx=28, pady=(0, 8))

    def _cargar_tabla(self):
        if not os.path.exists(DB_PATH):
            return
        for row in self.tabla.get_children():
            self.tabla.delete(row)
        try:
            with sqlite3.connect(DB_PATH) as conn:
                # Poblar combo de operadores
                ops = ['Todos'] + [r[0] for r in conn.execute(
                    "SELECT DISTINCT OPERADOR FROM incidentes ORDER BY OPERADOR"
                    ).fetchall() if r[0]]
                self.op_combo['values'] = ops

                q = "SELECT NUM_INC,OPERADOR,FECHA,MAGNITUD,TIPO_INSTALACION," \
                    "VOL_M3,LAT,LON,RECURSOS_AFECTADOS FROM incidentes WHERE 1=1"
                params = []
                s = self.search_var.get().strip()
                if s:
                    q += " AND (NUM_INC LIKE ? OR OPERADOR LIKE ? " \
                         "OR TIPO_INSTALACION LIKE ? OR DESC_ABREV LIKE ?)"
                    params += [f'%{s}%'] * 4
                op = self.op_var.get()
                if op and op != 'Todos':
                    q += " AND OPERADOR = ?"
                    params.append(op)
                q += " ORDER BY FECHA DESC"
                rows = conn.execute(q, params).fetchall()

            for i, row in enumerate(rows):
                tag = 'odd' if i % 2 else 'even'
                self.tabla.insert('', 'end', values=row, tags=(tag,))
            self.tabla.tag_configure('odd',  background='#1E2130')
            self.tabla.tag_configure('even', background=CARD)
            self.count_lbl.config(text=f"{len(rows)} registros")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _limpiar_filtros(self):
        self.search_var.set('')
        self.op_var.set('Todos')
        self._cargar_tabla()

    def _sort_tabla(self, col):
        rows = [(self.tabla.set(k, col), k)
                for k in self.tabla.get_children('')]
        rows.sort()
        for i, (_, k) in enumerate(rows):
            self.tabla.move(k, '', i)

    def _ver_detalle(self, event):
        sel = self.tabla.selection()
        if not sel:
            return
        vals = self.tabla.item(sel[0])['values']
        if not vals or not os.path.exists(DB_PATH):
            return
        num_inc = vals[0]
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM incidentes WHERE NUM_INC=?", (num_inc,)
            ).fetchone()
        if not row:
            return

        win = tk.Toplevel(self)
        win.title(f"Detalle — {num_inc}")
        win.geometry("520x480")
        win.configure(bg=PANEL)

        tk.Label(win, text=num_inc, font=FONT_H1, bg=PANEL,
                 fg=ACCENT).pack(anchor='w', padx=20, pady=(16, 4))
        tk.Label(win, text=row['OPERADOR'] or '—', font=FONT_B,
                 bg=PANEL, fg=MUTED).pack(anchor='w', padx=20)

        tk.Frame(win, bg=BORDER, height=1).pack(fill='x', padx=20, pady=12)

        fields = [
            ('Fecha',       'FECHA'),
            ('Magnitud',    'MAGNITUD'),
            ('Instalación', 'TIPO_INSTALACION'),
            ('Subtipo',     'SUBTIPO'),
            ('Área',        'AREA_CONCESION'),
            ('Vol m³',      'VOL_M3'),
            ('Agua %',      'AGUA_PCT'),
            ('Área afect.', 'AREA_AFECT_m2'),
            ('LAT',         'LAT'),
            ('LON',         'LON'),
            ('Recursos',    'RECURSOS_AFECTADOS'),
            ('Descripción', 'DESC_ABREV'),
        ]
        frame = tk.Frame(win, bg=PANEL)
        frame.pack(fill='both', expand=True, padx=20)
        for label, key in fields:
            r = tk.Frame(frame, bg=PANEL)
            r.pack(fill='x', pady=2)
            tk.Label(r, text=label+':', font=FONT_S, bg=PANEL,
                     fg=MUTED, width=12, anchor='e').pack(side='left')
            val = row[key] if row[key] is not None else '—'
            tk.Label(r, text=str(val), font=FONT_S, bg=PANEL,
                     fg=TEXT, anchor='w', wraplength=340,
                     justify='left').pack(side='left', padx=8)

    # ── TAB: ERRORES ─────────────────────────────────────────────────────────
    def _build_errores(self, parent):
        self._header(parent, "⚠  Informe de Errores",
                     "Campos faltantes, coordenadas inválidas y PDFs con problemas")

        bar = tk.Frame(parent, bg=BG)
        bar.pack(fill='x', padx=24, pady=(0, 12))
        self._btn(bar, "↺  Actualizar", ACCENT,
                  self._cargar_errores).pack(side='left')

        # Notebook interno
        nb_style = ttk.Style()
        nb_style.configure('Err.TNotebook', background=BG, borderwidth=0)
        nb_style.configure('Err.TNotebook.Tab', background=CARD,
                           foreground=MUTED, font=FONT_B, padding=(12, 6))
        nb_style.map('Err.TNotebook.Tab',
                     background=[('selected', ACCENT)],
                     foreground=[('selected', WHITE)])

        nb = ttk.Notebook(parent, style='Err.TNotebook')
        nb.pack(fill='both', expand=True, padx=24, pady=(0, 24))

        self.tab_campos  = tk.Frame(nb, bg=BG)
        self.tab_coords  = tk.Frame(nb, bg=BG)
        self.tab_log_err = tk.Frame(nb, bg=BG)
        nb.add(self.tab_campos,  text=' Campos nulos ')
        nb.add(self.tab_coords,  text=' Coordenadas inválidas ')
        nb.add(self.tab_log_err, text=' Errores del log ')

        # Campos nulos — treeview
        cols_n = ('NUM_INC','OPERADOR','CAMPO','VALOR')
        self.tree_nulos = self._make_tree(
            self.tab_campos, cols_n,
            ('N° Inc.','Operador','Campo vacío','Valor actual'), [100,160,160,200])

        # Coordenadas inválidas — treeview
        cols_c = ('NUM_INC','OPERADOR','LAT','LON','PROBLEMA')
        self.tree_coords = self._make_tree(
            self.tab_coords, cols_c,
            ('N° Inc.','Operador','LAT','LON','Problema'), [100,160,100,100,220])

        # Log errores — text
        lf = tk.Frame(self.tab_log_err, bg=BG)
        lf.pack(fill='both', expand=True, padx=0, pady=0)
        self.log_err_text = tk.Text(lf, bg='#0D0F17', fg=DANGER,
                                    font=FONT_M, bd=0, state='disabled')
        sb2 = ttk.Scrollbar(lf, command=self.log_err_text.yview)
        self.log_err_text.config(yscrollcommand=sb2.set)
        sb2.pack(side='right', fill='y')
        self.log_err_text.pack(fill='both', expand=True)

    def _make_tree(self, parent, cols, heads, widths):
        f = tk.Frame(parent, bg=BG)
        f.pack(fill='both', expand=True)
        tree = ttk.Treeview(f, columns=cols, show='headings',
                             style='Inc.Treeview')
        for col, head, w in zip(cols, heads, widths):
            tree.heading(col, text=head)
            tree.column(col, width=w, minwidth=40)
        vsb = ttk.Scrollbar(f, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side='right', fill='y')
        tree.pack(fill='both', expand=True)
        return tree

    def _cargar_errores(self):
        # Limpiar
        for t in [self.tree_nulos, self.tree_coords]:
            for r in t.get_children():
                t.delete(r)

        CAMPOS_CRITICOS = ['FECHA','MAGNITUD','TIPO_INSTALACION',
                           'SUBTIPO','LAT','LON','VOL_M3']
        LAT_MIN, LAT_MAX = -39.0, -32.0
        LON_MIN, LON_MAX = -70.0, -67.0

        if os.path.exists(DB_PATH):
            try:
                with sqlite3.connect(DB_PATH) as conn:
                    conn.row_factory = sqlite3.Row
                    rows = conn.execute(
                        "SELECT * FROM incidentes").fetchall()

                for row in rows:
                    num = row['NUM_INC'] or '?'
                    op  = row['OPERADOR'] or '?'
                    # Campos nulos
                    for campo in CAMPOS_CRITICOS:
                        val = row[campo]
                        if val is None or str(val).strip() == '':
                            self.tree_nulos.insert(
                                '', 'end',
                                values=(num, op, campo, 'VACÍO'),
                                tags=('warn',))
                    # Coordenadas inválidas
                    lat = row['LAT']
                    lon = row['LON']
                    prob = []
                    if lat is None: prob.append('LAT ausente')
                    elif not (LAT_MIN <= lat <= LAT_MAX):
                        prob.append(f'LAT {lat} fuera de rango')
                    if lon is None: prob.append('LON ausente')
                    elif not (LON_MIN <= lon <= LON_MAX):
                        prob.append(f'LON {lon} fuera de rango')
                    if prob:
                        self.tree_coords.insert(
                            '', 'end',
                            values=(num, op,
                                    lat if lat else '—',
                                    lon if lon else '—',
                                    ' | '.join(prob)),
                            tags=('err',))

                self.tree_nulos.tag_configure('warn', foreground=WARNING)
                self.tree_coords.tag_configure('err', foreground=DANGER)
            except Exception as e:
                messagebox.showerror("Error", str(e))

        # Errores del log
        self.log_err_text.config(state='normal')
        self.log_err_text.delete('1.0', 'end')
        if os.path.exists(LOG_PATH):
            with open(LOG_PATH, encoding='utf-8', errors='replace') as f:
                for line in f:
                    if '[ERROR]' in line or '[WARNING]' in line:
                        color = DANGER if '[ERROR]' in line else WARNING
                        self.log_err_text.insert('end', line)
        self.log_err_text.config(state='disabled')

    # ── TAB: REPORTE ─────────────────────────────────────────────────────────
    def _build_reporte(self, parent):
        self._header(parent, "↓  Generar Reporte",
                     "Exportá un informe HTML completo del estado del sistema")

        center = tk.Frame(parent, bg=BG)
        center.pack(expand=True)

        tk.Label(center, text="📋", font=('Segoe UI', 64),
                 bg=BG, fg=ACCENT).pack(pady=(0, 16))
        tk.Label(center,
                 text="El reporte incluye estadísticas generales,\n"
                      "registros con errores, campos faltantes\n"
                      "y coordenadas inválidas.",
                 font=FONT_B, bg=BG, fg=MUTED,
                 justify='center').pack(pady=(0, 32))

        self._btn(center, "  Generar y abrir reporte HTML  ",
                  ACCENT, self._generar_reporte,
                  big=True).pack(pady=8)
        self._btn(center, "  Solo guardar sin abrir  ",
                  CARD, lambda: self._generar_reporte(abrir=False)
                  ).pack(pady=4)

    def _generar_reporte(self, abrir=True):
        if not os.path.exists(DB_PATH):
            messagebox.showerror("Error", "No hay base de datos. Procesá PDFs primero.")
            return
        try:
            stats, nulos, coords_inv, log_errs = self._collect_report_data()
            html = self._render_html(stats, nulos, coords_inv, log_errs)
            path = os.path.join(BASE_DIR, 'data',
                                f'reporte_{datetime.now():%Y%m%d_%H%M%S}.html')
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(html)
            if abrir:
                webbrowser.open(f'file:///{path.replace(chr(92), "/")}')
            messagebox.showinfo("Reporte generado", f"Guardado en:\n{path}")
        except Exception as e:
            messagebox.showerror("Error al generar reporte", str(e))

    def _collect_report_data(self):
        LAT_MIN, LAT_MAX = -39.0, -32.0
        LON_MIN, LON_MAX = -70.0, -67.0
        CAMPOS = ['FECHA','MAGNITUD','TIPO_INSTALACION','SUBTIPO','LAT','LON','VOL_M3']

        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM incidentes").fetchall()
            total = len(rows)
            ops   = conn.execute(
                "SELECT OPERADOR, COUNT(*) c FROM incidentes "
                "GROUP BY OPERADOR ORDER BY c DESC").fetchall()

        nulos, coords_inv = [], []
        for row in rows:
            num = row['NUM_INC'] or '?'
            op  = row['OPERADOR'] or '?'
            for c in CAMPOS:
                v = row[c]
                if v is None or str(v).strip() == '':
                    nulos.append((num, op, c))
            lat, lon = row['LAT'], row['LON']
            prob = []
            if lat is None: prob.append('LAT ausente')
            elif not (LAT_MIN <= lat <= LAT_MAX): prob.append(f'LAT={lat}')
            if lon is None: prob.append('LON ausente')
            elif not (LON_MIN <= lon <= LON_MAX): prob.append(f'LON={lon}')
            if prob:
                coords_inv.append((num, op, lat, lon, ' | '.join(prob)))

        log_errs = []
        if os.path.exists(LOG_PATH):
            with open(LOG_PATH, encoding='utf-8', errors='replace') as f:
                log_errs = [l.rstrip() for l in f
                            if '[ERROR]' in l or '[WARNING]' in l]

        stats = {'total': total, 'operadores': ops,
                 'nulos': len(nulos), 'coords_inv': len(coords_inv),
                 'log_errs': len(log_errs)}
        return stats, nulos, coords_inv, log_errs

    def _render_html(self, stats, nulos, coords_inv, log_errs):
        def rows_html(data, cols):
            if not data:
                return '<tr><td colspan="999" style="color:#7B82A0;padding:16px">Sin registros</td></tr>'
            return ''.join(
                '<tr>' + ''.join(f'<td>{c}</td>' for c in row) + '</tr>'
                for row in data)

        ops_rows = ''.join(
            f'<tr><td>{r[0]}</td><td>{r[1]}</td></tr>'
            for r in stats['operadores'])

        nulos_rows = rows_html(nulos, ['N° Inc.','Operador','Campo'])
        coords_rows = rows_html(coords_inv, ['N° Inc.','Operador','LAT','LON','Problema'])
        log_text = '\n'.join(log_errs[-200:]) or 'Sin errores registrados.'

        fecha = datetime.now().strftime('%d/%m/%Y %H:%M')
        return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8">
<title>Reporte — Incidentes Ambientales</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',sans-serif;background:#0F1117;color:#E8EAF0;padding:32px}}
h1{{font-size:24px;color:#4F8EF7;margin-bottom:4px}}
.sub{{color:#7B82A0;font-size:13px;margin-bottom:32px}}
.cards{{display:flex;gap:16px;margin-bottom:32px;flex-wrap:wrap}}
.card{{background:#1A1D27;border:1px solid #2E3347;border-radius:10px;
       padding:20px 28px;min-width:160px}}
.card .num{{font-size:32px;font-weight:700;color:#4F8EF7}}
.card.warn .num{{color:#F7C948}}
.card.danger .num{{color:#F75F5F}}
.card .lbl{{color:#7B82A0;font-size:12px;margin-top:4px}}
h2{{font-size:16px;color:#7B82A0;margin:28px 0 12px;
    text-transform:uppercase;letter-spacing:1px}}
table{{width:100%;border-collapse:collapse;background:#1A1D27;
       border-radius:8px;overflow:hidden;margin-bottom:24px}}
th{{background:#2E3347;color:#7B82A0;font-size:12px;
    text-transform:uppercase;padding:10px 14px;text-align:left}}
td{{padding:9px 14px;border-bottom:1px solid #2E3347;font-size:13px}}
tr:last-child td{{border:none}}
tr:hover td{{background:#222636}}
pre{{background:#0D0F17;color:#F75F5F;padding:16px;border-radius:8px;
     font-size:12px;overflow-x:auto;white-space:pre-wrap;
     max-height:400px;overflow-y:auto}}
</style>
</head>
<body>
<h1>Reporte de Incidentes Ambientales</h1>
<p class="sub">Generado: {fecha}</p>

<div class="cards">
  <div class="card"><div class="num">{stats['total']}</div>
    <div class="lbl">Total registros</div></div>
  <div class="card warn"><div class="num">{stats['nulos']}</div>
    <div class="lbl">Campos nulos</div></div>
  <div class="card danger"><div class="num">{stats['coords_inv']}</div>
    <div class="lbl">Coords. inválidas</div></div>
  <div class="card danger"><div class="num">{stats['log_errs']}</div>
    <div class="lbl">Errores en log</div></div>
</div>

<h2>Registros por operador</h2>
<table><tr><th>Operador</th><th>Cantidad</th></tr>{ops_rows}</table>

<h2>Campos críticos vacíos</h2>
<table><tr><th>N° Inc.</th><th>Operador</th><th>Campo</th></tr>{nulos_rows}</table>

<h2>Coordenadas inválidas o fuera de Mendoza</h2>
<table><tr><th>N° Inc.</th><th>Operador</th><th>LAT</th>
<th>LON</th><th>Problema</th></tr>{coords_rows}</table>

<h2>Últimos errores del log</h2>
<pre>{log_text}</pre>
</body></html>"""

    # ── Helpers UI ───────────────────────────────────────────────────────────
    def _header(self, parent, title, subtitle):
        f = tk.Frame(parent, bg=BG)
        f.pack(fill='x', padx=24, pady=(24, 16))
        tk.Label(f, text=title, font=FONT_H1, bg=BG,
                 fg=WHITE).pack(anchor='w')
        tk.Label(f, text=subtitle, font=FONT_S, bg=BG,
                 fg=MUTED).pack(anchor='w')
        tk.Frame(parent, bg=BORDER, height=1).pack(fill='x',
                                                    padx=24, pady=(0, 16))

    def _btn(self, parent, text, color, cmd, big=False):
        font = ('Segoe UI', 11, 'bold') if big else FONT_B
        return tk.Button(parent, text=text, font=font,
                         bg=color, fg=WHITE, bd=0, cursor='hand2',
                         activebackground=ACCENT, activeforeground=WHITE,
                         padx=16 if big else 12, pady=8 if big else 5,
                         command=cmd)

    def _refresh_stats(self):
        if not os.path.exists(DB_PATH):
            self.stat_total.config(text='—')
            self.stat_ops.config(text='—')
            self.stat_err.config(text='—')
            return
        try:
            with sqlite3.connect(DB_PATH) as conn:
                total = conn.execute(
                    "SELECT COUNT(*) FROM incidentes").fetchone()[0]
                ops = conn.execute(
                    "SELECT COUNT(DISTINCT OPERADOR) FROM incidentes"
                ).fetchone()[0]
                errs = conn.execute(
                    "SELECT COUNT(*) FROM incidentes "
                    "WHERE LAT IS NULL OR LON IS NULL OR FECHA IS NULL"
                ).fetchone()[0]
            self.stat_total.config(text=str(total))
            self.stat_ops.config(text=str(ops))
            self.stat_err.config(
                text=str(errs),
                fg=DANGER if errs > 0 else SUCCESS)
        except:
            pass

if __name__ == '__main__':
    app = App()
    app.mainloop()