#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Flatr Apps Updater
# - GUI con PySide6
# - Modo daemon con argumento -daemon (revisa cada 15s)
#
# Requisitos: pip install PySide6 requests plyer

import sys, os, re, shutil, time, threading
from pathlib import Path
import xml.etree.ElementTree as ET
import requests
from plyer import notification
from PySide6 import QtCore, QtGui, QtWidgets

# Configuración
GITHUB_USER = "JesusQuijada34"
CHECK_INTERVAL = 15  # segundos

# -----------------------
# Utilidades
# -----------------------
def find_documents_candidates():
    home = Path.home()
    candidates = [
        home / "Documents",
        home / "Documentos",
        home / "Mis documentos",
        home / "My Documents",
    ]
    up = os.environ.get("USERPROFILE")
    if up:
        candidates.append(Path(up) / "Documents")
    return [p for p in candidates if p.exists()]

def parse_details(path: Path):
    try:
        root = ET.parse(str(path)).getroot()
        app_id = root.find("app").text.strip()
        version = root.find("version").text.strip()
        return app_id, version
    except Exception:
        return None, None

def version_tuple(vstr):
    nums = re.findall(r"\d+", vstr or "")
    return tuple(int(x) for x in nums) if nums else (0,)

def remote_details(app_id):
    url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{app_id}/main/details.xml"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            root = ET.fromstring(r.text)
            ver = root.find("version").text.strip()
            return r.text, ver
    except Exception:
        pass
    return None, None

def safe_backup(path: Path):
    if path.exists():
        shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))

def update_app(app_folder: Path):
    local_details = app_folder / "details.xml"
    app_id, local_ver = parse_details(local_details)
    if not app_id:
        return None
    remote_xml, remote_ver = remote_details(app_id)
    if not remote_ver:
        return None

    if version_tuple(remote_ver) > version_tuple(local_ver):
        safe_backup(local_details)
        local_details.write_text(remote_xml, encoding="utf-8")

        # Actualizar todos los archivos locales (excepto .bak)
        for root, _, files in os.walk(app_folder):
            for fname in files:
                if fname.endswith(".bak") or fname == "details.xml":
                    continue
                rel = os.path.relpath(os.path.join(root, fname), app_folder)
                url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{app_id}/main/{rel.replace(os.sep,'/')}"
                try:
                    r = requests.get(url, timeout=10)
                    if r.status_code == 200:
                        fpath = app_folder / rel
                        safe_backup(fpath)
                        fpath.write_text(r.text, encoding="utf-8")
                except Exception:
                    pass

        # Notificación
        notification.notify(
            title="Flatr Apps Updater",
            message=f"{app_id} actualizado a {remote_ver}",
            timeout=5
        )
        return app_id, local_ver, remote_ver
    return None

def scan_all_apps():
    results = []
    for doc in find_documents_candidates():
        flatr = doc / "Flatr Apps"
        if flatr.is_dir():
            for root, _, files in os.walk(flatr):
                if "details.xml" in files:
                    app_id, local_ver = parse_details(Path(root) / "details.xml")
                    if app_id:
                        _, remote_ver = remote_details(app_id)
                        results.append((root, app_id, local_ver, remote_ver or "—"))
    return results

# -----------------------
# Daemon mode
# -----------------------
def daemon_loop():
    while True:
        for doc in find_documents_candidates():
            flatr = doc / "Flatr Apps"
            if flatr.is_dir():
                for root, _, files in os.walk(flatr):
                    if "details.xml" in files:
                        update_app(Path(root))
        time.sleep(CHECK_INTERVAL)

# -----------------------
# GUI
# -----------------------
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Flatr Apps Updater")
        self.resize(800, 500)

        self.table = QtWidgets.QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["#", "App", "Versión local", "Versión remota", "Acción"])
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)

        refresh_btn = QtWidgets.QPushButton("🔄 Escanear")
        refresh_btn.clicked.connect(self.populate)

        update_all_btn = QtWidgets.QPushButton("⬆️ Actualizar todas")
        update_all_btn.clicked.connect(self.update_all)

        toolbar = QtWidgets.QHBoxLayout()
        toolbar.addWidget(refresh_btn)
        toolbar.addWidget(update_all_btn)
        toolbar.addStretch()

        top = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(top)
        v.addLayout(toolbar)
        v.addWidget(self.table)
        self.setCentralWidget(top)

        # Bandeja
        self.tray = QtWidgets.QSystemTrayIcon(QtGui.QIcon())
        self.tray.setToolTip("Flatr Apps Updater")
        menu = QtWidgets.QMenu()
        act_show = menu.addAction("Mostrar ventana")
        act_show.triggered.connect(self.showNormal)
        act_exit = menu.addAction("Salir")
        act_exit.triggered.connect(QtWidgets.QApplication.quit)
        self.tray.setContextMenu(menu)
        self.tray.show()

        self.apps = []
        self.populate()

    def populate(self):
        self.apps = scan_all_apps()
        self.table.setRowCount(len(self.apps))
        for i, (_, app_id, local, remote) in enumerate(self.apps):
            self.table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(i+1)))
            self.table.setItem(i, 1, QtWidgets.QTableWidgetItem(app_id))
            self.table.setItem(i, 2, QtWidgets.QTableWidgetItem(local))
            self.table.setItem(i, 3, QtWidgets.QTableWidgetItem(remote))
            btn = QtWidgets.QPushButton("Actualizar")
            btn.clicked.connect(lambda _, row=i: self.update_one(row))
            self.table.setCellWidget(i, 4, btn)

    def update_one(self, row):
        root, app_id, _, _ = self.apps[row]
        result = update_app(Path(root))
        if result:
            _, old_v, new_v = result
            QtWidgets.QMessageBox.information(self, "Actualizado", f"{app_id}: {old_v} → {new_v}")
        self.populate()

    def update_all(self):
        for i, (root, app_id, _, _) in enumerate(self.apps):
            update_app(Path(root))
        self.populate()

# -----------------------
# Main
# -----------------------
if __name__ == "__main__":
    if "-daemon" in sys.argv:
        print("Flatr Apps Updater corriendo en segundo plano cada 15s...")
        daemon_loop()
    else:
        app = QtWidgets.QApplication(sys.argv)
        win = MainWindow()
        win.show()
        sys.exit(app.exec())
      
