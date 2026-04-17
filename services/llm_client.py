import os
import time
from typing import Dict, List, Tuple
from urllib.parse import urlencode

import requests


class LLMClient:
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "openai").strip().lower()
        self.base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.api_key = os.getenv("LLM_API_KEY", "")
        self.timeout_seconds = int(os.getenv("LLM_TIMEOUT_SECONDS", "90"))
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "3200"))
        self.max_continuations = int(os.getenv("LLM_MAX_CONTINUATIONS", "3"))
        self.max_request_retries = int(os.getenv("LLM_MAX_REQUEST_RETRIES", "3"))
        self.retry_backoff_seconds = float(os.getenv("LLM_RETRY_BACKOFF_SECONDS", "1.5"))

    def _is_retryable_status(self, status_code: int) -> bool:
        return status_code in {408, 409, 425, 429, 500, 502, 503, 504}

    def _extract_retry_after(self, response: requests.Response) -> float:
        retry_after = response.headers.get("Retry-After", "").strip()
        if not retry_after:
            return 0.0
        try:
            return max(float(retry_after), 0.0)
        except ValueError:
            return 0.0

    def _post_with_retries(self, url: str, headers: Dict[str, str], payload: Dict) -> requests.Response:
        last_exc: requests.RequestException | None = None

        for attempt in range(self.max_request_retries + 1):
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout_seconds,
                )

                if response.status_code >= 400:
                    should_retry = (
                        attempt < self.max_request_retries
                        and self._is_retryable_status(response.status_code)
                    )
                    if should_retry:
                        retry_after_seconds = self._extract_retry_after(response)
                        backoff_seconds = self.retry_backoff_seconds * (2**attempt)
                        wait_seconds = retry_after_seconds if retry_after_seconds > 0 else backoff_seconds
                        time.sleep(wait_seconds)
                        continue

                response.raise_for_status()
                return response
            except requests.RequestException as exc:
                last_exc = exc
                status_code = getattr(getattr(exc, "response", None), "status_code", None)
                is_retryable = status_code is None or self._is_retryable_status(status_code)
                if attempt >= self.max_request_retries or not is_retryable:
                    raise
                time.sleep(self.retry_backoff_seconds * (2**attempt))

        if last_exc is not None:
            raise last_exc
        raise RuntimeError("Unexpected LLM request retry flow failure.")

    def _should_require_api_key(self) -> bool:
        local_hosts = ["localhost", "127.0.0.1"]
        return not any(host in self.base_url for host in local_hosts)

    def _openai_compatible_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Tuple[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        response = self._post_with_retries(
            f"{self.base_url}/chat/completions",
            headers,
            payload,
        )

        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("LLM response did not contain any choices.")

        first_choice = choices[0]
        content = first_choice.get("message", {}).get("content", "")
        if not content:
            raise RuntimeError("LLM response content was empty.")

        finish_reason = first_choice.get("finish_reason", "")
        return content.strip(), str(finish_reason)

    def _gemini_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Tuple[str, str]:
        headers = {"Content-Type": "application/json"}

        combined_prompt = "\n\n".join(
            f"{msg.get('role', 'user').upper()}: {msg.get('content', '')}" for msg in messages
        )

        payload = {
            "contents": [{"parts": [{"text": combined_prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        # Gemini public API expects :generateContent and API key as query parameter.
        query = urlencode({"key": self.api_key})
        url = f"{self.base_url}/models/{self.model}:generateContent?{query}"

        response = self._post_with_retries(url, headers, payload)

        data = response.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError("Gemini response did not contain candidates.")

        first_candidate = candidates[0]
        content = first_candidate.get("content", {})
        parts = content.get("parts", []) if isinstance(content, dict) else []
        text_parts = [part.get("text", "") for part in parts if isinstance(part, dict)]
        text = "".join(text_parts).strip()

        if not text:
            raise RuntimeError("Gemini response content was empty.")

        finish_reason = first_candidate.get("finishReason", "")
        return text, str(finish_reason)

    def _single_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Tuple[str, str]:
        if self.provider == "gemini":
            return self._gemini_chat(messages, temperature, max_tokens)
        return self._openai_compatible_chat(messages, temperature, max_tokens)

    def _is_truncated(self, finish_reason: str) -> bool:
        reason = (finish_reason or "").strip().lower()
        return reason in {"length", "max_tokens", "max_output_tokens"}

    def _chat_with_continuation(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        convo = list(messages)
        chunks: List[str] = []

        for _ in range(self.max_continuations + 1):
            text, finish_reason = self._single_chat(convo, temperature, max_tokens)
            chunks.append(text)

            if not self._is_truncated(finish_reason):
                break

            # Continue only when provider indicates length-based truncation.
            convo.append({"role": "assistant", "content": text})
            convo.append(
                {
                    "role": "user",
                    "content": (
                        "Continue from exactly where you stopped. "
                        "Do not repeat any previous text. "
                        "Return only the remaining content."
                    ),
                }
            )

        return "\n".join(chunk for chunk in chunks if chunk)

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2, max_tokens: int = None) -> str:
        if self._should_require_api_key() and not self.api_key:
            raise RuntimeError(
                "LLM_API_KEY is not set. Add it to your environment or use a local base URL."
            )

        effective_max_tokens = self.max_tokens if max_tokens is None else max_tokens

        try:
            return self._chat_with_continuation(messages, temperature, effective_max_tokens)
        except requests.RequestException as exc:
            raise RuntimeError(f"LLM request failed: {exc}") from exc
