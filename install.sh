#!/usr/bin/env bash
# Install typehere + type-box for the current user. No root required.
set -euo pipefail

BIN="${HOME}/.local/bin"
APPS="${HOME}/.local/share/applications"
UNITS="${HOME}/.config/systemd/user"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$BIN" "$APPS" "$UNITS"
install -m 755 "$HERE/typehere" "$BIN/typehere"
install -m 755 "$HERE/type-box.py" "$BIN/type-box"

# Keep the daemon alive so the first keystroke is not delayed by startup.
cat > "$UNITS/ydotoold.service" <<'EOF'
[Unit]
Description=ydotool virtual input daemon (for typehere)

[Service]
ExecStart=/usr/bin/ydotoold -p %t/.ydotool_socket -P 0600
Restart=always
RestartSec=2

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now ydotoold.service

cat > "$APPS/type-here.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Type Here
Comment=Type text at the cursor, in any app
Exec=${BIN}/type-box
Icon=input-keyboard
Terminal=false
Categories=Utility;
Keywords=type;paste;keyboard;
EOF
update-desktop-database "$APPS" >/dev/null 2>&1 || true

echo "Installed."
echo "  GUI:  type-box            (or 'Type Here' in the app grid)"
echo "  CLI:  typehere 'hello'"
echo
echo "Optional global hotkey for the GUI:"
echo "  Settings > Keyboard > Custom Shortcuts, or bind it from a terminal."
echo
echo "Optional hotkey that types whatever is currently in your clipboard:"
cat <<EOF
  gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings "['/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/typehere/']"
  gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybindings:/typehere/ name 'Type clipboard'
  gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybindings:/typehere/ command '${BIN}/typehere --clipboard --wait 0.4'
  gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybindings:/typehere/ binding '<Primary><Alt>v'
EOF
