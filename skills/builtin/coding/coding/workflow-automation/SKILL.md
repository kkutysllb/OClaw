---
name: workflow-automation
description: >-
  Use this skill for scripts, CLIs, developer tooling, task automation, codegen,
  project maintenance commands, and repeatable local workflows.
work_modes: [coding]
---

# Workflow Automation

## 适用场景

- 编写自动化脚本（构建、部署、测试、数据处理）
- 创建 CLI 工具提升开发效率
- 代码生成器（模板、scaffold、boilerplate）
- 项目维护脚本（清理、迁移、检查）

## 核心原则

1. **可重复**：脚本多次执行结果一致，幂等设计
2. **有反馈**：执行过程有清晰的进度和结果输出
3. **可中断**：长时间运行的任务支持优雅中断
4. **错误友好**：失败时给出明确的错误信息和修复建议
5. **参数化**：通过参数/配置控制行为，不硬编码

## 执行流程

### 1. 识别自动化场景

| 场景 | 自动化前 | 自动化后 |
|------|---------|---------|
| 项目初始化 | 手动创建目录和文件 | 一条命令生成脚手架 |
| 数据迁移 | 手动导出/导入 | 脚本自动迁移 |
| 环境检查 | 手动运行多个命令 | 一条命令检查所有依赖 |
| 代码生成 | 手动写样板代码 | 模板生成 |
| 定期清理 | 手动删除临时文件 | cron 任务自动清理 |

### 2. CLI 工具设计

```python
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(
        description="Project maintenance tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s check          # 检查环境
  %(prog)s clean          # 清理临时文件
  %(prog)s migrate --env prod  # 执行生产迁移
"""
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # check 命令
    check_parser = subparsers.add_parser("check", help="检查环境依赖")
    check_parser.add_argument("--verbose", "-v", action="store_true")

    # clean 命令
    clean_parser = subparsers.add_parser("clean", help="清理临时文件")
    clean_parser.add_argument("--dry-run", action="store_true", help="只显示不执行")

    # migrate 命令
    migrate_parser = subparsers.add_parser("migrate", help="执行数据迁移")
    migrate_parser.add_argument("--env", choices=["dev", "staging", "prod"], required=True)

    args = parser.parse_args()

    if args.command == "check":
        return run_check(args.verbose)
    elif args.command == "clean":
        return run_clean(args.dry_run)
    elif args.command == "migrate":
        return run_migrate(args.env)
```

### 3. 脚本最佳实践

```python
#!/usr/bin/env python3
"""Project maintenance script."""

import logging
import shutil
import subprocess
from pathlib import Path

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

def run_command(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """运行外部命令，处理错误。"""
    logger.info(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        logger.error(f"Command failed: {result.stderr}")
        raise subprocess.CalledProcessError(result.returncode, cmd, result.stderr)
    return result

def clean_temp_files(dry_run: bool = False) -> None:
    """清理临时文件（幂等操作）。"""
    patterns = ["__pycache__", ".pytest_cache", ".ruff_cache", "*.pyc", "*.tmp"]

    for pattern in patterns:
        for path in Path(".").rglob(pattern):
            if dry_run:
                logger.info(f"[DRY RUN] Would remove: {path}")
            else:
                logger.info(f"Removing: {path}")
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()

    logger.info("Clean complete.")

def check_environment() -> bool:
    """检查开发环境是否就绪。"""
    checks = [
        ("Python", "python3 --version"),
        ("Node.js", "node --version"),
        ("pnpm", "pnpm --version"),
    ]

    all_passed = True
    for name, cmd in checks:
        try:
            result = run_command(cmd.split(), check=False)
            if result.returncode == 0:
                logger.info(f"✅ {name}: {result.stdout.strip()}")
            else:
                logger.error(f"❌ {name}: not found")
                all_passed = False
        except FileNotFoundError:
            logger.error(f"❌ {name}: not found")
            all_passed = False

    return all_passed
```

### 4. Makefile 自动化

```makefile
.PHONY: help dev build test lint format check clean setup

help:  ## 显示帮助
\t@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\\033[36m%-20s\\033[0m %s\\n", $$1, $$2}'

setup:  ## 安装依赖
\tpnpm install
\tcd backend && uv sync

dev:  ## 启动开发环境
\tpnpm dev

test:  ## 运行所有测试
\tpnpm test
\tcd backend && pytest tests/ -v

lint:  ## 代码检查
\tpnpm lint
\tcd backend && ruff check .

format:  ## 格式化代码
\tpnpm format
\tcd backend && ruff format .

check:  ## 环境检查
\t@echo "Checking environment..."
\tpython scripts/check.py
\t@echo "✅ All checks passed"

clean:  ## 清理临时文件
\tfind . -type d -name "__pycache__" -exec rm -rf {} +
\trm -rf .pytest_cache .ruff_cache .next/cache
\t@echo "✅ Cleaned"
```

### 5. 代码生成器

```python
def generate_component(name: str, component_type: str = "functional") -> None:
    """生成 React 组件模板。"""
    template = f'''import {{ memo }} from 'react';

interface {name}Props {{
  // Props 定义
}}

function {name}({{ }}: {name}Props) {{
  return (
    <div className="{name.lower()}">
      {/* 组件内容 */}
    </div>
  );
}}

export default memo({name});
'''

    path = Path(f"src/components/{name}.tsx")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(template)
    logger.info(f"Generated: {path}")
```

## 工具优先级

| 工具 | 用途 |
|------|------|
| `write_file` | 创建脚本和工具 |
| Bash | 测试脚本执行 |
| `read_file` | 参考现有脚本 |

## 检查清单

- [ ] 脚本幂等（多次执行结果一致）
- [ ] 有清晰的进度和结果输出
- [ ] 有错误处理和友好提示
- [ ] 支持参数化（不硬编码路径/配置）
- [ ] 有 `--help` 说明（CLI 工具）
- [ ] 有 `--dry-run` 选项（危险操作）
- [ ] 脚本有 docstring 说明

## 反模式

| ❌ 避免 | ✅ 应该 |
|---------|--------|
| 脚本不可重复执行 | 幂等设计 |
| 无错误处理 | try/except + 友好提示 |
| 硬编码路径和配置 | 参数化 + 配置文件 |
| 无进度反馈 | 有日志/进度输出 |
| 危险操作无确认 | --dry-run 选项 |

## 输出要求

1. 提供可执行的脚本/工具
2. 脚本有清晰的参数和帮助说明
3. 执行过程有日志输出
4. 错误时有友好的错误信息
5. 提供使用示例
---
name: workflow-automation
description: >-
  Use this skill for scripts, CLIs, developer tooling, task automation, codegen,
  project maintenance commands, and repeatable local workflows.
work_modes: [coding]
---

