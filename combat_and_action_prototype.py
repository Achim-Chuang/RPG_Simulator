"""
Action Checks, Personal Combat & Army Battle Prototype
Demonstrates:
1. Regular actions auto-succeed; Challenging actions use Base 50% +/- 5% per modifier.
2. Personal Combat: Attacker pays 1 AP, Defender pays 0 AP; continuous rounds until 4 end conditions:
   - Condition 1: All on one side incapacitated/dead/retreated
   - Condition 2: Surrender (morale/hp check, traits like Cowardly vs. Fearless)
   - Condition 3: Special Awakening / Trait intervention
   - Condition 4: Narrative event interruption
3. Army Combat: Entering battle consumes the current TimeSlot (remaining AP -> 0).
   Each combat round progresses a full TimeSlot (e.g., Morning -> Afternoon).
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import random


# ==============================================================================
# 1. 行動檢定引擎 (Action Check Engine)
# ==============================================================================

class ActionCheckEngine:
    @staticmethod
    def execute_action(action_name: str, is_challenging: bool = False, modifiers: Optional[Dict[str, int]] = None, seed: Optional[int] = None) -> Tuple[bool, str]:
        """
        常規行動：自動 100% 成功
        挑戰型行動：基準 50%，每點修正增加或減少 5%
        """
        if not is_challenging:
            return True, f"【常規行動·自動成功】「{action_name}」無需投骰，穩步達成。"

        if seed is not None:
            random.seed(seed)

        base_rate = 0.50
        mod_sum = 0
        details = []

        if modifiers:
            for reason, val in modifiers.items():
                mod_sum += val
                pct = val * 5
                sign = "+" if pct >= 0 else ""
                details.append(f"{reason} ({sign}{pct}%)")

        final_rate = max(0.05, min(0.95, base_rate + (mod_sum * 0.05)))
        roll = random.random()
        success = roll <= final_rate

        detail_str = "、".join(details) if details else "無額外修正"
        log = (
            f"【挑戰行動檢定】「{action_name}」\n"
            f"  - 基準成功率: 50%\n"
            f"  - 因果修正項: {detail_str} (淨修正: {mod_sum * 5:+d}%)\n"
            f"  - 最終判定機率: {final_rate * 100:.1f}%\n"
            f"  - 投骰結果: {roll * 100:.1f}% -> {'【★ 檢定成功】' if success else '【✗ 檢定失敗】'}"
        )
        return success, log


# ==============================================================================
# 2. 個人戰鬥引擎 (Personal Combat Engine)
# ==============================================================================

class CombatantStatus(Enum):
    ACTIVE = "作戰中"
    INCAPACITATED = "失能昏迷"
    RETREATED = "撤退脫離"
    SURRENDERED = "主動投降"
    DEAD = "戰死"


@dataclass
class Combatant:
    id: str
    name: str
    side: str  # "A" (主角方) 或 "B" (敵對方)
    hp: int
    max_hp: int
    atk: int
    defense: int
    spd: int
    traits: List[str] = field(default_factory=list)
    status: CombatantStatus = CombatantStatus.ACTIVE

    @property
    def is_active(self) -> bool:
        return self.status == CombatantStatus.ACTIVE

    @property
    def surrender_threshold(self) -> float:
        """投降血量閾值：預設 25%，無所畏懼者永不投降，怯懦者 50% 就投降"""
        if "無所畏懼" in self.traits:
            return 0.0
        if "怯懦" in self.traits:
            return 0.50
        return 0.25


class PersonalCombatEngine:
    @staticmethod
    def run_combat(
        side_a: List[Combatant],
        side_b: List[Combatant],
        attacker_side: str = "A",
        attacker_ap: int = 10,
        special_intervention_round: Optional[int] = None,
        plot_event_round: Optional[int] = None
    ) -> Tuple[str, int]:
        """
        執行個人戰鬥循環：
        - 主動方消耗 1 AP，守方消耗 0 AP
        - 輪流依速度出手，直至達成四類終止條件
        """
        print("\n" + "=" * 70)
        print("                【個人戰鬥打響 (Personal Combat)】")
        print("=" * 70)

        # 1. AP 結算
        if attacker_side == "A":
            attacker_ap -= 1
            print(f"[AP消耗] 主動發起方 (Side A) 消耗 1 AP 投入戰鬥！(剩餘 AP: {attacker_ap})")
            print(f"[AP保護] 被動迎戰方 (Side B) 作為守方，消耗 0 AP！")
        else:
            print(f"[AP消耗] 敵方 (Side B) 主動突襲，我方 (Side A) 迎戰消耗 0 AP！(維持 AP: {attacker_ap})")

        round_num = 1
        combat_ended = False
        termination_reason = ""

        while not combat_ended:
            print(f"\n--- [第 {round_num} 回合交鋒] ---")

            # 檢定終止條件 4：劇情事件強制介入
            if plot_event_round and round_num == plot_event_round:
                termination_reason = "【終止條件 4：劇情事件】長老院治安巡防鐵騎鳴鏑趕到，戰鬥被強制叫停！"
                print(f"  ★ {termination_reason}")
                break

            # 檢定終止條件 3：特殊覺醒者法術/神技干涉
            if special_intervention_round and round_num == special_intervention_round:
                termination_reason = "【終止條件 3：特殊技能】主角釋放『心相威壓·神聖震懾』，全場敵我因果鎖定，戰意全消！"
                print(f"  ★ {termination_reason}")
                break

            # 排定出手順序 (依敏捷 Speed 降序)
            all_fighters = [c for c in side_a + side_b if c.is_active]
            all_fighters.sort(key=lambda x: x.spd, reverse=True)

            for fighter in all_fighters:
                if not fighter.is_active:
                    continue

                # 尋找目標
                enemies = [e for e in (side_b if fighter.side == "A" else side_a) if e.is_active]
                if not enemies:
                    break

                target = random.choice(enemies)
                # 傷害計算: max(1, Atk - Def)
                dmg = max(1, fighter.atk - target.defense)
                target.hp -= dmg
                print(f"  > {fighter.name} 疾速出手，擊中 {target.name}，造成 {dmg} 點傷害！({target.name} HP: {target.hp}/{target.max_hp})")

                # 狀態檢驗
                if target.hp <= 0:
                    target.hp = 0
                    target.status = CombatantStatus.INCAPACITATED
                    print(f"    [失能] {target.name} 遭受重擊倒地不起，失去意識！")
                else:
                    # 檢定終止條件 2：主動投降判定
                    hp_ratio = target.hp / target.max_hp
                    if hp_ratio <= target.surrender_threshold:
                        target.status = CombatantStatus.SURRENDERED
                        print(f"    [投降] {target.name} 負傷過重且意志瓦解，丟下兵器高舉雙手投降！")

            # 檢查各陣營剩餘作戰人員
            active_a = [c for c in side_a if c.is_active]
            active_b = [c for c in side_b if c.is_active]

            # 檢定終止條件 1：一方全員無人能戰
            if not active_a:
                surrendered_count = len([c for c in side_a if c.status == CombatantStatus.SURRENDERED])
                if surrendered_count == len(side_a):
                    termination_reason = "【終止條件 2：集體投降】Side A 全員繳械投降！戰鬥結束！"
                else:
                    termination_reason = "【終止條件 1：全員失能】Side A 全員潰敗失能！Side B 獲勝！"
                combat_ended = True
            elif not active_b:
                surrendered_count = len([c for c in side_b if c.status == CombatantStatus.SURRENDERED])
                if surrendered_count == len(side_b):
                    termination_reason = "【終止條件 2：集體投降】Side B 匪眾無力支撐，全員跪地求饒投降！"
                else:
                    termination_reason = "【終止條件 1：全員倒下】Side B 全員失去戰鬥力！Side A 完勝！"
                combat_ended = True

            round_num += 1

        print("\n" + "=" * 70)
        print(f"戰鬥落幕結算: {termination_reason}")
        print("=" * 70)
        return termination_reason, attacker_ap


# ==============================================================================
# 3. 軍隊戰鬥系統 (Army Combat Engine)
# ==============================================================================

class TimeSlot(Enum):
    MORNING = "早晨"
    AFTERNOON = "午後"
    NIGHT = "夜間"


@dataclass
class Army:
    name: str
    commander: str
    soldiers: int
    max_soldiers: int
    morale: float  # 0.0 ~ 100.0
    commander_traits: List[str] = field(default_factory=list)

    @property
    def is_routed(self) -> bool:
        return self.morale <= 0.0 or self.soldiers <= 0


class ArmyCombatEngine:
    @staticmethod
    def resolve_army_clash(
        attacker: Army,
        defender: Army,
        slot: TimeSlot,
        current_ap_pool: int
    ) -> Tuple[bool, TimeSlot, int]:
        """
        軍隊大戰回合：
        - 進入軍隊戰鬥直接強制結算當前時段（耗盡剩餘 AP）
        - 每個回合即耗費一個完整時段！
        """
        print("\n" + "#" * 70)
        print(f"      【軍團會戰】時段: [{slot.value}] | {attacker.name} VS {defender.name}")
        print("#" * 70)

        # 戰略時間消耗：直接耗盡該時段剩餘全部 AP
        consumed_ap = current_ap_pool
        current_ap_pool = 0
        print(f"[宏觀戰場代價] 萬人大軍列陣開拔，直接耗盡本時段全部剩餘 {consumed_ap} AP！時間轉瞬即逝！")

        # 統帥加成
        att_bonus = 0
        def_bonus = 0
        if "百戰直覺" in attacker.commander_traits:
            att_bonus += 2  # +10%
        if "軍神意志" in attacker.commander_traits:
            att_bonus += 4  # +20%
        if "固若金湯" in defender.commander_traits:
            def_bonus += 3  # +15%

        # 傷亡與士氣計算
        att_loss = int(attacker.soldiers * random.uniform(0.08, 0.15) * (1.0 - def_bonus * 0.05))
        def_loss = int(defender.soldiers * random.uniform(0.12, 0.22) * (1.0 + att_bonus * 0.05))

        attacker.soldiers = max(0, attacker.soldiers - att_loss)
        defender.soldiers = max(0, defender.soldiers - def_loss)

        # 士氣打擊
        morale_hit_att = random.uniform(10.0, 20.0)
        morale_hit_def = random.uniform(25.0, 45.0)

        attacker.morale = max(0.0, attacker.morale - morale_hit_att)
        defender.morale = max(0.0, defender.morale - morale_hit_def)

        print(f"\n[會戰結算 - {slot.value}階段]:")
        print(f"  * {attacker.name} (統帥: {attacker.commander}):")
        print(f"      戰損: -{att_loss} 人 (剩餘: {attacker.soldiers}/{attacker.max_soldiers}) | 當前士氣: {attacker.morale:.1f}/100")
        print(f"  * {defender.name} (統帥: {defender.commander}):")
        print(f"      戰損: -{def_loss} 人 (剩餘: {defender.soldiers}/{defender.max_soldiers}) | 當前士氣: {defender.morale:.1f}/100")

        # 判定勝負
        if defender.is_routed:
            print(f"\n  ★【大捷】敵軍「{defender.name}」陣線全面崩潰，士氣瓦解引發大潰敗！我軍大獲全勝！")
            return True, slot, current_ap_pool
        elif attacker.is_routed:
            print(f"\n  ✗【潰敗】我軍「{attacker.name}」傷亡過重，全軍撤出戰場！")
            return True, slot, current_ap_pool
        else:
            print(f"\n  [僵局] 雙方戰線膠著，殘陽如血，戰鬥將延續至下一個時段！")
            return False, slot, current_ap_pool


# ==============================================================================
# 實機情境演示
# ==============================================================================

def run_simulation():
    print("*" * 75)
    print("      行動檢定規則、個人戰鬥 (4種終結) 與軍隊大戰時段模擬")
    print("*" * 75)

    # -------------------------------------------------------------------------
    # 測試 1：挑戰型行動檢定 (50% 基準 +/- 5%)
    # -------------------------------------------------------------------------
    print("\n【測試 1：常規行動 vs 挑戰型行動檢定】")
    # 常規
    _, log_regular = ActionCheckEngine.execute_action("早市挑選新鮮食材", is_challenging=False)
    print(log_regular)

    # 挑戰：收買城門衛隊官員
    # 基準 50% + 市井算術(+1/+5%) + 天狐媚骨(+4/+20%) + 對方貪婪(+3/+15%) - 對方長官多疑(-2/-10%) = 80%
    modifiers = {
        "主角持有 [市井算術]": +1,
        "主角持有 [天狐媚骨] (Rare魅力)": +4,
        "官員弱點 [貪婪]": +3,
        "城防總管 [多疑盤查]": -2
    }
    _, log_challenging = ActionCheckEngine.execute_action(
        "深夜賄賂北門衛隊放行私貨",
        is_challenging=True,
        modifiers=modifiers,
        seed=42
    )
    print(log_challenging)

    # -------------------------------------------------------------------------
    # 測試 2：個人戰鬥 (主動 1 AP，守方 0 AP，主動投降判定)
    # -------------------------------------------------------------------------
    print("\n" + "-" * 75)
    print("【測試 2：個人戰鬥與終局條件二（主動投降）】")
    hero = Combatant("hero", "覺醒者主角", "A", hp=50, max_hp=50, atk=18, defense=5, spd=12, traits=["百戰直覺"])
    veteran = Combatant("vet", "退役老兵·加拉哈", "A", hp=60, max_hp=60, atk=15, defense=8, spd=10, traits=["無所畏懼"])

    bandit_boss = Combatant("b_boss", "荒野劫匪頭目", "B", hp=40, max_hp=40, atk=12, defense=3, spd=9, traits=["怯懦"])
    bandit_thug = Combatant("b_thug", "劫匪嘍囉", "B", hp=25, max_hp=25, atk=10, defense=2, spd=8, traits=[])

    # 主角主動發起戰鬥，起始 10 AP
    PersonalCombatEngine.run_combat(
        side_a=[hero, veteran],
        side_b=[bandit_boss, bandit_thug],
        attacker_side="A",
        attacker_ap=10
    )

    # -------------------------------------------------------------------------
    # 測試 3：軍隊大戰 (時段耗盡與跨時段戰役)
    # -------------------------------------------------------------------------
    print("\n" + "-" * 75)
    print("【測試 3：軍團大戰 —— 時段直接結束，戰鬥以時段為回合】")
    rebel_legion = Army(
        name="北方叛軍第一軍團",
        commander="叛將·雷恩",
        soldiers=1200,
        max_soldiers=1200,
        morale=80.0,
        commander_traits=[]
    )
    frost_legion = Army(
        name="北境霜狼近衛軍",
        commander="老兵將軍·加拉哈",
        soldiers=1000,
        max_soldiers=1000,
        morale=95.0,
        commander_traits=["百戰直覺", "軍神意志"]
    )

    slots_sequence = [TimeSlot.MORNING, TimeSlot.AFTERNOON, TimeSlot.NIGHT]
    slot_idx = 0
    current_ap = 8  # 假設早上已經做了點雜事剩 8 AP

    print(f"\n[會戰爆發] 霜狼近衛軍在【{slots_sequence[slot_idx].value}】遭遇叛軍主力！")

    while slot_idx < len(slots_sequence):
        slot = slots_sequence[slot_idx]
        ended, _, current_ap = ArmyCombatEngine.resolve_army_clash(
            attacker=frost_legion,
            defender=rebel_legion,
            slot=slot,
            current_ap_pool=current_ap
        )
        print(f"[{slot.value}結束] 該時段 AP 已全數耗盡 (剩餘: {current_ap})")
        if ended:
            break
        slot_idx += 1
        if slot_idx < len(slots_sequence):
            current_ap = 10
            print(f"\n[戰役延續] 烽火連天，戰事推進至【{slots_sequence[slot_idx].value}】！")


if __name__ == "__main__":
    run_simulation()
