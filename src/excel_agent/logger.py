"""日志配置和自定义回调处理器"""

import logging
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.tree import Tree
from rich.syntax import Syntax
from rich.text import Text

from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.outputs import LLMResult

from .config import get_config

# 全局 Console 实例
console = Console()


def get_logger(name: str) -> logging.Logger:
    """获取 Logger 实例"""
    return logging.getLogger(name)


def setup_logging(level: str = "INFO"):
    """配置全局日志"""
    # 定义日志格式
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # 创建 FileHandler，将日志写入根目录下的 excel_agent.log
    # mode="w" 表示每次运行时清空旧日志，只记录当前流程
    file_handler = logging.FileHandler("excel_agent.log", mode="w", encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(file_formatter)

    # RichHandler 保持原有配置
    rich_handler = RichHandler(console=console, rich_tracebacks=True, show_path=False)

    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[rich_handler, file_handler],
    )

    # 调整第三方库的日志级别
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)


class RichConsoleCallbackHandler(AsyncCallbackHandler):
    """Rich 风格的异步回调处理器，用于可视化打印 Agent 运行细节"""

    def __init__(self):
        self.console = console

    async def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """LLM 开始运行时调用"""
        model_name = "Unknown Model"
        if "name" in serialized:
            model_name = serialized["name"]

        self.console.print(
            Panel(
                Text(f"🤖 LLM Thinking ({model_name})...", style="cyan bold"),
                border_style="cyan",
            )
        )

    async def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """LLM 结束时调用"""
        # 可以打印 token 使用情况，如果有的话
        if response.llm_output and "token_usage" in response.llm_output:
            usage = response.llm_output["token_usage"]
            self.console.print(f"[dim]Tokens: {usage}[/dim]")

    async def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, **kwargs: Any
    ) -> None:
        """工具开始调用时调用"""
        tool_name = serialized.get("name", "Unknown Tool")

        tree = Tree(f"🛠️ Calling Tool: [bold yellow]{tool_name}[/bold yellow]")

        # 尝试美化输入参数（如果是 JSON）
        try:
            import json

            input_json = json.loads(input_str)
            formatted_json = json.dumps(input_json, indent=2, ensure_ascii=False)
            tree.add(Syntax(formatted_json, "json", theme="monokai", word_wrap=True))
        except:
            tree.add(Text(input_str, style="yellow"))

        self.console.print(tree)

    async def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """工具结束时调用"""
        # 截断过长的输出
        max_length = 500
        display_output = str(output)
        if len(display_output) > max_length:
            display_output = (
                display_output[:max_length]
                + f"... (truncated, total {len(display_output)} chars)"
            )

        self.console.print(
            Panel(
                Text(display_output, style="green"),
                title="✅ Tool Output",
                border_style="green",
                expand=False,
            )
        )

    async def on_tool_error(
        self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any
    ) -> None:
        """工具出错时调用"""
        self.console.print(
            Panel(
                Text(str(error), style="bold red"),
                title="❌ Tool Error",
                border_style="red",
            )
        )

    async def on_agent_action(self, action: Any, **kwargs: Any) -> Any:
        """Agent 决定采取行动时调用"""
        # 通常 on_tool_start 已经涵盖了大部分信息，这里可以简单记录
        pass

    async def on_agent_finish(self, finish: Any, **kwargs: Any) -> Any:
        """Agent 完成任务时调用"""
        output = finish.return_values.get("output", "")
        self.console.print(
            Panel(
                Text(output, style="bold white"),
                title="🏁 Final Answer",
                border_style="white",
            )
        )

    async def on_chain_error(
        self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any
    ) -> None:
        """链执行出错时调用"""
        # 忽略一些常见的中间错误，只打印严重的
        pass
