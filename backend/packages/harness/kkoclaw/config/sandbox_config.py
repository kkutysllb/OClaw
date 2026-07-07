from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class VolumeMountConfig(BaseModel):
    """Configuration for a volume mount."""

    host_path: str = Field(..., description="Path on the host machine")
    container_path: str = Field(..., description="Path inside the container")
    read_only: bool = Field(default=False, description="Whether the mount is read-only")


class SandboxConfig(BaseModel):
    """Config section for a sandbox.

    Common options:
        use: Class path of the sandbox provider (required)
        allow_host_bash: Enable host-side bash execution for LocalSandboxProvider.
            Dangerous and intended only for fully trusted local workflows.
        mounts: List of volume mounts to share directories with the sandbox
    """

    use: str = Field(
        ...,
        description="Class path of the sandbox provider (e.g. kkoclaw.sandbox.local:LocalSandboxProvider)",
    )
    allow_host_bash: bool = Field(
        default=False,
        description="Allow the bash tool to execute directly on the host when using LocalSandboxProvider. Dangerous; intended only for fully trusted local environments.",
    )
    mounts: list[VolumeMountConfig] = Field(
        default_factory=list,
        description="List of volume mounts to share directories with the sandbox",
    )

    bash_output_max_chars: int = Field(
        default=20000,
        ge=0,
        description="Maximum characters to keep from bash tool output. Output exceeding this limit is middle-truncated (head + tail), preserving the first and last half. Set to 0 to disable truncation.",
    )
    read_file_output_max_chars: int = Field(
        default=50000,
        ge=0,
        description="Maximum characters to keep from read_file tool output. Output exceeding this limit is head-truncated. Set to 0 to disable truncation.",
    )
    ls_output_max_chars: int = Field(
        default=20000,
        ge=0,
        description="Maximum characters to keep from ls tool output. Output exceeding this limit is head-truncated. Set to 0 to disable truncation.",
    )

    permission_scope: Literal["read-only", "read-write", "unrestricted"] = Field(
        default="read-write",
        description=(
            "Default sandbox permission scope used when a thread does not "
            "explicitly select one. 'read-write' (default) keeps the existing "
            "behaviour: tools may read/write the user workspace and sandbox "
            "internal paths, but external absolute paths are rejected. "
            "'read-only' blocks all write operations. 'unrestricted' trusts "
            "the whole host (only path-traversal is rejected). The per-thread "
            "PermissionScopeSelector overrides this default."
        ),
    )

    model_config = ConfigDict(extra="allow")
