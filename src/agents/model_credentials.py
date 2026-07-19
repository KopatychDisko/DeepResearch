from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelCredentials:
    openai_api_key: str | None
    google_api_key: str | None
    openrouter_api_key: str | None

    def has_any(self) -> bool:
        return (
            self.openai_api_key is not None
            or self.google_api_key is not None
            or self.openrouter_api_key is not None
        )


@dataclass(frozen=True)
class ResolvedLlmModel:
    model_name: str
    api_key: str


def load_model_credentials() -> ModelCredentials:
    return ModelCredentials(
        openai_api_key=os.environ.get("OPENAI_API_KEY"),
        google_api_key=os.environ.get("GOOGLE_API_KEY"),
        openrouter_api_key=os.environ.get("OPENROUTER_API_KEY"),
    )


def require_model_credentials(credentials: ModelCredentials) -> None:
    if credentials.has_any():
        return
    raise RuntimeError(
        "Missing model credentials: set OPENAI_API_KEY, GOOGLE_API_KEY, or OPENROUTER_API_KEY."
    )


def _provider_from_model(model_name: str) -> str:
    if ":" not in model_name:
        raise ValueError(f"Model name must include provider prefix, got: {model_name}")
    return model_name.split(":", 1)[0]


def _to_openrouter_model(configured_model: str) -> str:
    if configured_model.startswith("openrouter:"):
        return configured_model
    if configured_model.startswith("openai:"):
        openai_model_id: str = configured_model.removeprefix("openai:")
        return f"openrouter:openai/{openai_model_id}"
    if configured_model.startswith("google_genai:"):
        google_model_id: str = configured_model.removeprefix("google_genai:")
        return f"openrouter:google/{google_model_id}"
    return "openrouter:openai/gpt-5-mini"


def _resolve_openrouter_model(
    configured_model: str,
    credentials: ModelCredentials,
) -> ResolvedLlmModel:
    if credentials.openrouter_api_key is None:
        raise RuntimeError(
            "OPENROUTER_API_KEY is required when using openrouter models."
        )
    return ResolvedLlmModel(
        model_name=_to_openrouter_model(configured_model=configured_model),
        api_key=credentials.openrouter_api_key,
    )


def resolve_llm_model(
    configured_model: str,
    credentials: ModelCredentials,
) -> ResolvedLlmModel:
    provider: str = _provider_from_model(model_name=configured_model)

    if provider == "openrouter":
        return _resolve_openrouter_model(
            configured_model=configured_model,
            credentials=credentials,
        )

    if provider == "openai":
        if credentials.openai_api_key is not None:
            return ResolvedLlmModel(
                model_name=configured_model,
                api_key=credentials.openai_api_key,
            )
        if credentials.openrouter_api_key is not None:
            return _resolve_openrouter_model(
                configured_model=configured_model,
                credentials=credentials,
            )
        if credentials.google_api_key is not None:
            return ResolvedLlmModel(
                model_name="google_genai:gemini-2.5-flash",
                api_key=credentials.google_api_key,
            )
        raise RuntimeError(
            "No compatible credentials for openai model: set OPENAI_API_KEY or OPENROUTER_API_KEY."
        )

    if provider == "google_genai":
        if credentials.google_api_key is not None:
            return ResolvedLlmModel(
                model_name=configured_model,
                api_key=credentials.google_api_key,
            )
        if credentials.openrouter_api_key is not None:
            return _resolve_openrouter_model(
                configured_model=configured_model,
                credentials=credentials,
            )
        if credentials.openai_api_key is not None:
            return ResolvedLlmModel(
                model_name="openai:gpt-5-mini",
                api_key=credentials.openai_api_key,
            )
        raise RuntimeError(
            "No compatible credentials for google_genai model: set GOOGLE_API_KEY or OPENROUTER_API_KEY."
        )

    raise ValueError(f"Unsupported model provider in model name: {configured_model}")
