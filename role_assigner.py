"""
角色分配系统
"""
import random
from typing import List, Dict
from models import Player, RoleType


class RoleAssigner:
    """角色分配器"""
    
    @staticmethod
    def create_players(num_players: int = 9, spectator_mode: bool = False) -> tuple[List[Player], int]:
        """创建玩家"""
        players = []

        # 随机选择人类玩家的位置（如果不是观战模式）
        human_player_id = None
        if not spectator_mode:
            human_player_id = random.randint(0, num_players - 1)

        for i in range(num_players):
            name = f"玩家{i}"
            # 观战模式下所有玩家都是AI，否则随机选择一个玩家是真人
            is_ai = spectator_mode or i != human_player_id
            player = Player(
                id=i,
                name=name,
                is_ai=is_ai
            )
            players.append(player)

        return players, human_player_id
    
    @staticmethod
    def assign_roles(players: List[Player]) -> List[Player]:
        """随机分配角色给玩家"""
        
        # 角色配置：1个预言家，1个女巫，1个猎人，3个村民，3个狼人
        role_distribution = {
            RoleType.SEER: 1,
            RoleType.WITCH: 1,
            RoleType.HUNTER: 1,
            RoleType.VILLAGER: 3,
            RoleType.WEREWOLF: 3
        }
        
        # 创建角色列表
        role_list: List[RoleType] = []
        for role, count in role_distribution.items():
            role_list.extend([role] * count)
        
        print("\\n  === 游戏角色分配 ===")
        print(f"  共{len(players)}名玩家参与")
        print(f"  阵营：{len([r for r in role_list if r == RoleType.WEREWOLF])}个狼人 对阵 {len(players) - len([r for r in role_list if r == RoleType.WEREWOLF])}个好人\\n")
        
        # 随机分配角色给玩家
        random.shuffle(role_list)
        
        updated_players: List[Player] = []
        
        for i, player in enumerate(players):
            assigned_role = role_list[i]
            
            player.role = assigned_role
            
            if not player.is_ai:
                print(f"  【系统】您的角色是：{player.role.value}\\n")
            else:
                pass  # AI玩家不显示其身份（只显示给AI玩家自己）
            
            updated_players.append(player)
        
        return updated_players
    
    @staticmethod
    def show_role_distribution(players: List[Player]):
        """显示角色分布"""
        role_count: Dict[RoleType, int] = {}
        
        for player in players:
            if player.role:
                if player.role not in role_count:
                    role_count[player.role] = 0
                role_count[player.role] += 1
        
        print("\\n[ 游戏配置 ]")
        print("-" * 30)
        print(f"总玩家数量：{len(players)}")
        for role, count in role_count.items():
            print(f"{role.value}: {count}个")
        
        print("\\n[ 各玩家ID ]")
        for player in players:
            if player.role == RoleType.SEER or player.role == RoleType.WITCH or player.role == RoleType.HUNTER or player.role == RoleType.WEREWOLF or player.role == RoleType.VILLAGER:
                print(f"ID: {player.id} | 名称: {player.name} | 身份: {player.role.value}")
        print("")
        
        return role_count
    
    @staticmethod
    def get_player_role_status(player_id: int) -> Dict[str, any]:
        """获取玩家身份状态"""
        pass


# 示例用法
if __name__ == "__main__":
    print("创建玩家并分配角色：")
    players, human_id = RoleAssigner.create_players()
    print(f"\\n创建了{len(players)}名玩家，人类玩家ID: {human_id}")
    
    # 输出玩家信息
    for player in players:
        print(player)
    
    # 随机分配角色
    players = RoleAssigner.assign_roles(players)
    
    # 显示角色分布
    role_count = RoleAssigner.show_role_distribution(players)
    
    print("\\n各玩家ID和角色：")
    for player in players:
        if player.is_ai:
            print(f"  ID {player.id}: {player.name}")
        else:
            print(f"  ID {player.id}: {player.name} - {player.role.value}")
    
    print("\\n=== 角色分配完成 ===")
