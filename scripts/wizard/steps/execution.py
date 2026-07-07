"""Step: execution mode and safety-related capabilities."""

from __future__ import annotations

from dataclasses import dataclass

from wizard.ui import ask_yes_no, print_header, print_info, print_warning

LOCAL_SANDBOX = "kkoclaw.sandbox.local:LocalSandboxProvider"


@dataclass
class ExecutionStepResult:
    sandbox_use: str
    allow_host_bash: bool
    include_bash_tool: bool
    include_write_tools: bool


def run_execution_step(step_label: str = "Step 3/4") -> ExecutionStepResult:
    print_header(f"{step_label} · Execution & Safety")
    print_info("Choose how much execution power KKOCLAW should have in this workspace.")

    sandbox_use = LOCAL_SANDBOX

    print()
    print_warning(
        "Local sandbox is convenient but not a secure shell isolation boundary."
    )
    print_info("Keep host bash disabled unless this is a fully trusted local workflow.")

    include_bash_tool = ask_yes_no("Enable bash command execution?", default=False)
    include_write_tools = ask_yes_no(
        "Enable file write tools (write_file, str_replace)?", default=True
    )

    return ExecutionStepResult(
        sandbox_use=sandbox_use,
        allow_host_bash=sandbox_use == LOCAL_SANDBOX and include_bash_tool,
        include_bash_tool=include_bash_tool,
        include_write_tools=include_write_tools,
    )
