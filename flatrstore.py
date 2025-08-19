# flatr_store_grid_qss.py
import sys
import os
import re
import json
import shutil
import tempfile
import zipfile
import html
import threading
import hashlib
import platform
from pathlib import Path
from xml.etree import ElementTree as ET
from functools import partial
from datetime import datetime, timedelta

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt5.QtGui import QPixmap, QIcon, QFontDatabase, QFont, QColor, QPalette
from PyQt5.QtWidgets import (
    QApplication, QWidget, QMainWindow, QLabel, QLineEdit, QPushButton,
    QHBoxLayout, QVBoxLayout, QMessageBox, QToolButton, QScrollArea,
    QGridLayout, QComboBox, QProgressBar, QFrame, QSystemTrayIcon, QMenu, QStyle
)

try:
    import requests
except ImportError:
    raise RuntimeError("Instala 'requests' (pip install requests)")

try:
    import markdown
except ImportError:
    raise RuntimeError("Instala 'markdown' (pip install markdown)")

# ----------------------------
# CONFIG
# ----------------------------
RAW_LIST_URL = "https://raw.githubusercontent.com/JesusQuijada34/catalog/refs/heads/main/repo.list"
RAW_BASE = "https://raw.githubusercontent.com/JesusQuijada34"
GITHUB_BASE = "https://github.com/JesusQuijada34"
HOME = Path.home()
INSTALL_BASE = HOME / "Documents" / "Flatr Apps" if platform.system() != "Windows" else Path(os.getenv('APPDATA')) / "Flatr Apps"
CACHE_DIR = HOME / ".flatr_store_cache"
ICON_CACHE_DIR = CACHE_DIR / "icons"
ICON_INDEX_FILE = ICON_CACHE_DIR / "index.json"
VERSION_CHECK_INTERVAL = 20 * 60 * 1000  # 20 minutos en milisegundos
CACHE_DIR.mkdir(parents=True, exist_ok=True)
ICON_CACHE_DIR.mkdir(parents=True, exist_ok=True)

ROBOTO_TTF_URL = "https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Regular.ttf"
OFFLINE_ICON_PATH = Path(__file__).parent / "app" / "offlinemd.ico" #"offline-icon.ico"
MAIN_ICON = Path(__file__).parent / "app" / "app-icon.ico"

# ----------------------------
# THEME QSS
# ----------------------------
APP_QSS_DARK = r"""
/* Main window background */
QMainWindow {
    background-color: #2d2d2d;
    color: #ffffff;
}

/* Header */
#TopHeader {
    background: #1e1e1e;
    color: #ffffff;
    font-weight: 700;
    padding: 10px;
    border-bottom: 1px solid #3a3a3a;
}

/* Search and controls */
QLineEdit {
    background: #3a3a3a;
    border: 1px solid #4a4a4a;
    padding: 6px 8px;
    border-radius: 4px;
    color: #ffffff;
    selection-background-color: #4a6da7;
}

QComboBox {
    background: #3a3a3a;
    border: 1px solid #4a4a4a;
    padding: 4px 8px;
    border-radius: 4px;
    color: #ffffff;
}

QComboBox QAbstractItemView {
    background: #3a3a3a;
    color: #ffffff;
    selection-background-color: #4a6da7;
    border: 1px solid #4a4a4a;
}

/* App buttons */
QPushButton#appButton {
    background-color: #3a3a3a;
    border: 1px solid #4a4a4a;
    border-radius: 6px;
    padding: 5px;
    color: #ffffff;
}

QPushButton#appButton:hover {
    background-color: #4a4a4a;
    border: 1px solid #5a5a5a;
}

QPushButton#appButton:pressed {
    background-color: #2a2a2a;
    border: 1px solid #3a3a3a;
}

/* Big action buttons */
QPushButton {
    background: #4a6da7;
    color: #ffffff;
    border-radius: 4px;
    padding: 8px 12px;
    border: 1px solid #3a5a8a;
    font-weight: 600;
}

QPushButton:hover {
    background: #5a7db7;
}

QPushButton:pressed {
    background: #3a5a97;
}

/* Progress bar */
QProgressBar {
    border: 1px solid #3a3a3a;
    border-radius: 4px;
    text-align: center;
    background: #2a2a2a;
    color: #ffffff;
}

QProgressBar::chunk {
    background: #4a6da7;
    border-radius: 4px;
}

/* Custom MessageBox */
QMessageBox {
    background: #2d2d2d;
    color: #ffffff;
    border: 1px solid #3a3a3a;
}

QMessageBox QLabel {
    color: #ffffff;
}

QMessageBox QPushButton {
    min-width: 90px;
    padding: 6px;
}

/* Scroll area */
QScrollArea {
    border: none;
    background: transparent;
}

QScrollBar:vertical {
    border: none;
    background: #2d2d2d;
    width: 10px;
    margin: 0px 0px 0px 0px;
}

QScrollBar::handle:vertical {
    background: #4a4a4a;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    background: none;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

/* Offline mode */
#OfflineMode {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #27B224, stop:1 #4DB224);
}

#OfflineLabel {
    color: #aaaaaa;
    font-size: 16pt;
    qproperty-alignment: AlignCenter;
}
"""

APP_QSS_LIGHT = r"""
/* Main window background */
QMainWindow {
    background-color: #f5f5f5;
    color: #333333;
}

/* Header */
#TopHeader {
    background: #e0e0e0;
    color: #333333;
    font-weight: 700;
    padding: 10px;
    border-bottom: 1px solid #cccccc;
}

/* Search and controls */
QLineEdit {
    background: #ffffff;
    border: 1px solid #cccccc;
    padding: 6px 8px;
    border-radius: 4px;
    color: #333333;
    selection-background-color: #4a6da7;
}

QComboBox {
    background: #ffffff;
    border: 1px solid #cccccc;
    padding: 4px 8px;
    border-radius: 4px;
    color: #333333;
}

QComboBox QAbstractItemView {
    background: #ffffff;
    color: #333333;
    selection-background-color: #4a6da7;
    border: 1px solid #cccccc;
}

/* App buttons */
QPushButton#appButton {
    background-color: #ffffff;
    border: 1px solid #cccccc;
    border-radius: 6px;
    padding: 5px;
    color: #333333;
}

QPushButton#appButton:hover {
    background-color: #f0f0f0;
    border: 1px solid #bbbbbb;
}

QPushButton#appButton:pressed {
    background-color: #e0e0e0;
    border: 1px solid #aaaaaa;
}

/* Big action buttons */
QPushButton {
    background: #4a6da7;
    color: #ffffff;
    border-radius: 4px;
    padding: 8px 12px;
    border: 1px solid #3a5a8a;
    font-weight: 600;
}

QPushButton:hover {
    background: #5a7db7;
}

QPushButton:pressed {
    background: #3a5a97;
}

/* Progress bar */
QProgressBar {
    border: 1px solid #cccccc;
    border-radius: 4px;
    text-align: center;
    background: #ffffff;
    color: #333333;
}

QProgressBar::chunk {
    background: #4a6da7;
    border-radius: 4px;
}

/* Custom MessageBox */
QMessageBox {
    background: #ffffff;
    color: #333333;
    border: 1px solid #cccccc;
}

QMessageBox QLabel {
    color: #333333;
}

QMessageBox QPushButton {
    min-width: 90px;
    padding: 6px;
}

/* Scroll area */
QScrollArea {
    border: none;
    background: transparent;
}

QScrollBar:vertical {
    border: none;
    background: #f5f5f5;
    width: 10px;
    margin: 0px 0px 0px 0px;
}

QScrollBar::handle:vertical {
    background: #cccccc;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    background: none;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

/* Offline mode */
#OfflineMode {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #34CD80, stop:1 #34CDCC);
}

#OfflineLabel {
    color: #666666;
    font-size: 16pt;
    qproperty-alignment: AlignCenter;
}
"""

# ----------------------------
# UTILITIES
# ----------------------------
def safe_name(s: str) -> str:
    s = html.unescape(s or "")
    s = s.strip()
    s = re.sub(r"[^\w.-]", "_", s)
    return s or "unknown"

def ensure_install_base():
    INSTALL_BASE.mkdir(parents=True, exist_ok=True)

def parse_details_xml(xml_text: str):
    res = {"publisher": "", "name": "", "version": "", "raw": xml_text}
    if not xml_text:
        return res
    try:
        root = ET.fromstring(xml_text)
        def find_any(base, tag):
            el = base.find(tag)
            if el is not None and el.text:
                return el.text.strip()
            for it in base.iter():
                if it.tag.lower().endswith(tag.lower()) and it.text:
                    return it.text.strip()
            return None
        if root.tag.lower() == "app":
            res["publisher"] = find_any(root, "publisher") or ""
            res["name"] = find_any(root, "name") or ""
            res["version"] = find_any(root, "version") or ""
        else:
            app_elem = root.find("app")
            if app_elem is not None:
                res["publisher"] = find_any(app_elem, "publisher") or ""
                res["name"] = find_any(app_elem, "name") or ""
                res["version"] = find_any(app_elem, "version") or ""
            else:
                res["publisher"] = find_any(root, "publisher") or ""
                res["name"] = find_any(root, "name") or ""
                res["version"] = find_any(root, "version") or ""
    except Exception:
        pass
    return res

def installed_version_for(info: dict):
    pub = safe_name(info.get("publisher") or "unknown")
    nm = safe_name(info.get("app") or info.get("name") or info.get("repo"))
    versions = list(INSTALL_BASE.glob(f"{pub}.{nm}.*"))
    if not versions:
        return None, None
    dest = sorted(versions, key=lambda p: p.name, reverse=True)[0]
    details_path = None
    if (dest / "details.xml").is_file():
        details_path = dest / "details.xml"
    else:
        for p in dest.rglob("details.xml"):
            details_path = p
            break
    if details_path and details_path.exists():
        try:
            txt = details_path.read_text(encoding="utf-8", errors="ignore")
            parsed = parse_details_xml(txt)
            return parsed.get("version") or None, dest
        except Exception:
            return None, dest
    return None, dest

def cache_load():
    cache_file = CACHE_DIR / "repos_cache.json"
    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None

def cache_save(data):
    cache_file = CACHE_DIR / "repos_cache.json"
    try:
        cache_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

def load_icon_index():
    try:
        if ICON_INDEX_FILE.exists():
            return json.loads(ICON_INDEX_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}

def save_icon_index(idx):
    try:
        ICON_INDEX_FILE.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

def icon_hash(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()

def save_icon_to_cache_unique(repo: str, publisher: str, name: str, version: str, content: bytes):
    if not content:
        return None, None
    h = icon_hash(content)
    idx = load_icon_index()
    if h in idx:
        return idx[h], h
    fname = f"{safe_name(publisher)}.{safe_name(name)}.{safe_name(version)}.ico"
    path = ICON_CACHE_DIR / fname
    if path.exists():
        base = path.stem
        i = 1
        while True:
            candidate = ICON_CACHE_DIR / f"{base}_{i}.ico"
            if not candidate.exists():
                path = candidate
                break
            i += 1
    try:
        path.write_bytes(content)
        rel = str(path)
        idx[h] = rel
        save_icon_index(idx)
        return rel, h
    except Exception:
        return None, None

def load_icon_bytes(path_str):
    try:
        if not path_str:
            return None
        p = Path(path_str)
        if p.exists():
            return p.read_bytes()
    except Exception:
        pass
    return None

def create_windows_shortcut(target_path, shortcut_name, description="", icon_path=None):
    if platform.system() != "Windows":
        return False

    try:
        import winshell
        from win32com.client import Dispatch

        desktop = winshell.desktop()
        shortcut_path = os.path.join(desktop, f"{shortcut_name}.lnk")

        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = str(target_path)
        shortcut.WorkingDirectory = str(target_path.parent)
        shortcut.Description = description
        if icon_path:
            shortcut.IconLocation = str(icon_path)
        shortcut.save()
        return True
    except Exception:
        return False

# ----------------------------
# CONNECTIVITY
# ----------------------------
def is_connected(timeout=3):
    try:
        r = requests.head("https://raw.githubusercontent.com", timeout=timeout)
        return r.status_code < 500
    except Exception:
        try:
            r = requests.head("https://www.google.com", timeout=timeout)
            return r.status_code < 500
        except Exception:
            return False

class StyledMessageBox(QMessageBox):
    def __init__(self, title, text, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setText(text)
        self.setIcon(QMessageBox.Warning)
        self.setStandardButtons(QMessageBox.Ok)
        self.setStyleSheet("")

# ----------------------------
# THREADS
# ----------------------------
class RepoFetchThread(QThread):
    progress = pyqtSignal(int)
    finished_fetch = pyqtSignal(list)
    error = pyqtSignal(str)

    def run(self):
        try:
            r = requests.get(RAW_LIST_URL, timeout=20)
            r.raise_for_status()
            text = r.text
            self.progress.emit(10)
            repos = [r0.strip() for r0 in re.split(r'[,\n\r]+', text) if r0.strip()]
            results = []
            total = max(1, len(repos))

            for i, repo in enumerate(repos, start=1):
                item = self._fetch_repo_info(repo)
                if item:
                    results.append(item)
                self.progress.emit(10 + int(80 * (i / total)))

            unique_results = []
            seen_keys = set()
            for item in results:
                key = (item.get("app") or item.get("name", ""), item.get("publisher", ""))
                if key not in seen_keys and key != ("", ""):
                    seen_keys.add(key)
                    unique_results.append(item)

            self.progress.emit(100)
            cache_save(unique_results)
            self.finished_fetch.emit(unique_results)
        except Exception as e:
            self.error.emit(str(e))

    def _fetch_repo_info(self, repo):
        try:
            # Fetch details.xml first
            details_url = f"{RAW_BASE}/{repo}/main/details.xml"
            details_response = requests.get(details_url, timeout=8)
            details_xml = details_response.text if details_response.ok else ""

            parsed = parse_details_xml(details_xml)
            app_name = parsed.get("app") or parsed.get("name") or repo.split("/")[-1]
            publisher = parsed.get("publisher") or "unknown"
            version = parsed.get("version") or "0.0.0"

            # Fetch README
            readme_urls = [
                f"{RAW_BASE}/{repo}/main/README.md",
                f"{RAW_BASE}/{repo}/main/readme.md"
            ]
            readme_text = ""
            for url in readme_urls:
                try:
                    readme_response = requests.get(url, timeout=6)
                    if readme_response.ok:
                        readme_text = readme_response.text
                        break
                except Exception:
                    pass

            # Fetch icon
            icon_urls = [
                f"{RAW_BASE}/{repo}/main/app/app-icon.ico",
            ]
            icon_bytes = None
            for url in icon_urls:
                try:
                    icon_response = requests.get(url, timeout=6)
                    if icon_response.ok and icon_response.content:
                        icon_bytes = icon_response.content
                        break
                except Exception:
                    pass

            icon_cache_path, icon_h = None, None
            if icon_bytes:
                icon_cache_path, icon_h = save_icon_to_cache_unique(
                    repo, publisher, app_name, version, icon_bytes)

            item = {
                "repo": repo,
                "app": app_name,
                "name": parsed.get("name") or app_name,
                "publisher": publisher,
                "version": version,
                "icon_cache_path": icon_cache_path,
                "icon_hash": icon_h,
                "readme": readme_text,
                "details_xml": details_xml,
            }

            iv, dest = installed_version_for(item)
            item["installed_version"] = iv
            item["installed_path"] = str(dest) if dest else None
            item["update_available"] = False
            if iv and version and (iv != version):
                item["update_available"] = True

            return item
        except Exception:
            return None

class InstallThread(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished_install = pyqtSignal(bool, str, dict)  # Added info dict to return

    def __init__(self, info: dict, parent=None):
        super().__init__(parent)
        self.info = info
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            ensure_install_base()
            pub = safe_name(self.info.get("publisher") or "unknown")
            app_name = safe_name(self.info.get("app") or self.info.get("repo"))
            ver = safe_name(self.info.get("version") or "0.0.0")
            dest = INSTALL_BASE / f"{pub}.{app_name}.{ver}"
            zip_url = f"{GITHUB_BASE}/{self.info['repo']}/archive/refs/heads/main.zip"

            self.status.emit("Descargando...")
            tmp_file = None
            try:
                r = requests.get(zip_url, stream=True, timeout=30)
                if r.status_code != 200:
                    self.finished_install.emit(False, f"HTTP {r.status_code} al descargar ZIP", self.info)
                    return

                total = int(r.headers.get("content-length", 0) or 0)
                fd, path = tempfile.mkstemp(suffix=".zip")
                tmp_file = Path(path)
                downloaded = 0
                chunk = 8192

                with open(path, "wb") as fdobj:
                    for data in r.iter_content(chunk_size=chunk):
                        if self._cancelled:
                            self.finished_install.emit(False, "Cancelado", self.info)
                            try:
                                fdobj.close()
                            except Exception:
                                pass
                            try:
                                tmp_file.unlink()
                            except Exception:
                                pass
                            return
                        if data:
                            fdobj.write(data)
                            downloaded += len(data)
                            if total:
                                self.progress.emit(int(downloaded * 100 / total))

                self.status.emit("Descomprimiendo...")
                tmp_extract_dir = Path(tempfile.mkdtemp(prefix="flatr_extract_"))

                with zipfile.ZipFile(str(tmp_file), "r") as zf:
                    zf.extractall(str(tmp_extract_dir))

                if dest.exists():
                    shutil.rmtree(dest)
                dest.mkdir(parents=True, exist_ok=True)

                entries = [p for p in tmp_extract_dir.iterdir()]
                if len(entries) == 1 and entries[0].is_dir():
                    top = entries[0]
                    for child in top.iterdir():
                        target = dest / child.name
                        if target.exists():
                            if target.is_dir():
                                shutil.rmtree(target)
                            else:
                                target.unlink()
                        shutil.move(str(child), str(target))
                else:
                    for child in entries:
                        target = dest / child.name
                        if target.exists():
                            if target.is_dir():
                                shutil.rmtree(target)
                            else:
                                target.unlink()
                        shutil.move(str(child), str(target))

                # Save metadata
                details_xml = self.info.get("details_xml")
                if details_xml:
                    try:
                        (dest / "details.xml").write_text(details_xml, encoding="utf-8")
                    except Exception:
                        pass

                readme = self.info.get("readme")
                if readme:
                    try:
                        (dest / "README.md").write_text(readme, encoding="utf-8")
                    except Exception:
                        pass

                # Create Windows shortcut if applicable
                if platform.system() == "Windows":
                    main_script = None
                    for ext in [".py", ".exe", ".bat"]:
                        candidate = dest / f"{app_name}{ext}"
                        if candidate.exists():
                            main_script = candidate
                            break

                    if main_script:
                        icon_path = None
                        for icon_file in ["app-icon.ico", "icon.ico"]:
                            candidate = dest / "app" / icon_file
                            if candidate.exists():
                                icon_path = candidate
                                break

                        create_windows_shortcut(
                            main_script,
                            self.info.get("name") or app_name,
                            self.info.get("name") or app_name,
                            icon_path
                        )

                self.progress.emit(100)
                self.finished_install.emit(True, f"Instalado en: {dest}", self.info)
            finally:
                try:
                    if tmp_file and tmp_file.exists():
                        tmp_file.unlink()
                except Exception:
                    pass
                try:
                    if 'tmp_extract_dir' in locals() and tmp_extract_dir.exists():
                        shutil.rmtree(tmp_extract_dir, ignore_errors=True)
                except Exception:
                    pass
        except Exception as e:
            self.finished_install.emit(False, f"Error: {e}", self.info)

class VersionCheckThread(QThread):
    update_available = pyqtSignal(dict)
    no_updates = pyqtSignal()

    def __init__(self, repo_list, parent=None):
        super().__init__(parent)
        self.repo_list = repo_list
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            updates_found = False
            for info in self.repo_list:
                if self._cancelled:
                    return

                # Skip if not installed
                if not info.get("installed_version"):
                    continue

                # Fetch current version from repo
                try:
                    details_url = f"{RAW_BASE}/{info['repo']}/main/details.xml"
                    details_response = requests.get(details_url, timeout=10)
                    if details_response.ok:
                        parsed = parse_details_xml(details_response.text)
                        remote_version = parsed.get("version")

                        if remote_version and remote_version != info.get("installed_version"):
                            updates_found = True
                            new_info = info.copy()
                            new_info["version"] = remote_version
                            new_info["update_available"] = True
                            self.update_available.emit(new_info)
                except Exception:
                    continue

            if not updates_found:
                self.no_updates.emit()
        except Exception:
            self.no_updates.emit()

# ----------------------------
# UI: App Button and Detail Dialog
# ----------------------------
class AppButton(QPushButton):
    def __init__(self, info: dict, parent=None):
        super().__init__(parent)
        self.info = info
        self.setObjectName("appButton")
        self.setFixedSize(120, 120)
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(64, 64)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.set_icon()

        self.name_label = QLabel(info.get("name") or info.get("app") or info.get("repo"))
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setStyleSheet("font-size: 10px;")
        self.name_label.setWordWrap(True)

        layout.addWidget(self.icon_label, 0, Qt.AlignCenter)
        layout.addWidget(self.name_label, 0, Qt.AlignCenter)
        self.setLayout(layout)

        # Tooltip with info
        tip = f"{info.get('name') or info.get('app')}"
        if info.get("publisher"):
            tip += f"\nPublicado por: {info['publisher']}"
        if info.get("version"):
            tip += f"\nVersión: {info['version']}"
        if info.get("installed_version"):
            tip += f"\nInstalado: {info['installed_version']}"
            if info.get("update_available"):
                tip += "\n(Actualización disponible)"
        self.setToolTip(tip)

    def set_icon(self):
        b = None
        if self.info.get("icon_cache_path"):
            b = load_icon_bytes(self.info.get("icon_cache_path"))

        if b:
            pixmap = QPixmap()
            pixmap.loadFromData(b)
            pixmap = pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.icon_label.setPixmap(pixmap)
        else:
            # Default icon
            pixmap = QPixmap(64, 64)
            pixmap.fill(Qt.transparent)
            self.icon_label.setPixmap(pixmap)

class AppDetailDialog(QtWidgets.QDialog):
    def __init__(self, info: dict, parent=None):
        super().__init__(parent)
        self.info = info
        self.setWindowTitle(info.get("name") or info.get("app") or info.get("repo"))
        self.resize(800, 600)
        self.setup_ui()
        self.load_readme()

    def setup_ui(self):
        layout = QVBoxLayout()
        top_h = QHBoxLayout()

        # App icon and basic info
        icon_widget = QWidget()
        icon_layout = QVBoxLayout()
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(96, 96)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.set_icon()
        icon_layout.addWidget(self.icon_label, 0, Qt.AlignCenter)

        title = QLabel(self.info.get("name") or self.info.get("app") or self.info.get("repo"))
        title.setStyleSheet("font-size: 16pt; font-weight: bold;")
        icon_layout.addWidget(title, 0, Qt.AlignCenter)

        version = QLabel(f"Versión: {self.info.get('version') or 'Desconocida'}")
        version.setStyleSheet("color: #666666;")
        icon_layout.addWidget(version, 0, Qt.AlignCenter)

        if self.info.get("publisher"):
            publisher = QLabel(f"Publicado por: {self.info.get('publisher')}")
            publisher.setStyleSheet("color: #666666;")
            icon_layout.addWidget(publisher, 0, Qt.AlignCenter)

        icon_widget.setLayout(icon_layout)
        top_h.addWidget(icon_widget)

        # Action buttons
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(8)

        self.install_btn = QPushButton("Instalar")
        self.uninstall_btn = QPushButton("Desinstalar")
        self.open_folder_btn = QPushButton("Abrir carpeta")

        self.install_btn.clicked.connect(self.on_install)
        self.uninstall_btn.clicked.connect(self.on_uninstall)
        self.open_folder_btn.clicked.connect(self.on_open_folder)

        btn_layout.addWidget(self.install_btn)
        btn_layout.addWidget(self.uninstall_btn)
        btn_layout.addWidget(self.open_folder_btn)
        btn_layout.addStretch()

        top_h.addLayout(btn_layout)
        layout.addLayout(top_h)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        # Readme view
        self.readme_view = QtWidgets.QTextBrowser()
        self.readme_view.setOpenExternalLinks(True)
        layout.addWidget(self.readme_view, 1)

        self.setLayout(layout)
        self.update_install_state()

    def set_icon(self):
        b = None
        if self.info.get("icon_cache_path"):
            b = load_icon_bytes(self.info.get("icon_cache_path"))

        if b:
            pixmap = QPixmap()
            pixmap.loadFromData(b)
            pixmap = pixmap.scaled(96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.icon_label.setPixmap(pixmap)
        else:
            pixmap = QPixmap(96, 96)
            pixmap.fill(Qt.transparent)
            self.icon_label.setPixmap(pixmap)

    def load_readme(self):
        md = self.info.get("readme") or ""
        if md:
            html_text = markdown.markdown(md, extensions=['fenced_code', 'tables', 'codehilite'])
            self.readme_view.setHtml(html_text)
            return

        def fetch():
            for ru in [
                f"{RAW_BASE}/{self.info['repo']}/main/README.md",
                f"{RAW_BASE}/{self.info['repo']}/main/readme.md",
            ]:
                try:
                    rr = requests.get(ru, timeout=8)
                    if rr.ok and rr.text.strip():
                        html_text = markdown.markdown(rr.text, extensions=['fenced_code', 'tables', 'codehilite'])
                        QtCore.QMetaObject.invokeMethod(
                            self.readme_view, "setHtml", Qt.QueuedConnection,
                            QtCore.Q_ARG(str, html_text))
                        return
                except Exception:
                    pass
            QtCore.QMetaObject.invokeMethod(
                self.readme_view, "setHtml", Qt.QueuedConnection,
                QtCore.Q_ARG(str, "<i>No hay README disponible.</i>"))

        threading.Thread(target=fetch, daemon=True).start()

    def dest_folder(self) -> Path:
        pub = safe_name(self.info.get("publisher") or "unknown")
        app_name = safe_name(self.info.get("app") or self.info.get("repo"))
        ver = safe_name(self.info.get("version") or "0.0.0")
        return INSTALL_BASE / f"{pub}.{app_name}.{ver}"

    def update_install_state(self):
        installed = self.dest_folder().exists()
        self.install_btn.setEnabled(not installed)
        self.uninstall_btn.setEnabled(installed)
        self.open_folder_btn.setEnabled(installed)

    def on_install(self):
        dest = self.dest_folder()
        reply = QMessageBox.question(
            self, "Confirmar",
            f"¿Instalar en:\n{dest}?",
            QMessageBox.Yes | QMessageBox.No)

        if reply != QMessageBox.Yes:
            return

        self.install_btn.setEnabled(False)
        self.thread = InstallThread(self.info)
        self.thread.progress.connect(self.progress.setValue)
        self.thread.finished_install.connect(self.on_finished)
        self.thread.start()

    def on_finished(self, ok: bool, msg: str, info: dict):
        QMessageBox.information(self, "Instalación", msg if ok else f"Error: {msg}")
        self.info = info
        self.update_install_state()

    def on_uninstall(self):
        dest = self.dest_folder()
        if not dest.exists():
            QMessageBox.information(self, "No instalado", "No está instalado.")
            self.update_install_state()
            return

        reply = QMessageBox.question(
            self, "Confirmar",
            f"¿Eliminar {dest}?",
            QMessageBox.Yes | QMessageBox.No)

        if reply != QMessageBox.Yes:
            return

        try:
            shutil.rmtree(dest)
            QMessageBox.information(self, "Eliminado", "Desinstalado correctamente.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo eliminar: {e}")

        self.update_install_state()

    def on_open_folder(self):
        dest = self.dest_folder()
        if not dest.exists():
            QMessageBox.information(self, "No instalado", "No está instalado.")
            return

        try:
            if sys.platform.startswith("darwin"):
                __import__("subprocess").call(["open", str(dest)])
            elif os.name == "nt":
                os.startfile(str(dest))
            else:
                __import__("subprocess").call(["xdg-open", str(dest)])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir: {e}")

# ----------------------------
# MAIN WINDOW: Grid UI
# ----------------------------
class GridView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.grid = QGridLayout()
        self.grid.setAlignment(Qt.AlignTop)
        self.grid.setSpacing(15)
        self.grid.setContentsMargins(15, 15, 15, 15)
        self.container.setLayout(self.grid)
        self.scroll.setWidget(self.container)
        layout = QVBoxLayout()
        layout.addWidget(self.scroll)
        self.setLayout(layout)
        self.items = []  # list of (info, widget)

    def clear(self):
        for i in reversed(range(self.grid.count())):
            item = self.grid.itemAt(i)
            w = item.widget()
            if w:
                w.setParent(None)
        self.items = []

    def populate(self, infos, columns):
        self.clear()
        row = col = 0

        for info in infos:
            btn = AppButton(info)
            btn.clicked.connect(partial(self.open_detail, info))

            self.grid.addWidget(btn, row, col)
            self.items.append((info, btn))

            col += 1
            if col >= columns:
                col = 0
                row += 1

    def open_detail(self, info):
        iv, dest = installed_version_for(info)
        info["installed_version"] = iv
        info["installed_path"] = str(dest) if dest else None
        info["update_available"] = False
        if iv and info.get("version") and (iv != info.get("version")):
            info["update_available"] = True

        dlg = AppDetailDialog(info, parent=self)
        dlg.exec_()

class OfflineMode(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("OfflineMode")
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        # Icon
        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.set_icon()
        layout.addWidget(self.icon_label)

        # Message
        message = QLabel("No hay conexión a internet")
        message.setObjectName("OfflineLabel")
        layout.addWidget(message)

        self.setLayout(layout)

    def set_icon(self):
        if OFFLINE_ICON_PATH.exists():
            pixmap = QPixmap(str(OFFLINE_ICON_PATH))
            pixmap = pixmap.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.icon_label.setPixmap(pixmap)
        else:
            pixmap = QPixmap(str(MAIN_ICON))
            pixmap = pixmap.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.icon_label.setPixmap(pixmap)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setObjectName("MainWindow")
        self.setWindowTitle("Flatr Store")
        self.resize(1100, 760)
        self.repo_list = []
        self.dark_mode = True
        self.tray_icon = None
        self._setup_ui()
        self._apply_font()
        self._setup_tray_icon()
        self.setStyleSheet(APP_QSS_DARK)

        # Timer for version checks
        self.version_check_timer = QTimer(self)
        self.version_check_timer.setInterval(VERSION_CHECK_INTERVAL)
        self.version_check_timer.timeout.connect(self.check_for_updates)

        # Initial load
        if not is_connected():
            self.show_offline_mode()
        else:
            self.load_cache_then_fetch()
            self.version_check_timer.start()

    def _setup_ui(self):
        central = QWidget()
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setObjectName("TopHeader")
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(15, 5, 15, 5)

        self.title_label = QLabel("FLATR STORE")
        self.title_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        # Theme toggle button
        self.theme_btn = QPushButton()
        self.theme_btn.setFixedSize(30, 30)
        self.theme_btn.setFlat(True)
        self.theme_btn.clicked.connect(self.toggle_theme)
        self.update_theme_icon()
        header_layout.addWidget(self.theme_btn)

        # Search box
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar aplicaciones...")
        self.search.setFixedWidth(300)
        self.search.textChanged.connect(self.on_search_changed)
        header_layout.addWidget(self.search)

        header.setLayout(header_layout)
        self.layout.addWidget(header)

        # Controls row
        controls = QHBoxLayout()
        controls.setContentsMargins(15, 10, 15, 10)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["Todo", "Instaladas", "Con actualizaciones"])
        self.filter_combo.currentIndexChanged.connect(self.on_search_changed)
        controls.addWidget(self.filter_combo)

        self.refresh_btn = QPushButton("Refrescar")
        self.refresh_btn.clicked.connect(self.on_refresh)
        controls.addWidget(self.refresh_btn)

        controls.addStretch()

        self.progress = QProgressBar()
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        self.progress.setFixedWidth(200)
        controls.addWidget(self.progress)

        self.layout.addLayout(controls)

        # Main content area
        self.content_stack = QtWidgets.QStackedWidget()

        # Grid view
        self.grid_view = GridView()
        self.content_stack.addWidget(self.grid_view)

        # Offline mode
        self.offline_mode = OfflineMode()
        self.content_stack.addWidget(self.offline_mode)

        self.layout.addWidget(self.content_stack, 1)

        # Footer
        footer = QFrame()
        footer.setObjectName("TopHeader")
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(15, 5, 15, 5)

        self.status_label = QLabel("Listo")
        self.status_label.setStyleSheet("color: #aaaaaa;")
        footer_layout.addWidget(self.status_label)

        footer_layout.addStretch()

        self.credit_label = QLabel("© 2025 JesusQuijada34")
        self.credit_label.setStyleSheet("color: #aaaaaa;")
        footer_layout.addWidget(self.credit_label)

        footer.setLayout(footer_layout)
        self.layout.addWidget(footer)

        central.setLayout(self.layout)
        self.setCentralWidget(central)

    def _setup_tray_icon(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        self.tray_icon = QSystemTrayIcon(self)

        # Create tray icon menu
        tray_menu = QMenu()

        show_action = tray_menu.addAction("Mostrar")
        show_action.triggered.connect(self.show_normal)

        exit_action = tray_menu.addAction("Salir")
        exit_action.triggered.connect(self.close)

        self.tray_icon.setContextMenu(tray_menu)

        # Set icon
        if OFFLINE_ICON_PATH.exists():
            self.tray_icon.setIcon(QIcon(str(OFFLINE_ICON_PATH)))
        else:
            self.tray_icon.setIcon(QIcon(str(MAIN_ICON)))

        self.tray_icon.show()
        self.tray_icon.activated.connect(self.tray_icon_activated)

    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_normal()

    def show_normal(self):
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        self.activateWindow()

    def closeEvent(self, event):
        if self.tray_icon and self.tray_icon.isVisible():
            self.hide()
            event.ignore()
        else:
            event.accept()

    def _apply_font(self):
        try:
            r = requests.get(ROBOTO_TTF_URL, timeout=8)
            if r.ok and r.content:
                idf = QFontDatabase.addApplicationFontFromData(r.content)
                families = QFontDatabase.applicationFontFamilies(idf)
                if families:
                    QApplication.setFont(QFont(families[0], 10))
        except Exception:
            pass

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.update_theme_icon()
        self.setStyleSheet(APP_QSS_DARK if self.dark_mode else APP_QSS_LIGHT)

    def update_theme_icon(self):
        icon = self.style().standardIcon(
            QStyle.SP_DialogYesButton if self.dark_mode else QStyle.SP_DialogNoButton)
        self.theme_btn.setIcon(icon)
        self.theme_btn.setIconSize(QSize(20, 20))

    def show_offline_mode(self):
        self.content_stack.setCurrentWidget(self.offline_mode)
        self.status_label.setText("Modo offline - Sin conexión a internet")
        self.refresh_btn.setEnabled(False)

    def show_online_mode(self):
        self.content_stack.setCurrentWidget(self.grid_view)
        self.status_label.setText("Conectado a la base!")
        self.refresh_btn.setEnabled(True)

    def load_cache_then_fetch(self):
        cached = cache_load()
        if cached:
            self.repo_list = cached
            self._populate_grid()

        if is_connected():
            self.fetch_thread = RepoFetchThread()
            self.fetch_thread.progress.connect(self.progress.setValue)
            self.fetch_thread.finished_fetch.connect(self.on_repos_loaded)
            self.fetch_thread.error.connect(self.on_fetch_error)
            self.fetch_thread.start()
        else:
            self.show_offline_mode()

    def on_fetch_error(self, msg):
        dlg = StyledMessageBox("Error", f"No se pudo obtener la lista: {msg}", parent=self)
        dlg.exec_()

    def on_repos_loaded(self, results):
        self.repo_list = results
        self._populate_grid()
        self.show_online_mode()

    def check_for_updates(self):
        if not is_connected():
            return

        self.status_label.setText("Comprobando actualizaciones...")

        self.version_check_thread = VersionCheckThread(self.repo_list)
        self.version_check_thread.update_available.connect(self.on_update_available)
        self.version_check_thread.no_updates.connect(self.on_no_updates)
        self.version_check_thread.start()

    def on_update_available(self, info):
        # Update our repo list
        for i, item in enumerate(self.repo_list):
            if item.get("repo") == info.get("repo"):
                self.repo_list[i] = info
                break

        # Show notification
        if self.tray_icon:
            self.tray_icon.showMessage(
                "Actualización disponible",
                f"{info.get('name')} v{info.get('version')} está disponible",
                QSystemTrayIcon.Information,
                5000
            )

        # Update UI if needed
        self._populate_grid()
        self.status_label.setText("Actualizaciones disponibles")

    def on_no_updates(self):
        self.status_label.setText("Todas las aplicaciones están actualizadas")

    def on_refresh(self):
        if not is_connected():
            self.show_offline_mode()
            dlg = StyledMessageBox(
                "Sin conexión",
                "No hay conexión a Internet. No se puede refrescar.",
                parent=self)
            dlg.exec_()
            return

        self.fetch_thread = RepoFetchThread()
        self.fetch_thread.progress.connect(self.progress.setValue)
        self.fetch_thread.finished_fetch.connect(self.on_repos_loaded)
        self.fetch_thread.error.connect(self.on_fetch_error)
        self.fetch_thread.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._populate_grid()

    def _compute_columns(self):
        if self.content_stack.currentWidget() == self.offline_mode:
            return 1

        w = max(220, self.grid_view.scroll.viewport().width())
        cols = max(1, w // 140)  # 140px per column
        return cols

    def _populate_grid(self):
        if self.content_stack.currentWidget() == self.offline_mode:
            return

        filter_text = self.search.text().strip().lower()
        fidx = self.filter_combo.currentIndex()
        filtered = []

        for info in self.repo_list:
            # Apply filters
            name = (info.get("name") or "").lower()
            app = (info.get("app") or "").lower()
            pub = (info.get("publisher") or "").lower()
            repo = (info.get("repo") or "").lower()

            if filter_text:
                if (filter_text not in name and
                    filter_text not in app and
                    filter_text not in pub and
                    filter_text not in repo):
                    continue

            if fidx == 1:  # Installed
                if not info.get("installed_version"):
                    continue

            if fidx == 2:  # Updates available
                if not info.get("update_available"):
                    continue

            filtered.append(info)

        # Sort by name
        filtered.sort(key=lambda x: (x.get("name") or x.get("app") or x.get("repo")).lower())

        cols = self._compute_columns()
        self.grid_view.populate(filtered, cols)

    def on_search_changed(self, _=None):
        self._populate_grid()

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_QSS_DARK)

    """
    # Set dark palette for better dark mode support
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(45, 45, 45))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(35, 35, 35))
    palette.setColor(QPalette.AlternateBase, QColor(45, 45, 45))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(45, 45, 45))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)
    """

    w = MainWindow()
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
