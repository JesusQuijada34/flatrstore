#!/usr/bin/env python3
"""
main.py - Interfaz para "Proyectos de Jesús Quijada"

Features:
- Autoinstala dependencias (requests, PySide6, pygame, rich, pywebview) si faltan.
- Preferencia: PySide6 GUI con QSS estilo GitHub (buscador, cards, preview, descarga con progreso, abrir carpeta).
- Si USE_PYGAME=1 o PySide6 no está disponible -> Modo Pygame con efectos glow y cursor personalizado.
- Fallback: consola interactiva (rich si está disponible) o abrir web en navegador.
- Descargas guardadas en ./downloads/
- Fuente de datos: https://raw.githubusercontent.com/JesusQuijada34/catalog/refs/heads/main/repo.list
"""

import os, sys, subprocess, importlib, threading, time, math, webbrowser, io
from datetime import datetime
RAW_LIST_URL = "https://raw.githubusercontent.com/JesusQuijada34/catalog/refs/heads/main/repo.list"
GITHUB_BASE = "https://github.com/JesusQuijada34"
DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads")
USE_PYGAME = os.environ.get("USE_PYGAME", "0") == "1"

# ----------------------------
# Helper: auto-install imports
# ----------------------------
def ensure_package(pip_name, import_name=None):
    """
    Try to import module; if fails, install via pip and re-import.
    Returns module or None.
    """
    if import_name is None:
        import_name = pip_name
    try:
        return importlib.import_module(import_name)
    except Exception:
        print(f"[installer] Instalando {pip_name} ...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name], stdout=subprocess.DEVNULL)
            return importlib.import_module(import_name)
        except Exception as e:
            print(f"[installer] Error instalando {pip_name}: {e}")
            return None

# Ensure always available
requests = ensure_package("requests")
# Optional packages
PySide6 = ensure_package("PySide6")
pygame = ensure_package("pygame")
rich = ensure_package("rich")
pywebview = ensure_package("pywebview", "webview")  # import_name differs

# ----------------------------
# Utility functions
# ----------------------------
def ensure_download_dir():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def open_downloads_folder():
    path = os.path.abspath(DOWNLOAD_DIR)
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        print("No se pudo abrir carpeta de descargas. Ruta:", path)

def fetch_repo_list_quick():
    """Return list of repo names (str). Best-effort."""
    try:
        resp = requests.get(RAW_LIST_URL, timeout=12)
        resp.raise_for_status()
        names = [s.strip() for s in resp.text.split(",") if s.strip()]
        return names
    except Exception as e:
        print("Error cargando repo list:", e)
        return []

def fetch_repo_details(repo_name):
    """
    Best-effort fetch details.xml, splash/icon presence, demo.
    Returns dict with keys: repo_name, display_name, category, rating, icon, splash, preview, repo_zip
    """
    base_raw = f"https://raw.githubusercontent.com/JesusQuijada34/{repo_name}/main"
    details_url = f"{base_raw}/details.xml"
    icon = f"{base_raw}/app/app-icon.ico"
    splash = f"{base_raw}/assets/splash.png"
    repo_zip = f"{GITHUB_BASE}/{repo_name}/archive/refs/heads/main.zip"
    preview = f"https://jesusquijada34.github.io/{repo_name}"
    display = repo_name
    category = "Aplicación"
    rating = "4.0"
    try:
        r = requests.get(details_url, timeout=6)
        if r.ok and "<" in r.text:
            txt = r.text
            import re
            m = re.search(r"<name>(.*?)</name>", txt, re.S|re.I)
            if m: display = m.group(1).strip()
            m = re.search(r"<category>(.*?)</category>", txt, re.S|re.I)
            if m: category = m.group(1).strip()
            m = re.search(r"<rate>(.*?)</rate>", txt, re.S|re.I)
            if m: rating = m.group(1).strip()
    except Exception:
        pass
    # check splash/icon quickly with HEAD
    try:
        h = requests.head(splash, timeout=4)
        if not h.ok:
            splash = ""
    except Exception:
        splash = ""
    try:
        h2 = requests.head(preview, timeout=4, allow_redirects=True)
        if not (h2.ok or str(h2.status_code).startswith("3")):
            preview = ""
    except Exception:
        preview = ""
    return {
        "repo_name": repo_name,
        "display_name": display,
        "category": category,
        "rating": rating,
        "icon": icon,
        "splash": splash,
        "preview": preview,
        "repo_zip": repo_zip
    }

# --------------
# Downloader
# --------------
def download_with_progress(url, repo_name, progress_callback=None, chunk_size=8192):
    """
    Downloads url -> ./downloads/<repo_name>.zip
    Calls progress_callback(percent:int, downloaded:int, total:int) periodically on the same thread.
    """
    ensure_download_dir()
    local = os.path.join(DOWNLOAD_DIR, f"{repo_name}.zip")
    try:
        with requests.get(url, stream=True, timeout=20) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length",0) or 0)
            downloaded = 0
            with open(local, "wb") as f:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    if not chunk:
                        continue
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total:
                        pct = int(downloaded*100/total)
                        progress_callback(pct, downloaded, total)
        return local, None
    except Exception as e:
        return None, str(e)

# ----------------------------
# PySide6 GUI (QSS estilo GitHub)
# ----------------------------
def run_pyside6_gui():
    if not PySide6:
        raise RuntimeError("PySide6 no disponible")
    # import Qt modules
    from PySide6 import QtWidgets, QtCore, QtGui
    from PySide6.QtCore import Qt, Slot, Signal
    from PySide6.QtGui import QPixmap, QCursor
    from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                   QLineEdit, QPushButton, QScrollArea, QGridLayout, QFrame,
                                   QProgressDialog, QMessageBox, QFileDialog)
    # QSS inspired in GitHub color tokens (simplified)
    QSS = """
    QWidget { background: #f6f8fa; color: #24292f; font-family: -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial; }
    #header { background: #24292f; color: white; padding: 12px; }
    QLabel#title { font-weight: 700; font-size: 18px; color: white; }
    QLineEdit#search { padding: 6px; border-radius: 8px; border: 1px solid #d0d7de; background: white; }
    QPushButton { padding: 6px 10px; border-radius: 8px; background: #f6f8fa; border: 1px solid rgba(31,35,40,0.08); }
    QPushButton#primary { background: #1a7f37; color: white; border: none; padding: 6px 12px; }
    QFrame.card { background: white; border: 1px solid #d0d7de; border-radius: 8px; }
    QLabel.repoTitle { color: #0969da; font-weight: 700; font-size: 14px; }
    QLabel.small { color: #6e7781; font-size: 12px; }
    QScrollArea { border: none; }
    """

    class RepoCard(QFrame):
        def __init__(self, info, parent=None):
            super().__init__(parent)
            self.setProperty("class", "card")
            self.setObjectName("card")
            self.info = info
            self.setLayout(QVBoxLayout())
            self.layout().setContentsMargins(0,0,0,0)
            # Image area
            img = QLabel()
            img.setFixedHeight(140)
            img.setAlignment(Qt.AlignCenter)
            # Try load splash or icon
            pix = QPixmap()
            img_url = info.get("splash") or info.get("icon") or ""
            if img_url:
                try:
                    r = requests.get(img_url, timeout=6)
                    if r.ok:
                        pix.loadFromData(r.content)
                except Exception:
                    pix = QPixmap()
            img.setPixmap(pix.scaled(img.width() or 360, 140, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
            self.layout().addWidget(img)
            # Content
            content = QWidget()
            cv = QVBoxLayout(content)
            cv.setContentsMargins(10,10,10,10)
            title = QLabel(info.get("display_name",""))
            title.setObjectName("repoTitle")
            title.setProperty("class","repoTitle")
            cat = QLabel(info.get("category",""))
            cat.setProperty("class","small")
            btnrow = QHBoxLayout()
            preview_btn = QPushButton("Vista previa")
            preview_btn.setEnabled(bool(info.get("preview")))
            preview_btn.clicked.connect(lambda: webbrowser.open(info.get("preview")) if info.get("preview") else None)
            dl_btn = QPushButton("Descargar")
            dl_btn.setObjectName("primary")
            dl_btn.clicked.connect(lambda: self.start_download())
            btnrow.addWidget(preview_btn)
            btnrow.addWidget(dl_btn)
            cv.addWidget(title)
            cv.addWidget(cat)
            cv.addLayout(btnrow)
            self.layout().addWidget(content)

        def start_download(self):
            url = self.info.get("repo_zip")
            name = self.info.get("repo_name")
            dlg = QProgressDialog(f"Descargando {name}...", "Cancelar", 0, 100, self)
            dlg.setWindowModality(Qt.WindowModal)
            dlg.setMinimumDuration(150)
            dlg.show()
            def progress_cb(pct, d, t):
                # run in main thread
                QtCore.QMetaObject.invokeMethod(dlg, "setValue", Qt.QueuedConnection, QtCore.Q_ARG(int, pct))
            def _dl():
                local, err = download_with_progress(url, name, progress_callback=progress_cb)
                QtCore.QMetaObject.invokeMethod(dlg, "close", Qt.QueuedConnection)
                if err:
                    QtWidgets.QMessageBox.critical(self, "Error descarga", str(err))
                else:
                    msg = f"Guardado en: {local}"
                    QtWidgets.QMessageBox.information(self, "Descarga completada", msg)
            threading.Thread(target=_dl, daemon=True).start()

    class MainWindow(QtWidgets.QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Proyectos de Jesús Quijada")
            self.resize(1000, 720)
            self.central = QWidget()
            self.setCentralWidget(self.central)
            layout = QVBoxLayout(self.central)
            layout.setContentsMargins(0,0,0,0)
            # Header
            header = QFrame()
            header.setObjectName("header")
            hbox = QHBoxLayout(header)
            hbox.setContentsMargins(12,12,12,12)
            title = QLabel("Proyectos de Jesús Quijada")
            title.setObjectName("title")
            hbox.addWidget(title)
            hbox.addStretch()
            self.search = QLineEdit()
            self.search.setObjectName("search")
            self.search.setPlaceholderText("Buscar proyectos...")
            search_btn = QPushButton("Buscar")
            search_btn.clicked.connect(self.on_search)
            hbox.addWidget(self.search)
            hbox.addWidget(search_btn)
            # button open downloads
            open_btn = QPushButton("Abrir descargas")
            open_btn.clicked.connect(open_downloads_folder)
            hbox.addWidget(open_btn)
            # toggle pygame mode
            pg_btn = QPushButton("Forzar Pygame")
            pg_btn.clicked.connect(lambda: self.ask_restart_pygame())
            hbox.addWidget(pg_btn)
            layout.addWidget(header)
            # Scroll area for grid
            self.scroll = QScrollArea()
            self.scroll.setWidgetResizable(True)
            self.container = QWidget()
            self.grid = QGridLayout(self.container)
            self.grid.setSpacing(12)
            self.scroll.setWidget(self.container)
            layout.addWidget(self.scroll)
            # status bar
            self.status = QtWidgets.QStatusBar()
            self.setStatusBar(self.status)
            # load repos in background
            threading.Thread(target=self.load_and_populate, daemon=True).start()

        def ask_restart_pygame(self):
            QMessageBox.information(self, "Reiniciar", "Se reiniciará en modo Pygame si acepta. La app actual se cerrará.")
            # set env var and restart process
            os.environ["USE_PYGAME"] = "1"
            QtWidgets.QApplication.quit()
            # re-exec the script
            os.execv(sys.executable, [sys.executable] + sys.argv)

        def load_and_populate(self):
            names = fetch_repo_list_quick()
            self.status.showMessage(f"Cargando {len(names)} proyectos...")
            details = []
            for i, n in enumerate(names):
                details.append(fetch_repo_details(n))
                self.status.showMessage(f"Cargando {i+1}/{len(names)}")
            # sort by rating desc (best-effort numeric)
            try:
                details.sort(key=lambda x: float(x.get("rating") or 0), reverse=True)
            except Exception:
                pass
            QtCore.QMetaObject.invokeMethod(self, lambda: self.populate(details), Qt.QueuedConnection)

        @Slot()
        def populate(self, details):
            # clear grid
            while self.grid.count():
                item = self.grid.takeAt(0)
                w = item.widget()
                if w:
                    w.setParent(None)
            cols = 3
            r = c = 0
            for d in details:
                card = RepoCard(d)
                self.grid.addWidget(card, r, c)
                c += 1
                if c >= cols:
                    c = 0; r += 1
            self.status.showMessage(f"{len(details)} proyectos cargados")

        def on_search(self):
            term = self.search.text().strip().lower()
            # naive rebuild filter
            for i in range(self.grid.count()):
                w = self.grid.itemAt(i).widget()
                if not w: continue
                name = w.info.get("display_name","").lower()
                cat = w.info.get("category","").lower()
                visible = (term in name) or (term in cat) or (not term)
                w.setVisible(visible)

    app = QApplication(sys.argv)
    app.setStyleSheet(QSS)
    mw = MainWindow()
    mw.show()
    app.exec_()

# ----------------------------
# Pygame mode
# ----------------------------
def run_pygame_mode():
    if not pygame:
        raise RuntimeError("pygame no disponible")
    import pygame as pg
    pg.init()
    ensure_download_dir()
    W, H = 1100, 700
    screen = pg.display.set_mode((W,H))
    pg.display.set_caption("Proyectos - Pygame (Glow / Cursor)")
    clock = pg.time.Clock()
    # custom cursor surface (simple colored circle) or load file if present
    cursor_surf = pg.Surface((28,28), pg.SRCALPHA)
    pg.draw.circle(cursor_surf, (255,200,0,255), (14,14), 8)
    pg.draw.circle(cursor_surf, (255,255,255,120), (14,14), 14, 2)
    pg.mouse.set_visible(False)
    # load repos (synchronously for simplicity)
    names = fetch_repo_list_quick()
    details = [fetch_repo_details(n) for n in names]
    # layout cards in grid
    cards = []
    cols = 3
    pad = 18
    card_w = (W - pad*(cols+1))//cols
    card_h = 220
    font = pg.font.SysFont(None, 20)
    small = pg.font.SysFont(None, 16)
    # prefetch small images to surfaces (best-effort)
    for idx, d in enumerate(details):
        surf = pg.Surface((card_w, card_h), pg.SRCALPHA)
        # draw bg
        surf.fill((245,245,246))
        # fetch image content for splash/icon
        img_surf = None
        url = d.get("splash") or d.get("icon") or ""
        if url:
            try:
                resp = requests.get(url, timeout=6)
                if resp.ok:
                    img_file = io.BytesIO(resp.content)
                    img = pg.image.load(img_file).convert()
                    img = pg.transform.smoothscale(img, (card_w, 110))
                    surf.blit(img, (0,0))
            except Exception:
                pass
        # store label text, position to be set later
        cards.append({"info": d, "surf": surf, "rect": pg.Rect(pad + (idx%cols)*(card_w+pad), pad + (idx//cols)*(card_h+pad), card_w, card_h)})
    # state
    running = True
    download_tasks = []  # list of dicts: {repo_name, percent, status}
    selected = None
    def spawn_download(repo):
        task = {"repo": repo, "percent":0, "status":"running"}
        download_tasks.append(task)
        def _dl():
            def cb(pct, d, t):
                task["percent"] = pct
            local, err = download_with_progress(repo["repo_zip"], repo["repo_name"], progress_callback=cb)
            if err:
                task["status"] = f"error: {err}"
            else:
                task["status"] = f"saved: {local}"
        threading.Thread(target=_dl, daemon=True).start()
    # main loop
    while running:
        for ev in pg.event.get():
            if ev.type == pg.QUIT:
                running = False
            elif ev.type == pg.MOUSEBUTTONDOWN and ev.button == 1:
                mx,my = ev.pos
                for c in cards:
                    if c["rect"].collidepoint(mx,my):
                        # open preview if exists else start download
                        info = c["info"]
                        if info.get("preview"):
                            webbrowser.open(info["preview"])
                        else:
                            spawn_download(info)
        # draw background
        screen.fill((246,247,248))
        # draw cards with glow effect behind hovered
        mx,my = pg.mouse.get_pos()
        for c in cards:
            r = c["rect"]
            hovered = r.collidepoint(mx,my)
            # glow: draw blurred rect (approx by translucent border)
            if hovered:
                glow_col = (9,105,218,80)
                glow_s = pg.Surface((r.w+20, r.h+20), pg.SRCALPHA)
                pygame = pg  # alias
                pygame.draw.rect(glow_s, glow_col, glow_s.get_rect(), border_radius=10)
                screen.blit(glow_s, (r.x-10, r.y-10), special_flags=pg.BLEND_RGBA_ADD)
            # draw card background
            card_bg = pg.Surface((r.w, r.h))
            card_bg.fill((255,255,255))
            screen.blit(card_bg, (r.x, r.y))
            # border
            pg.draw.rect(screen, (208,215,222), r, 1, border_radius=8)
            # draw top image from surf if available
            surf = c["surf"]
            screen.blit(surf, (r.x, r.y))
            # draw title
            t = font.render(c["info"]["display_name"], True, (9,105,218))
            screen.blit(t, (r.x+8, r.y + 120))
            cat = small.render(c["info"]["category"], True, (110,119,129))
            screen.blit(cat, (r.x+8, r.y + 146))
            # draw buttons rects
            btn_w = 90; btn_h = 28
            bx = r.x + r.w - btn_w - 10
            by = r.y + r.h - btn_h - 10
            btn_rect = pg.Rect(bx, by, btn_w, btn_h)
            pg.draw.rect(screen, (240,240,241), btn_rect, border_radius=6)
            pg.draw.rect(screen, (27,31,36,40), btn_rect, 1, border_radius=6)
            btn_label = small.render("Descargar", True, (0,0,0))
            screen.blit(btn_label, (bx+10, by+6))
        # draw downloads overlay
        y = H - 80
        for t in download_tasks[-3:]:
            txt = f"{t['repo']['repo_name']} - {t.get('percent',0)}% - {t.get('status','')}"
            lbl = small.render(txt, True, (30,30,30))
            screen.blit(lbl, (10,y)); y += 22
        # draw custom cursor
        cx, cy = pg.mouse.get_pos()
        screen.blit(cursor_surf, (cx-14, cy-14))
        pg.display.flip()
        clock.tick(60)
    pg.quit()

# ----------------------------
# Console fallback
# ----------------------------
def run_console_fallback():
    # try rich interactive console
    if rich:
        from rich.console import Console
        console = Console()
        console.print("[bold green]Modo consola[/]")
        names = fetch_repo_list_quick()
        repos = [fetch_repo_details(n) for n in names]
        from rich.table import Table
        t = Table()
        t.add_column("#")
        t.add_column("Nombre")
        t.add_column("Categoria")
        t.add_column("Rating")
        for i,r in enumerate(repos,1):
            t.add_row(str(i), r["display_name"], r["category"], str(r["rating"]))
        console.print(t)
        console.print("Comando: d <n> descargar / p <n> preview / q salir")
        while True:
            cmd = console.input(">> ")
            if not cmd: continue
            if cmd in ("q","exit","quit"): break
            if cmd.startswith("d "):
                try:
                    idx = int(cmd.split()[1]) - 1
                    repo = repos[idx]
                    console.print(f"Descargando {repo['repo_name']} ...")
                    download_with_progress(repo["repo_zip"], repo["repo_name"], progress_callback=lambda pct,d,t: console.print(f"{pct}%"),)
                except Exception as e:
                    console.print("[red]Error[/]", e)
            if cmd.startswith("p "):
                try:
                    idx = int(cmd.split()[1]) - 1
                    repo = repos[idx]
                    if repo.get("preview"):
                        webbrowser.open(repo["preview"])
                    else:
                        console.print("[yellow]No hay preview[/]")
                except Exception as e:
                    console.print("[red]Error[/]", e)
    else:
        print("Consola simple:")
        names = fetch_repo_list_quick()
        for i,n in enumerate(names,1):
            print(i, n)
        print("Abrir en navegador: https://jesusquijada34.github.io/")

# ----------------------------
# Main launcher
# ----------------------------
def main():
    # prefer Pygame if forced
    if USE_PYGAME:
        try:
            run_pygame_mode()
            return
        except Exception as e:
            print("Error modo Pygame:", e)
    # try PySide6 GUI first
    try:
        run_pyside6_gui()
        return
    except Exception as e:
        print("PySide6 GUI no disponible o falló:", e)
    # If PySide6 failed, try pygame if available
    if pygame:
        try:
            run_pygame_mode()
            return
        except Exception as e:
            print("Pygame fallback falló:", e)
    # else try webview
    if pywebview:
        try:
            import webview
            webview.create_window("Proyectos - web", "https://jesusquijada34.github.io/")
            webview.start()
            return
        except Exception as e:
            print("webview fallback falló:", e)
    # else console
    run_console_fallback()

if __name__ == "__main__":
    main()
