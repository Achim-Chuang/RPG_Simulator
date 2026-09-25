"""
Ruins Exploration System: Environment-based procedural events, ancient traps, guardians, and lost relics.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
import random
from .character import Character
from .actions import ActionCheckEngine
from .combat import Combatant, PersonalCombatEngine


class RuinBiome(Enum):
    WASTELAND = "荒原廢墟"
    FOREST = "幽深密林神殿"
    TUNDRA = "極地凍土鋼鐵地堡"
    DESERT = "灼熱沙漠金字塔"


@dataclass
class RuinSite:
    ruin_id: str
    name: str
    biome: RuinBiome
    danger_level: int = 1  # 1 到 5
    is_looted: bool = False
    possible_loot: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ruin_id": self.ruin_id,
            "name": self.name,
            "biome": self.biome.name,
            "danger_level": self.danger_level,
            "is_looted": self.is_looted,
            "possible_loot": self.possible_loot
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RuinSite':
        return cls(
            ruin_id=data["ruin_id"],
            name=data["name"],
            biome=RuinBiome[data["biome"]],
            danger_level=data.get("danger_level", 1),
            is_looted=data.get("is_looted", False),
            possible_loot=data.get("possible_loot", [])
        )


class RuinsExplorationEngine:
    @staticmethod
    def explore_ruin(
        ruin: RuinSite,
        explorer: Character,
        seed: Optional[int] = None
    ) -> Tuple[str, Optional[str], List[str]]:
        """
        探索遺跡：
        - 耗費 2 AP
        - 事件隨機性：
          1. 陷阱考驗 (Action check 50% +/- 5%)
          2. 古代守衛交鋒 (戰鬥)
          3. 空無一物的廢墟 (Empty)
          4. 遠古秘寶或史前科技彩蛋 (Loot)
        """
        if seed is not None:
            random.seed(seed)

        logs = []
        logs.append(f"【深入遺跡】{explorer.name} 踏入位於【{ruin.biome.value}】的「{ruin.name}」（危險度: ★{ruin.danger_level}）！")

        if explorer.current_ap < 2:
            return "NO_AP", None, [f"{explorer.name} AP 不足（探索需 2 AP，剩餘 {explorer.current_ap} AP）。"]

        explorer.current_ap -= 2
        logs.append(f"消耗 2 點行動力進行深度搜索 (剩餘 AP: {explorer.current_ap})。")

        if ruin.is_looted:
            logs.append("這座遺跡早已在歲月中被洗劫一空，壁畫斑駁，只剩滿地碎石與塵埃。")
            return "EMPTY", None, logs

        # 決定事件類型：Trap (30%), Guardian (30%), Empty (20%), Loot (20%)
        event_roll = random.random()

        if event_roll < 0.30:
            # 1. 陷阱考驗
            trap_name = f"{ruin.biome.value}的古代符文落石機關"
            # 依角色詞條計算修正
            mods = {}
            trait_names = [t.name for t in explorer.innate_traits + explorer.acquired_traits + explorer.imprinted_traits]
            if "半精靈敏銳感知" in trait_names:
                mods["[半精靈敏銳感知]"] = +3  # +15%
            if "夜巡直覺" in trait_names:
                mods["[夜巡直覺]"] = +2  # +10%
            if "百戰直覺" in trait_names:
                mods["[百戰直覺]"] = +3  # +15%
            mods[f"環境凶險 (★{ruin.danger_level})"] = -ruin.danger_level  # -5% * danger

            success, check_log = ActionCheckEngine.execute_action(
                f"規避{trap_name}",
                is_challenging=True,
                modifiers=mods
            )
            logs.append(check_log)
            if success:
                logs.append(f"  ★ {explorer.name} 身手矯健，在千鈞一髮之際避開陷阱，安全穿越墓道！")
                reward = random.choice(ruin.possible_loot) if ruin.possible_loot else None
                if reward:
                    ruin.is_looted = True
                    logs.append(f"  ★ 在陷阱密室後方發現了未被歲月腐蝕的秘匣，獲得詞條秘典: 【{reward}】！")
                    return "LOOT", reward, logs
                return "PASS", None, logs
            else:
                logs.append(f"  ✗ 機關觸發！碎石砸落，{explorer.name} 狼狽脫險，精神受到震懾！")
                return "TRAP_HIT", None, logs

        elif event_roll < 0.60:
            # 2. 古代守衛交鋒
            logs.append(f"沉重的金屬摩擦聲響起！地宮深處走出一尊【★{ruin.danger_level} 古代機巧傀儡守衛】！")
            fighter_hero = Combatant(
                id=explorer.char_id,
                name=explorer.name,
                side="A",
                hp=50,
                max_hp=50,
                atk=18,
                defense=6,
                spd=12
            )
            guardian = Combatant(
                id="ancient_golem",
                name=f"遺跡守衛·VII型",
                side="B",
                hp=30 + ruin.danger_level * 10,
                max_hp=30 + ruin.danger_level * 10,
                atk=12 + ruin.danger_level * 2,
                defense=4 + ruin.danger_level,
                spd=7,
                traits=["無所畏懼"]
            )
            reason, _, combat_logs = PersonalCombatEngine.run_combat(
                side_a=[fighter_hero],
                side_b=[guardian],
                attacker_side="A",
                attacker_ap=explorer.current_ap + 1  # 補償已扣除的AP
            )
            logs.extend(combat_logs)

            if fighter_hero.is_active:
                logs.append("守衛傀儡轟然倒地，其核心散發著奇異的能量光暈！")
                reward = random.choice(ruin.possible_loot) if ruin.possible_loot else None
                if reward:
                    ruin.is_looted = True
                    logs.append(f"  ★ 拆解守衛殘骸，在基座深處起獲遠古遺存: 【{reward}】！")
                    return "LOOT", reward, logs
                return "WIN", None, logs
            else:
                logs.append(f"{explorer.name} 不敵遠古守衛，被迫撤出遺跡！")
                return "DEFEAT", None, logs

        elif event_roll < 0.80:
            # 3. 空無一物
            logs.append("穿過漫長深邃的石階，大殿空空蕩蕩，唯有殘破的支柱與隨風揚起的沙礫。這裡早已沒有任何有價值的遺物。")
            return "EMPTY", None, logs

        else:
            # 4. 直接尋獲古代寶庫
            logs.append("幸運眷顧！你發現了一處未曾崩塌的古代供奉聖所！")
            reward = random.choice(ruin.possible_loot) if ruin.possible_loot else None
            if reward:
                ruin.is_looted = True
                logs.append(f"  ★ 在石棺與水晶台前，起獲失落的遠古詞條真傳: 【{reward}】！")
                return "LOOT", reward, logs
            else:
                logs.append("聖所雖完好，但祭壇上的器物已自然風化為微塵。")
                return "EMPTY", None, logs
