"""
狼人杀游戏引擎
负责协调游戏流程、处理游戏阶段和玩家交互
"""

import asyncio
from typing import Dict, List, Optional, Any
from models import (
    Player, RoleType, PhaseType, GameState, ActionRecord,
    NightActions, ActionType, CampType
)
from role_assigner import RoleAssigner
from game_state_manager import GameStateManager
from ai_player import AIPlayer
from ai_client import AIClientManager
from openai_config import OpenAIClientManager


class GameEngine:
    """狼人杀游戏引擎"""

    def __init__(self, enable_ai_mode: bool = True, spectator_mode: bool = False):
        self.enable_ai_mode = enable_ai_mode
        self.spectator_mode = spectator_mode  # 观战模式：所有玩家都是AI
        self.players: List[Player] = []
        self.game_state = GameState()
        self.state_manager = GameStateManager()
        self.ai_players: Dict[int, AIPlayer] = {}
        self.openai_client: Optional[AIClientManager] = None

        # 游戏配置
        self.num_players = 9
        self.human_player_id = None  # 将在create_players中随机分配

    async def initialize_game(self) -> bool:
        """初始化游戏"""
        try:
            print("\n" + "=" * 60)
            print("  狼人杀游戏初始化")
            print("=" * 60)

            # 1. 创建玩家
            self.players, self.human_player_id = RoleAssigner.create_players(self.num_players, self.spectator_mode)

            # 2. 分配角色
            self.players = RoleAssigner.assign_roles(self.players)
            RoleAssigner.show_role_distribution(self.players)

            # 3. 初始化游戏状态
            self.game_state = GameState()
            self.game_state.alive_players = [p.id for p in self.players]

            # 4. 初始化AI玩家
            if self.enable_ai_mode:
                await self._initialize_ai_players()

            # 5. 初始化OpenAI客户端
            if self.enable_ai_mode:
                try:
                    self.openai_client = OpenAIClientManager()
                    await self.openai_client.initialize()
                    print("[系统] AI客户端初始化成功")
                except Exception as e:
                    print(f"[系统] AI客户端初始化失败: {e}")
                    print("[错误] 无法启动AI模式，游戏退出")
                    raise SystemExit("OpenAI客户端初始化失败，无法启动AI模式")

            print("[系统] 游戏初始化完成")
            return True

        except Exception as e:
            print(f"[错误] 游戏初始化失败: {e}")
            return False

    async def _initialize_ai_players(self):
        """初始化AI玩家"""
        for player in self.players:
            if player.is_ai:
                self.ai_players[player.id] = AIPlayer(
                    ai_id=player.id,
                    ai_name=player.name,
                    ai_role=player.role
                )
        print(f"[系统] 创建了 {len(self.ai_players)} 个AI玩家")

    async def run_game_loop(self) -> Optional[CampType]:
        """运行主游戏循环"""
        print("\n" + "=" * 60)
        print("  游戏开始！")
        print("=" * 60)

        while not self.game_state.game_over:
            # 检查胜利条件
            winner = self.game_state.check_winner(self.players)
            if winner:
                self.game_state.winner = winner
                self.game_state.game_over = True
                break

            # 夜晚阶段
            await self._process_night_phase()

            # 检查胜利条件
            winner = self.game_state.check_winner(self.players)
            if winner:
                self.game_state.winner = winner
                self.game_state.game_over = True
                break

            # 白天阶段
            await self._process_day_phase()

            # 投票阶段
            await self._process_vote_phase()

            # 进入下一轮
            self.game_state.current_round += 1

        # 游戏结束，显示结果
        self._display_game_result()
        return self.game_state.winner

    async def _process_night_phase(self):
        """处理夜晚阶段"""
        print(f"\n🌙 第{self.game_state.current_round}夜降临...")

        self.game_state.phase = PhaseType.NIGHT
        night_actions = NightActions()

        # 1. 狼人行动
        await self._process_werewolf_action(night_actions)

        # 2. 预言家查验
        await self._process_seer_action(night_actions)

        # 3. 女巫行动
        await self._process_witch_action(night_actions)

        # 保存夜晚行动
        self.game_state.night_actions = night_actions

        # 处理夜晚结果
        await self._resolve_night_actions(night_actions)

    async def _process_werewolf_action(self, night_actions: NightActions):
        """处理狼人杀人"""
        werewolves = [p for p in self.players if p.alive and p.role == RoleType.WEREWOLF]
        if not werewolves:
            return

        # 简单的狼人AI：随机选择一个非狼人玩家
        potential_targets = [p for p in self.players if p.alive and p.role != RoleType.WEREWOLF]
        if not potential_targets:
            return

        target_id = None
        if self.enable_ai_mode and werewolves[0].id in self.ai_players:
            # 使用AI决策
            try:
                ai_player = self.ai_players[werewolves[0].id]
                target_id = await ai_player.choose_werewolf_target(self.players, self.game_state, self.spectator_mode)
                if target_id is None:
                    # AI返回None，使用随机选择
                    import random
                    target = random.choice(potential_targets)
                    target_id = target.id
            except Exception as e:
                print(f"[系统] AI狼人决策出错: {e}，使用随机选择")
                import random
                target = random.choice(potential_targets)
                target_id = target.id
        else:
            # 随机选择
            import random
            target = random.choice(potential_targets)
            target_id = target.id

        # 确保target_id有效
        if target_id is not None:
            night_actions.werewolf_kill = target_id
            print(f"[狼人] 狼人选择击杀玩家 {target_id}")

    async def _process_seer_action(self, night_actions: NightActions):
        """处理预言家查验"""
        seers = [p for p in self.players if p.alive and p.role == RoleType.SEER]
        if not seers:
            return

        seer = seers[0]
        # 查验一个未知的玩家
        unknown_players = [p for p in self.players if p.alive and p.id != seer.id]
        if not unknown_players:
            return

        target_id = None
        if self.enable_ai_mode and seer.id in self.ai_players:
            # 使用AI决策
            try:
                ai_player = self.ai_players[seer.id]
                target_id = await ai_player.choose_seer_target(self.players, self.game_state, self.spectator_mode)
                if target_id is None:
                    # AI返回None，使用随机选择
                    import random
                    target = random.choice(unknown_players)
                    target_id = target.id
            except Exception as e:
                print(f"[系统] AI预言家决策出错: {e}，使用随机选择")
                import random
                target = random.choice(unknown_players)
                target_id = target.id
        else:
            # 简单AI：随机选择
            import random
            target = random.choice(unknown_players)
            target_id = target.id

        # 确保target_id有效
        if target_id is not None:
            night_actions.seer_check = target_id

            # 记录查验结果
            target = next((p for p in self.players if p.id == target_id), None)
            if target:
                result = "狼人" if target.role == RoleType.WEREWOLF else "好人"
                self.game_state.seer_results[target_id] = result
                print(f"[预言家] 预言家查验了玩家 {target_id}，结果是{result}")

    async def _process_witch_action(self, night_actions: NightActions):
        """处理女巫行动"""
        witches = [p for p in self.players if p.alive and p.role == RoleType.WITCH]
        if not witches:
            return

        witch = witches[0]

        # 检查女巫是否有药水可用
        can_save = witch.has_antidote and night_actions.werewolf_kill is not None
        can_poison = witch.has_poison

        if self.enable_ai_mode and witch.id in self.ai_players:
            # 使用AI决策
            ai_player = self.ai_players[witch.id]
            witch_action = await ai_player.choose_witch_action(
                self.players, self.game_state, night_actions.werewolf_kill, can_save, can_poison, self.spectator_mode
            )

            # 使用解药
            if witch_action.get("save") and can_save:
                night_actions.witch_save = night_actions.werewolf_kill
                self.game_state.witch_saved.append(night_actions.werewolf_kill)
                witch.has_antidote = False  # 解药已使用
                witch.used_antidote_night = self.game_state.current_round
                print(f"[女巫] 女巫使用解药救了玩家 {night_actions.werewolf_kill}")

            # 使用毒药
            elif witch_action.get("poison") and can_poison:
                target_id = witch_action["poison"]
                night_actions.witch_poison = target_id
                self.game_state.witch_poisoned.append(target_id)
                witch.has_poison = False  # 毒药已使用
                witch.used_poison_night = self.game_state.current_round
                print(f"[女巫] 女巫使用毒药毒死了玩家 {target_id}")
        else:
            # 简单AI逻辑：第一晚救人
            if self.game_state.current_round == 1 and can_save and night_actions.werewolf_kill:
                night_actions.witch_save = night_actions.werewolf_kill
                self.game_state.witch_saved.append(night_actions.werewolf_kill)
                witch.has_antidote = False
                witch.used_antidote_night = 1
                print(f"[女巫] 女巫第一晚使用解药救了玩家 {night_actions.werewolf_kill}")

    async def _resolve_night_actions(self, night_actions: NightActions):
        """处理夜晚行动结果"""
        deaths = []

        # 狼人击杀 - 只有当女巫选择救人时才阻止死亡
        if night_actions.werewolf_kill and night_actions.werewolf_kill != night_actions.witch_save:
            deaths.append(night_actions.werewolf_kill)

        # 女巫毒杀
        if night_actions.witch_poison:
            deaths.append(night_actions.witch_poison)

        # 处理死亡
        for player_id in deaths:
            player = next(p for p in self.players if p.id == player_id)
            player.alive = False
            self.game_state.alive_players.remove(player_id)
            self.game_state.dead_players.append(player_id)

            # 记录行动
            action = ActionRecord(
                action_type=ActionType.KILL,
                player_id=0,  # 系统行动
                target_id=player_id,
                phase="夜晚",
                round=self.game_state.current_round
            )
            self.game_state.history.append(action)

        # 公布夜晚结果
        if deaths:
            print(f"\n☠️ 昨晚死亡的玩家：{', '.join(str(d) for d in deaths)}")
        else:
            print("\n✅ 昨晚是个平安夜")

    async def _process_day_phase(self):
        """处理白天讨论阶段"""
        print(f"\n☀️ 第{self.game_state.current_round}天 - 发言讨论")

        self.game_state.phase = PhaseType.DAY

        # 存活玩家发言
        alive_players = [p for p in self.players if p.alive]
        for player in alive_players:
            if player.is_ai and self.enable_ai_mode and player.id in self.ai_players:
                ai_player = self.ai_players[player.id]
                speech = await ai_player.generate_speech(self.players, self.game_state, self.spectator_mode)
                print(f"\n[{player.name}] {speech}")
            else:
                # 简单的默认发言
                if not self.spectator_mode and player.id == self.human_player_id:
                    # 人类玩家输入（非观战模式）
                    print(f"\n轮到 {player.name} 发言：")
                    speech = input("请输入你的发言内容：")
                else:
                    # AI简单发言
                    speech = f"我是{player.name}，我认为我们应该仔细分析昨晚的情况。"
                    print(f"\n[{player.name}] {speech}")

    async def _process_vote_phase(self):
        """处理投票阶段"""
        print(f"\n⚖️ 第{self.game_state.current_round}天 - 投票")

        self.game_state.phase = PhaseType.VOTE
        votes: Dict[int, int] = {}

        # 存活玩家投票
        alive_players = [p for p in self.players if p.alive]
        for voter in alive_players:
            if voter.is_ai and self.enable_ai_mode and voter.id in self.ai_players:
                # AI投票
                ai_player = self.ai_players[voter.id]
                target_id = await ai_player.choose_vote_target(self.players, self.game_state, self.spectator_mode)
                votes[voter.id] = target_id
                print(f"[投票] {voter.name} 投票给玩家 {target_id}")
            else:
                # 人类投票或简单AI投票
                if not self.spectator_mode and voter.id == self.human_player_id:
                    print(f"\n{voter.name}，请投票：")
                    for p in alive_players:
                        if p.id != voter.id:
                            print(f"  {p.id}. {p.name}")

                    while True:
                        try:
                            vote_input = input("选择投票目标ID：")
                            target_id = int(vote_input)
                            if target_id in [p.id for p in alive_players if p.id != voter.id]:
                                votes[voter.id] = target_id
                                print(f"[投票] {voter.name} 投票给玩家 {target_id}")
                                break
                            else:
                                print("无效的目标ID，请重新选择")
                        except ValueError:
                            print("请输入有效的数字")
                else:
                    # 简单AI投票
                    import random
                    targets = [p.id for p in alive_players if p.id != voter.id]
                    target_id = random.choice(targets)
                    votes[voter.id] = target_id
                    print(f"[投票] {voter.name} 投票给玩家 {target_id}")

        # 统计投票结果
        vote_counts: Dict[int, int] = {}
        for target_id in votes.values():
            vote_counts[target_id] = vote_counts.get(target_id, 0) + 1

        if vote_counts:
            # 找出最高票
            max_votes = max(vote_counts.values())
            eliminated_players = [pid for pid, count in vote_counts.items() if count == max_votes]

            if len(eliminated_players) == 1:
                # 唯一最高票，处决
                eliminated_id = eliminated_players[0]
                player = next(p for p in self.players if p.id == eliminated_id)
                player.alive = False
                self.game_state.alive_players.remove(eliminated_id)
                self.game_state.dead_players.append(eliminated_id)
                self.game_state.voted_player = eliminated_id

                print(f"\n💀 玩家 {eliminated_id} ({player.name}) 被投票处决")
                print(f"   身份：{player.role.value}")

                # 记录行动
                action = ActionRecord(
                    action_type=ActionType.VOTE,
                    player_id=0,  # 系统行动
                    target_id=eliminated_id,
                    phase="投票",
                    round=self.game_state.current_round
                )
                self.game_state.history.append(action)

                # 猎人技能触发
                if player.role == RoleType.HUNTER:
                    await self._process_hunter_shoot(player)

            else:
                print("\n🤝 投票平局，无人被处决")

    async def _process_hunter_shoot(self, hunter: Player):
        """处理猎人开枪"""
        print(f"\n🔫 猎人 {hunter.name} 发动技能，可以带走一个人")

        # 猎人选择目标
        if not self.spectator_mode and hunter.id == self.human_player_id:
            # 人类猎人（非观战模式）
            alive_players = [p for p in self.players if p.alive]
            print("选择要带走的玩家：")
            for p in alive_players:
                print(f"  {p.id}. {p.name}")

            while True:
                try:
                    target_input = input("选择目标ID：")
                    target_id = int(target_input)
                    if target_id in [p.id for p in alive_players]:
                        target = next(p for p in self.players if p.id == target_id)
                        target.alive = False
                        self.game_state.alive_players.remove(target_id)
                        self.game_state.dead_players.append(target_id)
                        print(f"🔫 猎人带走了玩家 {target_id} ({target.name})")
                        break
                    else:
                        print("无效的目标ID")
                except ValueError:
                    print("请输入有效数字")
        else:
            # AI猎人
            if self.enable_ai_mode and hunter.id in self.ai_players:
                ai_player = self.ai_players[hunter.id]
                target_id = await ai_player.choose_hunter_target(self.players, self.game_state, self.spectator_mode)
            else:
                # 简单AI：随机选择
                import random
                alive_players = [p for p in self.players if p.alive]
                target = random.choice(alive_players)
                target_id = target.id

            target = next(p for p in self.players if p.id == target_id)
            target.alive = False
            self.game_state.alive_players.remove(target_id)
            self.game_state.dead_players.append(target_id)
            print(f"🔫 猎人带走了玩家 {target_id} ({target.name})")

    def _display_game_result(self):
        """显示游戏结果"""
        print("\n" + "=" * 60)
        print("  游戏结束！")
        print("=" * 60)

        if self.game_state.winner == CampType.WEREWOLF:
            print("🐺 狼人阵营获胜！")
        elif self.game_state.winner == CampType.VILLAGER:
            print("👥 好人阵营获胜！")
        else:
            print("🤝 游戏平局！")

        print(f"\n游戏进行了 {self.game_state.current_round} 轮")

        # 显示所有玩家身份
        print("\n玩家身份揭晓：")
        for player in self.players:
            status = "存活" if player.alive else "死亡"
            print(f"  玩家 {player.id} ({player.name}): {player.role.value} - {status}")

        print("\n感谢游戏！")

    def get_game_status(self) -> Dict[str, Any]:
        """获取游戏状态"""
        return {
            "current_round": self.game_state.current_round,
            "phase": self.game_state.phase.value,
            "alive_players": len([p for p in self.players if p.alive]),
            "werewolves_alive": len([p for p in self.players if p.alive and p.role == RoleType.WEREWOLF]),
            "game_over": self.game_state.game_over,
            "winner": self.game_state.winner.value if self.game_state.winner else None
        }


if __name__ == "__main__":
    async def main():
        engine = GameEngine(enable_ai_mode=True)
        if await engine.initialize_game():
            winner = await engine.run_game_loop()
            print(f"\n游戏结束，获胜方：{winner}")
        else:
            print("游戏初始化失败")

    asyncio.run(main())