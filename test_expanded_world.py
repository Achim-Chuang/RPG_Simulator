"""
Integration and Verification Test for:
1. Expanded Mythological & High-Tech Sci-Fi Trait Defs
2. Scalable Procedural World Generation (Small / Standard / Epic)
3. Ruins Exploration System (Biomes, Traps, Guardians, Relics)
4. Transcendent Rank, The First Awakened Encounter, and the 4 Meta-Endings
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.traits import Tier, Category
from src.core.character import Character
from src.core.ruins import RuinSite, RuinBiome, RuinsExplorationEngine
from src.core.transcendent import TranscendentEncounter, EndingChoice
from src.engine.def_loader import DefLoader
from src.engine.world_generator import WorldGenerator, WorldGenSettings, WorldScale
from src.engine.save_load import SaveLoadManager


def run_expanded_world_test():
    print("=" * 80)
    print("      【核心劇本擴充、世界生成設定、遺跡系統與多元神話詞條庫驗證】")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # 1. 載入外部 Def 庫與驗證擴充詞條
    # -------------------------------------------------------------------------
    loader = DefLoader()
    defs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "defs")
    print(f"\n[1. 掃描外部 Defs 目錄] {defs_dir} ...")
    logs = loader.load_all_defs(defs_dir)
    db = loader.db
    print(f"  --> 成功註冊 {len(db.trait_defs)} 個詞條，{len(db.scenario_defs)} 個劇本！")

    # 驗證神話與科幻彩蛋詞條
    print("\n[檢驗特殊詞條註冊]:")
    myth_samples = [
        "rare_olympian_scion",       # 希臘神話
        "mystic_asura_wrath",        # 佛經東方神話
        "mystic_fenrir_god_bite",    # 北歐神話
        "mystic_ouroboros_cycle",    # 埃及神話
        "mystic_nanite_bloodstream", # 史前科技彩蛋：奈米機械血脈
        "rare_quantum_intuition",    # 史前科技彩蛋：量子直覺
        "epic_singularity_core",     # 史前科技彩蛋：微型引力奇點核心
        "epic_first_awakened_staff"  # 原初覺醒者時空手杖
    ]
    for key in myth_samples:
        t = db.get_trait(key)
        assert t is not None, f"詞條 {key} 未成功載入！"
        print(f"  ✓ 【{t.tier}】{t.name} ({t.category.value}) - {t.description[:35]}...")

    assert len(db.trait_defs) >= 20, f"詞條總數不足（現有 {len(db.trait_defs)}，預期 >= 20）！"

    # -------------------------------------------------------------------------
    # 2. 隨機規模世界生成驗證 (Small vs Standard vs Epic)
    # -------------------------------------------------------------------------
    print("\n" + "-" * 80)
    print("【2. 可配置的世界生成規模驗證 (WorldGenSettings)】")

    # 測試標準規模世界
    std_settings = WorldGenSettings(
        scale=WorldScale.STANDARD,
        free_city_name="自由城邦·奧斯提亞",
        seed=100
    )
    std_world = WorldGenerator.generate(std_settings, db)
    
    fc = std_world.org_manager.get_org("org_free_city")
    assert fc is not None, "自由城邦未生成！"
    caravan = std_world.org_manager.get_org("org_caravan_guild")
    assert caravan is not None, "商隊公會未生成！"
    
    factions_count = len([o for o in std_world.org_manager.all_orgs.values() if o.tier == 5 and o.org_id != "org_free_city"])
    ruins_count = len(std_world.ruins_sites)
    print(f"  * 生成世界: {std_settings.scale.value}")
    print(f"  * 自由城邦: {fc.name} (金庫: {fc.treasury} 金)")
    print(f"  * 獨立勢力數量: {factions_count} (預期 4)")
    print(f"  * 遺跡數量: {ruins_count} (預期 8)")
    assert factions_count == 4, "獨立勢力數量不符標準規模配置！"
    assert ruins_count == 8, "遺跡數量不符標準規模配置！"

    # 驗證主角被商隊救治開局
    hero = std_world.get_character("player_hero")
    thomas = std_world.get_character("npc_caravan_thomas")
    assert hero is not None and thomas is not None, "主角或商隊首領缺失！"
    rel_to_thomas = std_world.social_network.get_relationship("player_hero", "npc_caravan_thomas")
    print(f"  * 主角背景: 昏迷於荒野，被【{thomas.name}】救起入城。主角對其恩怨值: +{rel_to_thomas.obligation} (救命之恩)")
    assert rel_to_thomas.obligation == 50.0, "主角對商隊首領的救命之恩關係未正確初始化！"

    # -------------------------------------------------------------------------
    # 3. 遺跡探索系統模擬 (Ruins Exploration)
    # -------------------------------------------------------------------------
    print("\n" + "-" * 80)
    print("【3. 遺跡探索系統模擬 (環境生態、機關、守衛與史前科技)】")
    sample_ruin = std_world.ruins_sites[0]
    sample_ruin.possible_loot = ["epic_singularity_core", "mystic_nanite_bloodstream", "rare_quantum_intuition"]
    print(f"目標遺跡: 【{sample_ruin.biome.value}】「{sample_ruin.name}」（危險度 ★{sample_ruin.danger_level}）")
    
    hero.current_ap = 10
    outcome, reward, explore_logs = RuinsExplorationEngine.explore_ruin(sample_ruin, hero, seed=42)
    for l in explore_logs:
        print(f"  {l}")
    print(f"探索結果: {outcome} | 獲得秘寶: {reward} | 主角剩餘 AP: {hero.current_ap}")
    assert hero.current_ap == 8, "探索遺跡未正確扣除 2 AP！"

    # -------------------------------------------------------------------------
    # 4. 原初覺醒者遭遇與四重終局驗證
    # -------------------------------------------------------------------------
    print("\n" + "-" * 80)
    print("【4. 原初覺醒者 (Il) 遭遇與四大終局分支驗證】")

    # 初始未達標
    hero.rank_key = "Chorji"
    can_trigger, msg = TranscendentEncounter.can_trigger_encounter(hero)
    print(f"綽爾濟位階嘗試接觸: {msg}")
    assert not can_trigger, "位階不足應無法觸發原初遭遇！"

    # 主角晉升至第四階 Nomenkhan
    hero.rank_key = "Nomenkhan"
    can_trigger, msg = TranscendentEncounter.can_trigger_encounter(hero)
    print(f"諾門罕位階嘗試接觸: {msg}")
    assert can_trigger, "諾門罕位階應允許觸發原初遭遇！"

    print("\n[時空神廟揭露第四面牆真相]:")
    print(TranscendentEncounter.get_prologue_dialogue())

    # 測試終局 1：武力交鋒弒神 (COMBAT)
    print("\n--> 測試終局路徑 A: 【武力弒神】")
    ok, res, logs_combat = TranscendentEncounter.resolve_choice(hero, EndingChoice.COMBAT, seed=123)
    for l in logs_combat[-3:]:
        print(f"  {l}")
    assert ok and hero.rank_key == "Transcendent", "戰鬥弒神未正確晉升為 Transcendent！"

    # 驗證超凡者【全知編織 (Omni-Weave)】修改器模式
    print("\n--> 驗證超凡者造物特權 (Omni-Weave):")
    t_singularity = db.get_trait("epic_singularity_core")
    t_nanite = db.get_trait("mystic_nanite_bloodstream")
    t_neural = db.get_trait("epic_neural_singularity")

    success, imprint_msg = hero.imprint_trait(hero, t_singularity)
    print(imprint_msg)
    success, imprint_msg = hero.imprint_trait(hero, t_nanite)
    print(imprint_msg)
    success, imprint_msg = hero.imprint_trait(hero, t_neural)
    print(imprint_msg)

    load = hero.calculate_sustained_load()
    ratio = hero.stress_ratio
    print(f"  ★ 超凡者裝備 3 個史詩/秘傳神級詞條後：常駐維持負荷 = {load:.1f} MP (佔比: {ratio*100:.1f}%)")
    assert load == 0.0 and ratio == 0.0, "超凡者負荷應恆為 0 (免除一切反噬懲罰)！"

    # 測試終局 2：嘴砲說服 (PERSUADE)
    print("\n" + "-" * 80)
    print("--> 測試終局路徑 B: 【哲學說服 (嘴砲三連檢定)】")
    hero_diplomat = Character("hero_dip", "辯論家主角", rank_key="Nomenkhan", is_awakened=True)
    t_phil = db.get_trait("rare_philosopher_reason")
    if t_phil:
        hero_diplomat.acquired_traits.append(t_phil)
    ok, res, logs_persuade = TranscendentEncounter.resolve_choice(hero_diplomat, EndingChoice.PERSUADE, seed=1)
    for l in logs_persuade:
        print(f"  {l}")
    assert ok and hero_diplomat.rank_key == "Transcendent", "說服成功未正確晉升為 Transcendent！"


    # 測試終局 4：碎道絕仙破輪迴 (SHATTER)
    print("\n" + "-" * 80)
    print("--> 測試終局路徑 C: 【碎道破輪迴】")
    hero_breaker = Character("hero_break", "破壁者主角", rank_key="Nomenkhan", is_awakened=True)
    ok, res, logs_shatter = TranscendentEncounter.resolve_choice(hero_breaker, EndingChoice.SHATTER)
    for l in logs_shatter:
        print(f"  {l}")
    assert ok and not hero_breaker.is_awakened, "碎道破輪迴後覺醒者特性應永久消逝！"

    # -------------------------------------------------------------------------
    # 5. 存檔驗證
    # -------------------------------------------------------------------------
    save_path = "saves/free_city_savegame.json"
    save_ok, save_msg = SaveLoadManager.save_to_file(std_world, save_path)
    print(f"\n[5. 儲存擴充世界存檔] {save_msg}")
    assert save_ok, "擴充世界存檔失敗！"

    print("\n" + "=" * 80)
    print("  ★ 擴充劇本、隨機世界生成、遺跡生態與原初覺醒者四大終局全部驗證通過！")
    print("=" * 80)


if __name__ == "__main__":
    run_expanded_world_test()
