"""
WorldState container: encapsulates Calendar, Characters, Organizations, Social Network, and Traits.
"""

from typing import Dict, List, Optional, Any
from ..core.traits import Trait, Tier, Category
from ..core.character import Character
from ..core.social import SocialNetwork
from ..core.organization import OrgManager, Organization
from ..core.calendar import WorldCalendar, TimeSlot
from ..core.map import WorldMap
from ..core.ruins import RuinSite
from ..core.economy import MerchantCaravan
from ..core.lifecycle import LifeCycleEngine


class WorldState:
    def __init__(self):
        self.trait_registry: Dict[str, Trait] = {}
        self.profession_registry: Dict[str, Dict[str, Any]] = {}
        self.lifecycle_engine: LifeCycleEngine = LifeCycleEngine()
        self.calendar: WorldCalendar = WorldCalendar()
        self.characters: Dict[str, Character] = {}
        self.social_network: SocialNetwork = SocialNetwork()
        self.org_manager: OrgManager = OrgManager(self.social_network)
        self.world_map: WorldMap = WorldMap()
        self.ruins_sites: List[RuinSite] = []
        self.caravans: List[MerchantCaravan] = []
        self.event_logs: List[str] = []

    def register_profession(self, prof_data: Dict[str, Any]):
        p_id = prof_data.get("id")
        if p_id:
            self.profession_registry[p_id] = prof_data

    def get_profession(self, prof_id: str) -> Optional[Dict[str, Any]]:
        return self.profession_registry.get(prof_id)

    def register_trait(self, trait: Trait):
        self.trait_registry[trait.id] = trait

    def get_trait(self, trait_id: str, character: Optional[Character] = None) -> Optional[Trait]:
        """查找詞條，優先自角色專屬自創庫查找，若無則查找全域詞條庫"""
        if character and trait_id in character.custom_traits:
            return character.custom_traits[trait_id]
        if trait_id in self.trait_registry:
            return self.trait_registry[trait_id]
        for c in self.characters.values():
            if trait_id in c.custom_traits:
                return c.custom_traits[trait_id]
        return None

    def add_character(self, character: Character):
        self.characters[character.char_id] = character

    def get_character(self, char_id: str) -> Optional[Character]:
        return self.characters.get(char_id)

    def execute_interaction(self, interaction_id: str, actor_id: str, target_id: str, **kwargs) -> Any:
        """執行角色間的互動動作 (串接 InteractionRegistry)"""
        from ..core.interactions import InteractionRegistry, InteractionResult
        actor = self.get_character(actor_id)
        target = self.get_character(target_id)
        if not actor or not target:
            return InteractionResult(success=False, message="執行失敗：角色不存在！")

        act = InteractionRegistry.get(interaction_id)
        if not act:
            return InteractionResult(success=False, message=f"未找到互動動作 ID「{interaction_id}」！")

        result = act.execute(actor, target, self, **kwargs)
        if result.success:
            self.event_logs.append(result.message)
        return result

    def advance_time_slot(self) -> List[str]:
        curr_slot = self.calendar.current_slot

        # 1. 驅動社會中各職業 NPC 執行當前時段日常排程管線 (Routine Pipelines)
        routine_logs = self.lifecycle_engine.execute_slot_routines(self)

        # 2. 推進時段 (結算 AP 與休息恢復)
        logs = self.calendar.advance_slot(list(self.characters.values()))
        logs.extend(routine_logs)

        # 3. 跨日結算 (晨曦破曉時觸發實體經濟與生命週期演進)
        if self.calendar.current_slot == TimeSlot.MORNING and curr_slot == TimeSlot.NIGHT:
            # 每日實體經濟循環
            econ_logs = self.run_daily_economic_cycle()
            logs.extend(econ_logs)

            # 每日社會生態與生命週期演進 (交友、結婚、懷孕、生育、世襲)
            life_logs = self.lifecycle_engine.run_daily_lifecycle(self)
            logs.extend(life_logs)

        self.event_logs.extend(logs)
        return logs

    def run_daily_economic_cycle(self) -> List[str]:
        logs = [f"【經濟運轉】第 {self.calendar.current_day} 天實體產業與城鎮供需結算開始："]
        
        # 1. 節點作坊生產與人口每日消耗
        for node in self.world_map.nodes.values():
            if node.market:
                ws_logs = node.market.execute_workshops()
                cons_logs = node.market.consume_daily()
                logs.extend([f"[{node.name}] {l}" for l in ws_logs if "停擺" in l or "產出" in l])
                logs.extend([f"[{node.name}] {l}" for l in cons_logs])
                
        # 2. 車隊行進與抵達貿易結算
        for caravan in self.caravans:
            if caravan.status == "TRAVELING":
                moved, move_msg = caravan.step_travel()
                logs.append(move_msg)
                if caravan.status == "ARRIVED" and caravan.current_node_id:
                    curr_node = self.world_map.get_node(caravan.current_node_id)
                    if curr_node and curr_node.market:
                        for cid, amt in list(caravan.cargo.items()):
                            succ, qty, payout, smsg = curr_node.market.sell_to_market(cid, amt)
                            if succ:
                                caravan.unload_cargo(cid, qty)
                                caravan.gold += payout
                                logs.append(f"【商隊貿易】{caravan.name} 在 [{curr_node.name}] 卸貨結算：{smsg}")
        return logs

    def run_monthly_economy(self) -> List[str]:
        logs = self.org_manager.monthly_economic_tick()
        self.event_logs.extend(logs)
        return logs

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": "1.0",
            "calendar": self.calendar.to_dict(),
            "professions": list(self.profession_registry.values()),
            "traits": [t.to_dict() for t in self.trait_registry.values()],
            "characters": [c.to_dict() for c in self.characters.values()],
            "social_network": self.social_network.to_dict(),
            "organizations": self.org_manager.to_dict(),
            "world_map": self.world_map.to_dict(),
            "ruins": [r.to_dict() for r in self.ruins_sites],
            "caravans": [c.to_dict() for c in self.caravans],
            "event_logs": self.event_logs[-100:]  # 保留最近 100 條世界歷史日誌
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorldState':
        world = cls()

        # 1. 恢復日曆
        world.calendar = WorldCalendar.from_dict(data["calendar"])

        # 1.5 恢復職業庫
        for p_data in data.get("professions", []):
            world.register_profession(p_data)

        # 2. 恢復詞條註冊庫
        for t_data in data.get("traits", []):
            trait = Trait.from_dict(t_data)
            world.register_trait(trait)
            
        # 3. 恢復社交圖譜
        world.social_network = SocialNetwork.from_dict(data.get("social_network", []))
        
        # 4. 恢復角色 (綁定詞條註冊庫)
        for c_data in data.get("characters", []):
            char = Character.from_dict(c_data, world.trait_registry)
            world.add_character(char)
            
        # 5. 恢復組織架構
        world.org_manager = OrgManager.from_dict(data.get("organizations", []), world.social_network)

        # 6. 恢復世界地圖
        if "world_map" in data:
            world.world_map = WorldMap.from_dict(data["world_map"])

        # 7. 恢復遺跡點位
        for r_data in data.get("ruins", []):
            world.ruins_sites.append(RuinSite.from_dict(r_data))
        
        # 8. 恢復行商車隊
        for c_data in data.get("caravans", []):
            world.caravans.append(MerchantCaravan.from_dict(c_data))

        # 9. 歷史日誌
        world.event_logs = data.get("event_logs", [])
        
        return world

