"""
Comprehensive Verification Suite for Multiverse Framework Adaptability:
1. Star Map & Thematic Node/Route Rendering (Fantasy vs Sci-Fi)
2. Advanced Combat: Ranged Firefight, Cover Deflection, Void Shield Absorption, and Armor Penetration
3. Morality & Corruption Axis (Soul Taint, Inquisitorial Purge Trigger)
4. Def Loader Multi-IP Expansion (Warhammer 40k & Star Wars mods)
5. Save/Load Persistence of Multiverse State
"""

import os
import json
from src.core.map import WorldMap, MapNode, MapEdge, NodeType, RoadType, WorldTheme
from src.core.combat import Combatant, CombatantStatus, PersonalCombatEngine
from src.core.traits import Trait, Tier, Category
from src.core.character import Character, CorruptionState
from src.engine.world import WorldState
from src.engine.def_loader import DefDatabase, DefLoader
from src.engine.save_load import SaveLoadManager


def test_star_map_thematic_abstraction():
    print("=" * 65)
    print("【測試 1】星圖拓撲抽象層：中世紀奇幻 <-> 星際科幻太空主題動態適配")
    print("=" * 65)

    # 1. 建立戰鎚 40K / 星戰風格的星圖
    space_map = WorldMap(theme=WorldTheme.SCI_FI)

    # 核心行星、軌道防禦空間站、失落太空廢船
    hive_world = MapNode(
        node_id="sys_armageddon",
        name="阿米吉多頓·巢都首星",
        node_type=NodeType.CITY,
        orbital_type="Hive World",
        theme_label="超級工業巢都行星 (Hive World)"
    )
    forge_station = MapNode(
        node_id="station_forge_01",
        name="極限第零號鑄造空間站",
        node_type=NodeType.OUTPOST,
        orbital_type="Orbital Station"
    )
    space_hulk = MapNode(
        node_id="hulk_sin_of_damnation",
        name="罪惡之譴號·太空巨石廢船",
        node_type=NodeType.RUIN,
        orbital_type="Space Hulk"
    )

    space_map.add_node(hive_world)
    space_map.add_node(forge_station)
    space_map.add_node(space_hulk)

    # 連接航道：超空間巡邏跳躍線與危險亞空間風暴裂隙
    space_map.add_edge(
        "sys_armageddon", "station_forge_01",
        road_type=RoadType.HIGHWAY,
        theme_label="曼德維爾常規跳躍航線",
        warp_instability=0.05
    )
    space_map.add_edge(
        "station_forge_01", "hulk_sin_of_damnation",
        road_type=RoadType.DANGEROUS_PATH,
        theme_label="恐虐撕裂者亞空間風暴走廊",
        warp_instability=0.75
    )

    # 檢驗科幻主題標籤解析
    hive_label = space_map.get_node_label(hive_world)
    station_label = space_map.get_node_label(forge_station)
    print(f"節點 1: {hive_world.name} -> 主題類型: [{hive_label}]")
    print(f"節點 2: {forge_station.name} -> 主題類型: [{station_label}]")

    assert "Hive World" in hive_label
    assert "Orbital Station" in station_label or "軌道防禦空間站" in station_label

    edge_storm = space_map.get_edge("station_forge_01", "hulk_sin_of_damnation")
    edge_label = space_map.get_edge_label(edge_storm)
    print(f"航道連線: [{edge_label}] | 亞空間風暴危險度: {edge_storm.warp_instability*100}%")
    assert edge_storm.warp_instability == 0.75

    # 導航尋路
    path = space_map.find_path("sys_armageddon", "hulk_sin_of_damnation")
    print(f"星圖跨星系導航路徑: {' -> '.join(path)}")
    assert path == ["sys_armageddon", "station_forge_01", "hulk_sin_of_damnation"]
    print("✓ 星圖主題切換、星體節點與亞空間危險航道拓撲運算完全正常！")


def test_combat_firefight_cover_shield_and_ap():
    print("\n" + "=" * 65)
    print("【測試 2】遠程火力駁火、掩體工事偏折、虛空護盾吸收與破甲穿透")
    print("=" * 65)

    # 1. 測試虛空盾全額吸傷
    paladin = Combatant(
        id="c_paladin",
        name="阿斯塔特禁衛·加雷斯",
        side="A",
        hp=200,
        max_hp=200,
        atk=30,
        defense=25,
        spd=15,
        shield=50,
        max_shield=50,
        cover=0.0
    )

    cultist = Combatant(
        id="c_cultist",
        name="混沌信徒射手",
        side="B",
        hp=50,
        max_hp=50,
        atk=40,
        defense=5,
        spd=10,
        is_ranged=True,
        armor_penetration=0
    )

    # 混沌信徒射擊：atk 40 vs def 25 -> 傷害 15。
    # 加雷斯有 50 虛空盾，應全額吸收，加雷斯 HP 依然維持 200/200，護盾剩餘 35！
    _, _, logs = PersonalCombatEngine.run_combat([paladin], [cultist], attacker_side="B")
    
    shield_absorb_logged = any("【護盾吸收】" in l for l in logs)
    print(f"加雷斯戰後狀態: HP {paladin.hp}/{paladin.max_hp} | 虛空盾: {paladin.shield}/{paladin.max_shield}")
    assert shield_absorb_logged is True, "應觸發【護盾吸收】"
    assert paladin.hp == 200, "護盾未破前，HP 應當毫髮無損"
    assert paladin.shield < 50, "護盾能量應被消耗"
    print("✓ 虛空盾全額吸收動能傷害驗證成功！")

    # 2. 測試破盾過載擊穿 (Shield Overload Break)
    heavy_gunner = Combatant(
        id="c_gunner",
        name="帝國熱熔重裝兵",
        side="A",
        hp=100,
        max_hp=100,
        atk=90,
        defense=10,
        spd=20,
        is_ranged=True,
        armor_penetration=20  # 熱熔破甲 20
    )
    shielded_boss = Combatant(
        id="c_boss",
        name="叛變星際戰士士官",
        side="B",
        hp=120,
        max_hp=120,
        atk=35,
        defense=20,
        spd=10,
        shield=30,
        max_shield=30,
        cover=0.0
    )

    # 熱熔兵攻擊：atk 90 vs def (20 - 20 = 0) -> raw dmg 90
    # Boss shield 30 < 90 -> 破盾，溢出 60 傷害直接打擊 Boss HP (120 - 60 = 60)
    _, _, logs2 = PersonalCombatEngine.run_combat([heavy_gunner], [shielded_boss], attacker_side="A")
    break_logged = any("【破盾過載擊穿】" in l for l in logs2)
    print(f"Boss 遭受熱熔轟擊後: HP {shielded_boss.hp}/{shielded_boss.max_hp} | 虛空盾: {shielded_boss.shield}/{shielded_boss.max_shield}")
    assert break_logged is True, "應觸發【破盾過載擊穿】"
    assert shielded_boss.shield == 0, "護盾應當被徹底過載瓦解"
    print("✓ 破盾過載擊穿與熱熔破甲穿透本體驗證成功！")

    # 3. 測試掩體偏折減傷 (Cover Mitigation)
    sniper = Combatant("c_snip", "克里格狙擊手", "A", 80, 80, atk=60, defense=10, spd=25, is_ranged=True)
    in_cover_soldier = Combatant("c_cov", "掩體內戰壕守軍", "B", 100, 100, atk=20, defense=10, spd=10, cover=0.5)

    _, _, logs3 = PersonalCombatEngine.run_combat([sniper], [in_cover_soldier], attacker_side="A")
    cover_logged = any("掩體工事" in l for l in logs3)
    assert cover_logged is True, "遠程射擊面對掩體應觸發掩體工事偏折"
    print("✓ 掩體工事對遠程火力的吸收偏折驗證成功！")


def test_morality_and_corruption_axis():
    print("\n" + "=" * 65)
    print("【測試 3】道德與靈魂腐化計量條：混沌侵蝕、西斯黑暗面與審判庭絕罰")
    print("=" * 65)

    hero = Character(
        char_id="hero_psyker_01",
        name="強大靈能者·瓦倫",
        rank_key="Nomenkhan",
        is_awakened=True
    )

    # 初始狀態：純淨聖潔
    init_state, init_desc = hero.get_corruption_state()
    print(f"初始靈魂狀態: {init_state.value} ({hero.corruption}/100.0) - {init_desc}")
    assert init_state == CorruptionState.SANCTIFIED
    assert hero.corruption == 0.0

    # 1. 刻印禁忌亞空間靈能閃電 (+15 腐化)
    warp_lightning = Trait(
        id="wh_warp_lightning",
        name="亞空間靈能閃電",
        category=Category.ACQUIRED,
        tier=Tier.RARE,
        description="撕裂物質界帷幕引導毀滅雷霆",
        corruption_delta=15.0
    )
    succ, log1 = hero.imprint_trait(hero, warp_lightning)
    print(log1)
    assert succ is True
    assert hero.corruption == 15.0
    assert hero.get_corruption_state()[0] == CorruptionState.SANCTIFIED

    # 2. 裝備恐虐嗜血魔刃 (+35 腐化) -> 總計 50 腐化
    daemon_blade = Trait(
        id="wh_daemon_blade",
        name="恐虐嗜血魔刃",
        category=Category.ARTIFACT,
        tier=Tier.MYSTIC,
        description="封印亞空間惡魔之刃",
        corruption_delta=35.0
    )
    succ2, log2 = hero.imprint_trait(hero, daemon_blade)
    print(log2)
    assert succ2 is True
    assert hero.corruption == 50.0
    assert hero.get_corruption_state()[0] == CorruptionState.TEMPTED

    # 3. 施展惡魔獻祭儀式 (+35 腐化) -> 累積達 85 腐化 (超過 80 觸發深淵魔宿與全域絕罰！)
    c_alert = hero.modify_corruption(35.0, reason="獻祭巢都平民呼喚亞空間實體")
    print(c_alert)
    curr_state, curr_desc = hero.get_corruption_state()
    print(f"當前靈魂狀態: {curr_state.value} ({hero.corruption}/100.0)")
    assert curr_state == CorruptionState.ABOMINATION
    assert "審判庭全域異端絕罰追殺令" in c_alert
    print("✓ 墮入深淵魔宿並湧現審判庭全域清洗絕罰！")

    # 4. 佩戴審判官純潔符印進行聖潔淨化 (-25 腐化)
    inquisitor_seal = Trait(
        id="wh_inquisitor_rosette",
        name="審判官純潔符印",
        category=Category.ARTIFACT,
        tier=Tier.MYSTIC,
        description="帝皇之名鐫刻的神聖信物",
        corruption_delta=-25.0
    )
    succ3, log3 = hero.imprint_trait(hero, inquisitor_seal)
    print(log3)
    assert hero.corruption == 60.0
    assert hero.get_corruption_state()[0] == CorruptionState.CORRUPTED
    print("✓ 聖潔洗滌淨化機制生效！")


def test_def_loader_multi_ip_expansion():
    print("\n" + "=" * 65)
    print("【測試 4】外部 Def 載入器：戰鎚 40K 與星戰 Mod 外部無縫掛載")
    print("=" * 65)

    db = DefDatabase()
    loader = DefLoader(db)
    load_logs = loader.load_all_defs("defs")

    print(f"成功掃描 defs/ 目錄，共執行 {len(load_logs)} 項載入。")

    # 檢查戰鎚 40K 詞條
    astartes_organs = db.get_trait("wh_astartes_organs")
    assert astartes_organs is not None, "阿斯塔特器官詞條應成功載入"
    assert astartes_organs.tier == Tier.RARE
    assert astartes_organs.modifiers.get("atk") == 25
    print(f"✓ 戰鎚 40K 詞條已載入: 【{astartes_organs.tier}】{astartes_organs.name}")

    # 檢查星戰詞條
    beskar_armor = db.get_trait("sw_beskar_armor")
    assert beskar_armor is not None, "曼達洛貝斯卡裝甲應成功載入"
    assert beskar_armor.tier == Tier.RARE
    assert beskar_armor.modifiers.get("def_val") == 45
    print(f"✓ 星戰詞條已載入: 【{beskar_armor.tier}】{beskar_armor.name}")

    # 檢查戰鎚 40K 劇本
    scenario_wh = db.get_scenario("scenario_hive_psyker")
    assert scenario_wh is not None, "戰鎚巢都劇本應成功載入"
    print(f"✓ 戰鎚 40K 劇本已載入: 《{scenario_wh.get('name')}》")


def test_multiverse_save_load_persistence():
    print("\n" + "=" * 65)
    print("【測試 5】星際科幻宇宙狀態完整存檔與讀檔持久化驗證")
    print("=" * 65)

    world = WorldState()
    # 設置星圖主題
    world.world_map = WorldMap(theme=WorldTheme.SCI_FI)
    hive_planet = MapNode("sys_terra", "神聖泰拉 (Holy Terra)", NodeType.CITY, coords=(0, 0), orbital_type="Throneworld")
    world.world_map.add_node(hive_planet)

    # 創建具有護盾、腐化度與阿斯塔特詞條的角色
    hero = Character("hero_spacemarine", "連隊冠軍·阿爾弗雷德", rank_key="Pandita", is_awakened=True)
    hero.corruption = 42.5
    world.add_character(hero)

    save_path = "saves/multiverse_savegame.json"
    os.makedirs("saves", exist_ok=True)
    SaveLoadManager.save_to_file(world, save_path)
    print(f"星際科幻存檔已寫入: {save_path}")

    succ, msg, loaded_world = SaveLoadManager.load_from_file(save_path)
    assert succ is True
    assert loaded_world.world_map.theme == WorldTheme.SCI_FI, "星圖科幻主題應當完整還原"
    loaded_hero = loaded_world.get_character("hero_spacemarine")
    assert loaded_hero is not None
    assert loaded_hero.corruption == 42.5, f"靈魂腐化度應精確還原為 42.5，實際: {loaded_hero.corruption}"
    assert loaded_world.world_map.get_node("sys_terra").orbital_type == "Throneworld"
    print("✓ 星圖主題、星體元數據、靈魂腐化度 100% 完美持久化還原！")


if __name__ == "__main__":
    test_star_map_thematic_abstraction()
    test_combat_firefight_cover_shield_and_ap()
    test_morality_and_corruption_axis()
    test_def_loader_multi_ip_expansion()
    test_multiverse_save_load_persistence()
    print("\n" + "=" * 65)
    print(" 恭喜！三大架構擴充 + 戰鎚40K/星戰多宇宙適配全部 5 大測試 PASS！")
    print("=" * 65)
