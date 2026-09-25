"""
Daily Life Schedule, Action Suites & Trait-Driven Coup Prototype
Demonstrates:
1. Daily schedule (Morning, Afternoon, Night) with 10 fixed AP per slot (unused AP converted to Rest).
2. Composite Action Suites (Pipelines that only settle rewards upon 100% completion).
3. Passive (Role-driven) vs. Active (Ambition-driven) suite activation.
4. Trait-driven Utility AI prioritizing actions (Diligent vs. Extremely Lazy).
5. The Protagonist tampering with an NPC's traits to trigger an emergent, autonomous coup!
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Tuple


class TimeSlot(Enum):
    MORNING = "早晨"
    AFTERNOON = "午後"
    NIGHT = "夜間"


@dataclass
class SubAction:
    name: str
    ap_cost: int


@dataclass
class ActionSuite:
    suite_id: str
    name: str
    category: str  # "business", "security", "conspiracy", "rest"
    steps: List[SubAction]
    current_step_idx: int = 0
    is_completed: bool = False
    repeatable: bool = True  # 是否每日可重複執行 (如日常經商)
    on_complete: Optional[Callable[['Person'], None]] = None

    @property
    def total_ap_cost(self) -> int:
        return sum(s.ap_cost for s in self.steps)

    @property
    def current_step(self) -> Optional[SubAction]:
        if self.current_step_idx < len(self.steps):
            return self.steps[self.current_step_idx]
        return None

    def advance(self, person: 'Person') -> Tuple[bool, str]:
        step = self.current_step
        if not step:
            return False, "無剩餘步驟"

        if person.current_ap < step.ap_cost:
            return False, f"AP不足（需 {step.ap_cost}，剩餘 {person.current_ap}）"

        person.current_ap -= step.ap_cost
        self.current_step_idx += 1
        log_msg = f"{person.name} 消耗 {step.ap_cost} AP 執行「{self.name}」步驟 [{self.current_step_idx}/{len(self.steps)}]: 【{step.name}】 (剩餘AP: {person.current_ap})"

        if self.current_step_idx >= len(self.steps):
            self.is_completed = True
            log_msg += f"\n  ★ 「{self.name}」全部步驟達成！進行最終結算！"
            print(f"  {log_msg}")
            if self.on_complete:
                self.on_complete(person)
            if self.repeatable:
                self.current_step_idx = 0
                self.is_completed = False
            return True, ""

        return True, log_msg


class Person:
    def __init__(self, char_id: str, name: str, traits: List[str], gold: float = 0.0):
        self.char_id = char_id
        self.name = name
        self.traits: List[str] = list(traits)
        self.gold: float = gold

        # 每日AP
        self.current_ap: int = 10
        self.rest_ap_accumulated: int = 0

        # 掛載的行動事件組庫
        self.active_suites: List[ActionSuite] = []
        self.in_progress_suite: Optional[ActionSuite] = None

    def has_trait(self, trait_name: str) -> bool:
        return trait_name in self.traits

    def add_trait(self, trait_name: str):
        if trait_name not in self.traits:
            self.traits.append(trait_name)

    def remove_trait(self, trait_name: str):
        if trait_name in self.traits:
            self.traits.remove(trait_name)

    def evaluate_utility(self, suite: ActionSuite) -> float:
        """
        性格驅動的效用 AI（Utility AI）：
        評估該事件組在當前情境下的渴望程度
        """
        score = 50.0  # 基準分

        # 延續性加成：如果已經在進行中，優先完成它
        if self.in_progress_suite == suite:
            score += 40.0

        if suite.category == "business":
            if self.has_trait("勤勉"):
                score += 50.0
            if self.has_trait("貪婪"):
                score += 35.0
            if self.has_trait("極度懶散"):
                score -= 60.0  # 嚴重厭惡工作

        elif suite.category == "security":
            if self.has_trait("忠厚本分"):
                score += 60.0
            if self.has_trait("野心家"):
                score -= 30.0  # 不屑於常規巡邏

        elif suite.category == "conspiracy":
            if self.has_trait("忠厚本分"):
                return -999.0  # 絕對排斥叛變
            if self.has_trait("野心家"):
                score += 80.0
            if self.has_trait("暗中欠債"):
                score += 40.0  # 走投無路，鋌而走險

        return score

    def act_slot(self, slot: TimeSlot):
        """在一個時段內分配 10 AP 執行行動"""
        self.current_ap = 10
        print(f"\n--- [{slot.value}] {self.name} 開始行動 (起始 AP: 10) ---")

        while self.current_ap > 0:
            # 1. 篩選有價值的事件組
            candidate_suites = [s for s in self.active_suites if not s.is_completed]
            if not candidate_suites:
                break

            # 2. 評估效用最高者
            best_suite = max(candidate_suites, key=self.evaluate_utility)
            utility_score = self.evaluate_utility(best_suite)

            # 如果最高效用低於門檻（例如極度懶散導致評分過低），選擇休息放空
            if utility_score < 30.0 and self.in_progress_suite is None:
                print(f"  [選擇放空] {self.name} 心神散漫（最高動機僅 {utility_score:.1f}），決定什麼都不做，坐下休息。")
                break

            # 3. 推進該事件組
            next_step = best_suite.current_step
            if not next_step or next_step.ap_cost > self.current_ap:
                # 剩餘 AP 不足以進行下一步驟
                break

            self.in_progress_suite = best_suite
            success, log = best_suite.advance(self)
            print(f"  {log}")

            if best_suite.is_completed or best_suite.current_step_idx == 0:
                self.in_progress_suite = None

        # 4. 時段結束結算：未用完的 AP 自動化為休息
        unused = self.current_ap
        if unused > 0:
            self.rest_ap_accumulated += unused
            print(f"  [時段結束] 剩餘 {unused} AP 自動轉化為「休息放鬆」（累計休息點數: {self.rest_ap_accumulated}）。未用 AP 清零。")
        self.current_ap = 0


# ==============================================================================
# 具體行動事件組工廠 (Suite Factory)
# ==============================================================================

def make_shop_suite() -> ActionSuite:
    def on_complete(p: Person):
        revenue = 65.0
        p.gold += revenue
        print(f"    >> [商業結算] 店鋪當日結算完畢，扣除進貨成本，淨賺 +{revenue:.1f} 金！(個人總資產: {p.gold:.1f} 金)")

    return ActionSuite(
        suite_id="suite_business_shop",
        name="經營個人商業",
        category="business",
        steps=[
            SubAction("早市進貨", ap_cost=1),
            SubAction("庫房理貨與上架", ap_cost=1),
            SubAction("開門迎客與買賣議價", ap_cost=1),
            SubAction("盤點賬冊與收支貨款", ap_cost=1)
        ],
        repeatable=True,
        on_complete=on_complete
    )


def make_patrol_suite() -> ActionSuite:
    def on_complete(p: Person):
        print(f"    >> [防務結算] 城防巡邏完成，排查潛在危險，衛隊長維持城池治安良好。")

    return ActionSuite(
        suite_id="suite_security_patrol",
        name="日常城防巡邏",
        category="security",
        steps=[
            SubAction("整飭衛隊隊列", ap_cost=2),
            SubAction("排查市集與城門盲區", ap_cost=2),
            SubAction("填寫防務治安通報", ap_cost=1)
        ],
        repeatable=True,
        on_complete=on_complete
    )


def make_coup_suite(target_lord_name: str) -> ActionSuite:
    def on_complete(p: Person):
        print(f"\n" + "!" * 70)
        print(f"  ★【政變成功·主客易位】！")
        print(f"  {p.name} 亮出偽造的逮捕手令與官印，守衛倒戈！")
        print(f"  舊城主【{target_lord_name}】被秘密軟禁押入地牢！{p.name} 正式入主城主府奪取大權！")
        print("!" * 70)

    return ActionSuite(
        suite_id="suite_conspiracy_coup",
        name="暗中發動政變",
        category="conspiracy",
        steps=[
            SubAction("深夜刺探城防換班漏洞", ap_cost=2),
            SubAction("密會並巨資收買北門親衛隊長", ap_cost=3),
            SubAction("偽造長老院彈劾手令與假印信", ap_cost=2),
            SubAction("帶領死士突入內堡逼宮奪取領主官印", ap_cost=3)
        ],
        repeatable=False,
        on_complete=on_complete
    )


# ==============================================================================
# 實機演練與驗證
# ==============================================================================

def run_simulation():
    print("=" * 75)
    print("   日常時段排程、行動事件組 (10 AP/時段) 與性格驅動政變模擬")
    print("=" * 75)

    # 1. 驗證情境一：勤勉商人 vs 極度懶散商人
    print("\n【情境一：性格驅動商業事件組 (勤勉 vs. 極度懶散)】")
    diligent_merchant = Person("m1", "勤勉商人·漢斯", traits=["小店商人", "勤勉"], gold=100.0)
    diligent_merchant.active_suites.append(make_shop_suite())

    lazy_merchant = Person("m2", "極度懶散商人·托比", traits=["小店商人", "極度懶散"], gold=100.0)
    lazy_merchant.active_suites.append(make_shop_suite())

    # 模擬早晨時段
    diligent_merchant.act_slot(TimeSlot.MORNING)
    lazy_merchant.act_slot(TimeSlot.MORNING)

    # 2. 驗證情境二：主角暗中篡改詞條，操縱忠誠副官發動政變
    print("\n" + "=" * 75)
    print("【情境二：主角本質篡改干涉 —— 忠誠副官的暗中政變】")
    officer = Person("officer_albert", "守備副官·艾伯特", traits=["親衛副官", "忠厚本分"], gold=50.0)
    
    # 初始掛載守備職責
    officer.active_suites.append(make_patrol_suite())
    
    print(f"\n[第 1 天] 初始狀態: {officer.name} 擁有詞條: {officer.traits}")
    print("當前城主：阿爾諾子爵（貪婪殘暴，但艾伯特忠厚本分）")
    
    # 第 1 天早晨與午後：艾伯特正常執行巡邏
    officer.act_slot(TimeSlot.MORNING)
    officer.act_slot(TimeSlot.AFTERNOON)

    # -------------------------------------------------------------------------
    # 主角介入：覺醒者夜訪
    # -------------------------------------------------------------------------
    print("\n" + "-" * 75)
    print("【深夜時刻：主角（覺醒者）使用本質干涉】")
    print("主角消耗精神力，悄悄對熟睡中的艾伯特進行本質篡改：")
    print("  [-] 剝離詞條: 「忠厚本分」")
    print("  [+] 刻印詞條: 「野心家」 (對權力產生無盡渴望)")
    print("  [+] 刻印詞條: 「暗中欠債」 (被地下賭場逼債，急需奪權自保)")
    
    officer.remove_trait("忠厚本分")
    officer.add_trait("野心家")
    officer.add_trait("暗中欠債")
    
    # 被動/情境解鎖「暗中發動政變」事件組
    coup = make_coup_suite(target_lord_name="阿爾諾子爵")
    officer.active_suites.append(coup)
    
    print(f"艾伯特新詞條矩陣: {officer.traits}")
    print(f"艾伯特意識深處解鎖事件組: 【{coup.name}】(共需 {coup.total_ap_cost} AP)")
    print("-" * 75)

    # -------------------------------------------------------------------------
    # 第 2 天：艾伯特的性格效用 AI 全面倒向政變！
    # -------------------------------------------------------------------------
    print("\n[第 2 天] 艾伯特的 Utility AI 決策徹底翻轉：")
    patrol_score = officer.evaluate_utility(officer.active_suites[0])
    coup_score = officer.evaluate_utility(officer.active_suites[1])
    print(f"  * 「日常城防巡邏」動機評分: {patrol_score:.1f}")
    print(f"  * 「暗中發動政變」動機評分: {coup_score:.1f} (壓倒性勝出！)")

    # 第 2 天早晨：執行前兩步驟 (刺探 2 AP + 收買 3 AP = 5 AP)
    officer.act_slot(TimeSlot.MORNING)

    # 第 2 天午後：執行後兩步驟 (偽造 2 AP + 逼宮 3 AP = 5 AP) 完成政變！
    officer.act_slot(TimeSlot.AFTERNOON)


if __name__ == "__main__":
    run_simulation()
