"""
游戏核心数据模型
"""

from enum import Enum
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class RoleType(str, Enum):
    """角色类型"""
    WEREWOLF = "狼人"
    VILLAGER = "村民"
    SEER = "预言家"
    WITCH = "女巫"
    HUNTER = "猎人"


class CampType(str, Enum):
    """阵营类型"""
    WEREWOLF = "狼人阵营"
    VILLAGER = "好人阵营"


class PhaseType(str, Enum):
    """游戏阶段"""
    NIGHT = "黑夜"
    DAY = "白天"
    VOTE = "投票"


class ActionType(str, Enum):
    """行动类型"""
    KILL = "杀人"
    CHECK = "查验"
    SAVE = "救人"
    POISON = "毒人"
    SHOOT = "开枪"
    VOTE = "投票"


class Player(BaseModel):
    """玩家模型"""
    id: int = Field(..., description="玩家ID")
    name: str = Field(default="", description="玩家名称")
    role: Optional[RoleType] = Field(default=None, description="角色")
    alive: bool = Field(default=True, description="是否存活")
    is_ai: bool = Field(default=True, description="是否为AI")
    role_revealed: bool = Field(default=False, description="身份是否公开")

    # 女巫专用属性
    has_antidote: bool = Field(default=True, description="是否有解药")
    has_poison: bool = Field(default=True, description="是否有毒药")
    used_antidote_night: Optional[int] = Field(default=None, description="使用解药的夜晚")
    used_poison_night: Optional[int] = Field(default=None, description="使用毒药的夜晚")
    
    def __str__(self) -> str:
        """显示玩家状态"""
        status = "✓" if self.alive else "✗"
        role = self.role.value if self.role else "未知"
        return f"[{self.id}] {self.name} {status} - {role}"
    
    def get_display_info(self) -> str:
        """获取显示信息"""
        return self.__str__()
    
    @property
    def camp(self) -> str:
        """获取玩家阵营"""
        if self.role is None:
            return "未知"
        if self.role == RoleType.WEREWOLF:
            return "狼人阵营"
        return "好人阵营"


class ActionRecord(BaseModel):
    """行动记录"""
    action_type: ActionType
    player_id: int
    target_id: Optional[int] = None
    phase: str
    round: int
    timestamp: datetime = Field(default=datetime.now())
    
    class Config:
        use_enum_values = True


class NightActions(BaseModel):
    """夜晚行动记录"""
    werewolf_kill: Optional[int] = None
    seer_check: Optional[int] = None
    witch_save: Optional[int] = None
    witch_poison: Optional[int] = None
    hunter_shoot: Optional[int] = None


class GameState(BaseModel):
    """游戏状态"""
    current_round: int = 1
    phase: PhaseType = PhaseType.NIGHT
    alive_players: List[int] = []
    dead_players: List[int] = []
    history: List[ActionRecord] = []
    night_actions: Optional[NightActions] = None
    knife_target: Optional[int] = None
    seer_results: Dict[int, str] = {}
    witch_saved: List[int] = []
    witch_poisoned: List[int] = []
    voted_player: Optional[int] = None
    game_over: bool = False
    winner: Optional[CampType] = None
    
    def get_alive_players(self) -> List[int]:
        """获取存活玩家"""
        return [p for p in self.alive_players if p]
    
    def is_player_alive(self, player_id: int) -> bool:
        """检查玩家是否存活"""
        return player_id in self.alive_players
    
    def check_winner(self, players: List[Player]) -> Optional[CampType]:
        """检查获胜阵营"""
        if self.winner:
            return self.winner

        alive_players = [p for p in players if p.alive]
        alive_werewolf_count = sum(1 for p in alive_players if p.role == RoleType.WEREWOLF)

        # 如果没有狼人存活，好人获胜
        if alive_werewolf_count == 0:
            return CampType.VILLAGER

        # 计算存活的好人数（狼人一方外的好人加神职平民）
        alive_good_count = len(alive_players) - alive_werewolf_count

        # 如果好人数量少于等于狼人，狼人获胜
        if alive_good_count <= alive_werewolf_count:
            return CampType.WEREWOLF

        return None
