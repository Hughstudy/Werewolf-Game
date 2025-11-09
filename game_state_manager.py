"""
游戏状态管理器 - 清理版本
负责管理游戏状态、记录历史和检查胜利条件
"""

from typing import Dict, List, Optional, Any
from models import (
    Player, RoleType, PhaseType, GameState, ActionRecord,
    NightActions, ActionType, CampType
)
from role_assigner import RoleAssigner


class GameStateManager:
    """游戏状态管理器"""

    def __init__(self):
        self.players: List[Player] = []
        self.game_state: GameState = GameState()
        self.night_actions: NightActions = NightActions()

    def initialize_game(self) -> None:
        """初始化游戏"""
        print("\n" + "=" * 60)
        print("  开始游戏！")
        print("=" * 60 + "\n")

        # 创建并分配玩家
        self.players, _ = RoleAssigner.create_players()
        self.players = RoleAssigner.assign_roles(self.players)

        # 初始化游戏状态
        self.reset_game_state()

        # 显示开局信息
        print(f"\n🏮 本局共有{len(self.players)}名玩家")
        print(f"🏮 游戏阶段：第{self.game_state.current_round}个夜晚")

        werewolf_count = self.count_roles(RoleType.WEREWOLF)
        good_players_count = self.count_roles(RoleType.SEER) + self.count_roles(RoleType.WITCH) + self.count_roles(RoleType.HUNTER) + self.count_roles(RoleType.VILLAGER)
        print(f"🏮 目标：{good_players_count}个好人需要找到{werewolf_count}个狼人！\n")

    def reset_game_state(self) -> None:
        """重置游戏状态，用于初始化游戏"""
        self.game_state = GameState()
        self.game_state.alive_players = [p.id for p in self.players]
        self.game_state.phase = PhaseType.NIGHT
        self.night_actions = NightActions()

    def count_roles(self, role_type: RoleType) -> int:
        """统计特定角色的数量"""
        return len([p for p in self.players if p.role == role_type])

    def get_alive_players(self) -> List[Player]:
        """获取存活的玩家列表"""
        return [p for p in self.players if p.alive]

    def get_alive_werewolves(self) -> List[Player]:
        """获取存活的狼人列表"""
        return [p for p in self.players if p.alive and p.role == RoleType.WEREWOLF]

    def get_role_distribution(self) -> Dict[RoleType, int]:
        """获取角色分布统计"""
        distribution = {}
        for player in self.players:
            if player.role:
                distribution[player.role] = distribution.get(player.role, 0) + 1
        return distribution

    def check_victory_conditions(self) -> Optional[CampType]:
        """检查胜利条件"""
        # 检查狼人是否全部死亡
        alive_werewolves = self.get_alive_werewolves()
        if len(alive_werewolves) == 0:
            return CampType.VILLAGER

        # 检查好人是否太少
        alive_players = self.get_alive_players()
        alive_good_count = len([p for p in alive_players if p.role != RoleType.WEREWOLF])

        # 如果好人数量少于等于狼人，狼人获胜
        if alive_good_count <= len(alive_werewolves):
            return CampType.WEREWOLF

        return None

    def process_player_death(self, player_id: int, death_cause: str) -> None:
        """处理玩家死亡"""
        player = next((p for p in self.players if p.id == player_id), None)
        if player and player.alive:
            player.alive = False

            # 更新游戏状态
            if player_id in self.game_state.alive_players:
                self.game_state.alive_players.remove(player_id)
            self.game_state.dead_players.append(player_id)

            # 记录行动
            action_type = ActionType.KILL if death_cause in ["werewolf", "vote", "poison"] else ActionType.SAVE
            action = ActionRecord(
                action_type=action_type,
                player_id=0,  # 系统行动
                target_id=player_id,
                phase=self.game_state.phase.value,
                round=self.game_state.current_round
            )
            self.game_state.history.append(action)

            print(f"\n💀 玩家 {player_id} ({player.name}) 死亡 - 原因：{death_cause}")

    def record_action(self, action_type: ActionType, player_id: int, target_id: Optional[int] = None, additional_info: Optional[Dict] = None):
        """记录游戏行动"""
        action = ActionRecord(
            action_type=action_type,
            player_id=player_id,
            target_id=target_id,
            phase=self.game_state.phase.value,
            round=self.game_state.current_round
        )
        self.game_state.history.append(action)

        if additional_info:
            # 可以在这里添加额外的信息记录
            pass

    def get_game_summary(self) -> Dict[str, Any]:
        """获取游戏摘要信息"""
        alive_players = self.get_alive_players()
        alive_werewolves = self.get_alive_werewolves()

        role_distribution = self.get_role_distribution()

        return {
            "current_round": self.game_state.current_round,
            "current_phase": self.game_state.phase.value,
            "total_players": len(self.players),
            "alive_players_count": len(alive_players),
            "alive_werewolves_count": len(alive_werewolves),
            "alive_good_count": len(alive_players) - len(alive_werewolves),
            "dead_players_count": len(self.game_state.dead_players),
            "role_distribution": {
                role.value: count for role, count in role_distribution.items()
            },
            "game_over": self.game_state.game_over,
            "winner": self.game_state.winner.value if self.game_state.winner else None
        }

    def get_player_status(self, player_id: int) -> Dict[str, Any]:
        """获取特定玩家的状态"""
        player = next((p for p in self.players if p.id == player_id), None)
        if not player:
            return {}

        return {
            "id": player.id,
            "name": player.name,
            "role": player.role.value if player.role else None,
            "alive": player.alive,
            "is_ai": player.is_ai,
            "camp": player.camp
        }

    def get_phase_summary(self) -> Dict[str, Any]:
        """获取当前阶段摘要"""
        return {
            "phase": self.game_state.phase.value,
            "round": self.game_state.current_round,
            "alive_players": len(self.get_alive_players()),
            "werewolves_alive": len(self.get_alive_werewolves()),
            "recent_actions": self.game_state.history[-5:] if self.game_state.history else []
        }

    def display_current_status(self):
        """显示当前游戏状态"""
        print(f"\n{'='*50}")
        print(f"第{self.game_state.current_round}轮 - {self.game_state.phase.value}")
        print(f"{'='*50}")

        alive_players = self.get_alive_players()
        print(f"\n存活玩家 ({len(alive_players)}人):")
        for player in alive_players:
            print(f"  {player.id}. {player.name}")

        dead_players = [p for p in self.players if not p.alive]
        if dead_players:
            print(f"\n死亡玩家 ({len(dead_players)}人):")
            for player in dead_players:
                print(f"  {player.id}. {player.name} ({player.role.value})")

    def validate_player_action(self, player_id: int, action_type: str, target_id: Optional[int] = None) -> bool:
        """验证玩家行动是否合法"""
        player = next((p for p in self.players if p.id == player_id), None)
        if not player or not player.alive:
            return False

        # 根据角色和阶段验证行动
        if self.game_state.phase == PhaseType.NIGHT:
            if player.role == RoleType.WEREWOLF and action_type == "kill":
                # 狼人只能杀非狼人
                target = next((p for p in self.players if p.id == target_id), None)
                return target and target.alive and target.role != RoleType.WEREWOLF

            elif player.role == RoleType.SEER and action_type == "check":
                # 预言家不能查验自己
                target = next((p for p in self.players if p.id == target_id), None)
                return target and target.alive and target.id != player_id

            elif player.role == RoleType.WITCH and action_type in ["save", "poison"]:
                # 女巫用药验证
                if action_type == "save":
                    # 只能救当晚被杀的人
                    return target_id == self.night_actions.werewolf_kill and target_id not in self.game_state.witch_saved
                else:  # poison
                    target = next((p for p in self.players if p.id == target_id), None)
                    return target and target.alive

        elif self.game_state.phase == PhaseType.VOTE and action_type == "vote":
            # 投票阶段，所有存活玩家都可以投票
            target = next((p for p in self.players if p.id == target_id), None)
            return target and target.alive and target.id != player_id

        return False

    def get_next_phase(self) -> PhaseType:
        """获取下一个游戏阶段"""
        current_phase_index = list(PhaseType).index(self.game_state.phase)
        next_phase_index = (current_phase_index + 1) % len(list(PhaseType))

        # 如果从投票阶段进入下一轮，回到夜晚
        if self.game_state.phase == PhaseType.VOTE:
            self.game_state.current_round += 1
            return PhaseType.NIGHT

        return list(PhaseType)[next_phase_index]

    def advance_phase(self) -> PhaseType:
        """推进到下一个游戏阶段"""
        next_phase = self.get_next_phase()
        self.game_state.phase = next_phase

        # 重置夜晚行动记录
        if next_phase == PhaseType.NIGHT:
            self.night_actions = NightActions()

        return next_phase

    def end_game(self, winner: CampType):
        """结束游戏"""
        self.game_state.game_over = True
        self.game_state.winner = winner

    def export_game_history(self) -> List[Dict[str, Any]]:
        """导出游戏历史记录"""
        return [
            {
                "round": action.round,
                "phase": action.phase,
                "action": action.action_type.value,
                "player_id": action.player_id,
                "target_id": action.target_id,
                "timestamp": action.timestamp.isoformat()
            }
            for action in self.game_state.history
        ]


if __name__ == "__main__":
    # 测试游戏状态管理器
    manager = GameStateManager()

    print("测试游戏状态管理器...")

    # 这里可以添加测试代码
    print("游戏状态管理器测试完成")