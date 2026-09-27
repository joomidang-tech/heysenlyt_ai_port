"""LlmPort — 어댑터에 **주입되는 LLM**의 모양. 의존성 0.

이 파일이 최상위(세대 폴더 밖)인 이유(2026-09-27 세대 축 개편): 종전엔 `ports/recipe_port.py` 안에 얹혀 있었는데,
  LlmPort 는 레시피 전용이 아니라 **모든 포트가 인자로 받는 공통 주입 표면**이다
  (모든 세대의 RecipePort·ConversationPort·ComposePort 가 `llm: LlmPort | None`) — 통합코드가 어댑터에 **주는** 역방향 포트라 세대와 무관하다. 한 계약 파일 안에
  살면 "레시피의 부속"으로 읽히고, 실제로 icad_port 가 recipe_port 를 import 하는 기묘한
  의존이 생겼다. 공통 어휘는 공통 자리에 둔다.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LlmPort(Protocol):
    """주입되는 LLM의 모양 — 네트워크는 인자로 들어온다.

    세 표면 (heysenlyt v1.2.0 실제 LLM 사용에서 도출):
      - call / call_text : 단발 완성. 조향 노트선정(note_prediction)·식향 expo Stage-1 선택.
      - chat             : function-calling 대화. v1.2.0 `/api/chat`(messages + tools → tool_calls).

    tier: 다층 LLM 힌트 (chat/mid/vector/enrich). 단층 구현은 무시해도 된다. 기본 "mid".
    구현이 결정적일 필요는 없으나, 같은 입력에 같은 응답을 주는 구현(녹화본·캐시)을 꽂으면
    전체 파이프라인이 재현 가능해진다 — 골든셋·세대 비교의 전제.

    ── 실패 계약 (Raises) — "자유롭게 던지되, 정책 갈리는 곳만 타입으로" ─────────────
    파이썬엔 검사 예외가 없다. 그래서 강제하지 않는다 — **어댑터(관호)는 예외를 자유롭게 던져도
    된다.** 서버(통합코드)는 무엇이 오든 catch-all 로 받아 502 로 변환하므로 **서버가 죽지 않는다.**

    다만 서버가 **다르게 대처해야 하는** 실패(=정책이 갈리는 곳)는 아래 `errors.py` 공유 타입을
    쓰면 서버가 맞춤 대응한다. 이건 강제가 아니라 **협업 어휘**다 — 쓰면 특정 정책, 안 쓰면 502:
      - LlmTimeoutError     상류 타임아웃              → 서버 504 (또는 재시도)
      - LlmUnavailableError 모델·프로바이더 다운/셧다운 → 서버 503 / failover / 재시도
      - LlmResponseError    응답이 계약 형식을 어김      → 서버 502
      - (그 외 아무 예외)                              → 서버 502 (안전망)
    셋 다 LlmError 하위. 어댑터는 failover 를 하지 않고 **신호만** — 대처는 서버 정책.
    (공유 타입 매핑은 test_llm_error_contract·서버 test 로 확인.)
    """

    def call(
        self, *, system_prompt: str, user_prompt: str, tier: str = "mid",
        temperature: float | None = None, max_tokens: int | None = None,
    ) -> dict:
        """JSON 응답. temperature/max_tokens=None이면 구현 기본값(호출별 오버라이드 보존)."""
        ...

    def call_text(
        self, *, system_prompt: str, user_prompt: str, tier: str = "mid",
        temperature: float | None = None, max_tokens: int | None = None,
    ) -> str:
        """텍스트 응답."""
        ...

    def chat(
        self, *, system_prompt: str, messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None, tier: str = "chat",
        temperature: float | None = None, max_tokens: int | None = None,
    ) -> dict:
        """대화 한 턴(function-calling). v1.2.0 `/api/chat` 계약을 SSE→한 턴으로 접은 형태.

        messages : [{"role": "user"|"assistant", "content": str}, ...] (system 은 인자로 분리).
        tools    : OpenAI/OpenRouter function tool 스키마 리스트 (없으면 순수 대화).
        반환      : {"content": str, "tool_calls": [{"name": str, "args": dict}, ...]}
                   — content=AI 발화, tool_calls=이번 턴 호출된 함수들(순서 보존).
        """
        ...
