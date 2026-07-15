from __future__ import annotations

import json

import json_repair
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, ValidationError
from typing import Type, TypeVar

from employer_dd_agent.configuration import Configuration
from employer_dd_agent.llm_service import create_llm_text_model, create_llm_structured_model

ModelType = TypeVar("ModelType", bound=BaseModel)


def _message_content_to_text(message: BaseMessage) -> str:
    content_value: object = message.content
    if isinstance(content_value, str):
        return content_value
    if isinstance(content_value, list):
        text_parts: list[str] = []
        for part in content_value:
            if isinstance(part, str):
                text_parts.append(part)
                continue
            if isinstance(part, dict):
                text_value: object = part.get("text")
                if isinstance(text_value, str):
                    text_parts.append(text_value)
        if text_parts:
            return "\n".join(text_parts)
    raise TypeError(f"Unsupported message content type: {type(content_value).__name__}")


def _parse_json_payload(raw_text: str) -> dict[str, object]:
    stripped_text: str = raw_text.strip()
    if not stripped_text:
        raise TypeError("Structured JSON payload is empty")
    repaired_payload: object = json_repair.loads(stripped_text)
    if not isinstance(repaired_payload, dict):
        raise TypeError(
            f"Repaired JSON must be an object, got {type(repaired_payload).__name__}"
        )
    return repaired_payload


def _json_text_to_model(raw_text: str, model_class: Type[ModelType]) -> ModelType:
    payload: dict[str, object] = _parse_json_payload(raw_text=raw_text)
    return model_class.model_validate(payload)


def coerce_structured_output(output: object, model_class: Type[ModelType]) -> ModelType:
    if output is None:
        raise TypeError(
            f"Structured output for {model_class.__name__} returned None. "
            "Increase structured_llm_max_tokens or retry the run."
        )
    if isinstance(output, model_class):
        return output
    if isinstance(output, dict):
        return model_class.model_validate(output)
    if isinstance(output, str):
        return _json_text_to_model(raw_text=output, model_class=model_class)
    if isinstance(output, BaseMessage):
        return _json_text_to_model(
            raw_text=_message_content_to_text(message=output),
            model_class=model_class,
        )
    raise TypeError(
        f"Structured output must be {model_class.__name__}, dict, str, or message, "
        f"got {type(output).__name__}"
    )


def _structured_json_instruction(model_class: Type[ModelType]) -> str:
    schema_text: str = json.dumps(model_class.model_json_schema(), ensure_ascii=False, indent=2)
    return (
        "\n\nReturn one valid JSON object that matches this schema exactly. "
        "Do not wrap the JSON in markdown fences.\n"
        f"{schema_text}"
    )


def invoke_structured_output(
    config: RunnableConfig,
    model_class: Type[ModelType],
    prompt: str,
) -> ModelType:
    settings: Configuration = Configuration.from_runnable_config(config)
    structured_model = create_llm_structured_model(
        config=config,
        class_name=model_class,
    )
    json_prompt: str = f"{prompt}{_structured_json_instruction(model_class=model_class)}"
    last_error: Exception | None = None

    for _attempt_index in range(settings.max_structured_output_retries):
        candidate_output: object = structured_model.invoke(json_prompt)
        if candidate_output is None:
            continue
        try:
            return coerce_structured_output(output=candidate_output, model_class=model_class)
        except (TypeError, ValidationError, ValueError) as error:
            last_error = error

    text_model = create_llm_text_model(config=config)
    raw_response: object = text_model.invoke(json_prompt)
    try:
        return coerce_structured_output(output=raw_response, model_class=model_class)
    except (TypeError, ValidationError, ValueError) as error:
        last_error = error

    if last_error is None:
        raise RuntimeError(
            f"Structured output for {model_class.__name__} failed without a captured error."
        )
    raise RuntimeError(
        f"Structured output for {model_class.__name__} failed after retries and json_repair."
    ) from last_error
