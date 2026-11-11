"""P9: o "computador" como servidor MCP, com governanca na frente.

Qualquer cliente MCP (um agente nosso, um agente de codigo, o Claude Desktop...) usa as ferramentas:
  get_elements, screenshot, goto, click, fill, fill_secret, press
e todas passam por: allowlist de dominios -> classificacao (read/write/send/deny) -> aprovacao humana
-> limites de acoes/tempo -> cofre/mascaramento -> auditoria.

    uv run python -m p09_gateway_mcp.server            # stdio (como servidor MCP)
Variaveis: POLICY_FILE, APPROVAL_MODE (ask|auto_approve|auto_deny), GOVERNANCE=off (SO PARA O LAB: desliga a politica),
           AUDIT_FILE, CU_SECRET_<ID>=valor
"""
import os
import time
from pathlib import Path

from mcp.server.mcpserver import Image, MCPServer   # mcp 2.x (no 1.x era FastMCP)
from mcp.server.mcpserver.exceptions import ToolError
from playwright.async_api import async_playwright

from p02_dom_a11y.agent import SNAPSHOT_JS
from p09_gateway_mcp.governance import Approver, Audit, Policy, Vault

HERE = Path(__file__).parent
policy = Policy.load(os.getenv("POLICY_FILE", HERE / "policy.yaml"))
if os.getenv("APPROVAL_MODE"):
    policy.approval = os.environ["APPROVAL_MODE"]
GOV = os.getenv("GOVERNANCE", "on") != "off"
vault = Vault()
audit = Audit(os.getenv("AUDIT_FILE", "runs/audit.jsonl"), vault)
approver = Approver(policy.approval)
mcp = MCPServer("governed-computer")

S = {"pw": None, "page": None, "t0": time.time(), "n": 0}


async def page():
    if S["page"] is None:
        S["pw"] = await async_playwright().start()
        browser = await S["pw"].chromium.launch()
        ctx = await browser.new_context(viewport={"width": 1024, "height": 768})

        async def gate(route):                    # allowlist de REDE no navegador (nem script de pagina escapa)
            if GOV and not policy.host_allowed(route.request.url):
                audit.log(tool="network", url=route.request.url, decision="deny", reason="host fora da allowlist")
                return await route.abort()
            await route.continue_()

        await ctx.route("**/*", gate)
        S["page"] = await ctx.new_page()
    return S["page"]


def deny(tool, args, reason):
    audit.log(tool=tool, args=args, decision="deny", reason=reason)
    raise ToolError(f"NEGADO pela politica: {reason}")   # ToolError: a mensagem chega ao cliente


def limits(tool, args):
    S["n"] += 1
    if GOV and (S["n"] > policy.max_actions or time.time() - S["t0"] > policy.max_seconds):
        deny(tool, args, "limite de acoes/tempo da sessao excedido")


async def element(ref):
    p = await page()
    return await p.locator(f'[data-ref="{ref}"]').evaluate(
        "el => ({text: (el.innerText || el.value || el.name || '').trim(), type: el.type || '', tag: el.tagName.toLowerCase()})")


def authorize(tool, args, cls, desc):
    """cls: read | write | send | deny. Aplica a politica e registra."""
    limits(tool, args)
    if GOV:
        if cls == "deny":
            deny(tool, args, f"acao proibida: {desc}")
        if cls == "send" and not approver.request(f"{tool} {desc}"):
            deny(tool, args, f"aprovacao humana negada: {desc}")
    audit.log(tool=tool, args=args, cls=cls, decision="allow", desc=desc)


# --------------------------------------------------------------------------- ferramentas
@mcp.tool()
async def get_elements() -> str:
    """Lista os elementos interativos da pagina atual (com `ref`) e o texto visivel."""
    authorize("get_elements", {}, "read", "")
    p = await page()
    elems = await p.evaluate(SNAPSHOT_JS)
    text = (await p.inner_text("body"))[:1500]
    return vault.scrub(f"URL: {p.url}\nTEXTO:\n{text}\nELEMENTOS:\n" + "\n".join(elems))


@mcp.tool()
async def screenshot() -> Image:
    """Screenshot PNG da pagina."""
    authorize("screenshot", {}, "read", "")
    return Image(data=await (await page()).screenshot(type="png"), format="png")


@mcp.tool()
async def goto(url: str) -> str:
    """Abre uma URL."""
    if GOV and not policy.host_allowed(url):
        limits("goto", {"url": url})
        deny("goto", {"url": url}, f"dominio fora da allowlist: {url}")
    authorize("goto", {"url": url}, "write", url)
    await (await page()).goto(url)
    return "ok"


@mcp.tool()
async def click(ref: int) -> str:
    """Clica no elemento `ref`."""
    el = await element(ref)
    authorize("click", {"ref": ref}, policy.classify_click(el["text"]), f'clique em "{el["text"]}"')
    p = await page()
    await p.locator(f'[data-ref="{ref}"]').click(timeout=5000)
    await p.wait_for_load_state()
    return "ok"


@mcp.tool()
async def fill(ref: int, text: str) -> str:
    """Preenche um campo de texto. Campos de senha exigem fill_secret."""
    el = await element(ref)
    if GOV and el["type"] == "password":
        limits("fill", {"ref": ref})
        deny("fill", {"ref": ref}, "campo de senha: use fill_secret (segredos nao passam pelo modelo)")
    authorize("fill", {"ref": ref, "text": text}, "write", f'campo "{el["text"]}"')
    await (await page()).locator(f'[data-ref="{ref}"]').fill(text, timeout=5000)
    return "ok"


@mcp.tool()
async def fill_secret(secret_id: str, ref: int) -> str:
    """Preenche o campo `ref` com um segredo do cofre. O valor NUNCA volta ao modelo nem aos logs."""
    authorize("fill_secret", {"secret_id": secret_id, "ref": ref}, "write", f"segredo {secret_id}")
    await (await page()).locator(f'[data-ref="{ref}"]').fill(vault.get(secret_id), timeout=5000)
    return "ok (valor mascarado)"


@mcp.tool()
async def press(key: str) -> str:
    """Pressiona uma tecla (ex.: Enter)."""
    authorize("press", {"key": key}, "send" if key.lower() == "enter" else "write", key)
    await (await page()).keyboard.press(key)
    return "ok"


if __name__ == "__main__":
    mcp.run()
