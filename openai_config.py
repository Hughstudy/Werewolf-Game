"""
OpenAI配置兼容性文件
为了保持向后兼容性，重新导出新的AI客户端结构
"""

from ai_client import AIClientManager, get_ai_client, OpenAIConfig

# 为了向后兼容，保留原始的类名
OpenAIClientManager = AIClientManager

__all__ = ['OpenAIClientManager', 'OpenAIConfig', 'get_ai_client']