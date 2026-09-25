"""
End-to-End Integration Test for the Consolidate src/ Architecture & Save/Load System.
"""

import os
import sys

# 將工作區根目錄加入 Python 搜尋路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.traits import Trait, Tier, Category
from src.core.character import Character
from src.core.organization import OrgTier, Organization
from src.core.actions import ActionCheckEngine, ActionSuite, SubAction
from src.core.combat import Combatant, PersonalCombatEngine
from src.engine.world import WorldState
from src.engine.save_load import SaveLoadManager


def run_integration_test():
    print("=" * 75)
    print("      【端到端系統整合與存檔/讀檔驗證 (Integration Test)】")
    print("=" * 75)

    # 1. 建立初始世界狀態
    world = WorldState()

    # 2. 註冊詞條庫
    t_dagger = Trait("reg_dagger", "粗淺匕首技巧", Category.ACQUIRED, Tier.REGULAR, "匕首命中+10%")
    t_arithmetic = Trait("reg_arithmetic", "市井算術", Category.ACQUIRED, Tier.REGULAR, "議價加成+5%")
    t_alertness = Trait("reg_alertness", "夜巡直覺", Category.ACQUIRED, Tier.REGULAR, "遭遇突襲率-15%")
    t_veteran = Trait("unc_veteran", "百戰直覺", Category.ACQUIRED, Tier.UNCOMMON, "免疫初級恐慌")
    t_charm = Trait("rare_fox_charm", "天狐媚骨", Category.INNATE, Tier.RARE, "說服成功率大幅上升")

    for t in [t_dagger, t_arithmetic, t_alertness, t_veteran, t_charm]:
        world.register_trait(t)
    print(f"[1. 詞條註冊] 已註冊 {len(world.trait_registry)} 個跨階級詞條。")

    # 3. 創建角色並加入世界
    hero = Character("hero_01", "無名孤兒(主角)", rank_key="Chorji", is_awakened=True, gold=150.0)
    veteran = Character("vet_01", "受傷老兵·加拉哈", rank_key="Chorji", is_awakened=False, gold=50.0)
    world.add_character(hero)
    world.add_character(veteran)
    print(f"[2. 角色建立] 已注入主角（{hero.name}）與老兵（{veteran.name}）。")

    # 4. 執行核心操作：主角刻印詞條
    hero.imprint_trait(hero, t_arithmetic)
    hero.imprint_trait(hero, t_alertness)
    print(f"[3. 本質刻印] 主角成功刻印 2 個詞條，當前維持負荷: {hero.calculate_sustained_load():.1f}/{hero.max_mp:.1f} MP ({hero.stress_ratio*100:.1f}%)")

    # 5. 執行核心操作：建立社交關係與二人小隊
    world.social_network.modify("vet_01", "hero_01", d_aff=60.0, d_resp=40.0, d_ob=30.0)
    success, org_msg, squad = world.org_manager.create_personal_org("hero_01", "vet_01", "破曉開拓小隊")
    print(f"[4. 社交與組織] {org_msg}")

    # 6. 創建獨立勢力與封地
    empire = Organization(
        org_id="org_empire",
        name="神聖洛蘭王國",
        tier=OrgTier.INDEPENDENT,
        leader_id="king_01",
        treasury=15000.0,
        fief_name="王都·黃金城",
        fief_monthly_income=5000.0
    )
    world.org_manager.all_orgs[empire.org_id] = empire

    world.org_manager.create_local_faction(
        superior_org=empire,
        lord_id="hero_01",
        name="鐵拳領府",
        fief_name="黑岩堡",
        fief_income=800.0,
        tribute_rate=0.20
    )
    print(f"[5. 分封領地] 主角獲封「黑岩堡」，成為地方勢力！")

    # 7. 推進日曆時段
    hero.current_ap -= 4 # 主角早上花了 4 AP
    print(f"\n[推進前] 第 {world.calendar.current_day} 天【{world.calendar.current_slot.value}】，主角剩餘 AP: {hero.current_ap}")
    adv_logs = world.advance_time_slot()
    for log in adv_logs:
        print(f"  --> {log}")
    print(f"[推進後] 第 {world.calendar.current_day} 天【{world.calendar.current_slot.value}】，主角 AP 已刷新為: {hero.current_ap} (休息累計: {hero.rest_accumulated})")

    # 8. 儲存遊戲世界狀態
    save_path = "saves/savegame_test.json"
    print("\n" + "-" * 75)
    print(f"【開始存檔】序列化 WorldState 至 {save_path} ...")
    save_ok, save_msg = SaveLoadManager.save_to_file(world, save_path)
    print(save_msg)
    assert save_ok, "存檔過程出現異常！"

    # 9. 讀檔還原至全新的 WorldState 實例
    print(f"【開始讀檔】自 {save_path} 逆向反序列化還原...")
    load_ok, load_msg, restored_world = SaveLoadManager.load_from_file(save_path)
    print(load_msg)
    assert load_ok, "讀檔過程出現異常！"

    # 10. 深度斷言驗證 (Deep State Assertions)
    print("\n" + "-" * 75)
    print("【深度狀態一致性驗證】")

    # A. 驗證日曆時段
    assert restored_world.calendar.current_day == world.calendar.current_day, "日曆天數不符！"
    assert restored_world.calendar.current_slot == world.calendar.current_slot, "日曆時段不符！"
    print("  ✓ 日曆狀態一致：天數與時段完美吻合。")

    # B. 驗證角色與詞條數值
    r_hero = restored_world.get_character("hero_01")
    assert r_hero is not None, "主角角色遺失！"
    assert r_hero.name == hero.name, "角色名稱不符！"
    assert len(r_hero.imprinted_traits) == 2, "刻印詞條數量不符！"
    assert abs(r_hero.calculate_sustained_load() - hero.calculate_sustained_load()) < 1e-4, "精神維持負荷不符！"
    assert r_hero.rest_accumulated == hero.rest_accumulated, "休息點數不符！"
    print(f"  ✓ 主角狀態一致：刻印詞條 {[t.name for t in r_hero.imprinted_traits]}，負荷 {r_hero.calculate_sustained_load():.1f} MP 吻合。")

    # C. 驗證社交關係矩陣
    rel = restored_world.social_network.get_relationship("vet_01", "hero_01")
    assert abs(rel.affection - 60.0) < 1e-4, "好感度不符！"
    assert abs(rel.respect - 40.0) < 1e-4, "敬畏度不符！"
    assert abs(rel.willingness - 48.0) < 1e-4, "意願評分不符！"
    print(f"  ✓ 社交圖譜一致：老兵對主角好感={rel.affection}，意願={rel.willingness:.1f} 吻合。")

    # D. 驗證五階組織樹與地盤
    r_fief = restored_world.org_manager.get_org("org_loc_hero_01")
    assert r_fief is not None, "地方勢力組織遺失！"
    assert r_fief.fief_name == "黑岩堡", "地盤名稱不符！"
    assert r_fief.treasury == 1000.0, "領地金庫不符！"
    print(f"  ✓ 組織架構一致：地方勢力「{r_fief.name}」領地【{r_fief.fief_name}】金庫 {r_fief.treasury} 金 吻合。")

    print("\n" + "=" * 75)
    print("  ★ 全部整合測試通過！架構整合與統一 JSON 存檔/讀檔系統驗證成功！")
    print("=" * 75)


if __name__ == "__main__":
    run_integration_test()
