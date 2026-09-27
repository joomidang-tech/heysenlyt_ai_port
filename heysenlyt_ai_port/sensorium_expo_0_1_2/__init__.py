"""sensorium-expo-0.1.2 — 세대 선언. 이 폴더의 계약 전부가 여기서 나간다."""

from __future__ import annotations

from heysenlyt_ai_port.sensorium_expo_0_1_2.recipe import Palette, RecipeParam, RecipePort, RecipeReply
from heysenlyt_ai_port.sensorium_expo_0_1_2.conversation import ConversationParam, ConversationPort, ConverseReply, Demographics

VERSION_ID = "sensorium-expo-0.1.2"
DOMAIN = "flavor"           # 이 세대가 서는 라우트 축 (/v1/{domain}/…)
from heysenlyt_ai_port.sensorium_expo_0_1_2.ai_contract import AiContract

# 통합코드가 이 세대에 부르는 호출 — `AiContract` 의 추상 메서드에서 파생(손으로 적지 않는다).
PORTS = tuple(n for n in ("recipe", "conversation", "compose") if n in AiContract.__abstractmethods__)

__all__ = ["VERSION_ID", "DOMAIN", "PORTS", "AiContract", "ConversationParam", "ConversationPort", "ConverseReply", "Demographics", "Palette", "RecipeParam", "RecipePort", "RecipeReply"]
