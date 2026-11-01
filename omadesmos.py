#!/usr/bin/env python3
"""Omadesmos: the Desmos calculators in a locked-down Omarchy window.

Runs the real Desmos site, so every calculator works in full: graphing, 3D,
geometry, scientific, four-function and matrix. There is no address bar, and
pages outside Desmos are blocked, so this app can't be used as a web browser.
"""

import json
import os
import sys
from urllib.parse import urlparse

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
gi.require_version("WebKit2", "4.1")
from gi.repository import Gdk, Gio, GLib, Gtk, WebKit2  # noqa: E402

APP_ID = "org.pacificachristian.OmaDesmos"
SYSTEM_CONFIG = "/etc/omadesmos/config.json"
BUNDLED_CONFIG = os.path.join(os.path.dirname(os.path.realpath(__file__)), "config.json")
DATA_DIR = os.path.join(GLib.get_user_data_dir(), "omadesmos")
CACHE_DIR = os.path.join(GLib.get_user_cache_dir(), "omadesmos")
LAST_MODE = os.path.join(DATA_DIR, "last-mode")

# Header switcher: (label, path on desmos_url). The first is the default.
MODES = [
    ("Graphing", "calculator"),
    ("3D", "3d"),
    ("Geometry", "geometry"),
    ("Scientific", "scientific"),
    ("Basic", "fourfunction"),
    ("Matrix", "matrix"),
]
LABELS = {slug: label for label, slug in MODES}


def load_config():
    # The admin-owned system config always wins. Students can't edit it, and
    # there is no env var or flag override that could point the app elsewhere.
    path = SYSTEM_CONFIG if os.path.exists(SYSTEM_CONFIG) else BUNDLED_CONFIG
    with open(path) as f:
        cfg = json.load(f)
    desmos_host = urlparse(cfg["desmos_url"]).hostname
    cfg["allowed_hosts"] = [desmos_host] + cfg.get("allowed_hosts", [])
    return cfg


def host_matches(uri, hosts):
    host = urlparse(uri).hostname or ""
    return any(host == h or host.endswith("." + h) for h in hosts)


def is_web(uri):
    return urlparse(uri).scheme in ("http", "https")


def content_filter_rules(hosts):
    # WebKit content-blocker rules: block every http(s) page or frame document,
    # then let the listed hosts through. Scripts, images and styles from other
    # hosts (CDNs) still load. Pages only open where we allow.
    rules = [{"trigger": {"url-filter": "^https?://", "resource-type": ["document"]},
              "action": {"type": "block"}},
             {"trigger": {"url-filter": "^file:"}, "action": {"type": "block"}}]
    for h in hosts:
        pattern = "^https?://([^/]*\\.)?" + h.replace(".", "\\.") + "[:/]"
        rules.append({"trigger": {"url-filter": pattern}, "action": {"type": "ignore-previous-rules"}})
    return json.dumps(rules)


def read_last_mode():
    try:
        with open(LAST_MODE) as f:
            slug = f.read().strip()
    except OSError:
        return MODES[0][1]
    return slug if slug in LABELS else MODES[0][1]


def save_last_mode(slug):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(LAST_MODE, "w") as f:
            f.write(slug)
    except OSError:
        pass


class DesmosWindow(Gtk.ApplicationWindow):
    """Main window: one view per calculator, each kept loaded so switching never loses
    work. A popup (sign-in, help) is a window with a single view and no switcher."""

    updating = False  # set while update_header syncs the toggle buttons

    def __init__(self, app, related=None):
        super().__init__(application=app, title="Desmos")
        self.app = app
        self.set_default_size(1280, 860)
        self.set_icon_name("omadesmos")
        self.views = {}
        self.stack = Gtk.Stack()
        self.popup = related is not None
        if self.popup:
            view = self.new_view(related)
            view.show()  # a Gtk.Stack has no visible child until it's shown
            self.stack.add(view)
        self.connect("key-press-event", self.on_key)
        self.build_ui()

    @property
    def view(self):
        return self.stack.get_visible_child()

    def new_view(self, related=None):
        if related:
            view = WebKit2.WebView.new_with_related_view(related)
        else:
            view = WebKit2.WebView(web_context=self.app.context, user_content_manager=self.app.content)
            settings = view.get_settings()
            settings.set_enable_developer_extras(False)
            settings.set_enable_back_forward_navigation_gestures(True)
            settings.set_enable_write_console_messages_to_stdout(False)
            # The 3D calculator draws with WebGL inside a worker (OffscreenCanvas). WebKitGTK
            # only allows that with WebGL moved into the GPU process; without both flags
            # Desmos shows "This browser isn't configured" instead of the 3D graph.
            settings.set_enable_webgl(True)
            features = WebKit2.Settings.get_all_features()
            for i in range(features.get_length()):
                feature = features.get(i)
                if feature.get_identifier() in ("AllowWebGLInWorkers", "UseGPUProcessForWebGL"):
                    settings.set_feature_enabled(feature, True)

        view.connect("decide-policy", self.on_decide_policy)
        view.connect("create", self.on_create)
        view.connect("permission-request", lambda v, r: r.deny() or True)
        view.connect("load-changed", lambda *a: self.update_header())
        view.connect("notify::title", lambda *a: self.update_header())
        view.connect("web-process-terminated", lambda v, r: v.reload())
        if self.popup:
            view.connect("ready-to-show", lambda v: self.show_all())
            view.connect("close", lambda v: self.destroy())
        return view

    def build_ui(self):
        header = Gtk.HeaderBar(show_close_button=True)
        self.back = Gtk.Button.new_from_icon_name("go-previous-symbolic", Gtk.IconSize.BUTTON)
        self.back.set_tooltip_text("Back (Alt+Left)")
        self.back.connect("clicked", lambda b: self.view.go_back())
        header.pack_start(self.back)

        # One linked row of calculator buttons; the current one is pressed in.
        self.mode_buttons = {}
        if not self.popup:
            switcher = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            switcher.get_style_context().add_class("linked")
            for i, (label, slug) in enumerate(MODES, 1):
                b = Gtk.ToggleButton(label=label)
                b.set_tooltip_text(f"{label} calculator (Ctrl+{i})")
                b.connect("clicked", self.on_mode_clicked, slug)
                switcher.pack_start(b, False, False, 0)
                self.mode_buttons[slug] = b
            header.set_custom_title(switcher)
        self.set_titlebar(header)
        self.header = header

        self.notice = Gtk.InfoBar(message_type=Gtk.MessageType.INFO, show_close_button=True, revealed=False)
        self.notice_label = Gtk.Label(xalign=0)
        self.notice.get_content_area().add(self.notice_label)
        self.notice.connect("response", lambda bar, r: bar.set_revealed(False))

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.pack_start(self.notice, False, False, 0)
        box.pack_start(self.stack, True, True, 0)
        self.add(box)

    def show_mode(self, slug):
        # Each calculator loads the first time it's opened, then stays in memory.
        if slug not in self.views:
            view = self.new_view()
            view.show()
            self.views[slug] = view
            self.stack.add_named(view, slug)
            view.load_uri(self.app.cfg["desmos_url"].rstrip("/") + "/" + slug)
        self.stack.set_visible_child_name(slug)
        save_last_mode(slug)
        self.update_header()
        self.view.grab_focus()

    def on_mode_clicked(self, button, slug):
        if not self.updating:
            self.show_mode(slug)

    def update_header(self):
        view = self.view
        if not view:
            return
        self.back.set_sensitive(view.can_go_back())
        if self.popup:
            self.header.set_title(view.get_title() or "Desmos")
            return
        current = self.stack.get_visible_child_name()
        self.updating = True
        for slug, b in self.mode_buttons.items():
            b.set_active(slug == current)
        self.updating = False
        self.set_title("Desmos " + LABELS[current])

    def show_notice(self, text):
        self.notice_label.set_text(text)
        self.notice.set_revealed(True)
        GLib.timeout_add_seconds(5, lambda: self.notice.set_revealed(False) and False)

    def blocked(self, uri):
        host = urlparse(uri).hostname or uri
        self.show_notice(f"{host} isn't available in Desmos. Ask your teacher if you need it.")

    def on_decide_policy(self, view, decision, kind):
        allowed = self.app.cfg["allowed_hosts"]
        if kind == WebKit2.PolicyDecisionType.NAVIGATION_ACTION:
            action = decision.get_navigation_action()
            uri = action.get_request().get_uri()
            if is_web(uri) and not host_matches(uri, allowed):
                decision.ignore()
                if action.is_user_gesture():
                    self.blocked(uri)
                return True
        elif kind == WebKit2.PolicyDecisionType.RESPONSE:
            uri = decision.get_request().get_uri()
            if decision.is_main_frame_main_resource() and is_web(uri) and not host_matches(uri, allowed):
                decision.ignore()
                self.blocked(uri)
                return True
            if not decision.is_mime_type_supported():
                decision.download()
                return True
        return False

    def on_create(self, view, action):
        uri = action.get_request().get_uri()
        if uri and is_web(uri) and not host_matches(uri, self.app.cfg["allowed_hosts"]):
            self.blocked(uri)
            return None
        # New tabs and sign-in popups open as another locked-down window.
        return DesmosWindow(self.app, related=view).view

    def on_key(self, win, event):
        ctrl = event.state & Gdk.ModifierType.CONTROL_MASK
        alt = event.state & Gdk.ModifierType.MOD1_MASK
        key = Gdk.keyval_name(event.keyval)
        v = self.view
        actions = {
            (alt, "Left"): v.go_back,
            (alt, "Right"): v.go_forward,
            (ctrl, "r"): v.reload,
            (True, "F5"): v.reload,
            (ctrl, "equal"): lambda: v.set_zoom_level(v.get_zoom_level() + 0.1),
            (ctrl, "plus"): lambda: v.set_zoom_level(v.get_zoom_level() + 0.1),
            (ctrl, "minus"): lambda: v.set_zoom_level(max(0.3, v.get_zoom_level() - 0.1)),
            (ctrl, "0"): lambda: v.set_zoom_level(1.0),
            (ctrl, "w"): self.close,
        }
        for i, (_, slug) in enumerate(MODES, 1):
            if not self.popup:
                actions[(ctrl, str(i))] = lambda s=slug: self.show_mode(s)
        for (mod, name), fn in actions.items():
            if mod and key == name:
                fn()
                return True
        return False


class OmaDesmos(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.cfg = None

    def do_startup(self):
        Gtk.Application.do_startup(self)
        self.cfg = load_config()

        manager = WebKit2.WebsiteDataManager(base_data_directory=DATA_DIR, base_cache_directory=CACHE_DIR)
        self.context = WebKit2.WebContext.new_with_website_data_manager(manager)
        self.context.get_cookie_manager().set_persistent_storage(
            os.path.join(DATA_DIR, "cookies.sqlite"), WebKit2.CookiePersistentStorage.SQLITE)
        self.context.connect("download-started", self.on_download)
        self.content = WebKit2.UserContentManager()

    def do_activate(self):
        if self.get_windows():
            self.get_windows()[0].present()
            return
        win = DesmosWindow(self)
        win.show_all()
        # Nothing loads until the site blocker is in place: fail closed.
        store = WebKit2.UserContentFilterStore.new(os.path.join(CACHE_DIR, "filters"))
        rules = GLib.Bytes.new(content_filter_rules(self.cfg["allowed_hosts"]).encode())
        store.save("allowlist", rules, None, self.on_filter_ready, win)

    def on_filter_ready(self, store, result, win):
        try:
            self.content.add_filter(store.save_finish(result))
        except GLib.Error as e:
            win.show_notice(f"Couldn't start safely ({e.message}). Please tell your teacher.")
            return
        win.show_mode(read_last_mode())

    def on_download(self, context, download):
        # Desmos image and graph exports land in ~/Downloads, never overwriting a file.
        def destination(dl, name):
            folder = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD) or GLib.get_home_dir()
            base, ext = os.path.splitext(os.path.basename(name) or "desmos")
            path, n = os.path.join(folder, base + ext), 1
            while os.path.exists(path):
                path, n = os.path.join(folder, f"{base} ({n}){ext}"), n + 1
            dl.set_destination(GLib.filename_to_uri(path))
            return True

        def finished(dl):
            path = GLib.filename_from_uri(dl.get_destination())[0]
            for win in self.get_windows():
                win.show_notice(f"Saved to {path}")
                break

        download.connect("decide-destination", destination)
        download.connect("finished", finished)


if __name__ == "__main__":
    GLib.set_prgname(APP_ID)  # Wayland app id, matches the .desktop file
    sys.exit(OmaDesmos().run(sys.argv))
