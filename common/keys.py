"""Normaliza nomes de teclas dos provedores para o estilo xdotool."""

_NAMES = {
    "enter": "Return", "return": "Return", "esc": "Escape", "escape": "Escape",
    "ctrl": "ctrl", "control": "ctrl", "alt": "alt", "shift": "shift",
    "cmd": "super", "meta": "super", "super": "super", "win": "super", "windows": "super",
    "space": "space", "tab": "Tab", "backspace": "BackSpace", "delete": "Delete", "del": "Delete",
    "arrowleft": "Left", "arrowright": "Right", "arrowup": "Up", "arrowdown": "Down",
    "left": "Left", "right": "Right", "up": "Up", "down": "Down",
    "pageup": "Prior", "pagedown": "Next", "home": "Home", "end": "End",
}


def to_xdotool(keys) -> str:
    """['CTRL','S'] ou 'ctrl+s' -> 'ctrl+s'."""
    if isinstance(keys, str):
        keys = keys.split("+")
    out = []
    for k in keys:
        low = k.strip().lower()
        out.append(_NAMES.get(low, low if len(low) == 1 else k.strip()))
    return "+".join(out)
