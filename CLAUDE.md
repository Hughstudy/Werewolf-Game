# 狼人杀游戏开发文档

## 项目概述
这是一个9人狼人杀文字推理游戏，包含1个真人玩家和8个AI玩家。游戏使用Python + uv + OpenAI API技术栈开发，已完成核心功能实现。

## 角色配置
- **预言家**: 1个 - 每晚可查验一名玩家的真实身份
- **女巫**: 1个 - 拥有灵药（救人）和毒药（毒人）两瓶药水
- **猎人**: 1个 - 被杀或投票后可以开枪射杀一人
- **村民**: 3个 - 没有特殊技能的平民
- **狼人**: 3个 - 每晚可以杀人，白天可以假冒其他角色

## 阵营设置
- **狼人阵营**: 3个狼人
- **好人阵营**: 预言家、女巫、猎人、3个村民

## 获胜条件
- 狼人阵营胜利：好人数量小于等于狼人数量
- 好人阵营胜利：所有狼人死亡

## 核心模块架构

### 1. 游戏引擎 (game_engine.py) ✅ 已完成
```python
class GameEngine:
    async def initialize_game(): 初始化游戏
    async def run_game_loop(): 主游戏循环
    async def _process_night_phase(): 处理夜晚阶段
    async def _process_day_phase(): 处理白天阶段
    async def _process_vote_phase(): 处理投票阶段
    def get_game_status(): 获取游戏状态
```

### 2. AI玩家系统 (ai_player.py) ✅ 已完成
```python
class AIThinking:
    def analyze_situation(): 分析当前局势
    def _analyze_as_werewolf(): 狼人AI分析
    def _analyze_as_seer(): 预言家AI分析
    def _analyze_as_witch(): 女巫AI分析

class AIPlayer:
    async def think(): 第一步 - 基于历史记录思考
    async def act(): 第二步 - 执行具体行动
    async def generate_speech(): 生成发言内容
    async def choose_*_target(): 选择各类行动目标
```

### 3. 角色分配器 (role_assigner.py) ✅ 已完成
```python
class RoleAssigner:
    @staticmethod
    def create_players(): 创建9个玩家(1真人+8AI)
    def assign_roles(): 随机分配角色
    def show_role_distribution(): 显示角色分布
```

### 4. 游戏状态管理器 (game_state_manager.py) ✅ 已完成
```python
class GameStateManager:
    def initialize_game(): 初始化游戏
    def get_alive_players(): 获取存活玩家
    def check_victory_conditions(): 检查胜利条件
    def process_player_death(): 处理玩家死亡
    def get_game_summary(): 获取游戏摘要
```

### 5. 数据模型 (models.py) ✅ 已完成
```python
class Player(BaseModel):
    id: int
    name: str
    role: Optional[RoleType]
    alive: bool
    is_ai: bool

class GameState(BaseModel):
    current_round: int
    phase: PhaseType
    alive_players: List[int]
    history: List[ActionRecord]

class ActionRecord(BaseModel):
    action_type: ActionType
    player_id: int
    target_id: Optional[int]
    phase: str
    round: int
```

### 6. AI客户端系统 (ai_client/) ✅ 已完成重构
```python
# 基础AI客户端 (ai_client/base.py)
class AIClientManager:
    async def initialize(): 初始化Silicon Flow客户端
    async def generate_response(): 生成AI响应
    async def generate_werewolf_target(): 生成狼人击杀目标
    async def generate_seer_target(): 生成预言家查验目标
    async def generate_vote_target(): 生成投票目标

# 角色处理器 (ai_client/role_processors.py)
class WerewolfProcessor: 狼人AI决策逻辑
class SeerProcessor: 预言家AI决策逻辑
class WitchProcessor: 女巫AI决策逻辑
class HunterProcessor: 猎人AI决策逻辑
class VillagerProcessor: 村民AI决策逻辑
```

**配置特性**:
- 仅支持Silicon Flow API (简化配置)
- 默认模型: Qwen/Qwen3-8B
- 高级角色模型: moonshotai/Kimi-K2-Instruct-0905 (预言家)
- 增强的AI角色策略提示和欺骗逻辑

## 游戏流程

### 1. 初始化阶段 ✅
- 创建9个玩家(1真人+8AI)
- 随机分配角色
- 显示角色分布
- 初始化游戏状态

### 2. 夜晚阶段 ✅
- 狼人选择目标杀人
- 预言家查验身份
- 女巫使用药水（救人/毒人）
- 处理夜晚结果和死亡

### 3. 白天阶段 ✅
- 公布昨夜死亡信息
- 存活玩家发言讨论
- AI生成角色化发言

### 4. 投票阶段 ✅
- 所有玩家投票
- 最高票者被处决
- 猎人技能触发(如适用)

### 5. 胜利检查 ✅
- 检查是否满足获胜条件
- 显示游戏结果和统计

## AI行为系统

### AI思考模式（两步法）✅
1. **思考阶段**: `AIThinking.analyze_situation()` - 基于历史记录和当前状态分析
2. **行动阶段**: `AIPlayer.act()` - 执行标准操作

### 角色AI特性 ✅
- **狼人AI**: 伪装策略，隐藏身份，误导投票
- **预言家AI**: 每晚必须查验，白天报查验结果
- **女巫AI**: 谨慎用药，第一晚救人，可能毒杀可疑者
- **猎人AI**: 威慑发言，死亡时带走可疑目标
- **村民AI**: 逻辑推理，分析发言找出狼人

## API接口规范

### 核心游戏接口 ✅
```python
# 游戏初始化
engine = GameEngine(enable_ai_mode=True)
await engine.initialize_game()

# 运行游戏
winner = await engine.run_game_loop()

# 获取游戏状态
status = engine.get_game_status()
```

### AI决策接口 ✅
```python
# 狼人决策
target_id = await ai_player.choose_werewolf_target(players, game_state)

# 预言家决策
target_id = await ai_player.choose_seer_target(players, game_state)

# 女巫决策
action = await ai_player.choose_witch_action(players, game_state, killed_player)

# 投票决策
target_id = await ai_player.choose_vote_target(players, game_state)

# 猎人决策
target_id = await ai_player.choose_hunter_target(players, game_state)

# 发言生成
speech = await ai_player.generate_speech(players, game_state)
```

### 状态管理接口 ✅
```python
# 获取存活玩家
alive_players = manager.get_alive_players()

# 检查胜利条件
winner = manager.check_victory_conditions()

# 处理玩家死亡
manager.process_player_death(player_id, death_cause)

# 获取游戏摘要
summary = manager.get_game_summary()
```

## 配置说明

### 环境变量 ✅
- `SILICON_FLOW_API_KEY`: Silicon Flow API密钥 (必需)
- `SILICON_FLOW_BASE_URL`: API基础地址 (默认: https://api.siliconflow.cn/v1)
- `OPENAI_MODEL_*`: 不同角色的模型配置 (可选)

### Silicon Flow模型配置 ✅
```python
models = {
    "WEREWOLF": "Qwen/Qwen3-8B",                    # 狼人模型
    "VILLAGER": "Qwen/Qwen3-8B",                    # 村民模型
    "SEER": "moonshotai/Kimi-K2-Instruct-0905",     # 预言家模型 (高级推理)
    "WITCH": "Qwen/Qwen3-8B",                       # 女巫模型
    "HUNTER": "Qwen/Qwen3-8B"                       # 猎人模型
}
```

## 启动方式 ✅

### 运行游戏
```bash
uv run python main.py
```

### 游戏模式
1. **简单模式**: 基础AI，无需OpenAI API
2. **完整模式**: 智能AI，需要OpenAI API配置
3. **观战模式**: 纯AI对战，无需参与

## 代码质量

### 运行代码检查 ✅
```bash
uv run ruff check .          # 检查代码质量
uv run ruff check . --fix   # 自动修复问题
```

### 项目结构 ✅
```
werewolf/
├── main.py              # 游戏主入口
├── game_engine.py       # 游戏引擎核心
├── ai_player.py         # AI玩家系统
├── game_state_manager.py # 游戏状态管理
├── models.py            # 数据模型定义
├── role_assigner.py     # 角色分配器
├── ai_client/           # AI客户端系统（重构）
│   ├── __init__.py      # 包导出
│   ├── base.py          # 基础AI客户端
│   └── role_processors.py # 角色处理器
├── openai_config.py     # 兼容性文件
├── openai_config_backup.py # 原始文件备份
├── run.py               # 简单运行脚本
├── pyproject.toml       # 项目配置
└── CLAUDE.md           # 项目文档
```

## 开发进度

### ✅ 已完成模块
- [x] 数据模型定义 (models.py)
- [x] 角色分配系统 (role_assigner.py)
- [x] 游戏状态管理器 (game_state_manager.py)
- [x] AI玩家系统 (ai_player.py) - 完整的思考-行动模式
- [x] 游戏引擎 (game_engine.py) - 完整的游戏循环
- [x] AI客户端系统重构 (ai_client/) - 按角色分离的AI决策逻辑
- [x] OpenAI集成 (ai_client/) - 兼容性保留
- [x] 主程序入口 (main.py)
- [x] 代码质量检查 (ruff)

### 🎮 游戏功能
- [x] 完整的夜晚阶段 (狼人杀人、预言家查验、女巫用药)
- [x] 白天讨论阶段 (AI发言生成)
- [x] 投票阶段 (投票统计和处决)
- [x] 猎人技能 (死亡时开枪)
- [x] 胜利条件检查
- [x] 游戏结果显示和统计

### 🔧 技术特性
- [x] 异步游戏循环
- [x] 类型注解和Pydantic模型
- [x] 模块化设计
- [x] 错误处理
- [x] 代码格式检查

## 扩展功能规划

### 未来可添加功能
- 游戏历史回放
- AI难度等级调整
- 自定义角色配置
- 多语言支持
- 图形界面
- 语音合成
- 在线多人模式

## 使用示例

### 基础使用
```python
import asyncio
from game_engine import GameEngine

async def main():
    # 创建游戏引擎
    engine = GameEngine(enable_ai_mode=True)

    # 初始化游戏
    if await engine.initialize_game():
        # 运行游戏
        winner = await engine.run_game_loop()
        print(f"游戏结束，获胜方：{winner}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 配置Silicon Flow
```python
import os
os.environ["SILICON_FLOW_API_KEY"] = "your-silicon-flow-api-key"
# 可选：自定义模型
os.environ["OPENAI_MODEL_SEER"] = "moonshotai/Kimi-K2-Instruct-0905"
```

---

*本文档随代码更新而更新，最后更新时间：2025-11-09*
- 禁止启动游戏