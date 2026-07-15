from __future__ import annotations

import os
from typing import Any

from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field


class Configuration(BaseModel):
    llm_model: str = Field(default="openai:gpt-5-mini")
    structured_llm_model: str | None = Field(default=None)
    tools_llm_model: str | None = Field(default=None)
    chunk_llm_model: str | None = Field(default=None)
    structured_llm_max_tokens: int = Field(default=4096)
    tools_llm_max_tokens: int = Field(default=800)
    max_structured_output_retries: int = Field(default=3)
    max_tools_output_retries: int = Field(default=3)
    max_tool_iterations: int = Field(default=5)
    tavily_max_results: int = Field(default=5)
    chunk_size: int = Field(default=1200)
    chunk_overlap: int = Field(default=120)
    sqlite_checkpointer_path: str = Field(default=".planning/checkpoints/research.sqlite")
    langfuse_tracing_enabled: bool = Field(default=True)

    def get_structured_model_name(self) -> str:
        if self.structured_llm_model is not None:
            return self.structured_llm_model
        return self.llm_model

    def get_tools_model_name(self) -> str:
        if self.tools_llm_model is not None:
            return self.tools_llm_model
        return self.llm_model

    def get_chunk_model_name(self) -> str:
        if self.chunk_llm_model is not None:
            return self.chunk_llm_model
        return self.llm_model

    @classmethod
    def from_runnable_config(cls, config: RunnableConfig) -> "Configuration":
        configurable: dict[str, Any] = config.get("configurable", {})
        values: dict[str, Any] = {}
        for field_name in cls.model_fields:
            env_value: str | None = os.environ.get(field_name.upper())
            if env_value is not None:
                values[field_name] = env_value
                continue
            if field_name in configurable:
                values[field_name] = configurable[field_name]
        return cls(**values)
