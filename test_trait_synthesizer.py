"""
Test Suite for Dynamic Procedural Trait Synthesizer, Hero Custom Traits, and Save/Load Persistence.
"""

import os
import sys
import json

# 加入根目錄到搜尋路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.traits import Trait, Tier, Category
from src.core.character import Character
from src.core.trait_synthesizer import TraitSynthesizer
from src.engine.world import WorldState
from src.engine.save_load import SaveLoadManager
from src.engine.def_loader import DefLoader


def run_trait_synthesizer_tests():
    print("=" * 75)
    print("      【即時詞條生成器 (TraitSynthesizer) 與主角專屬存檔整合測試】")
    print("=" * 75)

    # 1. 測試基礎雙詞條融合
    print("\n[測試 1] 語意合成與數值共鳴雜交 (Fusion)")
    t_flame = Trait(
        id="rare_flame_heart",
        name="熾熱炎心",
        category=Category.INNATE,
        tier=Tier.RARE,
        description="心臟如熔爐般跳動，散發高溫氣息。",
        modifiers={"fire_damage": 1.25, "melee_power": 1.10},
        tags=["fire", "melee"],
        corruption_delta=0.0
    )
    t_blade = Trait(
        id="unc_shadow_blade",
        name="幽影殘刃",
        category=Category.ACQUIRED,
        tier=Tier.UNCOMMON,
        description="隱於暗處的刺殺短刃技術。",
        modifiers={"melee_power": 1.20, "stealth": 0.30},
        tags=["dark", "melee"],
        corruption_delta=3.0
    )

    fused_trait = TraitSynthesizer.fuse(t_flame, t_blade, seed=42)
    print(f"  - 原料 1: 【{t_flame.tier}】「{t_flame.name}」 Tags={t_flame.tags} Modifiers={t_flame.modifiers}")
    print(f"  - 原料 2: 【{t_blade.tier}】「{t_blade.name}」 Tags={t_blade.tags} Modifiers={t_blade.modifiers}")
    print(f"  --> 融合產物: 【{fused_trait.tier}】「{fused_trait.name}」 (ID: {fused_trait.id})")
    print(f"      描述: {fused_trait.description}")
    print(f"      屬性: {fused_trait.modifiers}")
    print(f"      標籤: {fused_trait.tags}")
    print(f"      腐化變動: {fused_trait.corruption_delta:+0.1f}")
    print(f"      溯源親代: {fused_trait.parents}")

    assert fused_trait.is_synthetic is True, "合成詞條必須標記為 is_synthetic=True！"
    assert fused_trait.tier >= Tier.RARE, "融合詞條階級應大於等於較高母體！"
    assert "melee_power" in fused_trait.modifiers, "雙方共有屬性 melee_power 必須保留！"
    assert fused_trait.parents == ["rare_flame_heart", "unc_shadow_blade"], "親代親緣必須精確紀錄！"
    assert "fire" in fused_trait.tags and "dark" in fused_trait.tags, "標籤聯集必須包含雙方元素！"
    print("  ✓ 基礎雙詞條語意與數值融合驗證通過！")

    # 2. 測試詞條洗鍊與變異 (Mutation / Refine)
    print("\n[測試 2] 詞條變異與數值洗鍊 (Mutation)")
    mutated = TraitSynthesizer.mutate(fused_trait, focus_modifier="melee_power", purify_corruption=True, seed=123)
    print(f"  --> 洗鍊產物: 【{mutated.tier}】「{mutated.name}」")
    print(f"      屬性強化: {mutated.modifiers['melee_power']} (原: {fused_trait.modifiers['melee_power']})")
    print(f"      淨化腐化值: {mutated.corruption_delta} (原: {fused_trait.corruption_delta})")
    assert mutated.modifiers["melee_power"] > fused_trait.modifiers["melee_power"], "指定洗鍊屬性必須獲得提升！"
    assert mutated.corruption_delta <= 0.0, "淨化功能應消除負面腐化！"
    print("  ✓ 詞條洗鍊與腐化淨化功能正常！")

    # 3. 測試主角執行本質重組與刻印
    print("\n[測試 3] 主角本質編織者行動：消耗 MP 融合並刻印至自身")
    hero = Character("hero_weaver", "伊爾·本質編織者", rank_key="Pandita", is_awakened=True, gold=200.0)
    initial_mp = hero.current_mp
    success, fuse_log, custom_trait = TraitSynthesizer.execute_hero_fusion(hero, t_flame, t_blade, seed=99)
    assert success is True, "主角本質融合應該成功！"
    assert custom_trait is not None
    assert hero.current_mp < initial_mp, "融合必須消耗主角 MP！"
    assert custom_trait.id in hero.custom_traits, "合成詞條必須註冊至主角專屬 custom_traits 中！"
    print(f"  {fuse_log}")

    # 刻印自創詞條
    imprint_ok, imprint_msg = hero.imprint_trait(hero, custom_trait)
    assert imprint_ok is True, "主角刻印自創詞條失敗！"
    assert custom_trait in hero.imprinted_traits, "刻印槽位中必須包含該自創詞條！"
    print(f"  --> 刻印反饋:\n      {imprint_msg}")
    print(f"  --> 當前常駐負荷: {hero.calculate_sustained_load():.1f} / {hero.max_mp:.1f} MP ({hero.stress_ratio*100:.1f}%)")
    print("  ✓ 主角專屬自創詞條成功刻印，負荷運算無誤！")

    # 4. 測試存讀檔持久化與全域 Def 隔離
    print("\n[測試 4] 存檔持久化驗證：自創詞條隨主角存檔還原，且絕不污染全域 Def 庫")
    world = WorldState()
    world.register_trait(t_flame)
    world.register_trait(t_blade)
    world.add_character(hero)

    save_path = "saves/test_dynamic_trait_save.json"
    succ, save_msg = SaveLoadManager.save_to_file(world, save_path)
    assert succ is True, f"存檔失敗: {save_msg}"
    print(f"  --> 存檔寫入完成: {save_path}")

    # 檢查 JSON 內容結構
    with open(save_path, "r", encoding="utf-8") as f:
        saved_json = json.load(f)

    # 驗證: 全域 traits 清單中只有靜態詞條，沒有臨時合成詞條
    global_trait_ids = [t["id"] for t in saved_json["traits"]]
    assert custom_trait.id not in global_trait_ids, "自創詞條不應污染全域 traits 清單！"

    # 驗證: 主角的節點下包含 custom_traits 清單
    hero_json = [c for c in saved_json["characters"] if c["char_id"] == "hero_weaver"][0]
    hero_custom_ids = [ct["id"] for ct in hero_json["custom_traits"]]
    assert custom_trait.id in hero_custom_ids, "主角節點下必須保存完整自創詞條資料！"
    print("  ✓ JSON 序列化結構確認：全域乾淨，個體保存！")

    # 執行讀檔還原
    load_ok, load_msg, loaded_world = SaveLoadManager.load_from_file(save_path)
    assert load_ok is True, f"讀檔失敗: {load_msg}"
    
    loaded_hero = loaded_world.get_character("hero_weaver")
    assert loaded_hero is not None
    assert custom_trait.id in loaded_hero.custom_traits, "讀檔後主角專屬詞條庫遺失！"
    
    restored_trait = loaded_hero.custom_traits[custom_trait.id]
    assert restored_trait.name == custom_trait.name, "還原詞條名稱不匹配！"
    assert restored_trait.modifiers == custom_trait.modifiers, "還原詞條修飾符不匹配！"
    assert restored_trait.parents == custom_trait.parents, "還原親代溯源不匹配！"
    assert len(loaded_hero.imprinted_traits) == 1, "讀檔後刻印槽位未正常恢復！"
    assert loaded_hero.imprinted_traits[0].id == custom_trait.id, "恢復刻印詞條 ID 不符！"

    # 驗證 WorldState.get_trait
    w_found = loaded_world.get_trait(custom_trait.id, loaded_hero)
    assert w_found is not None and w_found.id == custom_trait.id, "WorldState.get_trait 應能跨層解析主角自創詞條！"
    print("  ✓ 存讀檔完全還原！自創詞條無損復原並掛載於主角槽位中。")

    # 5. 測試多代累計融合 (Multi-generational Ancestry)
    print("\n[測試 5] 多代迭代合成測試 (A + B -> C, C + D -> D_ultra)")
    t_cyber = Trait(
        id="rare_cyber_core",
        name="量子超頻核心",
        category=Category.ARTIFACT,
        tier=Tier.RARE,
        description="軍用級生物義體運算中樞。",
        modifiers={"computation": 50.0, "reaction_speed": 1.2},
        tags=["tech", "cyber"],
        corruption_delta=0.0
    )
    c3 = TraitSynthesizer.fuse(custom_trait, t_cyber, hero=hero, seed=777)
    print(f"  --> 次世代超凡融合產物: 【{c3.tier}】「{c3.name}」")
    print(f"      溯源親代清單: {c3.parents}")
    print(f"      綜合標籤: {c3.tags}")
    print(f"      超頻複合屬性: {c3.modifiers}")
    assert custom_trait.id in c3.parents and t_cyber.id in c3.parents
    assert "cyber" in c3.tags and "fire" in c3.tags
    print("  ✓ 多代複合融合親緣溯源無誤！")

    print("\n" + "=" * 75)
    print("  ★ 即時詞條生成器、主角獨立基因庫與無污染存讀檔測試全部通過！")
    print("=" * 75)


if __name__ == "__main__":
    run_trait_synthesizer_tests()
