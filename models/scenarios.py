"""
Banco de cenários de phishing para o Simulador de Cenários.
Dados carregados do arquivo JSON externo (data/scenarios.json).
"""

import json
from pathlib import Path

_SCENARIOS_FILE = Path(__file__).resolve().parent.parent / "data" / "scenarios.json"


def _load_scenarios() -> tuple[list[str], list[dict]]:
    """Carrega cenários do arquivo JSON."""
    data = json.loads(_SCENARIOS_FILE.read_text(encoding="utf-8"))
    scenarios = data.get("scenarios", [])
    # Converte alerts de listas para tuplas (compatibilidade)
    for s in scenarios:
        s["alerts"] = [tuple(a) for a in s.get("alerts", [])]
    return data.get("categories", []), scenarios


SCENARIO_CATEGORIES, SCENARIOS = _load_scenarios()

