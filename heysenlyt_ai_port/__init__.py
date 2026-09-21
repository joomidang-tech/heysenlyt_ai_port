"""heysenlyt_ai_port — heysenlyt(프로덕트팀) ↔ SENSORIUM(연구소) 계약 라이브러리.

## 구성 — **order web 먼저, 그 안에서 계약 단위** (2026-09-21 · 세 층 같은 모양)
포트 · 통합코드(`heysenlyt-ai/application`) · 어댑터(`heysenlyt_ai_adapter`)가 **같은 세 폴더**를 갖는다.
  어댑터는 통합 레포로 **통째 복사**해 쓰므로, 세 층의 모양이 같아야 "이 order web 의 길"을
  포트 → 유스케이스 → 구현으로 **같은 자리에서** 따라갈 수 있다. 한 계약(포트 + 입력 DTO + 응답 DTO)은
  여전히 한 파일이다(2026-09-20 수직 슬라이스 그대로 — 이번엔 그 파일들을 order web 으로 묶었을 뿐).

| 폴더 | 파일 | 무엇 |
|------|------|------|
| `heysenlyt/` | `recipe.py`       | 헤이센릿 order web — 레시피 생성·재조향 |
| `icad/`      | `compose.py`      | 향연 order web — 대화 이력 → payload 하나 |
| `shared/`    | `conversation.py` | 대화 한 턴 — **두 order web 공용**(향연은 `params` 로 정책만 얹는다) |
| `shared/`    | `llm.py`          | `LlmPort` — 주입되는 LLM 의 모양(세 포트 전부 인자로 받는다) |
| `shared/`    | `palette.py`      | `Palette` — 이번 요청에서 쓸 수 있는 향료(레시피·향연 입력이 함께 든다) |
| `shared/`    | `version.py`      | `VersionPort` · `VersionInfo`(도장의 출처) |
| `shared/`    | `errors.py`       | 실패 어휘(`LlmError` 계열) |

⛔ 의존 방향은 `heysenlyt/`·`icad/` → `shared/` 뿐이다. 두 order web 폴더는 서로를 모른다(tests/test_shape.py).
⛔ 의존성 0 — 표준 라이브러리 외 import 금지(test_dependency_free.py 로 강제).
⛔ **공개 표면은 톱레벨 재수출뿐이다** — 소비자는 `from heysenlyt_ai_port import RecipePort` 로만
   쓴다(실측 2026-09-20: 서브모듈 경로를 직접 import 하는 소비자 0건). 그래서 내부 배치는
   이 파일이 같은 이름을 계속 내보내는 한 자유롭게 바꿀 수 있다 — 이번 개편이 그 성질에 기댔다.
"""

from heysenlyt_ai_port.shared.conversation import (
    ConversationParam,
    ConversationPort,
    ConverseReply,
    Demographics,
)
from heysenlyt_ai_port.shared.errors import (
    LlmError,
    LlmResponseError,
    LlmTimeoutError,
    LlmUnavailableError,
)
from heysenlyt_ai_port.icad.compose import (
    IcadComposeParam,
    IcadComposePort,
    IcadComposeReply,
    IcadPrior,
    IcadTurn,
)
from heysenlyt_ai_port.shared.llm import LlmPort
from heysenlyt_ai_port.shared.palette import Palette
from heysenlyt_ai_port.heysenlyt.recipe import (
    RecipeParam,
    RecipePort,
    RecipeReply,
    RegenerateParam,
)
from heysenlyt_ai_port.shared.version import VersionInfo, VersionPort

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
