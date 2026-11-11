"""Constroi a imagem e sobe/derruba o container.   uv run python docker/run.py up|down|build"""
import subprocess
import sys
from pathlib import Path

IMAGE, NAME = "cu-harness", "cu-sandbox"
HERE = Path(__file__).parent


def sh(*cmd, check=True):
    return subprocess.run(cmd, check=check)


def up(name=NAME, novnc_port=6080, cdp_port=9223):
    sh("docker", "rm", "-f", name, check=False)
    sh("docker", "run", "-d", "--name", name, "-p", f"{novnc_port}:6080", "-p", f"{cdp_port}:9223", "--shm-size=512m", IMAGE)
    print(f"Assista em http://localhost:{novnc_port}/vnc.html  (container {name})")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "up"
    if cmd == "build":
        sh("docker", "build", "-t", IMAGE, str(HERE))
    elif cmd == "up":
        up()
    elif cmd == "down":
        sh("docker", "rm", "-f", NAME)
