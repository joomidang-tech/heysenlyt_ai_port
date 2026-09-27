"""모양 계약 — 포트는 **센소리움 세대**로 갈린다(2026-09-27 개편).

어댑터(`heysenlyt_ai_adapter`)·통합코드(`heysenlyt-ai/application`)가 같은 세대 폴더를 갖는다. 어댑터는
세대 폴더째 복사해 쓰므로 세대 폴더는 **자기완결**이어야 한다 — 세대끼리 import 하면 복사가 성립하지 않는다.
"""

from __future__ import annotations

import ast
from pathlib import Path

import heysenlyt_ai_port
from heysenlyt_ai_port import GENERATIONS, generation_folder

PKG = Path(heysenlyt_ai_port.__file__).parent
TOP_FILES = {"__init__.py", "errors.py", "llm.py", "version.py"}   # 세대 무관 계약 — 이 넷뿐
_IMPORT_ROOT = PKG.parent.resolve()


def _imports(py: Path) -> set[str]:
    out: set[str] = set()
    parts = list(py.resolve().relative_to(_IMPORT_ROOT).with_suffix("").parts)
    pkg = parts[:-1]
    for node in ast.walk(ast.parse(py.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom):
            if node.level:
                base = pkg[: len(pkg) - (node.level - 1)]
                names = [node.module] if node.module else [a.name for a in node.names]
                out.update(".".join([*base, n]) for n in names)
            elif node.module:
                out.add(node.module)
        elif isinstance(node, ast.Import):
            out.update(a.name for a in node.names)
    return out


def _generation_dirs() -> set[str]:
    return {p.name for p in PKG.iterdir() if p.is_dir() and p.name != "__pycache__"}


def test_folders_are_exactly_the_registered_generations():
    assert _generation_dirs() == {generation_folder(v) for v in GENERATIONS}, sorted(_generation_dirs())
    for version_id, module in GENERATIONS.items():
        assert module.VERSION_ID == version_id
        assert module.__name__ == f"heysenlyt_ai_port.{generation_folder(version_id)}"


def test_top_level_holds_only_generation_agnostic_contracts():
    assert {p.name for p in PKG.glob("*.py")} == TOP_FILES


def test_generation_folders_are_self_contained():
    """세대 폴더는 자기 자신 + 최상위 3파일만 import 한다. 다른 세대·`shared` 류 공용 폴더 금지."""
    allowed_top = {f"heysenlyt_ai_port.{n[:-3]}" for n in TOP_FILES - {"__init__.py"}}
    for folder in _generation_dirs():
        for py in (PKG / folder).rglob("*.py"):
            for mod in _imports(py):
                if not mod.startswith("heysenlyt_ai_port"):
                    continue
                ok = mod == "heysenlyt_ai_port" or mod in allowed_top or mod.startswith(f"heysenlyt_ai_port.{folder}")
                assert ok, f"{folder}/{py.name} → {mod} (세대 밖 import)"
                assert mod != "heysenlyt_ai_port", f"{folder}/{py.name} → 톱레벨 import(세대 레지스트리 순환)"


def test_each_generation_declares_domain_and_ports_that_exist():
    for module in GENERATIONS.values():
        assert module.DOMAIN in ("fragrance", "flavor")
        for port in module.PORTS:
            assert (PKG / generation_folder(module.VERSION_ID) / f"{port}.py").exists(), (module.VERSION_ID, port)
            cls = {"recipe": "RecipePort", "conversation": "ConversationPort", "compose": "ComposePort"}[port]
            assert hasattr(module, cls), (module.VERSION_ID, cls)


def test_generation_id_to_folder_rule():
    assert generation_folder("sensorium-fragrance-1.0.0") == "sensorium_fragrance_1_0_0"
    assert generation_folder("sensorium-fragrance-1.0.0+tecan") == "sensorium_fragrance_1_0_0"  # 기기 변형은 AI 세대가 아니다
    assert heysenlyt_ai_port.base_version("sensorium-expo-0.1.2+tecan") == "sensorium-expo-0.1.2"
    assert heysenlyt_ai_port.base_version(None) is None and heysenlyt_ai_port.base_version("  ") is None


def test_public_surface_is_declared():
    for name in heysenlyt_ai_port.__all__:
        assert hasattr(heysenlyt_ai_port, name), name


def test_every_conversation_contract_has_the_fields_the_harness_relies_on():
    """통합코드 `application/silence.py`(침묵 복구 · 세대 무관)는 모든 세대의 대화 계약이 이 형상이라고 가정한다 —
    입력에 `require_text`, 출력에 reply·done·result·keywords·history·stamp. 세대가 형상을 바꾸면 여기서 먼저 걸린다."""
    import dataclasses

    for module in GENERATIONS.values():
        if "conversation" not in module.PORTS:
            continue
        inp = {f.name for f in dataclasses.fields(module.ConversationParam)}
        assert {"domain", "message", "history", "lang", "kickoff", "params", "require_text"} <= inp, module.VERSION_ID
        out = {f.name for f in dataclasses.fields(module.ConverseReply)}
        assert {"reply", "done", "result", "keywords", "history", "stamp"} <= out, module.VERSION_ID


def test_palette_carries_names_only_in_every_generation():
    """양(mL)·포트 번호·펌프 주소가 계약에 새면 안 된다 — 세대마다 Palette 가 따로 있으니 세대마다 잠근다."""
    import dataclasses

    for module in GENERATIONS.values():
        assert [f.name for f in dataclasses.fields(module.Palette)] == ["notes"], module.VERSION_ID


def test_legacy_top_level_shim_is_present_and_points_at_the_first_generations():
    """v1.4.0 사이클 한정 하위호환(검증팀 P1). 통합 main 이 세대 축으로 승격되면 이 테스트와 shim 을 함께 지운다."""
    from heysenlyt_ai_port import sensorium_fragrance_1_0_0 as frag
    from heysenlyt_ai_port import sensorium_icad_0_1_0 as icad

    for name in heysenlyt_ai_port.LEGACY_TOP_LEVEL_NAMES:
        assert hasattr(heysenlyt_ai_port, name), name
        assert name not in heysenlyt_ai_port.__all__, f"{name}: shim 은 공개 표면(__all__)이 아니다"
    assert heysenlyt_ai_port.RecipePort is frag.RecipePort
    assert heysenlyt_ai_port.IcadComposePort is icad.ComposePort


def test_generation_folder_rejects_empty_ids():
    import pytest

    for bad in (None, "", "   ", "+tecan"):
        with pytest.raises(ValueError):
            generation_folder(bad)  # type: ignore[arg-type]


def test_generation_contract_is_abstract_and_ports_are_derived_from_it():
    """세대가 제공할 것 = `AiContract` 의 추상 메서드. PORTS 는 거기서 파생 — 두 목록이 따로 살지 않는다(2026-09-27)."""
    import pytest

    for module in GENERATIONS.values():
        with pytest.raises(TypeError):
            module.AiContract()  # type: ignore[abstract]
        abstract = module.AiContract.__abstractmethods__
        assert set(module.PORTS) <= abstract
        assert set(module.PORTS) == abstract - {"chat_stamp"}
    assert "chat_stamp" in heysenlyt_ai_port.sensorium_icad_0_1_0.AiContract.__abstractmethods__
