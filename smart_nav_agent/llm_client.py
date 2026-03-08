from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - runtime environment dependent
    OpenAI = None  # type: ignore

from .config import Config
from .exceptions import LLMError
from .models import ExecutionRecord, ProgressSnapshot, SubTask, TaskPlan


class LLMClient:
    def __init__(self, config: Config):
        self.config = config
        self.model = str(config.get("llm.model", "deepseek-chat"))
        self.temperature = float(config.get("llm.temperature", 0.2))
        self.max_tokens = int(config.get("llm.max_tokens", 1024))
        self.timeout = int(config.get("llm.timeout", 45))
        self.api_key = str(config.get("llm.api_key", "")).strip()
        base_url = str(config.get("llm.base_url", "https://api.deepseek.com")).strip()
        self.client: Optional[Any] = None
        if self.api_key:
            if OpenAI is None:
                raise LLMError("openai SDK 未安装，请先 `pip install -r requirements.txt`。")
            self.client = OpenAI(api_key=self.api_key, base_url=base_url, timeout=self.timeout)

    def _chat(self, messages: List[Dict[str, str]]) -> str:
        if not self.client:
            raise LLMError("No API key configured for LLM.")
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            content = resp.choices[0].message.content
            if not content:
                raise LLMError("LLM returned empty content.")
            return content
        except Exception as e:
            raise LLMError(f"LLM request failed: {e}") from e

    def _extract_json(self, text: str) -> Dict[str, Any]:
        raw = text.strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.startswith("json"):
                raw = raw[4:].strip()
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end < 0 or end <= start:
            raise LLMError("Cannot find JSON object in LLM response.")
        fragment = raw[start : end + 1]
        try:
            return json.loads(fragment)
        except json.JSONDecodeError as e:
            raise LLMError(f"Failed to parse LLM JSON: {e}") from e

    def _fallback_plan(self, instruction: str, semantic_objects: List[Dict[str, Any]]) -> TaskPlan:
        instruction_l = instruction.lower()
        chosen = None
        for obj in semantic_objects:
            keys = [obj.get("name", ""), *obj.get("aliases", []), obj.get("category", ""), obj.get("room", "")]
            if any(k and k.lower() in instruction_l for k in keys):
                chosen = obj
                break
        subtasks: List[SubTask] = []
        if chosen:
            subtasks.append(SubTask(action="navigate", target_name=str(chosen["name"]), reason="fallback keyword match"))
        return TaskPlan(
            original_instruction=instruction,
            subtasks=subtasks,
            notes="fallback plan (no API key or LLM failed)",
        )

    def plan_tasks(
        self,
        instruction: str,
        semantic_objects: List[Dict[str, Any]],
        progress: ProgressSnapshot,
        recent_dialogue: List[Dict[str, str]],
        max_subtasks: int = 8,
    ) -> TaskPlan:
        if not self.client:
            return self._fallback_plan(instruction, semantic_objects)

        system_prompt = (
            "你是机器人导航任务规划器。"
            "仅能使用语义地图中已有物体进行规划。"
            "输出严格JSON，不要输出其他文字。"
            '格式: {"subtasks":[{"action":"navigate","target":"物体名","reason":"原因"}],"notes":"说明"}。'
            f"子任务最多 {max_subtasks} 个。"
        )
        user_payload = {
            "instruction": instruction,
            "semantic_map_objects": semantic_objects,
            "current_progress": {
                "original_instruction": progress.original_instruction,
                "completed": progress.completed,
                "in_progress": progress.in_progress,
                "pending": progress.pending,
            },
            "recent_dialogue": recent_dialogue,
        }
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ]

        content = self._chat(messages)
        parsed = self._extract_json(content)
        subtasks_raw = parsed.get("subtasks", [])
        if not isinstance(subtasks_raw, list):
            raise LLMError("LLM subtasks format invalid.")

        subtasks: List[SubTask] = []
        for item in subtasks_raw[:max_subtasks]:
            if not isinstance(item, dict):
                continue
            action = str(item.get("action", "navigate")).strip() or "navigate"
            target = str(item.get("target", "")).strip()
            if not target:
                continue
            reason = str(item.get("reason", "")).strip()
            subtasks.append(SubTask(action=action, target_name=target, reason=reason))

        return TaskPlan(
            original_instruction=instruction,
            subtasks=subtasks,
            notes=str(parsed.get("notes", "")).strip(),
        )

    def summarize_task(
        self,
        original_instruction: str,
        records: List[ExecutionRecord],
        progress: ProgressSnapshot,
        recent_dialogue: List[Dict[str, str]],
    ) -> str:
        if not records:
            return "没有可总结的任务执行记录。"

        if not self.client:
            success_count = sum(1 for r in records if r.success)
            return f"任务结束：共 {len(records)} 步，成功 {success_count} 步，失败 {len(records)-success_count} 步。"

        system_prompt = "你是机器人执行结果总结助手，请输出简明中文总结。"
        rec_json = [
            {
                "step_index": r.step_index,
                "action": r.action,
                "target_name": r.target_name,
                "target_obj_id": r.target_obj_id,
                "success": r.success,
                "message": r.message,
            }
            for r in records
        ]
        user_payload = {
            "original_instruction": original_instruction,
            "execution_records": rec_json,
            "current_progress": {
                "original_instruction": progress.original_instruction,
                "completed": progress.completed,
                "in_progress": progress.in_progress,
                "pending": progress.pending,
            },
            "recent_dialogue": recent_dialogue,
        }
        text = self._chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ]
        )
        return text.strip()

    def notify_interrupt(self, interrupted_instruction: str, reason: str = "user_interrupt") -> str:
        if not self.client:
            return f"任务已中断：{interrupted_instruction}"
        payload = {"interrupted_instruction": interrupted_instruction, "reason": reason}
        text = self._chat(
            [
                {"role": "system", "content": "用户中断了机器人任务，请给出一句中文确认回应。"},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ]
        )
        return text.strip()
