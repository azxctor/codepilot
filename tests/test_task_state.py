from codepilot.task_state import PlanStep, TaskState


def test_task_state_starts_goal_with_default_plan() -> None:
    state = TaskState()

    state.start_goal("总结这个项目")

    assert state.goal == "总结这个项目"
    assert state.status == "running"
    assert state.current_step == 0
    assert [step.description for step in state.plan] == [
        "理解用户目标",
        "读取必要项目上下文",
        "基于真实上下文回答",
    ]


def test_task_state_renders_status_and_plan() -> None:
    state = TaskState()
    state.start_goal("查找入口文件")
    state.set_plan(
        [
            PlanStep(description="列出项目文件", status="done"),
            PlanStep(description="读取入口文件", status="running"),
        ]
    )

    assert state.render_status() == "当前状态：running；目标：查找入口文件；当前步骤：读取入口文件"
    assert state.render_plan() == "当前计划：\n1. [done] 列出项目文件\n2. [running] 读取入口文件"


def test_task_state_renders_empty_state() -> None:
    state = TaskState()

    assert state.render_status() == "当前状态：idle"
    assert state.render_plan() == "当前计划：暂无任务计划"
