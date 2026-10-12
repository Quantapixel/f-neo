#!/usr/bin/env python3
"""type-box - paste text into a box, then have it typed at your cursor."""

from __future__ import annotations

import os
import subprocess
import sys
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TYPEHERE = os.path.join(HERE, "typehere")
CACHE_DIR = os.path.join(GLib.get_user_cache_dir(), "type-here")
LAST_TEXT = os.path.join(CACHE_DIR, "last.txt")


class TypeBox(Gtk.ApplicationWindow):
    def __init__(self, app: Gtk.Application) -> None:
        super().__init__(application=app, title="Type Here")
        self.set_default_size(960, 380)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        for edge in ("top", "bottom", "start", "end"):
            getattr(root, f"set_margin_{edge}")(12)
        self.set_child(root)

        self.view = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR)
        self.view.set_monospace(True)
        self.view.get_buffer().connect("changed", self.on_changed)

        scroller = Gtk.ScrolledWindow()
        scroller.set_child(self.view)
        scroller.set_vexpand(True)
        root.append(scroller)

        footer = Gtk.Box(spacing=8)
        root.append(footer)

        footer.append(Gtk.Label(label="Delay"))
        self.delay = Gtk.SpinButton.new_with_range(0, 10, 0.5)
        self.delay.set_value(3)
        self.delay.set_tooltip_text(
            "Seconds to wait after this window hides, so you can click where the text should land."
        )
        footer.append(self.delay)

        self.paste_mode = Gtk.CheckButton(label="Paste (Ctrl+V)")
        self.paste_mode.set_tooltip_text(
            "Use clipboard paste instead of key events. Handles emoji and accents; "
            "briefly uses your clipboard."
        )
        footer.append(self.paste_mode)

        self.shift_enter = Gtk.CheckButton(label="No auto-indent (Shift+Enter)")
        self.shift_enter.set_tooltip_text(
            "Type newlines as Shift+Enter, so code editors do not add their own "
            "indentation on top of the spaces that are typed."
        )
        footer.append(self.shift_enter)

        self.auto_code = Gtk.CheckButton(label="Auto-code indent (Shift+Enter)")
        self.auto_code.set_tooltip_text(
            "Detect code and type newlines as Shift+Enter, so the editor does "
            "not add its own indentation on top of the typed spaces."
        )
        self.auto_code.set_active(True)
        footer.append(self.auto_code)

        self.backspace_indent = Gtk.CheckButton(label="Backspace correction")
        self.backspace_indent.set_tooltip_text(
            "Instead of Shift+Enter, press Backspace after each newline to "
            "remove auto-indent. Only use this when the target editor reliably "
            "auto-indents; otherwise it can delete the newline."
        )
        footer.append(self.backspace_indent)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        footer.append(spacer)

        self.button = Gtk.Button(label="Type at cursor")
        self.button.add_css_class("suggested-action")
        self.button.connect("clicked", self.on_type)
        footer.append(self.button)

        self.status = Gtk.Label(label="Paste or type text, then press Enter.", xalign=0)
        self.status.add_css_class("dim-label")
        root.append(self.status)

        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self.on_key)
        self.add_controller(keys)

        self.load_last()

    def buffer_text(self) -> str:
        buffer = self.view.get_buffer()
        return buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)

    def set_buffer_text(self, text: str) -> None:
        self.view.get_buffer().set_text(text)

    def on_changed(self, _buffer: Gtk.TextBuffer) -> None:
        if self.status.get_label().startswith("Typing in"):
            self.status.set_text("")

    def on_key(self, _controller, keyval: int, _keycode: int, state: Gdk.ModifierType) -> bool:
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter) and not state & Gdk.ModifierType.SHIFT_MASK:
            self.on_type(None)
            return True
        return False

    def on_type(self, _widget) -> None:
        text = self.buffer_text()
        if not text.strip():
            self.status.set_text("Nothing to type.")
            return

        self.save_last(text)
        delay = self.delay.get_value()
        self.status.set_text(f"Typing in {delay:.1f}s - click where you want it...")

        # Hide ourselves: focus falls back to the window you were in.
        self.minimize()

        def work() -> None:
            command = [TYPEHERE, "--stdin", "--wait", str(delay)]
            if self.paste_mode.get_active():
                command.append("--paste")
            elif self.backspace_indent.get_active():
                command.append("--backspace-indent")
            elif self.shift_enter.get_active():
                command.append("--shift-enter")
            elif self.auto_code.get_active():
                command.append("--auto-code")
            else:
                command.append("--no-auto-code")
            result = subprocess.run(command, input=text.encode("utf-8"), capture_output=True)
            error = result.stderr.decode("utf-8", "replace").strip()
            GLib.idle_add(self.report, result.returncode, error)

        threading.Thread(target=work, daemon=True).start()

    def report(self, returncode: int, error: str) -> bool:
        if returncode == 0:
            self.status.set_text("Done.")
        else:
            self.status.set_text(error or "Typehere failed.")
            self.present()  # surface the error instead of failing silently
        return GLib.SOURCE_REMOVE

    def load_last(self) -> None:
        try:
            with open(LAST_TEXT, encoding="utf-8") as handle:
                self.set_buffer_text(handle.read())
        except OSError:
            pass

    def save_last(self, text: str) -> None:
        try:
            os.makedirs(CACHE_DIR, exist_ok=True)
            with open(LAST_TEXT, "w", encoding="utf-8") as handle:
                handle.write(text)
        except OSError:
            pass


class TypeBoxApp(Gtk.Application):
    def __init__(self) -> None:
        super().__init__(application_id="dev.local.TypeHere")

    def do_activate(self) -> None:
        if not os.access(TYPEHERE, os.X_OK):
            print(f"type-box: {TYPEHERE} is missing or not executable", file=sys.stderr)
            raise SystemExit(1)
        TypeBox(self).present()


if __name__ == "__main__":
    raise SystemExit(TypeBoxApp().run(sys.argv))
