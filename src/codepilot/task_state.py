from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


StepStatus = Literal["pending", "running", "done", "blocked"]
TaskStatus = Literal["idle", "planning", "running", "waiting_approval", "blocked", "done"]


@dataclass
class PlanStep:
    description: str
    status: StepStatus = "pending"


@dataclass
class TaskState:
    goal: str = ""
    plan: list[PlanStep] = field(default_factory=list)
    current_step: int | None = None
    status: TaskStatus = "idle"

    def start_goal(self, goal: str) -> None:
        self.goal = goal
        self.status = "running"
        self.current_step = 0
        self.plan = [
            PlanStep(description="理解用户目标", status="running"),
            PlanStep(description="读取必要项目上下文"),
            PlanStep(description="基于真实上下文回答"),
        ]

    def set_plan(self, plan: list[PlanStep]) -> None:
        self.plan = plan
        self.current_step = _first_active_step(plan)
        self.status = "running" if plan else "idle"

    def mark_done(self) -> None:
        self.status = "done"
        for step in self.plan:
            if step.status in {"pending", "running"}:
                step.status = "done"
        if self.plan:
            self.current_step = len(self.plan) - 1

    def render_status(self) -> str:
        if self.status == "idle" or not self.goal:
            return "当前状态：idle"

        current = self._current_step()
        if current is None:
            return f"当前状态：{self.status}；目标：{self.goal}"
        return f"当前状态：{self.status}；目标：{self.goal}；当前步骤：{current.description}"

    def render_plan(self) -> str:
        if not self.plan:
            return "当前计划：暂无任务计划"

        lines = ["当前计划："]
        for index, step in enumerate(self.plan, start=1):
            lines.append(f"{index}. [{step.status}] {step.description}")
        return "\n".join(lines)

    def _current_step(self) -> PlanStep | None:
        if self.current_step is None:
            return None
        if self.current_step < 0 or self.current_step >= len(self.plan):
            return None
        return self.plan[self.current_step]


def _first_active_step(plan: list[PlanStep]) -> int | None:
    for index, step in enumerate(plan):
        if step.status == "running":
            return index
    for index, step in enumerate(plan):
        if step.status == "pending":
            return index
    return len(plan) - 1 if plan else None
