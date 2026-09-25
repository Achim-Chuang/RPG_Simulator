"""
Core Trait & Mental Overload Simulation Prototype
Verifies the 5 Tibetan-inspired Mage Ranks, Trait classification,
exponential sustained load formula (lambda=0.08), and overload backlash states.
"""

from enum import IntEnum, Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math


class Tier(IntEnum):
    REGULAR = 1
    UNCOMMON = 2
    RARE = 3
    MYSTIC = 4
    EPIC = 5

    def __str__(self):
        return self.name.capitalize()


class Category(Enum):
    INNATE = "先天"
    ACQUIRED = "後天"
    ARTIFACT = "器物"


class MentalState(Enum):
    EQUILIBRIUM = "平穩境 (0% - 70%)"
    TENSION = "緊繃境 (71% - 100%)"
    EROSION = "侵蝕境 (101% - 130%)"
    DISSOLUTION = "崩解境 (> 130%)"


@dataclass
class MageRankDef:
    name: str
    tier_cap: Tier
    slot_cap: int
    mp_multiplier: float
    required_interactions: int
    breakthrough_event: str


MAGE_RANKS: Dict[str, MageRankDef] = {
    "Chorji": MageRankDef(
        name="綽爾濟 (Chorji)",
        tier_cap=Tier.REGULAR,
        slot_cap=3,
        mp_multiplier=1.0,  # Base 100
        required_interactions=0,
        breakthrough_event="【自我覺察】：看見萬物本質，初步干涉因果。"
    ),
    "Shabrung": MageRankDef(
        name="夏仲 (Shabrung)",
        tier_cap=Tier.UNCOMMON,
        slot_cap=5,
        mp_multiplier=2.0,  # 200
        required_interactions=100,
        breakthrough_event="【心識拓寬】：經歷瀕死或精神質變，神經網絡重組。"
    ),
    "Pandita": MageRankDef(
        name="班智達 (Pandita)",
        tier_cap=Tier.RARE,
        slot_cap=10,
        mp_multiplier=4.0,  # 400
        required_interactions=500,
        breakthrough_event="【博學者之眼】：研讀《古源刻印手稿》，掌握詞條語法。"
    ),
    "Nomenkhan": MageRankDef(
        name="諾門罕 (Nomenkhan)",
        tier_cap=Tier.MYSTIC,
        slot_cap=20,
        mp_multiplier=8.0,  # 800
        required_interactions=1000,
        breakthrough_event="【法王冠冕】：達成世俗人生大事（立國/子嗣），悟透因果之重。"
    ),
    "Hutuktu": MageRankDef(
        name="呼圖克圖 (Hutuktu)",
        tier_cap=Tier.EPIC,
        slot_cap=50,
        mp_multiplier=20.0, # 2000
        required_interactions=5000,
        breakthrough_event="【轉世與不朽】：覲見第一代永生覺醒者，重組生命法則。"
    )
}

# 基礎數值常數
TIER_BASE_LOAD = {
    Tier.REGULAR: 15.0,
    Tier.UNCOMMON: 28.0,
    Tier.RARE: 50.0,
    Tier.MYSTIC: 90.0,
    Tier.EPIC: 160.0
}

TIER_BASE_INSTANT_COST = {
    Tier.REGULAR: 20.0,
    Tier.UNCOMMON: 40.0,
    Tier.RARE: 80.0,
    Tier.MYSTIC: 160.0,
    Tier.EPIC: 350.0
}

LAMBDA_REPULSION = 0.08  # 排斥膨脹係數


@dataclass
class Trait:
    id: str
    name: str
    category: Category
    tier: Tier
    description: str
    modifiers: Dict[str, float] = field(default_factory=dict)

    @property
    def base_load(self) -> float:
        return TIER_BASE_LOAD[self.tier]

    @property
    def instant_cost(self) -> float:
        return TIER_BASE_INSTANT_COST[self.tier]


class Character:
    def __init__(self, char_id: str, name: str, rank_key: str = "Chorji", is_awakened: bool = False):
        self.char_id = char_id
        self.name = name
        self.rank_key = rank_key
        self.is_awakened = is_awakened
        self.interaction_count = 0

        # 詞條槽位
        self.innate_traits: List[Trait] = []
        self.acquired_traits: List[Trait] = []
        self.imprinted_traits: List[Trait] = []  # 由魔法篡改/刻印的詞條，承受維持負荷

        # 當前可用精神力點數（瞬時池）
        self.current_mp: float = self.max_mp

    @property
    def rank_def(self) -> MageRankDef:
        return MAGE_RANKS[self.rank_key]

    @property
    def max_mp(self) -> float:
        return 100.0 * self.rank_def.mp_multiplier

    def calculate_sustained_load(self) -> float:
        """
        計算當前所有被刻印詞條的總維持負荷：
        Total Load = (Sum of Base Load) * (1 + lambda)^(N - 1)
        """
        n = len(self.imprinted_traits)
        if n == 0:
            return 0.0

        base_sum = sum(t.base_load for t in self.imprinted_traits)
        multiplier = math.pow(1.0 + LAMBDA_REPULSION, n - 1)
        return base_sum * multiplier

    @property
    def stress_ratio(self) -> float:
        """精神負荷佔比 (0.0 = 0%, 1.0 = 100%)"""
        return self.calculate_sustained_load() / self.max_mp

    def get_mental_state(self) -> Tuple[MentalState, str]:
        ratio = self.stress_ratio
        if ratio <= 0.70:
            return MentalState.EQUILIBRIUM, "心神平穩，精神力正常自然恢復。"
        elif ratio <= 1.00:
            return MentalState.TENSION, "太陽穴輕微抽痛，神經緊繃，感知+5%，精神恢復減半。"
        elif ratio <= 1.30:
            return MentalState.EROSION, "精神遭受侵蝕！開始出現多疑與幻聽，每日面臨意志檢定。"
        else:
            return MentalState.DISSOLUTION, "【思維崩解】！大腦超載臨界，爆發異象衝擊，面臨永久性思維碎裂！"

    def can_interact_with(self, trait: Trait) -> Tuple[bool, str]:
        """檢查覺醒者位階是否允許與該階級詞條互動"""
        if not self.is_awakened:
            return False, f"{self.name} 並未覺醒，無法直視或干涉本質。"

        if self.rank_def.tier_cap < trait.tier:
            return False, (
                f"位階不足！當前位階【{self.rank_def.name}】最高僅能干涉【{self.rank_def.tier_cap}】，"
                f"無法處理【{trait.tier}】詞條「{trait.name}」。"
            )
        return True, "許可"

    def imprint_trait(self, target: 'Character', trait: Trait, resistance: float = 1.0) -> Tuple[bool, str]:
        """
        對目標刻印詞條
        """
        allowed, msg = self.can_interact_with(trait)
        if not allowed:
            return False, f"刻印失敗：{msg}"

        # 槽位限制檢定（自身維持或目標維持）
        if len(target.imprinted_traits) >= target.rank_def.slot_cap:
            return False, f"刻印失敗：{target.name} 的刻印槽位已滿（{target.rank_def.slot_cap}/{target.rank_def.slot_cap}）！"

        # 瞬時消耗計算
        n_target = len(target.imprinted_traits)
        instant_cost = trait.instant_cost * (1.0 + 0.15 * n_target) * resistance

        if self.current_mp < instant_cost:
            return False, f"刻印失敗：瞬時精神力不足（需 {instant_cost:.1f}，現有 {self.current_mp:.1f}）。"

        # 扣除瞬時精神力並增加互動計數
        self.current_mp -= instant_cost
        self.interaction_count += 1
        target.imprinted_traits.append(trait)

        load = target.calculate_sustained_load()
        state, state_desc = target.get_mental_state()

        return True, (
            f"成功將【{trait.tier}】「{trait.name}」刻印至 {target.name}！\n"
            f"  - 施法者消耗瞬時精神力: {instant_cost:.1f} MP (剩餘: {self.current_mp:.1f})\n"
            f"  - {target.name} 當前刻印詞條數: {len(target.imprinted_traits)}/{target.rank_def.slot_cap}\n"
            f"  - {target.name} 常駐維持負荷: {load:.1f} / {target.max_mp:.1f} ({target.stress_ratio*100:.1f}%)\n"
            f"  - 精神狀態: {state.value} -> {state_desc}"
        )

    def strip_trait(self, target: 'Character', trait: Trait) -> Tuple[bool, str]:
        """剝離目標身上的刻印詞條"""
        if trait not in target.imprinted_traits:
            return False, f"{target.name} 身上未找到刻印詞條「{trait.name}」。"

        target.imprinted_traits.remove(trait)
        self.interaction_count += 1
        load = target.calculate_sustained_load()
        state, _ = target.get_mental_state()

        return True, (
            f"已成功剝離 {target.name} 身上的「{trait.name}」。\n"
            f"  - 當前常駐負荷降至: {load:.1f} / {target.max_mp:.1f} ({target.stress_ratio*100:.1f}%)\n"
            f"  - 當前狀態: {state.value}"
        )


# ==============================================================================
# 模擬驗證與情境演練
# ==============================================================================

def run_simulation():
    print("=" * 70)
    print("      核心詞條與精神過載模擬原型 (Core Simulation Prototype)")
    print("=" * 70)

    # 1. 建立測試詞條庫
    traits_db = {
        # Regular
        "reg_malnourished": Trait("reg_malnourished", "重度營養不良", Category.ACQUIRED, Tier.REGULAR, "體力上限-20%"),
        "reg_fracture": Trait("reg_fracture", "右臂骨折", Category.ACQUIRED, Tier.REGULAR, "無法持重武器"),
        "reg_dagger": Trait("reg_dagger", "粗淺匕首技巧", Category.ACQUIRED, Tier.REGULAR, "匕首命中+10%"),
        "reg_arithmetic": Trait("reg_arithmetic", "市井算術", Category.ACQUIRED, Tier.REGULAR, "交易議價+5%"),
        "reg_alertness": Trait("reg_alertness", "夜巡直覺", Category.ACQUIRED, Tier.REGULAR, "遭遇突襲率-15%"),
        
        # Uncommon
        "unc_veteran": Trait("unc_veteran", "百戰直覺", Category.ACQUIRED, Tier.UNCOMMON, "格擋率+20%，免疫初級恐慌"),
        "unc_iron_skin": Trait("unc_iron_skin", "剛體秘術", Category.ACQUIRED, Tier.UNCOMMON, "受到物理傷害減免15%"),
        
        # Rare
        "rare_fox_charm": Trait("rare_fox_charm", "天狐媚骨", Category.INNATE, Tier.RARE, "社交說服率+35%"),
        
        # Mystic
        "mystic_dragon_eye": Trait("mystic_dragon_eye", "真龍之瞳", Category.INNATE, Tier.MYSTIC, "洞悉所有因果缺陷"),
        
        # Epic
        "epic_immortal": Trait("epic_immortal", "不朽之息", Category.INNATE, Tier.EPIC, "壽命鎖死，免除自然死亡")
    }

    # 2. 初始化角色
    hero = Character("hero", "無名孤兒 (主角)", rank_key="Chorji", is_awakened=True)
    veteran = Character("veteran", "受傷的退役老兵", rank_key="Chorji", is_awakened=False)

    print(f"\n[角色初始化]")
    print(f"主角: {hero.name} | 位階: {hero.rank_def.name} | MP: {hero.current_mp}/{hero.max_mp} | 槽位: {hero.rank_def.slot_cap}")
    print(f"NPC: {veteran.name} | 凡人未覺醒\n")

    # 3. 測試情境一：位階限制檢定
    print("-" * 70)
    print("【測試情境 1：位階限制檢定】")
    print(f"主角（綽爾濟 / Regular階）嘗試在自己身上刻印【Uncommon】「{traits_db['unc_veteran'].name}」...")
    success, msg = hero.imprint_trait(hero, traits_db["unc_veteran"])
    print(f"結果: {msg}")

    # 4. 測試情境二：平滑指數負荷增長驗證 (1 ~ 3 個 Regular 詞條)
    print("\n" + "-" * 70)
    print("【測試情境 2：平滑指數負荷增長 (綽爾濟位階滿槽)】")
    test_traits = [traits_db["reg_dagger"], traits_db["reg_arithmetic"], traits_db["reg_alertness"]]

    for i, t in enumerate(test_traits, 1):
        print(f"\n--> 刻印第 {i} 個 Regular 詞條: 「{t.name}」")
        success, msg = hero.imprint_trait(hero, t)
        print(msg)

    # 5. 測試情境三：槽位極限與突破晉升 (綽爾濟 -> 夏仲)
    print("\n" + "-" * 70)
    print("【測試情境 3：突破晉升 (Chorji -> Shabrung)】")
    print("嘗試刻印第 4 個詞條（已達綽爾濟槽位上限 3）:")
    success, msg = hero.imprint_trait(hero, traits_db["reg_fracture"])
    print(f"結果: {msg}")

    print("\n[世界事件觸發] 主角完成了 100 次本質洞悉，並在邊境瀕死中達成突破！")
    hero.rank_key = "Shabrung"
    hero.current_mp = hero.max_mp  # 突破後回滿精神力
    print(f"★ 晉升為【{hero.rank_def.name}】！")
    print(f"   - 精神力總量翻倍: {hero.max_mp} MP")
    print(f"   - 槽位擴展至: {hero.rank_def.slot_cap} 個")
    print(f"   - 最高干涉階級解鎖: {hero.rank_def.tier_cap}")
    print(f"   - 當前既有 3 個詞條在新總量下的負荷率: {hero.stress_ratio*100:.1f}% (降至輕鬆平穩狀態)")

    # 6. 測試情境四：跨階刻印與精神過載反噬 (突破後刻印 Uncommon)
    print("\n" + "-" * 70)
    print("【測試情境 4：夏仲位階刻印 Uncommon 詞條與極限過載】")
    print(f"刻印【Uncommon】「{traits_db['unc_veteran'].name}」:")
    success, msg = hero.imprint_trait(hero, traits_db["unc_veteran"])
    print(msg)

    print(f"\n刻印第 5 個詞條【Uncommon】「{traits_db['unc_iron_skin'].name}」:")
    success, msg = hero.imprint_trait(hero, traits_db["unc_iron_skin"])
    print(msg)

    # 7. 測試情境五：超載臨界狀態模擬
    print("\n" + "-" * 70)
    print("【測試情境 5：過載臨界分析】")
    print(f"當前主角身上的刻印詞條清單: {[t.name for t in hero.imprinted_traits]}")
    total_load = hero.calculate_sustained_load()
    ratio = hero.stress_ratio
    state, desc = hero.get_mental_state()
    print(f"總持續負荷: {total_load:.2f} / {hero.max_mp} ({ratio*100:.1f}%)")
    print(f"當前狀態: {state.value}")
    print(f"狀態效應: {desc}")
    print("=" * 70)


if __name__ == "__main__":
    run_simulation()
