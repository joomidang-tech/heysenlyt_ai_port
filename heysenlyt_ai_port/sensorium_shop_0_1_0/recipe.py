"""sensorium-shop-0.1.0 — 센릿샵 레시피 계약(APP-RECIPE · TAB-RECIPE · 수정본 포함). 의존성 0.

기획 정본: HoS AI PRD 2부(§10~§14) · 정책보드 APP-RECIPE.

| 화면 요소 | 만드는 쪽 | 이 계약의 칸 |
|---|---|---|
| 이름(1~20자 · 향료 이름 없음) | AI | `ShopRecipe.name` |
| 설명(한 줄 · 「~향」으로 끝남) | AI | `ShopRecipe.description` |
| 조향 노트(손님 말을 근거로 한 이유 · 넣은 것과 뺀 것) | AI | `ShopRecipe.composer_note` |
| 향료 구성 | 엔진 | `ShopRecipe.notes[]`(id 필수 · palette 안의 id 만) |
| 향 계열 | 매핑표(통합코드) | — 이 계약에 없다 |

## 통합코드 몫 (어댑터가 하지 않는 것)
  · 버튼 시점 · 멱등(같은 대화로 두 번 만들지 않기) · 최소 2초 / 60초 실패 · 다시 시도.
  · **이름 20자 초과 · 같은 계정에 같은 이름** → AI 를 다시 부르지 않고 통합코드가 다시 짓는다(「이름 2」).
  · 저장·표시·향 계열 매핑. `is_valid=False` 면 저장하지 않고 「레시피를 만들지 못했어요」.

## 수정본 = 새 레시피 (2부 §13)
  재조향(`regenerate`)이 아니라 **같은 `generate`** 에 수정 대화(`params.conversation`)와 원본 맥락(`params.revise`)을 싣는다.
  이름·설명·노트를 새로 짓고, 노트의 근거는 수정 대화에서 들은 말이다(원본 노트를 고쳐 쓰지 않는다).
"""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from heysenlyt_ai_port.errors import PortContractError
from heysenlyt_ai_port.llm import LlmPort
from heysenlyt_ai_port.sensorium_shop_0_1_0.revise import MAX_TURNS, ReviseContext, ScentBrief, Turn, turns_from_wire
from heysenlyt_ai_port.version import Stamp, VersionPort

_NOTE_KEYS = {  # 와이어 키 → 필드명 — 향장향 세대와 같은 와이어(통합코드의 포트 매핑·표시가 그대로 읽는다)
    "id": "id", "name": "name", "nameKo": "name_ko", "nameJa": "name_ja",
    "amountMl": "amount_ml", "percent": "percent", "type": "type",
    "description": "description", "descriptionKo": "description_ko", "descriptionJa": "description_ja",
}
_RECIPE_KEYS = {
    "name": "name", "description": "description", "composerNote": "composer_note", "totalVolumeMl": "total_volume_ml",
}


def _freeze_extra(obj: Any, known: set[str] | frozenset[str]) -> None:
    extra = getattr(obj, "extra")
    if not isinstance(extra, Mapping):
        raise PortContractError(f"{type(obj).__name__}.extra 는 Mapping 이어야 한다({type(extra).__name__})")
    clash = sorted(set(extra) & set(known))
    if clash:
        raise PortContractError(f"{type(obj).__name__}.extra 가 계약 필드와 겹친다: {clash}")
    object.__setattr__(obj, "extra", dict(extra))


@dataclass(frozen=True)
class Palette:
    """이번 요청에서 쓸 수 있는 향료 — 그 기기·매장에 실제로 꽂혀 있는 것(향료 id 튜플).
    ⛔ 양(mL)·포트 번호·펌프 주소는 싣지 않는다. 계약·실패 규약은 향장향 세대 `Palette` 절과 같다
    (None = 제한 없음 · 목록 밖 키 무시 · 너무 적으면 `is_valid=False` · 빈 목록은 통합코드가 422).
    notes 는 비어 있지 않은 문자열의 튜플이다(목록으로 주면 튜플로 바꾼다 · 그 밖의 모양은 `PortContractError`)."""

    notes: tuple[str, ...]

    def __post_init__(self) -> None:
        n = self.notes
        if isinstance(n, (str, bytes)) or not isinstance(n, (list, tuple)):
            raise PortContractError(f"Palette.notes 는 향료 id 목록이어야 한다({type(n).__name__})")
        if not all(isinstance(x, str) and x.strip() for x in n):
            raise PortContractError("Palette.notes 의 항목은 비어 있지 않은 문자열이어야 한다")
        object.__setattr__(self, "notes", tuple(n))


@dataclass(frozen=True)
class RecipeNote:
    """향료 한 줄 — id 필수(매핑 전용) · name 필수(표시 전용). 향장향 세대와 같은 규칙."""

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
            raise PortContractError(f"RecipeNote.id 는 비어 있지 않은 문자열이어야 한다: {self.id!r}")
        if not isinstance(self.name, str) or not self.name.strip():
            raise PortContractError(f"RecipeNote.name 은 비어 있지 않은 문자열이어야 한다: {self.name!r}")

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "RecipeNote":
        if not isinstance(d, Mapping) or "id" not in d:
            raise PortContractError("RecipeNote.from_dict: Mapping 이 아니거나 필수 키 'id' 누락")
        known = {f: d[w] for w, f in _NOTE_KEYS.items() if w in d}
        return cls(**known, extra={k: v for k, v in d.items() if k not in _NOTE_KEYS})

    def to_dict(self) -> dict[str, Any]:
        out = {w: getattr(self, f) for w, f in _NOTE_KEYS.items() if getattr(self, f) is not None}
        out.update(self.extra)
        return out


@dataclass(frozen=True)
class ShopRecipe:
    """센릿샵 레시피 — 텍스트는 요청 `lang` 한 언어로 쓴다(언어별 칸을 따로 두지 않는다).

    name          : 이름(1~20자 · 향료 이름 없음 — 손님이 먼저 말했으면 예외). 넘거나 겹치면 통합코드가 처리.
    description   : 한 줄 설명 — 「~향」으로 끝난다 · 향료 이름 없음.
    composer_note : 조향 노트 — 손님이 한 말을 1개 이상 알아볼 수 있게 넣고, 조향 결정마다 근거가 된 손님 말이 있다.
                    넣은 것뿐 아니라 뺀 것도 이유와 함께 · 향료 이름·계열 없음 · 질문·감탄으로 닫지 않는다.
    brief         : 이 레시피를 만든 요점(`ScentBrief` · **필수**) — 손님이 말하지 않은 칸은 추정·기본값으로 채우고 `inferred` 에 적는다
                    (PRD §4 「못 받으면」: 목적 = 내 몸에 뿌릴 향 · 느낌 = 대화에서 추정 · §5: 피할 향 = 없음 `()`).
                    통합코드가 레시피에 저장해 다음 수정 때 `ReviseContext.brief` 로 돌려준다(피할 향의 정식 통로).
    notes         : 향료 구성(엔진) — 비면 `is_valid=False` 와 함께.
    """

    name: str
    description: str
    composer_note: str
    brief: ScentBrief
    notes: tuple[RecipeNote, ...] = ()
    total_volume_ml: float | None = None
    extra: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _freeze_extra(self, set(_RECIPE_KEYS) | {"notes", "brief"})
        if not isinstance(self.brief, ScentBrief):
            raise PortContractError("ShopRecipe.brief 는 ScentBrief 여야 한다")
        for k in ("name", "description", "composer_note"):
            if not isinstance(getattr(self, k), str):
                raise PortContractError(f"ShopRecipe.{k} 는 문자열이어야 한다")
        object.__setattr__(self, "notes", tuple(self.notes or ()))
        if not all(isinstance(n, RecipeNote) for n in self.notes):
            raise PortContractError("ShopRecipe.notes 의 항목은 RecipeNote 여야 한다")

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "ShopRecipe":
        if not isinstance(d, Mapping):
            raise PortContractError("ShopRecipe.from_dict: Mapping 이 아니다")
        known = {f: d[w] for w, f in _RECIPE_KEYS.items() if w in d}
        known.setdefault("name", "")
        known.setdefault("description", "")
        known.setdefault("composer_note", "")
        if d.get("brief") is None:
            raise PortContractError("ShopRecipe.from_dict: 필수 키 'brief' 누락")
        notes = tuple(RecipeNote.from_dict(n) for n in (d.get("notes") or ()))
        return cls(**known, brief=ScentBrief.from_dict(d["brief"]), notes=notes,
                   extra={k: v for k, v in d.items() if k not in _RECIPE_KEYS and k not in ("notes", "brief")})

    def to_dict(self) -> dict[str, Any]:
        out = {w: getattr(self, f) for w, f in _RECIPE_KEYS.items() if getattr(self, f) is not None}
        out["brief"] = self.brief.to_dict()
        out["notes"] = [n.to_dict() for n in self.notes]
        out.update(self.extra)
        return out


_OPTION_KEYS = ("conversation", "revise", "takenNames")
MAX_TAKEN_NAMES = 500
MAX_TAKEN_NAME_CHARS = 40


@dataclass(frozen=True)
class RecipeOptions:
    """레시피 호출 옵션(`RecipeParam.params`) — 와이어 키 `conversation` · `revise`. 밖의 키는 거부.

    conversation : 이 레시피의 대화 **전체**(`Turn` · 손님·AI 둘 다 · 수정본이면 수정 대화 · ≤ 100턴). **필수 · 비면 안 된다.**
                   조향 노트가 「손님 말을 근거로 왜 이렇게 만들었나」를 쓰려면 AI 질문까지 있어야 한다.
    revise       : 수정본일 때 원본 맥락. 새 레시피일 땐 None.
    taken_names  : 그 계정에 이미 있는 레시피 이름(≤ 500개 · 각 ≤ 40자) — 이름을 지을 때 피한다(PRD 2부 §11 · 겹치면 통합코드가 「이름 2」로 마무리).
    """

    conversation: tuple[Turn, ...]
    revise: ReviseContext | None = None
    taken_names: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "conversation", turns_from_wire(self.conversation, "RecipeOptions.conversation",
                                                                 max_turns=MAX_TURNS))
        if not self.conversation:
            raise PortContractError("RecipeOptions.conversation 은 비어 있으면 안 된다")
        if self.revise is not None and not isinstance(self.revise, ReviseContext):
            raise PortContractError("RecipeOptions.revise 는 ReviseContext 여야 한다")
        tn = self.taken_names
        if isinstance(tn, str) or not isinstance(tn, (list, tuple)) or not all(isinstance(x, str) for x in tn):
            raise PortContractError("RecipeOptions.taken_names 는 문자열 목록이어야 한다")
        if len(tn) > MAX_TAKEN_NAMES:
            raise PortContractError(f"RecipeOptions.taken_names 는 {MAX_TAKEN_NAMES}개 이하여야 한다({len(tn)}개)")
        if any(len(x) > MAX_TAKEN_NAME_CHARS for x in tn):
            raise PortContractError(f"RecipeOptions.taken_names 의 항목은 {MAX_TAKEN_NAME_CHARS}자 이하여야 한다")
        object.__setattr__(self, "taken_names", tuple(tn))

    @classmethod
    def from_dict(cls, d: Mapping[str, Any] | None) -> "RecipeOptions":
        d = d or {}
        if not isinstance(d, Mapping):
            raise PortContractError(f"RecipeOptions.from_dict: Mapping 이 아니다({type(d).__name__})")
        bad = sorted(set(d) - set(_OPTION_KEYS))
        if bad:
            raise PortContractError(f"허용되지 않는 params: {bad} (sensorium-shop 허용: {sorted(_OPTION_KEYS)})")
        rev = d.get("revise")
        return cls(conversation=turns_from_wire(d.get("conversation"), "params.conversation"),
                   revise=ReviseContext.from_dict(rev) if rev is not None else None,
                   taken_names=d.get("takenNames") or ())

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"conversation": [t.to_wire() for t in self.conversation],
                               "takenNames": list(self.taken_names)}
        if self.revise is not None:
            out["revise"] = self.revise.to_dict()
        return out


@dataclass(frozen=True)
class RecipeParam:
    """레시피 한 번(새 레시피 · 수정본 공용).

    prompt  : 손님 말을 이은 것(통합코드가 만든다 · ≤4000자) — 서버 라우트 공용 칸(로그 상관용). 판단 입력은 `params.conversation`.
    params  : `RecipeOptions`(대화 전체 · 수정 맥락 · 이미 있는 이름) — **필수**.
    palette : 설치된 향료 — None = **모름**(배치 조회 실패 · 어댑터는 자기 카탈로그에서 고르고 매핑 확인은 통합코드 주문 접수가 한다).
              빈 목록(「없음」)은 통합코드가 어댑터 전에 422 로 끊는다.
    lang    : 결과 텍스트 언어.
    """

    prompt: str
    params: RecipeOptions
    palette: Palette | None
    mode: str | None = None
    lang: str = "ko"

    def __post_init__(self) -> None:
        if not isinstance(self.params, RecipeOptions):
            raise PortContractError(f"RecipeParam.params 는 RecipeOptions 여야 한다({type(self.params).__name__})")
        if self.palette is not None and not isinstance(self.palette, Palette):
            raise PortContractError("RecipeParam.palette 는 Palette 또는 None 이어야 한다")


@dataclass(frozen=True)
class RecipeReply:
    """generate 출력. `is_valid=False` = 이 입력·구성으로는 못 만든다(지어내지 않고 정직하게 · 사유는 warnings).
    와이어의 `is_valid` 는 필수 bool 이다 — 빠지면 「성공」으로 간주하지 않고 `PortContractError`."""

    domain: str
    version: str
    stamp: Stamp
    recipe: ShopRecipe
    is_valid: bool = True
    warnings: tuple[str, ...] = ()
    result_type: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.stamp, Stamp):
            raise PortContractError("RecipeReply.stamp 는 Stamp 여야 한다")
        if not isinstance(self.recipe, ShopRecipe):
            raise PortContractError(f"RecipeReply.recipe 는 ShopRecipe 여야 한다({type(self.recipe).__name__})")
        if not isinstance(self.is_valid, bool):
            raise PortContractError(f"RecipeReply.is_valid 는 bool 이어야 한다({type(self.is_valid).__name__})")
        object.__setattr__(self, "warnings", tuple(str(w) for w in (self.warnings or ())))

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "RecipeReply":
        if not isinstance(d, Mapping):
            raise PortContractError("RecipeReply.from_dict: Mapping 이 아니다")
        missing = [k for k in ("domain", "version", "stamp", "recipe", "is_valid") if k not in d]
        if missing:
            raise PortContractError(f"RecipeReply.from_dict: 필수 키 누락 {missing}")
        return cls(domain=d["domain"], version=d["version"], stamp=Stamp.from_dict(d["stamp"]),
                   recipe=ShopRecipe.from_dict(d["recipe"]), is_valid=d["is_valid"],
                   warnings=tuple(d.get("warnings") or ()), result_type=str(d.get("result_type") or ""))

    def to_dict(self) -> dict[str, Any]:
        return {"domain": self.domain, "version": self.version, "stamp": self.stamp.to_dict(),
                "recipe": self.recipe.to_dict(), "is_valid": self.is_valid, "warnings": list(self.warnings),
                "result_type": self.result_type}


class RecipePort(VersionPort):
    """레시피를 만드는 함수 — 1회 호출. 불변식: 재진입(상태 0) · 부작용은 llm 인자로만 · 같은 입력+같은 llm 응답 → 같은 반환.
    ⛔ regenerate 는 없다 — 수정본도 generate(새 레시피)다."""

    @abstractmethod
    def generate(self, request: RecipeParam, llm: LlmPort | None = None) -> RecipeReply:
        ...
