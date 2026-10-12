# type-at-cursor

Type text wherever your cursor is - a paste box you can paste into, then have it
typed out into the app you were actually working in.

## How it works

The hard part is not the box, it is the "type into any app" part.

On Wayland a normal program cannot move your focus or send keystrokes to another
window: that was deliberately removed, which is why `xdotool` is useless here.
There are only two doors left:

1. **A compositor protocol** - the Wayland virtual-keyboard protocol (`wtype`) or
   the XDG RemoteDesktop portal. Clean, but each has its own consent flow.
2. **The kernel's uinput layer** - create a virtual keyboard device at
   `/dev/uinput`. The kernel injects its events as if it were real hardware, so
   they arrive *below* the compositor and land in whatever has focus. No window
   logic, no compositor cooperation, works in Wayland, XWayland and X11 alike.

This tool takes door 2 via `ydotool`. Your system already has everything needed:
the `uinput` module is loaded and `/dev/uinput` carries an ACL giving your user
`rw`. So there is nothing to install and no root involved.

The only remaining trick is focus. When you click a button in the box window, the
box *is* the focused window. So the box hides itself first, focus falls back to
your previous app, and typing starts after a short delay.

## Usage

    ./type-box.py

Paste into the box, click where the text should go, press **Type at cursor**.
The default 3 second delay is the window in which you click your target.

Command line:

    ./typehere 'hello world'          # type these arguments
    pbpaste | ./typehere --stdin      # type piped input
    ./typehere --clipboard            # type whatever is in the clipboard
    ./typehere --clipboard -w 0.5     # ...after half a second
    ./typehere --paste 'ünïcodé 🎉'   # via Ctrl+V, for anything exotic
    ./typehere --no-fallback 'ünïcodé'  # force raw key events, dropping what fits
    ./typehere 'def f():\n    return 1'        # code is detected automatically
    ./typehere --no-auto-code 'def f():\n    return 1'  # force raw key events
    ./typehere --backspace-indent 'def f():\n    return 1'  # explicit backspace mode

`--paste` puts the text on the clipboard, presses Ctrl+V, then restores your old
clipboard. It is slower but handles characters the keycode table does not know.

Key events can only express what a US keyboard can produce, and ydotool drops
anything else *silently* - `ünïcodé` arrives as `ncod`. So if the text is not
pure ASCII, `typehere` switches to paste mode on its own and says so on stderr.
Pass `--no-fallback` to keep raw key events and accept the dropped characters.

Code detection is on by default. When the text looks like source code, `typehere`
types it line by line and uses **Shift+Enter** for newlines, so the editor does
not add its own indentation on top of the typed spaces. This is safe even when
the target app has auto-indent disabled. Non-code text is typed unchanged. Use
`--no-auto-code` to turn this off.

If your editor reliably auto-indents, `--backspace-indent` uses Backspace
instead: after each newline it removes the editor's added indentation, then
types the line's own indentation. Pass `--indent-width 2` if the editor indents
with two spaces; otherwise the width is detected from the text and falls back
to four. Do not use backspace mode in plain text fields - there is no
auto-indent to remove, so the backspaces delete the newline.

The GUI has an **Auto-code indent (Shift+Enter)** checkbox (checked by default)
and a separate **Backspace correction** checkbox for the explicit backspace
mode.
**No auto-indent (Shift+Enter)** is the older approach that avoids editor
auto-indent entirely by typing newlines as Shift+Enter.

## Install

    ./install.sh

Copies both scripts to `~/.local/bin`, adds a systemd user service so the
`ydotoold` daemon is always running (no startup delay on the first keystroke),
and adds a "Type Here" desktop entry. Then prints the one-liner for a global
hotkey.

## Notes

- Keystrokes go to the **focused** window, so focus your target during the delay.
- The tool cannot tell where text landed; some apps ignore synthetic paste or
  drop events if they are typed too fast. Raise `--key-delay` if that happens.
- Keycode mode sends what a US keyboard can produce; non-ASCII text is routed to
  `--paste` automatically rather than being silently mangled.
- Paste mode rewrites your clipboard for a moment and restores it afterwards. If
  a clipboard manager repopulates it in between, disable that or use keycode mode.
