from __future__ import annotations

from typing import Type

from langchain.chat_models import init_chat_model
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.tools import BaseTool
from pydantic import BaseModel

from employer_dd_agent.configuration import Configuration


_configurable_model = init_chat_model(configurable_fields=("model", "max_tokens", "api_key"))


def _build_model(
    config: RunnableConfig,
    model_chain: Runnable,
    model_name: str,
    max_tokens: int,
    max_retries: int,
) -> Runnable:
    configurable: dict[str, object] = config.get("configurable", {})
    api_key_value: object = configurable.get("api_key")
    runtime_config: dict[str, object] = {
        "model": model_name,
        "max_tokens": max_tokens,
    }
    if isinstance(api_key_value, str) and api_key_value:
        runtime_config["api_key"] = api_key_value
    return model_chain.with_retry(stop_after_attempt=max_retries).with_config(runtime_config)


def create_llm_with_tools(tools: list[BaseTool], config: RunnableConfig) -> Runnable:
    settings: Configuration = Configuration.from_runnable_config(config)
    model_with_tools: Runnable = _configurable_model.bind_tools(tools)
    return _build_model(
        config=config,
        model_chain=model_with_tools,
        model_name=settings.get_tools_model_name(),
        max_tokens=settings.tools_llm_max_tokens,
        max_retries=settings.max_tools_output_retries,
    )


def create_llm_structured_model(
    config: RunnableConfig,
    class_name: Type[BaseModel],
) -> Runnable:
    settings: Configuration = Configuration.from_runnable_config(config)
    model_name: str = settings.get_structured_model_name()
    if model_name.startswith("openrouter:"):
        structured_model: Runnable = _configurable_model.with_structured_output(
            class_name,
            method="function_calling",
        )
    else:
        structured_model = _configurable_model.with_structured_output(class_name)
    return _build_model(
        config=config,
        model_chain=structured_model,
        model_name=model_name,
        max_tokens=settings.structured_llm_max_tokens,
        max_retries=1,
    )


def create_llm_text_model(config: RunnableConfig) -> Runnable:
    settings: Configuration = Configuration.from_runnable_config(config)
    return _build_model(
        config=config,
        model_chain=_configurable_model,
        model_name=settings.get_structured_model_name(),
        max_tokens=settings.structured_llm_max_tokens,
        max_retries=1,
    )
