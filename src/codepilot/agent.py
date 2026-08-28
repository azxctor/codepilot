from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from codepilot.config import CodePilotConfig
from codepilot.llm import ChatMessage, LLMError, OpenAICompatibleLLM
from codepilot.session import SessionStore
from codepilot.task_state import TaskState
from codepilot.tools import ToolRegistry, default_readonly_registry
from codepilot.workspace import Workspace


class LLM(Protocol):
    def chat(self, messages: list[ChatMessage]) -> str:
        ...


DEFAULT_SYSTEM_PROMPT = """你是 CodePilot，一个本地代码助手。
你可以通过只读工具获取当前工作区上下文，不要猜测文件内容。
如果需要工具，请只输出一个 JSON 对象：
{"tool": "list_files", "args": {"path": "."}}
{"tool": "read_file", "args": {"path": "README.md", "start_line": 1, "end_line": 80}}
{"tool": "search_text", "args": {"query": "main", "glob": "*.py"}}
拿到工具结果后，再基于真实内容回答用户。"""


@dataclass
class ConversationAgent:
    llm: LLM
    session_store: SessionStore | None = None
    history: list[ChatMessage] = field(default_factory=list)
    tool_registry: ToolRegistry | None = None
    task_state: TaskState = field(default_factory=TaskState)
    max_tool_iterations: int = 8
    system_prompt: str = DEFAULT_SYSTEM_PROMPT

    def respond(self, message: str) -> str:
        if self.task_state.status in {"idle", "done"}:
            self.task_state.start_goal(message)

        user_message = ChatMessage(role="user", content=message)
        self.history.append(user_message)
        if self.session_store is not None:
            self.session_store.append("user_message", {"content": message})

        tool_iterations = 0
        while True:
            try:
                content = self.llm.chat(self._messages_for_llm())
            except LLMError as exc:
                content = f"LLM 调用失败：{exc}"
                self._append_assistant_message(content)
                return content

            tool_request = parse_tool_request(content)
            if tool_request is None:
                self.task_state.mark_done()
                self._append_assistant_message(content)
                return content

            if tool_iterations >= self.max_tool_iterations:
                content = f"工具调用超过上限（{self.max_tool_iterations}），已停止。"
                self._append_assistant_message(content)
                return content

            tool_iterations += 1
            tool_result_message = self._execute_tool_request(tool_request)
            self.history.append(ChatMessage(role="user", content=tool_result_message))

    @property
    def status(self) -> str:
        return self.task_state.render_status()

    @property
    def plan(self) -> str:
        return self.task_state.render_plan()

    def _messages_for_llm(self) -> list[ChatMessage]:
        tool_descriptions = ""
        if self.tool_registry is not None:
            tool_descriptions = "\n\n可用工具：\n" + self.tool_registry.describe_tools()
        return [ChatMessage(role="system", content=self.system_prompt + tool_descriptions)] + list(self.history)

    def _append_assistant_message(self, content: str) -> None:
        assistant_message = ChatMessage(role="assistant", content=content)
        self.history.append(assistant_message)
        if self.session_store is not None:
            self.session_store.append("assistant_message", {"content": content})

    def _execute_tool_request(self, request: "ToolRequest") -> str:
        if self.session_store is not None:
            self.session_store.append("tool_call", {"tool": request.tool, "args": request.args})

        if self.tool_registry is None:
            result_content = "没有可用工具。"
            if self.session_store is not None:
                self.session_store.append("tool_result", {"tool": request.tool, "ok": False, "error": result_content})
            return f"工具 {request.tool} 失败：\n{result_content}"

        result = self.tool_registry.execute(request.tool, request.args)
        if self.session_store is not None:
            self.session_store.append(
                "tool_result",
                {"tool": request.tool, "ok": result.ok, "content": result.content, "error": result.error},
            )

        if result.ok:
            return f"工具 {request.tool} 返回：\n{result.content}"
        return f"工具 {request.tool} 失败：\n{result.error}"


@dataclass(frozen=True)
class ToolRequest:
    tool: str
    args: dict


def parse_tool_request(content: str) -> ToolRequest | None:
    payload = _extract_json_object(content)
    if payload is None:
        return None

    tool = payload.get("tool")
    args = payload.get("args", {})
    if not isinstance(tool, str) or not isinstance(args, dict):
        return None
    return ToolRequest(tool=tool, args=args)


def _extract_json_object(content: str) -> dict | None:
    stripped = content.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()

    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    if not isinstance(value, dict):
        return None
    return value


def create_default_agent(config: CodePilotConfig, workspace: Path | None = None) -> ConversationAgent:
    session_store = SessionStore.create(config.sessions_dir)
    workspace_root = workspace or Path.cwd()
    code_workspace = Workspace(workspace_root, max_file_chars=config.max_file_chars)
    return ConversationAgent(
        llm=OpenAICompatibleLLM(config=config),
        session_store=session_store,
        tool_registry=default_readonly_registry(code_workspace),
        max_tool_iterations=config.max_tool_iterations,
    )
