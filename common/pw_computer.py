"""Um `Computer` que e uma pagina do Playwright: pixels + mouse/teclado, mas SEM Docker.

Util para testar loops de pixels (P1, P5) contra um navegador isolado (nao toca no seu desktop).
O navegador ve apenas a pagina (viewport), sem barra de endereco: abra a URL com `goto` antes.
"""
from common.computer import Computer


class PlaywrightComputer(Computer):
    def __init__(self, page, width=1280, height=800):
        self.page, self.width, self.height = page, width, height
        page.set_viewport_size({"width": width, "height": height})

    def screenshot(self):
        return self.page.screenshot(type="png")

    def click(self, x, y, button="left"):
        self.page.mouse.click(x, y, button=button)

    def double_click(self, x, y):
        self.page.mouse.dblclick(x, y)

    def move(self, x, y):
        self.page.mouse.move(x, y)

    def drag(self, x1, y1, x2, y2):
        self.page.mouse.move(x1, y1)
        self.page.mouse.down()
        self.page.mouse.move(x2, y2)
        self.page.mouse.up()

    def type(self, text):
        self.page.keyboard.type(text)

    def key(self, combo):
        # xdotool 'ctrl+s'/'Return' -> Playwright 'Control+s'/'Enter'
        names = {"ctrl": "Control", "Return": "Enter", "super": "Meta", "BackSpace": "Backspace",
                 "Prior": "PageUp", "Next": "PageDown", "Escape": "Escape"}
        self.page.keyboard.press("+".join(names.get(k, k) for k in combo.split("+")))

    def scroll(self, x, y, dx, dy):
        self.page.mouse.move(x, y)
        self.page.mouse.wheel(dx * 100, dy * 100)
