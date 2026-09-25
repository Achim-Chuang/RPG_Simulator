"""
Travel Engine: Handles node-based movement, AP consumption, and dynamic travel encounters
(Bandit Ambush, Caravan Meeting, Weather Hazard, Wandering Hermits, Peaceful Travel).
"""

from enum import Enum
from typing import Tuple, List, Optional, Any
import random
from .character import Character
from .map import WorldMap, MapNode, MapEdge, RoadType
from .combat import Combatant, PersonalCombatEngine
from .actions import ActionCheckEngine


class TravelEncounterType(Enum):
    PEACEFUL = "平安順暢"
    BANDIT_AMBUSH = "荒野劫匪伏擊"
    CARAVAN_MEET = "邂逅流動商隊"
    WEATHER_HAZARD = "極端天候阻路"
    WANDERING_HERMIT = "偶遇隱世高人"


class TravelEngine:
    @staticmethod
    def travel_to_node(
        world_map: WorldMap,
        traveler: Character,
        target_node_id: str,
        seed: Optional[int] = None
    ) -> Tuple[bool, str, List[str]]:
        """
        角色沿相連邊移動至目標節點：
        - 檢查鄰接與連通性
        - 扣除道路 AP 代價
        - 依道路危險度與角色詞條判定旅途動態遭遇
        """
        if seed is not None:
            random.seed(seed)

        logs = []
        curr_node_id = traveler.current_location_id
        curr_node = world_map.get_node(curr_node_id)
        target_node = world_map.get_node(target_node_id)

        if not curr_node or not target_node:
            return False, "INVALID_NODE", [f"錯誤：起點或終點節點無效 ({curr_node_id} -> {target_node_id})。"]

        edge = world_map.get_edge(curr_node_id, target_node_id)
        if not edge:
            return False, "NO_PATH", [f"無直達道路：無法從「{curr_node.name}」直接步行至「{target_node.name}」！"]

        if traveler.current_ap < edge.ap_cost:
            return False, "NO_AP", [f"行動力不足：前往「{target_node.name}」需 {edge.ap_cost} AP，但 {traveler.name} 僅剩 {traveler.current_ap} AP！"]

        # 扣除 AP 並更新位置
        traveler.current_ap -= edge.ap_cost
        traveler.current_location_id = target_node_id

        logs.append(
            f"【啟程行路】{traveler.name} 沿著【{edge.road_type.value}】從「{curr_node.name}」出發，"
            f"前往「{target_node.name}」 (消耗 {edge.ap_cost} AP，剩餘 {traveler.current_ap} AP)。"
        )

        # ---------------------------------------------------------------------
        # 旅途遭遇判定
        # ---------------------------------------------------------------------
        trait_names = [t.name for t in traveler.innate_traits + traveler.acquired_traits + traveler.imprinted_traits]
        
        # 遭遇率修正
        danger = edge.danger_rating
        if "商隊護衛經驗" in trait_names:
            danger = max(0.05, danger - 0.15)
        if "夜巡直覺" in trait_names:
            danger = max(0.05, danger - 0.10)

        encounter_roll = random.random()

        if encounter_roll > danger:
            # 平安無事
            logs.append(f"  [平穩行旅] 沿途天朗氣清，商旅行人絡繹不絕。{traveler.name} 平安抵達「{target_node.name}」。")
            return True, TravelEncounterType.PEACEFUL.name, logs

        # 觸發非平穩動態遭遇 (Ambush 45%, Caravan 25%, Weather 20%, Hermit 10%)
        sub_roll = random.random()

        if sub_roll < 0.45:
            # 1. 劫匪伏擊
            logs.append("  [警報·劫匪攔路] 路旁草叢傳來破空呼嘯！數名荒原流寇拔出鋼刀攔住去路！")
            bandit = Combatant(
                id="road_bandit",
                name="攔路路匪首領",
                side="B",
                hp=35,
                max_hp=35,
                atk=13,
                defense=3,
                spd=9,
                traits=["怯懦"]
            )
            hero_fighter = Combatant(
                id=traveler.char_id,
                name=traveler.name,
                side="A",
                hp=50,
                max_hp=50,
                atk=18,
                defense=6,
                spd=11
            )
            reason, _, combat_logs = PersonalCombatEngine.run_combat(
                side_a=[hero_fighter],
                side_b=[bandit],
                attacker_side="B",  # 敵方突襲，我方守方不扣額外AP
                attacker_ap=traveler.current_ap
            )
            logs.extend(combat_logs)
            if hero_fighter.is_active:
                logs.append(f"  ★ 戰鬥勝利！{traveler.name} 掃清障礙，成功抵達「{target_node.name}」！")
                return True, TravelEncounterType.BANDIT_AMBUSH.name, logs
            else:
                logs.append(f"  ✗ 旅途受創！{traveler.name} 負傷突出重圍，狼狽逃入「{target_node.name}」。")
                return True, TravelEncounterType.BANDIT_AMBUSH.name, logs

        elif sub_roll < 0.70:
            # 2. 邂逅流動商隊
            logs.append("  [奇遇·流動商隊] 荒野驛道旁，你偶遇一支來自遠方海灣的重裝貨運駱駝商隊。")
            logs.append("  商隊首領熱情地向你兜售特產，並分享了最近各勢力領地的物價浮動情報。")
            traveler.gold += 15.0  # 順手倒賣微量特產小賺一筆
            logs.append(f"  ★ 隨車隊同行一段路程，順手協助理貨獲得微薄報酬 +15.0 金！順利抵達「{target_node.name}」。")
            return True, TravelEncounterType.CARAVAN_MEET.name, logs

        elif sub_roll < 0.90:
            # 3. 極端天候阻路
            hazard_name = "荒野暴風狂砂" if edge.road_type == RoadType.TRAIL else "深山驟降暴雪"
            logs.append(f"  [險阻·極端天候] 突遭【{hazard_name}】！天地間視線不足三步，寒風如刀！")
            if "荒原游牧血統" in trait_names:
                logs.append(f"  ★ {traveler.name} 憑藉「荒原游牧血統」，熟練地拉緊防風兜帽辨識方位，安然穿過風暴！")
            else:
                logs.append(f"  風沙撲面，體力加速流失。{traveler.name} 咬牙頂風前行，終於踉蹌走出險境。")
            return True, TravelEncounterType.WEATHER_HAZARD.name, logs

        else:
            # 4. 偶遇隱世高人
            logs.append("  [奇遇·隱世高人] 在道旁廢棄的界碑涼亭下，一位衣衫襤褸的老僧正閉目冥想。")
            logs.append(f"  他睜開雙眼打量著 {traveler.name}，似笑非笑地提點了兩句呼吸吐納之法。")
            traveler.interaction_count += 1
            logs.append(f"  ★ 心有所悟！{traveler.name} 精神力微量拓寬，從容邁入「{target_node.name}」。")
            return True, TravelEncounterType.WANDERING_HERMIT.name, logs
