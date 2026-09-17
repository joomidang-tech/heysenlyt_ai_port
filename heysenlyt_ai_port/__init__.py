"""heysenlyt_ai_port — heysenlyt(프로덕트팀) ↔ SENSORIUM(연구소) 계약 라이브러리.

라이브러리 구성:
  ports/  — Port(RecipePort·ConversationPort·VersionPort·IcadComposePort)·주입 인터페이스(LlmPort)
  dto/    — 입력/버전 DTO(RecipeParam·RegenerateParam·ConversationParam·VersionInfo·
            IcadComposeParam·IcadTurn·IcadPrior)·응답 DTO(RecipeReply·ConverseReply·IcadComposeReply)

⛔ 의존성 0 — 표준 라이브러리 외 import 금지(test_dependency_free.py로 강제).
공개 표면은 톱레벨 재수출: `from heysenlyt_ai_port import RecipePort, RecipeParam, ...`
"""

from heysenlyt_ai_port.dto.replies import ConverseReply, IcadComposeReply, RecipeReply
from heysenlyt_ai_port.dto.params import (
    ConversationParam,
    Demographics,
    IcadComposeParam,
    IcadPrior,
    IcadTurn,
    RecipeParam,
    RegenerateParam,
    VersionInfo,
)
from heysenlyt_ai_port.errors import (
    LlmError,
    LlmResponseError,
    LlmTimeoutError,
    LlmUnavailableError,
)
from heysenlyt_ai_port.ports.conversation_port import ConversationPort
from heysenlyt_ai_port.ports.icad_port import IcadComposePort
from heysenlyt_ai_port.ports.recipe_port import LlmPort, RecipePort
from heysenlyt_ai_port.ports.version_port import VersionPort

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
    "RecipePort",
    "RecipeReply",
    "RecipeParam",
    "RegenerateParam",
    "VersionInfo",
    "VersionPort",
]
