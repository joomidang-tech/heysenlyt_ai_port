"""sensorium-fragrance-1.0.0 — 레시피 계약. 의존성 0.

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

    id        : 향료 id — **필수 · 비면 PortContractError.** 이 세대 카탈로그 키를 소문자로 정규화한 값.
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
# `notes` 의 문자열은 **향료 id** 다 — 레시피 `RecipeNote.id` · web 포트 매핑 키와 같은 문자열. 이 세대의 id 는
#   엔진 카탈로그 키를 소문자로 정규화한 값이다(예 "Bitter Lemon" → "bitter lemon" = 지금 web 포트 매핑 값 · 마이그레이션 0).
#   어댑터는 대소문자를 가리지 않고 받는다(web 이 아직 원래 키를 보내는 창). 두 트랙 모두 web 이 같은 키의 미러를 들고 있다:
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


# ## 레시피 호출 옵션 — `RecipeParam.params` · `RegenerateParam.params` (2026-09-29 · dict → 클래스)
_OPTION_KEYS = {  # 와이어 키 → 필드명 (어댑터 허용목록과 같은 집합 — 밖의 키는 PortContractError)
    "temperature": "temperature", "complexity": "complexity", "ratio": "ratio",
    "name": "name", "nameKo": "name_ko", "nameJa": "name_ja",
    "story": "story", "storyKo": "story_ko", "storyJa": "story_ja",
}
_RATIO_KEYS = ("TOP", "MIDDLE", "BASE")


def _is_num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


@dataclass(frozen=True)
class LayerRatio:
    """층별 비중(`params.ratio` · 와이어 키 "TOP"·"MIDDLE"·"BASE"). 빠진 층은 어댑터 기본값."""

    top: float | None = None
    middle: float | None = None
    base: float | None = None

    def __post_init__(self) -> None:
        for f in ("top", "middle", "base"):
            v = getattr(self, f)
            if v is not None and not _is_num(v):
                raise PortContractError(f"LayerRatio.{f} 는 숫자여야 한다({v!r})")

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "LayerRatio":
        if not isinstance(d, Mapping):
            raise PortContractError(f"LayerRatio.from_dict: Mapping 이 아니다({type(d).__name__})")
        bad = sorted(set(d) - set(_RATIO_KEYS))
        if bad:
            raise PortContractError(f"RecipeOptions.ratio 는 {list(_RATIO_KEYS)} 만 받는다({bad})")
        return cls(**{k.lower(): d[k] for k in _RATIO_KEYS if d.get(k) is not None})

    def to_dict(self) -> dict[str, float]:
        return {k: getattr(self, k.lower()) for k in _RATIO_KEYS if getattr(self, k.lower()) is not None}


@dataclass(frozen=True)
class RecipeOptions:
    """향장향 레시피 호출 옵션. 모든 칸 선택(None = 어댑터 기본값).

    temperature : LLM 온도.
    complexity  : 노트 수 목표(정수 · 기본 8).
    ratio       : 층별 비중 {"TOP","MIDDLE","BASE"} → 숫자(기본 0.30 · 0.50 · 0.20).
    name·name_ko·name_ja·story·story_ko·story_ja : 대화가 확정한 향 이름·스토리(web `nameStory`). 비면 어댑터가 짓는다.
    """

    temperature: float | None = None
    complexity: int | None = None
    ratio: LayerRatio | None = None
    name: str | None = None
    name_ko: str | None = None
    name_ja: str | None = None
    story: str | None = None
    story_ko: str | None = None
    story_ja: str | None = None

    def __post_init__(self) -> None:
        if self.temperature is not None and not _is_num(self.temperature):
            raise PortContractError(f"RecipeOptions.temperature 는 숫자여야 한다({self.temperature!r})")
        if self.complexity is not None and (isinstance(self.complexity, bool) or not isinstance(self.complexity, int)):
            raise PortContractError(f"RecipeOptions.complexity 는 정수여야 한다({self.complexity!r})")
        if self.ratio is not None and not isinstance(self.ratio, LayerRatio):
            raise PortContractError(f"RecipeOptions.ratio 는 LayerRatio 여야 한다({type(self.ratio).__name__})")
        for f in ("name", "name_ko", "name_ja", "story", "story_ko", "story_ja"):
            v = getattr(self, f)
            if v is not None and not isinstance(v, str):
                raise PortContractError(f"RecipeOptions.{f} 는 문자열이어야 한다({type(v).__name__})")

    @classmethod
    def from_dict(cls, d: Mapping[str, Any] | None) -> "RecipeOptions":
        d = d or {}
        if not isinstance(d, Mapping):
            raise PortContractError(f"RecipeOptions.from_dict: Mapping 이 아니다({type(d).__name__})")
        bad = sorted(set(d) - set(_OPTION_KEYS))
        if bad:
            raise PortContractError(f"허용되지 않는 params: {bad} (fragrance 허용: {sorted(_OPTION_KEYS)})")
        known = {f: d[w] for w, f in _OPTION_KEYS.items() if d.get(w) is not None}
        if "ratio" in known:
            known["ratio"] = LayerRatio.from_dict(known["ratio"])
        return cls(**known)

    def to_dict(self) -> dict[str, Any]:
        """와이어 키(camelCase) · None 칸 생략 — 어댑터 엔진이 읽는 dict 모양 그대로."""
        out: dict[str, Any] = {}
        for w, f in _OPTION_KEYS.items():
            v = getattr(self, f)
            if v is not None:
                out[w] = v.to_dict() if f == "ratio" else v
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

    ⛔ prior 필드는 없다 — 재조향은 이 DTO 가 아니라 **RegenerateParam** 이다(계약상 별개 동작).
       nullable prior 로 두 동작을 한 타입에 얹으면 "무엇이 지배하나"가 타입에서 사라진다.
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
class RegenerateParam:
    """재조향 한 번 — 손님이 결과를 맡아보고 "이렇게 바꿔줘"를 넣은 상황.

    generate 와 **별개 동작**이라 별개 DTO 로 둔다. 두 동작의 차이는 prior 유무가 아니라
    **무엇이 결과를 지배하느냐**다:

      generate    : prompt 가 지배. 백지에서 만든다.
      regenerate  : feedback 이 지배. prior 는 "직전엔 이랬다"는 **참고 맥락일 뿐 픽스가 아니다**
                    — 결과가 prior 와 크게 달라지는 것이 정상이고, 그래야 맞다.

    이 구분이 기획 결정(2026-08-14 D1 "B 방식")이다. 미세조정(A′ — prior 를 base 로 깔고
    비율만 만지는 쪽)은 **기각됐다.** 어댑터가 그 둘을 헷갈리지 않도록 계약 표면에서 갈라 둔다.

    feedback    : 손님이 적은 수정 방향. 예 "덜 우디하게" / "잔향을 더 진하게" (≤300자, 화면 규칙)
    prior       : 직전 generate/regenerate 가 돌려준 **레시피**(FragranceRecipe). 참고 맥락.
                  ⛔ 상태는 어댑터가 아니라 호출자(서버)가 보관한다 — 재진입 안전의 전제.
                  ⚠️ 옛 레시피(id 없는 줄)는 통합코드가 경계에서 id 를 채워 넣는다 — 포트는 id 없는 줄을 받지 않는다.
    prior_stamp : 그 레시피의 도장(모르면 None). 새로 만들지 않고 prior 를 그대로 돌려주는 경로가 이어받는다.
    mode/lang/params : RecipeParam 과 같은 의미.
    """

    feedback: str
    prior: FragranceRecipe
    mode: str | None = None
    lang: str = "ko"
    params: RecipeOptions = field(default_factory=RecipeOptions)  # (2026-09-29) dict → 옵션 클래스
    # (2026-09-20) 이번 요청에서 **쓸 수 있는 향료** — 그 기기에 실제로 꽂혀 있는 것. None = 제한 없음(현행).
    #   계약·어휘·실패 규약 정본 = 이 파일 `Palette` 절. ⚠️ 신규 필드라 **끝에** 둔다(위치인자 소비자 호환).
    palette: Palette | None = None
    # (2026-09-29) prior 의 도장 — prior 가 dict 였을 땐 그 안에 있었다. 레시피가 클래스가 되며 칸이 갈렸다.
    prior_stamp: Stamp | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.prior, FragranceRecipe):
            raise PortContractError(f"RegenerateParam.prior 는 FragranceRecipe 여야 한다({type(self.prior).__name__})")
        if self.prior_stamp is not None and not isinstance(self.prior_stamp, Stamp):
            raise PortContractError(f"RegenerateParam.prior_stamp 는 Stamp 여야 한다({type(self.prior_stamp).__name__})")
        if not isinstance(self.params, RecipeOptions):
            raise PortContractError(f"RegenerateParam.params 는 RecipeOptions 여야 한다({type(self.params).__name__})")


@dataclass(frozen=True)
class RecipeReply:
    """generate·regenerate 출력(클래스 · 2026-09-29). `to_dict()` 가 와이어 JSON 이자 다음 요청의 prior 원천.

    stamp  : 도장(Stamp).
    recipe : 레시피(FragranceRecipe) — 향료 줄마다 id 필수.
    """

    domain: str  # "fragrance"
    version: str  # "1.0.0"
    stamp: Stamp
    recipe: FragranceRecipe
    is_valid: bool = True
    warnings: tuple[str, ...] = ()
    result_type: str = ""  # "module:Class" — prior 복원 힌트(와이어 값)
    state: Mapping[str, Any] = field(default_factory=dict)  # 호출자 보관 상태(불투명)

    def __post_init__(self) -> None:
        if not isinstance(self.stamp, Stamp):
            raise PortContractError(f"RecipeReply.stamp 는 Stamp 여야 한다({type(self.stamp).__name__})")
        if not isinstance(self.recipe, FragranceRecipe):
            raise PortContractError(f"RecipeReply.recipe 는 FragranceRecipe 여야 한다({type(self.recipe).__name__})")
        object.__setattr__(self, "warnings", _str_tuple(self.warnings))

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "RecipeReply":
        if not isinstance(d, Mapping):
            raise PortContractError(f"RecipeReply.from_dict: Mapping 이 아니다({type(d).__name__})")
        missing = [k for k in ("domain", "version", "stamp", "recipe") if k not in d]
        if missing:
            raise PortContractError(f"RecipeReply.from_dict: 필수 키 누락 {missing}")
        return cls(domain=d["domain"], version=d["version"], stamp=Stamp.from_dict(d["stamp"]),
                   recipe=FragranceRecipe.from_dict(d["recipe"]), is_valid=bool(d.get("is_valid", True)),
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

    반환 = RecipeReply(클래스). 와이어는 `to_dict()`. 그 `recipe` 를 RegenerateParam.prior 로 넣으면 재조향.
    """

    @abstractmethod
    def generate(self, request: RecipeParam, llm: LlmPort | None = None) -> RecipeReply:
        """레시피 생성 — prompt 가 지배한다. 위 불변식 참조.

        재조향(손님 피드백 반영)은 이 메서드가 아니라 regenerate() 다.
        """
        ...

    @abstractmethod
    def regenerate(
        self, request: RegenerateParam, llm: LlmPort | None = None
    ) -> RecipeReply:
        """재조향 — **feedback 이 지배**하는 신규 레시피. prior 는 참고 맥락(픽스 아님).

        generate 와 갈라 둔 이유: 두 동작은 "지배하는 입력"이 다르다. 한 메서드에 nullable
        prior 로 얹으면 그 차이가 타입에서 사라지고, 어댑터마다 "prior 를 얼마나 존중하나"가
        갈린다. 기획 결정(B 방식)은 **크게 달라지는 것이 정상**이다 — 그걸 계약에 박아 둔다.

        구현은 생성 경로를 generate 와 공유해도 된다(프롬프트를 무엇으로 만드느냐만 다르다).
        계약이 요구하는 건 **두 동작이 호출자에게 구분되어 보이는 것**이지 코드 분리가 아니다.

        불변식은 generate 와 동일(재진입·부작용은 인자로·같은 입력이면 같은 반환).
        """
        ...
