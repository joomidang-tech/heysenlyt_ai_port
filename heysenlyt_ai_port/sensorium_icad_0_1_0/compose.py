"""sensorium-icad-0.1.0 — 향연 compose 계약. 의존성 0.

⛔ 이 파일은 **이 세대만의 계약**이다(2026-09-27 세대 축 개편). 다른 세대와 내용이 같아 보여도 공유하지 않는다 —
   세대가 갈릴 때 옛 세대 계약을 건드리지 않기 위해 처음부터 세대 폴더 안에 둔다. 세대끼리 import 금지(tests/test_shape.py).
   세대 무관 계약(LlmPort · 실패 어휘 · VersionPort)만 패키지 최상위에 있다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from heysenlyt_ai_port.errors import PortContractError
from heysenlyt_ai_port.llm import LlmPort
from heysenlyt_ai_port.version import Stamp, VersionPort  # get_version() 도 추상 메서드 — 무조건 구현(2026-09-27)



def _str_tuple(v: Any) -> tuple[str, ...]:
    """문자열 목록 칸 정규화 — 문자열 하나가 오면 글자로 쪼개지 않고 한 항목으로(9/29 검증 P3)."""
    if v is None:
        return ()
    if isinstance(v, str):
        return (v,)
    return tuple(str(x) for x in v)

# ## 레시피 모양 — 클래스로 강제한다 (2026-09-29)
#
# 포트는 인터페이스라 **파라미터·리턴이 전부 클래스**다. 레시피를 dict 로 주고받던 동안에는 어댑터가 무엇을 빼먹어도
#   포트가 몰랐고, 통합코드가 응답을 받은 뒤에야(또는 web 주문 접수에서야) 알았다.
#
# ⛔ **향료 한 줄의 `id` 는 필수다.** 향료를 부르는 이름(name·nameKo…)과 향료를 가리키는 id 를 **분리**한다(9/29 합의).
#   · id   = 매핑·판정 전용. 팔레트 키 · 레시피 `notes[].id` · web 포트 매핑이 **같은 문자열**이다.
#   · name = 화면 표시 전용. 바뀌어도(괄호·표기·언어) 매핑이 깨지지 않는다.
#   id 가 비면 `RecipeNote` 를 만드는 순간 PortContractError(ValueError·TypeError 하위) — 레시피가 조용히 web 까지 가서 접수 409 로 터지지 않는다.
#
# 와이어(JSON) 키는 지금 그대로다(camelCase) — `to_dict()` 가 오늘과 같은 모양을 내고, 새 키는 `id` 하나뿐이다.
#   계약에 이름이 없는 키는 `extra` 에 **보존**한다(엔진이 더 싣는 값을 포트가 삼키지 않게).
#   None 인 칸은 `to_dict()` 에서 **생략**한다 — "없었다"와 "빈 값이었다"를 와이어에서 구분하기 위해서다.

_NOTE_KEYS = {  # 와이어 키 → 필드명
    "id": "id", "name": "name", "nameKo": "name_ko", "nameJa": "name_ja",
    "amountMl": "amount_ml", "percent": "percent", "type": "type",
    "description": "description", "descriptionKo": "description_ko", "descriptionJa": "description_ja",
}
_RECIPE_KEYS = {
    "name": "name", "nameKo": "name_ko", "nameJa": "name_ja",
    "story": "story", "storyKo": "story_ko", "storyJa": "story_ja",
    "totalVolumeMl": "total_volume_ml",
}


def _freeze_extra(obj: Any, known: set[str] | frozenset[str]) -> None:
    """`extra` 검사 — 계약 밖 키만 담는다. **알려진 와이어 키와 겹치면 PortContractError** (2026-09-29 코드리뷰 P2).

    `to_dict()` 는 마지막에 extra 를 덧붙이므로, 겹치는 키를 허용하면 검증된 필드(예 `id`·`is_valid`)를 extra 가
    덮어써 불변식이 우회된다. 겹침을 막고, 밖에서 원본 dict 를 바꿔도 따라 바뀌지 않게 사본으로 떼어 둔다.
    """
    extra = getattr(obj, "extra")
    if not isinstance(extra, Mapping):
        raise PortContractError(f"{type(obj).__name__}.extra 는 Mapping 이어야 한다({type(extra).__name__})")
    clash = sorted(set(extra) & set(known))
    if clash:
        raise PortContractError(f"{type(obj).__name__}.extra 가 계약 필드와 겹친다: {clash}")
    object.__setattr__(obj, "extra", dict(extra))


@dataclass(frozen=True)
class RecipeNote:
    """레시피의 향료 한 줄.

    id        : 향료 id — **필수 · 비면 PortContractError.** 향연 = ICAD `material_id`(정규화: 공백 제거·소문자·NFC).
    name      : 표시명(엔진 카탈로그 이름) — 필수.
    amount_ml : 이 향료의 양(**mL**). 단위를 바꾸면 1000배 오토출이다.
    percent   : 레시피 안 비율(%).
    type      : "top" | "middle" | "base".
    extra     : 계약 밖 키(보존만 한다).
    """

    id: str
    name: str
    amount_ml: float | None = None
    percent: float | None = None
    type: str | None = None
    name_ko: str | None = None
    name_ja: str | None = None
    description: str | None = None
    description_ko: str | None = None
    description_ja: str | None = None
    extra: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _freeze_extra(self, set(_NOTE_KEYS))
        if not isinstance(self.id, str) or not self.id.strip():
            raise PortContractError(f"RecipeNote.id 는 비어 있지 않은 문자열이어야 한다(향료 id · 이름과 분리): {self.id!r}")
        if not isinstance(self.name, str) or not self.name.strip():
            raise PortContractError(f"RecipeNote.name 은 비어 있지 않은 문자열이어야 한다: {self.name!r}")

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "RecipeNote":
        if not isinstance(d, Mapping):
            raise PortContractError(f"RecipeNote.from_dict: Mapping 이 아니다({type(d).__name__})")
        if "id" not in d:
            raise PortContractError(f"RecipeNote.from_dict: 필수 키 'id' 누락(name={d.get('name')!r})")
        known = {field_name: d[wire] for wire, field_name in _NOTE_KEYS.items() if wire in d}
        extra = {k: v for k, v in d.items() if k not in _NOTE_KEYS}
        return cls(**known, extra=extra)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for wire, field_name in _NOTE_KEYS.items():
            v = getattr(self, field_name)
            if v is not None:
                out[wire] = v
        out.update(self.extra)
        return out


@dataclass(frozen=True)
class FragranceRecipe:
    """향장향 레시피 — web 이 읽는 FragranceResult 형상.

    notes           : 향료 줄들(RecipeNote). 무효 레시피는 빈 튜플.
    total_volume_ml : 향료 총량(**mL**).
    name·story(+Ko·Ja) : 결과 카드 이름·스토리.
    extra           : 계약 밖 키(보존만 한다).
    """

    notes: tuple[RecipeNote, ...] | None = None
    total_volume_ml: float | None = None
    name: str | None = None
    name_ko: str | None = None
    name_ja: str | None = None
    story: str | None = None
    story_ko: str | None = None
    story_ja: str | None = None
    extra: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _freeze_extra(self, set(_RECIPE_KEYS) | {"notes"})
        if self.notes is not None:
            notes = tuple(self.notes)
            bad = [type(n).__name__ for n in notes if not isinstance(n, RecipeNote)]
            if bad:
                raise PortContractError(f"FragranceRecipe.notes 는 RecipeNote 여야 한다: {bad}")
            object.__setattr__(self, "notes", notes)

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "FragranceRecipe":
        if not isinstance(d, Mapping):
            raise PortContractError(f"FragranceRecipe.from_dict: Mapping 이 아니다({type(d).__name__})")
        known: dict[str, Any] = {field_name: d[wire] for wire, field_name in _RECIPE_KEYS.items() if wire in d}
        if "notes" in d:
            raw = d["notes"]
            if not isinstance(raw, (list, tuple)):
                raise PortContractError(f"FragranceRecipe.from_dict: notes 가 리스트가 아니다({type(raw).__name__})")
            known["notes"] = tuple(RecipeNote.from_dict(n) for n in raw)
        extra = {k: v for k, v in d.items() if k not in _RECIPE_KEYS and k != "notes"}
        return cls(**known, extra=extra)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for wire, field_name in _RECIPE_KEYS.items():
            v = getattr(self, field_name)
            if v is not None:
                out[wire] = v
        if self.notes is not None:
            out["notes"] = [n.to_dict() for n in self.notes]
        out.update(self.extra)
        return out


@dataclass(frozen=True)
class ComposerNote:
    """결과 화면 조향노트의 인용(9/15 사양서 §4-4) — 참가자 발화 원문 한 문장 + AI 한 문장.

    quote               : 참가자 발화 **원문 그대로**(web 이 `history[quote_history_index]` 와 완전 일치로 검증).
    quote_history_index : 요청 `ComposeParam.history` 에서 그 발화의 인덱스(0 이상 정수).
    slot                : 조향노트 본문(기획 AI PRD §5 — 4턴 이탈 4-5문장 ≤100자 · 10턴 완주 5-7문장 ≤140자 ·
                          향료명·계열명·감정군·효능 문구 금지). 사양서 초안의 "≤80자 한 문장"은 PRD 가 대체했다.
    """

    quote: str
    quote_history_index: int
    slot: str

    def __post_init__(self) -> None:
        if not isinstance(self.quote, str) or not self.quote.strip():
            raise PortContractError("ComposerNote.quote 는 비어 있지 않은 문자열이어야 한다")
        if isinstance(self.quote_history_index, bool) or not isinstance(self.quote_history_index, int) or self.quote_history_index < 0:
            raise PortContractError(f"ComposerNote.quote_history_index 는 0 이상 정수여야 한다({self.quote_history_index!r})")
        if not isinstance(self.slot, str) or not self.slot.strip():
            raise PortContractError("ComposerNote.slot 은 비어 있지 않은 문자열이어야 한다")

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "ComposerNote":
        if not isinstance(d, Mapping):
            raise PortContractError(f"ComposerNote.from_dict: Mapping 이 아니다({type(d).__name__})")
        for k in ("quote", "quote_history_index", "slot"):
            if k not in d:
                raise PortContractError(f"ComposerNote.from_dict: 필수 키 '{k}' 누락")
        return cls(quote=d["quote"], quote_history_index=d["quote_history_index"], slot=d["slot"])

    def to_dict(self) -> dict[str, Any]:
        return {"quote_history_index": self.quote_history_index, "quote": self.quote, "slot": self.slot}


# ## 향연 감정 라벨 — 클래스 (2026-09-29 · Mapping → IcadEmotion)
_EMOTION_GROUPS = ("recovery", "balance", "vitality", "focus", "connection")
_EMOTION_KEYS = ("group", "id", "ko", "description", "runner_up", "margin")


@dataclass(frozen=True)
class IcadEmotion:
    """결과 카드의 감정 라벨. 유효 결과(`IcadPayload.is_valid=True`)면 `group` 이 5군 중 하나여야 한다.

    group       : 감정군 id(recovery · balance · vitality · focus · connection) — web 이 읽는 칸.
    id · ko · description · runner_up · margin : 엔진 라벨 산출(표시·로그용).
    extra       : 계약 밖 키(예 `scores`) — 보존하되 통합코드가 무엇을 내보낼지 고른다(점수는 내보내지 않는다).
    빈 라벨(무효 결과의 `{}`)은 모든 칸 None.
    """

    group: str | None = None
    id: str | None = None
    ko: str | None = None
    description: str | None = None
    runner_up: str | None = None
    margin: float | None = None
    extra: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _freeze_extra(self, set(_EMOTION_KEYS))
        for f in ("group", "id", "ko", "description", "runner_up"):
            v = getattr(self, f)
            if v is not None and not isinstance(v, str):
                raise PortContractError(f"IcadEmotion.{f} 는 문자열이어야 한다({type(v).__name__})")
        if self.group is not None and self.group not in _EMOTION_GROUPS:
            raise PortContractError(f"IcadEmotion.group 은 5군 중 하나여야 한다({self.group!r})")
        if self.margin is not None and (isinstance(self.margin, bool) or not isinstance(self.margin, (int, float))):
            raise PortContractError(f"IcadEmotion.margin 은 숫자여야 한다({self.margin!r})")

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "IcadEmotion":
        if not isinstance(d, Mapping):
            raise PortContractError(f"IcadEmotion.from_dict: Mapping 이 아니다({type(d).__name__})")
        known = {k: d[k] for k in _EMOTION_KEYS if d.get(k) is not None}
        return cls(**known, extra={k: v for k, v in d.items() if k not in _EMOTION_KEYS})

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {k: getattr(self, k) for k in _EMOTION_KEYS if getattr(self, k) is not None}
        out.update(self.extra)
        return out


# ## 향연 결과 payload — 클래스 (2026-09-29)
_PAYLOAD_KEYS = {  # 와이어 키 → 필드명 (recipe·emotion 등 구조 칸은 따로 다룬다)
    "is_valid": "is_valid", "name": "name", "description": "description", "direction": "direction",
    "fragrance_load_pct": "fragrance_load_pct",
}
_PAYLOAD_MAPS = ("grounding", "regulatory", "recipe_icad")  # 내부 형상 불투명 — Mapping 그대로(보고서·원본 보존용)


@dataclass(frozen=True)
class IcadPayload:
    """향연 compose 결과(결과 카드) — web 이 읽는 키만 필드로 두고 나머지는 extra 로 보존한다.

    is_valid : 만들었나(필수). False 면 errors 에 사유가 있어야 한다.
    recipe   : FragranceRecipe — 향료 줄마다 **id 필수**(향연 = ICAD `material_id`).
    emotion·grounding·regulatory·recipe_icad : 내부 형상이 불투명한 칸(Mapping 그대로 · 포트는 단정하지 않는다).
    """

    is_valid: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    name: str | None = None
    description: str | None = None
    direction: str | None = None
    recipe: FragranceRecipe | None = None
    emotion: IcadEmotion | None = None  # (2026-09-29) Mapping → IcadEmotion
    grounding: Mapping[str, Any] | None = None
    regulatory: Mapping[str, Any] | None = None
    recipe_icad: Mapping[str, Any] | None = None
    fragrance_load_pct: float | None = None
    result_keywords: tuple[str, ...] | None = None
    composer_note: ComposerNote | None = None  # 9/15 사양서 §4-4 — 객체(quote·quote_history_index·slot)
    extra: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _freeze_extra(self, set(_PAYLOAD_KEYS) | set(_PAYLOAD_MAPS) | {"recipe", "errors", "warnings", "result_keywords", "composer_note", "emotion"})
        if not isinstance(self.is_valid, bool):
            raise PortContractError(f"IcadPayload.is_valid 는 bool 이어야 한다({type(self.is_valid).__name__})")
        if self.recipe is not None and not isinstance(self.recipe, FragranceRecipe):
            raise PortContractError(f"IcadPayload.recipe 는 FragranceRecipe 여야 한다({type(self.recipe).__name__})")
        object.__setattr__(self, "errors", _str_tuple(self.errors))
        object.__setattr__(self, "warnings", _str_tuple(self.warnings))
        if self.result_keywords is not None:
            object.__setattr__(self, "result_keywords", _str_tuple(self.result_keywords))
        if self.emotion is not None and not isinstance(self.emotion, IcadEmotion):
            raise PortContractError(f"IcadPayload.emotion 은 IcadEmotion 이어야 한다({type(self.emotion).__name__})")
        if self.is_valid and (self.emotion is None or self.emotion.group is None):
            raise PortContractError("IcadPayload: 유효 결과(is_valid=True)는 emotion.group(5군)이 있어야 한다")
        if self.composer_note is not None and not isinstance(self.composer_note, ComposerNote):
            raise PortContractError(f"IcadPayload.composer_note 는 ComposerNote 여야 한다({type(self.composer_note).__name__})")

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "IcadPayload":
        if not isinstance(d, Mapping):
            raise PortContractError(f"IcadPayload.from_dict: Mapping 이 아니다({type(d).__name__})")
        if "is_valid" not in d:
            raise PortContractError("IcadPayload.from_dict: 필수 키 'is_valid' 누락")
        known: dict[str, Any] = {f: d[w] for w, f in _PAYLOAD_KEYS.items() if w in d}
        for k in _PAYLOAD_MAPS:
            if k in d:
                known[k] = d[k]
        if "recipe" in d:
            known["recipe"] = FragranceRecipe.from_dict(d["recipe"])
        for k in ("errors", "warnings", "result_keywords"):
            if k in d:
                known[k] = _str_tuple(d[k])
        if d.get("emotion") is not None:
            known["emotion"] = IcadEmotion.from_dict(d["emotion"])
        if d.get("composer_note") is not None:
            known["composer_note"] = ComposerNote.from_dict(d["composer_note"])
        handled = set(_PAYLOAD_KEYS) | set(_PAYLOAD_MAPS) | {"recipe", "errors", "warnings", "result_keywords", "composer_note", "emotion"}
        extra = {k: v for k, v in d.items() if k not in handled}
        return cls(**known, extra=extra)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"is_valid": self.is_valid, "errors": list(self.errors), "warnings": list(self.warnings)}
        for w, f in _PAYLOAD_KEYS.items():
            v = getattr(self, f)
            if v is not None and w not in out:
                out[w] = v
        for k in _PAYLOAD_MAPS:
            v = getattr(self, k)
            if v is not None:
                out[k] = dict(v)
        if self.emotion is not None:
            out["emotion"] = self.emotion.to_dict()
        if self.recipe is not None:
            out["recipe"] = self.recipe.to_dict()
        if self.result_keywords is not None:
            out["result_keywords"] = list(self.result_keywords)
        if self.composer_note is not None:
            out["composer_note"] = self.composer_note.to_dict()
        out.update(self.extra)
        return out


# ## Palette — 이번 요청에서 **쓸 수 있는 향료** (2026-09-20 신설 · 2026-09-27 세대 폴더 안으로)
# 
# ## 왜 필요한가 — 엔진은 기기를 모른 채 고른다
# 센소리움(레시피) 모델은 **향료 → 하드웨어 → 산식**이 한 덩어리다. 그런데 계약에는 그 첫 칸(향료)을
#   넘길 자리가 없었다. 엔진은 자기 안의 카탈로그(향장향 27종 · 식향 16종) 전체에서 고르고, **그 기기에
#   실제로 무엇이 꽂혀 있는지는 모른다.** 운영자가 관제에서 포트 매핑을 바꿔도 엔진 출력은 그대로다.
# 
# 결과는 늦게 드러난다 — 엔진이 안 꽂힌 향료를 고르면:
#   · 향장향 : 주문 접수에서 409 `fragrance_note_unmapped` 로 거절된다(손님은 결과 화면까지 본 뒤다).
#   · 식향   : 접수 검사조차 없어 **조립까지 내려가서** 터진다(`unmapped liquid`). 손님은 대기 화면에 남는다.
#   게다가 향장향은 지금 **정확히 만석**이다(3펌프 × 9칸 = 27칸 · 카탈로그 27종). 28번째 향료를 더하는
#   순간 그 향료는 영구 미매핑이 되고, 엔진이 그걸 고른 주문은 전부 위 길로 떨어진다.
# 
# ⇒ web 이 "지금 이 기기에 꽂힌 향료"를 실어 보내고, 엔진이 **그 안에서만** 고른다.
#   그러면 향료 라인업을 바꾸는 일이 **운영자의 포트 매핑 편집 하나**로 끝난다(엔진 재배포 0).
# 
# ## 어휘 — 향료 id (2026-09-29 · 이름과 분리)
# `notes` 의 문자열은 **향료 id** 다 — 레시피 `RecipeNote.id` · web 포트 매핑 키와 같은 문자열(향연 = ICAD `material_id`).
#   어댑터는 **id 정확 일치**(앞뒤 공백·대소문자·유니코드 정규형만 무시)로만 받는다 — 표시명·괄호 앞 이름으로
#   느슨하게 맞추지 않는다(AI 는 맞췄다고 보는데 web 접수가 거부하는 어긋남을 막기 위해 · 2026-09-29).
#   참고(헤이센릿 쪽 미러):
#   · 향장향 : `domain/fragrance/recipe.py` `NOTE_META` 키(예 "Bitter Lemon") ↔ web `NoteMetadata.ts` `NOTE_META`
#   · 식향   : `domain/flavor/recipe.py` 팔레트 16종 키                        ↔ web `shared/expo/palette.ts`
#   새 어휘를 만들지 않는다 — 번역 층이 하나 늘면 그 층이 곧 드리프트 지점이다.
# 
# ## 계약
#   · `palette=None`(기본)  → **제한 없음.** 오늘과 1비트도 다르지 않다(하위호환 · 구 web·구 어댑터 그대로 동작).
#   · `palette.notes` 있음  → 어댑터는 **그 목록 안에서만** 고른다. 목록 밖 향료를 결과에 내지 않는다.
#   · 목록에 **카탈로그에 없는 키**가 섞여 오면 → 어댑터는 그 키를 **무시한다**(거부하지 않는다).
#         web 과 엔진의 카탈로그가 잠깐 어긋난 배포 창에서 주문이 통째로 죽지 않게 하려는 것이다.
#   · 걸러 내고 **남은 것이 너무 적어 만들 수 없으면** → 어댑터는 `is_valid: false` + `warnings` 로 돌려준다.
#         "몇 종이면 만들 수 있나"는 **산식의 문제라 어댑터가 정한다**(향장향 8향 선정 · 식향 역할별 최소 등).
#         예외로 던지지 않는다 — 실패가 아니라 "이 구성으로는 못 만든다"는 정상 답이다.
#   · 빈 목록(`notes=()`)은 **서버가 어댑터를 부르기 전에 422 로 끊는다** — 만들 재료가 0 이면 갈 이유가 없다.
# 
# ## 어댑터가 정할 것 (계약이 단정하지 않는 것)
#   · 목록을 **어떻게** 지키나 — 프롬프트에 주입하나 · 선정 뒤 거르나 · 둘 다 하나.
#   · 목록이 작을 때 품질을 어떻게 지키나(8향을 못 채우면 줄이나 · 대체하나).
#   · 재조향(`regenerate`)에서 prior 의 향료가 지금 목록에 없으면 어떻게 다루나.
#   계약이 요구하는 건 **결과에 목록 밖 향료가 없다**는 것 하나다.

@dataclass(frozen=True)
class Palette:
    """이번 요청에서 쓸 수 있는 향료 목록 — 그 기기에 실제로 꽂혀 있는 것.

    notes : 향료 id 의 튜플(순서 무의미 · 중복 없음). 헤더 「어휘」 참조.
            ⛔ 양(mL)·포트 번호·펌프 주소는 **싣지 않는다** — 엔진은 "무엇을 쓸 수 있나"만 알면 된다.
               "어디에 꽂혔나"는 조립(web `wire`·pi)의 일이고, 그게 엔진에 닿으면 하드웨어 배치가
               산식에 새어 들어간다.
    """

    notes: tuple[str, ...]


@dataclass(frozen=True)
class ComposeTurn:
    """대화 한 턴 — `role` 은 "user" | "assistant" 만(서버 Body 가 400 경계를 강제한다)."""

    role: str
    content: str

    def __post_init__(self) -> None:
        if self.role not in ("user", "assistant"):
            raise PortContractError(f"ComposeTurn.role 은 user | assistant 여야 한다({self.role!r})")
        if not isinstance(self.content, str):
            raise PortContractError(f"ComposeTurn.content 는 문자열이어야 한다({type(self.content).__name__})")


@dataclass(frozen=True)
class ComposePrior:
    """2차(활동 4)에만 실리는 **1차 결과 요약** — 사용 여부는 어댑터 판단.

    ⛔ 배합 양(amountMl·percent·totalVolumeMl)은 **절대 싣지 않는다**(사양서 §2-3 · I-D23).
       converse 응답은 손님 SSE 로 그대로 내려가는데 그 경로엔 배합 allowlist 가 없어, 양이
       프롬프트에 들어가면 AI 한 마디로 샌다. 향료명(note_names)까지만이 계약이다.
       서버는 양 키가 들어오면 400 이 아니라 **버리고 경고**한다.
    """

    name: str
    emotion_group: str
    note_names: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not isinstance(self.emotion_group, str):
            raise PortContractError("ComposePrior.name·emotion_group 은 문자열이어야 한다")
        if isinstance(self.note_names, (str, bytes)) or any(not isinstance(n, str) for n in self.note_names):
            raise PortContractError("ComposePrior.note_names 는 문자열 목록이어야 한다")
        object.__setattr__(self, "note_names", tuple(self.note_names))


@dataclass(frozen=True)
class ComposeOptions:
    """compose 호출 옵션(`ComposeParam.params`) — 지금은 받는 옵션이 없다(빈 클래스 · 밖의 키는 거부).

    옵션이 필요해지면 칸을 **여기 추가**한다(허용목록 = 이 클래스의 필드).
    """

    @classmethod
    def from_dict(cls, d: Mapping[str, Any] | None) -> "ComposeOptions":
        d = d or {}
        if not isinstance(d, Mapping):
            raise PortContractError(f"ComposeOptions.from_dict: Mapping 이 아니다({type(d).__name__})")
        if d:
            raise PortContractError(f"허용되지 않는 params: {sorted(d)} (icad compose 허용: [])")
        return cls()

    def to_dict(self) -> dict[str, Any]:
        return {}


@dataclass(frozen=True)
class ComposeParam:
    """향연 compose 한 번 — **대화 이력 전체**가 입력이다(사양서 §3-1 · 서버 IcadComposeBody 와 1:1).

    ⛔ `RecipeParam` 과 **별개 DTO** 다(사양서 §3-3). 입력이 `prompt`(한 문장) 가 아니라
       `history`(이력 전문)라 개념이 다르고, 식향엔 이 동작이 없어야 한다 — 현행 `regenerate` 가
       fragrance 에만 있는 것과 같은 자세. `RecipeParam` 에 nullable history 를 얹으면
       "무엇이 지배하나(prompt 냐 history 냐)"가 타입에서 사라진다.

    history : 이번 회차 대화 전문(≤100턴 · 상한은 서버가 강제) — 관호 확정 입력.
    round   : 1 | 2. 서버가 access_codes 로 **재확정한 값**(클라 주장값 아님).
    prior   : 2차에만. 양 없음(ComposePrior 참조).
    lang    : 1차 파일럿 "ko" 고정(서버가 그 경계를 잡는다 — 여기선 타입만).
    params  : 어댑터 확장 슬롯(현행 RecipeParam.params 와 같은 의미 · 허용목록은 어댑터 소유).
    선언 3필드(sensorium_version·ai_models·ai_model)는 서버 층(ModelSelection)에서 소비되고
    LLM 핀으로 적용되므로 이 DTO 엔 실리지 않는다 — 현행 RecipeParam 과 같은 배선.
    """

    history: tuple[ComposeTurn, ...]
    round: int = 1
    prior: ComposePrior | None = None
    lang: str = "ko"
    params: ComposeOptions = field(default_factory=ComposeOptions)  # (2026-09-29) dict → 옵션 클래스
    # (2026-09-20) 이번 요청에서 **쓸 수 있는 향료** — 그 기기에 실제로 꽂혀 있는 것. None = 제한 없음(현행).
    #   계약·어휘·실패 규약 정본 = 이 파일 `Palette` 절. ⚠️ 신규 필드라 **끝에** 둔다(위치인자 소비자 호환).
    palette: Palette | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.history, tuple) or any(not isinstance(t, ComposeTurn) for t in self.history):
            raise PortContractError("ComposeParam.history 는 ComposeTurn 튜플이어야 한다")
        if isinstance(self.round, bool) or self.round not in (1, 2):
            raise PortContractError(f"ComposeParam.round 는 1 또는 2 여야 한다({self.round!r})")
        if self.prior is not None and not isinstance(self.prior, ComposePrior):
            raise PortContractError(f"ComposeParam.prior 는 ComposePrior 여야 한다({type(self.prior).__name__})")
        if not isinstance(self.params, ComposeOptions):
            raise PortContractError(f"ComposeParam.params 는 ComposeOptions 여야 한다({type(self.params).__name__})")
        if self.palette is not None and not isinstance(self.palette, Palette):
            raise PortContractError(f"ComposeParam.palette 는 Palette 여야 한다({type(self.palette).__name__})")


@dataclass(frozen=True)
class ComposeReply:
    """향연 compose 출력(클래스 · 2026-09-29) — 봉투 `{payload, stamp, llm_models_used?}`.

    payload         : IcadPayload — 그 안의 `recipe` 는 현행 향장향과 같은 FragranceResult 형상
                      (`notes[]{id, name, nameKo, amountMl(**mL**), percent, type: top|middle|base}` + `totalVolumeMl`(mL)).
                      web 변환기·pi 조립이 이 형식만 읽는다. 단위를 바꾸면 1000배 오토출이다.
    stamp           : 도장(Stamp).
    llm_models_used : tier→model. **모르면 None = to_dict() 에서 키 생략**(거짓값 금지 · 사양서 §4-5).

    ⚠️ 와이어 키는 snake_case(`llm_models_used`) — web 미러 IcadContracts.ts 와 1:1.
    """

    payload: IcadPayload
    stamp: Stamp
    llm_models_used: Mapping[str, str] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.payload, IcadPayload):
            raise PortContractError(f"ComposeReply.payload 는 IcadPayload 여야 한다({type(self.payload).__name__})")
        if not isinstance(self.stamp, Stamp):
            raise PortContractError(f"ComposeReply.stamp 는 Stamp 여야 한다({type(self.stamp).__name__})")

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "ComposeReply":
        if not isinstance(d, Mapping):
            raise PortContractError(f"ComposeReply.from_dict: Mapping 이 아니다({type(d).__name__})")
        missing = [k for k in ("payload", "stamp") if k not in d]
        if missing:
            raise PortContractError(f"ComposeReply.from_dict: 필수 키 누락 {missing}")
        used = d.get("llm_models_used")
        return cls(payload=IcadPayload.from_dict(d["payload"]), stamp=Stamp.from_dict(d["stamp"]),
                   llm_models_used=dict(used) if used is not None else None)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"payload": self.payload.to_dict(), "stamp": self.stamp.to_dict()}
        if self.llm_models_used is not None:
            d["llm_models_used"] = dict(self.llm_models_used)  # 모르면 싣지 않는다(옵셔널 키)
        return d


class ComposePort(VersionPort):
    """향연 compose 의 약속 — 연구소(관호)가 상속해 이 세대의 compose 어댑터를 만든다."""

    @abstractmethod
    def compose(
        self, param: ComposeParam, llm: LlmPort | None = None
    ) -> ComposeReply:
        """대화 이력 → 제품 payload 하나. 내부 엔진·라벨링·규제 호출 횟수·순서는 어댑터 소관."""
        ...
