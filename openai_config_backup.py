"""
OpenAI配置和客户端管理 - Silicon Flow版本
基于Silicon Flow API的AI响应生成
"""

import os
import asyncio
import logging
from typing import Dict, Optional, Any, List
from openai import AsyncOpenAI


class OpenAIConfig:
    """OpenAI配置管理"""

    @staticmethod
    def load_config() -> Dict[str, Any]:
        """加载Silicon Flow配置"""
        # 获取API密钥
        api_key = os.getenv("SILICON_FLOW_API_KEY")
        if not api_key:
            print("\n⚠️ 未配置 Silicon Flow API Key")
            print("请设置环境变量 SILICON_FLOW_API_KEY")
            return {}

        base_url = os.getenv("SILICON_FLOW_BASE_URL", "https://api.siliconflow.cn/v1")

        # Silicon Flow支持的模型配置
        config = {
            "api_key": api_key,
            "base_url": base_url,
            "models": {
                "WEREWOLF": os.getenv("OPENAI_MODEL_WEREWOLF", "Qwen/Qwen3-8B"),
                "VILLAGER": os.getenv("OPENAI_MODEL_VILLAGER", "Qwen/Qwen3-8B"),
                "SEER": os.getenv("OPENAI_MODEL_SEER", "moonshotai/Kimi-K2-Instruct-0905"),  # 高级模型
                "WITCH": os.getenv("OPENAI_MODEL_WITCH", "Qwen/Qwen3-8B"),
                "HUNTER": os.getenv("OPENAI_MODEL_HUNTER", "Qwen/Qwen3-8B")
            },
            "timeout": 30,
            "max_tokens": 500,
            "temperature": 0.7
        }

        return config


class OpenAIClientManager:
    """OpenAI客户端管理器"""

    def __init__(self):
        self.client: Optional[AsyncOpenAI] = None
        self.config: Dict[str, Any] = {}
        self._initialized = False

    async def initialize(self) -> bool:
        """初始化Silicon Flow客户端"""
        try:
            self.config = OpenAIConfig.load_config()
            if not self.config:
                return False

            self.client = AsyncOpenAI(
                api_key=self.config["api_key"],
                base_url=self.config["base_url"],
                timeout=self.config.get("timeout", 30)
            )

            # 测试连接 - 使用一个通用的测试模型
            await self._test_connection()
            self._initialized = True
            logging.debug("✅ Silicon Flow客户端初始化成功")
            logging.debug(f"   API地址: {self.config['base_url']}")
            logging.debug("   📡 使用 Silicon Flow API")
            logging.debug(f"   🤖 模型配置: {self.config['models']}")
            return True

        except Exception as e:
            print(f"❌ Silicon Flow客户端初始化失败: {e}")
            return False

    async def _test_connection(self):
        """测试API连接"""
        try:
            # 使用默认模型测试连接
            await self.client.chat.completions.create(
                model="Qwen/Qwen3-8B",
                messages=[{"role": "user", "content": "测试"}],
                max_tokens=5
            )
            return True
        except Exception as e:
            raise Exception(f"API连接测试失败: {e}")

    async def generate_response(
        self,
        prompt: str,
        role_type: str = "VILLAGER",
        context: Optional[Dict] = None
    ) -> str:
        """生成AI响应"""
        if not self._initialized or not self.client:
            return self._get_fallback_response(role_type, context)

        try:
            model = self.config["models"].get(role_type, "Qwen/Qwen3-8B")

            messages = [
                {
                    "role": "system",
                    "content": self._get_system_prompt(role_type, context)
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]

            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=self.config.get("max_tokens", 500),
                temperature=self.config.get("temperature", 0.7)
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"⚠️ AI响应生成失败: {e}")
            return self._get_fallback_response(role_type, context)

    def _get_system_prompt(self, role_type: str, context: Optional[Dict] = None) -> str:
        """获取角色特定的系统提示词"""
        base_prompt = """你正在玩一个高水平的狼人杀游戏。你需要根据你的角色制定策略，发表有逻辑性的发言。
发言要符合角色特点，长度适中（30-80字），要有说服力。注意观察其他玩家的发言模式。"""

        role_prompts = {
            "WEREWOLF": """你是狼人阵营. 你的策略: 身份隐藏, 假装成村民或神职, 绝不承认自己是狼人; 混淆视听, 制造混乱, 引导好人互相猜疑; 假装站边, 可以假装相信某个"预言家", 或者自己冒充预言家发假金水; 撒谎技巧, 编造合理的推理, 质疑真正的好人; 保护队友, 避免投票给狼同伴, 必要时转移目标; 夜晚统一行动, 和狼队友配合击杀关键角色。

常见话术: "我觉得XX有点可疑, 他的发言很奇怪"; "我是村民, 但我觉得XX可能是预言家"; "这个预言家(假的)的验人逻辑有问题"; "昨晚我可能是被救了, 所以很感激救我的人".""",

            "VILLAGER": """你是村民. 你的策略: 逻辑推理, 通过发言漏洞找出狼人; 谨慎发言, 不要乱跳身份, 避免被狼人针对; 观察细节, 注意谁在带节奏, 谁在保护谁; 质疑可疑者, 对发言矛盾的人提出质疑; 配合神职, 相信真正的预言家, 跟随投票; 避免站错队, 不要轻易相信自称神职的人。

常见话术: "我是村民, XX的发言逻辑有问题"; "XX和XX像是在互保, 可能都是狼"; "我听XX的分析比较有道理"; "建议大家不要急着投票, 先多分析".""",

            "SEER": """你是预言家. 你的策略: 身份跳明, 第一天开始就要报出身份, 建立信任; 每晚查验, 必须查验并公布结果(金水/查杀); 验人逻辑, 解释为什么选择查验某个人; 带领好人, 利用验人结果指导投票; 应对悍跳, 对抗冒充预言家的狼人; 保护自己, 避免被狼人票杀或毒杀。

必须公布的信息: "我是预言家, 昨晚验了XX, 他是金水(好人)"; "我是预言家, 昨晚验了XX, 他是查杀(狼人)"; 解释验人理由: "因为XX的发言可疑, 所以我选择验他".""",

            "WITCH": """你是女巫. 你的策略: 谨慎暴露, 可以适当暗示身份, 但不要跳明; 解药使用, 第一晚大概率救(除非很确定谁被刀); 毒药使用, 确定是狼人时使用, 不要乱毒; 信息管理, 可以透露救了谁的信息获取信任; 配合预言家, 相信真预言家, 毒杀可疑对象; 自保优先, 保命更重要, 不要盲目救人。

可以透露的信息: "我可能是女巫, 昨晚救了一个人"; "我有特殊能力, 知道XX不是好人"; "如果你们确定XX是狼人, 我可以处理他".""",

            "HUNTER": """你是猎人. 你的策略: 威慑作用, 明确身份, 让狼人不敢轻易杀你; 带队能力, 利用威慑力带领好人投票; 开枪逻辑, 确保带走最可疑的人; 身份可信, 可以适度证明自己身份; 保护神职, 优先保护预言家等关键角色; 临死开枪, 即使被票也要确保带走狼人。

标志性发言: "我是猎人, 我的枪会对准狼人"; "如果我是狼人, 我天打雷劈"; "你们票我可以, 但我死前一定会开枪"; "我怀疑XX是狼人, 随时准备带走他"."""
        }

        role_prompt = role_prompts.get(role_type, base_prompt)

        if context:
            context_info = f"""
当前游戏情况:
- 第{context.get('round', 1)}天
- 存活{context.get('alive_players', 9)}人
- 你的身份: {context.get('role', '未知')}
- 当前阶段: {context.get('phase', '白天')}

游戏策略提示:
{self._get_strategy_tips(role_type)}
"""
            return base_prompt + "\n\n" + role_prompt + context_info

        return base_prompt + "\n\n" + role_prompt

    def _get_strategy_tips(self, role_type: str) -> str:
        """获取角色策略提示"""
        strategies = {
            "WEREWOLF": """撒谎技巧: 编造合理的怀疑理由; 质疑好人阵营的团结; 制造好人内部分歧; 保护狼队友, 转移目标; 必要时悍跳神职角色""",

            "VILLAGER": """推理技巧: 找出发言矛盾点; 分析投票行为模式; 识别谁在保护谁; 不要轻信自称神职者; 保持客观理性""",

            "SEER": """验人技巧: 优先验跳神职的人; 注意发言反常的人; 及时公布验人结果; 解释验人理由; 带领好人阵营""",

            "WITCH": """用药技巧: 第一晚尽量救(除非明确知道谁被刀); 毒药要在确定目标时使用; 可以适度透露信息建立信任; 配合预言家的验人结果; 保护自己更重要""",

            "HUNTER": """开枪技巧: 明确身份增加威慑; 观察最可疑的目标; 即使被票也要带走狼人; 优先带走悍跳狼; 相信自己的判断"""
        }
        return strategies.get(role_type, "保持诚实, 逻辑分析")

    def _get_fallback_response(self, role_type: str, context: Optional[Dict] = None) -> str:
        """获取备用响应（当AI不可用时）"""
        fallback_responses = {
            "WEREWOLF": [
                "我觉得我们需要更仔细地分析情况。",
                "我注意到一些人的发言很有问题。",
                "我们应该从投票结果中找线索。"
            ],
            "VILLAGER": [
                "我是个普通村民，希望大家能找出狼人。",
                "我觉得我们应该听听更多人的意见。",
                "我会仔细分析每个人的发言。"
            ],
            "SEER": [
                "我是预言家，我会努力找出狼人。",
                "我的查验结果会帮助大家。",
                "请相信我的判断。"
            ],
            "WITCH": [
                "我是女巫，我会谨慎使用我的能力。",
                "大家有什么想法都可以交流。",
                "我会保护好人阵营。"
            ],
            "HUNTER": [
                "我是猎人，我的枪会对准可疑的人。",
                "希望大家投票要慎重。",
                "我不会让狼人轻易获胜。"
            ]
        }

        import random
        responses = fallback_responses.get(role_type, fallback_responses["VILLAGER"])
        return random.choice(responses)

    async def generate_werewolf_target(self, players: List, game_state: Any) -> int:
        """生成狼人击杀目标"""
        if not self._initialized:
            # 简单AI：随机选择
            import random
            non_werewolves = [p for p in players if p.alive and p.role != "WEREWOLF"]
            return random.choice(non_werewolves).id if non_werewolves else 0

        alive_players = [p for p in players if p.alive]
        non_werewolves = [p for p in alive_players if p.role != "WEREWOLF"]

        if not non_werewolves:
            return 0

        # 智能击杀策略
        role_priority = {
            "SEER": 5,    # 预言家最危险，优先击杀
            "WITCH": 4,   # 女巫能救人毒人，很危险
            "HUNTER": 3,  # 猎人能带走人，中等危险
            "VILLAGER": 1 # 村民威胁最小
        }

        target_list = []
        for target in non_werewolves:
            priority = role_priority.get(target.role, 1)
            target_list.append(f"{target.id}. {target.name} (优先级: {priority})")

        prompt = f"""作为狼人，选择今晚要击杀的目标。

存活玩家信息：
{chr(10).join(target_list)}

击杀策略：
1. 优先击杀预言家（他知道狼人身份）
2. 其次击杀女巫（她能救人和毒人）
3. 再击杀猎人（他能开枪带走人）
4. 最后才击杀村民

请只回复目标玩家的数字ID："""

        response = await self.generate_response(prompt, "WEREWOLF", {"role": "WEREWOLF"})

        try:
            target_id = int(response.strip())
            # 验证目标是否有效
            if target_id in [p.id for p in non_werewolves]:
                return target_id
        except (ValueError, AttributeError):
            pass

        # 如果AI选择无效，按优先级选择
        for target in non_werewolves:
            if target.role == "SEER":
                return target.id
        for target in non_werewolves:
            if target.role == "WITCH":
                return target.id
        for target in non_werewolves:
            if target.role == "HUNTER":
                return target.id

        # 最后随机选择村民
        import random
        return random.choice(non_werewolves).id

    async def generate_seer_target(self, players: List, game_state: Any) -> int:
        """生成预言家查验目标"""
        if not self._initialized:
            # 简单AI：随机选择
            import random
            unknown_players = [p for p in players if p.alive and p.id != game_state.get('current_player_id', 0)]
            return random.choice(unknown_players).id if unknown_players else 0

        seer_id = game_state.get('current_player_id', 0)
        alive_players = [p for p in players if p.alive and p.id != seer_id]

        if not alive_players:
            return 0

        # 智能查验策略
        target_list = []
        for target in alive_players:
            target_list.append(f"{target.id}. {target.name}")

        prompt = f"""作为预言家，选择今晚要查验的目标。

存活玩家：
{chr(10).join(target_list)}

查验策略：
1. 优先查验跳神职的人（验证他们身份真假）
2. 查验发言最活跃的人（他们可能是狼人带节奏）
3. 查验发言矛盾的人（可能在撒谎）
4. 查验很少发言的人（可能在隐藏身份）

请只回复目标玩家的数字ID："""

        response = await self.generate_response(prompt, "SEER", {"role": "SEER"})

        try:
            target_id = int(response.strip())
            # 验证目标是否有效
            if target_id in [p.id for p in alive_players]:
                return target_id
        except (ValueError, AttributeError):
            pass

        # 如果AI选择无效，随机选择
        import random
        return random.choice(alive_players).id

    async def generate_vote_target(self, players: List, game_state: Any) -> int:
        """生成投票目标"""
        if not self._initialized:
            # 简单AI：随机选择
            import random
            voter_id = game_state.get('current_player_id', 0)
            votable_players = [p for p in players if p.alive and p.id != voter_id]
            return random.choice(votable_players).id if votable_players else 0

        voter_id = game_state.get('current_player_id', 0)
        role = game_state.get('current_player_role', 'VILLAGER')
        votable_players = [p for p in players if p.alive and p.id != voter_id]

        if not votable_players:
            return 0

        target_list = []
        for target in votable_players:
            target_list.append(f"{target.id}. {target.name}")

        # 根据角色定制投票策略
        role_strategies = {
            "WEREWOLF": """
狼人投票策略：
1. 投票给最可疑的好人（不是狼同伴）
2. 跟随其他好人的投票，融入群体
3. 不要一直投同一个人，避免暴露
4. 必要时弃票或投次要目标""",

            "SEER": """
预言家投票策略：
1. 投票给查杀的玩家（你验出的狼人）
2. 说服其他人相信你的查验结果
3. 不要轻易投票给金水玩家
4. 带领好人阵营投票""",

            "WITCH": """
女巫投票策略：
1. 相信并支持真预言家的查杀
2. 投票给你怀疑的狼人
3. 不要暴露自己的女巫身份
4. 配合神职角色行动""",

            "HUNTER": """
猎人投票策略：
1. 投票给最可疑的狼人
2. 利用威慑力带领投票
3. 明确表达你的怀疑理由
4. 准备好开枪带走目标""",

            "VILLAGER": """
村民投票策略：
1. 相信并跟随真预言家
2. 分析发言找出漏洞
3. 不要轻信自称神职的人
4. 投票给最可疑的人"""
        }

        strategy = role_strategies.get(role, role_strategies["VILLAGER"])

        prompt = f"""作为{role}，选择今天的投票目标。

可投票玩家：
{chr(10).join(target_list)}

{strategy}

请只回复目标玩家的数字ID："""

        response = await self.generate_response(prompt, role, {"role": role})

        try:
            target_id = int(response.strip())
            # 验证目标是否有效
            if target_id in [p.id for p in votable_players]:
                return target_id
        except (ValueError, AttributeError):
            pass

        # 如果AI选择无效，随机选择
        import random
        return random.choice(votable_players).id

    async def generate_speech(self, players: List, game_state: Any, role: str) -> str:
        """生成发言内容"""
        context = {
            "round": game_state.get("current_round", 1),
            "alive_players": len([p for p in players if p.alive]),
            "role": role,
            "phase": game_state.get("phase", "白天")
        }

        prompt = f"""现在是狼人杀游戏的{context['phase']}阶段。
请根据你的角色{role}发表一段简短的发言（20-50字）。"""

        return await self.generate_response(prompt, role, context)


# 全局客户端实例
_global_client: Optional[OpenAIClientManager] = None


async def get_openai_client() -> OpenAIClientManager:
    """获取全局OpenAI客户端"""
    global _global_client
    if _global_client is None:
        _global_client = OpenAIClientManager()
        await _global_client.initialize()
    return _global_client


async def generate_ai_speech(players: List, game_state: Any, role: str) -> str:
    """便捷函数：生成AI发言"""
    client = await get_openai_client()
    return await client.generate_speech(players, game_state, role)


async def generate_ai_decision(decision_type: str, players: List, game_state: Any, role: str) -> int:
    """便捷函数：生成AI决策"""
    client = await get_openai_client()

    if decision_type == "werewolf_kill":
        return await client.generate_werewolf_target(players, game_state)
    elif decision_type == "seer_check":
        return await client.generate_seer_target(players, game_state)
    elif decision_type == "vote":
        return await client.generate_vote_target(players, game_state)
    else:
        return 0


if __name__ == "__main__":
    # 测试Silicon Flow配置
    print("测试Silicon Flow配置...")

    config = OpenAIConfig.load_config()
    if config:
        print("✅ 配置加载成功")
        logging.debug(f"   模型配置: {config['models']}")
    else:
        print("❌ 配置加载失败")

    # 测试客户端
    async def test_client():
        client = OpenAIClientManager()
        success = await client.initialize()
        if success:
            response = await client.generate_response("测试消息", "VILLAGER")
            print(f"测试响应: {response}")

    asyncio.run(test_client())