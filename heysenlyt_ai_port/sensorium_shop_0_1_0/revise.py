"""sensorium-shop-0.1.0 — 대화·레시피 공용 클래스: `Turn` · `ScentBrief` · `ReviseContext`. 의존성 0.

⭐ 포트는 통합코드가 정의한다 — 어댑터가 기획(HoS AI PRD)을 지키는 데 필요한 값은 전부 파라미터로, 통합코드가 쓸 값은 전부
   응답으로, 모두 클래스로 주고받는다(2026-10-19).

## 길이 상한 (비용·DoS 방어 — 넘으면 `PortContractError` · 통합코드가 400 으로 돌려준다)
  Turn.content ≤ 4000자 · 대화(history/conversation) ≤ 100턴 · ScentBrief 글 칸 ≤ 200자 · 목록 칸 ≤ 20개(항목 ≤ 200자)
  ReviseContext: original_request ≤ 1500 · composer_note ≤ 700 · recipe_name ≤ 40 · recipe_description ≤ 300 · note_names ≤ 60개
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from heysenlyt_ai_port.errors import PortContractError

REACTIONS = ("like", "dislike", "none")      # 👍 맞아요 · 👎 아쉬워요 · 평가 없음(아직 안 맡음 포함)
ROLES = ("user", "assistant")
WEIGHTS = ("light", "medium", "heavy")       # 가볍게 정돈 · 중간 · 묵직하게 가라앉음(PRD 1부 §4 무게감)
BRIEF_FIELDS = ("purpose", "feel", "avoid", "liked", "weight", "occasion")

MAX_TURN_CHARS = 4000            # 대화 한 턴
MAX_TURNS = 100                  # 대화 턴 수(history · conversation)
MAX_BRIEF_TEXT_CHARS = 200       # ScentBrief 글 칸 · 목록 항목 하나
MAX_BRIEF_LIST_ITEMS = 20        # ScentBrief 목록 칸
MAX_ORIGINAL_REQUEST_CHARS = 1500
MAX_COMPOSER_NOTE_CHARS = 700
MAX_RECIPE_NAME_CHARS = 40
MAX_RECIPE_DESCRIPTION_CHARS = 300
MAX_NOTE_NAMES = 60


def _reject_unknown(cls_name: str, d: Mapping[str, Any], allowed: tuple[str, ...] | set[str]) -> None:
    bad = sorted(set(d) - set(allowed))
    if bad:
        raise PortContractError(f"허용되지 않는 {cls_name} 키: {bad} (허용: {sorted(allowed)})")


def _opt_str(cls_name: str, key: str, v: Any) -> None:
    if v is not None and not isinstance(v, str):
        raise PortContractError(f"{cls_name}.{key} 는 문자열이어야 한다({type(v).__name__})")


def _max_chars(cls_name: str, key: str, v: Any, limit: int) -> None:
    if isinstance(v, str) and len(v) > limit:
        raise PortContractError(f"{cls_name}.{key} 는 {limit}자 이하여야 한다({len(v)}자)")


def _str_tuple(cls_name: str, key: str, v: Any, *, nullable: bool = False, max_items: int | None = None,
               max_item_chars: int | None = None) -> tuple[str, ...] | None:
    if v is None:
        if nullable:
            return None
        return ()
    if isinstance(v, str) or not isinstance(v, (list, tuple)) or not all(isinstance(x, str) for x in v):
        raise PortContractError(f"{cls_name}.{key} 는 문자열 목록이어야 한다")
    if max_items is not None and len(v) > max_items:
        raise PortContractError(f"{cls_name}.{key} 는 {max_items}개 이하여야 한다({len(v)}개)")
    if max_item_chars is not None:
        for x in v:
            _max_chars(cls_name, key, x, max_item_chars)
    return tuple(v)


@dataclass(frozen=True)
class Turn:
    """대화 한 턴. role = "user" | "assistant". 와이어 = `[role, content]` 또는 `{role, content}`(둘 다 받는다 · 내보낼 땐 `[role, content]`)."""

    role: str
    content: str

    def __post_init__(self) -> None:
        if self.role not in ROLES:
            raise PortContractError(f"Turn.role 은 {ROLES} 중 하나여야 한다({self.role!r})")
        if not isinstance(self.content, str):
            raise PortContractError("Turn.content 는 문자열이어야 한다")
        _max_chars("Turn", "content", self.content, MAX_TURN_CHARS)

    @classmethod
    def from_wire(cls, t: Any) -> "Turn":
        if isinstance(t, Turn):
            return t
        if isinstance(t, Mapping):
            _reject_unknown("Turn", t, ("role", "content"))
            return cls(role=t.get("role"), content=t.get("content"))  # type: ignore[arg-type]
        if isinstance(t, (list, tuple)) and len(t) == 2:
            return cls(role=t[0], content=t[1])
        raise PortContractError("Turn 은 [role, content] 또는 {role, content} 여야 한다")

    def to_wire(self) -> list[str]:
        return [self.role, self.content]


def turns_from_wire(raw: Any, what: str, *, max_turns: int | None = None) -> tuple[Turn, ...]:
    if raw is None:
        return ()
    if isinstance(raw, (str, bytes)) or not isinstance(raw, (list, tuple)):
        raise PortContractError(f"{what} 는 턴 목록이어야 한다({type(raw).__name__})")
    if max_turns is not None and len(raw) > max_turns:
        raise PortContractError(f"{what} 는 {max_turns}턴 이하여야 한다({len(raw)}턴)")
    return tuple(Turn.from_wire(t) for t in raw)


@dataclass(frozen=True)
class ScentBrief:
    """손님이 원하는 향의 요점(HoS AI PRD 1부 §4) — 필수 3(목적 · 원하는 느낌 · 피할 향) + 선택 3(좋아하는 향 · 무게감 · 상황).

    모든 칸에서 **None = 아직 모름**(안 물었거나 못 들음). 피할 향·좋아하는 향은 **`()` = 「없다」고 답함** — None 과 다르다.
    inferred : 손님이 말하지 않아 **AI 가 추정·기본값으로 채운 칸 이름**(PRD §4 「못 받으면」·§5 「#4 에 모자라면 추정 · 피할 향 = 없음」).
               레시피 응답에서만 채운다(대화 응답은 들은 것만).
    """

    purpose: str | None = None              # 목적 — 예 「내 몸에 뿌릴 향」 · 「매장 입구 공간향」 · 「선물」
    feel: str | None = None                 # 원하는 느낌(분위기 · 장면 · 기억)
    avoid: tuple[str, ...] | None = None    # 피할 향 — () = 없다고 답함
    liked: tuple[str, ...] | None = None    # 좋아하는 향 · 참고 향수
    weight: str | None = None               # "light" | "medium" | "heavy"
    occasion: str | None = None             # 쓰는 상황 · 계절
    inferred: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for k in ("purpose", "feel", "occasion"):
            _opt_str("ScentBrief", k, getattr(self, k))
            _max_chars("ScentBrief", k, getattr(self, k), MAX_BRIEF_TEXT_CHARS)
        if self.weight is not None and self.weight not in WEIGHTS:
            raise PortContractError(f"ScentBrief.weight 는 {WEIGHTS} 중 하나여야 한다({self.weight!r})")
        for k in ("avoid", "liked"):
            object.__setattr__(self, k, _str_tuple("ScentBrief", k, getattr(self, k), nullable=True,
                                                   max_items=MAX_BRIEF_LIST_ITEMS, max_item_chars=MAX_BRIEF_TEXT_CHARS))
        inf = _str_tuple("ScentBrief", "inferred", self.inferred) or ()
        bad = [x for x in inf if x not in BRIEF_FIELDS]
        if bad:
            raise PortContractError(f"ScentBrief.inferred 의 값은 {BRIEF_FIELDS} 중 하나여야 한다({bad})")
        object.__setattr__(self, "inferred", inf)

    @property
    def required_collected(self) -> int:
        """필수 3개 중 채워진 수(PRD QC 「#4 까지 필수 정보 3개」 계측용)."""
        return sum(1 for v in (self.purpose, self.feel, self.avoid) if v is not None)

    @classmethod
    def from_dict(cls, d: Any) -> "ScentBrief":
        if not isinstance(d, Mapping):
            raise PortContractError(f"ScentBrief.from_dict: Mapping 이 아니다({type(d).__name__})")
        _reject_unknown("ScentBrief", d, (*BRIEF_FIELDS, "inferred"))
        return cls(**{k: d.get(k) for k in BRIEF_FIELDS}, inferred=d.get("inferred") or ())

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for k in BRIEF_FIELDS:
            v = getattr(self, k)
            out[k] = list(v) if isinstance(v, tuple) else v
        out["inferred"] = list(self.inferred)
        return out


_REVISE_KEYS = {  # 와이어 키 → 필드명
    "originalRequest": "original_request", "recipeName": "recipe_name", "recipeDescription": "recipe_description",
    "composerNote": "composer_note", "noteNames": "note_names", "brief": "brief",
    "latestReaction": "latest_reaction", "reactions": "reactions",
}


@dataclass(frozen=True)
class ReviseContext:
    """수정 대화·수정본이 알아야 하는 원본 — 통합코드가 원본 레시피·대화·시향 평가에서 채운다(어댑터는 DB 를 못 본다).

    original_request   : 원본 대화의 손님 말(≤1500자).
    recipe_name        : 원본 이름(수정본은 이 이름과 겹치지 않게 새로 짓는다).
    recipe_description : 원본 한 줄 설명.
    composer_note      : 원본 조향 노트(≤700자).
    note_names         : 원본 향료 이름(엔진 순서 · 양 없음).
    brief              : 원본을 만들 때의 `ScentBrief`(원본 레시피 응답에서 받아 저장한 것 · 옛 레시피는 None).
    latest_reaction    : 가장 최근 시향 평가 — 고정 첫 질문을 고른 기준.
    reactions          : 시향 평가 이력(오래된 것 → 최근) — 「예전 평가는 AI 가 대화에서 참고한다」.
    """

    original_request: str
    recipe_name: str
    latest_reaction: str = "none"
    recipe_description: str = ""
    composer_note: str = ""
    note_names: tuple[str, ...] = ()
    brief: ScentBrief | None = None
    reactions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for k, limit in (("original_request", MAX_ORIGINAL_REQUEST_CHARS), ("recipe_name", MAX_RECIPE_NAME_CHARS),
                         ("recipe_description", MAX_RECIPE_DESCRIPTION_CHARS), ("composer_note", MAX_COMPOSER_NOTE_CHARS)):
            if not isinstance(getattr(self, k), str):
                raise PortContractError(f"ReviseContext.{k} 는 문자열이어야 한다")
            _max_chars("ReviseContext", k, getattr(self, k), limit)
        if self.latest_reaction not in REACTIONS:
            raise PortContractError(f"ReviseContext.latest_reaction 은 {REACTIONS} 중 하나여야 한다({self.latest_reaction!r})")
        object.__setattr__(self, "note_names", _str_tuple("ReviseContext", "note_names", self.note_names,
                                                          max_items=MAX_NOTE_NAMES))
        reacts = _str_tuple("ReviseContext", "reactions", self.reactions) or ()
        if any(r not in REACTIONS for r in reacts):
            raise PortContractError(f"ReviseContext.reactions 의 값은 {REACTIONS} 중 하나여야 한다")
        object.__setattr__(self, "reactions", reacts)
        if self.brief is not None and not isinstance(self.brief, ScentBrief):
            raise PortContractError("ReviseContext.brief 는 ScentBrief 여야 한다")

    @classmethod
    def from_dict(cls, d: Any) -> "ReviseContext":
        if not isinstance(d, Mapping):
            raise PortContractError(f"ReviseContext.from_dict: Mapping 이 아니다({type(d).__name__})")
        _reject_unknown("ReviseContext", d, set(_REVISE_KEYS))
        for req in ("originalRequest", "recipeName"):
            if req not in d:
                raise PortContractError(f"ReviseContext.from_dict: 필수 키 {req!r} 누락")
        b = d.get("brief")
        return cls(original_request=d["originalRequest"], recipe_name=d["recipeName"],
                   # null = 키 없음과 같다(「평가 없음」) — web 이 값이 없을 때 null 을 싣는 습관
                   latest_reaction="none" if d.get("latestReaction") is None else d["latestReaction"],
                   recipe_description=d.get("recipeDescription") or "", composer_note=d.get("composerNote") or "",
                   note_names=d.get("noteNames") or (), brief=ScentBrief.from_dict(b) if b is not None else None,
                   reactions=d.get("reactions") or ())

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for w, f in _REVISE_KEYS.items():
            v = getattr(self, f)
            if f == "brief":
                out[w] = v.to_dict() if v is not None else None
            else:
                out[w] = list(v) if isinstance(v, tuple) else v
        return out
