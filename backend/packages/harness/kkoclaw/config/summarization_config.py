"""Configuration for conversation summarization."""

from typing import Literal

from pydantic import BaseModel, Field

ContextSizeType = Literal["fraction", "tokens", "messages"]

# Tool names treated as skill-file reads when capturing loaded skills into the
# durable skill_context channel (DurableContextMiddleware).
DEFAULT_SKILL_FILE_READ_TOOL_NAMES: tuple[str, ...] = ("read_file", "read", "view", "cat")


class ContextSize(BaseModel):
    """Context size specification for trigger or keep parameters."""

    type: ContextSizeType = Field(description="Type of context size specification")
    value: int | float = Field(description="Value for the context size specification")

    def to_tuple(self) -> tuple[ContextSizeType, int | float]:
        """Convert to tuple format expected by SummarizationMiddleware."""
        return (self.type, self.value)


class SummarizationConfig(BaseModel):
    """Configuration for automatic conversation summarization.

    Enabled by default — summarization is a core stability mechanism that
    keeps long-running tasks from blowing out the model's context window.
    Override in config.yaml only to disable or tune thresholds.
    """

    enabled: bool = Field(
        default=True,
        description="Whether to enable automatic conversation summarization. Enabled by default — prevents long-task context blowout.",
    )
    model_name: str | None = Field(
        default=None,
        description="Model name to use for summarization (None = use a lightweight model)",
    )
    trigger: ContextSize | list[ContextSize] | None = Field(
        # 默认触发条件：消息数达到 40 条 OR token 达到 24000。
        # 用 messages + tokens 而非 fraction，因为 fraction 依赖 max_input_tokens，
        # 而各模型真实窗口差异大、config 里容易虚标（如 1000000），导致 fraction 永不触发。
        # messages=40 是一个与模型无关的稳健阈值；tokens=24000 约为常见 128K 窗口的 ~18%。
        default_factory=lambda: [
            ContextSize(type="messages", value=40),
            ContextSize(type="tokens", value=24000),
        ],
        description="One or more thresholds that trigger summarization. When any threshold is met, summarization runs. "
        "Defaults to messages=40 OR tokens=24000 (model-independent thresholds). "
        "Examples: {'type': 'messages', 'value': 50} triggers at 50 messages, "
        "{'type': 'tokens', 'value': 4000} triggers at 4000 tokens, "
        "{'type': 'fraction', 'value': 0.8} triggers at 80% of model's max input tokens",
    )
    keep: ContextSize = Field(
        default_factory=lambda: ContextSize(type="messages", value=20),
        description="Context retention policy after summarization. Specifies how much history to preserve. "
        "Examples: {'type': 'messages', 'value': 20} keeps 20 messages, "
        "{'type': 'tokens', 'value': 3000} keeps 3000 tokens, "
        "{'type': 'fraction', 'value': 0.3} keeps 30% of model's max input tokens",
    )
    trim_tokens_to_summarize: int | None = Field(
        default=4000,
        description="Maximum tokens to keep when preparing messages for summarization. Pass null to skip trimming.",
    )
    summary_prompt: str | None = Field(
        default=None,
        description="Custom prompt template for generating summaries. If not provided, uses the default LangChain prompt.",
    )
    preserve_recent_skill_count: int = Field(
        default=5,
        ge=0,
        description="Number of most-recently-loaded skill files to exclude from summarization. Set to 0 to disable skill preservation.",
    )
    preserve_recent_skill_tokens: int = Field(
        default=25000,
        ge=0,
        description="Total token budget reserved for recently-loaded skill files that must be preserved across summarization.",
    )
    preserve_recent_skill_tokens_per_skill: int = Field(
        default=5000,
        ge=0,
        description="Per-skill token cap when preserving skill files across summarization. Skill reads above this size are not rescued.",
    )
    skill_file_read_tool_names: list[str] = Field(
        default_factory=lambda: ["read_file", "read", "view", "cat"],
        description="Tool names treated as skill file reads when preserving recently-loaded skills across summarization.",
    )


# Global configuration instance
_summarization_config: SummarizationConfig = SummarizationConfig()


def get_summarization_config() -> SummarizationConfig:
    """Get the current summarization configuration."""
    return _summarization_config


def set_summarization_config(config: SummarizationConfig) -> None:
    """Set the summarization configuration."""
    global _summarization_config
    _summarization_config = config


def load_summarization_config_from_dict(config_dict: dict) -> None:
    """Load summarization configuration from a dictionary."""
    global _summarization_config
    _summarization_config = SummarizationConfig(**config_dict)
