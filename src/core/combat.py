"""
Personal Combat and Army Battles.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
import random
from .calendar import TimeSlot


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
    side: str
    hp: int
    max_hp: int
    atk: int
    defense: int
    spd: int
    shield: int = 0
    max_shield: int = 0
    cover: float = 0.0          # 掩體防禦比例 (0.0 無掩體, 0.3 半身掩體, 0.5 堅固掩體)
    armor_penetration: int = 0  # 破甲穿透值 (無視目標多少 defense)
    is_ranged: bool = False     # 是否為遠程交火武裝
    traits: List[str] = field(default_factory=list)
    status: CombatantStatus = CombatantStatus.ACTIVE

    @property
    def is_active(self) -> bool:
        return self.status == CombatantStatus.ACTIVE

    @property
    def surrender_threshold(self) -> float:
        if "無所畏懼" in self.traits:
            return 0.0
        if "怯懦" in self.traits:
            return 0.50
        return 0.25

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "side": self.side,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "atk": self.atk,
            "defense": self.defense,
            "spd": self.spd,
            "shield": self.shield,
            "max_shield": self.max_shield,
            "cover": self.cover,
            "armor_penetration": self.armor_penetration,
            "is_ranged": self.is_ranged,
            "traits": self.traits,
            "status": self.status.name
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Combatant':
        return cls(
            id=data["id"],
            name=data["name"],
            side=data["side"],
            hp=data["hp"],
            max_hp=data["max_hp"],
            atk=data["atk"],
            defense=data["defense"],
            spd=data["spd"],
            shield=data.get("shield", 0),
            max_shield=data.get("max_shield", 0),
            cover=float(data.get("cover", 0.0)),
            armor_penetration=data.get("armor_penetration", 0),
            is_ranged=data.get("is_ranged", False),
            traits=data.get("traits", []),
            status=CombatantStatus[data.get("status", "ACTIVE")]
        )


class PersonalCombatEngine:
    @staticmethod
    def run_combat(
        side_a: List[Combatant],
        side_b: List[Combatant],
        attacker_side: str = "A",
        attacker_ap: int = 10,
        special_intervention_round: Optional[int] = None,
        plot_event_round: Optional[int] = None
    ) -> Tuple[str, int, List[str]]:
        logs = []
        logs.append("【個人戰鬥打響 (Personal Combat)】")

        if attacker_side == "A":
            attacker_ap -= 1
            logs.append(f"[AP消耗] 主動發起方 (Side A) 消耗 1 AP (剩餘 AP: {attacker_ap})；守方 (Side B) 消耗 0 AP！")
        else:
            logs.append(f"[AP保護] 敵方 (Side B) 主動突襲，我方 (Side A) 迎戰消耗 0 AP (維持 AP: {attacker_ap})！")

        round_num = 1
        combat_ended = False
        termination_reason = ""

        while not combat_ended:
            if plot_event_round and round_num == plot_event_round:
                termination_reason = "【終止條件 4：劇情事件】長老院治安鐵騎鳴鏑趕到，戰鬥被強制叫停！"
                break

            if special_intervention_round and round_num == special_intervention_round:
                termination_reason = "【終止條件 3：特殊技能】主角釋放『神聖震懾』，全場因果鎖定，戰意全消！"
                break

            all_fighters = [c for c in side_a + side_b if c.is_active]
            all_fighters.sort(key=lambda x: x.spd, reverse=True)

            for fighter in all_fighters:
                if not fighter.is_active:
                    continue

                enemies = [e for e in (side_b if fighter.side == "A" else side_a) if e.is_active]
                if not enemies:
                    break

                target = random.choice(enemies)

                # 1. 破甲穿透計算 (Armor Penetration)
                effective_def = max(0, target.defense - fighter.armor_penetration)
                base_dmg = max(1, fighter.atk - effective_def)

                # 2. 掩體防禦偏折 (Cover Mitigation against ranged attacks)
                if fighter.is_ranged and target.cover > 0:
                    cover_red = int(round(base_dmg * target.cover))
                    dmg = max(1, base_dmg - cover_red)
                    logs.append(f"  > [掩體工事] {target.name} 藉掩體工事阻截偏折火力，吸收 {cover_red} 傷害！")
                else:
                    dmg = base_dmg

                # 3. 虛空盾 / 能量護盾吸收 (Shield Absorption before HP damage)
                dmg_to_hp = dmg
                if target.shield > 0:
                    if dmg <= target.shield:
                        target.shield -= dmg
                        dmg_to_hp = 0
                        logs.append(f"  > {fighter.name} 命中 {target.name}！【護盾吸收】虛空偏轉盾全額吸收 {dmg} 傷害 (護盾剩餘: {target.shield}/{target.max_shield})")
                    else:
                        absorbed = target.shield
                        dmg_to_hp = dmg - target.shield
                        target.shield = 0
                        logs.append(f"  > {fighter.name} 命中 {target.name}！【破盾過載擊穿】虛空護盾過載崩解！吸收 {absorbed} 點，溢出 {dmg_to_hp} 傷害穿透本體！")
                else:
                    weapon_tag = "【遠程齊射】" if fighter.is_ranged else "【近戰猛擊】"
                    ap_tag = f" (破甲穿透 {fighter.armor_penetration})" if fighter.armor_penetration > 0 else ""
                    logs.append(f"  > {fighter.name} {weapon_tag} 擊中 {target.name}{ap_tag}，造成 {dmg_to_hp} 傷害 ({target.name} HP: {max(0, target.hp - dmg_to_hp)}/{target.max_hp})")

                if dmg_to_hp > 0:
                    target.hp -= dmg_to_hp

                if target.hp <= 0:
                    target.hp = 0
                    target.status = CombatantStatus.INCAPACITATED
                    logs.append(f"    [失能] {target.name} 倒地失去意識！")
                else:
                    hp_ratio = target.hp / target.max_hp
                    if hp_ratio <= target.surrender_threshold:
                        target.status = CombatantStatus.SURRENDERED
                        logs.append(f"    [投降] {target.name} 負傷意志崩潰，高舉雙手投降！")

            active_a = [c for c in side_a if c.is_active]
            active_b = [c for c in side_b if c.is_active]

            if not active_a:
                surrendered = len([c for c in side_a if c.status == CombatantStatus.SURRENDERED])
                termination_reason = "【終止條件 2：集體投降】Side A 全員投降！" if surrendered == len(side_a) else "【終止條件 1：全員失能】Side A 全員倒下！"
                combat_ended = True
            elif not active_b:
                surrendered = len([c for c in side_b if c.status == CombatantStatus.SURRENDERED])
                termination_reason = "【終止條件 2：集體投降】Side B 匪眾全員求饒投降！" if surrendered == len(side_b) else "【終止條件 1：全員倒下】Side B 全員失去戰鬥力！Side A 獲勝！"
                combat_ended = True

            round_num += 1

        logs.append(f"戰鬥落幕: {termination_reason}")
        return termination_reason, attacker_ap, logs


@dataclass
class Army:
    name: str
    commander: str
    soldiers: int
    max_soldiers: int
    morale: float
    commander_traits: List[str] = field(default_factory=list)

    @property
    def is_routed(self) -> bool:
        return self.morale <= 0.0 or self.soldiers <= 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "commander": self.commander,
            "soldiers": self.soldiers,
            "max_soldiers": self.max_soldiers,
            "morale": self.morale,
            "commander_traits": self.commander_traits
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Army':
        return cls(
            name=data["name"],
            commander=data["commander"],
            soldiers=data["soldiers"],
            max_soldiers=data["max_soldiers"],
            morale=data["morale"],
            commander_traits=data.get("commander_traits", [])
        )


class ArmyCombatEngine:
    @staticmethod
    def resolve_army_clash(
        attacker: Army,
        defender: Army,
        slot: TimeSlot,
        current_ap_pool: int
    ) -> Tuple[bool, int, List[str]]:
        logs = []
        logs.append(f"【軍團大戰】時段: [{slot.value}] | {attacker.name} VS {defender.name}")
        logs.append(f"[宏觀戰場代價] 戰事爆發，直接耗盡本時段剩餘 {current_ap_pool} AP！")
        current_ap_pool = 0

        att_bonus = (2 if "百戰直覺" in attacker.commander_traits else 0) + (4 if "軍神意志" in attacker.commander_traits else 0)
        def_bonus = 3 if "固若金湯" in defender.commander_traits else 0

        att_loss = int(attacker.soldiers * random.uniform(0.08, 0.15) * (1.0 - def_bonus * 0.05))
        def_loss = int(defender.soldiers * random.uniform(0.12, 0.22) * (1.0 + att_bonus * 0.05))

        attacker.soldiers = max(0, attacker.soldiers - att_loss)
        defender.soldiers = max(0, defender.soldiers - def_loss)

        attacker.morale = max(0.0, attacker.morale - random.uniform(10.0, 20.0))
        defender.morale = max(0.0, defender.morale - random.uniform(25.0, 45.0))

        logs.append(f"  * {attacker.name}: 戰損 -{att_loss} (剩餘 {attacker.soldiers}/{attacker.max_soldiers}) | 士氣: {attacker.morale:.1f}")
        logs.append(f"  * {defender.name}: 戰損 -{def_loss} (剩餘 {defender.soldiers}/{defender.max_soldiers}) | 士氣: {defender.morale:.1f}")

        if defender.is_routed:
            logs.append(f"  ★【大捷】敵軍「{defender.name}」陣線潰敗，我軍大獲全勝！")
            return True, current_ap_pool, logs
        elif attacker.is_routed:
            logs.append(f"  ✗【潰敗】我軍「{attacker.name}」全線潰退！")
            return True, current_ap_pool, logs
        else:
            logs.append("  [膠著] 雙方暫時收兵，戰事延續至下一個時段！")
            return False, current_ap_pool, logs
