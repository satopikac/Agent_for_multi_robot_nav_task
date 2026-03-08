from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from .models import SemanticObject, SubTask


class BaseNavigationController(ABC):
    @abstractmethod
    def navigate(self, subtask: SubTask, target: SemanticObject) -> bool:
        raise NotImplementedError


class SimulatedROSNavigationController(BaseNavigationController):
    def __init__(self, topic_goal: str, topic_result: str, frame_id: str = "map"):
        self.topic_goal = topic_goal
        self.topic_result = topic_result
        self.frame_id = frame_id

    def _print_move_base_cmd(self, target: SemanticObject) -> None:
        x, y, yaw = target.position
        print("\n[ROS-MOCK] publish move_base goal:")
        print(f"  topic: {self.topic_goal}")
        print("  payload:")
        print(f"    frame_id: {self.frame_id}")
        print(f"    x: {x:.3f}, y: {y:.3f}, yaw: {yaw:.3f}")
        print(f"    target: {target.name} ({target.obj_id}) in room {target.room}")
        print(f"  wait feedback topic: {self.topic_result}")

    def navigate(self, subtask: SubTask, target: SemanticObject) -> bool:
        self._print_move_base_cmd(target)
        while True:
            user_input = input("请输入导航结果 [success/fail]: ").strip().lower()
            if user_input == "success":
                return True
            if user_input == "fail":
                return False
            print("无效输入，请输入 success 或 fail。")


class ROSNavigationController(BaseNavigationController):
    def __init__(self) -> None:
        pass

    def navigate(self, subtask: SubTask, target: SemanticObject) -> bool:
        raise NotImplementedError("Real ROS controller is not implemented yet.")

