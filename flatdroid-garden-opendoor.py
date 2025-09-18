"""
main.py

Versión Kivy de la página "Proyectos de Jesús Quijada".
- Descarga lista de repos (rawListURL) desde GitHub.
- Muestra tarjetas con imagen, título, categoría y rating.
- Botones: Vista previa (abre demo si existe) y Descargar (descarga zip del repo).
- Banner de cumpleaños con cuenta regresiva y animación "confetti" simple.
- Todo embebido en un string KV (sin archivo .kv separado).

Requisitos:
    pip install kivy requests

Notas:
 - En Android/Termux puede requerir permisos y ajustes adicionales para guardar archivos.
 - Las descargas usan threads para no bloquear la UI.
"""

from kivy.app import App
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.properties import StringProperty, NumericProperty, BooleanProperty, ListProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import AsyncImage
from kivy.clock import mainthread, Clock
from kivy.animation import Animation
from kivy.graphics import Color, Rectangle, Ellipse

import threading
import requests
import webbrowser
import os
import time
from datetime import datetime

# Opcional (útil en desktop)
Window.size = (420, 800)

KV = f"""
#:import dp kivy.metrics.dp

<Header@BoxLayout>:
    size_hint_y: None
    height: dp(64)
    padding: dp(10)
    spacing: dp(10)
    orientation: 'horizontal'
    canvas.before:
        Color:
            rgba: 0.14, 0.16, 0.18, 1
        Rectangle:
            pos: self.pos
            size: self.size
    Label:
        text: "Proyectos de Jesús Quijada"
        color: 1,1,1,1
        bold: True
        font_size: '18sp'
        size_hint_x: 0.55
    BoxLayout:
        orientation: 'horizontal'
        size_hint_x: 0.45
        spacing: dp(6)
        TextInput:
            id: search_input
            hint_text: "Buscar proyectos..."
            size_hint_x: 0.75
            multiline: False
        Button:
            text: "Buscar"
            size_hint_x: 0.25
            on_release: app.on_search(search_input.text)

<Card@BoxLayout>:
    orientation: 'vertical'
    size_hint_y: None
    height: dp(240)
    padding: dp(0)
    spacing: dp(0)
    canvas.before:
        Color:
            rgba: app.card_bg_color
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [8]
        Color:
            rgba: app.card_border_color
        Line:
            rounded_rectangle: (*self.pos, *self.size, 8)
            width: 1
    BoxLayout:
        size_hint_y: 0.6
        pos_hint: {'top': 1}
        AsyncImage:
            id: preview_img
            source: root.splash if hasattr(root, 'splash') and root.splash else root.icon
            allow_stretch: True
            keep_ratio: False
            on_error: self.source = root.icon if root.icon else ''
    BoxLayout:
        orientation: 'vertical'
        padding: dp(10)
        spacing: dp(6)
        Label:
            text: root.title
            bold: True
            color: app.accent_color
            size_hint_y: None
            height: self.texture_size[1]
            text_size: self.width, None
        Label:
            text: root.category
            font_size: '12sp'
            color: app.muted_color
            size_hint_y: None
            height: self.texture_size[1]
        BoxLayout:
            size_hint_y: None
            height: dp(36)
            spacing: dp(8)
            Button:
                text: "Vista previa"
                on_release: app.on_preview(root.preview_url)
                disabled: not root.preview_url
            Button:
                text: "Descargar"
                on_release: app.on_download(root.repo_name, root.repo_zip)
"""

# Main KV layout
APP_KV = """
BoxLayout:
    orientation: "vertical"

    Header:

    ScrollView:
        id: main_scroll
        do_scroll_x: False
        GridLayout:
            id: main_grid
            cols: 1
            size_hint_y: None
            height: self.minimum_height
            padding: dp(12)
            spacing: dp(12)

            # Loading area
            BoxLayout:
                id: loading_box
                orientation: 'vertical'
                size_hint_y: None
                height: dp(160)
                padding: dp(12)
                spacing: dp(8)
                canvas.before:
                    Color:
                        rgba: 1,1,1,1
                    Rectangle:
                        pos: self.pos
                        size: self.size
                Label:
                    id: loading_label
                    text: "Cargando proyectos..."
                    size_hint_y: None
                    height: self.texture_size[1]

            Label:
                text: "🔮 Recomendados para ti"
                font_size: '20sp'
                bold: True
                size_hint_y: None
                height: self.texture_size[1]

            GridLayout:
                id: featured_grid
                cols: 2
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(10)

            Label:
                text: "🏆 Listas de éxitos"
                font_size: '20sp'
                bold: True
                size_hint_y: None
                height: self.texture_size[1]

            GridLayout:
                id: ranking_grid
                cols: 1
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(8)

            Label:
                text: "🎮 Todos los proyectos"
                font_size: '20sp'
                bold: True
                size_hint_y: None
                height: self.texture_size[1]

            GridLayout:
                id: all_apps_grid
                cols: 1
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(12)

            # Footer spacer
            Widget:
                size_hint_y: None
                height: dp(24)

    # Birthday/celebration overlay (initially hidden)
    FloatLayout:
        id: overlay
        size_hint: 1, 1

        BoxLayout:
            id: birthday_box
            orientation: 'horizontal'
            size_hint: None, None
            size: dp(360), dp(80)
            pos: root.width - self.width - dp(16), dp(16)
            padding: dp(10)
            spacing: dp(10)
            canvas.before:
                Color:
                    rgba: 1, 0.6, 0.2, 1
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [12]
            Image:
                id: gift_img
                source: ''
                size_hint: None, None
                size: dp(48), dp(48)
            BoxLayout:
                orientation: 'vertical'
                Label:
                    id: countdown_text
                    text: "Faltan 00:00:00"
                    color: 1,1,1,1
                    bold: True
                Label:
                    id: countdown_detail
                    text: "Cuenta regresiva"
                    color: 1,1,1,1
            Button:
                text: "Cerrar"
                size_hint_x: None
                width: dp(64)
                on_release: app.hide_birthday()

"""

# Combine KV
FULL_KV = KV + "\n" + APP_KV

# App-level colors & small helpers
class ProjectCard(BoxLayout):
    title = StringProperty("Título")
    category = StringProperty("Aplicación")
    rating = NumericProperty(4.0)
    splash = StringProperty("")       # splash image url
    icon = StringProperty("")         # icon url
    preview_url = StringProperty("")  # live demo
    repo_name = StringProperty("")    # repo short name
    repo_zip = StringProperty("")     # zip download url


class ProjectsApp(App):
    # Colors (as rgba tuples)
    accent_color = ListProperty([0.04, 0.41, 0.86, 1])  # azul
    muted_color = ListProperty([0.45, 0.49, 0.52, 1])
    card_bg_color = ListProperty([1, 1, 1, 1])
    card_border_color = ListProperty([0.86, 0.87, 0.88, 1])

    # URLs
    rawListURL = "https://raw.githubusercontent.com/JesusQuijada34/catalog/refs/heads/main/repo.list"

    def build(self):
        Builder.load_string(FULL_KV)
        self.root = Builder.load_string("BoxLayout:")  # dummy to have root var
        # Actually build the layout from the KV top-level (we will create a dynamic root)
        main = Builder.template("BoxLayout")
        # Instead of templates, load the big root UI:
        self.interface = Builder.load_string(APP_KV)
        # store main containers
        self.main_grid = self.interface.ids.main_grid
        self.featured_grid = self.interface.ids.featured_grid
        self.all_apps_grid = self.interface.ids.all_apps_grid
        self.loading_label = self.interface.ids.loading_label
        self.ranking_grid = self.interface.ids.ranking_grid
        self.overlay = self.interface.ids.overlay
        self.birthday_box = self.interface.ids.birthday_box
        self.countdown_text = self.interface.ids.countdown_text
        self.countdown_detail = self.interface.ids.countdown_detail

        # Hide birthday initially
        self.birthday_box.opacity = 0
        self.birthday_box.disabled = True

        # Start background load
        threading.Thread(target=self.load_repos, daemon=True).start()
        # Start birthday init
        Clock.schedule_once(lambda dt: self.init_birthday(), 1)

        return self.interface

    def on_search(self, text):
        text = text.strip().lower()
        if not text:
            # reload all
            self.populate_all(self.all_repos)
        else:
            filt = [r for r in self.all_repos if text in r['display_name'].lower() or text in r.get('category','').lower()]
            self.populate_all(filt)

    # ---------- Networking & parsing ----------
    def load_repos(self):
        # Download repo list
        self._set_loading("Descargando lista...")
        try:
            r = requests.get(self.rawListURL, timeout=20)
            r.raise_for_status()
            repo_text = r.text
            repo_names = [s.strip() for s in repo_text.split(',') if s.strip()]
            if not repo_names:
                self._set_loading("Lista vacía o formato inesperado.")
                return
        except Exception as e:
            self._set_loading(f"Error al bajar la lista: {e}")
            return

        self._set_loading(f"Cargando {len(repo_names)} proyectos...")
        # fetch details in threads (limited concurrency)
        details = []
        lock = threading.Lock()
        finished = 0

        def worker(name):
            nonlocal finished
            info = self.get_repo_details(name)
            with lock:
                details.append(info)
                finished += 1
                self._set_loading(f"Cargando proyectos... ({finished}/{len(repo_names)})")

        threads = []
        for nm in repo_names:
            t = threading.Thread(target=worker, args=(nm,), daemon=True)
            t.start()
            threads.append(t)
            # a tiny throttle
            time.sleep(0.05)

        # wait for threads
        for t in threads:
            t.join(timeout=30)

        # Sort by rating desc
        details_sorted = sorted(details, key=lambda x: float(x.get('rating', 0) or 0), reverse=True)
        self.all_repos = details_sorted

        # update UI on main thread
        self._set_loading("Renderizando UI...")
        Clock.schedule_once(lambda dt: self.populate_ui(details_sorted), 0)

    def get_repo_details(self, repo_name):
        # Try to fetch details.xml (best effort), check splash and demo
        base_raw = f"https://raw.githubusercontent.com/JesusQuijada34/{repo_name}/main"
        details_url = f"{base_raw}/details.xml"
        icon_url = f"{base_raw}/app/app-icon.ico"
        zip_url = f"https://github.com/JesusQuijada34/{repo_name}/archive/refs/heads/main.zip"
        splash_url = f"{base_raw}/assets/splash.png"
        preview = None

        rating = "4.0"
        display_name = repo_name
        category = "Aplicación"

        # details.xml
        try:
            r = requests.get(details_url, timeout=8)
            if r.ok and "<" in r.text:
                # quick parse for <name>, <category>, <rate>
                txt = r.text
                import re
                m_name = re.search(r"<name>(.*?)</name>", txt, re.S|re.I)
                m_cat = re.search(r"<category>(.*?)</category>", txt, re.S|re.I)
                m_rate = re.search(r"<rate>(.*?)</rate>", txt, re.S|re.I)
                if m_name:
                    display_name = m_name.group(1).strip()
                if m_cat:
                    category = m_cat.group(1).strip()
                if m_rate:
                    rating = m_rate.group(1).strip()
        except Exception:
            pass

        # check splash
        try:
            h = requests.head(splash_url, timeout=6)
            if not h.ok:
                splash_url = ""
        except Exception:
            splash_url = ""

        # check demo on gh-pages
        try:
            demo = f"https://jesusquijada34.github.io/{repo_name}"
            h2 = requests.head(demo, timeout=6, allow_redirects=True)
            if h2.ok or str(h2.status_code).startswith('3'):
                preview = demo
        except Exception:
            preview = None

        return {
            "repo_name": repo_name,
            "display_name": display_name,
            "category": category,
            "rating": rating,
            "icon": icon_url,
            "splash": splash_url,
            "preview": preview,
            "repo_zip": zip_url
        }

    # ---------- UI population ----------
    @mainthread
    def _set_loading(self, text):
        try:
            self.loading_label.text = text
        except Exception:
            pass

    def populate_ui(self, repos):
        # Clear loading and populate featured / all
        self.loading_label.text = "Proyectos cargados"
        # featured: first 6
        featured = repos[:6]
        self.featured_grid.clear_widgets()
        for r in featured:
            card = ProjectCard()
            card.title = r['display_name']
            card.category = r['category']
            card.rating = float(r.get('rating', 4.0) or 4.0)
            card.icon = r.get('icon','')
            card.splash = r.get('splash','')
            card.preview_url = r.get('preview') or ""
            card.repo_name = r['repo_name']
            card.repo_zip = r.get('repo_zip','')
            self.featured_grid.add_widget(card)

        # ranking: simple list of top 6 broken into rows
        self.ranking_grid.clear_widgets()
        top_slice = repos[:9]
        for i in range(0, min(len(top_slice), 9), 3):
            row = BoxLayout(size_hint_y=None, height=dp(80), spacing=dp(8))
            for j in range(3):
                idx = i + j
                if idx < len(top_slice):
                    info = top_slice[idx]
                    b = ButtonLikeRanking(text=f"{info['display_name']}\\n{info['category']}")
                    # open repo on click
                    b.repo = info
                    b.bind(on_release=self._on_open_repo_short)
                    row.add_widget(b)
                else:
                    row.add_widget(Label())
            self.ranking_grid.add_widget(row)

        # all apps
        self.populate_all(repos)

    def populate_all(self, repos):
        self.all_apps_grid.clear_widgets()
        for r in repos:
            card = ProjectCard()
            card.title = r['display_name']
            card.category = r['category']
            card.rating = float(r.get('rating', 4.0) or 4.0)
            card.icon = r.get('icon','')
            card.splash = r.get('splash','')
            card.preview_url = r.get('preview') or ""
            card.repo_name = r['repo_name']
            card.repo_zip = r.get('repo_zip','')
            self.all_apps_grid.add_widget(card)

    # ---------- Actions ----------
    def on_preview(self, url):
        if not url:
            self._popup("No hay demo disponible", "Este proyecto no tiene vista previa.")
            return
        webbrowser.open(url)

    def on_download(self, repo_name, zip_url):
        if not zip_url:
            self._popup("Error", "URL de descarga no encontrada.")
            return
        # Ask: start download thread
        threading.Thread(target=self._download_thread, args=(repo_name, zip_url), daemon=True).start()
        self._popup("Descarga iniciada", f"Descargando {repo_name} ...")

    def _download_thread(self, repo_name, url):
        # Create downloads dir
        try:
            dl_dir = os.path.join(os.getcwd(), "downloads")
            os.makedirs(dl_dir, exist_ok=True)
            local_fname = os.path.join(dl_dir, f"{repo_name}.zip")
            with requests.get(url, stream=True, timeout=15) as r:
                r.raise_for_status()
                total = int(r.headers.get('content-length', 0))
                chunk_size = 8192
                downloaded = 0
                with open(local_fname, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                # finished
            self._popup(f"Descarga completada", f"Guardado en: {local_fname}")
        except Exception as e:
            self._popup("Error en descarga", str(e))

    # ---------- Small popups ----------
    @mainthread
    def _popup(self, title, message):
        p = Popup(title=title, content=Label(text=message), size_hint=(0.8, 0.4))
        p.open()

    # ---------- Ranking button handler ----------
    def _on_open_repo_short(self, widget):
        repo = getattr(widget, 'repo', None)
        if repo:
            url = f"https://github.com/JesusQuijada34/{repo['repo_name']}"
            webbrowser.open(url)

    # ---------- Birthday / countdown ----------
    def init_birthday(self):
        # birthday original: 1 Sept 2009
        birthday = datetime(2009, 9, 1)
        now = datetime.now()
        # if current month is Aug or Sep show banner
        if now.month in (8, 9):
            # show banner
            self.birthday_box.opacity = 1
            self.birthday_box.disabled = False
            # animate subtle pulsing
            anim = Animation(scale=1.02, duration=1) + Animation(scale=1.0, duration=1)
            anim.repeat = True
            # update countdown per second
            Clock.schedule_interval(lambda dt: self.update_countdown(birthday), 0.5)
            # simple confetti scheduled occasionally
            Clock.schedule_interval(lambda dt: self._confetti_once(), 4)

    @mainthread
    def update_countdown(self, birthday):
        now = datetime.now()
        # next upcoming birthday (this year or next)
        target = datetime(now.year, birthday.month, birthday.day)
        if target <= now:
            target = datetime(now.year + 1, birthday.month, birthday.day)
        delta = target - now
        days = delta.days
        hours, rem = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(rem, 60)
        self.countdown_text.text = f"Faltan {days:02d}d {hours:02d}h:{minutes:02d}m"
        self.countdown_detail.text = f"{seconds:02d}s restantes"

    def hide_birthday(self):
        # fade out
        Animation(opacity=0, d=0.4).start(self.birthday_box)
        self.birthday_box.disabled = True

    def _confetti_once(self):
        # Simple confetti: draw colored ellipses that fall and fade
        canvas = self.interface.canvas
        colors = [
            (1, 0, 0, 1), (0, 1, 0, 1), (0, 0, 1, 1),
            (1, 1, 0, 1), (1, 0, 1, 1), (0, 1, 1, 1)
        ]
        # spawn a few confetti pieces in overlay
        for i in range(6):
            x = dp(20 + i*60)
            y = self.interface.height + dp(10)
            w = dp(8 + (i % 3)*4)
            h = w
            col = colors[i % len(colors)]
            instrs = []
            with self.interface.canvas:
                c = Color(*col)
                e = Ellipse(pos=(x, y), size=(w, h))
                instrs.append((c, e))
            # animate down
            anim = Animation(pos=(x, -dp(40)), size=(w, h), duration=3 + i*0.2, t='out_quad') + Animation(a=0, d=0.1)
            # bind update
            def _update(anim, widget, instr=e):
                pass
            # schedule removal
            def _remove(dt, instr_pair=(c, e)):
                try:
                    self.interface.canvas.remove(instr_pair[1])
                    self.interface.canvas.remove(instr_pair[0])
                except Exception:
                    pass
            Clock.schedule_once(_remove, 4.0)

if __name__ == "__main__":
    # helper widgets referenced in code
    from kivy.uix.button import Button
    class ButtonLikeRanking(Button):
        repo = None

    # register ProjectCard rule so KV can instantiate <Card> as ProjectCard
    from kivy.factory import Factory
    Factory.register('ProjectCard', cls=ProjectCard)

    ProjectsApp().run()
