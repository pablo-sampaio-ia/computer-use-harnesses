"""P4: agente Windows por UI Automation (UIA). O modelo recebe a ARVORE de controles em texto.

    [e3] Edit "Nome completo" id=txtNome value=""
    [e7] Button "Salvar cliente" id=btnSalvar

e age por ferramentas: click(ref), set_text(ref, text), select(ref, option), send_keys(keys).
Acoes usam padroes UIA (InvokePattern, ValuePattern...): nao movem o mouse real nem dependem de coordenadas.

SEGURANCA: o agente fica preso a UM processo (pid). Ele nunca ve nem toca nas outras janelas do desktop.

    uv sync --extra windows
    uv run python -m p04_windows_uia.agent --demo
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

from pywinauto import Application

from common.llm import LLM
from common.toolloop import run_tool_agent

HERE = Path(__file__).parent

# Tipos de controle que valem a pena mostrar ao modelo (o resto e ruido: paineis, pane, etc.).
INTERESTING = {"Edit", "Button", "ComboBox", "CheckBox", "RadioButton", "Text", "MenuItem", "ListItem",
               "TabItem", "Hyperlink", "Document", "DataItem", "Slider", "Spinner", "Tree", "TreeItem"}

TITLEBAR = {"Sistema", "Minimizar", "Maximizar", "Fechar", "Restaurar", "Abrir"}

SYSTEM = ("Voce opera um aplicativo Windows de desktop por ferramentas. A cada passo recebe a arvore de controles "
          "(UI Automation) do aplicativo, com numeros `ref` como e1, e2... Os refs mudam a cada passo: use os do estado mais "
          "recente. Use set_text para campos de texto, select para listas, click para botoes. Leia o valor dos campos "
          "na propria arvore para verificar. Quando terminar, chame `done`.")


class UiaSession:
    """Prende o agente a um processo e traduz refs <-> controles."""

    def __init__(self, pid):
        self.app = Application(backend="uia").connect(process=pid, timeout=15)
        self.refs = {}

    def window(self):
        return self.app.top_window()           # a janela/dialogo mais ao topo DESTE app

    def dump(self, max_elems=120):
        """Percorre os descendentes e monta o texto da arvore. Guarda ref -> controle."""
        self.refs.clear()
        win = self.window()
        lines = [f'JANELA: "{win.window_text()}"']
        for ctl in win.descendants():
            info = ctl.element_info
            ctype = info.control_type
            if ctype not in INTERESTING:
                continue
            name = (info.name or "").strip()
            if ctype == "Text" and not name:
                continue
            if name in TITLEBAR:                    # ruido: botoes da barra de titulo
                continue
            ref = f"e{len(self.refs) + 1}"
            self.refs[ref] = ctl
            line = f'[{ref}] {ctype} "{name[:60]}"'
            if info.automation_id:
                line += f" id={info.automation_id}"
            if ctype in ("Edit", "ComboBox", "Document"):
                try:
                    val = ctl.selected_text() if ctype == "ComboBox" else ctl.get_value()
                except Exception:
                    val = ctl.window_text()
                line += f' value="{val[:60]}"'
            if not info.enabled:
                line += " (desabilitado)"
            lines.append(line)
            if len(self.refs) >= max_elems:
                lines.append("... (arvore truncada)")
                break
        return "\n".join(lines)

    def ctl(self, ref):
        if ref not in self.refs:
            raise KeyError(f"ref {ref} nao existe no estado atual")
        return self.refs[ref]


def make_tools(s: UiaSession):
    def click(ref):
        c = s.ctl(ref)
        try:
            c.invoke()                          # InvokePattern: sem mouse real
        except Exception:
            c.click_input()                     # fallback: clique real (limitacao: precisa de foco/visivel)
        time.sleep(0.4)
        return "ok"

    def set_text(ref, text):
        s.ctl(ref).set_edit_text(text)          # ValuePattern
        return "ok"

    def select(ref, option):
        s.ctl(ref).select(option)
        return "ok"

    def send_keys(keys):
        s.window().type_keys(keys, with_spaces=True)   # sintaxe pywinauto: ^s = Ctrl+S, {ENTER}
        return "ok"

    def done(resumo=""):
        return "fim"

    obj = lambda props, req: {"type": "object", "properties": props, "required": req}
    ref = {"ref": {"type": "string"}}
    return [
        ({"name": "click", "description": "Aciona um botao/item", "parameters": obj(ref, ["ref"])}, click),
        ({"name": "set_text", "description": "Define o texto de um campo",
          "parameters": obj({**ref, "text": {"type": "string"}}, ["ref", "text"])}, set_text),
        ({"name": "select", "description": "Seleciona uma opcao de uma lista suspensa",
          "parameters": obj({**ref, "option": {"type": "string"}}, ["ref", "option"])}, select),
        ({"name": "send_keys", "description": "Envia teclas a janela (^s = Ctrl+S, {ENTER})",
          "parameters": obj({"keys": {"type": "string"}}, ["keys"])}, send_keys),
        ({"name": "done", "description": "Encerra a tarefa", "parameters": obj({"resumo": {"type": "string"}}, [])}, done),
    ]


def run_on_pid(pid, goal, llm=None, max_steps=25, verbose=True):
    s = UiaSession(pid)
    return run_tool_agent(llm or LLM(), SYSTEM, goal, s.dump, make_tools(s), max_steps, verbose)


def launch_legacy(out_file):
    """Abre o formulario WinForms de teste e devolve o processo.

    -ExecutionPolicy Bypass vale so para ESTE processo (nao altera a politica do sistema); sem ele,
    maquinas com scripts desabilitados recusam o .ps1.
    """
    p = subprocess.Popen(["powershell", "-STA", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(HERE / "legacy_form.ps1"),
                          "-OutFile", str(out_file)])
    time.sleep(4)
    return p


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("goal", nargs="?")
    ap.add_argument("--pid", type=int, help="PID do app alvo")
    ap.add_argument("--demo", action="store_true", help="abre o formulario legado de teste e cadastra clientes")
    ap.add_argument("--dump", action="store_true", help="so imprime a arvore (sem LLM)")
    args = ap.parse_args()
    out = Path("runs/clientes_win.jsonl").resolve()
    if args.demo:
        out.parent.mkdir(exist_ok=True)
        out.write_text("", encoding="utf-8")
        proc = launch_legacy(out)
        pid = proc.pid
        goal = args.goal or ("Cadastre os clientes: 'Ana Lima', ana@exemplo.com, telefone 11 90000-0001, tipo Pessoa fisica; "
                             "e 'Bruno SA', contato@bruno.com, telefone 11 90000-0002, tipo Empresa. Clique em 'Salvar cliente' em cada um.")
    else:
        pid, goal = args.pid, args.goal
        proc = None
    try:
        if args.dump:
            print(UiaSession(pid).dump())
            sys.exit(0)
        run_on_pid(pid, goal)
    finally:
        if proc:
            proc.terminate()
    if args.demo:
        print("--- registros ---\n" + out.read_text(encoding="utf-8-sig"))
