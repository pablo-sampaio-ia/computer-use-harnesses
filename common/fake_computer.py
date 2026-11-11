"""Tela simulada (Pillow) para testar o encanamento das APIs SEM Docker e sem tocar no seu desktop.

Desenha um botao "OK" e registra os cliques/teclas. Se o clique cai no botao, a tela muda para "Feito!".
"""
import io

from PIL import Image, ImageDraw

from common.computer import Computer


class FakeComputer(Computer):
    def __init__(self, width=1024, height=768):
        self.width, self.height = width, height
        self.btn = (400, 300, 624, 380)      # x1,y1,x2,y2
        self.log, self.pressed = [], False

    def screenshot(self):
        img = Image.new("RGB", (self.width, self.height), (235, 235, 235))
        d = ImageDraw.Draw(img)
        d.text((20, 20), "Tarefa de teste: clique no botao OK", fill=(0, 0, 0))
        color = (80, 200, 80) if self.pressed else (60, 120, 220)
        d.rectangle(self.btn, fill=color)
        d.text((490, 335), "Feito!" if self.pressed else "OK", fill=(255, 255, 255))
        buf = io.BytesIO()
        img.save(buf, "PNG")
        return buf.getvalue()

    def click(self, x, y, button="left"):
        self.log.append(("click", x, y))
        x1, y1, x2, y2 = self.btn
        if x1 <= x <= x2 and y1 <= y <= y2:
            self.pressed = True

    def double_click(self, x, y):
        self.click(x, y)

    def move(self, x, y):
        self.log.append(("move", x, y))

    def drag(self, x1, y1, x2, y2):
        self.log.append(("drag", x1, y1, x2, y2))

    def type(self, text):
        self.log.append(("type", text))

    def key(self, combo):
        self.log.append(("key", combo))

    def scroll(self, x, y, dx, dy):
        self.log.append(("scroll", x, y, dx, dy))
