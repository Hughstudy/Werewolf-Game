"""
狼人杀游戏主程序 - 清理版本
游戏启动入口和主循环控制
"""

import asyncio
import sys
import os
import logging
from typing import Optional

# 添加当前目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from game_engine import GameEngine  # noqa: E402
from models import CampType  # noqa: E402

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# 设置DEBUG级别只在需要时显示详细信息
logging.getLogger().setLevel(logging.WARNING)  # 默认只显示WARNING及以上级别


class WerewolfGame:
    """狼人杀游戏主类"""

    def __init__(self, enable_ai: bool = True, spectator_mode: bool = False):
        self.engine = GameEngine(enable_ai_mode=enable_ai, spectator_mode=spectator_mode)
        self.game_active = False

    async def start(self):
        """启动游戏"""
        print("\n" + "=" * 70)
        print("  🔥 狼人杀游戏")
        print("=" * 70)

        try:
            # 初始化游戏
            if not await self.engine.initialize_game():
                print("❌ 游戏初始化失败")
                return

            self.game_active = True

            # 显示游戏控制说明
            self._show_game_controls()

            # 开始主游戏循环
            winner = await self.engine.run_game_loop()

            # 游戏结束
            self.game_active = False
            self._show_game_end_message(winner)

        except KeyboardInterrupt:
            print("\n\n⚠️ 游戏被用户中断")
            self.game_active = False
        except Exception as e:
            print(f"\n❌ 游戏运行出错: {e}")
            self.game_active = False

    def _show_game_controls(self):
        """显示游戏控制说明"""
        print("\n" + "=" * 70)
        print("  📋 游戏说明")
        print("=" * 70)
        print("1. 其他玩家都是AI，你需要找出隐藏的狼人")
        print("2. 游戏包含夜晚、白天讨论、投票三个阶段")
        print("3. 你需要根据其他玩家的发言找出狼人")
        print("4. 在投票阶段选择你认为是狼人的玩家")
        print("\n按 Ctrl+C 可以随时退出游戏")
        print("=" * 70)

    def _show_game_end_message(self, winner: Optional[CampType]):
        """显示游戏结束消息"""
        print("\n" + "=" * 70)
        print("  🏁 游戏结束")
        print("=" * 70)

        if winner == CampType.WEREWOLF:
            print("🐺 狼人阵营获胜！")
            print("   狼人成功隐藏身份，击败了好人阵营")
        elif winner == CampType.VILLAGER:
            print("👥 好人阵营获胜！")
            print("   所有狼人都被找出来并消灭了")
        else:
            print("🤝 游戏平局")
            print("   没有明显的获胜方")

        # 显示游戏状态统计
        status = self.engine.get_game_status()
        print("\n📊 游戏统计:")
        print(f"   总轮数: {status['current_round']}")
        print(f"   存活玩家: {status['alive_players']}")
        print(f"   存活狼人: {status['werewolves_alive']}")

        print("\n感谢游玩！")
        print("=" * 70)


def get_user_choice() -> str:
    """获取用户游戏模式选择"""
    print("\n" + "=" * 50)
    print("  🎮 选择游戏模式")
    print("=" * 50)
    print("1. 简单模式 (基础AI，快速游戏)")
    print("2. 完整模式 (智能AI，OpenAI增强)")
    print("3. 观战模式 (纯AI对战，无需参与)")
    print("4. 退出游戏")
    print("=" * 50)

    while True:
        try:
            choice = input("\n请选择模式 (1-4): ").strip()
            if choice in ['1', '2', '3', '4']:
                return choice
            else:
                print("❌ 无效选择，请输入 1-4")
        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            sys.exit(0)


async def main():
    """主函数"""
    print("🐺 欢迎来到狼人杀游戏！")

    while True:
        try:
            choice = get_user_choice()

            if choice == '1':
                # 简单模式
                print("\n🎮 启动简单模式...")
                game = WerewolfGame(enable_ai=False)
                await game.start()

            elif choice == '2':
                # 完整模式
                print("\n🤖 启动完整模式...")
                print("   (需要配置 OpenAI API)")
                game = WerewolfGame(enable_ai=True)
                await game.start()

            elif choice == '3':
                # 观战模式
                print("\n👀 启动观战模式...")
                game = WerewolfGame(enable_ai=True, spectator_mode=True)
                await game.start()

            elif choice == '4':
                # 退出
                print("\n👋 感谢游玩，再见！")
                break

            # 询问是否再来一局
            if choice in ['1', '2', '3']:
                while True:
                    try:
                        replay = input("\n是否再来一局？(y/n): ").strip().lower()
                        if replay in ['y', 'yes', '是']:
                            break
                        elif replay in ['n', 'no', '否']:
                            print("\n👋 再见！")
                            return
                        else:
                            print("请输入 y 或 n")
                    except KeyboardInterrupt:
                        print("\n\n👋 再见！")
                        return

        except KeyboardInterrupt:
            print("\n\n👋 游戏被中断，再见！")
            break
        except Exception as e:
            print(f"\n❌ 发生错误: {e}")
            print("请重新开始游戏...")


if __name__ == "__main__":
    # 运行主程序
    asyncio.run(main())