# Smart Navigation Agent

基于 Python + OpenAI SDK（可对接 DeepSeek）的智能导航 Agent，支持中文任务理解、语义地图约束规划、任务队列执行、进度状态管理与任务总结。

## 快速开始

```bash
cd /home/mei123/workspace/agentdemo/pr3
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py --config config.json --map semantic_map.json
```

## 指令

- 自然语言任务：如 `去泡咖啡`、`找遥控器`
- `status` / `状态`：查看当前任务进度
- `interrupt` / `中断`：中断并清空任务队列
- `exit` / `quit` / `结束`：退出系统

## 配置

编辑 `config.json`：

- `llm.api_key`：DeepSeek API Key（通过 OpenAI SDK 调用）
- `llm.base_url`：默认 `https://api.deepseek.com`
- `llm.model`：默认 `deepseek-chat`
- `ros.*`：模拟 move_base 话题配置
- `memory.max_history_turns`：最近对话轮数

## 语义地图

`semantic_map.json` 中定义可用目标物体。系统会在任务规划后做二次校验，只保留地图内可匹配目标。

## 说明

- 若未配置 API Key，系统会使用本地降级规划与总结逻辑，便于离线联调。
- 当前导航执行器为模拟模式，会打印 `move_base` 指令并等待输入 `success/fail`。
- 已预留真实 ROS 导航控制器接口：`smart_nav_agent/navigation.py` 中的 `ROSNavigationController`。

