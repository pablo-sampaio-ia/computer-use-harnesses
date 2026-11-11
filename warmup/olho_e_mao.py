"""Warm-up: "olho e mao" sem IA. Ver = screenshot. Agir = mouse e teclado.

Dois modos:
  --container cu-sandbox   age no container (seguro; recomendado)
  --local                  age na SUA tela. Use apenas em VM descartavel!

Abre o Mousepad por atalho do terminal e digita um texto em coordenadas fixas.
Observe: se a resolucao ou o DPI mudar, as coordenadas fixas quebram. E por isso
que o computer use precisa de um modelo que ENXERGA onde clicar.
"""
import argparse
import time
from pathlib import Path

from common.computer import ContainerComputer, LocalComputer

ap = argparse.ArgumentParser()
ap.add_argument("--container")
ap.add_argument("--local", action="store_true")
args = ap.parse_args()

if args.container:
    pc = ContainerComputer(args.container)
    pc.sh("sh", "-c", "mousepad >/dev/null 2>&1 &")      # "agir" fora da GUI, so para abrir o app
elif args.local:
    pc = LocalComputer()
else:
    raise SystemExit("use --container NOME ou --local")

print(f"tela: {pc.width}x{pc.height}")
time.sleep(3)                                            # espera a janela abrir
Path("antes.png").write_bytes(pc.screenshot())           # VER
pc.click(pc.width // 2, pc.height // 2)                  # AGIR: foco no meio da tela
pc.type("Ola do olho e mao!")
time.sleep(0.5)
Path("depois.png").write_bytes(pc.screenshot())
print("salvos antes.png e depois.png")
