"""
角色特定的AI处理器
每个角色有自己的决策逻辑和策略提示
"""

import random
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

from models import Player, GameState, RoleType
from .base import BaseAIClient


class BaseRoleProcessor(ABC):
    """角色处理器基类"""

    @abstractmethod
    async def generate_kill_target(self, client: BaseAIClient, players: List[Player], game_state: GameState, current_player_id: int = 0) -> int:
        """生成击杀目标 - 只有狼人和女巫有这个能力"""
        pass

    @abstractmethod
    async def generate_check_target(self, client: BaseAIClient, players: List[Player], game_state: GameState) -> int:
        """生成查验目标 - 只有预言家有这个能力"""
        pass

    @abstractmethod
    async def generate_vote_target(self, client: BaseAIClient, players: List[Player], game_state: GameState) -> int:
        """生成投票目标"""
        pass

    @abstractmethod
    async def generate_speech(self, client: BaseAIClient, players: List[Player], game_state: GameState) -> str:
        """生成发言内容"""
        pass

    def get_strategy_tips(self) -> str:
        """获取策略提示"""
        return "根据你的角色特点和当前局势做出最佳决策。"

    def get_system_prompt(self) -> str:
        """获取角色特定的系统提示词"""
        return "你是狼人杀游戏中的一名玩家，需要根据你的角色做出明智的决策。"


class WerewolfProcessor(BaseRoleProcessor):
    """狼人AI处理器"""

    def get_system_prompt(self) -> str:
        return """你是狼人阵营的核心成员。你的目标是隐藏身份，误导好人，保护狼队友。

关键策略：
- 绝不暴露真实身份
- 假装分析推理，暗中保护队友
- 制造好人之间的猜疑
- 在关键时刻误导投票方向
- 与狼队友配合行动

记住：获胜需要消灭所有好人或让好人数量≤狼人数量。"""

    def get_strategy_tips(self) -> str:
        return """狼人策略：
1. 优先击杀神职（预言家、女巫、猎人）
2. 避免击杀狼队友
3. 选择对好人阵营威胁最大的目标
4. 考虑之前的发言和行为
5. 保护狼队友，转移目标"""

    async def generate_kill_target(self, client: BaseAIClient, players: List[Player], game_state: GameState, current_player_id: int = 0) -> int:
        """生成狼人击杀目标"""
        if not client._initialized:
            # 简单AI：随机选择
            non_werewolves = [p for p in players if p.alive and p.role != RoleType.WEREWOLF]
            return random.choice(non_werewolves).id if non_werewolves else 0

        alive_players = [p for p in players if p.alive]
        non_werewolves = [p for p in alive_players if p.role != RoleType.WEREWOLF]

        if not non_werewolves:
            return 0

        # 智能击杀策略
        role_priority = {
            RoleType.SEER: 5,    # 预言家最危险，优先击杀
            RoleType.WITCH: 4,   # 女巫能救人毒人，很危险
            RoleType.HUNTER: 3,  # 猎人能带走人，中等危险
            RoleType.VILLAGER: 1 # 村民威胁最小
        }

        target_list = []
        for target in non_werewolves:
            priority = role_priority.get(target.role, 1)
            target_list.append(f"{target.id}. {target.name} (优先级: {priority})")

        # 识别狼人队友
        werewolf_teammates = [p for p in alive_players if p.role == RoleType.WEREWOLF and p.id != current_player_id]
        teammate_info = f"狼人队友: {[f'玩家{w.id}' for w in werewolf_teammates]}" if werewolf_teammates else "无其他狼人队友"

        prompt = f"""作为狼人，选择今晚要击杀的目标。

{teammate_info}

存活目标：
{chr(10).join(target_list)}

重要提醒：
- 你的狼人队友是上面列出的玩家，绝对不要攻击队友
- 只能从非狼人玩家中选择击杀目标
- 优先击杀神职（预言家、女巫、猎人），他们威胁最大
- 其次击除普通村民

请只回复目标玩家的数字ID，不要其他内容。"""

        response = await client.generate_response(prompt, "WEREWOLF", max_tokens=10)

        try:
            return int(response.strip())
        except (ValueError, AttributeError):
            # 如果AI返回无效结果，随机选择
            return random.choice(non_werewolves).id

    async def generate_check_target(self, client: BaseAIClient, players: List[Player], game_state: GameState) -> int:
        """狼人没有查验能力"""
        return 0

    async def generate_vote_target(self, client: BaseAIClient, players: List[Player], game_state: GameState) -> int:
        """生成狼人投票目标"""
        votable_players = [p for p in players if p.alive and p.id != 0]  # 假设当前玩家ID为0
        if not votable_players:
            return 0

        if not client._initialized:
            # 简单投票：随机选择非狼人
            non_werewolves = [p for p in votable_players if p.role != RoleType.WEREWOLF]
            return random.choice(non_werewolves).id if non_werewolves else random.choice(votable_players).id

        # 狼人投票策略
        werewolf_teammates = [p for p in votable_players if p.role == RoleType.WEREWOLF]
        non_teammates = [p for p in votable_players if p.role != RoleType.WEREWOLF]

        target_list = []
        for target in votable_players:
            is_teammate = target.role == RoleType.WEREWOLF
            status = "队友" if is_teammate else "好人"
            target_list.append(f"{target.id}. {target.name} ({status})")

        teammate_info = f""
        if werewolf_teammates:
            teammate_info = f"\n重要提醒：你的狼人队友是 {[f'玩家{w.id}' for w in werewolf_teammates]}，绝对不要投票给队友！"

        prompt = f"""作为狼人，选择今天的投票目标。

可投票目标：
{chr(10).join(target_list)}

投票策略：投票给最可疑的好人，保护狼队友，融入群体{teammate_info}

请只回复目标玩家的数字ID，不要其他内容。"""

        response = await client.generate_response(prompt, "WEREWOLF", max_tokens=10)

        try:
            target_id = int(response.strip())
            # 确保不投票给队友
            if target_id in [w.id for w in werewolf_teammates]:
                # 如果AI选择了队友，投票给最可疑的非队友
                return random.choice(non_teammates).id if non_teammates else random.choice(votable_players).id
            return target_id
        except (ValueError, AttributeError):
            # 备用逻辑：投票给最可疑的非队友
            return random.choice(non_teammates).id if non_teammates else random.choice(votable_players).id

    async def generate_speech(self, client: BaseAIClient, players: List[Player], game_state: GameState) -> str:
        """生成狼人发言"""
        werewolf_teammates = [p for p in players if p.alive and p.role == RoleType.WEREWOLF and p.id != 0]
        teammate_info = ""
        if werewolf_teammates:
            teammate_info = f"""
重要提醒：你的狼人队友是 {[f'玩家{w.id}' for w in werewolf_teammates]}。发言时注意：
- 绝对不要暴露队友身份
- 不要指责或攻击队友
- 必要时可以暗中为队友辩护
- 引导投票向其他目标"""

        prompt = f"""你是玩家0（狼人），现在是第{game_state.current_round}轮的{game_state.phase.value}阶段。{teammate_info}

请根据你的狼人角色和当前局势，发表一段有策略性的发言（30-80字）：
- 要符合狼人伪装的特点
- 体现你的策略意图
- 可以隐藏信息或误导他人
- 发言要有说服力

只说发言内容，不要其他解释。"""

        return await client.generate_response(prompt, "WEREWOLF", max_tokens=100)


class SeerProcessor(BaseRoleProcessor):
    """预言家AI处理器"""

    def get_system_prompt(self) -> str:
        return """你是好人阵营的预言家。你的目标是找出所有狼人。

关键策略：
- 第一晚开始就要公布身份和查验结果
- 每晚必须查验并公布结果（金水/查杀）
- 带领好人阵营投票
- 识别假预言家（悍跳狼）
- 解释查验逻辑，建立威信

记住：你的信息对好人阵营至关重要。"""

    async def generate_kill_target(self, client: BaseAIClient, players: List[Player], game_state: GameState, current_player_id: int = 0) -> int:
        """预言家没有击杀能力"""
        return 0

    async def generate_check_target(self, client: BaseAIClient, players: List[Player], game_state: GameState) -> int:
        """生成预言家查验目标"""
        if not client._initialized:
            # 简单AI：随机选择
            unknown_players = [p for p in players if p.alive and p.id != 0]
            return random.choice(unknown_players).id if unknown_players else 0

        # 预言家查验策略
        check_candidates = [p for p in players if p.alive and p.id != 0]

        if not check_candidates:
            return 0

        # 基于发言活跃度、行为可疑度等因素排序
        priority_targets = []
        for target in check_candidates:
            # 简化版：优先查验发言活跃或行为可疑的人
            priority = random.random()  # 这里可以用更复杂的逻辑
            priority_targets.append((target.id, target.name, priority))

        # 按优先级排序
        priority_targets.sort(key=lambda x: x[2], reverse=True)

        target_list = []
        for tid, name, priority in priority_targets:
            target_list.append(f"{tid}. {name} (可疑度: {priority:.2f})")

        prompt = f"""作为预言家，选择今晚要查验的目标。

查验策略：
1. 优先查验发言最活跃的人（可能是狼人带节奏）
2. 查验发言矛盾的人（可能在撒谎）
3. 查验很少发言的人（可能在隐藏身份）

可查验目标：
{chr(10).join(target_list)}

请只回复目标玩家的数字ID，不要其他内容。"""

        response = await client.generate_response(prompt, "SEER", max_tokens=10)

        try:
            return int(response.strip())
        except (ValueError, AttributeError):
            # 备用逻辑：选择优先级最高的目标
            return priority_targets[0][0] if priority_targets else 0

    async def generate_vote_target(self, client: BaseAIClient, players: List[Player], game_state: GameState) -> int:
        """生成预言家投票目标"""
        # 预言家投票逻辑
        votable_players = [p for p in players if p.alive and p.id != 0]
        if not votable_players:
            return 0

        target_list = []
        for target in votable_players:
            target_list.append(f"{target.id}. {target.name}")

        prompt = f"""作为预言家，选择今天的投票目标。

投票策略：投票给查杀的狼人，带领好人阵营

可投票目标：
{chr(10).join(target_list)}

请只回复目标玩家的数字ID，不要其他内容。"""

        response = await client.generate_response(prompt, "SEER", max_tokens=10)

        try:
            return int(response.strip())
        except (ValueError, AttributeError):
            return random.choice(votable_players).id

    async def generate_speech(self, client: BaseAIClient, players: List[Player], game_state: GameState) -> str:
        """生成预言家发言"""
        prompt = f"""你是玩家0（预言家），现在是第{game_state.current_round}轮的{game_state.phase.value}阶段。

请根据你的预言家角色和当前局势，发表一段有策略性的发言（30-80字）：
- 要体现预言家的分析能力
- 可以公布查验结果（如果有）
- 带领好人阵营找到狼人
- 建立威信和信任

只说发言内容，不要其他解释。"""

        return await client.generate_response(prompt, "SEER", max_tokens=100)


class WitchProcessor(BaseRoleProcessor):
    """女巫AI处理器"""

    def get_system_prompt(self) -> str:
        return """你是好人阵营的女巫，拥有一瓶解药和一瓶毒药。

关键策略：
- 谨慎使用解药，第一晚通常救人
- 毒药要用在确定是狼人的目标上
- 不要暴露女巫身份，避免成为狼人目标
- 观察夜晚被杀的人来判断是否使用解药
- 配合真预言家的行动"""

    async def generate_kill_target(self, client: BaseAIClient, players: List[Player], game_state: GameState, current_player_id: int = 0) -> int:
        """女巫的毒杀能力"""
        # 这里需要传入更多上下文，比如是否使用了毒药
        return 0

    async def generate_check_target(self, client: BaseAIClient, players: List[Player], game_state: GameState) -> int:
        """女巫没有查验能力"""
        return 0

    async def generate_vote_target(self, client: BaseAIClient, players: List[Player], game_state: GameState) -> int:
        """生成女巫投票目标"""
        votable_players = [p for p in players if p.alive and p.id != 0]
        if not votable_players:
            return 0

        prompt = f"""作为女巫，选择今天的投票目标。

投票策略：相信真预言家，投票给可疑的狼人

可投票目标：
{chr(10).join([f"{p.id}. {p.name}" for p in votable_players])}

请只回复目标玩家的数字ID，不要其他内容。"""

        response = await client.generate_response(prompt, "WITCH", max_tokens=10)

        try:
            return int(response.strip())
        except (ValueError, AttributeError):
            return random.choice(votable_players).id

    async def generate_speech(self, client: BaseAIClient, players: List[Player], game_state: GameState) -> str:
        """生成女巫发言"""
        prompt = f"""你是玩家0（女巫），现在是第{game_state.current_round}轮的{game_state.phase.value}阶段。

请根据你的女巫角色和当前局势，发表一段有策略性的发言（30-80字）：
- 要谨慎，不要暴露身份
- 可以暗示自己有特殊能力
- 配合好人阵营的分析
- 避免成为狼人的目标

只说发言内容，不要其他解释。"""

        return await client.generate_response(prompt, "WITCH", max_tokens=100)


class HunterProcessor(BaseRoleProcessor):
    """猎人AI处理器"""

    def get_system_prompt(self) -> str:
        return """你是好人阵营的猎人，死亡时可以带走一名玩家。

关键策略：
- 发言要有威慑作用
- 可以暴露身份来震慑狼人
- 死亡时要确保带走真正的狼人
- 保护好人阵营的重要角色
- 不要被狼人误导"""

    async def generate_kill_target(self, client: BaseAIClient, players: List[Player], game_state: GameState, current_player_id: int = 0) -> int:
        """猎人在死亡时的开枪能力，这里不处理"""
        return 0

    async def generate_check_target(self, client: BaseAIClient, players: List[Player], game_state: GameState) -> int:
        """猎人没有查验能力"""
        return 0

    async def generate_vote_target(self, client: BaseAIClient, players: List[Player], game_state: GameState) -> int:
        """生成猎人投票目标"""
        votable_players = [p for p in players if p.alive and p.id != 0]
        if not votable_players:
            return 0

        prompt = f"""作为猎人，选择今天的投票目标。

投票策略：投票给最可疑的狼人，准备开枪

可投票目标：
{chr(10).join([f"{p.id}. {p.name}" for p in votable_players])}

请只回复目标玩家的数字ID，不要其他内容。"""

        response = await client.generate_response(prompt, "HUNTER", max_tokens=10)

        try:
            return int(response.strip())
        except (ValueError, AttributeError):
            return random.choice(votable_players).id

    async def generate_speech(self, client: BaseAIClient, players: List[Player], game_state: GameState) -> str:
        """生成猎人发言"""
        prompt = f"""你是玩家0（猎人），现在是第{game_state.current_round}轮的{game_state.phase.value}阶段。

请根据你的猎人角色和当前局势，发表一段有策略性的发言（30-80字）：
- 可以适当暴露身份来震慑狼人
- 发言要有威慑作用
- 分析谁是可疑的狼人
- 保护好人阵营

只说发言内容，不要其他解释。"""

        return await client.generate_response(prompt, "HUNTER", max_tokens=100)


class VillagerProcessor(BaseRoleProcessor):
    """村民AI处理器"""

    def get_system_prompt(self) -> str:
        return """你是好人阵营的普通村民，没有特殊技能。

关键策略：
- 仔细分析每个人的发言
- 识别发言中的矛盾
- 相信真预言家的查验结果
- 跟随好人阵营投票
- 避免被狼人误导"""

    async def generate_kill_target(self, client: BaseAIClient, players: List[Player], game_state: GameState, current_player_id: int = 0) -> int:
        """村民没有击杀能力"""
        return 0

    async def generate_check_target(self, client: BaseAIClient, players: List[Player], game_state: GameState) -> int:
        """村民没有查验能力"""
        return 0

    async def generate_vote_target(self, client: BaseAIClient, players: List[Player], game_state: GameState) -> int:
        """生成村民投票目标"""
        votable_players = [p for p in players if p.alive and p.id != 0]
        if not votable_players:
            return 0

        prompt = f"""作为村民，选择今天的投票目标。

投票策略：跟随真预言家，投票给最可疑的人

可投票目标：
{chr(10).join([f"{p.id}. {p.name}" for p in votable_players])}

请只回复目标玩家的数字ID，不要其他内容。"""

        response = await client.generate_response(prompt, "VILLAGER", max_tokens=10)

        try:
            return int(response.strip())
        except (ValueError, AttributeError):
            return random.choice(votable_players).id

    async def generate_speech(self, client: BaseAIClient, players: List[Player], game_state: GameState) -> str:
        """生成村民发言"""
        prompt = f"""你是玩家0（村民），现在是第{game_state.current_round}轮的{game_state.phase.value}阶段。

请根据你的村民角色和当前局势，发表一段有策略性的发言（30-80字）：
- 体现村民的观察和分析
- 指出发言中的可疑之处
- 支持好人阵营的判断
- 逻辑清晰，理性分析

只说发言内容，不要其他解释。"""

        return await client.generate_response(prompt, "VILLAGER", max_tokens=100)