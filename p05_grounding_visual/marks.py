"""Set-of-Mark: desenha caixas NUMERADAS sobre a tela. O modelo escolhe "clicar na 7" (nao uma coordenada).

Fontes de caixas para telas SEM arvore (canvas, Citrix, apps customizados):
  - ocr : caixas de texto detectadas por OCR (rapidocr, leve, roda em CPU)
  - grid: grade numerada (baseline sem nenhum modelo de deteccao)
Alternativa mais forte (nao incluida): OmniParser (detector de icones + legendas) — ver README.
"""
import io

from PIL import Image, ImageDraw


def detect_ocr(png: bytes, min_conf=0.5):
    """Devolve lista de (x1, y1, x2, y2, texto) usando OCR."""
    from rapidocr_onnxruntime import RapidOCR
    import numpy as np
    img = np.array(Image.open(io.BytesIO(png)).convert("RGB"))
    result, _ = RapidOCR()(img)
    boxes = []
    for pts, text, conf in result or []:
        if float(conf) < min_conf:
            continue
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        boxes.append((int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys)), text))
    # ordem de leitura (de cima para baixo, esquerda para direita)
    return sorted(boxes, key=lambda b: (b[1] // 10, b[0]))


def detect_grid(png: bytes, cols=16, rows=10):
    w, h = Image.open(io.BytesIO(png)).size
    cw, ch = w / cols, h / rows
    return [(int(c * cw), int(r * ch), int((c + 1) * cw), int((r + 1) * ch), "") for r in range(rows) for c in range(cols)]


def draw_marks(png: bytes, boxes):
    """Devolve (png marcado, texto-legenda 'N: "texto" @ (cx,cy)')."""
    img = Image.open(io.BytesIO(png)).convert("RGB")
    d = ImageDraw.Draw(img)
    legend = []
    for n, (x1, y1, x2, y2, text) in enumerate(boxes, 1):
        d.rectangle((x1, y1, x2, y2), outline=(255, 0, 0), width=2)
        d.rectangle((x1, max(0, y1 - 14), x1 + 8 * len(str(n)) + 6, y1), fill=(255, 0, 0))
        d.text((x1 + 3, max(0, y1 - 13)), str(n), fill=(255, 255, 255))
        legend.append(f'{n}: "{text}" box=({x1},{y1},{x2},{y2})' if text else f"{n}: box=({x1},{y1},{x2},{y2})")
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue(), "\n".join(legend)
