"""LLM API client for evaluation."""
import json
import logging
from typing import Optional, AsyncGenerator
from openai import AsyncOpenAI
from app.core.config import settings, save_config_to_file

logger = logging.getLogger(__name__)


class LLMClient:
    """OpenAI-compatible LLM client for intranet deployment."""

    def __init__(self):
        self.client: Optional[AsyncOpenAI] = None
        self._explicitly_configured: bool = False  # True only after user saves config
        self._init_client()

    @property
    def is_configured(self) -> bool:
        """Whether the LLM has been explicitly configured by the user."""
        return self._explicitly_configured

    def mark_configured(self):
        """Mark LLM as explicitly configured (called after loading persisted config)."""
        self._explicitly_configured = True

    def _init_client(self):
        try:
            self.client = AsyncOpenAI(
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url,
            )
            logger.info(f"LLM client initialized: {settings.llm_base_url}")
        except Exception as e:
            logger.warning(f"Failed to init LLM client: {e}")
            self.client = None

    def update_config(self, api_key: str, base_url: str, model: str):
        """Update LLM configuration dynamically and persist to disk."""
        settings.llm_api_key = api_key
        settings.llm_base_url = base_url
        settings.llm_model = model
        self._init_client()
        self._explicitly_configured = True
        # Persist to file so config survives container restart
        save_config_to_file()

    async def test_connection(self) -> dict:
        """Test LLM connection by sending a real API request.

        Returns:
            dict with keys: ok (bool), message (str), model (str)
        """
        if not self.client:
            return {"ok": False, "message": "LLM client not initialized"}

        try:
            # Send a minimal test request (1 token max to save cost)
            response = await self.client.chat.completions.create(
                model=settings.llm_model,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=1,
                temperature=0,
            )
            reply = response.choices[0].message.content or ""
            return {
                "ok": True,
                "message": f"连接成功，模型响应正常",
                "model": settings.llm_model,
            }
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"LLM test connection failed: {error_msg}")
            # Provide user-friendly error messages
            if "401" in error_msg or "Unauthorized" in error_msg or "Invalid API Key" in error_msg:
                hint = "API Key 无效或未授权，请检查 Key"
            elif "404" in error_msg or "not found" in error_msg.lower():
                hint = f"接口地址不存在 (404)，请检查 Base URL 是否正确"
            elif "Connection" in error_msg or "connect" in error_msg.lower() or "timeout" in error_msg.lower():
                hint = f"无法连接到服务器，请检查网络和 Base URL 是否正确"
            elif "429" in error_msg:
                hint = "请求频率过高或余额不足，请稍后再试"
            else:
                hint = f"连接失败: {error_msg[:200]}"
            return {"ok": False, "message": hint}

    async def chat(
        self,
        messages: list,
        temperature: float = None,
        max_tokens: int = None,
        response_format: dict = None,
    ) -> str:
        """Send a chat completion request."""
        if not self.client:
            raise RuntimeError("LLM client not configured. Please set API configuration.")

        kwargs = {
            "model": settings.llm_model,
            "messages": messages,
            "temperature": temperature or settings.llm_temperature,
            "max_tokens": max_tokens or settings.llm_max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        try:
            response = await self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"LLM API error: {e}")
            raise

    async def chat_stream(
        self,
        messages: list,
        temperature: float = None,
        max_tokens: int = None,
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion response."""
        if not self.client:
            raise RuntimeError("LLM client not configured.")

        try:
            stream = await self.client.chat.completions.create(
                model=settings.llm_model,
                messages=messages,
                temperature=temperature or settings.llm_temperature,
                max_tokens=max_tokens or settings.llm_max_tokens,
                stream=True,
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"LLM stream error: {e}")
            raise


# Global LLM client instance
llm_client = LLMClient()
