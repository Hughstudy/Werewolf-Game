"""
AI玩家系统 - 清理版本
实现基于思考-行动模式的AI玩家逻辑
"""

import random
from typing import Dict, List, Optional, Any
from datetime import datetime
from models import Player, RoleType, GameState
from ai_client import AIClientManager
from openai_config import OpenAIClientManager


class AIMemory:
    """AI记忆系统"""

    def __init__(self):
        self.speech_history: List[Dict] = []  # 发言历史
        self.thinking_history: List[Dict] = []  # 思考历史
        self.game_events: List[Dict] = []      # 游戏事件历史

    def add_speech(self, round: int, player_id: int, speech: str):
        """添加发言记录"""
        self.speech_history.append({
            "round": round,
            "player_id": player_id,
            "speech": speech,
            "timestamp": datetime.now()
        })

    def add_thinking(self, round: int, phase: str, thinking: str):
        """添加思考记录"""
        self.thinking_history.append({
            "round": round,
            "phase": phase,
            "thinking": thinking,
            "timestamp": datetime.now()
        })

    def add_game_event(self, round: int, phase: str, event: str):
        """添加游戏事件"""
        self.game_events.append({
            "round": round,
            "phase": phase,
            "event": event,
            "timestamp": datetime.now()
        })

    def compact_state(self, current_round: int) -> str:
        """压缩当前状态为字符串"""
        recent_speeches = [s for s in self.speech_history if s["round"] >= current_round - 2]
        recent_events = [e for e in self.game_events if e["round"] >= current_round - 1]

        state = f"第{current_round}轮记忆摘要:\n"

        if recent_events:
            state += "重要事件:\n"
            for event in recent_events[-5:]:  # 最近5个事件
                state += f"- {event['event']}\n"

        if recent_speeches:
            state += "最近发言:\n"
            for speech in recent_speeches[-10:]:  # 最近10个发言
                state += f"- 玩家{speech['player_id']}: {speech['speech']}\n"

        return state


class AIThinking:
    """AI思考记录"""

    def __init__(self, player_id: int, players: List[Player], game_state: GameState, memory: AIMemory):
        self.player_id = player_id
        self.round = game_state.current_round
        self.phase = game_state.phase
        self.timestamp = datetime.now()

        # 基础信息
        self.all_players = players
        self.alive_players = [p for p in players if p.alive]
        self.my_player = next(p for p in players if p.id == player_id)
        self.my_role = self.my_player.role
        self.memory = memory

        # 分析结果
        self.suspicion_levels: Dict[int, float] = {}  # 对其他玩家的怀疑程度 (0-1)
        self.trust_levels: Dict[int, float] = {}      # 对其他玩家的信任程度 (0-1)
        self.strategy_thoughts: str = ""              # 策略思考

        # 决策结果
        self.recommended_actions: Dict[str, Any] = {}

        # 思考过程记录
        self.thinking_process: str = ""

    def analyze_situation(self):
        """分析当前局势"""
        # 根据角色进行不同的分析
        if self.my_role == RoleType.WEREWOLF:
            self._analyze_as_werewolf()
        elif self.my_role == RoleType.SEER:
            self._analyze_as_seer()
        elif self.my_role == RoleType.WITCH:
            self._analyze_as_witch()
        elif self.my_role == RoleType.HUNTER:
            self._analyze_as_hunter()
        else:  # VILLAGER
            self._analyze_as_villager()

    def _analyze_as_werewolf(self):
        """狼人AI分析"""
        # 识别队友
        [p for p in self.alive_players if p.role == RoleType.WEREWOLF and p.id != self.player_id]

        # 识别威胁目标
        threats = []
        for player in self.alive_players:
            if player.role != RoleType.WEREWOLF:
                threat_level = 0.5
                # 神职角色威胁更高
                if player.role in [RoleType.SEER, RoleType.WITCH, RoleType.HUNTER]:
                    threat_level = 0.8
                threats.append((player.id, threat_level))

        # 设置怀疑度（伪装）
        for player in self.alive_players:
            if player.id == self.player_id:
                continue
            if player.role == RoleType.WEREWOLF:
                self.suspicion_levels[player.id] = 0.1  # 队友，低怀疑度
                self.trust_levels[player.id] = 0.9
            else:
                # 对好人假装怀疑
                self.suspicion_levels[player.id] = random.uniform(0.3, 0.7)
                self.trust_levels[player.id] = 1 - self.suspicion_levels[player.id]

        # 推荐：优先击杀神职
        if threats:
            threats.sort(key=lambda x: x[1], reverse=True)
            self.recommended_actions["kill_target"] = threats[0][0]

    def _analyze_as_seer(self):
        """预言家AI分析"""
        # 基于查验结果分析
        known_werewolves = [pid for pid, result in getattr(self.my_player, 'seer_results', {}).items() if result == "狼人"]
        known_good = [pid for pid, result in getattr(self.my_player, 'seer_results', {}).items() if result == "好人"]

        for player in self.alive_players:
            if player.id == self.player_id:
                continue

            if player.id in known_werewolves:
                self.suspicion_levels[player.id] = 1.0
                self.trust_levels[player.id] = 0.0
            elif player.id in known_good:
                self.suspicion_levels[player.id] = 0.0
                self.trust_levels[player.id] = 1.0
            else:
                # 未知玩家，基于发言和行为分析
                self.suspicion_levels[player.id] = random.uniform(0.2, 0.6)
                self.trust_levels[player.id] = 1 - self.suspicion_levels[player.id]

        # 推荐：查验最可疑的未知玩家
        unknown_players = [p for p in self.alive_players if p.id != self.player_id and p.id not in known_werewolves and p.id not in known_good]
        if unknown_players:
            unknown_players.sort(key=lambda p: self.suspicion_levels[p.id], reverse=True)
            self.recommended_actions["check_target"] = unknown_players[0].id

    def _analyze_as_witch(self):
        """女巫AI分析"""
        # 女巫需要平衡用药
        for player in self.alive_players:
            if player.id == self.player_id:
                continue

            # 基础怀疑度
            self.suspicion_levels[player.id] = random.uniform(0.2, 0.6)
            self.trust_levels[player.id] = 1 - self.suspicion_levels[player.id]

        # 如果有验银水（预言家查验过的好人），提高信任度
        # 这里简化处理
        self.recommended_actions["save_tonight"] = True  # 第一晚通常救人
        self.recommended_actions["poison_target"] = None  # 暂时不毒人

    def _analyze_as_hunter(self):
        """猎人AI分析"""
        # 猎人需要识别狼人，为死亡做准备
        for player in self.alive_players:
            if player.id == self.player_id:
                continue
            self.suspicion_levels[player.id] = random.uniform(0.2, 0.6)
            self.trust_levels[player.id] = 1 - self.suspicion_levels[player.id]

        # 如果死亡，优先带走最可疑的人
        if self.suspicion_levels:
            most_suspicious = max(self.suspicion_levels.items(), key=lambda x: x[1])
            self.recommended_actions["shoot_if_dead"] = most_suspicious[0]

    def _analyze_as_villager(self):
        """村民AI分析"""
        # 村民主要依靠逻辑推理
        for player in self.alive_players:
            if player.id == self.player_id:
                continue
            self.suspicion_levels[player.id] = random.uniform(0.3, 0.5)
            self.trust_levels[player.id] = 1 - self.suspicion_levels[player.id]


class AIPlayer:
    """AI玩家类"""

    def __init__(self, ai_id: int, ai_name: str, ai_role: Optional[RoleType] = None):
        self.id = ai_id
        self.name = ai_name
        self.role = ai_role
        self.memory = AIMemory()  # 新的记忆系统
        self.thinking_history: List[AIThinking] = []

        # OpenAI客户端
        self.openai_client: Optional[OpenAIClientManager] = None

    async def think(self, players: List[Player], game_state: GameState, spectator_mode: bool = False) -> AIThinking:
        """第一步：使用OpenAI进行深度思考分析"""
        # 初始化OpenAI客户端
        if self.openai_client is None:
            try:
                self.openai_client = OpenAIClientManager()
                await self.openai_client.initialize()
            except Exception as e:
                print(f"[系统] AI玩家{self.id} OpenAI客户端初始化失败: {e}")
                raise Exception(f"OpenAI客户端初始化失败: {e}")

        thinking = AIThinking(self.id, players, game_state, self.memory)

        # 使用OpenAI进行策略思考
        try:
            # 获取压缩的当前状态
            current_state = self.memory.compact_state(game_state.current_round)

            # 构建思考prompt
            thinking_prompt = f"""
你是玩家{self.id}，角色是{self.role.value}。

{current_state}

当前游戏状态:
- 第{game_state.current_round}轮，{game_state.phase.value}阶段
- 存活玩家: {[p.id for p in thinking.alive_players]}
- 你的角色: {self.role.value}

请进行深度策略思考:
1. 分析当前局势和威胁
2. 识别可能的队友和敌人
3. 制定本阶段的行动策略
4. 预测其他玩家的行动

请用简洁的要点回答（50-100字）。
"""

            # 调用OpenAI生成思考
            thinking_response = await self.openai_client.generate_response(
                thinking_prompt,
                self.role.value,
                {
                    "round": game_state.current_round,
                    "phase": game_state.phase.value,
                    "role": self.role.value
                }
            )

            thinking.thinking_process = thinking_response
            thinking.strategy_thoughts = thinking_response

            # 观战模式下显示AI思考过程
            if spectator_mode:
                print(f"\n🧠 [AI思考] 玩家{self.id} ({self.role.value}) 第{game_state.current_round}轮{game_state.phase.value}阶段:")
                print(f"💭 {thinking_response}")

            # 记录思考到记忆中
            self.memory.add_thinking(game_state.current_round, game_state.phase.value, thinking_response)

        except Exception as e:
            print(f"[系统] AI玩家{self.id} 思考失败: {e}")
            raise Exception(f"OpenAI思考失败: {e}")

        # 基于思考结果进行简单分析（备用）
        thinking.analyze_situation()

        # 保存到历史记录
        self.thinking_history.append(thinking)

        return thinking

    def _get_role_system_prompt(self) -> str:
        """获取角色特定的系统提示词"""
        role_prompts = {
            "狼人": """你是狼人阵营的核心成员。你的目标是隐藏身份，误导好人，保护狼队友。
关键策略：
- 绝不暴露真实身份
- 假装分析推理，暗中保护队友
- 制造好人之间的猜疑
- 在关键时刻误导投票方向
- 与狼队友配合行动

记住：获胜需要消灭所有好人或让好人数量≤狼人数量。""",

            "预言家": """你是好人阵营的预言家。你的目标是找出所有狼人。
关键策略：
- 第一晚开始就要公布身份和查验结果
- 每晚必须查验并公布结果（金水/查杀）
- 带领好人阵营投票
- 识别假预言家（悍跳狼）
- 解释查验逻辑，建立威信

记住：你的信息对好人阵营至关重要。""",

            "女巫": """你是拥有解药和毒药的女巫。你是好人阵营的重要角色。
关键策略：
- 第一晚通常救人（除非明确知道刀口是谁）
- 谨慎使用毒药，只在确定狼人时使用
- 可以适当暗示身份获取信任
- 配合预言家的验人结果
- 保护自己比救人更重要

记住：你只有一瓶解药和一瓶毒药。""",

            "猎人": """你是拥有威慑力的猎人。你是好人阵营的保护者。
关键策略：
- 明确身份增加威慑力
- 死亡时必须带走最可疑的人
- 保护预言家等关键角色
- 发言要有威慑作用
- 相信自己的判断

记住：你的枪是好人阵营的重要武器。""",

            "村民": """你是普通的村民，需要通过逻辑推理帮助好人获胜。
关键策略：
- 仔细分析每个人的发言
- 相信真正的预言家
- 不要轻易自称神职
- 识别发言中的漏洞
- 团结好人阵营

记住：你的投票对找出狼人很重要。"""
        }

        return role_prompts.get(self.role.value, "你是狼人杀游戏的玩家，需要根据你的角色制定最佳策略。")

    async def act(self, thinking: AIThinking, action_type: str) -> Optional[int]:
        """第二步：根据思考结果执行行动"""
        if action_type == "werewolf_kill":
            return await self._choose_werewolf_target(thinking)
        elif action_type == "seer_check":
            return await self._choose_seer_target(thinking)
        elif action_type == "witch_action":
            return await self._choose_witch_action(thinking)
        elif action_type == "vote":
            return await self._choose_vote_target(thinking)
        elif action_type == "hunter_shoot":
            return await self._choose_hunter_target(thinking)
        else:
            return None

    async def _choose_werewolf_target(self, thinking: AIThinking) -> Optional[int]:
        """选择狼人击杀目标 - 使用OpenAI决策"""
        try:
            # 使用OpenAI进行智能击杀决策
            non_werewolves = [p for p in thinking.alive_players if p.role != RoleType.WEREWOLF]
            if not non_werewolves:
                return None

            target_list = []
            for target in non_werewolves:
                role_priority = 5 if target.role in [RoleType.SEER, RoleType.WITCH, RoleType.HUNTER] else 1
                target_list.append(f"{target.id}. {target.name} (威胁等级: {role_priority})")

            # 识别狼人队友
            werewolf_teammates = [p for p in thinking.alive_players if p.role == RoleType.WEREWOLF and p.id != self.id]
            teammate_info = f"狼人队友: {[f'玩家{w.id}' for w in werewolf_teammates]}" if werewolf_teammates else "无其他狼人队友"

            decision_prompt = f"""
作为狼人，选择今晚要击杀的目标。

{teammate_info}

存活目标：
{chr(10).join(target_list)}

重要提醒：
- 你的狼人队友是上面列出的玩家，绝对不要攻击队友
- 只能从非狼人玩家中选择击杀目标
- 优先击杀神职（预言家、女巫、猎人），他们威胁最大
- 其次击除普通村民

请只回复目标玩家的数字ID，不要其他内容。
"""

            response = await self.openai_client.generate_response(
                decision_prompt,
                "WEREWOLF",
                {
                    "round": thinking.round,
                    "phase": "夜晚",
                    "role": "WEREWOLF",
                    "action": "击杀决策"
                }
            )

            try:
                target_id = int(response.strip())
                if target_id in [p.id for p in non_werewolves]:
                    return target_id
            except ValueError:
                pass

            # AI响应无效时使用推荐目标
            if "kill_target" in thinking.recommended_actions:
                return thinking.recommended_actions["kill_target"]

            # 备选方案：优先击杀神职
            gods = [p for p in non_werewolves if p.role in [RoleType.SEER, RoleType.WITCH, RoleType.HUNTER]]
            return random.choice(gods).id if gods else random.choice(non_werewolves).id

        except Exception as e:
            print(f"[系统] AI玩家{self.id} 狼人击杀决策失败: {e}")
            raise Exception(f"OpenAI击杀决策失败: {e}")

    async def _choose_seer_target(self, thinking: AIThinking) -> Optional[int]:
        """选择预言家查验目标 - 使用OpenAI决策"""
        try:
            # 获取已查验过的玩家
            checked_players = set(getattr(thinking.my_player, 'seer_results', {}).keys())
            unknown_players = [p for p in thinking.alive_players if p.id != self.id and p.id not in checked_players]

            if not unknown_players:
                return None

            target_list = []
            for target in unknown_players:
                # 基于发言活跃度、行为可疑度等因素排序
                suspicion_score = thinking.suspicion_levels.get(target.id, 0.5)
                target_list.append(f"{target.id}. {target.name} (可疑度: {suspicion_score:.2f})")

            decision_prompt = f"""
作为预言家，选择今晚要查验的目标。

可查验目标：
{chr(10).join(target_list)}

查验策略：
1. 优先查验发言最活跃的人（可能是狼人带节奏）
2. 查验发言矛盾的人（可能在撒谎）
3. 查验很少发言的人（可能在隐藏身份）
4. 查验自称神职的人（验证身份真假）

请只回复目标玩家的数字ID，不要其他内容。
"""

            response = await self.openai_client.generate_response(
                decision_prompt,
                "SEER",
                {
                    "round": thinking.round,
                    "phase": "夜晚",
                    "role": "SEER",
                    "action": "查验决策"
                }
            )

            try:
                target_id = int(response.strip())
                if target_id in [p.id for p in unknown_players]:
                    return target_id
            except ValueError:
                pass

            # AI响应无效时使用推荐目标
            if "check_target" in thinking.recommended_actions:
                return thinking.recommended_actions["check_target"]

            # 备选方案：查验最可疑的未知玩家
            if thinking.suspicion_levels:
                most_suspicious = max(thinking.suspicion_levels.items(), key=lambda x: x[1])
                if most_suspicious[0] in [p.id for p in unknown_players]:
                    return most_suspicious[0]

            return random.choice(unknown_players).id

        except Exception as e:
            print(f"[系统] AI玩家{self.id} 预言家查验决策失败: {e}")
            raise Exception(f"OpenAI查验决策失败: {e}")

    async def _choose_witch_action(self, thinking: AIThinking, killed_player: Optional[int], can_save: bool, can_poison: bool) -> Dict[str, Any]:
        """选择女巫行动"""
        action = {"save": False, "poison": None}

        # 救人决策 - 考虑是否有解药
        if can_save and killed_player is not None:
            # 第一晚倾向于救人
            if thinking.round == 1:
                action["save"] = True
            # 后续晚上基于分析决定
            elif thinking.recommended_actions.get("save_tonight", False):
                action["save"] = True

        # 毒人决策 - 考虑是否有毒药
        if can_poison and thinking.suspicion_levels:
            most_suspicious = max(thinking.suspicion_levels.items(), key=lambda x: x[1])
            if most_suspicious[1] > 0.8:  # 高度怀疑才毒
                action["poison"] = most_suspicious[0]

        return action

    async def _choose_vote_target(self, thinking: AIThinking) -> Optional[int]:
        """选择投票目标 - 使用OpenAI决策"""
        try:
            # 获取可投票的玩家
            votable_players = [p for p in thinking.alive_players if p.id != self.id]
            if not votable_players:
                return None

            target_list = []
            for target in votable_players:
                suspicion_score = thinking.suspicion_levels.get(target.id, 0.5)
                trust_score = thinking.trust_levels.get(target.id, 0.5)
                target_list.append(f"{target.id}. {target.name} (可疑度: {suspicion_score:.2f}, 信任度: {trust_score:.2f})")

            # 根据角色制定投票策略
            role_strategy = {
                "WEREWOLF": "投票给最可疑的好人，保护狼队友，融入群体",
                "SEER": "投票给查杀的狼人，带领好人阵营",
                "WITCH": "相信真预言家，投票给可疑的狼人",
                "HUNTER": "投票给最可疑的狼人，准备开枪",
                "VILLAGER": "跟随真预言家，投票给最可疑的人"
            }

            strategy = role_strategy.get(self.role.value, "投票给最可疑的人")

            # 如果是狼人，明确告知队友信息
            teammate_info = ""
            if self.role == RoleType.WEREWOLF:
                werewolf_teammates = [p for p in thinking.alive_players if p.role == RoleType.WEREWOLF and p.id != self.id]
                if werewolf_teammates:
                    teammate_info = f"\n重要提醒：你的狼人队友是 {[f'玩家{w.id}' for w in werewolf_teammates]}，绝对不要投票给队友！"

            decision_prompt = f"""
作为{self.role.value}，选择今天的投票目标。

可投票目标：
{chr(10).join(target_list)}

你的角色策略：{strategy}{teammate_info}

投票原则：
1. 根据你的角色特点和已知信息做决策
2. 考虑之前的发言和行为
3. 避免投错人（特别是神职角色）
4. 团结你的阵营

请只回复目标玩家的数字ID，不要其他内容。
"""

            response = await self.openai_client.generate_response(
                decision_prompt,
                self.role.value,
                {
                    "round": thinking.round,
                    "phase": "投票",
                    "role": self.role.value,
                    "action": "投票决策"
                }
            )

            try:
                target_id = int(response.strip())
                if target_id in [p.id for p in votable_players]:
                    return target_id
            except ValueError:
                pass

            # AI响应无效时的备用逻辑
            if thinking.suspicion_levels:
                most_suspicious = max(thinking.suspicion_levels.items(), key=lambda x: x[1])

                # 狼人不会投票给队友
                if self.role == RoleType.WEREWOLF:
                    werewolves = [p for p in thinking.alive_players if p.role == RoleType.WEREWOLF and p.id != self.id]
                    if most_suspicious[0] not in [w.id for w in werewolves]:
                        return most_suspicious[0]
                    else:
                        # 投票给第二可疑的非队友
                        sorted_suspicious = sorted(thinking.suspicion_levels.items(), key=lambda x: x[1], reverse=True)
                        for pid, suspicion in sorted_suspicious:
                            if pid not in [w.id for w in werewolves]:
                                return pid

                return most_suspicious[0]

            return random.choice(votable_players).id

        except Exception as e:
            print(f"[系统] AI玩家{self.id} 投票决策失败: {e}")
            raise Exception(f"OpenAI投票决策失败: {e}")

    async def _choose_hunter_target(self, thinking: AIThinking) -> Optional[int]:
        """选择猎人开枪目标"""
        if "shoot_if_dead" in thinking.recommended_actions:
            return thinking.recommended_actions["shoot_if_dead"]

        # 开枪给最可疑的人
        if thinking.suspicion_levels:
            most_suspicious = max(thinking.suspicion_levels.items(), key=lambda x: x[1])
            return most_suspicious[0]
        return None

    async def generate_speech(self, players: List[Player], game_state: GameState, spectator_mode: bool = False) -> str:
        """生成发言内容"""
        thinking = await self.think(players, game_state, spectator_mode)

        # 使用OpenAI生成发言
        try:
            # 构建更具上下文的发言prompt
            current_state = self.memory.compact_state(game_state.current_round)

            # 如果是狼人，明确告知队友信息以避免发言时误伤队友
            teammate_reminder = ""
            if self.role == RoleType.WEREWOLF:
                werewolf_teammates = [p for p in thinking.alive_players if p.role == RoleType.WEREWOLF and p.id != self.id]
                if werewolf_teammates:
                    teammate_reminder = f"\n重要提醒：你的狼人队友是 {[f'玩家{w.id}' for w in werewolf_teammates]}。发言时注意：\n- 绝对不要暴露队友身份\n- 不要指责或攻击队友\n- 必要时可以暗中为队友辩护\n- 引导投票向其他目标"

            speech_prompt = f"""
你是玩家{self.id}（{self.role.value}），现在是第{game_state.current_round}轮的{game_state.phase.value}阶段。

{current_state}{teammate_reminder}

你的策略思考: {thinking.strategy_thoughts}

请根据你的角色和当前局势，发表一段有策略性的发言（30-80字）：
- 要符合你的角色特点
- 体现你的策略意图
- 可以隐藏信息或误导他人（如果你是狼人）
- 发言要有说服力

只说发言内容，不要其他解释。
"""

            # 生成发言
            speech = await self.openai_client.generate_response(
                speech_prompt,
                self.role.value,
                {
                    "round": game_state.current_round,
                    "phase": game_state.phase.value,
                    "role": self.role.value
                }
            )

            # 观战模式下显示AI发言
            if spectator_mode:
                print(f"💬 [AI发言] 玩家{self.id} ({self.role.value}): {speech}")

            # 记录发言到记忆中
            self.memory.add_speech(game_state.current_round, self.id, speech)

            return speech

        except Exception as e:
            print(f"[系统] AI玩家{self.id} 发言生成失败: {e}")
            raise Exception(f"OpenAI发言生成失败: {e}")

    def _fallback_speech(self, thinking: AIThinking) -> str:
        """备用发言生成（当OpenAI不可用时）"""
        if self.role == RoleType.WEREWOLF:
            return "我是好人，我觉得大家应该仔细分析昨晚的情况。"
        elif self.role == RoleType.SEER:
            return "我是预言家，昨晚查验了一个人，稍后会公布结果。"
        elif self.role == RoleType.WITCH:
            return "我有一些信息想分享，大家要认真听。"
        elif self.role == RoleType.HUNTER:
            return "我是猎人，狼人最好小心点。"
        else:  # VILLAGER
            return "我是村民，希望大家能找出狼人。"

    def _generate_werewolf_speech(self, thinking: AIThinking) -> str:
        """生成狼人发言"""
        speeches = [
            f"我是{thinking.my_role.value}，我觉得我们应该分析一下昨晚的情况。",
            "我建议我们仔细听听每个人的发言。",
            "我觉得有些人的发言很有问题。",
            "我们需要找出真正的狼人。",
            "从我观察来看，有些人很值得怀疑。"
        ]

        # 加一些伪装内容
        if thinking.suspicion_levels:
            # 指控一个好人（但不要是队友）
            non_werewolves = [(pid, level) for pid, level in thinking.suspicion_levels.items()
                            if pid != self.id and next((p for p in thinking.all_players if p.id == pid), None).role != RoleType.WEREWOLF]
            if non_werewolves:
                target_id = max(non_werewolves, key=lambda x: x[1])[0]
                next(p.name for p in thinking.all_players if p.id == target_id)
                speeches.append(f"我比较怀疑玩家{target_id}，因为他的发言有些矛盾。")

        return random.choice(speeches)

    def _generate_seer_speech(self, thinking: AIThinking) -> str:
        """生成预言家发言"""
        # 预言家通常会报查验结果
        my_results = getattr(thinking.my_player, 'seer_results', {})

        if my_results:
            # 报昨夜的查验结果
            last_check = list(my_results.items())[-1]
            target_id, result = last_check
            next(p.name for p in thinking.all_players if p.id == target_id)
            return f"我是预言家，昨晚查验了玩家{target_id}，他是{result}。"
        else:
            # 第一晚
            return "我是预言家，今晚我会开始查验。"

    def _generate_witch_speech(self, thinking: AIThinking) -> str:
        """生成女巫发言"""
        speeches = [
            "我是女巫，第一晚我救人了。",
            "作为女巫，我会谨慎使用我的药水。",
            "大家有什么想法可以交流一下。",
            "我会根据情况决定是否使用毒药。"
        ]
        return random.choice(speeches)

    def _generate_hunter_speech(self, thinking: AIThinking) -> str:
        """生成猎人发言"""
        speeches = [
            "我是猎人，如果我被投票出局，我会带走一个人。",
            "作为猎人，希望大家投票要慎重。",
            "我会仔细分析每个人的发言。",
            "我的枪口会对准可疑的人。"
        ]
        return random.choice(speeches)

    def _generate_villager_speech(self, thinking: AIThinking) -> str:
        """生成村民发言"""
        speeches = [
            "我是个普通村民，希望大家能找出狼人。",
            "我觉得我们应该从发言中找线索。",
            "我会认真听每个人的分析。",
            "作为好人，我会支持正义的一方。"
        ]
        return random.choice(speeches)

    def _update_memory(self, thinking: AIThinking):
        """更新AI记忆"""
        # 记录其他玩家的行为模式
        for player_id, suspicion in thinking.suspicion_levels.items():
            if player_id not in self.memory:
                self.memory[player_id] = {
                    "suspicion_history": [],
                    "trust_history": [],
                    "actions": []
                }

            self.memory[player_id]["suspicion_history"].append(suspicion)
            self.memory[player_id]["trust_history"].append(thinking.trust_levels.get(player_id, 0))

        # 限制记忆长度
        if len(self.thinking_history) > 10:
            self.thinking_history.pop(0)

    # 为了兼容旧代码，保留一些方法名
    async def choose_werewolf_target(self, players: List[Player], game_state: GameState, spectator_mode: bool = False) -> Optional[int]:
        thinking = await self.think(players, game_state, spectator_mode)
        target_id = await self._choose_werewolf_target(thinking)
        if spectator_mode and target_id is not None:
            print(f"🎯 [AI行动] 玩家{self.id} ({self.role.value}) 选择击杀目标: 玩家{target_id}")
        return target_id

    async def choose_seer_target(self, players: List[Player], game_state: GameState, spectator_mode: bool = False) -> Optional[int]:
        thinking = await self.think(players, game_state, spectator_mode)
        target_id = await self._choose_seer_target(thinking)
        if spectator_mode and target_id is not None:
            print(f"🔍 [AI行动] 玩家{self.id} ({self.role.value}) 选择查验目标: 玩家{target_id}")
        return target_id

    async def choose_witch_action(self, players: List[Player], game_state: GameState, killed_player: Optional[int], can_save: bool = True, can_poison: bool = True, spectator_mode: bool = False) -> Dict[str, Any]:
        thinking = await self.think(players, game_state, spectator_mode)
        action = await self._choose_witch_action(thinking, killed_player, can_save, can_poison)

        # 观战模式下显示女巫决策
        if spectator_mode:
            if killed_player and action["save"] and can_save:
                print(f"💊 [AI行动] 玩家{self.id} ({self.role.value}) 决定使用解药救玩家{killed_player}")
            if action["poison"] and can_poison:
                print(f"☠️ [AI行动] 玩家{self.id} ({self.role.value}) 决定使用毒药毒玩家{action['poison']}")
            if not (killed_player and action["save"] and can_save) and not (action["poison"] and can_poison):
                print(f"⚖️ [AI行动] 玩家{self.id} ({self.role.value}) 决定不使用药水")

        # 如果有人被杀且女巫决定救人
        if killed_player and action["save"] and can_save:
            return {"save": True, "poison": action["poison"] if can_poison else None}
        return {"save": False, "poison": action["poison"] if can_poison else None}

    async def choose_vote_target(self, players: List[Player], game_state: GameState, spectator_mode: bool = False) -> Optional[int]:
        thinking = await self.think(players, game_state, spectator_mode)
        target_id = await self._choose_vote_target(thinking)
        if spectator_mode and target_id is not None:
            print(f"🗳️ [AI行动] 玩家{self.id} ({self.role.value}) 投票给: 玩家{target_id}")
        return target_id

    async def choose_hunter_target(self, players: List[Player], game_state: GameState, spectator_mode: bool = False) -> Optional[int]:
        thinking = await self.think(players, game_state, spectator_mode)
        target_id = await self._choose_hunter_target(thinking)
        if spectator_mode and target_id is not None:
            print(f"🔫 [AI行动] 玩家{self.id} ({self.role.value}) 决定开枪带走: 玩家{target_id}")
        return target_id


if __name__ == "__main__":
    # 测试AI玩家
    ai_player = AIPlayer(1, "AI测试玩家", RoleType.WEREWOLF)
    print(f"创建了AI玩家：{ai_player.name}，角色：{ai_player.role}")
    print(f"激进程度：{ai_player.aggression_level:.2f}")
    print(f"逻辑能力：{ai_player.logic_level:.2f}")