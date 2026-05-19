import logging
from typing import Any

import aiohttp

from bot.config import Settings


logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Ты AI-ассистент для малого и среднего бизнеса. Ты помогаешь клиентам "
    "выбирать продукты, объясняешь различия между сухофруктами, орехами, "
    "курагой, изюмом и финиками, предлагаешь подарочные наборы и отвечаешь "
    "вежливо. Отвечай только на русском языке или английском, если спросят. Ответы должны быть короткими, "
    "полезными и ориентированными на покупку и добавь в конце радостный эмодзи."
)

FALLBACK_MESSAGE = (
    "Извините, AI-ассистент временно недоступен. Попробуйте позже или "
    "свяжитесь с менеджером Мира сухофруктов: +7-928-111-11-11"
)


class HuggingFaceAIService:
    def __init__(self, settings: Settings) -> None:
        self._api_token = settings.huggingface_api_token
        self._model = settings.huggingface_model
        self._url = "https://router.huggingface.co/v1/chat/completions"

    async def ask(self, user_message: str) -> str:
        headers = {
            "Authorization": f"Bearer {self._api_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message.strip()},
            ],
            "max_tokens": 180,
            "temperature": 0.4,
            "stream": False,
        }

        try:
            timeout = aiohttp.ClientTimeout(total=45)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(self._url, headers=headers, json=payload) as response:
                    if response.status >= 400:
                        error_text = await response.text()
                        logger.warning(
                            "Hugging Face API error status=%s body=%s",
                            response.status,
                            error_text,
                        )
                        return FALLBACK_MESSAGE

                    data = await response.json()
        except (aiohttp.ClientError, TimeoutError) as exc:
            logger.warning("Hugging Face API request failed: %s", exc)
            return FALLBACK_MESSAGE

        answer = self._extract_answer(data)
        return answer or FALLBACK_MESSAGE

    @property
    def model(self) -> str:
        return self._model

    @staticmethod
    def _extract_answer(data: Any) -> str:
        if isinstance(data, dict):
            choices = data.get("choices")
            if isinstance(choices, list) and choices:
                first_choice = choices[0]
                if isinstance(first_choice, dict):
                    message = first_choice.get("message")
                    if isinstance(message, dict):
                        return str(message.get("content", "")).strip()

            error = data.get("error")
            if error:
                logger.warning("Hugging Face API returned error: %s", error)

        return ""
