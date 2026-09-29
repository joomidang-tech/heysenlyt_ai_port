"""포트 = 인터페이스 — **파라미터·리턴은 클래스로 강제**한다(2026-09-29).

무엇을 잠그나
  · 모든 추상 메서드의 리턴 어노테이션이 클래스다(dict 금지) — 어댑터가 dict 를 돌려주면 타입에서 어긋난다.
  · 레시피 한 줄의 `id` 는 필수다(향료 id · 이름과 분리). 비었거나 없으면 만드는 순간 예외.
  · `to_dict()`/`from_dict()` 왕복이 와이어 모양을 보존한다 — 계약 밖 키는 extra 로 살아남고, None 인 칸은 생략된다.
"""

from __future__ import annotations

import typing

import pytest

import heysenlyt_ai_port
from heysenlyt_ai_port import GENERATIONS, Stamp
from heysenlyt_ai_port import sensorium_expo_0_1_2 as expo
from heysenlyt_ai_port import sensorium_fragrance_1_0_0 as frag
from heysenlyt_ai_port import sensorium_icad_0_1_0 as icad

STAMP = {"model": "m", "mode": "rule", "released_at": "2026-05-28", "kernel_version": "m+rule+2026-05-28"}
NOTE = {"id": "bergamot", "name": "Bergamot", "nameKo": "베르가못", "amountMl": 0.03, "percent": 30, "type": "top",
        "futureKey": 1}


def _abstract_methods(cls):
    return {n: getattr(cls, n) for n in getattr(cls, "__abstractmethods__", ())}


@pytest.mark.parametrize("module", list(GENERATIONS.values()), ids=list(GENERATIONS))
def test_every_abstract_method_returns_a_class_not_a_dict(module):
    ports = [module.AiContract] + [getattr(module, c) for c in ("RecipePort", "ConversationPort", "ComposePort")
                                   if hasattr(module, c)]
    for cls in ports:
        for name, fn in _abstract_methods(cls).items():
            hints = typing.get_type_hints(fn, globalns={**vars(module), **vars(heysenlyt_ai_port)})
            ret = hints.get("return")
            assert isinstance(ret, type), f"{module.VERSION_ID} {cls.__name__}.{name} → {ret!r} (클래스여야 한다)"
            assert ret is not dict, f"{module.VERSION_ID} {cls.__name__}.{name} 가 dict 를 돌려준다"


@pytest.mark.parametrize("gen", [frag, icad])
def test_recipe_note_requires_a_non_empty_id(gen):
    with pytest.raises(ValueError):
        gen.RecipeNote(id="", name="Bergamot")
    with pytest.raises(ValueError):
        gen.RecipeNote(id="   ", name="Bergamot")
    with pytest.raises(ValueError):
        gen.RecipeNote.from_dict({k: v for k, v in NOTE.items() if k != "id"})
    with pytest.raises(ValueError):  # 레시피 안의 한 줄만 빠져도 레시피를 만들 수 없다
        gen.FragranceRecipe.from_dict({"notes": [NOTE, {"name": "Musk", "amountMl": 0.01}]})


def test_flavor_item_requires_a_non_empty_id():
    with pytest.raises(ValueError):
        expo.FlavorItem(id="")
    with pytest.raises(ValueError):
        expo.FlavorItem.from_dict({"amount_ml": 0.1, "role": "main"})


@pytest.mark.parametrize("gen", [frag, icad])
def test_fragrance_recipe_roundtrip_keeps_wire_shape(gen):
    wire = {"name": "바다", "nameKo": "바다", "notes": [NOTE], "totalVolumeMl": 0.1, "extraTop": "x"}
    r = gen.FragranceRecipe.from_dict(wire)
    assert r.notes[0].id == "bergamot" and r.notes[0].name == "Bergamot" and r.notes[0].amount_ml == 0.03
    assert r.to_dict() == wire                      # 계약 밖 키(futureKey·extraTop)까지 그대로
    assert gen.FragranceRecipe().to_dict() == {}    # 없던 칸은 만들어 내지 않는다(빈 prior 엣지)


def test_flavor_recipe_roundtrip_keeps_wire_shape():
    wire = {"drinkTitle": "달빛", "items": [{"channel_id": "grape", "amount_ml": 0.1, "role": "main"}],
            "sweetMl": 1.0, "families": {"grape": 5.0}, "specialAromas": [], "newKey": True}
    r = expo.FlavorRecipe.from_dict(wire)
    assert r.items[0].id == "grape"
    assert r.to_dict() == wire


@pytest.mark.parametrize("gen", [frag, expo])
def test_recipe_reply_refuses_dicts_where_classes_belong(gen):
    recipe_cls = gen.FragranceRecipe if gen is frag else gen.FlavorRecipe
    with pytest.raises(TypeError):
        gen.RecipeReply(domain="d", version="1", stamp=STAMP, recipe=recipe_cls())  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        gen.RecipeReply(domain="d", version="1", stamp=Stamp.from_dict(STAMP), recipe={})  # type: ignore[arg-type]
    reply = gen.RecipeReply(domain="d", version="1", stamp=Stamp.from_dict(STAMP), recipe=recipe_cls(),
                            warnings=["w"])
    assert gen.RecipeReply.from_dict(reply.to_dict()).to_dict() == reply.to_dict()


def test_regenerate_prior_is_a_recipe_class():
    with pytest.raises(TypeError):
        frag.RegenerateParam(feedback="덜 우디하게", prior={"recipe": {}})  # type: ignore[arg-type]
    p = frag.RegenerateParam(feedback="덜 우디하게", prior=frag.FragranceRecipe.from_dict({"notes": [NOTE]}),
                             prior_stamp=Stamp.from_dict(STAMP))
    assert p.prior.notes[0].id == "bergamot"


@pytest.mark.parametrize("gen", [frag, expo, icad])
def test_converse_reply_is_typed_and_keeps_the_wire(gen):
    wire = {"reply": "안녕", "done": False, "result": None, "keywords": [], "history": [["user", "a"]], "stamp": STAMP}
    assert gen.ConverseReply.from_dict(wire).to_dict() == wire
    assert gen.ConverseReply(reply="안녕").to_dict()["stamp"] == {}   # 도장을 모르면 오늘처럼 {}
    with pytest.raises(TypeError):
        gen.ConverseReply(reply="안녕", stamp=STAMP)  # type: ignore[arg-type]


def test_icad_payload_keeps_opaque_blocks_and_requires_note_ids():
    wire = {"is_valid": True, "errors": [], "warnings": [], "name": "저녁 이불", "description": "d", "direction": "우디",
            "recipe": {"notes": [dict(NOTE, id="sandalwood")], "totalVolumeMl": 0.1},
            "emotion": {"group": "recovery"}, "regulatory": {"verdict": "unknown"}, "grounding": {},
            "recipe_icad": {"ingredients": []}, "fragrance_load_pct": 10.0, "_impl": "sensorium/_icad"}
    p = icad.IcadPayload.from_dict(wire)
    assert p.recipe.notes[0].id == "sandalwood" and p.extra == {"_impl": "sensorium/_icad"}
    assert p.to_dict() == wire
    with pytest.raises(ValueError):
        icad.IcadPayload.from_dict({**wire, "recipe": {"notes": [{"name": "Sandalwood"}]}})


def test_stamp_refuses_empty_fields():
    with pytest.raises(ValueError):
        Stamp(model="", mode="rule", released_at="2026-05-28", kernel_version="k")
    with pytest.raises(ValueError):
        Stamp.from_dict({"model": "m"})


# ── 계약 위반 전용 예외 · extra 우회 차단 (2026-09-29 코드리뷰 P2) ─────────────────────────────
from heysenlyt_ai_port import PortContractError  # noqa: E402


def test_port_contract_error_is_backward_compatible():
    # 전용 타입이 생기기 전 `except ValueError`/`except TypeError` 로 잡던 코드가 그대로 잡혀야 한다.
    assert issubclass(PortContractError, ValueError) and issubclass(PortContractError, TypeError)


@pytest.mark.parametrize("mod", [frag, icad], ids=["fragrance", "icad"])
def test_empty_note_id_raises_port_contract_error(mod):
    with pytest.raises(PortContractError):
        mod.RecipeNote(id="  ", name="Bergamot")
    with pytest.raises(PortContractError):
        mod.RecipeNote.from_dict({"name": "Bergamot"})


def test_flavor_item_without_id_raises_port_contract_error():
    with pytest.raises(PortContractError):
        expo.FlavorItem.from_dict({"amount_ml": 1.0})


def test_empty_stamp_raises_port_contract_error():
    with pytest.raises(PortContractError):
        Stamp(model="", mode="rule", released_at="2026-05-28", kernel_version="x")


@pytest.mark.parametrize("make", [
    lambda: frag.RecipeNote(id="a", name="b", extra={"id": ""}),
    lambda: icad.RecipeNote(id="a", name="b", extra={"name": ""}),
    lambda: frag.FragranceRecipe(notes=(), extra={"notes": [{"name": "x"}]}),
    lambda: icad.IcadPayload(is_valid=False, extra={"is_valid": True}),
    lambda: icad.IcadPayload(is_valid=False, extra={"recipe": {"notes": []}}),
    lambda: expo.FlavorItem(id="grape", extra={"channel_id": ""}),
    lambda: expo.FlavorRecipe(extra={"items": []}),
], ids=["note-id", "icad-note-name", "notes", "is_valid", "icad-recipe", "channel_id", "items"])
def test_extra_cannot_override_contract_fields(make):
    with pytest.raises(PortContractError):
        make()


def test_extra_is_detached_from_callers_dict():
    src = {"futureKey": 1}
    note = frag.RecipeNote(id="bergamot", name="Bergamot", extra=src)
    src["id"] = ""  # 만든 뒤 원본을 바꿔도 검증된 값이 덮이지 않는다
    assert note.to_dict()["id"] == "bergamot"


# ── 향연 결과 화면 인용(9/15 사양서 §4-4) — composer_note 는 객체 (2026-09-29) ───────────────────
def test_composer_note_is_an_object_with_required_fields():
    import pytest
    from heysenlyt_ai_port.errors import PortContractError
    from heysenlyt_ai_port.sensorium_icad_0_1_0 import ComposerNote, IcadPayload

    wire = {"is_valid": True, "emotion": {"group": "recovery"},
            "composer_note": {"quote_history_index": 2, "quote": "비 오는 날 창가", "slot": "젖은 창가의 한 장면."}}
    p = IcadPayload.from_dict(wire)
    assert isinstance(p.composer_note, ComposerNote)
    assert p.to_dict()["composer_note"] == wire["composer_note"]
    for bad in ({"quote": "", "quote_history_index": 0, "slot": "s"}, {"quote": "q", "quote_history_index": -1, "slot": "s"},
                {"quote": "q", "quote_history_index": True, "slot": "s"}, {"quote": "q", "slot": "s"}):
        with pytest.raises(PortContractError):
            IcadPayload.from_dict({"is_valid": False, "composer_note": bad})
    with pytest.raises(PortContractError):
        IcadPayload(is_valid=False, composer_note="문자열은 안 된다")  # type: ignore[arg-type]


# ── 파라미터 안의 형식 있는 칸도 클래스 (2026-09-29 · params · hyangyeon · last_known_axes · result · emotion) ────
def test_hyangyeon_context_is_a_class_and_round_trips_the_web_shape():
    import pytest
    from heysenlyt_ai_port.errors import PortContractError
    from heysenlyt_ai_port.sensorium_icad_0_1_0 import ConversationOptions, ConversationParam, HyangyeonContext, HyangyeonPrior

    web = {"hyangyeon": {"round": 2, "final_turn": False, "turn": 3,
                         "prior": {"name": "저녁 이불", "emotion_group": "recovery", "keywords": ["창가", "빗소리"]}}}
    opts = ConversationOptions.from_dict(web)
    assert isinstance(opts.hyangyeon, HyangyeonContext) and isinstance(opts.hyangyeon.prior, HyangyeonPrior)
    assert opts.to_dict() == web
    assert ConversationParam(domain="fragrance", params=opts).params.hyangyeon.turn == 3
    for bad in ({"round": 3}, {"round": 1, "final_turn": "yes"}, {"round": 1, "turn": 0}, {"final_turn": True},
                {"round": 1, "extra": 1}, {"round": 2, "prior": {"name": "a", "last_turns": []}},
                {"round": 2, "prior": {"name": "a", "emotion_group": "슬픔"}}, {"round": 2, "prior": {"keywords": "창가"}}):
        with pytest.raises(PortContractError):
            ConversationOptions.from_dict({"hyangyeon": bad})
    with pytest.raises(PortContractError):
        ConversationOptions.from_dict({"other": 1})
    with pytest.raises(PortContractError):
        ConversationParam(domain="fragrance", params={"hyangyeon": {"round": 1}})  # type: ignore[arg-type]


@pytest.mark.parametrize("gen", ["sensorium_fragrance_1_0_0", "sensorium_expo_0_1_2", "sensorium_icad_0_1_0"])
def test_conversation_param_fields_are_classes(gen):
    import importlib
    from heysenlyt_ai_port.errors import PortContractError

    m = importlib.import_module(f"heysenlyt_ai_port.{gen}")
    axes = m.KnownAxes.from_dict({"scene": "바다", "mood": None})
    assert axes.to_dict() == {"scene": "바다"}
    with pytest.raises(PortContractError):
        m.KnownAxes.from_dict({"scene": "바다", "color": "파랑"})
    with pytest.raises(PortContractError):
        m.ConversationParam(domain="x", last_known_axes={"scene": "바다"})  # type: ignore[arg-type]
    with pytest.raises(PortContractError):
        m.ConversationParam(domain="x", demographics=m.Demographics(age=-1))
    # 대화 결과 — 도구 인자를 클래스로(스키마 밖 키는 extra 로 보존 · 와이어 그대로)
    res = m.ChatResult.from_dict({"story": "s", "unknownKey": 1})
    assert res.to_dict() == {"story": "s", "unknownKey": 1} if gen != "sensorium_expo_0_1_2" else True
    with pytest.raises(PortContractError):
        m.ConverseReply(reply="r", result={"story": "s"})  # type: ignore[arg-type]


def test_recipe_options_are_classes_with_the_adapter_allowlist():
    from heysenlyt_ai_port.errors import PortContractError
    from heysenlyt_ai_port.sensorium_expo_0_1_2 import RecipeOptions as FlavorOptions
    from heysenlyt_ai_port.sensorium_fragrance_1_0_0 import RecipeOptions, RecipeParam

    o = RecipeOptions.from_dict({"name": "저녁", "nameKo": "저녁", "complexity": 6, "ratio": {"TOP": 0.3, "MIDDLE": 0.5, "BASE": 0.2}})
    assert o.to_dict() == {"complexity": 6, "ratio": {"TOP": 0.3, "MIDDLE": 0.5, "BASE": 0.2}, "name": "저녁", "nameKo": "저녁"}
    with pytest.raises(PortContractError, match="허용되지 않는 params"):
        RecipeOptions.from_dict({"evil": 1})
    for bad in ({"complexity": "8"}, {"ratio": {"TOP": "a"}}, {"name": 3}, {"temperature": True}):
        with pytest.raises(PortContractError):
            RecipeOptions.from_dict(bad)
    with pytest.raises(PortContractError):
        RecipeParam("한 문장", params={"complexity": 8})  # type: ignore[arg-type]
    f = FlavorOptions.from_dict({"recent_lead_channels": ["lemon"], "sweet_level": 3})
    assert f.to_dict() == {"sweet_level": 3, "recent_lead_channels": ["lemon"]}
    with pytest.raises(PortContractError, match="허용되지 않는 params"):
        FlavorOptions.from_dict({"complexity": 8})
    with pytest.raises(PortContractError):
        FlavorOptions.from_dict({"recent_lead_channels": "lemon"})


def test_icad_emotion_is_a_class_and_valid_payload_needs_a_group():
    from heysenlyt_ai_port.errors import PortContractError
    from heysenlyt_ai_port.sensorium_icad_0_1_0 import ComposeOptions, ComposeParam, ComposeTurn, IcadEmotion, IcadPayload

    e = IcadEmotion.from_dict({"id": "recovery", "group": "recovery", "margin": 0.5, "scores": {"recovery": 1}})
    assert e.to_dict() == {"group": "recovery", "id": "recovery", "margin": 0.5, "scores": {"recovery": 1}}
    assert IcadPayload.from_dict({"is_valid": False, "emotion": {}}).to_dict()["emotion"] == {}
    for bad in ({"group": "슬픔"}, {"group": 1}, {"margin": "0.5"}):
        with pytest.raises(PortContractError):
            IcadEmotion.from_dict(bad)
    with pytest.raises(PortContractError):
        IcadPayload(is_valid=True)
    with pytest.raises(PortContractError):
        IcadPayload(is_valid=True, emotion={"group": "recovery"})  # type: ignore[arg-type]
    with pytest.raises(PortContractError):
        ComposeOptions.from_dict({"temperature": 0.5})
    with pytest.raises(PortContractError):
        ComposeParam(history=(ComposeTurn("system", "x"),))
    with pytest.raises(PortContractError):
        ComposeParam(history=[ComposeTurn("user", "x")])  # type: ignore[arg-type]


# ── 남은 dict 칸 클래스화 (2026-09-29) — ratio · 식향 계열/특수향 ────────────────────────────
def test_layer_ratio_is_a_class_and_roundtrips():
    import pytest
    from heysenlyt_ai_port.errors import PortContractError
    from heysenlyt_ai_port.sensorium_fragrance_1_0_0 import LayerRatio, RecipeOptions

    o = RecipeOptions.from_dict({"ratio": {"TOP": 0.3, "BASE": 0.2}, "complexity": 8})
    assert isinstance(o.ratio, LayerRatio) and o.ratio.middle is None
    assert o.to_dict() == {"complexity": 8, "ratio": {"TOP": 0.3, "BASE": 0.2}}
    for bad in ({"ratio": {"TOP": "x"}}, {"ratio": {"LOW": 1}}, {"ratio": {"TOP": True}}):
        with pytest.raises(PortContractError):
            RecipeOptions.from_dict(bad)
    with pytest.raises(PortContractError):
        RecipeOptions(ratio={"TOP": 0.3})  # type: ignore[arg-type]  — dict 는 안 된다


def test_flavor_families_and_special_aromas_are_typed():
    import pytest
    from heysenlyt_ai_port.errors import PortContractError
    from heysenlyt_ai_port.sensorium_expo_0_1_2 import FlavorRecipe, SpecialAroma

    wire = {"families": {"citrus": 5.0, "grape": 1.0}, "familyLabels": {"citrus": "시트러스"},
            "specialAromas": [{"id": "rose", "name": "장미", "amount_ml": 0.1}], "items": []}
    r = FlavorRecipe.from_dict(wire)
    assert isinstance(r.special_aromas[0], SpecialAroma)
    assert r.to_dict() == wire
    for bad in ({"families": {"citrus": "5"}}, {"familyLabels": {"citrus": 1}},
                {"specialAromas": [{"id": "rose", "name": "장미"}]}, {"specialAromas": "rose"}):
        with pytest.raises(PortContractError):
            FlavorRecipe.from_dict(bad)


def test_string_list_fields_do_not_split_a_single_string():
    """errors·warnings·result_keywords 에 문자열 하나가 오면 한 항목 — 글자로 쪼개지 않는다(9/29 검증 P3)."""
    from heysenlyt_ai_port.sensorium_icad_0_1_0 import IcadPayload

    p = IcadPayload.from_dict({"is_valid": False, "errors": "boom", "warnings": "w"})
    assert p.errors == ("boom",) and p.warnings == ("w",)
    assert IcadPayload(is_valid=False, result_keywords="창가").result_keywords == ("창가",)  # type: ignore[arg-type]
