"""
Test Suite for Dynamic Organizational Offices, Cultural Council Templates,
and the Extensible Interpersonal Interactions Framework.
"""

import os
import sys
from typing import Any, Dict, List, Optional

# 加入根目錄到搜尋路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.traits import Trait, Tier, Category
from src.core.character import Character
from src.core.organization import Organization, OrgTier, Office, Authority, OrgManager
from src.core.social import SocialNetwork
from src.core.interactions import (
    InteractionRegistry,
    BaseInteraction,
    InteractionCategory,
    InteractionResult,
    ConverseInteraction,
    GiftGoldInteraction,
    ThreatenDuelInteraction,
    AppointOfficeInteraction,
    ScanEssenceInteraction,
    ImprintTargetTraitInteraction,
    InstigateRebellionInteraction
)
from src.engine.world import WorldState
from src.engine.save_load import SaveLoadManager


def run_tests():
    print("=" * 75)
    print("      【動態職能席位、文化內閣皮膚與角色互動系統測試】")
    print("=" * 75)

    # 1. 建立世界與角色
    world = WorldState()
    hero = Character("hero_01", "伊爾·本質編織者", rank_key="Pandita", is_awakened=True, gold=300.0)
    marshal = Character("npc_marshal", "加拉哈·鐵血將軍", rank_key="Chorji", is_awakened=False, gold=50.0)
    treasurer = Character("npc_treasurer", "戈爾德·精明商賈", rank_key="Chorji", is_awakened=False, gold=20.0)
    
    # 註冊詞條並裝備
    t_tactician = Trait("unc_tactician_eye", "戰術推演之眼", Category.ACQUIRED, Tier.UNCOMMON, "戰術指揮加成")
    t_monopoly = Trait("rare_monopoly_baron", "托拉斯寡頭手腕", Category.ACQUIRED, Tier.RARE, "商業利潤加成")
    t_ambitious = Trait("unc_ambitious", "野心家", Category.ACQUIRED, Tier.UNCOMMON, "渴望篡位自立")
    t_fox = Trait("rare_fox_charm", "天狐媚骨", Category.INNATE, Tier.RARE, "社交好感大幅提升")

    world.register_trait(t_tactician)
    world.register_trait(t_monopoly)
    world.register_trait(t_ambitious)
    world.register_trait(t_fox)

    marshal.acquired_traits.append(t_tactician)
    treasurer.acquired_traits.append(t_monopoly)
    hero.innate_traits.append(t_fox)

    world.add_character(hero)
    world.add_character(marshal)
    world.add_character(treasurer)

    # 建立組織並套用奇幻內閣
    kingdom = Organization(
        org_id="org_kingdom",
        name="神聖洛蘭王國",
        tier=OrgTier.INDEPENDENT,
        leader_id="hero_01",
        fief_name="洛蘭王都",
        fief_monthly_income=500.0,
        treasury=2000.0
    )
    world.org_manager.all_orgs[kingdom.org_id] = kingdom

    # ==============================================================================
    # 測試 1: 文化內閣皮膚與職能槽位
    # ==============================================================================
    print("\n[測試 1] 文化內閣皮膚 (Council Templates) 與職權拆分")
    kingdom.apply_council_template("feudal_fantasy")
    assert len(kingdom.offices) == 6, "奇幻內閣應具備 6 大核心職位！"
    assert "marshal" in kingdom.offices and kingdom.offices["marshal"].title == "王國大元帥"
    assert "treasurer" in kingdom.offices and kingdom.offices["treasurer"].title == "財政總管"
    print(f"  ✓ 成功套用「奇幻王國」內閣架構: {[o.title for o in kingdom.offices.values()]}")

    # 測試切換為科幻星區帝國皮膚
    kingdom.apply_council_template("scifi_empire")
    assert kingdom.offices["warmaster"].title == "星區大戰帥"
    assert Authority.MILITARY in kingdom.offices["warmaster"].authorities
    print(f"  ✓ 成功動態切換為「星際科幻帝國」內閣: {[o.title for o in kingdom.offices.values()]}")

    # 切換回奇幻
    kingdom.apply_council_template("feudal_fantasy")

    # ==============================================================================
    # 測試 2: 官員任命、權能代理與效率運算 (適任 vs 懸缺)
    # ==============================================================================
    print("\n[測試 2] 職位任命、詞條適任度加成與懸缺懲罰")
    # 懸缺狀態檢定
    eff_vacant, msg_vacant = kingdom.get_authority_efficiency(Authority.MILITARY, world.characters)
    assert eff_vacant == 0.50, "職務懸缺時效率應為 50% 懲罰！"
    print(f"  - 懸缺測試: {msg_vacant}")

    # 任命大元帥
    succ, app_msg = kingdom.appoint_office("marshal", "npc_marshal")
    assert succ is True
    assert kingdom.get_authority_holder(Authority.MILITARY) == "npc_marshal"
    print(f"  - 任命反饋: {app_msg.splitlines()[0]}")

    # 任命財政總管
    kingdom.appoint_office("treasurer", "npc_treasurer")

    # 檢驗持有【戰術推演之眼】將領的效率
    eff_marshal, msg_marshal = kingdom.get_authority_efficiency(Authority.MILITARY, world.characters)
    assert eff_marshal > 1.0, "持有戰術詞條之將領應具備效率加成！"
    print(f"  - 適任檢定 (軍事): {msg_marshal}")

    eff_treasurer, msg_treasurer = kingdom.get_authority_efficiency(Authority.TREASURY, world.characters)
    assert eff_treasurer > 1.0, "持有寡頭手腕之官員應具備財政效率加成！"
    print(f"  - 適任檢定 (財政): {msg_treasurer}")
    print("  ✓ 職權代理與詞條加成檢定全部符合預期！")

    # ==============================================================================
    # 測試 3: 社交情感互動 (Converse, GiftGold, Threaten)
    # ==============================================================================
    print("\n[測試 3] 社交與情感互動 (Converse, GiftGold, ThreatenDuel)")
    # 攀談 (主角持有天狐媚骨)
    res_conv = world.execute_interaction("converse", "hero_01", "npc_marshal")
    assert res_conv.success is True
    assert res_conv.delta_affection > 15.0, "天狐媚骨應大幅增加好感！"
    print(f"  {res_conv.message.splitlines()[0]}")

    # 賞賜金幣
    res_gift = world.execute_interaction("gift_gold", "hero_01", "npc_marshal", amount=100.0)
    assert res_gift.success is True
    assert marshal.gold == 150.0 and hero.gold == 200.0
    print(f"  {res_gift.message.splitlines()[0]}")

    # 武力威懾
    res_threaten = world.execute_interaction("threaten_duel", "hero_01", "npc_treasurer")
    assert res_threaten.success is True
    assert res_threaten.delta_respect > 0
    print(f"  {res_threaten.message.splitlines()[0]}")
    print("  ✓ 基礎情感互動執行流暢無誤！")

    # ==============================================================================
    # 測試 4: 主角金手指本質干預 (ScanEssence, ImprintTargetTrait)
    # ==============================================================================
    print("\n[測試 4] 主角本質干預特權 (ScanEssence, ImprintTargetTrait)")
    # 洞察本質
    res_scan = world.execute_interaction("scan_essence", "hero_01", "npc_marshal")
    assert res_scan.success is True
    print(f"  {res_scan.message}")

    # 給將軍刻印【野心家】！
    res_imp = world.execute_interaction("imprint_target_trait", "hero_01", "npc_marshal", trait=t_ambitious)
    assert res_imp.success is True
    assert t_ambitious in marshal.imprinted_traits
    print(f"  --> 暗中操作成功：已將【野心家】刻印至將軍靈魂中！")

    # ==============================================================================
    # 測試 5: 權謀與策動自立叛亂 (InstigateRebellion)
    # ==============================================================================
    print("\n[測試 5] 權謀策反與宮鬥反噬 (InstigateRebellion)")
    # 刻印野心家後，目標叛亂傾向分數大增
    # 重置新時間槽 AP
    hero.current_ap = 10
    # 我們讓將軍對國王的意願值降低
    world.social_network.modify("npc_marshal", "hero_01", d_aff=-30.0) # 刻意壓低對領主滿意度
    res_rebel = world.execute_interaction("instigate_rebellion", "hero_01", "npc_marshal", target_org_id="org_kingdom")
    print(f"  {res_rebel.message}")
    assert res_rebel.success is True, "握有軍權且具野心之將領策反應成功！"
    assert res_rebel.extra_data.get("coup_ready") is True
    print("  ✓ 角色詞條導向之政治陰謀與策反判定正確！")

    # ==============================================================================
    # 測試 6: 互動系統的可擴充性 (Extensibility Verification)
    # ==============================================================================
    print("\n[測試 6] 互動系統擴充性 (註冊自定義互動：血誓同盟)")
    class BloodOathInteraction(BaseInteraction):
        id = "blood_oath"
        name = "締結血誓"
        category = InteractionCategory.CONTRACT
        ap_cost = 5

        def execute(self, actor: Character, target: Character, world_state: Any, **kwargs) -> InteractionResult:
            actor.current_ap -= self.ap_cost
            rel = world_state.social_network.modify(target.char_id, actor.char_id, d_aff=50.0, d_ob=50.0)
            return InteractionResult(
                success=True,
                message=f"【生死血誓】{actor.name} 與 {target.name} 歃血為盟！結為異姓兄弟！"
            )

    InteractionRegistry.register(BloodOathInteraction())
    assert InteractionRegistry.get("blood_oath") is not None
    res_oath = world.execute_interaction("blood_oath", "hero_01", "npc_treasurer")
    assert res_oath.success is True
    print(f"  {res_oath.message}")
    print("  ✓ 自定義擴充互動註冊與執行成功！")

    # ==============================================================================
    # 測試 7: 存讀檔持久化 (Offices & Incumbents)
    # ==============================================================================
    print("\n[測試 7] 內閣職能與任職狀態存讀檔還原")
    save_path = "saves/test_council_save.json"
    succ, save_msg = SaveLoadManager.save_to_file(world, save_path)
    assert succ is True
    print(f"  --> 存檔寫入: {save_path}")

    load_succ, load_msg, loaded_world = SaveLoadManager.load_from_file(save_path)
    assert load_succ is True
    loaded_org = loaded_world.org_manager.get_org("org_kingdom")
    assert loaded_org is not None
    assert len(loaded_org.offices) == 6
    assert loaded_org.offices["marshal"].incumbent_id == "npc_marshal"
    assert loaded_org.offices["treasurer"].incumbent_id == "npc_treasurer"
    assert loaded_org.get_authority_holder(Authority.MILITARY) == "npc_marshal"
    print("  ✓ 讀檔後內閣職位與任職名單無損還原！")

    print("\n" + "=" * 75)
    print("  ★ 職能席位、文化內閣、角色互動與權謀擴充測試全部通過！")
    print("=" * 75)


if __name__ == "__main__":
    run_tests()
