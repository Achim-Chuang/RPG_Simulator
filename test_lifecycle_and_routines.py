"""
Comprehensive Verification Suite for Social Professions, Daily Scheduled Routines,
and the LifeCycle Engine (Courtship, Marriage, Genetic Childbirth, and Succession).
"""

import os
import sys

# 加入根目錄到搜尋路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.traits import Trait, Tier, Category
from src.core.character import Character
from src.core.organization import Organization, OrgTier, Office, Authority
from src.core.calendar import TimeSlot
from src.core.lifecycle import LifeCycleEngine
from src.engine.world import WorldState
from src.engine.def_loader import DefLoader
from src.engine.save_load import SaveLoadManager


def run_tests():
    print("=" * 75)
    print("      【社會階級職業排程、戀愛求婚、遺傳生育與生死傳承測試】")
    print("=" * 75)

    # 1. 建立世界與載入外部職業定義庫
    loader = DefLoader()
    defs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "defs")
    loader.load_all_defs(defs_path)
    
    world = WorldState()
    for t in loader.db.trait_defs.values():
        world.register_trait(t)
    for p in loader.db.profession_defs.values():
        world.register_profession(p)

    assert "prof_artisan" in world.profession_registry, "工匠職業未能載入世界！"
    assert "prof_guard" in world.profession_registry, "衛兵職業未能載入世界！"
    print(f"[1. 職業定義庫載入] 已註冊 {len(world.profession_registry)} 個社會核心職業與日常管線。")

    # 2. 建立測試居民
    # 父親：鐵匠加拉哈 (男，24歲，持有矮人熔火地心)
    dad = Character("char_dad", "加拉哈·熔火鐵匠", rank_key="Chorji", is_awakened=True, gold=100.0)
    dad.gender = "male"
    dad.age = 24
    dad.profession_id = "prof_artisan"
    if "unc_dwarf_forge_heart" in world.trait_registry:
        dad.innate_traits.append(world.trait_registry["unc_dwarf_forge_heart"])

    # 母親：學者塞拉 (女，22歲，持有半精靈敏銳感知)
    mom = Character("char_mom", "塞拉·精靈學者", rank_key="Chorji", is_awakened=False, gold=80.0)
    mom.gender = "female"
    mom.age = 22
    mom.profession_id = "prof_scholar"
    if "unc_half_elf_vision" in world.trait_registry:
        mom.innate_traits.append(world.trait_registry["unc_half_elf_vision"])

    # 衛兵同僚：巡邏兵漢斯 (男，28歲)
    guard = Character("char_guard", "漢斯·城防衛兵", rank_key="Chorji", is_awakened=False, gold=50.0)
    guard.gender = "male"
    guard.age = 28
    guard.profession_id = "prof_guard"

    world.add_character(dad)
    world.add_character(mom)
    world.add_character(guard)

    # ==============================================================================
    # 測試 1: 日常時辰排程自動運轉 (晨工、午商、夜飲)
    # ==============================================================================
    print("\n[測試 2] 職業排程自動化運轉 (早晨生產、午後經商、夜間社交)")
    initial_dad_gold = dad.gold
    
    # 早晨時段推進
    world.calendar.current_slot = TimeSlot.MORNING
    world.lifecycle_engine.execute_slot_routines(world)
    assert dad.gold > initial_dad_gold, "工匠晨間生產應賺取計件工資！"
    print(f"  ✓ 早晨時段：工匠 {dad.name} 順利打鐵開工，金幣增長至 {dad.gold:.1f} 金。")

    # 夜間時段推進 (觸發同城夜間社交聚會)
    world.calendar.current_slot = TimeSlot.NIGHT
    dad.current_ap = 10
    mom.current_ap = 10
    guard.current_ap = 10
    world.lifecycle_engine.execute_slot_routines(world)
    
    rel_dm = world.social_network.get_relationship(dad.char_id, mom.char_id)
    print(f"  ✓ 夜間時段：酒館與居所交際運作，{dad.name} 與 {mom.name} 關係好感建立為 {rel_dm.affection:.1f}。")

    # ==============================================================================
    # 測試 2: 自由相愛與求婚成家 (Courtship & Marriage)
    # ==============================================================================
    print("\n[測試 3] 感情升溫、良緣締結與家庭共同基金成立")
    # 人為提升相處好感度至符合結婚標準
    world.social_network.modify(dad.char_id, mom.char_id, d_aff=60.0, d_resp=40.0, d_ob=40.0)
    world.social_network.modify(mom.char_id, dad.char_id, d_aff=60.0, d_resp=40.0, d_ob=40.0)

    marriage_logs = world.lifecycle_engine.process_courtship_and_marriage(world)
    assert dad.spouse_id == mom.char_id and mom.spouse_id == dad.char_id, "夫妻雙向配偶 ID 應綁定！"
    for l in marriage_logs:
        print(f"  {l}")
    print("  ✓ 婚姻締結完成！雙方正式建立家室。")

    # ==============================================================================
    # 測試 3: 懷孕受孕與新生兒遺傳誕生 (Pregnancy & Childbirth)
    # ==============================================================================
    print("\n[測試 4] 孕育生命、血脈稟賦遺傳與新角色生成")
    # 人為觸發懷孕倒數
    mom.pregnancy_timer = 1
    mom.pregnancy_partner_id = dad.char_id

    # 跨日迎來分娩
    birth_logs = world.lifecycle_engine.process_pregnancy_and_childbirth(world)
    assert len(mom.children_ids) == 1, "母親應記錄有 1 名子女！"
    assert len(dad.children_ids) == 1, "父親應記錄有 1 名子女！"
    
    baby_id = mom.children_ids[0]
    baby = world.get_character(baby_id)
    assert baby is not None, "新生兒角色應已注入世界實體池中！"
    assert baby.parent_ids == [dad.char_id, mom.char_id], "新生兒父母 ID 應精確溯源！"
    assert len(baby.innate_traits) > 0, "新生兒應成功遺傳父母的先天稟賦！"
    
    for l in birth_logs:
        print(f"  {l}")
    print(f"  --> 新生兒身分: {baby.name} (性別: {baby.gender}, 年齡: {baby.age})")
    print(f"  --> 繼承之先天詞條: {[t.name for t in baby.innate_traits]}")
    print(f"  --> 雙親親情好感: 母親好感={world.social_network.get_relationship(mom.char_id, baby.char_id).affection:.1f}")
    print("  ✓ 生命延續與遺傳演算法驗證完全無誤！")

    # ==============================================================================
    # 測試 4: 英雄遲暮、死亡與世襲繼承 (Mortality & Succession)
    # ==============================================================================
    print("\n[測試 5] 人物壽終正寢、遺產交接與組織官職血脈世襲")
    # 建立王國組織，任命父親為王國大元帥
    kingdom = Organization("org_test_kingdom", "洛蘭王國", OrgTier.INDEPENDENT, leader_id="hero_consul", treasury=1000.0)
    marshal_office = Office("marshal", "王國大元帥", [Authority.MILITARY], incumbent_id=dad.char_id)
    kingdom.add_office(marshal_office)
    world.org_manager.all_orgs[kingdom.org_id] = kingdom

    # 模擬父親老邁離世
    dad.gold = 500.0
    dad.age = 80
    
    # 讓孩子成年具備承襲資格 (設為 18 歲)
    baby.age = 18

    death_msg = world.lifecycle_engine.handle_character_death(dad, world, cause="安詳壽終")
    print(f"  {death_msg}")

    assert dad.is_alive is False, "父親死亡狀態應為 False！"
    assert mom.gold > 80.0, "未亡人配偶應繼承父親遺產金幣！"
    assert marshal_office.incumbent_id == baby.char_id, "王國大元帥職位應由長子正式世襲接任！"
    print(f"  ✓ 遺產與官職順利交接，大元帥現任長官: {marshal_office.incumbent_id} ({baby.name})！")

    # ==============================================================================
    # 測試 5: 存讀檔持久化 (家族譜系、職業與生死狀態)
    # ==============================================================================
    print("\n[測試 6] 社會譜系與生活狀態存讀檔完整性")
    save_path = "saves/test_lifecycle_save.json"
    succ, save_msg = SaveLoadManager.save_to_file(world, save_path)
    assert succ is True
    print(f"  --> 存檔寫入: {save_path}")

    load_succ, load_msg, loaded_world = SaveLoadManager.load_from_file(save_path)
    assert load_succ is True
    
    l_mom = loaded_world.get_character(mom.char_id)
    l_baby = loaded_world.get_character(baby.char_id)
    assert l_mom is not None and l_baby is not None
    assert l_mom.spouse_id == dad.char_id
    assert l_baby.parent_ids == [dad.char_id, mom.char_id]
    assert l_baby.profession_id == "prof_artisan"
    assert l_baby.is_alive is True
    print("  ✓ 讀檔後譜系親緣、家庭結構與職業身分完整還原！")

    print("\n" + "=" * 75)
    print("  ★ 社會職業日常排程、自由戀愛、遺傳生育與世襲繼承測試全部通過！")
    print("=" * 75)


if __name__ == "__main__":
    run_tests()
