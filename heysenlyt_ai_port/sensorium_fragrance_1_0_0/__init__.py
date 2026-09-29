"""sensorium-fragrance-1.0.0 — 세대 선언. 이 폴더의 계약 전부가 여기서 나간다."""

from __future__ import annotations

from heysenlyt_ai_port.sensorium_fragrance_1_0_0.recipe import FragranceRecipe, LayerRatio, Palette, RecipeNote, RecipeOptions, RecipeParam, RecipePort, RecipeReply, RegenerateParam
from heysenlyt_ai_port.sensorium_fragrance_1_0_0.conversation import ChatResult, ConversationOptions, ConversationParam, ConversationPort, ConverseReply, Demographics, KnownAxes

VERSION_ID = "sensorium-fragrance-1.0.0"
DOMAIN = "fragrance"           # 이 세대가 서는 라우트 축 (/v1/{domain}/…)
from heysenlyt_ai_port.sensorium_fragrance_1_0_0.ai_contract import AiContract

# 통합코드가 이 세대에 부르는 호출 — `AiContract` 의 추상 메서드에서 파생(손으로 적지 않는다).
PORTS = tuple(n for n in ("recipe", "conversation", "compose") if n in AiContract.__abstractmethods__)

__all__ = ["DOMAIN", "PORTS", "VERSION_ID", "AiContract", "ChatResult", "ConversationOptions", "ConversationParam", "ConversationPort", "ConverseReply", "Demographics", "KnownAxes", "FragranceRecipe", "LayerRatio", "Palette", "RecipeNote", "RecipeOptions", "RecipeParam", "RecipePort", "RecipeReply", "RegenerateParam"]
