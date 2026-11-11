"""Escala de screenshots: o modelo ve uma imagem menor; convertemos as coordenadas de volta."""
import io

from PIL import Image


class Scaler:
    """Reduz a tela para no maximo `max_width` de largura (mantendo a proporcao).

    O experimento de resolucao do P1 e simplesmente variar `max_width`.
    """

    def __init__(self, screen_w, screen_h, max_width=1280):
        self.screen_w, self.screen_h = screen_w, screen_h
        self.factor = min(1.0, max_width / screen_w)          # <= 1.0
        self.model_w = round(screen_w * self.factor)
        self.model_h = round(screen_h * self.factor)

    def to_model_image(self, png: bytes) -> bytes:
        """PNG da tela real -> PNG no tamanho que o modelo ve."""
        if self.factor == 1.0:
            return png
        img = Image.open(io.BytesIO(png)).convert("RGB")
        img = img.resize((self.model_w, self.model_h), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, "PNG")
        return buf.getvalue()

    def to_screen(self, x, y):
        """Coordenada no espaco do modelo -> coordenada na tela real."""
        return round(x / self.factor), round(y / self.factor)
