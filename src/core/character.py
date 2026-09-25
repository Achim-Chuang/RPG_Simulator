"""
Character entity, Mental Load calculations, and Essence Weaving operations.
"""

from enum import Enum
from typing import List, Dict, Tuple, Optional, Any
import math
from .traits import Trait, Tier, MAGE_RANKS, MageRankDef, LAMBDA_REPULSION


class MentalState(Enum):
    EQUILIBRIUM = "平穩境 (0% - 70%)"
    TENSION = "緊繃境 (71% - 100%)"
    EROSION = "侵蝕境 (101% - 130%)"
    DISSOLUTION = "崩解境 (> 130%)"


class CorruptionState(Enum):
    SANCTIFIED = "聖潔純真 (0 - 20)"
    TEMPTED = "凡心動搖 (21 - 50)"
    CORRUPTED = "混沌侵蝕 (51 - 80)"
    ABOMINATION = "深淵魔宿 (81 - 100)"


class Character:
    def __init__(
        self,
        char_id: str,
        name: str,
        rank_key: str = "Chorji",
        is_awakened: bool = False,
        gold: float = 0.0,
        current_location_id: str = "node_free_city"
    ):
        self.char_id = char_id
        self.name = name
        self.rank_key = rank_key
        self.is_awakened = is_awakened
        self.interaction_count = 0
        self.gold = gold
        self.current_location_id = current_location_id

        # 行動點數 (AP) 與累積休息點數
        self.current_ap: int = 10
        self.rest_accumulated: int = 0

        # 靈魂腐化值 (0.0 ~ 100.0)
        self.corruption: float = 0.0

        # 詞條槽位
        self.innate_traits: List[Trait] = []
        self.acquired_traits: List[Trait] = []
        self.imprinted_traits: List[Trait] = []

        # 精神力
        self.current_mp: float = self.max_mp

    @property
    def rank_def(self) -> MageRankDef:
        return MAGE_RANKS.get(self.rank_key, MAGE_RANKS["Chorji"])

    @property
    def max_mp(self) -> float:
        return 100.0 * self.rank_def.mp_multiplier

    def calculate_sustained_load(self) -> float:
        if self.rank_key == "Transcendent":
            return 0.0  # 超凡者超越因果負荷，負擔永遠為 0
        n = len(self.imprinted_traits)
        if n == 0:
            return 0.0
        base_sum = sum(t.base_load for t in self.imprinted_traits)
        multiplier = math.pow(1.0 + LAMBDA_REPULSION, n - 1)
        return base_sum * multiplier

    @property
    def stress_ratio(self) -> float:
        if self.rank_key == "Transcendent":
            return 0.0
        return self.calculate_sustained_load() / self.max_mp

    def get_mental_state(self) -> Tuple[MentalState, str]:
        if self.rank_key == "Transcendent":
            return MentalState.EQUILIBRIUM, "【超凡神格】：意志與宇宙因果同頻，永恆安寧。"
        ratio = self.stress_ratio
        if ratio <= 0.70:
            return MentalState.EQUILIBRIUM, "心神平穩，精神力正常自然恢復。"
        elif ratio <= 1.00:
            return MentalState.TENSION, "太陽穴輕微抽痛，神經緊繃，感知+5%，精神恢復減半。"
        elif ratio <= 1.30:
            return MentalState.EROSION, "精神遭受侵蝕！開始出現多疑與幻聽，每日面臨意志檢定。"
        else:
            return MentalState.DISSOLUTION, "【思維崩解】！大腦超載臨界，爆發異象衝擊，面臨永久性思維碎裂！"

    def get_corruption_state(self) -> Tuple[CorruptionState, str]:
        if self.corruption <= 20.0:
            return CorruptionState.SANCTIFIED, "靈魂純淨如初，神聖意志堅如磐石。"
        elif self.corruption <= 50.0:
            return CorruptionState.TEMPTED, "低語侵擾，凡心微動，但理智尚存。"
        elif self.corruption <= 80.0:
            return CorruptionState.CORRUPTED, "【混沌侵蝕】心智受邪祟滲透，外貌呈現異變，正道勢力高度警惕！"
        else:
            return CorruptionState.ABOMINATION, "【深淵魔宿】靈魂徹底墮落為惡魔宿主/黑暗君主，觸發全域異端絕罰！"

    def modify_corruption(self, delta: float, reason: str = "") -> str:
        old_val = self.corruption
        self.corruption = max(0.0, min(100.0, round(self.corruption + delta, 1)))
        state, _ = self.get_corruption_state()
        direction = "加深" if delta > 0 else "淨化"
        msg = f"【靈魂印記】{self.name} 腐化度{direction} {abs(delta):.1f} (當前: {self.corruption}/100.0) [{state.value}] 原因：{reason}"
        if old_val < 80.0 and self.corruption >= 80.0:
            msg += "\n  ⚠【極度警報】靈魂墮落突破臨界點！觸發審判庭全域異端絕罰追殺令！"
        return msg

    def can_interact_with(self, trait: Trait) -> Tuple[bool, str]:
        if self.rank_key == "Transcendent":
            return True, "【超凡者權柄】：凌駕一切位階，全知編織一切本質。"
        if not self.is_awakened:
            return False, f"{self.name} 並未覺醒，無法直視或干涉本質。"
        if self.rank_def.tier_cap < trait.tier:
            return False, (
                f"位階不足！當前位階【{self.rank_def.name}】最高僅能干涉【{self.rank_def.tier_cap}】，"
                f"無法處理【{trait.tier}】詞條「{trait.name}」。"
            )
        return True, "許可"

    def imprint_trait(self, target: 'Character', trait: Trait, resistance: float = 1.0) -> Tuple[bool, str]:
        allowed, msg = self.can_interact_with(trait)
        if not allowed:
            return False, f"刻印失敗：{msg}"

        if self.rank_key != "Transcendent" and len(target.imprinted_traits) >= target.rank_def.slot_cap:
            return False, f"刻印失敗：{target.name} 的刻印槽位已滿（{target.rank_def.slot_cap}/{target.rank_def.slot_cap}）！"

        n_target = len(target.imprinted_traits)
        instant_cost = 0.0 if self.rank_key == "Transcendent" else trait.instant_cost * (1.0 + 0.15 * n_target) * resistance

        if self.current_mp < instant_cost:
            return False, f"刻印失敗：瞬時精神力不足（需 {instant_cost:.1f}，現有 {self.current_mp:.1f}）。"

        self.current_mp -= instant_cost
        self.interaction_count += 1
        target.imprinted_traits.append(trait)

        corruption_log = ""
        if trait.corruption_delta != 0.0:
            c_msg = target.modify_corruption(trait.corruption_delta, f"刻印詞條「{trait.name}」")
            corruption_log = f"\n  - {c_msg}"

        load = target.calculate_sustained_load()
        state, state_desc = target.get_mental_state()

        return True, (
            f"成功將【{trait.tier}】「{trait.name}」刻印至 {target.name}！\n"
            f"  - 消耗瞬時精神力: {instant_cost:.1f} MP (剩餘: {self.current_mp:.1f})\n"
            f"  - {target.name} 常駐負荷: {load:.1f}/{target.max_mp:.1f} ({target.stress_ratio*100:.1f}%) [{state.value}]"
            f"{corruption_log}"
        )


    def strip_trait(self, target: 'Character', trait: Trait) -> Tuple[bool, str]:
        if trait not in target.imprinted_traits:
            return False, f"{target.name} 身上未找到刻印詞條「{trait.name}」。"

        target.imprinted_traits.remove(trait)
        self.interaction_count += 1
        load = target.calculate_sustained_load()
        state, _ = target.get_mental_state()

        return True, (
            f"已成功剝離 {target.name} 身上的「{trait.name}」。\n"
            f"  - 當前常駐負荷降至: {load:.1f}/{target.max_mp:.1f} ({target.stress_ratio*100:.1f}%) [{state.value}]"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "char_id": self.char_id,
            "name": self.name,
            "rank_key": self.rank_key,
            "is_awakened": self.is_awakened,
            "interaction_count": self.interaction_count,
            "gold": self.gold,
            "current_location_id": self.current_location_id,
            "current_ap": self.current_ap,
            "rest_accumulated": self.rest_accumulated,
            "current_mp": self.current_mp,
            "corruption": self.corruption,
            "innate_traits": [t.id for t in self.innate_traits],
            "acquired_traits": [t.id for t in self.acquired_traits],
            "imprinted_traits": [t.id for t in self.imprinted_traits]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], trait_registry: Dict[str, Trait]) -> 'Character':
        char = cls(
            char_id=data["char_id"],
            name=data["name"],
            rank_key=data.get("rank_key", "Chorji"),
            is_awakened=data.get("is_awakened", False),
            gold=data.get("gold", 0.0),
            current_location_id=data.get("current_location_id", "node_free_city")
        )
        char.interaction_count = data.get("interaction_count", 0)
        char.current_ap = data.get("current_ap", 10)
        char.rest_accumulated = data.get("rest_accumulated", 0)
        char.current_mp = data.get("current_mp", char.max_mp)
        char.corruption = float(data.get("corruption", 0.0))

        for tid in data.get("innate_traits", []):
            if tid in trait_registry:
                char.innate_traits.append(trait_registry[tid])
        for tid in data.get("acquired_traits", []):
            if tid in trait_registry:
                char.acquired_traits.append(trait_registry[tid])
        for tid in data.get("imprinted_traits", []):
            if tid in trait_registry:
                char.imprinted_traits.append(trait_registry[tid])

        return char
