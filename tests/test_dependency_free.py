"""계약 4 — heysenlyt_ai_port는 의존성 0 (표준 라이브러리만). AST 수준 강제."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import heysenlyt_ai_port


def test_ports_package_is_dependency_free():
    allowed = set(sys.stdlib_module_names) | {"heysenlyt_ai_port"}
    pkg = Path(heysenlyt_ai_port.__file__).parent
    for py in pkg.rglob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                roots = [(node.module or "").split(".")[0]] if node.level == 0 else []
            else:
                continue
            for r in roots:
                assert r in allowed, f"{py.name}: 외부 의존 import '{r}' — 의존성 0 위반"


# ══════════════════════════════════════════════════════════════════════════════
# 향연(ICAD) 계약 — v1.4.0 신규 심볼 (사양서 §3). 의존성 0 은 위 AST 테스트가 함께 강제한다.
# ══════════════════════════════════════════════════════════════════════════════
import dataclasses

import pytest


def test_icad_symbols_are_exported_at_top_level():
    from heysenlyt_ai_port import (  # noqa: F401 — 톱레벨 재수출이 계약 표면이다
        IcadComposeParam, IcadComposePort, IcadComposeReply, IcadPrior, IcadTurn,
    )
    for name in ("IcadComposeParam", "IcadComposePort", "IcadComposeReply", "IcadPrior", "IcadTurn"):
        assert name in heysenlyt_ai_port.__all__, name


def test_icad_dtos_are_frozen():
    from heysenlyt_ai_port import IcadComposeParam, IcadComposeReply, IcadPrior, IcadTurn

    turn = IcadTurn(role="user", content="바닷가")
    prior = IcadPrior(name="창을 연 사람", emotion_group="recovery", note_names=("Bergamot",))
    param = IcadComposeParam(history=(turn,), round=2, prior=prior)
    reply = IcadComposeReply(payload={"is_valid": True}, stamp={"model": "m"})
    for obj, attr in ((turn, "role"), (prior, "name"), (param, "round"), (reply, "payload")):
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(obj, attr, "x")


def test_icad_param_defaults_match_the_spec():
    from heysenlyt_ai_port import IcadComposeParam, IcadTurn

    p = IcadComposeParam(history=(IcadTurn("user", "안녕"),))
    assert p.round == 1 and p.prior is None and p.lang == "ko" and p.params == {}
    # 같은 값 두 개는 같다(frozen dataclass 동등성 — 재현·골든셋 비교의 전제).
    assert p == IcadComposeParam(history=(IcadTurn("user", "안녕"),))


def test_icad_port_is_abstract_and_not_a_recipe_port():
    from heysenlyt_ai_port import IcadComposePort, RecipePort

    assert not issubclass(IcadComposePort, RecipePort)  # 사양서 §3-3 — 상속하지 않는다
    with pytest.raises(TypeError):
        IcadComposePort()  # type: ignore[abstract]


def test_icad_reply_to_dict_roundtrip_and_optional_models_used():
    from heysenlyt_ai_port import IcadComposeReply

    payload = {"name": "창을 연 사람", "recipe": {"notes": []}, "is_valid": True, "errors": [], "warnings": []}
    stamp = {"model": "m", "mode": "rule", "released_at": "2026-05-28", "kernel_version": "m+rule+2026-05-28"}
    plain = IcadComposeReply(payload=payload, stamp=stamp).to_dict()
    assert plain == {"payload": payload, "stamp": stamp}  # 모르면 키 자체를 싣지 않는다
    assert "llm_models_used" not in plain

    used = IcadComposeReply(payload=payload, stamp=stamp, llm_models_used={"chat": "x/y"}).to_dict()
    assert used["llm_models_used"] == {"chat": "x/y"}  # snake_case 와이어 키(IcadContracts.ts)
    # 라운드트립 — dict 로 폈다가 다시 DTO 로 접으면 같다.
    assert IcadComposeReply(**used) == IcadComposeReply(payload=payload, stamp=stamp, llm_models_used={"chat": "x/y"})
