"""
Integration Test for the World Map Graph, Node Movement, Travel Encounters, and Pathfinding.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.map import WorldMap, MapNode, MapEdge, NodeType, RoadType
from src.core.travel import TravelEngine, TravelEncounterType
from src.core.ruins import RuinsExplorationEngine
from src.engine.def_loader import DefLoader
from src.engine.world_generator import WorldGenerator, WorldGenSettings, WorldScale
from src.engine.save_load import SaveLoadManager


def run_travel_map_test():
    print("=" * 80)
    print("      【地圖與節點移動機制 (Travel Map & Encounters) 實機驗證】")
    print("=" * 80)

    # 1. 初始化資料庫與生成標準規模世界
    loader = DefLoader()
    defs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "defs")
    loader.load_all_defs(defs_dir)

    settings = WorldGenSettings(scale=WorldScale.STANDARD, seed=2024)
    world = WorldGenerator.generate(settings, loader.db)
    wmap = world.world_map

    print(f"\n[1. 大地圖網絡生成檢驗]")
    print(f"  * 節點總數: {len(wmap.nodes)} 個")
    print(f"  * 雙向道路連線: {len(wmap.edges)//2} 條")

    node_types = {}
    for n in wmap.nodes.values():
        node_types[n.node_type.value] = node_types.get(n.node_type.value, 0) + 1
    for k, v in node_types.items():
        print(f"    - {k}: {v} 處")

    # 2. 驗證主角起始位置
    hero = world.get_character("player_hero")
    assert hero is not None, "主角缺失！"
    assert hero.current_location_id == "node_caravan_station", "主角開局位置應為商會驛站！"
    start_node = wmap.get_node(hero.current_location_id)
    print(f"\n[2. 玩家初始位置] 主角身處: 「{start_node.name}」 (ID: {start_node.node_id})，當前 AP: {hero.current_ap}")

    # 3. 測試鄰居查詢與直達官道移動 (商會驛站 -> 自由城邦)
    print("\n" + "-" * 80)
    print("【3. 測試平坦商道移動 (HIGHWAY: 1 AP)】")
    neighbors = wmap.get_neighbors("node_caravan_station")
    print(f"「{start_node.name}」的相鄰連通節點:")
    for n, e in neighbors:
        print(f"  --> 前往「{n.name}」 | 道路類型: 【{e.road_type.value}】 | 消耗 AP: {e.ap_cost} | 危險度: {e.danger_rating*100:.0f}%")

    # 主角從商會驛站進城
    hero.current_ap = 10
    ok, enc, logs = TravelEngine.travel_to_node(wmap, hero, "node_free_city", seed=50)
    for l in logs:
        print(f"  {l}")

    assert ok, "進城移動失敗！"
    assert hero.current_location_id == "node_free_city", "主角未抵達自由城邦！"
    assert hero.current_ap == 9, "官道移動應精準扣除 1 AP！"
    print(f"  ✓ 移動成功！主角抵達「自由城邦·奧斯提亞」，剩餘 AP: {hero.current_ap}。")

    # 4. 測試導航尋路演算法 (從自由城邦導航至遠方遺跡)
    print("\n" + "-" * 80)
    print("【4. 最短路徑導航尋路 (BFS Pathfinding)】")
    # 找尋第一個遺跡節點
    ruin_nodes = [n for n in wmap.nodes.values() if n.node_type == NodeType.RUIN]
    target_ruin_node = ruin_nodes[0]
    print(f"目標目的地: 遠方遺跡「{target_ruin_node.name}」 (ID: {target_ruin_node.node_id})")

    path = wmap.find_path("node_free_city", target_ruin_node.node_id)
    assert path is not None, "未找到通往遺跡的路徑！"
    print(f"規劃導航路線 (共 {len(path)} 個節點):")
    for step_idx, nid in enumerate(path):
        n = wmap.get_node(nid)
        print(f"  [{step_idx+1}] {n.name} ({n.node_type.value})")

    # 5. 沿規劃路線行進並觸發旅途遭遇
    print("\n" + "-" * 80)
    print("【5. 沿荒野長途行進與旅途動態遭遇測試】")
    # 下一步前往商道中繼驛站
    next_node_id = path[1]
    ok, enc_type, travel_logs = TravelEngine.travel_to_node(wmap, hero, next_node_id, seed=12)
    for l in travel_logs:
        print(f"  {l}")
    assert ok, "前往中繼驛站失敗！"
    print(f"遭遇類型: {enc_type} | 主角當前位置: {hero.current_location_id} | 剩餘 AP: {hero.current_ap}")

    # 最後一段：從驛站深入險峻遺跡小徑 (TRAIL: 2 AP)
    final_node_id = path[2]
    ok, enc_type, travel_logs = TravelEngine.travel_to_node(wmap, hero, final_node_id, seed=15)
    for l in travel_logs:
        print(f"  {l}")
    assert ok, "抵達遺跡小徑失敗！"
    assert hero.current_location_id == target_ruin_node.node_id, "主角未成功抵達遺跡節點！"
    print(f"  ★ 主角克服長途跋涉，順利抵達目標遺跡「{target_ruin_node.name}」！剩餘 AP: {hero.current_ap}")

    # 6. 抵達遺跡後直接銜接遺跡探索
    print("\n" + "-" * 80)
    print("【6. 旅途終點：抵達遺跡現場並展開深度探索】")
    ruin_obj = next(r for r in world.ruins_sites if r.ruin_id == target_ruin_node.ruin_id)
    outcome, reward, explore_logs = RuinsExplorationEngine.explore_ruin(ruin_obj, hero, seed=42)
    for l in explore_logs:
        print(f"  {l}")
    print(f"探索結果: {outcome} | 獲得物品: {reward} | 主角剩餘 AP: {hero.current_ap}")

    # 7. 存讀檔持久化驗證
    print("\n" + "-" * 80)
    print("【7. 地圖圖譜與角色座標存讀檔驗證】")
    save_file = "saves/travel_world_save.json"
    s_ok, s_msg = SaveLoadManager.save_to_file(world, save_file)
    print(s_msg)
    assert s_ok, "存檔失敗！"

    l_ok, l_msg, restored_world = SaveLoadManager.load_from_file(save_file)
    print(l_msg)
    assert l_ok, "讀檔失敗！"

    # 深度驗證還原狀態
    r_hero = restored_world.get_character("player_hero")
    assert r_hero.current_location_id == target_ruin_node.node_id, "讀檔後主角所在地點不符！"
    assert len(restored_world.world_map.nodes) == len(wmap.nodes), "讀檔後地圖節點數量不符！"
    assert len(restored_world.world_map.edges) == len(wmap.edges), "讀檔後地圖道路連線數量不符！"
    print(f"  ✓ 驗證通過：主角位置完美還原於「{target_ruin_node.name}」，大地圖網絡 {len(restored_world.world_map.nodes)} 個節點完整無損。")

    print("\n" + "=" * 80)
    print("  ★ 地圖圖譜、道路 AP 消耗、路徑導航、旅途動態遭遇與存讀檔測試全部通過！")
    print("=" * 80)


if __name__ == "__main__":
    run_travel_map_test()
