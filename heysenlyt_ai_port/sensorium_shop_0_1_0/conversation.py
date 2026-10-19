"""sensorium-shop-0.1.0 — 센릿샵 대화 계약(APP-CHAT · APP-CHAT-EDIT · TAB 동일). 의존성 0.

기획 정본: HoS AI PRD 1부 · 정책보드 APP-CHAT·APP-CHAT-EDIT.

## 이 세대가 대화에 새로 받는 것 (향장향 1.0.0 대화와 다른 점)
  · `params.palette`            설치된 향료 — 「설치된 향료로 만들 수 없는 향은 약속하지 않는다」를 지키는 재료.
  · `params.aiTurn`            이번 답이 AI 발화 몇 번째인가 — 「#4 까지 필수 3개」.
  · `params.recipeButtonAiTurn` 버튼이 보이기 시작하는 AI 발화 번호 — 「서두르면 버튼이 곧 나온다고 안내」.
  · `params.revise`            수정 대화일 때 원본 맥락(`ReviseContext` · 원본 `ScentBrief` 포함).
  · `params.openingQuestion`   수정 대화의 **고정 첫 질문**(화면이 이미 띄운 문장) — 다시 묻지 않는다.
  응답 `result` = 지금까지 들은 요점(`ScentBrief`).

## 통합코드 몫 (어댑터가 하지 않는 것 — 「어댑터 = 순수 기능」)
  · 「레시피 만들기」 버튼 시점(AI 발화 #4 · 수정 대화는 첫 메시지 뒤) · 응답 대기 30초 · 다시 시도 3번 · 입력 상한.
  · 고정 첫 질문 고르기(가장 최근 시향 평가 → 3문장 중 하나) · 침묵 복구(`require_text` 재호출).

⛔ 하네스 형상 불변 — 통합코드의 침묵 복구 하네스가 모든 세대에 기대하는 칸(입력 `require_text` 등 · 출력 reply·done·
   result·keywords·history·stamp)을 그대로 갖는다(이 레포 형상 테스트가 잠근다).
"""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from heysenlyt_ai_port.errors import PortContractError
from heysenlyt_ai_port.llm import LlmPort
from heysenlyt_ai_port.sensorium_shop_0_1_0.recipe import Palette
from heysenlyt_ai_port.sensorium_shop_0_1_0.revise import MAX_TURNS, ReviseContext, ScentBrief, Turn, turns_from_wire
from heysenlyt_ai_port.version import Stamp, VersionPort

_OPTION_KEYS = ("palette", "aiTurn", "recipeButtonAiTurn", "revise", "openingQuestion")
MAX_OPENING_QUESTION_CHARS = 200


@dataclass(frozen=True)
class ConversationOptions:
    """대화 호출 옵션(`ConversationParam.params`) — 통합코드가 아는 값은 전부 여기로 넘긴다(어댑터가 추측하지 않게).

    palette              : 설치된 향료(id) — 「만들 수 없는 향은 약속하지 않는다」. **키 필수 · 값 None = 모름**(배치 조회 실패 —
                           모름 ≠ 없음 · 그때 어댑터는 자기 카탈로그 안에서 말하되 특정 향료를 장담하지 않는다).
    ai_turn              : 이번 답이 AI 발화 몇 번째인가(1부터 · 고정 첫 질문은 세지 않는다) — 「#4 까지 필수 3개」의 기준.
    recipe_button_ai_turn: 「레시피 만들기」 버튼이 보이기 시작하는 AI 발화 번호(새 대화 = 4 · 수정 대화 = 1 — 첫 메시지 뒤).
                           `ai_turn >= recipe_button_ai_turn` 이면 이번 답 뒤 버튼이 보인다 — 「서두르는 손님에게 버튼이 곧 나온다」 안내의 근거.
    revise               : 수정 대화일 때 원본(`ReviseContext`). 새 대화는 None.
    opening_question     : 수정 대화에서 화면이 이미 띄운 고정 첫 질문 — 다시 묻지 않는다. 새 대화는 None. ≤ 200자.
    """

    palette: Palette | None
    ai_turn: int
    recipe_button_ai_turn: int
    revise: ReviseContext | None = None
    opening_question: str | None = None

    def __post_init__(self) -> None:
        if self.palette is not None and not isinstance(self.palette, Palette):
            raise PortContractError("ConversationOptions.palette 는 Palette 또는 None 이어야 한다")
        for k in ("ai_turn", "recipe_button_ai_turn"):
            v = getattr(self, k)
            if isinstance(v, bool) or not isinstance(v, int) or v < 1:
                raise PortContractError(f"ConversationOptions.{k} 는 1 이상 정수여야 한다({v!r})")
        if self.revise is not None and not isinstance(self.revise, ReviseContext):
            raise PortContractError("ConversationOptions.revise 는 ReviseContext 여야 한다")
        if self.opening_question is not None:
            if not isinstance(self.opening_question, str):
                raise PortContractError("ConversationOptions.opening_question 은 문자열이어야 한다")
            if len(self.opening_question) > MAX_OPENING_QUESTION_CHARS:
                raise PortContractError(f"ConversationOptions.opening_question 은 {MAX_OPENING_QUESTION_CHARS}자 이하여야 한다"
                                        f"({len(self.opening_question)}자)")

    @property
    def recipe_button_visible(self) -> bool:
        return self.ai_turn >= self.recipe_button_ai_turn

    @classmethod
    def from_dict(cls, d: Mapping[str, Any] | None) -> "ConversationOptions":
        if not isinstance(d, Mapping):
            raise PortContractError(f"ConversationOptions.from_dict: Mapping 이 아니다({type(d).__name__})")
        bad = sorted(set(d) - set(_OPTION_KEYS))
        if bad:
            raise PortContractError(f"허용되지 않는 params: {bad} (sensorium-shop 허용: {sorted(_OPTION_KEYS)})")
        for req in ("palette", "aiTurn", "recipeButtonAiTurn"):
            if req not in d:
                raise PortContractError(f"params.{req} 는 필수다(sensorium-shop)")
        pal = d["palette"]
        if pal is not None and (isinstance(pal, str) or not isinstance(pal, (list, tuple))
                                or not all(isinstance(x, str) for x in pal)):
            raise PortContractError("params.palette 는 향료 id 문자열 목록 또는 null(모름)이어야 한다")
        rev = d.get("revise")
        return cls(palette=Palette(notes=tuple(pal)) if pal is not None else None, ai_turn=d["aiTurn"], recipe_button_ai_turn=d["recipeButtonAiTurn"],
                   revise=ReviseContext.from_dict(rev) if rev is not None else None,
                   opening_question=d.get("openingQuestion"))

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"palette": list(self.palette.notes) if self.palette is not None else None,
                               "aiTurn": self.ai_turn,
                               "recipeButtonAiTurn": self.recipe_button_ai_turn}
        if self.revise is not None:
            out["revise"] = self.revise.to_dict()
        if self.opening_question is not None:
            out["openingQuestion"] = self.opening_question
        return out


@dataclass(frozen=True)
class ConversationParam:
    """대화 한 턴. 상태(대화 기록)는 호출자가 history 로 보관·회송한다.

    domain       : "fragrance" — 라우트 축(`/v1/fragrance/converse` + `sensorium_version`).
    message      : 이번 손님 말(통합코드 상한 1000자 — 정책보드 APP-CHAT 「입력 1000자」).
    history      : 이번 대화의 앞 턴들(`Turn` · ≤ 100턴) · 수정 대화면 맨 앞에 고정 첫 질문이 assistant 턴으로 있다.
    lang         : "ko" | "en" | "ja" | "vi".
    kickoff      : 센릿샵은 쓰지 않는다(첫 문구는 화면 고정) — 하네스 형상 칸.
    params       : `ConversationOptions`.
    require_text : True = 발화를 반드시 낸다(침묵 복구 재호출 · 보장 방법은 어댑터 자유).
    """

    domain: str
    params: ConversationOptions
    message: str | None = None
    history: tuple[Turn, ...] = ()
    lang: str = "ko"
    kickoff: bool = False
    require_text: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.params, ConversationOptions):
            raise PortContractError(f"ConversationParam.params 는 ConversationOptions 여야 한다({type(self.params).__name__})")
        object.__setattr__(self, "history", turns_from_wire(self.history, "ConversationParam.history", max_turns=MAX_TURNS))


@dataclass(frozen=True)
class ConverseReply:
    """converse 출력 — 통합코드가 쓰는 값은 전부 여기로 받는다.

    reply   : 손님에게 보일 말.
    result  : 지금까지 대화에서 **들은** 요점(`ScentBrief` · 추정 없음 → `inferred` 는 반드시 비어 있다 · 필수)
              — 통합코드가 「#4 까지 필수 3개」 QC 를 계측한다.
    history : 이번 턴을 반영한 기록(`Turn`).
    stamp   : 이 답을 만든 세대·모델 도장(필수).
    done · keywords : 하네스 형상 칸 — 센릿샵은 판정에 쓰지 않는다(done=False · keywords=()).
    """

    reply: str
    result: ScentBrief
    stamp: Stamp
    history: tuple[Turn, ...] = ()
    done: bool = False
    keywords: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.reply, str):
            raise PortContractError(f"ConverseReply.reply 는 문자열이어야 한다({type(self.reply).__name__})")
        if not isinstance(self.result, ScentBrief):
            raise PortContractError("ConverseReply.result 는 ScentBrief 여야 한다")
        if self.result.inferred:
            raise PortContractError("ConverseReply.result.inferred 는 비어 있어야 한다(대화는 들은 것만 보고한다)")
        if not isinstance(self.stamp, Stamp):
            raise PortContractError("ConverseReply.stamp 는 Stamp 여야 한다")
        object.__setattr__(self, "keywords", tuple(self.keywords or ()))
        object.__setattr__(self, "history", turns_from_wire(self.history, "ConverseReply.history"))

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "ConverseReply":
        if not isinstance(d, Mapping):
            raise PortContractError("ConverseReply.from_dict: Mapping 이 아니다")
        missing = [k for k in ("reply", "result", "stamp") if d.get(k) is None]
        if missing:
            raise PortContractError(f"ConverseReply.from_dict: 필수 키 누락 {missing}")
        return cls(reply=d["reply"], result=ScentBrief.from_dict(d["result"]), stamp=Stamp.from_dict(d["stamp"]),
                   history=turns_from_wire(d.get("history"), "history"), done=bool(d.get("done", False)),
                   keywords=tuple(d.get("keywords") or ()))

    def to_dict(self) -> dict[str, Any]:
        return {"reply": self.reply, "done": self.done, "result": self.result.to_dict(),
                "keywords": list(self.keywords), "history": [t.to_wire() for t in self.history],
                "stamp": self.stamp.to_dict()}


class ConversationPort(VersionPort):
    """대화 한 턴 — 1회 호출. 내부에서 재시도·폴백·추가 호출을 돌지 않는다(그건 통합코드 몫).
    불변식: 재진입(상태 0) · 부작용은 llm 인자로만 · 같은 입력 + 같은 llm 응답 → 같은 반환."""

    @abstractmethod
    def converse(self, request: ConversationParam, llm: LlmPort | None = None) -> ConverseReply:
        ...
