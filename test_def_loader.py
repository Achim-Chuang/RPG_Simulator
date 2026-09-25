"""
Test RimWorld-style External Def Loader & Scenario World Generator.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.engine.def_loader import DefLoader, DefDatabase
from src.engine.save_load import SaveLoadManager
from src.core.traits import Tier, Category


def run_def_loader_test():
    print("=" * 75)
    print("      【RimWorld 式外部 Def 載入器與劇本生成測試】")
    print("=" * 75)

    loader = DefLoader()
    defs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "defs")

    print(f"\n[1. 掃描外部 Def 目錄] 掃描路徑: {defs_path} ...")
    load_logs = loader.load_all_defs(defs_path)
    for log in load_logs:
        print(f"  --> {log}")

    # 驗證詞條註冊
    print("\n[2. 檢驗 DefDatabase 註冊狀態]")
    db = loader.db
    print(f"  - 詞條註冊總數: {len(db.trait_defs)}")
    print(f"  - 劇本註冊總數: {len(db.scenario_defs)}")

    assert "reg_human_body" in db.trait_defs, "YAML 先天詞條 reg_human_body 未載入！"
    assert "reg_street_smart" in db.trait_defs, "JSON 後天詞條 reg_street_smart 未載入！"
    assert "rare_fox_charm" in db.trait_defs, "Mod 東方神話詞條 rare_fox_charm 未載入！"
    assert "scenario_wilderness_orphan" in db.scenario_defs, "YAML 主線劇本未載入！"
    print("  ✓ 詞條與劇本註冊完整（跨 YAML/JSON/Mod 目錄）。")

    # 驗證 Mod 詞條數值
    fox_trait = db.get_trait("rare_fox_charm")
    assert fox_trait.tier == Tier.RARE, "Mod 詞條階級解析錯誤！"
    assert fox_trait.category == Category.INNATE, "Mod 詞條分類解析錯誤！"
    print(f"  ✓ Mod 詞條解析無誤: 【{fox_trait.tier}】「{fox_trait.name}」 - {fox_trait.description}")

    # 驗證劇本世界生成
    print("\n[3. 根據劇本《荒野孤兒·覺醒者崛起》生成全新 WorldState]")
    world = loader.create_world_from_scenario("scenario_wilderness_orphan")
    assert world is not None, "劇本世界生成失敗！"

    # 檢查主角狀態
    hero = world.get_character("hero_orphan")
    assert hero is not None, "主角 hero_orphan 未生成！"
    assert hero.is_awakened is True, "主角覺醒狀態錯誤！"
    assert hero.gold == 45.0, "主角初始金幣錯誤！"
    assert any(t.id == "reg_human_body" for t in hero.innate_traits), "主角先天詞條未掛載！"
    assert any(t.id == "reg_street_smart" for t in hero.acquired_traits), "主角後天詞條未掛載！"
    print(f"  ✓ 主角狀態正確: {hero.name} (金幣: {hero.gold} 金，持有先天: {[t.name for t in hero.innate_traits]})")

    # 檢查 NPC 狀態
    npc = world.get_character("npc_galahad")
    assert npc is not None, "NPC 加拉哈未生成！"
    assert any(t.id == "unc_veteran_instinct" for t in npc.acquired_traits), "NPC 詞條百戰直覺未掛載！"
    print(f"  ✓ NPC 狀態正確: {npc.name} (持有後天: {[t.name for t in npc.acquired_traits]})")

    # 檢查初始勢力
    org = world.org_manager.get_org("org_border_kingdom")
    assert org is not None, "初始帝國勢力未生成！"
    assert org.fief_name == "黑石隘口要塞", "地盤要塞名稱錯誤！"
    assert org.treasury == 12000.0, "帝國初始金庫錯誤！"
    print(f"  ✓ 勢力狀態正確: {org.name} (地盤: {org.fief_name}，金庫: {org.treasury} 金)")

    # 檢查社交關係
    rel = world.social_network.get_relationship("npc_galahad", "hero_orphan")
    assert rel.affection == 25.0, "初始好感度錯誤！"
    assert rel.respect == 15.0, "初始敬畏度錯誤！"
    print(f"  ✓ 社交圖譜正確: 老兵對主角 好感={rel.affection}, 敬畏={rel.respect}, 意願={rel.willingness:.1f}")

    # 驗證存讀檔鏈路
    save_path = "saves/scenario_savegame.json"
    print(f"\n[4. 驗證劇本生成世界的存讀檔鏈路] 寫入至 {save_path} ...")
    save_ok, save_msg = SaveLoadManager.save_to_file(world, save_path)
    print(f"  --> {save_msg}")
    assert save_ok, "存檔失敗！"

    load_ok, load_msg, restored = SaveLoadManager.load_from_file(save_path)
    print(f"  --> {load_msg}")
    assert load_ok, "讀檔失敗！"
    assert restored.get_character("hero_orphan").name == "無名少年", "還原主角不符！"
    print("  ✓ 存讀檔完全相容！")

    print("\n" + "=" * 75)
    print("  ★ RimWorld 式外部 Def 載入器、Mod 合併與劇本世界生成測試全部通過！")
    print("=" * 75)


if __name__ == "__main__":
    run_def_loader_test()
