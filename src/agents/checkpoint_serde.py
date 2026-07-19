from __future__ import annotations

import enum
import inspect

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from pydantic import BaseModel

import agents.models as models_module


def _collect_allowed_checkpoint_modules() -> list[tuple[str, ...]]:
    allowed_modules: list[tuple[str, ...]] = []
    for symbol_name in sorted(dir(models_module)):
        symbol_value: object = getattr(models_module, symbol_name)
        if not inspect.isclass(symbol_value):
            continue
        if issubclass(symbol_value, BaseModel) and symbol_value is not BaseModel:
            allowed_modules.append((models_module.__name__, symbol_name))
            continue
        if issubclass(symbol_value, enum.Enum) and symbol_value is not enum.Enum:
            allowed_modules.append((models_module.__name__, symbol_name))
    return allowed_modules


def create_checkpoint_serde() -> JsonPlusSerializer:
    return JsonPlusSerializer(
        allowed_msgpack_modules=_collect_allowed_checkpoint_modules(),
    )
