#!/bin/sh
# Sobe o display virtual, o gerenciador de janelas, o VNC/noVNC e o sistema legado.
Xvfb :1 -screen 0 "$SCREEN" -nolisten tcp &
sleep 1
fluxbox >/dev/null 2>&1 &
x11vnc -display :1 -forever -shared -nopw -quiet -rfbport 5900 >/dev/null 2>&1 &
websockify --web /usr/share/novnc 6080 localhost:5900 >/dev/null 2>&1 &
python3 /opt/legacy/legacy_app.py >/tmp/legacy.log 2>&1 &
# Mantem o container vivo.
exec tail -f /dev/null
