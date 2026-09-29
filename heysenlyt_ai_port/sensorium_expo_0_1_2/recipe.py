"""sensorium-expo-0.1.2 — 레시피 계약. 의존성 0.

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
# 포트는 인터페이스라 **파라미터·리턴이 전부 클래스**다(dict 로 주고받으면 어댑터가 무엇을 빼먹어도 포트가 모른다).
#
# ⛔ **재료 한 줄의 `id` 는 필수다.** 식향은 원래부터 재료를 id(`channel_id` — 팔레트 16종 키)로 불러 왔다.
#   클래스 필드는 `id` 이고, 와이어 키는 오늘 그대로 `channel_id` 다(web 조립이 이 키로 포트를 찾는다 · 와이어 변경 0).
#   id 가 비면 `FlavorItem` 을 만드는 순간 ValueError.
#
# 계약에 이름이 없는 키는 `extra` 에 **보존**한다. None 인 칸은 `to_dict()` 에서 생략한다("없었다" ≠ "빈 값").

_ITEM_KEYS = {"channel_id": "id", "amount_ml": "amount_ml", "role": "role"}  # 와이어 키 → 필드명
_FLAVOR_KEYS = {
    "drinkTitle": "drink_title", "reason": "reason", "tastingNote": "tasting_note",
    "scene": "scene", "mood": "mood", "taste": "taste", "tier": "tier",
    "families": "families", "familyLabels": "family_labels", "specialAromas": "special_aromas",
    "sweetMl": "sweet_ml", "sourMl": "sour_ml", "baseMl": "base_ml", "kernelVersion": "kernel_version",
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
class FlavorItem:
    """식향 재료(아로마) 한 줄.

    id        : 재료 id — **필수 · 비면 ValueError.** 와이어 키는 `channel_id`.
    amount_ml : 양(**mL**).
    role      : "main" | "sub" | "accent".
    extra     : 계약 밖 키(보존만 한다).
    """

    id: str
    amount_ml: float | None = None
    role: str | None = None
    extra: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _freeze_extra(self, set(_ITEM_KEYS))
        if not isinstance(self.id, str) or not self.id.strip():
            raise PortContractError(f"FlavorItem.id(channel_id) 는 비어 있지 않은 문자열이어야 한다: {self.id!r}")

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "FlavorItem":
        if not isinstance(d, Mapping):
            raise PortContractError(f"FlavorItem.from_dict: Mapping 이 아니다({type(d).__name__})")
        if "channel_id" not in d:
            raise PortContractError("FlavorItem.from_dict: 필수 키 'channel_id' 누락")
        known = {field_name: d[wire] for wire, field_name in _ITEM_KEYS.items() if wire in d}
        extra = {k: v for k, v in d.items() if k not in _ITEM_KEYS}
        return cls(**known, extra=extra)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for wire, field_name in _ITEM_KEYS.items():
            v = getattr(self, field_name)
            if v is not None:
                out[wire] = v
        out.update(self.extra)
        return out


@dataclass(frozen=True)
class SpecialAroma:
    """계열 6축 밖의 특수향 한 줄(`specialAromas[]`) — 와이어 키 {id, name, amount_ml} 그대로."""

    id: str
    name: str
    amount_ml: float

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise PortContractError("SpecialAroma.id 는 비어 있지 않은 문자열이어야 한다")
        if not isinstance(self.name, str):
            raise PortContractError(f"SpecialAroma.name 은 문자열이어야 한다({type(self.name).__name__})")
        if isinstance(self.amount_ml, bool) or not isinstance(self.amount_ml, (int, float)):
            raise PortContractError(f"SpecialAroma.amount_ml 은 숫자여야 한다({self.amount_ml!r})")

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "SpecialAroma":
        if not isinstance(d, Mapping):
            raise PortContractError(f"SpecialAroma.from_dict: Mapping 이 아니다({type(d).__name__})")
        for k in ("id", "name", "amount_ml"):
            if k not in d:
                raise PortContractError(f"SpecialAroma.from_dict: 필수 키 '{k}' 누락")
        return cls(id=d["id"], name=d["name"], amount_ml=d["amount_ml"])

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "amount_ml": self.amount_ml}


def _typed_map(name: str, v: Any, value_types: tuple[type, ...]) -> dict[str, Any]:
    """키=문자열 · 값=지정 타입인 사전만 받는다(계열 축처럼 **키가 데이터**인 칸 — 값 타입은 강제)."""
    if not isinstance(v, Mapping):
        raise PortContractError(f"FlavorRecipe.{name} 는 Mapping 이어야 한다({type(v).__name__})")
    bad = [k for k, x in v.items() if not isinstance(k, str) or isinstance(x, bool) or not isinstance(x, value_types)]
    if bad:
        raise PortContractError(f"FlavorRecipe.{name} 값 타입 위반: {bad[:5]}")
    return dict(v)


@dataclass(frozen=True)
class FlavorRecipe:
    """식향 레시피 — ExpoRecipePayload 형상(web 이 읽는 모양 그대로).

    items : 아로마 재료 줄들(FlavorItem). 무효 레시피는 비어 있거나 없다.
    나머지 : 음료 이름·이유·축(scene/mood/taste)·당/산/기주(mL)·계열·도장. 계약 밖 키는 extra.
    """

    items: tuple[FlavorItem, ...] | None = None
    drink_title: str | None = None
    reason: str | None = None
    tasting_note: str | None = None
    scene: str | None = None
    mood: str | None = None
    taste: str | None = None
    tier: str | None = None
    families: Mapping[str, float] | None = None  # 계열 6축 → 1.0~5.0 (축 이름은 데이터)
    family_labels: Mapping[str, str] | None = None  # 축 → 표시 이름
    special_aromas: tuple[SpecialAroma, ...] | None = None
    sweet_ml: float | None = None
    sour_ml: float | None = None
    base_ml: float | None = None
    kernel_version: str | None = None
    extra: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _freeze_extra(self, set(_FLAVOR_KEYS) | {"items"})
        if self.items is not None:
            items = tuple(self.items)
            bad = [type(i).__name__ for i in items if not isinstance(i, FlavorItem)]
            if bad:
                raise PortContractError(f"FlavorRecipe.items 는 FlavorItem 이어야 한다: {bad}")
            object.__setattr__(self, "items", items)
        if self.families is not None:
            object.__setattr__(self, "families", _typed_map("families", self.families, (int, float)))
        if self.family_labels is not None:
            object.__setattr__(self, "family_labels", _typed_map("family_labels", self.family_labels, (str,)))
        if self.special_aromas is not None:
            sa = tuple(self.special_aromas)
            bad = [type(a).__name__ for a in sa if not isinstance(a, SpecialAroma)]
            if bad:
                raise PortContractError(f"FlavorRecipe.special_aromas 는 SpecialAroma 여야 한다: {bad}")
            object.__setattr__(self, "special_aromas", sa)

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "FlavorRecipe":
        if not isinstance(d, Mapping):
            raise PortContractError(f"FlavorRecipe.from_dict: Mapping 이 아니다({type(d).__name__})")
        known: dict[str, Any] = {field_name: d[wire] for wire, field_name in _FLAVOR_KEYS.items() if wire in d}
        if "items" in d:
            raw = d["items"]
            if not isinstance(raw, (list, tuple)):
                raise PortContractError(f"FlavorRecipe.from_dict: items 가 리스트가 아니다({type(raw).__name__})")
            known["items"] = tuple(FlavorItem.from_dict(i) for i in raw)
        if d.get("specialAromas") is not None:
            raw_sa = d["specialAromas"]
            if not isinstance(raw_sa, (list, tuple)):
                raise PortContractError(f"FlavorRecipe.from_dict: specialAromas 가 리스트가 아니다({type(raw_sa).__name__})")
            known["special_aromas"] = tuple(SpecialAroma.from_dict(a) for a in raw_sa)
        extra = {k: v for k, v in d.items() if k not in _FLAVOR_KEYS and k != "items"}
        return cls(**known, extra=extra)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for wire, field_name in _FLAVOR_KEYS.items():
            v = getattr(self, field_name)
            if v is None:
                continue
            if field_name == "special_aromas":
                out[wire] = [a.to_dict() for a in v]
            else:
                out[wire] = dict(v) if isinstance(v, Mapping) else (list(v) if isinstance(v, tuple) else v)
        if self.items is not None:
            out["items"] = [i.to_dict() for i in self.items]
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
# ## 어휘 — 재료 id (2026-09-29 · 이름과 분리)
# `notes` 의 문자열은 **재료 id** 다 — 레시피 `FlavorItem.id`(와이어 `channel_id`) · web 포트 매핑 키와 같은 문자열.
#   두 트랙 모두 web 이 같은 키의 미러를 들고 있다:
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

    notes : 재료 id 의 튜플(순서 무의미 · 중복 없음). 헤더 「어휘」 참조.
            ⛔ 양(mL)·포트 번호·펌프 주소는 **싣지 않는다** — 엔진은 "무엇을 쓸 수 있나"만 알면 된다.
               "어디에 꽂혔나"는 조립(web `wire`·pi)의 일이고, 그게 엔진에 닿으면 하드웨어 배치가
               산식에 새어 들어간다.
    """

    notes: tuple[str, ...]


# ## 레시피 호출 옵션 — `RecipeParam.params` (2026-09-29 · dict → 클래스)
_OPTION_KEYS = ("temperature", "sweet_ml", "sweet_level", "sour_level", "tier", "max_tokens", "recent_lead_channels")


def _is_num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


@dataclass(frozen=True)
class RecipeOptions:
    """식향 레시피 호출 옵션. 모든 칸 선택(None = 어댑터 기본값). 값의 범위(1~5 등)는 엔진이 기존대로 판정한다.

    temperature · max_tokens · tier : LLM 호출 옵션.
    sweet_ml · sweet_level · sour_level : 당·산 오버라이드.
    recent_lead_channels : 리드 분산용 최근 리드 채널 id(서버가 주입 · web `flavor/finalize`).
    """

    temperature: float | None = None
    sweet_ml: float | None = None
    sweet_level: float | None = None
    sour_level: float | None = None
    tier: str | None = None
    max_tokens: int | None = None
    recent_lead_channels: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        for f in ("temperature", "sweet_ml", "sweet_level", "sour_level"):
            v = getattr(self, f)
            if v is not None and not _is_num(v):
                raise PortContractError(f"RecipeOptions.{f} 는 숫자여야 한다({v!r})")
        if self.tier is not None and not isinstance(self.tier, str):
            raise PortContractError(f"RecipeOptions.tier 는 문자열이어야 한다({type(self.tier).__name__})")
        if self.max_tokens is not None and (isinstance(self.max_tokens, bool) or not isinstance(self.max_tokens, int)):
            raise PortContractError(f"RecipeOptions.max_tokens 는 정수여야 한다({self.max_tokens!r})")
        if self.recent_lead_channels is not None:
            v = self.recent_lead_channels
            if isinstance(v, (str, bytes)) or not isinstance(v, (tuple, list)) or any(not isinstance(x, str) for x in v):
                raise PortContractError("RecipeOptions.recent_lead_channels 는 문자열 목록이어야 한다")
            object.__setattr__(self, "recent_lead_channels", tuple(v))

    @classmethod
    def from_dict(cls, d: Mapping[str, Any] | None) -> "RecipeOptions":
        d = d or {}
        if not isinstance(d, Mapping):
            raise PortContractError(f"RecipeOptions.from_dict: Mapping 이 아니다({type(d).__name__})")
        bad = sorted(set(d) - set(_OPTION_KEYS))
        if bad:
            raise PortContractError(f"허용되지 않는 params: {bad} (flavor 허용: {sorted(_OPTION_KEYS)})")
        return cls(**{k: d[k] for k in _OPTION_KEYS if d.get(k) is not None})

    def to_dict(self) -> dict[str, Any]:
        """None 칸 생략 — 어댑터 엔진이 읽는 dict 모양 그대로."""
        out: dict[str, Any] = {}
        for k in _OPTION_KEYS:
            v = getattr(self, k)
            if v is not None:
                out[k] = list(v) if k == "recent_lead_channels" else v
        return out


@dataclass(frozen=True)
class RecipeParam:
    """한 번의 레시피 요청. 불변(frozen) — 요청 객체 재사용이 안전하다.

    prompt : 자연어 요청(백지 생성). 손님 피드백은 여기가 아니라 RegenerateParam.feedback.
             조향=한 문장(예 "제주 서귀포 해수욕장의 향"), 식향=취향 축 요약(scene/mood/taste).
    mode   : 도메인 내 방식. 조향 "rule"(v1.2.0 기본) / 식향 "generative"(expo, v1.2.0 기본).
             None이면 도메인 기본값.
    lang   : 결과 텍스트 언어 ("ko"|"en"|"ja"|"vi"). 비-ko는 ko 병기(직원 주문 읽기 P0).
    params : 방식 파라미터 오버라이드. 조향 {complexity, ratio} / 식향 {} / 공통 {temperature}.
             어댑터 허용목록 밖 키는 거부된다(비용·통제 이탈 차단).

    """

    prompt: str
    mode: str | None = None
    lang: str = "ko"
    params: RecipeOptions = field(default_factory=RecipeOptions)  # (2026-09-29) dict → 옵션 클래스
    # (2026-09-20) 이번 요청에서 **쓸 수 있는 향료** — 그 기기에 실제로 꽂혀 있는 것. None = 제한 없음(현행).
    #   계약·어휘·실패 규약 정본 = 이 파일 `Palette` 절. ⚠️ 신규 필드라 **끝에** 둔다(위치인자 소비자 호환).
    palette: Palette | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.params, RecipeOptions):
            raise PortContractError(f"RecipeParam.params 는 RecipeOptions 여야 한다({type(self.params).__name__})")
        if self.palette is not None and not isinstance(self.palette, Palette):
            raise PortContractError(f"RecipeParam.palette 는 Palette 여야 한다({type(self.palette).__name__})")


@dataclass(frozen=True)
class RecipeReply:
    """generate 출력(클래스 · 2026-09-29). `to_dict()` 가 와이어 JSON.

    stamp  : 도장(Stamp).
    recipe : 레시피(FlavorRecipe) — 재료 줄마다 id(channel_id) 필수.
    """

    domain: str  # "flavor"
    version: str  # "0.1.2"
    stamp: Stamp
    recipe: FlavorRecipe
    is_valid: bool = True
    warnings: tuple[str, ...] = ()
    result_type: str = ""  # "module:Class" — 와이어 값
    state: Mapping[str, Any] = field(default_factory=dict)  # 호출자 보관 상태(불투명)

    def __post_init__(self) -> None:
        if not isinstance(self.stamp, Stamp):
            raise PortContractError(f"RecipeReply.stamp 는 Stamp 여야 한다({type(self.stamp).__name__})")
        if not isinstance(self.recipe, FlavorRecipe):
            raise PortContractError(f"RecipeReply.recipe 는 FlavorRecipe 여야 한다({type(self.recipe).__name__})")
        object.__setattr__(self, "warnings", _str_tuple(self.warnings))

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "RecipeReply":
        if not isinstance(d, Mapping):
            raise PortContractError(f"RecipeReply.from_dict: Mapping 이 아니다({type(d).__name__})")
        missing = [k for k in ("domain", "version", "stamp", "recipe") if k not in d]
        if missing:
            raise PortContractError(f"RecipeReply.from_dict: 필수 키 누락 {missing}")
        return cls(domain=d["domain"], version=d["version"], stamp=Stamp.from_dict(d["stamp"]),
                   recipe=FlavorRecipe.from_dict(d["recipe"]), is_valid=bool(d.get("is_valid", True)),
                   warnings=tuple(d.get("warnings") or ()), result_type=str(d.get("result_type") or ""),
                   state=dict(d.get("state") or {}))

    def to_dict(self) -> dict[str, Any]:
        return {"domain": self.domain, "version": self.version, "stamp": self.stamp.to_dict(),
                "recipe": self.recipe.to_dict(), "is_valid": self.is_valid, "warnings": list(self.warnings),
                "result_type": self.result_type, "state": dict(self.state)}


class RecipePort(VersionPort):
    """레시피를 만드는 함수 — 연구소(관호)가 이 클래스를 상속해 어댑터를 만든다.

    계약 불변식 (구현이 반드시 지킬 것):
      1. 재진입: generate()는 self의 어떤 상태도 바꾸지 않는다. 같은 인스턴스로
         여러 번·동시에 불러도 호출끼리 간섭하지 않는다.
      2. 부작용은 인자로: 밖으로 나가는 호출(LLM)은 llm 인자를 통해서만.
         llm=None이면 구현 기본 클라이언트를 쓴다 (현행 프로덕션 동작).
      3. 같은 입력 + 같은 llm 응답 → 같은 반환 dict.

    반환 = RecipeReply(클래스). 와이어는 `to_dict()`.
    """

    @abstractmethod
    def generate(self, request: RecipeParam, llm: LlmPort | None = None) -> RecipeReply:
        """레시피 생성 — prompt 가 지배한다. 위 불변식 참조.

        """
        ...

    # ⛔ regenerate 없음 — 식향에는 재조향 개념이 없다(기획 D2 · 2026-08-14). 이 세대는 generate 하나만 부른다.
