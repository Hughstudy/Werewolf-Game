"""
AI客户端包
重构后的AI决策系统，按角色分离逻辑
"""

from .base import AIClientManager, get_ai_client, OpenAIConfig
from .role_processors import (
    BaseRoleProcessor,
    WerewolfProcessor,
    SeerProcessor,
    WitchProcessor,
    HunterProcessor,
    VillagerProcessor
)

__all__ = [
    'AIClientManager',
    'get_ai_client',
    'OpenAIConfig',
    'BaseRoleProcessor',
    'WerewolfProcessor',
    'SeerProcessor',
    'WitchProcessor',
    'HunterProcessor',
    'VillagerProcessor'
]