# Ambiente descartavel para os projetos: Linux com display virtual (Xvfb),
# gerenciador de janelas leve, VNC + noVNC para assistir pelo navegador,
# xdotool (agir), ImageMagick (screenshot), um editor, o Chromium e um
# "sistema legado" de brinquedo (legacy_app.py) para as tarefas de demonstracao.
FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive DISPLAY=:1 SCREEN=1280x800x24
RUN apt-get update && apt-get install -y --no-install-recommends \
      xvfb fluxbox x11vnc novnc websockify xdotool imagemagick socat \
      mousepad chromium xterm python3 python3-pip fonts-dejavu-core ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Chromium dentro de container precisa de --no-sandbox (o proprio container e o sandbox).
RUN echo 'export CHROMIUM_FLAGS="$CHROMIUM_FLAGS --no-sandbox --no-first-run --disable-gpu --start-maximized"' \
      > /etc/chromium.d/cu-flags

RUN useradd -m agent && mkdir -p /opt/legacy /tmp/state /home/agent/Documents /home/agent/.fluxbox \
    && chown -R agent /tmp/state /home/agent
COPY legacy_app.py /opt/legacy/legacy_app.py
COPY entrypoint.sh /entrypoint.sh
COPY fluxbox_menu /home/agent/.fluxbox/menu
RUN chmod +x /entrypoint.sh && chown agent /home/agent/.fluxbox/menu
USER agent
WORKDIR /home/agent
# 6080 = noVNC (http://localhost:6080/vnc.html); 8000 = sistema legado; 9223 = CDP do Chromium (P2/P3)
EXPOSE 6080 8000 9223
ENTRYPOINT ["/entrypoint.sh"]
