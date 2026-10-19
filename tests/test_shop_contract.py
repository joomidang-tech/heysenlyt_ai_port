"""sensorium-shop-0.1.0 — 센릿샵 계약 잠금(HoS AI PRD · 2026-10-19). 넘길 것은 전부 파라미터로 · 받을 것은 전부 응답으로 · 클래스로."""
from __future__ import annotations

import dataclasses

import pytest

from heysenlyt_ai_port import PortContractError, Stamp
from heysenlyt_ai_port import sensorium_shop_0_1_0 as shop

STAMP = Stamp(model="m", mode="rule", released_at="2026-10-19", kernel_version="sensorium-shop-0.1.0")
BRIEF = {"purpose": "매장 입구 공간향", "feel": "차분한 마른 나무", "avoid": ["단 향"], "liked": [], "weight": "light",
         "occasion": None, "inferred": []}
REVISE = {"originalRequest": "매장 입구 향", "recipeName": "차분한 나무", "latestReaction": "dislike",
          "recipeDescription": "마른 나무 향", "composerNote": "단 향은 싫다고 하셔서 뺐어요.", "noteNames": ["시더우드"],
          "brief": BRIEF, "reactions": ["like", "dislike"]}
OPTS = {"palette": ["cedarwood"], "aiTurn": 2, "recipeButtonAiTurn": 4}


def test_ports_are_recipe_and_conversation_only():
    assert set(shop.PORTS) == {"recipe", "conversation"}
    assert not hasattr(shop.RecipePort, "regenerate")  # 수정본도 generate(새 레시피)


def test_turn_is_a_class_and_accepts_both_wire_shapes():
    assert shop.Turn.from_wire(["user", "hi"]) == shop.Turn.from_wire({"role": "user", "content": "hi"}) == shop.Turn("user", "hi")
    assert shop.Turn("assistant", "x").to_wire() == ["assistant", "x"]
    with pytest.raises(PortContractError):
        shop.Turn("system", "x")
    with pytest.raises(PortContractError):
        shop.Turn.from_wire({"role": "user", "content": "x", "extra": 1})


def test_scent_brief_separates_unknown_from_none_answer():
    unknown = shop.ScentBrief()
    said_none = shop.ScentBrief(avoid=())
    assert unknown.avoid is None and said_none.avoid == () and unknown != said_none
    b = shop.ScentBrief.from_dict(BRIEF)
    assert b.required_collected == 3 and shop.ScentBrief.from_dict(b.to_dict()) == b
    with pytest.raises(PortContractError):
        shop.ScentBrief(weight="very heavy")
    with pytest.raises(PortContractError):
        shop.ScentBrief(inferred=("gender",))
    with pytest.raises(PortContractError):
        shop.ScentBrief.from_dict({**BRIEF, "concentration": "EDP"})


def test_conversation_options_require_everything_the_adapter_needs():
    o = shop.ConversationOptions.from_dict({**OPTS, "revise": REVISE, "openingQuestion": "어떤 점이 아쉬웠나요?"})
    assert o.palette.notes == ("cedarwood",) and o.ai_turn == 2 and not o.recipe_button_visible
    assert o.revise.brief.avoid == ("단 향",)
    assert shop.ConversationOptions.from_dict(o.to_dict()) == o
    for missing in ("palette", "aiTurn", "recipeButtonAiTurn"):
        with pytest.raises(PortContractError):
            shop.ConversationOptions.from_dict({k: v for k, v in OPTS.items() if k != missing})
    with pytest.raises(PortContractError):
        shop.ConversationOptions.from_dict({**OPTS, "aiTurn": 0})
    unknown = shop.ConversationOptions.from_dict({**OPTS, "palette": None})  # 키는 필수 · 값 None = 모름(조회 실패)
    assert unknown.palette is None and unknown.to_dict()["palette"] is None
    with pytest.raises(PortContractError):
        shop.ConversationOptions.from_dict({**OPTS, "hyangyeon": {}})


def test_conversation_param_has_harness_fields_and_typed_history():
    p = shop.ConversationParam(domain="fragrance", params=shop.ConversationOptions.from_dict(OPTS),
                               message="m", history=(["assistant", "a"],))
    assert p.history == (shop.Turn("assistant", "a"),)
    assert dataclasses.replace(p, require_text=True).require_text is True


def test_converse_reply_requires_brief_and_stamp_and_keeps_wire_shape():
    rep = shop.ConverseReply(reply="안녕하세요", result=shop.ScentBrief(purpose="공간"), stamp=STAMP,
                             history=(shop.Turn("assistant", "안녕하세요"),))
    w = rep.to_dict()
    assert set(w) == {"reply", "done", "result", "keywords", "history", "stamp"}
    assert w["history"] == [["assistant", "안녕하세요"]]
    assert shop.ConverseReply.from_dict(w) == rep
    with pytest.raises(PortContractError):
        shop.ConverseReply.from_dict({**w, "result": None})


def test_revise_context_requires_core_and_rejects_amounts():
    with pytest.raises(PortContractError):
        shop.ReviseContext.from_dict({"recipeName": "x"})
    with pytest.raises(PortContractError):
        shop.ReviseContext.from_dict({**REVISE, "latestReaction": "meh"})
    with pytest.raises(PortContractError):
        shop.ReviseContext.from_dict({**REVISE, "amountMl": 1})
    r = shop.ReviseContext.from_dict(REVISE)
    assert shop.ReviseContext.from_dict(r.to_dict()) == r


def test_recipe_options_require_conversation_and_carry_taken_names():
    a = shop.RecipeOptions.from_dict({"conversation": [["user", "hi"], {"role": "assistant", "content": "yo"}],
                                      "takenNames": ["차분한 나무"]})
    assert a.conversation == (shop.Turn("user", "hi"), shop.Turn("assistant", "yo")) and a.taken_names == ("차분한 나무",)
    with pytest.raises(PortContractError):
        shop.RecipeOptions.from_dict({"conversation": []})
    with pytest.raises(PortContractError):
        shop.RecipeOptions.from_dict({"conversation": [["system", "x"]]})
    with pytest.raises(PortContractError):
        shop.RecipeOptions.from_dict({"conversation": [["user", "x"]], "prompt": "x"})


def test_recipe_requires_brief_and_wire_carries_everything_integration_uses():
    r = shop.ShopRecipe(name="차분한 나무", description="마른 나무의 담백함에 온기를 더한 향", composer_note="…",
                        brief=shop.ScentBrief(purpose="공간", feel="차분", avoid=(), inferred=("avoid",)),
                        notes=(shop.RecipeNote(id="cedarwood", name="Cedarwood", amount_ml=0.1, type="middle"),))
    reply = shop.RecipeReply(domain="fragrance", version="0.1.0", stamp=STAMP, recipe=r)
    w = reply.to_dict()
    assert {"name", "description", "composerNote", "brief", "notes"} <= set(w["recipe"])
    assert w["recipe"]["brief"]["avoid"] == [] and w["recipe"]["brief"]["inferred"] == ["avoid"]
    assert shop.RecipeReply.from_dict(w) == reply
    bad = {**w["recipe"]}
    bad.pop("brief")
    with pytest.raises(PortContractError):
        shop.ShopRecipe.from_dict(bad)
    with pytest.raises(PortContractError):
        shop.RecipeNote(id="", name="x")


def test_recipe_param_requires_options_and_palette():
    opts = shop.RecipeOptions.from_dict({"conversation": [["user", "x"]]})
    shop.RecipeParam(prompt="x", params=opts, palette=shop.Palette(notes=("cedarwood",)))
    assert shop.RecipeParam(prompt="x", params=opts, palette=None).palette is None  # 모름 ≠ 없음
    with pytest.raises(TypeError):
        shop.RecipeParam(prompt="x", params=opts)  # type: ignore[call-arg]


# ── 길이 상한(비용·DoS) — 경계값은 통과 · 한 칸 넘으면 PortContractError (2026-10-19 검증 반영) ──────────────
from heysenlyt_ai_port.sensorium_shop_0_1_0 import conversation as _conv_mod  # noqa: E402
from heysenlyt_ai_port.sensorium_shop_0_1_0 import recipe as _recipe_mod  # noqa: E402


def test_turn_content_cap_4000():
    shop.Turn("user", "가" * 4000)
    with pytest.raises(PortContractError):
        shop.Turn("user", "가" * 4001)


def test_history_and_conversation_cap_100_turns():
    opts = shop.ConversationOptions.from_dict(OPTS)
    turns = [["user", "x"]] * 100
    shop.ConversationParam(domain="fragrance", params=opts, history=tuple(turns))
    shop.RecipeOptions.from_dict({"conversation": turns})
    with pytest.raises(PortContractError):
        shop.ConversationParam(domain="fragrance", params=opts, history=tuple(turns + [["user", "x"]]))
    with pytest.raises(PortContractError):
        shop.RecipeOptions.from_dict({"conversation": turns + [["user", "x"]]})


@pytest.mark.parametrize("key,limit", [("originalRequest", 1500), ("composerNote", 700), ("recipeName", 40),
                                       ("recipeDescription", 300)])
def test_revise_text_caps(key, limit):
    shop.ReviseContext.from_dict({**REVISE, key: "a" * limit})
    with pytest.raises(PortContractError):
        shop.ReviseContext.from_dict({**REVISE, key: "a" * (limit + 1)})


def test_revise_note_names_cap_60():
    shop.ReviseContext.from_dict({**REVISE, "noteNames": ["n"] * 60})
    with pytest.raises(PortContractError):
        shop.ReviseContext.from_dict({**REVISE, "noteNames": ["n"] * 61})


@pytest.mark.parametrize("key", ["purpose", "feel", "occasion"])
def test_brief_text_caps_200(key):
    shop.ScentBrief(**{key: "a" * 200})
    with pytest.raises(PortContractError):
        shop.ScentBrief(**{key: "a" * 201})


@pytest.mark.parametrize("key", ["avoid", "liked"])
def test_brief_list_caps_20_items_200_chars(key):
    shop.ScentBrief(**{key: tuple(["a" * 200] * 20)})
    with pytest.raises(PortContractError):
        shop.ScentBrief(**{key: tuple(["a"] * 21)})
    with pytest.raises(PortContractError):
        shop.ScentBrief(**{key: ("a" * 201,)})


def test_taken_names_caps_500_items_40_chars():
    conv = [["user", "x"]]
    shop.RecipeOptions.from_dict({"conversation": conv, "takenNames": ["a" * 40] * 500})
    with pytest.raises(PortContractError):
        shop.RecipeOptions.from_dict({"conversation": conv, "takenNames": ["a"] * 501})
    with pytest.raises(PortContractError):
        shop.RecipeOptions.from_dict({"conversation": conv, "takenNames": ["a" * 41]})
    assert _recipe_mod.MAX_TAKEN_NAMES == 500 and _recipe_mod.MAX_TAKEN_NAME_CHARS == 40


def test_opening_question_cap_200():
    shop.ConversationOptions.from_dict({**OPTS, "openingQuestion": "q" * 200})
    with pytest.raises(PortContractError):
        shop.ConversationOptions.from_dict({**OPTS, "openingQuestion": "q" * 201})
    assert _conv_mod.MAX_OPENING_QUESTION_CHARS == 200


# ── 포트 엄격성 ──────────────────────────────────────────────────────────────────────────────
def test_latest_reaction_null_is_none():
    assert shop.ReviseContext.from_dict({**REVISE, "latestReaction": None}).latest_reaction == "none"
    no_key = {k: v for k, v in REVISE.items() if k != "latestReaction"}
    assert shop.ReviseContext.from_dict(no_key).latest_reaction == "none"


def test_recipe_reply_requires_is_valid_bool():
    r = shop.ShopRecipe(name="n", description="d", composer_note="c", brief=shop.ScentBrief())
    w = shop.RecipeReply(domain="fragrance", version="0.1.0", stamp=STAMP, recipe=r, is_valid=False).to_dict()
    w.pop("is_valid")
    with pytest.raises(PortContractError):
        shop.RecipeReply.from_dict(w)  # 빠지면 「성공」으로 간주하지 않는다
    with pytest.raises(PortContractError):
        shop.RecipeReply.from_dict({**w, "is_valid": "yes"})
    assert shop.RecipeReply.from_dict({**w, "is_valid": False}).is_valid is False


def test_converse_reply_result_must_not_carry_inferred():
    with pytest.raises(PortContractError):
        shop.ConverseReply(reply="r", result=shop.ScentBrief(purpose="p", inferred=("purpose",)), stamp=STAMP)
    w = shop.ConverseReply(reply="r", result=shop.ScentBrief(purpose="p"), stamp=STAMP).to_dict()
    w["result"]["inferred"] = ["purpose"]
    with pytest.raises(PortContractError):
        shop.ConverseReply.from_dict(w)


def test_palette_validates_and_coerces():
    assert shop.Palette(notes=["a", "b"]).notes == ("a", "b")  # list → tuple
    for bad in ("ab", ("a", ""), ("a", 1), None, ("  ",)):
        with pytest.raises(PortContractError):
            shop.Palette(notes=bad)  # type: ignore[arg-type]
    from heysenlyt_ai_port import sensorium_fragrance_1_0_0 as frag
    assert frag.Palette is not shop.Palette  # 다른 세대의 Palette 는 별개 클래스(손대지 않는다)


def test_shop_port_docstrings_carry_no_internal_paths():
    """public 레포 — 내부 파일 경로(기획 문서·통합코드 모듈)를 계약 문구에 싣지 않는다."""
    import pathlib
    import re

    root = pathlib.Path(shop.__file__).parent
    for f in root.glob("*.py"):
        text = f.read_text(encoding="utf-8")
        assert not re.search(r"(planner|developer|ai-developer)/|application/\w+\.py|\.md\b", text), f.name


# ── 2026-10-19 칸 둘(관호님 워크오더 「향료 id 33종」 §7) — 직전 요점 회송 · 👎 이유 ─────────────────────────────

def test_conversation_options_round_trips_previous_brief():
    from heysenlyt_ai_port.sensorium_shop_0_1_0.conversation import ConversationOptions
    from heysenlyt_ai_port.sensorium_shop_0_1_0.revise import ScentBrief

    wire = {"palette": ["cedarwood"], "aiTurn": 2, "recipeButtonAiTurn": 4,
            "brief": {"purpose": "매장 입구", "feel": None, "avoid": [], "liked": None, "weight": None,
                      "occasion": None, "inferred": []}}
    o = ConversationOptions.from_dict(wire)
    assert isinstance(o.brief, ScentBrief) and o.brief.purpose == "매장 입구" and o.brief.avoid == ()
    assert o.to_dict()["brief"]["purpose"] == "매장 입구"
    # 없으면 키도 없다(첫 턴 · 오늘 와이어 그대로)
    assert "brief" not in ConversationOptions.from_dict({"palette": None, "aiTurn": 1, "recipeButtonAiTurn": 4}).to_dict()
    assert ConversationOptions.from_dict({"palette": None, "aiTurn": 1, "recipeButtonAiTurn": 4, "brief": None}).brief is None


def test_conversation_options_rejects_malformed_brief():
    import pytest

    from heysenlyt_ai_port.errors import PortContractError
    from heysenlyt_ai_port.sensorium_shop_0_1_0.conversation import ConversationOptions

    for bad in ("요점", {"purpose": "x" * 201}, {"unknown": 1}):
        with pytest.raises(PortContractError):
            ConversationOptions.from_dict({"palette": None, "aiTurn": 1, "recipeButtonAiTurn": 4, "brief": bad})


def test_revise_context_reaction_reasons_optional_and_capped():
    import pytest

    from heysenlyt_ai_port.errors import PortContractError
    from heysenlyt_ai_port.sensorium_shop_0_1_0.revise import ReviseContext

    base = {"originalRequest": "마른 나무", "recipeName": "차분한 나무"}
    assert ReviseContext.from_dict(base).reaction_reasons == ()
    r = ReviseContext.from_dict({**base, "latestReaction": "dislike", "reactionReasons": ["너무 달아요"]})
    assert r.reaction_reasons == ("너무 달아요",) and r.to_dict()["reactionReasons"] == ["너무 달아요"]
    for bad in (["x" * 201], ["a"] * 21, "너무 달아요"):
        with pytest.raises(PortContractError):
            ReviseContext.from_dict({**base, "reactionReasons": bad})
