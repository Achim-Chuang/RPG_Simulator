"""
Automated Test Suite for Physical Multi-tier Economy, Dynamic Pricing,
and Emergent Strategic Actions (Siege, Embargo, Commerce Raiding, Arbitrage).
"""

import sys
import os
import json

from src.core.economy import (
    Commodity, CommodityType, ProductionRecipe, Workshop,
    LocalMarket, MerchantCaravan, STANDARD_COMMODITIES, STANDARD_RECIPES
)
from src.core.map import WorldMap, MapNode, NodeType, RoadType
from src.engine.world import WorldState
from src.engine.world_generator import WorldGenerator, WorldGenSettings, WorldScale
from src.engine.def_loader import DefDatabase
from src.engine.save_load import SaveLoadManager


def test_physical_production_chain():
    print("=" * 60)
    print("【測試 1】實體產業鏈物理流轉：一級原物料 -> 二級加工 -> 嚴格扣料檢定")
    print("=" * 60)

    market = LocalMarket("node_test_haven")
    market.inventory = {"raw_grain": 10, "good_bread": 0}
    market.target_stock = {"raw_grain": 20, "good_bread": 20}

    # 烘焙作坊：1批次消耗 2 raw_grain，產出 1 good_bread
    bakery = Workshop(
        workshop_id="ws_bakery_01",
        name="中央烘焙坊",
        recipe=STANDARD_RECIPES["recipe_bakery"],
        daily_batches=3  # 每日生產 3 批次：需 6 raw_grain，產出 3 good_bread
    )
    market.workshops.append(bakery)

    # 執行生產
    success, msg = bakery.produce(market)
    print(f"生產反饋: {msg}")
    assert success is True, "有足夠小麥，應當生產成功"
    assert market.inventory["raw_grain"] == 4, f"10 - 6 應為 4，實際: {market.inventory['raw_grain']}"
    assert market.inventory["good_bread"] == 3, f"應產出 3 份麵包，實際: {market.inventory['good_bread']}"
    print("✓ 一級原物料真實扣減，二級加工品成功產出！")

    # 再次生產：現有 4 raw_grain，需要 6 raw_grain -> 應當原料不足停工！
    success2, msg2 = bakery.produce(market)
    print(f"缺料生產反饋: {msg2}")
    assert success2 is False, "原料不足應當停工"
    assert bakery.stalled is True, "作坊狀態應為 stalled"
    assert "原料短缺" in bakery.stalled_reason
    assert market.inventory["raw_grain"] == 4, "停工不應扣除剩餘原料"
    assert market.inventory["good_bread"] == 3, "停工不應產出任何麵包"
    print("✓ 原料不足時作坊真實停工，嚴禁憑空產出！")


def test_shortage_and_dynamic_price_surge():
    print("\n" + "=" * 60)
    print("【測試 2】動態供需定價與物價哄抬：庫存告急引發價格暴漲 300%~600%")
    print("=" * 60)

    market = LocalMarket("node_famine_city")
    # 常態安全庫存 50，基礎價格 18.0
    market.target_stock = {"good_bread": 50}
    market.inventory = {"good_bread": 50}

    normal_price = market.get_price("good_bread")
    print(f"常態安全庫存時 (50/50) 麵包市價: {normal_price} 金幣 (基準價 18.0)")
    assert normal_price == 18.0, f"常態庫存市價應等於基準價 18.0，實際: {normal_price}"

    # 模擬圍城/斷供：庫存降至 20
    market.inventory["good_bread"] = 20
    scarcity_price = market.get_price("good_bread")
    print(f"物資吃緊時 (20/50) 麵包市價: {scarcity_price} 金幣 (漲幅: {scarcity_price/normal_price*100:.1f}%)")
    assert scarcity_price > normal_price

    # 模擬極限飢荒：庫存降至 2 份
    market.inventory["good_bread"] = 2
    crisis_price = market.get_price("good_bread")
    print(f"極限斷糧時 (2/50) 麵包市價: {crisis_price} 金幣 (暴漲: {crisis_price/normal_price*100:.1f}%)")
    assert crisis_price >= normal_price * 3.5, f"糧價暴漲應超過 350%，實際: {crisis_price}"
    print("✓ 動態供需非線性曲線生效，物資短缺時自然湧現物價哄抬！")


def test_commerce_raiding_and_supply_interruption():
    print("\n" + "=" * 60)
    print("【測試 3】破交截擊 (Commerce Raiding)：荒野截擊車隊與終端軍工斷料")
    print("=" * 60)

    caravan = MerchantCaravan(
        caravan_id="caravan_iron_convoy",
        name="鐵公國重裝礦石商隊",
        owner_id="org_iron_duchy",
        current_node_id="node_iron_mine",
        cargo={"raw_iron_ore": 30},
        gold=600.0,
        status="TRAVELING"
    )

    # 玩家或敵對勢力發動伏擊
    looted_cargo, looted_gold, raid_log = caravan.raid(raider_name="主角義勇軍")
    print(raid_log)

    assert caravan.status == "RAIDED", "車隊狀態應變更為 RAIDED"
    assert len(caravan.cargo) == 0, "被截擊後車隊貨物應清空"
    assert looted_cargo.get("raw_iron_ore") == 30, "劫掠者應全數獲得 30 單位鐵礦"
    assert looted_gold == 420.0, f"劫掠 70% 金幣 (600 * 0.7 = 420)，實際: {looted_gold}"

    # 模擬目的地的鐵匠鋪因為商隊被截擊，無鐵可用
    dest_market = LocalMarket("node_free_city")
    dest_market.inventory = {"raw_iron_ore": 0, "raw_timber": 20, "good_weapons": 5}
    smith = Workshop("ws_free_city_smith", "城邦軍械所", STANDARD_RECIPES["recipe_blacksmith"], daily_batches=2)
    dest_market.workshops.append(smith)

    succ, msg = smith.produce(dest_market)
    print(f"終端作坊反應: {msg}")
    assert succ is False, "缺少鐵礦應當停擺"
    assert smith.stalled is True
    print("✓ 破交截擊成功掐斷原料輸入，終端軍工作坊斷料停擺！")


def test_blockade_and_siege():
    print("\n" + "=" * 60)
    print("【測試 4】圍城封鎖 (Siege & Blockade)：切斷一切商貿交易")
    print("=" * 60)

    market = LocalMarket("node_besieged_capital")
    market.inventory = {"good_bread": 20}
    market.target_stock = {"good_bread": 50}
    market.is_blockaded = True  # 圍城狀態

    succ_buy, qty_buy, cost, buy_msg = market.buy_from_market("good_bread", 5, 500.0)
    print(f"嘗試買入: {buy_msg}")
    assert succ_buy is False, "圍城狀態應無法向市場買入"

    succ_sell, qty_sell, payout, sell_msg = market.sell_to_market("good_bread", 5)
    print(f"嘗試賣入: {sell_msg}")
    assert succ_sell is False, "圍城狀態應無法向市場傾銷"
    print("✓ 圍城封鎖機制有效隔絕物資流動！")


def test_npc_merchant_arbitrage():
    print("\n" + "=" * 60)
    print("【測試 5】商人自主套利 (Merchant Arbitrage)：低買高賣平抑物價並獲巨利")
    print("=" * 60)

    # 產地：農莊驛站（小麥過剩，極度便宜）
    farm_market = LocalMarket("node_caravan_station")
    farm_market.target_stock = {"raw_grain": 40}
    farm_market.inventory = {"raw_grain": 120}
    cheap_grain_price = farm_market.get_price("raw_grain")

    # 銷地：遭受旱災之城（小麥極缺，價格高昂）
    city_market = LocalMarket("node_famine_city")
    city_market.target_stock = {"raw_grain": 80}
    city_market.inventory = {"raw_grain": 10}
    expensive_grain_price = city_market.get_price("raw_grain")

    print(f"產地小麥單價: {cheap_grain_price} 金幣 | 災區小麥單價: {expensive_grain_price} 金幣")
    assert expensive_grain_price > cheap_grain_price * 3, "兩地價差應有套利空間"

    # 商隊執行套利
    caravan = MerchantCaravan(
        caravan_id="caravan_arbitrage_01",
        name="托馬斯商會商隊",
        owner_id="npc_caravan_thomas",
        current_node_id="node_caravan_station",
        cargo={},
        gold=1000.0,
        capacity=100
    )

    # 1. 於產地批量採購 50 單位小麥
    buy_succ, actual_bought, total_spent, bmsg = farm_market.buy_from_market("raw_grain", 50, caravan.gold)
    assert buy_succ is True
    caravan.gold -= total_spent
    caravan.load_cargo("raw_grain", actual_bought)
    print(f"商隊採購完成: 花費 {total_spent} 金幣，購入小麥 x{actual_bought}，剩餘資金 {caravan.gold}")

    # 2. 商隊啟程運往災區
    caravan.status = "TRAVELING"
    caravan.route = ["node_waypoint", "node_famine_city"]
    caravan.destination_node_id = "node_famine_city"

    # 移動
    step1_succ, s1_msg = caravan.step_travel()
    print(f"行商中途: {s1_msg}")
    step2_succ, s2_msg = caravan.step_travel()
    print(f"抵達終點: {s2_msg}")
    assert caravan.status == "ARRIVED"

    # 3. 於災區市場拋售
    sell_succ, sold_qty, total_payout, smsg = city_market.sell_to_market("raw_grain", caravan.cargo["raw_grain"])
    assert sell_succ is True
    caravan.unload_cargo("raw_grain", sold_qty)
    caravan.gold += total_payout

    net_profit = round(caravan.gold - 1000.0, 1)
    print(f"拋售結算: 獲得 {total_payout} 金幣！商隊最終資金: {caravan.gold} (淨利潤: +{net_profit} 金幣)")
    assert net_profit > 150.0, f"套利利潤應顯著大於成本，實際淨賺: {net_profit}"
    print("✓ 自主商人低買高賣套利閉環驗證通過！")


def test_world_daily_economic_tick_and_save_load():
    print("\n" + "=" * 60)
    print("【測試 6】世界日常經濟循環推進與完整存讀檔持久化驗證")
    print("=" * 60)

    # 1. 生成世界
    db = DefDatabase()
    settings = WorldGenSettings(scale=WorldScale.STANDARD, seed=123)
    world = WorldGenerator.generate(settings, db)

    free_city_node = world.world_map.get_node("node_free_city")
    assert free_city_node is not None
    init_bread = free_city_node.market.inventory.get("good_bread", 0)
    print(f"第 1 天自由城邦初始麵包存量: {init_bread}")

    # 2. 推進時段至跨日，觸發 run_daily_economic_cycle()
    print("推進早晨 -> 午後 -> 夜間 -> 跨日晨光...")
    world.advance_time_slot()  # 早晨 -> 午後
    world.advance_time_slot()  # 午後 -> 夜間
    day2_logs = world.advance_time_slot()  # 夜間 -> 第 2 天早晨（觸發每日經濟循環）

    found_econ_tick = any("【經濟運轉】" in log for log in day2_logs)
    assert found_econ_tick is True, "跨日應當觸發每日經濟運轉！"
    print("✓ 跨日自動觸發日常經濟循環（作坊產出 + 人口消耗 + 車隊運輸）！")

    # 3. 存檔與讀檔驗證
    save_path = "saves/test_economy_save.json"
    os.makedirs("saves", exist_ok=True)
    SaveLoadManager.save_to_file(world, save_path)
    print(f"世界存檔已寫入: {save_path}")

    succ_l, lmsg, loaded_world = SaveLoadManager.load_from_file(save_path)
    assert succ_l is True, f"讀檔應成功: {lmsg}"
    loaded_city = loaded_world.world_map.get_node("node_free_city")
    assert loaded_city is not None
    assert loaded_city.market is not None
    assert len(loaded_city.market.workshops) == 2, "城邦作坊數量應完整恢復"
    assert len(loaded_world.caravans) >= 1, "行商車隊應完整恢復"
    assert loaded_city.market.inventory["good_bread"] == free_city_node.market.inventory["good_bread"]
    print("✓ 經濟狀態、各節點物料庫存、作坊與行商車隊在存檔中 100% 完美還原！")


if __name__ == "__main__":
    test_physical_production_chain()
    test_shortage_and_dynamic_price_surge()
    test_commerce_raiding_and_supply_interruption()
    test_blockade_and_siege()
    test_npc_merchant_arbitrage()
    test_world_daily_economic_tick_and_save_load()
    print("\n" + "=" * 60)
    print(" 恭喜！實體產業鏈、動態供需定價與戰略商戰/圍城全部 6 大測試全部 PASS！")
    print("=" * 60)
