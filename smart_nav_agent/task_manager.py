from __future__ import annotations

from collections import deque
from typing import Deque, Dict, List, Optional

from .models import ExecutionRecord, ProgressSnapshot, SubTask, TaskPlan


class TaskManager:
    def __init__(self) -> None:
        self.original_instruction: str = ""
        self._pending: Deque[SubTask] = deque()
        self._completed: List[ExecutionRecord] = []
        self._current: Optional[SubTask] = None
        self._current_step_index = 0

    def set_plan(self, plan: TaskPlan) -> None:
        self.clear()
        self.original_instruction = plan.original_instruction
        for subtask in plan.subtasks:
            self._pending.append(subtask)

    def clear(self) -> None:
        self.original_instruction = ""
        self._pending.clear()
        self._completed.clear()
        self._current = None
        self._current_step_index = 0

    def has_pending(self) -> bool:
        return bool(self._pending)

    def next_task(self) -> Optional[SubTask]:
        if not self._pending:
            self._current = None
            return None
        self._current = self._pending.popleft()
        self._current_step_index += 1
        return self._current

    def complete_current(self, success: bool, message: str = "") -> None:
        if not self._current:
            return
        self._completed.append(
            ExecutionRecord(
                step_index=self._current_step_index,
                action=self._current.action,
                target_name=self._current.target_name,
                target_obj_id=self._current.target_obj_id,
                success=success,
                message=message,
            )
        )
        self._current = None

    def records(self) -> List[ExecutionRecord]:
        return list(self._completed)

    def progress_snapshot(self) -> ProgressSnapshot:
        completed = [
            {
                "step": str(r.step_index),
                "action": r.action,
                "target": r.target_name,
                "result": "success" if r.success else "fail",
            }
            for r in self._completed
        ]
        in_progress = None
        if self._current:
            in_progress = {"action": self._current.action, "target": self._current.target_name}
        pending = [{"action": t.action, "target": t.target_name} for t in self._pending]
        return ProgressSnapshot(
            original_instruction=self.original_instruction,
            completed=completed,
            in_progress=in_progress,
            pending=pending,
        )

    def status_text(self, mode: str = "simulation") -> str:
        progress = self.progress_snapshot()
        lines = [
            f"执行模式: {mode}",
            f"当前大任务: {self.original_instruction or '无'}",
            f"已完成: {len(progress.completed)}",
            f"进行中: {progress.in_progress or '无'}",
            f"待执行: {len(progress.pending)}",
        ]
        if progress.pending:
            for idx, task in enumerate(progress.pending, start=1):
                lines.append(f"  {idx}. {task['action']} -> {task['target']}")
        return "\n".join(lines)

