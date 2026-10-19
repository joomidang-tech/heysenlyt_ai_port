"""sensorium-shop-0.1.0 — 센릿샵(House of Senlyt) 세대 선언. 이 폴더의 계약 전부가 여기서 나간다.

라우트 축은 향장향(`/v1/fragrance/*`)이고 요청의 `sensorium_version` 이 이 세대를 고른다(통합코드의 세대 선택).
"""

from __future__ import annotations

from heysenlyt_ai_port.sensorium_shop_0_1_0.recipe import Palette, RecipeNote, RecipeOptions, RecipeParam, RecipePort, RecipeReply, ShopRecipe
from heysenlyt_ai_port.sensorium_shop_0_1_0.conversation import ConversationOptions, ConversationParam, ConversationPort, ConverseReply
from heysenlyt_ai_port.sensorium_shop_0_1_0.revise import BRIEF_FIELDS, REACTIONS, ROLES, WEIGHTS, ReviseContext, ScentBrief, Turn

VERSION_ID = "sensorium-shop-0.1.0"
DOMAIN = "fragrance"           # 이 세대가 서는 라우트 축 (/v1/{domain}/…)
from heysenlyt_ai_port.sensorium_shop_0_1_0.ai_contract import AiContract  # noqa: E402

# 통합코드가 이 세대에 부르는 호출 — `AiContract` 의 추상 메서드에서 파생(손으로 적지 않는다).
PORTS = tuple(n for n in ("recipe", "conversation", "compose") if n in AiContract.__abstractmethods__)

__all__ = [
    "BRIEF_FIELDS", "DOMAIN", "PORTS", "REACTIONS", "ROLES", "VERSION_ID", "WEIGHTS", "AiContract",
    "ConversationOptions", "ConversationParam", "ConversationPort", "ConverseReply",
    "Palette", "RecipeNote", "RecipeOptions", "RecipeParam", "RecipePort", "RecipeReply", "ReviseContext", "ScentBrief", "ShopRecipe", "Turn",
]
