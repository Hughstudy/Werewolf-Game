"""
AI客户端基础管理
处理OpenAI客户端的初始化和通用功能
"""

import os
import logging
import asyncio
from typing import Dict, Any, Optional, List
from openai import AsyncOpenAI

from models import Player, GameState


class OpenAIConfig:
    """OpenAI配置管理"""

    @staticmethod
    def load_config() -> Dict[str, Any]:
        """加载OpenAI配置"""
        config = {
            "api_key": os.environ.get("SILICON_FLOW_API_KEY"),
            "base_url": os.environ.get("SILICON_FLOW_BASE_URL", "https://api.siliconflow.cn/v1"),
            "models": {
                "WEREWOLF": os.environ.get("OPENAI_MODEL_WEREWOLF", "Qwen/Qwen3-8B"),
                "VILLAGER": os.environ.get("OPENAI_MODEL_VILLAGER", "Qwen/Qwen3-8B"),
                "SEER": os.environ.get("OPENAI_MODEL_SEER", "Qwen/Qwen3-8B"),
                "WITCH": os.environ.get("OPENAI_MODEL_WITCH", "Qwen/Qwen3-8B"),
                "HUNTER": os.environ.get("OPENAI_MODEL_HUNTER", "Qwen/Qwen3-8B")
            }
        }

        if not config["api_key"]:
            print("\n⚠️ 未配置 Silicon Flow API Key")
            print("请设置环境变量 SILICON_FLOW_API_KEY")
            return None

        return config


class BaseAIClient:
    """AI客户端基础类"""

    def __init__(self):
        self.config: Optional[Dict[str, Any]] = None
        self.client: Optional[AsyncOpenAI] = None
        self._initialized = False

    async def initialize(self) -> bool:
        """初始化客户端"""
        try:
            # 加载配置
            self.config = OpenAIConfig.load_config()
            if not self.config:
                return False

            # 创建OpenAI客户端
            self.client = AsyncOpenAI(
                api_key=self.config["api_key"],
                base_url=self.config["base_url"]
            )

            # 测试连接 - 使用一个通用的测试模型
            await self._test_connection()
            self._initialized = True
            logging.debug("✅ AI客户端初始化成功")
            logging.debug(f"   API地址: {self.config['base_url']}")
            logging.debug("   📡 使用 Silicon Flow API")
            logging.debug(f"   🤖 模型配置: {self.config['models']}")
            return True

        except Exception as e:
            print(f"❌ AI客户端初始化失败: {e}")
            return False

    async def _test_connection(self):
        """测试连接"""
        if not self.client:
            return

        try:
            # 使用一个简单的测试请求
            test_model = list(self.config['models'].values())[0]
            response = await self.client.chat.completions.create(
                model=test_model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            logging.debug("API连接测试成功")
        except Exception as e:
            logging.warning(f"API连接测试失败: {e}")
            raise

    async def generate_response(
        self,
        prompt: str,
        role_type: str = "VILLAGER",
        context: Optional[Dict] = None,
        max_tokens: int = 150
    ) -> str:
        """生成AI响应的通用方法"""
        if not self._initialized or not self.client:
            logging.warning("AI客户端未初始化，使用备用响应")
            return self._get_fallback_response(role_type, context)

        try:
            system_prompt = self._get_system_prompt(role_type, context)

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]

            model = self.config["models"].get(role_type, self.config["models"]["VILLAGER"])

            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.7
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logging.warning(f"AI响应生成失败: {e}，使用备用响应")
            return self._get_fallback_response(role_type, context)

    def _get_system_prompt(self, role_type: str, context: Optional[Dict] = None) -> str:
        """获取系统提示词的基础方法"""
        base_prompt = """你正在玩一个高水平的狼人杀游戏。你需要根据你的角色制定策略，发表有逻辑性的发言。
发言要符合角色特点，长度适中（30-80字），要有说服力。注意观察其他玩家的发言模式。"""

        # 这里可以被子类重写以提供更具体的提示词
        return base_prompt

    def _get_fallback_response(self, role_type: str, context: Optional[Dict] = None) -> str:
        """获取备用响应的基础方法"""
        fallback_responses = {
            "WEREWOLF": "我需要仔细观察每个人的发言。",
            "VILLAGER": "我觉得我们应该从发言中找线索。",
            "SEER": "根据我的查验结果，我们需要谨慎投票。",
            "WITCH": "我会谨慎使用我的药水。",
            "HUNTER": "我会仔细分析每个人的发言。"
        }

        return fallback_responses.get(role_type, "我需要更多信息来做出判断。")


class AIClientManager(BaseAIClient):
    """AI客户端管理器 - 主要入口"""

    def __init__(self):
        super().__init__()
        # 在这里可以添加角色特定的处理器
        from .role_processors import WerewolfProcessor, SeerProcessor, WitchProcessor, HunterProcessor, VillagerProcessor

        self.role_processors = {
            "WEREWOLF": WerewolfProcessor(),
            "SEER": SeerProcessor(),
            "WITCH": WitchProcessor(),
            "HUNTER": HunterProcessor(),
            "VILLAGER": VillagerProcessor()
        }

    async def generate_werewolf_target(self, players: List[Player], game_state: GameState, current_player_id: int = 0) -> int:
        """生成狼人击杀目标"""
        return await self.role_processors["WEREWOLF"].generate_kill_target(self, players, game_state, current_player_id)

    async def generate_seer_target(self, players: List[Player], game_state: GameState) -> int:
        """生成预言家查验目标"""
        return await self.role_processors["SEER"].generate_check_target(self, players, game_state)

    async def generate_vote_target(self, players: List[Player], game_state: GameState, role: str) -> int:
        """生成投票目标"""
        return await self.role_processors[role].generate_vote_target(self, players, game_state)

    async def generate_speech(self, players: List[Player], game_state: GameState, role: str) -> str:
        """生成发言内容"""
        return await self.role_processors[role].generate_speech(self, players, game_state)


# 便捷函数
async def get_ai_client() -> AIClientManager:
    """获取AI客户端实例"""
    client = AIClientManager()
    await client.initialize()
    return client
