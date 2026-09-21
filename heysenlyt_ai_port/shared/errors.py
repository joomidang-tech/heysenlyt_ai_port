"""계약 익셉션 — LLM 호출 실패의 타입. 의존성 0 (표준 라이브러리만).

경계(2026-08-12): **어댑터(관호)가 raise, 서버(통합코드)가 catch·대처.**
어댑터는 예외를 **자유롭게 던져도 된다** — 서버가 catch-all 로 받아 502 로 변환하므로 안 죽는다.
다만 서버가 **다르게 대처해야 하는** 실패(정책이 갈리는 곳)는 아래 공유 타입을 쓰면 맞춤 대응한다
(강제 아님, 협업 어휘). 어댑터는 failover·재시도·에러응답을 하지 않고 "무엇이 잘못됐나"만 신호하고,
서버가 그 타입을 보고 **정책**을 정한다(재시도·모델 failover·HTTP 상태).

매핑 관례(서버 정책 권장):
  LlmTimeoutError     → 504 (또는 재시도)
  LlmUnavailableError → 503 / failover / 재시도 (모델·프로바이더 다운·셧다운)
  LlmResponseError    → 502 (응답이 계약 형식을 어김)
"""

from __future__ import annotations


class LlmError(Exception):
    """LLM 호출 실패의 베이스 — **형태(shape)까지 계약으로 정의**한다.

    필드:
      code      : 기계가 읽는 안정 코드(예 "llm_timeout"). 서버 에러 응답 `{code, message}` 에 그대로 실린다.
      message   : 사람이 읽는 설명(예외 문자열).
      retryable : 서버가 재시도/ failover 해도 되는 실패인지 힌트(네트워크·5xx=True, 계약위반=False).
                  서버 정책이 참고만 한다(강제 아님).

    to_dict() = 서버가 손님에게 돌려주는 에러 봉투 `{code, message}` (v1.2.0 응답 형태와 동일).
    관호님은 `raise LlmUnavailableError("...")` 처럼 던지면 되고, code/retryable 은 타입이 정해준다
    (필요하면 인자로 오버라이드).
    """

    code: str = "llm_error"
    retryable: bool = False

    def __init__(self, message: str = "", *, code: str | None = None, retryable: bool | None = None):
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if retryable is not None:
            self.retryable = retryable

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


class LlmTimeoutError(LlmError):
    """상류(LLM) 응답 타임아웃 — 재시도 가능."""

    code = "llm_timeout"
    retryable = True


class LlmUnavailableError(LlmError):
    """모델·프로바이더 불가(5xx·연결 실패·모델 셧다운) — 재시도/ failover 대상."""

    code = "llm_unavailable"
    retryable = True


class LlmResponseError(LlmError):
    """LLM 응답이 계약 형식을 어김(파싱 불가 등) — 재시도 무의미."""

    code = "llm_response"
    retryable = False
