"""
Scalable Procedural World Generator.
Generates Free City, surrounding Independent Factions, Ruins, and starting organizations
based on player scale configuration (Small / Standard / Epic).
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import random
import math
from ..core.organization import Organization, OrgTier
from ..core.character import Character
from ..core.ruins import RuinSite, RuinBiome
from ..core.map import WorldMap, MapNode, NodeType, RoadType
from ..core.economy import STANDARD_RECIPES, Workshop, MerchantCaravan
from ..engine.world import WorldState
from ..engine.def_loader import DefDatabase



class WorldScale(Enum):
    SMALL = "小型世界 (1城邦+2勢力, 4遺跡, 上限15組織)"
    STANDARD = "標準世界 (1城邦+4勢力, 8遺跡, 上限30組織)"
    EPIC = "史詩世界 (1城邦+8勢力, 16遺跡, 上限60組織)"

    @property
    def config(self) -> Dict[str, int]:
        if self == WorldScale.SMALL:
            return {"factions": 2, "ruins": 4, "max_orgs": 15}
        elif self == WorldScale.STANDARD:
            return {"factions": 4, "ruins": 8, "max_orgs": 30}
        else:
            return {"factions": 8, "ruins": 16, "max_orgs": 60}


@dataclass
class WorldGenSettings:
    scale: WorldScale = WorldScale.STANDARD
    free_city_name: str = "自由城邦·奧斯提亞"
    seed: Optional[int] = None
    custom_factions: Optional[int] = None
    custom_ruins: Optional[int] = None


FACTION_PRESETS = [
    ("org_iron_duchy", "鐵血騎士大公國", "獅鷲要塞城", 2500.0, 15000.0, "大公·雷德蒙德"),
    ("org_forest_elves", "翠林精靈隱邦", "晨曦聖樹之庭", 2000.0, 18000.0, "長老·阿爾溫"),
    ("org_desert_caliphate", "黃金大漠汗國", "太陽綠洲王都", 2200.0, 16000.0, "蘇丹·阿卜杜勒"),
    ("org_daoist_sect", "雲隱九天道盟", "太虛浮空洞府", 3000.0, 20000.0, "宗主·清虛道君"),
    ("org_tundra_mechanists", "永凍鋼鐵先祖遺民", "零號古代地下城", 1800.0, 22000.0, "總工長·維克托"),
    ("org_pirate_confederacy", "自由群島海盜聯邦", "浪湧走私自由港", 1500.0, 9000.0, "提督·黑鬍子"),
    ("org_steppe_horde", "碎骨狼族游牧汗國", "萬狼奔騰大帳", 1600.0, 8000.0, "大汗·拔都"),
    ("org_holy_theocracy", "晨光神聖審判教國", "聖火光明大教堂", 3500.0, 25000.0, "教宗·英諾森十世")
]

RUIN_NAME_POOLS = {
    RuinBiome.WASTELAND: ["崩解的黑曜石祭壇", "焦土舊王朝地宮", "風蝕巨石柱群", "前代超凡者荒塚"],
    RuinBiome.FOREST: ["古木纏繞的月神殿", "精靈失落古都秘庫", "盤根錯節的祭祀之井", "翡翠林地下回廊"],
    RuinBiome.TUNDRA: ["冰封鋼鐵先祖第七地堡", "極光永凍星艦殘骸", "深霜機械冷卻核心", "萬年冰核觀象台"],
    RuinBiome.DESERT: ["流沙掩埋的黃金金字塔", "法老冥河墓道", "狂風迷城日晷台", "古代鍊金方尖碑"]
}


class WorldGenerator:
    @staticmethod
    def generate(settings: WorldGenSettings, def_db: DefDatabase) -> WorldState:
        if settings.seed is not None:
            random.seed(settings.seed)

        cfg = settings.scale.config
        faction_count = settings.custom_factions if settings.custom_factions is not None else cfg["factions"]
        ruins_count = settings.custom_ruins if settings.custom_ruins is not None else cfg["ruins"]

        world = WorldState()
        wmap = WorldMap()

        # 1. 注入詞條庫
        for t in def_db.trait_defs.values():
            world.register_trait(t)

        # 2. 建立自由城邦（核心中樞）
        free_city = Organization(
            org_id="org_free_city",
            name=settings.free_city_name,
            tier=OrgTier.INDEPENDENT,
            leader_id="npc_consul",
            fief_name="奧斯提亞海灣城",
            fief_monthly_income=4000.0,
            treasury=30000.0
        )
        world.org_manager.all_orgs[free_city.org_id] = free_city

        # 地圖節點：自由城邦
        free_city_node = MapNode(
            node_id="node_free_city",
            name=settings.free_city_name,
            node_type=NodeType.CITY,
            coords=(0, 0),
            fief_or_org_id=free_city.org_id
        )
        if free_city_node.market:
            free_city_node.market.inventory = {
                "raw_grain": 25,
                "good_bread": 50,
                "good_weapons": 25,
                "good_medicine": 15,
                "spec_ostia_vintage": 12
            }
            free_city_node.market.target_stock = {
                "raw_grain": 40,
                "good_bread": 60,
                "good_weapons": 30,
                "good_medicine": 20,
                "spec_ostia_vintage": 15
            }
            free_city_node.market.daily_consumption = {
                "good_bread": 8,
                "good_medicine": 1
            }
            free_city_node.market.workshops.extend([
                Workshop("ws_free_city_bakery", "城邦市民大烘焙坊", STANDARD_RECIPES["recipe_bakery"], daily_batches=4),
                Workshop("ws_free_city_winery", "海灣烈焰皇家釀酒莊園", STANDARD_RECIPES["recipe_winery"], daily_batches=1)
            ])
        wmap.add_node(free_city_node)

        # 3. 建立城邦商會（救助主角的組織）與商會驛站節點
        caravan_guild = Organization(
            org_id="org_caravan_guild",
            name="北方開拓商隊會社",
            tier=OrgTier.LARGE,
            leader_id="npc_caravan_thomas",
            treasury=3500.0,
            parent_id="org_free_city"
        )
        world.org_manager.all_orgs[caravan_guild.org_id] = caravan_guild
        free_city.sub_org_ids.append(caravan_guild.org_id)

        station_node = MapNode(
            node_id="node_caravan_station",
            name="城郊·商會驛站",
            node_type=NodeType.TOWN,
            coords=(1, 0),
            fief_or_org_id=caravan_guild.org_id
        )
        if station_node.market:
            station_node.market.inventory = {
                "raw_grain": 90,
                "raw_timber": 30,
                "good_bread": 20
            }
            station_node.market.target_stock = {
                "raw_grain": 70,
                "raw_timber": 25,
                "good_bread": 15
            }
            station_node.market.daily_consumption = {
                "good_bread": 2
            }
            station_node.market.workshops.extend([
                Workshop("ws_caravan_farm", "商會墾殖大農莊", STANDARD_RECIPES["recipe_grain_farm"], daily_batches=2),
                Workshop("ws_caravan_lumber", "邊境密林伐木場", STANDARD_RECIPES["recipe_lumberyard"], daily_batches=1)
            ])
        wmap.add_node(station_node)
        wmap.add_edge("node_free_city", "node_caravan_station", RoadType.HIGHWAY)

        # 4. 生成隨機獨立勢力與周邊商貿道路
        chosen_presets = random.sample(FACTION_PRESETS, min(faction_count, len(FACTION_PRESETS)))
        waypoint_node_ids = []

        for idx, (fid, fname, fief, income, treas, leader) in enumerate(chosen_presets):
            fac = Organization(
                org_id=fid,
                name=fname,
                tier=OrgTier.INDEPENDENT,
                leader_id=f"npc_leader_{fid}",
                fief_name=fief,
                fief_monthly_income=income,
                treasury=treas
            )
            world.org_manager.all_orgs[fac.org_id] = fac

            # 環形座標分佈
            angle = (2 * math.pi * idx) / len(chosen_presets)
            fx = int(round(math.cos(angle) * 12))
            fy = int(round(math.sin(angle) * 12))
            wx = int(round(fx // 2))
            wy = int(round(fy // 2))

            node_fac_id = f"node_{fid}"
            node_way_id = f"node_waypoint_{fid}"
            waypoint_node_ids.append(node_way_id)

            fac_node = MapNode(node_fac_id, fname, NodeType.CITY, coords=(fx, fy), fief_or_org_id=fid)
            if fac_node.market:
                if fid == "org_iron_duchy":
                    fac_node.market.inventory = {"raw_iron_ore": 60, "raw_timber": 20, "good_weapons": 40, "spec_damascus_steel": 8, "good_bread": 25}
                    fac_node.market.target_stock = {"raw_iron_ore": 50, "raw_timber": 20, "good_weapons": 30, "spec_damascus_steel": 10, "good_bread": 25}
                    fac_node.market.daily_consumption = {"good_bread": 3}
                    fac_node.market.workshops.extend([
                        Workshop(f"ws_{fid}_mine", f"{fname}鐵礦山脈", STANDARD_RECIPES["recipe_iron_mine"], daily_batches=3),
                        Workshop(f"ws_{fid}_smith", f"{fname}皇家軍工鍛造所", STANDARD_RECIPES["recipe_blacksmith"], daily_batches=3),
                        Workshop(f"ws_{fid}_damascus", f"{fname}秘傳大馬士革鍛爐", STANDARD_RECIPES["recipe_damascus_forge"], daily_batches=1)
                    ])
                elif fid == "org_forest_elves":
                    fac_node.market.inventory = {"raw_herbs": 50, "raw_timber": 40, "good_medicine": 30, "good_bread": 20}
                    fac_node.market.target_stock = {"raw_herbs": 40, "raw_timber": 30, "good_medicine": 20, "good_bread": 20}
                    fac_node.market.daily_consumption = {"good_bread": 2}
                    fac_node.market.workshops.extend([
                        Workshop(f"ws_{fid}_herbs", f"{fname}神聖草藥圃", STANDARD_RECIPES["recipe_herb_garden"], daily_batches=3),
                        Workshop(f"ws_{fid}_apothecary", f"{fname}精靈秘藥研磨坊", STANDARD_RECIPES["recipe_apothecary"], daily_batches=2)
                    ])
                else:
                    fac_node.market.inventory = {"raw_grain": 40, "good_bread": 20, "raw_timber": 20}
                    fac_node.market.target_stock = {"raw_grain": 35, "good_bread": 20, "raw_timber": 15}
                    fac_node.market.daily_consumption = {"good_bread": 2}
                    fac_node.market.workshops.extend([
                        Workshop(f"ws_{fid}_farm", f"{fname}領地農墾所", STANDARD_RECIPES["recipe_grain_farm"], daily_batches=1),
                        Workshop(f"ws_{fid}_bakery", f"{fname}烘焙房", STANDARD_RECIPES["recipe_bakery"], daily_batches=2)
                    ])
            wmap.add_node(fac_node)

            way_node = MapNode(node_way_id, f"商道中繼·第{idx+1}荒野驛站", NodeType.OUTPOST, coords=(wx, wy))
            if way_node.market:
                way_node.market.inventory = {"good_bread": 10, "raw_grain": 10}
                way_node.market.target_stock = {"good_bread": 10, "raw_grain": 10}
                way_node.market.daily_consumption = {"good_bread": 1}
            wmap.add_node(way_node)

            # 連接：城邦 <-> 中繼驛站 (官道) <-> 王國首都 (官道/小徑)
            wmap.add_edge("node_free_city", node_way_id, RoadType.HIGHWAY)
            wmap.add_edge(node_way_id, node_fac_id, RoadType.HIGHWAY)

        # 5. 隨機生成遺跡站點並連接至荒野網絡
        loot_keys = list(world.trait_registry.keys())
        biomes_list = list(RuinBiome)
        ruins_sites: List[RuinSite] = []

        for i in range(ruins_count):
            biome = biomes_list[i % len(biomes_list)]
            preset_names = RUIN_NAME_POOLS[biome]
            base_name = preset_names[i % len(preset_names)]
            danger = random.randint(1, 5)

            loot_samples = random.sample(loot_keys, min(3, len(loot_keys))) if loot_keys else []
            ruin_id = f"ruin_{i+1:02d}"
            ruin = RuinSite(
                ruin_id=ruin_id,
                name=f"{base_name}·第{i+1}區",
                biome=biome,
                danger_level=danger,
                possible_loot=loot_samples
            )
            ruins_sites.append(ruin)

            # 遺跡地圖節點
            nearest_way_id = waypoint_node_ids[i % len(waypoint_node_ids)]
            way_node = wmap.get_node(nearest_way_id)
            rx = way_node.coords[0] + random.choice([-3, 3, -4, 4])
            ry = way_node.coords[1] + random.choice([-3, 3, -4, 4])

            node_ruin_id = f"node_{ruin_id}"
            wmap.add_node(MapNode(
                node_id=node_ruin_id,
                name=ruin.name,
                node_type=NodeType.RUIN,
                coords=(rx, ry),
                ruin_id=ruin_id
            ))
            road = RoadType.TRAIL if danger <= 3 else RoadType.DANGEROUS_PATH
            wmap.add_edge(nearest_way_id, node_ruin_id, road)

        # 6. 生成主角（荒野甦醒，發燒被商隊救起安置於商會驛站）
        hero = Character(
            char_id="player_hero",
            name="無名少年 (主角)",
            rank_key="Chorji",
            is_awakened=True,
            gold=20.0,
            current_location_id="node_caravan_station"
        )
        if "reg_human_body" in world.trait_registry:
            hero.innate_traits.append(world.trait_registry["reg_human_body"])
        world.add_character(hero)

        # 7. 生成救助主角的商隊首領 NPC
        caravan_master = Character(
            char_id="npc_caravan_thomas",
            name="商隊首領·托馬斯",
            rank_key="Chorji",
            is_awakened=False,
            gold=300.0,
            current_location_id="node_caravan_station"
        )
        if "reg_street_smart" in world.trait_registry:
            caravan_master.acquired_traits.append(world.trait_registry["reg_street_smart"])
        world.add_character(caravan_master)

        # 8. 建立救命之恩關係
        world.social_network.modify("npc_caravan_thomas", "player_hero", d_aff=40.0, d_resp=10.0, d_ob=0.0)
        world.social_network.modify("player_hero", "npc_caravan_thomas", d_aff=50.0, d_resp=20.0, d_ob=50.0)

        # 9. 建立商會初始行商車隊（托馬斯商會先遣隊）
        caravan = MerchantCaravan(
            caravan_id="caravan_thomas_01",
            name="商會先遣糧秣車隊",
            owner_id="npc_caravan_thomas",
            current_node_id="node_caravan_station",
            cargo={"raw_grain": 40},
            gold=800.0,
            capacity=150,
            status="IDLE"
        )
        world.caravans.append(caravan)

        world.world_map = wmap
        world.ruins_sites = ruins_sites

        world.event_logs.append(
            f"【世界生成完畢】規模: {settings.scale.name} | 地圖節點: {len(wmap.nodes)} 個 | "
            f"道路連線: {len(wmap.edges)//2} 條 | 獨立勢力: {len(chosen_presets)} | 遺跡: {len(ruins_sites)}"
        )

        return world

