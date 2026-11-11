"""Testes offline (sem API, sem Docker): escala, teclas e traducao de acoes dos provedores.

    uv run python -m unittest discover -s tests -t .
"""
import io
import unittest

from PIL import Image

from common.images import Scaler
from common.keys import to_xdotool
from common.providers import AnthropicProvider, GeminiProvider, OpenAIProvider
from p05_grounding_visual.grounding import parse_point
from p07_robustez.robust import screen_changed


def png(color, size=(200, 100)):
    b = io.BytesIO()
    Image.new("RGB", size, color).save(b, "PNG")
    return b.getvalue()


class Common(unittest.TestCase):
    def test_scaler_roundtrip(self):
        s = Scaler(1920, 1080, 1280)
        self.assertEqual((s.model_w, s.model_h), (1280, 720))
        self.assertEqual(s.to_screen(640, 360), (960, 540))
        img = Image.open(io.BytesIO(s.to_model_image(png((1, 2, 3), (1920, 1080)))))
        self.assertEqual(img.size, (1280, 720))

    def test_scaler_does_not_upscale(self):
        self.assertEqual(Scaler(1024, 768, 1280).factor, 1.0)

    def test_keys(self):
        self.assertEqual(to_xdotool(["CTRL", "S"]), "ctrl+s")
        self.assertEqual(to_xdotool(["ENTER"]), "Return")
        self.assertEqual(to_xdotool("ctrl+shift+Tab"), "ctrl+shift+Tab")

    def test_openai_actions(self):
        a = OpenAIProvider._action({"type": "click", "x": 5, "y": 6, "button": "left"}, "c1")
        self.assertEqual((a.kind, a.x, a.y, a.call_id), ("click", 5, 6, "c1"))
        d = OpenAIProvider._action({"type": "drag", "path": [{"x": 1, "y": 2}, {"x": 9, "y": 8}]}, "c")
        self.assertEqual((d.x, d.y, d.x2, d.y2), (1, 2, 9, 8))
        s = OpenAIProvider._action({"type": "scroll", "x": 0, "y": 0, "scroll_x": 0, "scroll_y": 300}, "c")
        self.assertEqual((s.dx, s.dy), (0, 3))

    def test_anthropic_actions(self):
        a = AnthropicProvider._action("left_click", {"coordinate": [10, 20]}, "t1")
        self.assertEqual((a.kind, a.x, a.y), ("click", 10, 20))
        k = AnthropicProvider._action("key", {"text": "ctrl+s"}, "t")
        self.assertEqual(k.text, "ctrl+s")
        r = AnthropicProvider._action("right_click", {"coordinate": [1, 1]}, "t")
        self.assertEqual(r.button, "right")

    def test_gemini_normalized_coordinates(self):
        g = GeminiProvider.__new__(GeminiProvider)          # sem criar cliente/API
        g.w, g.h = 1000, 500
        a = g._action("click", {"x": 500, "y": 500}, "id")
        self.assertEqual((a.x, a.y), (500, 250))
        t = g._action("type", {"text": "oi", "press_enter": True}, "id")
        self.assertEqual(t.text, "oi\n")

    def test_parse_point(self):
        self.assertEqual(parse_point('{"x": 10, "y": 20}', 100, 100), (10, 20))
        self.assertEqual(parse_point("click(start_box='(33,44)')", 100, 100), (33, 44))
        self.assertEqual(parse_point('{"x": 999, "y": 5}', 100, 100), (99, 5))      # limita a imagem

    def test_screen_changed(self):
        self.assertFalse(screen_changed(png((10, 10, 10)), png((10, 10, 10))))
        self.assertTrue(screen_changed(png((0, 0, 0)), png((255, 255, 255))))


if __name__ == "__main__":
    unittest.main()
