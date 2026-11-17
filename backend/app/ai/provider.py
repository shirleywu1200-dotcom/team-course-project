"""依設定決定用哪個 AIClient（13.4 SDD D-4）。

AI_PROVIDER 未設定或不是 anthropic 時一律關閉：所有 AI 端點走退路，不產生費用。
"""

from app.ai.anthropic_client import AnthropicAIClient
from app.ai.client import AIClient, FakeAIClient
from app.config import Settings


def ai_from_settings(settings: Settings) -> AIClient:
    if settings.ai_provider == "anthropic":
        return AnthropicAIClient(api_key=settings.anthropic_api_key, model=settings.ai_model)
    return FakeAIClient(available=False)
