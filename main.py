from __future__ import annotations

import argparse
import sys

from smart_nav_agent.agent import SmartNavigationAgent
from smart_nav_agent.config import Config
from smart_nav_agent.llm_client import LLMClient
from smart_nav_agent.navigation import SimulatedROSNavigationController
from smart_nav_agent.semantic_map import SemanticMap


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LLM-based Smart Navigation Agent")
    parser.add_argument("--config", default="config.json", help="Path to config JSON")
    parser.add_argument("--map", dest="map_path", default="semantic_map.json", help="Path to semantic map JSON")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        config = Config.from_json(args.config)
        semantic_map = SemanticMap.from_json(args.map_path)
        llm = LLMClient(config)
        navigator = SimulatedROSNavigationController(
            topic_goal=str(config.get("ros.topic_move_base_goal")),
            topic_result=str(config.get("ros.topic_move_base_result")),
            frame_id=str(config.get("ros.frame_id", "map")),
        )
        agent = SmartNavigationAgent(config=config, semantic_map=semantic_map, llm_client=llm, navigator=navigator)
    except Exception as e:
        print(f"初始化失败: {e}")
        return 1

    print("智能导航Agent已启动。输入自然语言任务，或使用 status/状态, interrupt/中断, exit/quit/结束。")
    while True:
        try:
            user_input = input("\n你> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n收到退出信号，系统结束。")
            return 0

        if not user_input:
            continue
        output = agent.handle_command(user_input)
        if output == "exit":
            print("系统正常退出。")
            return 0
        print(f"Agent> {output}")


if __name__ == "__main__":
    sys.exit(main())

