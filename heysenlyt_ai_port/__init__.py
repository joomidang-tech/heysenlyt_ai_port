"""heysenlyt_ai_port — heysenlyt(프로덕트팀) ↔ SENSORIUM(연구소) 계약 라이브러리.

## 구성 — **계약 단위 수직 슬라이스** (2026-09-20 구조 개편)
한 계약(포트 + 입력 DTO + 응답 DTO)을 **한 파일**에 모은다. 종전엔 `ports/` 와 `dto/` 로
  수평 분할돼 있어, 향연 계약 하나를 읽으려면 세 파일(ports/icad_port·dto/params·dto/replies)을
  열어야 했고 `dto/params.py` 안에서 **두 order web 의 DTO 가 섞여** 있었다.

| 파일 | 무엇 | 누가 쓰나 |
|------|------|-----------|
| `llm.py`          | `LlmPort` — 주입되는 LLM 의 모양      | **공통**(세 포트 전부 인자로 받는다) |
| `errors.py`       | 실패 어휘(`LlmError` 계열)            | **공통** |
| `version.py`      | `VersionPort` · `VersionInfo`         | **공통**(도장의 출처) |
| `palette.py`      | `Palette` — 이번 요청에서 쓸 수 있는 향료 | **공통**(레시피·향연 입력이 함께 든다) |
| `conversation.py` | 대화 한 턴                            | **두 order web 공용**(향연은 `params` 로 정책만 얹는다) |
| `recipe.py`       | 레시피 생성·재조향                    | 헤이센릿 order web |
| `icad.py`         | 향연 compose(대화 이력 → payload 하나) | 향연 order web |

⛔ 의존성 0 — 표준 라이브러리 외 import 금지(test_dependency_free.py 로 강제).
⛔ **공개 표면은 톱레벨 재수출뿐이다** — 소비자는 `from heysenlyt_ai_port import RecipePort` 로만
   쓴다(실측 2026-09-20: 서브모듈 경로를 직접 import 하는 소비자 0건). 그래서 내부 배치는
   이 파일이 같은 이름을 계속 내보내는 한 자유롭게 바꿀 수 있다 — 이번 개편이 그 성질에 기댔다.
"""

from heysenlyt_ai_port.conversation import (
    ConversationParam,
    ConversationPort,
    ConverseReply,
    Demographics,
)
from heysenlyt_ai_port.errors import (
    LlmError,
    LlmResponseError,
    LlmTimeoutError,
    LlmUnavailableError,
)
from heysenlyt_ai_port.icad import (
    IcadComposeParam,
    IcadComposePort,
    IcadComposeReply,
    IcadPrior,
    IcadTurn,
)
from heysenlyt_ai_port.llm import LlmPort
from heysenlyt_ai_port.palette import Palette
from heysenlyt_ai_port.recipe import (
    RecipeParam,
    RecipePort,
    RecipeReply,
    RegenerateParam,
)
from heysenlyt_ai_port.version import VersionInfo, VersionPort

__all__ = [
    "ConversationPort",
    "ConversationParam",
    "ConverseReply",
    "Demographics",
    "IcadComposeParam",
    "IcadComposePort",
    "IcadComposeReply",
    "IcadPrior",
    "IcadTurn",
    "LlmError",
    "LlmPort",
    "LlmResponseError",
    "LlmTimeoutError",
    "LlmUnavailableError",
    "Palette",
    "RecipePort",
    "RecipeReply",
    "RecipeParam",
    "RegenerateParam",
    "VersionInfo",
    "VersionPort",
]
