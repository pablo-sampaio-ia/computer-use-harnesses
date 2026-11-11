"""Interface `Computer`: o minimo para "ver" e "agir" numa tela.

Cada projeto da trilha troca a implementacao (container X11, Playwright, UIA...).
O resto do harness so conhece esta classe.
"""
import subprocess


class Computer:
    """Contrato minimo. Coordenadas sempre em pixels da tela REAL."""

    width: int
    height: int

    def screenshot(self) -> bytes:
        """Devolve a tela inteira como PNG (bytes)."""
        raise NotImplementedError

    def click(self, x, y, button="left"):
        raise NotImplementedError

    def double_click(self, x, y):
        raise NotImplementedError

    def move(self, x, y):
        raise NotImplementedError

    def drag(self, x1, y1, x2, y2):
        raise NotImplementedError

    def type(self, text):
        raise NotImplementedError

    def key(self, combo):
        """Ex.: 'Return', 'ctrl+s', 'alt+Tab' (nomes no estilo xdotool)."""
        raise NotImplementedError

    def scroll(self, x, y, dx, dy):
        """dy > 0 rola para baixo; dx > 0 para a direita (em 'cliques' de roda)."""
        raise NotImplementedError

    def close(self):
        pass


class ContainerComputer(Computer):
    """Controla um container Linux com display virtual (docker/Dockerfile).

    Tudo passa por `docker exec`: xdotool para agir, ImageMagick `import` para ver.
    """

    def __init__(self, container, width=1280, height=800, display=":1"):
        self.container = container
        self.width, self.height = width, height
        self.display = display

    def sh(self, *args, input_bytes=None, timeout=30):
        """Roda um comando dentro do container e devolve stdout (bytes)."""
        cmd = ["docker", "exec", "-i", "-e", f"DISPLAY={self.display}", self.container, *args]
        r = subprocess.run(cmd, input=input_bytes, capture_output=True, timeout=timeout)
        if r.returncode != 0:
            raise RuntimeError(f"{args[0]} falhou: {r.stderr.decode(errors='replace')[:300]}")
        return r.stdout

    def screenshot(self):
        return self.sh("import", "-window", "root", "png:-")

    def move(self, x, y):
        self.sh("xdotool", "mousemove", str(int(x)), str(int(y)))

    def click(self, x, y, button="left"):
        n = {"left": "1", "middle": "2", "right": "3"}[button]
        self.sh("xdotool", "mousemove", str(int(x)), str(int(y)), "click", n)

    def double_click(self, x, y):
        self.sh("xdotool", "mousemove", str(int(x)), str(int(y)), "click", "--repeat", "2", "--delay", "80", "1")

    def drag(self, x1, y1, x2, y2):
        self.sh("xdotool", "mousemove", str(int(x1)), str(int(y1)), "mousedown", "1",
                "mousemove", str(int(x2)), str(int(y2)), "mouseup", "1")

    def type(self, text):
        # '--' evita que textos iniciados por '-' sejam lidos como opcao.
        self.sh("xdotool", "type", "--delay", "15", "--", text)

    def key(self, combo):
        self.sh("xdotool", "key", combo)

    def scroll(self, x, y, dx, dy):
        self.sh("xdotool", "mousemove", str(int(x)), str(int(y)))
        # botoes de roda no X11: 4=cima 5=baixo 6=esquerda 7=direita
        for amount, neg, pos in ((dy, "4", "5"), (dx, "6", "7")):
            if amount:
                self.sh("xdotool", "click", "--repeat", str(abs(int(amount))), neg if amount < 0 else pos)


class LocalComputer(Computer):
    """Controla a tela da MAQUINA ONDE ROTA. Use somente dentro de uma VM descartavel."""

    def __init__(self):
        import mss
        import pyautogui
        self.pg, self.mss = pyautogui, mss
        self.width, self.height = pyautogui.size()

    def screenshot(self):
        import io
        from PIL import Image
        with self.mss.mss() as sct:
            raw = sct.grab(sct.monitors[1])
        buf = io.BytesIO()
        Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX").save(buf, "PNG")
        return buf.getvalue()

    def move(self, x, y):
        self.pg.moveTo(x, y)

    def click(self, x, y, button="left"):
        self.pg.click(x, y, button=button)

    def double_click(self, x, y):
        self.pg.doubleClick(x, y)

    def drag(self, x1, y1, x2, y2):
        self.pg.moveTo(x1, y1)
        self.pg.dragTo(x2, y2, duration=0.4)

    def type(self, text):
        self.pg.write(text, interval=0.02)

    def key(self, combo):
        self.pg.hotkey(*combo.lower().replace("return", "enter").split("+"))

    def scroll(self, x, y, dx, dy):
        self.pg.moveTo(x, y)
        if dy:
            self.pg.scroll(-int(dy))
        if dx:
            self.pg.hscroll(int(dx))
