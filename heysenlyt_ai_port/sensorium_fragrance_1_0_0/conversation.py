"""sensorium-fragrance-1.0.0 — 대화 계약. 의존성 0.

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


@dataclass(frozen=True)
class Demographics:
    """손님 인구통계 — v1.2.0 대화가 톤·추천에 반영하던 값 (선택)."""

    gender: str = ""  # "male" | "female" | "" (미지정)
    age: int = 0  # 0 = 미지정

    def __post_init__(self) -> None:
        if not isinstance(self.gender, str):
            raise PortContractError(f"Demographics.gender 는 문자열이어야 한다({type(self.gender).__name__})")
        if isinstance(self.age, bool) or not isinstance(self.age, int) or self.age < 0:
            raise PortContractError(f"Demographics.age 는 0 이상 정수여야 한다({self.age!r})")


# ## 대화 입력·출력의 형식 있는 칸 — 클래스로 강제한다 (2026-09-29)
#
# 포트는 인터페이스라 파라미터·리턴이 전부 클래스다. dict 로 받던 `params`·`last_known_axes`·`result` 도 형식이 정해져
#   있으므로 클래스로 둔다. 통합코드가 web JSON 을 **경계에서 한 번** `from_dict` 로 편다 — 허용 밖 키·타입 위반은
#   PortContractError(ValueError·TypeError 하위). 와이어(JSON) 키는 오늘 그대로(`to_dict`).


def _reject_unknown(cls_name: str, d: Mapping[str, Any], allowed: tuple[str, ...], label: str) -> None:
    bad = sorted(set(d) - set(allowed))
    if bad:
        raise PortContractError(f"허용되지 않는 {label}: {bad} ({cls_name} 허용: {sorted(allowed)})")


def _opt_str(cls_name: str, key: str, v: Any) -> None:
    if v is not None and not isinstance(v, str):
        raise PortContractError(f"{cls_name}.{key} 는 문자열이어야 한다({type(v).__name__})")


@dataclass(frozen=True)
class KnownAxes:
    """식향 대화의 지난 턴 제출 축 에코(v1.2.0 lastKnownAxes) — 통합코드는 판정 않고 그대로 넘긴다.

    web 이 보내는 키는 셋뿐(`app/api/chat/route.ts` lastKnownAxes: scene · mood · taste). 값이 없는 축은 None.
    """

    scene: str | None = None
    mood: str | None = None
    taste: str | None = None

    _KEYS = ("scene", "mood", "taste")

    def __post_init__(self) -> None:
        for k in self._KEYS:
            _opt_str("KnownAxes", k, getattr(self, k))

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "KnownAxes":
        if not isinstance(d, Mapping):
            raise PortContractError(f"KnownAxes.from_dict: Mapping 이 아니다({type(d).__name__})")
        _reject_unknown("KnownAxes", d, cls._KEYS, "last_known_axes 키")
        return cls(**{k: d.get(k) for k in cls._KEYS})

    def to_dict(self) -> dict[str, str]:
        return {k: getattr(self, k) for k in self._KEYS if getattr(self, k) is not None}


# 향장향 대화 결과 — submitFragranceResult 도구 인자(engine/conversation.py submit_fragrance_result_tool).
_RESULT_KEYS = {  # 와이어 키 → 필드명
    "emotion": "emotion", "memory": "memory", "place": "place", "fragranceName": "fragrance_name", "story": "story",
    "koEmotion": "ko_emotion", "koMemory": "ko_memory", "koPlace": "ko_place",
    "koFragranceName": "ko_fragrance_name", "koStory": "ko_story",
}


@dataclass(frozen=True)
class ChatResult:
    """대화가 "지금 만들 수 있음"을 제출했을 때의 취향 축(향장향). 모든 칸 선택 — 모델이 채운 것만 있다.

    extra : 도구 스키마 밖 키(모델이 덧붙인 것) — 그대로 보존(와이어 불변). 계약 필드와 겹치면 PortContractError.
    """

    emotion: str | None = None
    memory: str | None = None
    place: str | None = None
    fragrance_name: str | None = None
    story: str | None = None
    ko_emotion: str | None = None
    ko_memory: str | None = None
    ko_place: str | None = None
    ko_fragrance_name: str | None = None
    ko_story: str | None = None
    extra: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        extra = self.extra
        if not isinstance(extra, Mapping):
            raise PortContractError(f"ChatResult.extra 는 Mapping 이어야 한다({type(extra).__name__})")
        clash = sorted(set(extra) & (set(_RESULT_KEYS) | set(_RESULT_KEYS.values())))
        if clash:
            raise PortContractError(f"ChatResult.extra 가 계약 필드와 겹친다: {clash}")
        object.__setattr__(self, "extra", dict(extra))
        for f in _RESULT_KEYS.values():
            _opt_str("ChatResult", f, getattr(self, f))

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "ChatResult":
        if not isinstance(d, Mapping):
            raise PortContractError(f"ChatResult.from_dict: Mapping 이 아니다({type(d).__name__})")
        known = {f: d[w] for w, f in _RESULT_KEYS.items() if w in d and d[w] is not None}
        extra = {k: v for k, v in d.items() if k not in _RESULT_KEYS}
        return cls(**known, extra=extra)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {w: getattr(self, f) for w, f in _RESULT_KEYS.items() if getattr(self, f) is not None}
        out.update(self.extra)
        return out


@dataclass(frozen=True)
class ConversationOptions:
    """대화 호출 옵션(`ConversationParam.params`) — 향장향 대화는 옵션을 받지 않는다(빈 클래스 · 밖의 키는 거부)."""

    @classmethod
    def from_dict(cls, d: Mapping[str, Any] | None) -> "ConversationOptions":
        d = d or {}
        if not isinstance(d, Mapping):
            raise PortContractError(f"ConversationOptions.from_dict: Mapping 이 아니다({type(d).__name__})")
        _reject_unknown("fragrance", d, (), "params")
        return cls()

    def to_dict(self) -> dict[str, Any]:
        return {}


@dataclass(frozen=True)
class ConversationParam:
    """대화 한 턴 — v1.2.0 `POST /api/chat` ChatRequestBody 대응.

    message=None + kickoff=True 이면 대화 시작(AI 선 발화·첫 질문).
    상태(대화 기록)는 호출자(서버)가 history로 보관·회송한다 — RecipePort.prior와 같은 왕복 규약.
    """

    domain: str  # "fragrance"(향장향) | "flavor"(식향)
    message: str | None = None  # 손님 발화(userMessage). None+kickoff=첫 발화 요청
    history: tuple[tuple[str, str], ...] = ()  # ((role, content), ...) role: "user"|"assistant"
    lang: str = "ko"  # "ko"|"en"|"ja"|"vi"
    demographics: Demographics | None = None
    kickoff: bool = False  # 첫 턴 AI 선 발화
    # 식향 전용(v1.2.0 §E) — 클라가 지난 턴 자기 제출 축을 회송(통합코드는 판정 않고 에코).
    last_known_axes: KnownAxes | None = None  # (2026-09-29) dict → KnownAxes
    params: ConversationOptions = field(default_factory=ConversationOptions)  # (2026-09-29) dict → 옵션 클래스
    # 이 호출은 **발화(텍스트)를 반드시 받아야 한다**고 호출자가 요구하는 축.
    #   왜 필요한가 — 모델이 도구만 부르고 텍스트를 빠뜨리는 턴이 있다(실측 2026-08-15:
    #   content 빈 채 tool_calls=['suggestKeywords']). 그때 호출자는 재호출로 메우려 하는데,
    #   **같은 조건으로 다시 부르면 같은 답이 온다**(실측 재호출 성공률 0/2). 조건을 바꿀
    #   손잡이가 계약에 없어서 재호출이 구조적으로 무의미했다.
    #   ⚠️ 무엇을 요구하는지만 정한다 — **어떻게 보장할지는 어댑터 소유**(도구 회수·넛지·프롬프트
    #   강화 중 무엇을 쓸지는 구현 자유). 호출자는 "텍스트가 필요하다"까지만 말한다.
    #   ⚠️ 이 호출의 산출물은 **발화뿐**이라고 봐야 한다 — 도구를 회수하는 구현이면 keywords·
    #   done·result 가 비어 돌아온다. 호출자는 직전 턴의 그 값들을 유지하고 발화만 취한다.
    require_text: bool = False
    # (2026-09-11) `require_keywords`(칩 전용 호출 축, 2026-08-16 신설)는 **삭제**됐다 — 객관식 칩이
    #   제품에서 폐기돼 받을 산출물 자체가 없다. 마지막 필드였으므로 위치인자 호환은 깨지지 않는다.


    def __post_init__(self) -> None:
        if self.last_known_axes is not None and not isinstance(self.last_known_axes, KnownAxes):
            raise PortContractError(f"ConversationParam.last_known_axes 는 KnownAxes 여야 한다({type(self.last_known_axes).__name__})")
        if not isinstance(self.params, ConversationOptions):
            raise PortContractError(f"ConversationParam.params 는 ConversationOptions 여야 한다({type(self.params).__name__})")
        if self.demographics is not None and not isinstance(self.demographics, Demographics):
            raise PortContractError(f"ConversationParam.demographics 는 Demographics 여야 한다({type(self.demographics).__name__})")

@dataclass(frozen=True)
class ConverseReply:
    """converse 출력 — v1.2.0 SSE(token·tool·done)를 한 턴 결과로 접은 형태.

    reply    : AI 발화 전체(v1.2.0 token 델타 누적분).
    keywords : ⚠️ 폐기(2026-09-11) — 객관식 칩 제거. **항상 빈 리스트.** 위치인자 4번째라 자리만 유지한다
               (지우면 위치인자 소비자가 깨진다). 호출자는 이 값을 읽지 않는다.
    done     : readiness 툴이 호출됨(취향 축 제출 완료). v1.2.0 finishReason="tool" 계열.
               ⛔ done=True 여도 대화는 계속될 수 있다(더 깊어지면 갱신 재제출) — 종료가 아니라
               "지금 만들 수 있음" 신호. 실제 확정(제조/조향)은 별도 레시피 호출.
    result   : done일 때 취향 축 페이로드.
               식향 = {scene,mood,taste,drinkTitle,reason,(recipeId),(ko*)}
               향장향 = {emotion,memory,place,fragranceName,story,(ko*)}
    history  : 이번 턴 반영한 갱신 기록 — 통째가 다음 요청의 history.
    """

    reply: str
    done: bool = False
    result: ChatResult | None = None  # (2026-09-29) 취향 축 — 도구 인자를 클래스로(스키마 밖 키는 extra 보존)
    keywords: tuple[str, ...] = ()  # 폐기 — 항상 () (위치인자 호환용 자리)
    history: tuple[tuple[str, str], ...] = ()
    # 대화도 4개 독립 능력 중 하나 — 자기 버전 도장을 싣는다(어댑터가 3값 합쳐 kernel_version 제공).
    #   (2026-09-29) dict → Stamp. 모르면 None(와이어는 오늘처럼 `{}`).
    stamp: Stamp | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.reply, str):
            raise PortContractError(f"ConverseReply.reply 는 문자열이어야 한다({type(self.reply).__name__})")
        if self.stamp is not None and not isinstance(self.stamp, Stamp):
            raise PortContractError(f"ConverseReply.stamp 는 Stamp 여야 한다({type(self.stamp).__name__})")
        if self.result is not None and not isinstance(self.result, ChatResult):
            raise PortContractError(f"ConverseReply.result 는 ChatResult 여야 한다({type(self.result).__name__})")
        object.__setattr__(self, "keywords", tuple(self.keywords or ()))
        object.__setattr__(self, "history", tuple((str(r), str(c)) for r, c in (self.history or ())))

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "ConverseReply":
        if not isinstance(d, Mapping):
            raise PortContractError(f"ConverseReply.from_dict: Mapping 이 아니다({type(d).__name__})")
        if "reply" not in d:
            raise PortContractError("ConverseReply.from_dict: 필수 키 'reply' 누락")
        stamp = d.get("stamp")
        res = d.get("result")
        return cls(reply=d["reply"], done=bool(d.get("done", False)),
                   result=ChatResult.from_dict(res) if res is not None else None,
                   keywords=tuple(d.get("keywords") or ()), history=tuple(tuple(h) for h in (d.get("history") or ())),
                   stamp=Stamp.from_dict(stamp) if stamp else None)

    def to_dict(self) -> dict[str, Any]:
        return {"reply": self.reply, "done": self.done,
                "result": self.result.to_dict() if self.result is not None else None,
                "keywords": list(self.keywords), "history": [list(h) for h in self.history],
                "stamp": self.stamp.to_dict() if self.stamp is not None else {}}


class ConversationPort(VersionPort):
    """대화 함수의 약속 — 반환 = ConverseReply(클래스 · 2026-09-29). 와이어는 `to_dict()`:
    {"reply": AI 발화, "keywords": 폐기(항상 []), "done": readiness 제출됨,
     "result": done일 때 취향 축 페이로드|None, "history": 갱신된 기록}.
    history 통째가 다음 요청의 history. 재진입·llm 인자 주입 불변식은 RecipePort와 동일.
    """

    @abstractmethod
    def converse(self, request: ConversationParam, llm: LlmPort | None = None) -> ConverseReply:
        ...
