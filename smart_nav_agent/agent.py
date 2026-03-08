from __future__ import annotations

from typing import List, Tuple

from .config import Config
from .exceptions import LLMError, TaskPlanningError
from .llm_client import LLMClient
from .memory import DialogueMemory
from .models import ProgressSnapshot, SubTask, TaskPlan
from .navigation import BaseNavigationController
from .semantic_map import SemanticMap
from .task_manager import TaskManager


class SmartNavigationAgent:
    def __init__(
        self,
        config: Config,
        semantic_map: SemanticMap,
        llm_client: LLMClient,
        navigator: BaseNavigationController,
    ):
        self.config = config
        self.semantic_map = semantic_map
        self.llm = llm_client
        self.navigator = navigator
        self.task_manager = TaskManager()
        self.memory = DialogueMemory(max_turns=int(config.get("memory.max_history_turns", 8)))
        self.strict_map_only = bool(config.get("planner.strict_map_only", True))
        self.max_subtasks = int(config.get("planner.max_subtasks", 8))
        self.mode = str(config.get("runtime.mode", "simulation"))

    def _validate_plan_with_map(self, plan: TaskPlan) -> Tuple[TaskPlan, List[str]]:
        validated: List[SubTask] = []
        dropped: List[str] = []
        for st in plan.subtasks:
            obj, _score = self.semantic_map.match_object(st.target_name)
            if obj:
                st.target_name = obj.name
                st.target_obj_id = obj.obj_id
                validated.append(st)
            else:
                dropped.append(st.target_name)

        if self.strict_map_only:
            plan.subtasks = validated
        else:
            plan.subtasks = validated if validated else plan.subtasks
        return plan, dropped

    def _build_pre_plan_progress(self, instruction: str) -> ProgressSnapshot:
        return ProgressSnapshot(
            original_instruction=instruction,
            completed=[],
            in_progress=None,
            pending=[],
        )

    def plan_new_task(self, instruction: str) -> TaskPlan:
        progress = self._build_pre_plan_progress(instruction)
        raw_plan = self.llm.plan_tasks(
            instruction=instruction,
            semantic_objects=self.semantic_map.as_prompt_brief(),
            progress=progress,
            recent_dialogue=self.memory.recent(),
            max_subtasks=self.max_subtasks,
        )
        validated_plan, dropped = self._validate_plan_with_map(raw_plan)
        if dropped:
            print(f"[Planner] 以下目标不在语义地图中，已忽略: {dropped}")
        if not validated_plan.subtasks:
            raise TaskPlanningError("无法从指令中规划出可执行子任务（语义地图内）。")
        return validated_plan

    def _execute_current_queue(self) -> None:
        while self.task_manager.has_pending():
            current = self.task_manager.next_task()
            if not current:
                break
            obj = self.semantic_map.find_by_id(current.target_obj_id or "")
            if not obj:
                self.task_manager.complete_current(False, "target object missing in map")
                print(f"[Executor] 目标不存在，子任务失败: {current.target_name}")
                continue
            print(f"\n[Executor] 执行子任务: {current.action} -> {obj.name}")
            ok = self.navigator.navigate(current, obj)
            self.task_manager.complete_current(ok, "navigation feedback")
            print("[Executor] 结果:", "success" if ok else "fail")

    def run_instruction(self, instruction: str) -> str:
        self.memory.add_user(instruction)
        plan = self.plan_new_task(instruction)
        self.task_manager.set_plan(plan)
        print(f"[Planner] 已生成 {len(plan.subtasks)} 个子任务。")
        self._execute_current_queue()
        progress = self.task_manager.progress_snapshot()
        summary = self.llm.summarize_task(
            original_instruction=instruction,
            records=self.task_manager.records(),
            progress=progress,
            recent_dialogue=self.memory.recent(),
        )
        self.memory.add_assistant(summary)
        self.task_manager.clear()
        return summary

    def interrupt(self) -> str:
        current_instruction = self.task_manager.original_instruction or "无当前任务"
        self.task_manager.clear()
        msg = self.llm.notify_interrupt(current_instruction)
        self.memory.add_assistant(msg)
        return msg

    def status(self) -> str:
        status_text = self.task_manager.status_text(mode=self.mode)
        self.memory.add_assistant(status_text)
        return status_text

    def handle_command(self, text: str) -> str:
        normalized = text.strip().lower()
        if normalized in {"interrupt", "中断"}:
            return self.interrupt()
        if normalized in {"status", "状态"}:
            return self.status()
        if normalized in {"exit", "quit", "结束"}:
            return "exit"

        try:
            return self.run_instruction(text)
        except (TaskPlanningError, LLMError) as e:
            msg = f"任务失败: {e}"
            self.memory.add_assistant(msg)
            self.task_manager.clear()
            return msg
        except Exception as e:
            msg = f"系统异常: {e}"
            self.memory.add_assistant(msg)
            self.task_manager.clear()
            return msg
