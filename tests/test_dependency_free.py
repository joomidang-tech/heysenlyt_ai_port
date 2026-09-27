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
# 세대별 계약 스팟체크 — 향연 compose(sensorium-icad-0.1.0) · 팔레트(각 세대 recipe/compose 안)
# ══════════════════════════════════════════════════════════════════════════════
import dataclasses

import pytest

from heysenlyt_ai_port import sensorium_expo_0_1_2 as expo
from heysenlyt_ai_port import sensorium_fragrance_1_0_0 as frag
from heysenlyt_ai_port import sensorium_icad_0_1_0 as icad


def test_compose_dtos_are_frozen():
    turn = icad.ComposeTurn(role="user", content="바닷가")
    prior = icad.ComposePrior(name="창을 연 사람", emotion_group="recovery", note_names=("Bergamot",))
    param = icad.ComposeParam(history=(turn,), round=2, prior=prior)
    reply = icad.ComposeReply(payload={"is_valid": True}, stamp={"model": "m"})
    for obj, attr in ((turn, "role"), (prior, "name"), (param, "round"), (reply, "payload")):
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(obj, attr, "x")


def test_compose_param_defaults_match_the_spec():
    p = icad.ComposeParam(history=(icad.ComposeTurn("user", "안녕"),))
    assert p.round == 1 and p.prior is None and p.lang == "ko" and p.params == {}
    assert p == icad.ComposeParam(history=(icad.ComposeTurn("user", "안녕"),))


def test_compose_port_is_abstract_and_not_a_recipe_port():
    assert not issubclass(icad.ComposePort, frag.RecipePort)  # 사양서 §3-3 — 상속하지 않는다
    with pytest.raises(TypeError):
        icad.ComposePort()  # type: ignore[abstract]


def test_compose_reply_to_dict_roundtrip_and_optional_models_used():
    payload = {"name": "창을 연 사람", "recipe": {"notes": []}, "is_valid": True, "errors": [], "warnings": []}
    stamp = {"model": "m", "mode": "rule", "released_at": "2026-05-28", "kernel_version": "m+rule+2026-05-28"}
    plain = icad.ComposeReply(payload=payload, stamp=stamp).to_dict()
    assert plain == {"payload": payload, "stamp": stamp}
    assert "llm_models_used" not in plain
    used = icad.ComposeReply(payload=payload, stamp=stamp, llm_models_used={"chat": "x/y"}).to_dict()
    assert used["llm_models_used"] == {"chat": "x/y"}
    assert icad.ComposeReply(**used) == icad.ComposeReply(payload=payload, stamp=stamp, llm_models_used={"chat": "x/y"})


def test_expo_generation_has_no_regenerate():
    """식향에는 재조향 개념이 없다(기획 D2) — 세대 계약이 그 사실을 타입으로 말한다."""
    assert not hasattr(expo, "RegenerateParam") and not hasattr(expo.RecipePort, "regenerate")
    assert hasattr(frag, "RegenerateParam") and hasattr(frag.RecipePort, "regenerate")


def test_palette_is_frozen_in_every_generation():
    for gen in (frag, expo, icad):
        p = gen.Palette(notes=("Bitter Lemon", "Musk"))
        assert p.notes == ("Bitter Lemon", "Musk")
        with pytest.raises(dataclasses.FrozenInstanceError):
            p.notes = ()  # type: ignore[misc]


def test_palette_is_optional_and_last_on_every_input_dto():
    """하위호환 두 축 — 기본값 None(구 web 그대로) · 마지막 필드(위치인자 소비자 자리 유지)."""
    for cls in (frag.RecipeParam, frag.RegenerateParam, expo.RecipeParam, icad.ComposeParam):
        names = [f.name for f in dataclasses.fields(cls)]
        assert names[-1] == "palette", f"{cls.__name__}: palette 가 마지막 필드가 아니다 — {names}"
    assert frag.RecipeParam("한 문장").palette is None
    assert frag.RegenerateParam("덜 달게", {}).palette is None
    assert icad.ComposeParam(history=(icad.ComposeTurn("user", "안녕"),)).palette is None
    r = expo.RecipeParam("한 문장", "generative", "en", {"sweet_level": 3})
    assert (r.mode, r.lang, r.params, r.palette) == ("generative", "en", {"sweet_level": 3}, None)
