"""
LifeCycle & Daily Routine Simulation Engine.
Implements:
1. Daily Routine Pipelines across Morning, Afternoon, and Night for all professions.
2. Interpersonal Relationship Dynamics (automatic social bonding, rivalries).
3. Courtship and Marriage (pair-bonding, household funds).
4. Pregnancy, Childbirth, and Genetic Trait Inheritance (generating new characters).
5. Aging, Succession, and Legacy.
"""

import uuid
import random
from typing import Dict, List, Optional, Tuple, Any
from .character import Character
from .traits import Trait, Tier, Category
from .social import SocialNetwork, Relationship
from .organization import Organization, Office, Authority
from .calendar import TimeSlot


CHILD_MALE_NAMES = ["亞倫", "索爾", "雷恩", "修伊", "凱恩", "安德", "艾爾文", "洛克", "雷諾", "泰倫"]
CHILD_FEMALE_NAMES = ["莉莉亞", "艾拉", "塞拉", "艾蓮娜", "薇薇安", "克萊兒", "卡蜜拉", "希爾達", "艾米麗"]


class LifeCycleEngine:
    """
    社會生態與生命週期演進引擎 (Life Cycle & Routine Orchestrator)
    """

    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed) if seed is not None else random.Random()

    # ==========================================================================
    # 1. 職業日常排程執行 (Slot Routine Pipelines)
    # ==========================================================================

    def execute_slot_routines(self, world_state: Any) -> List[str]:
        """
        根據當前時段 (早晨/午後/夜間)，驅動世界中所有活著的 NPC 執行職業排程
        """
        logs = []
        curr_slot: TimeSlot = world_state.calendar.current_slot
        slot_key = curr_slot.name.lower()  # "morning", "afternoon", "night"

        # 依地點將角色分組，便利於夜間同地社交
        characters_by_node: Dict[str, List[Character]] = {}
        for char in list(world_state.characters.values()):
            if not char.is_alive:
                continue
            loc = char.current_location_id or "node_free_city"
            characters_by_node.setdefault(loc, []).append(char)

        for char in list(world_state.characters.values()):
            if not char.is_alive or char.current_ap <= 0:
                continue
            
            # 取得職業定義 (若無則使用預設平民冒險者)
            prof_data = world_state.get_profession(char.profession_id) if hasattr(world_state, "get_profession") else None
            routine = None
            if prof_data and "routines" in prof_data and slot_key in prof_data["routines"]:
                routine = prof_data["routines"][slot_key]

            # 預設行為
            if not routine:
                if curr_slot == TimeSlot.MORNING:
                    routine = {"action_name": "日常晨間勞作", "ap_cost": 6, "action_type": "produce_craft"}
                elif curr_slot == TimeSlot.AFTERNOON:
                    routine = {"action_name": "市集與工坊穿梭", "ap_cost": 6, "action_type": "market_trade"}
                else:
                    routine = {"action_name": "酒館夜間聚首", "ap_cost": 5, "action_type": "tavern_social"}

            ap_cost = min(char.current_ap, routine.get("ap_cost", 5))
            action_type = routine.get("action_type", "home_rest")
            act_name = routine.get("action_name", "公務")
            char.current_ap -= ap_cost

            # 執行具體行為邏輯
            if action_type in ("produce_craft", "inventory_audit"):
                wage = prof_data.get("base_daily_wage", 15.0) * 0.4 if prof_data else 5.0
                char.gold += wage
                # 若當地節點有市場，注入微量商品庫存
                node = world_state.world_map.get_node(char.current_location_id) if hasattr(world_state, "world_map") else None
                if node and node.market and "tools" in node.market.inventory:
                    node.market.inventory["tools"] += 1.0

            elif action_type in ("market_trade", "trade_profit"):
                profit = prof_data.get("base_daily_wage", 25.0) * 0.6 if prof_data else 8.0
                char.gold += profit

            elif action_type in ("patrol_security", "gate_duty"):
                # 巡邏壓制混亂度
                pass

            elif action_type in ("tavern_social", "banquet_social", "salon_social"):
                # 在同一地點隨機挑選另一人進行社交增進感情
                peers = [p for p in characters_by_node.get(char.current_location_id, []) if p.char_id != char.char_id]
                if peers:
                    target = self.rng.choice(peers)
                    d_aff = self.rng.uniform(3.0, 7.0)
                    d_resp = self.rng.uniform(1.0, 4.0)
                    world_state.social_network.modify(target.char_id, char.char_id, d_aff=d_aff, d_resp=d_resp)
                    world_state.social_network.modify(char.char_id, target.char_id, d_aff=d_aff, d_resp=d_resp)

            elif action_type == "home_rest":
                char.rest_accumulated += ap_cost

        return logs

    # ==========================================================================
    # 2. 每日跨日生命週期演進 (Daily LifeCycle Progression)
    # ==========================================================================

    def run_daily_lifecycle(self, world_state: Any) -> List[str]:
        """
        每日凌晨觸發：
        1. 撮合未婚青年談戀愛與結婚 (Courtship & Marriage)
        2. 懷孕檢定與新生命誕生 (Pregnancy & Childbirth)
        3. 衰老、壽終與世襲繼承 (Aging, Mortality & Succession)
        """
        logs = []

        # 1. 婚姻撮合
        marriage_logs = self.process_courtship_and_marriage(world_state)
        logs.extend(marriage_logs)

        # 2. 生育與嬰兒生成
        birth_logs = self.process_pregnancy_and_childbirth(world_state)
        logs.extend(birth_logs)

        # 3. 衰老與自然傳承
        aging_logs = self.process_aging_and_succession(world_state)
        logs.extend(aging_logs)

        return logs

    # ==========================================================================
    # 3. 求愛與婚姻機制 (Courtship & Marriage)
    # ==========================================================================

    def process_courtship_and_marriage(self, world_state: Any) -> List[str]:
        logs = []
        unmarried_chars = [c for c in world_state.characters.values() if c.is_alive and not c.spouse_id and c.age >= 16]
        
        # 按地點篩選
        by_node: Dict[str, List[Character]] = {}
        for c in unmarried_chars:
            by_node.setdefault(c.current_location_id, []).append(c)

        for loc_id, pool in by_node.items():
            if len(pool) < 2:
                continue

            for i in range(len(pool)):
                c1 = pool[i]
                if c1.spouse_id:
                    continue

                for j in range(i + 1, len(pool)):
                    c2 = pool[j]
                    if c2.spouse_id:
                        continue
                    
                    # 性別互補 (簡易婚姻規則，可擴充)
                    if c1.gender == c2.gender:
                        continue

                    # 檢定雙向情感
                    r12 = world_state.social_network.get_relationship(c1.char_id, c2.char_id)
                    r21 = world_state.social_network.get_relationship(c2.char_id, c1.char_id)

                    # 門檻：雙方好感度 >= 50 且 合作意願 >= 40
                    if r12.affection >= 45.0 and r21.affection >= 45.0 and r12.willingness >= 35.0 and r21.willingness >= 35.0:
                        # 締結婚姻！
                        c1.spouse_id = c2.char_id
                        c2.spouse_id = c1.char_id

                        # 合併 30% 財產為家庭共同基金
                        dowry = round((c1.gold + c2.gold) * 0.15, 1)
                        c1.gold += dowry * 0.5
                        c2.gold += dowry * 0.5

                        # 雙方好感鎖定在極高值
                        world_state.social_network.modify(c1.char_id, c2.char_id, d_aff=30.0, d_resp=20.0, d_ob=30.0)
                        world_state.social_network.modify(c2.char_id, c1.char_id, d_aff=30.0, d_resp=20.0, d_ob=30.0)

                        loc_node = world_state.world_map.get_node(loc_id) if hasattr(world_state, "world_map") else None
                        loc_name = loc_node.name if loc_node else loc_id
                        logs.append(f"【良緣締結】{c1.name} 與 {c2.name} 互生情愫、喜結連理！於 [{loc_name}] 正式成婚！")
                        break

        return logs

    # ==========================================================================
    # 4. 生育與新生兒本質遺傳 (Pregnancy & Childbirth)
    # ==========================================================================

    def process_pregnancy_and_childbirth(self, world_state: Any) -> List[str]:
        logs = []
        female_chars = [c for c in world_state.characters.values() if c.is_alive and c.gender == "female" and c.spouse_id]

        for mom in female_chars:
            dad = world_state.get_character(mom.spouse_id)
            if not dad or not dad.is_alive:
                continue

            # 1. 懷孕受孕判定
            if mom.pregnancy_timer == 0:
                # 同一地點且夫妻感情好時，每日有 20% 機率受孕 (測試模擬速率)
                if mom.current_location_id == dad.current_location_id:
                    rel = world_state.social_network.get_relationship(mom.char_id, dad.char_id)
                    if rel.affection >= 50.0 and self.rng.random() < 0.25:
                        mom.pregnancy_timer = 2  # 2 天孕期
                        mom.pregnancy_partner_id = dad.char_id
                        logs.append(f"【胎息有兆】{mom.name} 感受到了生命的律動，懷上了與 {dad.name} 的骨肉！")

            # 2. 孕期倒數與生產
            elif mom.pregnancy_timer > 0:
                mom.pregnancy_timer -= 1
                if mom.pregnancy_timer <= 0:
                    # 嬰兒誕生！
                    baby_gender = "male" if self.rng.random() < 0.5 else "female"
                    baby_first_name = self.rng.choice(CHILD_MALE_NAMES if baby_gender == "male" else CHILD_FEMALE_NAMES)
                    
                    # 提取父親/家族姓氏前綴
                    dad_prefix = dad.name.split("·")[0] if "·" in dad.name else dad.name[:2]
                    baby_full_name = f"{dad_prefix}氏·{baby_first_name}"
                    
                    baby_id = f"char_{uuid.uuid4().hex[:8]}"
                    baby = Character(
                        char_id=baby_id,
                        name=baby_full_name,
                        rank_key="Chorji",
                        is_awakened=False,
                        gold=10.0,
                        current_location_id=mom.current_location_id
                    )
                    baby.gender = baby_gender
                    baby.age = 0
                    baby.parent_ids = [dad.char_id, mom.char_id]
                    baby.profession_id = "prof_artisan"

                    # 繼承父母遺傳 (Genetic Trait Inheritance)
                    inherited_traits: List[Trait] = []
                    
                    # 從父親繼承先天詞條 (50% 機率)
                    for t in dad.innate_traits:
                        if self.rng.random() < 0.50 and t not in inherited_traits:
                            inherited_traits.append(t)
                    
                    # 從母親繼承先天詞條 (50% 機率)
                    for t in mom.innate_traits:
                        if self.rng.random() < 0.50 and t not in inherited_traits:
                            inherited_traits.append(t)

                    # 若父母皆無先天詞條，給予標準常態之軀
                    if not inherited_traits and "reg_human_body" in world_state.trait_registry:
                        inherited_traits.append(world_state.trait_registry["reg_human_body"])

                    baby.innate_traits.extend(inherited_traits)

                    # 覺醒天賦遺傳：若父母任一方是覺醒者，有 40% 機率天生覺醒
                    if dad.is_awakened or mom.is_awakened:
                        if self.rng.random() < 0.40:
                            baby.is_awakened = True

                    # 父母子女雙向建立最高親情連結
                    mom.children_ids.append(baby.char_id)
                    dad.children_ids.append(baby.char_id)
                    world_state.social_network.modify(mom.char_id, baby.char_id, d_aff=80.0, d_resp=10.0, d_ob=60.0)
                    world_state.social_network.modify(dad.char_id, baby.char_id, d_aff=80.0, d_resp=10.0, d_ob=60.0)
                    world_state.social_network.modify(baby.char_id, mom.char_id, d_aff=80.0, d_resp=50.0, d_ob=50.0)
                    world_state.social_network.modify(baby.char_id, dad.char_id, d_aff=80.0, d_resp=50.0, d_ob=50.0)

                    # 加入世界狀態
                    world_state.add_character(baby)
                    mom.pregnancy_partner_id = None

                    trait_names = [t.name for t in baby.innate_traits]
                    awakened_str = "【天生覺醒者！】" if baby.is_awakened else ""
                    logs.append(
                        f"【麟兒誕生】{mom.name} 順利誕下一名健康的{'男嬰' if baby_gender == 'male' else '女嬰'}「{baby.name}」！\n"
                        f"  --> {awakened_str}遺傳雙親血脈稟賦: {trait_names}。"
                    )

        return logs

    # ==========================================================================
    # 5. 衰老、逝世與官職世襲 (Aging, Mortality & Succession)
    # ==========================================================================

    def process_aging_and_succession(self, world_state: Any) -> List[str]:
        logs = []
        for char in list(world_state.characters.values()):
            if not char.is_alive:
                continue

            # 年齡增長 (每 30 天算長一歲)
            if world_state.calendar.current_day % 30 == 0:
                char.age += 1

            # 壽終正寢檢定 (若超過 75 歲，每日有微小機率自然逝世)
            if char.age >= 75 and char.rank_key != "Transcendent":
                if self.rng.random() < 0.05:
                    death_log = self.handle_character_death(char, world_state, cause="壽終正寢")
                    logs.append(death_log)

        return logs

    def handle_character_death(self, char: Character, world_state: Any, cause: str = "戰死") -> str:
        """
        處理角色死亡、遺產繼承與官職世襲
        """
        char.is_alive = False
        logs = [f"【星落殞滅】{char.name}（享年 {char.age} 歲）不幸{cause}，舉國哀悼！"]

        # 1. 遺產繼承：若有配偶或子女，全數金幣遺留給第一繼承人
        heir: Optional[Character] = None
        if char.spouse_id:
            heir = world_state.get_character(char.spouse_id)
        if not heir and char.children_ids:
            heir = world_state.get_character(char.children_ids[0])

        if heir and char.gold > 0:
            heir.gold += char.gold
            logs.append(f"  - 遺產交接：遺留的 {char.gold:.1f} 枚金幣全數由繼承人「{heir.name}」繼承。")
            char.gold = 0.0

        # 2. 官職懸缺與世襲：若其在組織中握有 Office，優先由其成年子女世襲，否則退為懸缺
        for org in world_state.org_manager.all_orgs.values():
            for off in org.offices.values():
                if off.incumbent_id == char.char_id:
                    # 尋找具備世襲資格的成年子女
                    eligible_children = [
                        world_state.get_character(cid)
                        for cid in char.children_ids
                        if world_state.get_character(cid) and world_state.get_character(cid).is_alive and world_state.get_character(cid).age >= 16
                    ]
                    if eligible_children:
                        successor = eligible_children[0]
                        org.appoint_office(off.office_id, successor.char_id)
                        logs.append(f"  - 【血脈世襲】「{off.title}」之職由其長子/長女「{successor.name}」正式承襲！")
                    else:
                        org.vacate_office(off.office_id)
                        logs.append(f"  - 【職位懸缺】「{off.title}」目前無合法繼承人，暫時懸缺由領袖代管！")

        return "\n".join(logs)
