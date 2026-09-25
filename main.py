#!/usr/bin/env python3
"""
RPG Simulator - 主遊戲啟動入口 (Main Game Launcher)
執行本程式即可啟動現代終端 TUI 互動介面 (魔眼殺機視界 + Undertale 式底部互動艙)。

使用方式:
    python3 main.py                 # 啟動 TUI 介面
    python3 main.py --test          # 執行全部 10 大自動化測試套件
"""

import os
import sys
import argparse

# 將專案根目錄加入模組搜尋路徑
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


def run_all_tests():
    """執行全系統自動化測試套件"""
    import subprocess
    test_files = [
        "test_def_loader.py",
        "test_economy_simulation.py",
        "test_expanded_world.py",
        "test_integrated_system.py",
        "test_interactions_and_offices.py",
        "test_lifecycle_and_routines.py",
        "test_multiverse_framework.py",
        "test_trait_synthesizer.py",
        "test_travel_map.py",
        "test_ui_app.py",
    ]
    print("=" * 75)
    print("      【RPG Simulator: 執行全系統 10 大自動化測試套件】")
    print("=" * 75)
    all_passed = True
    for tfile in test_files:
        tpath = os.path.join(ROOT_DIR, tfile)
        if not os.path.exists(tpath):
            continue
        print(f"\n▶ 正在執行: {tfile} ...")
        res = subprocess.run([sys.executable, tpath])
        if res.returncode != 0:
            print(f"❌ {tfile} 執行失敗！")
            all_passed = False
            break

    if all_passed:
        print("\n" + "=" * 75)
        print("  🎉 全系統 10 大測試套件全部 100% 通過！")
        print("=" * 75)
    else:
        print("\n" + "=" * 75)
        print("  ❌ 測試套件中存在失敗項目，請檢閱輸出紀錄。")
        print("=" * 75)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="RPG Simulator - The Essence Weaver")
    parser.add_argument("--test", action="store_true", help="執行全系統 10 大自動化測試")
    parser.add_argument("--scenario", type=str, default="scenario_free_city_awakening", help="指定初始劇本 ID")
    args = parser.parse_args()

    if args.test:
        run_all_tests()
        return

    # 啟動 Textual TUI
    from src.ui.app import RPGSimulatorApp
    from src.engine.def_loader import DefLoader
    from src.engine.world import WorldState

    loader = DefLoader()
    defs_dir = os.path.join(ROOT_DIR, "defs")
    world = None
    if os.path.exists(defs_dir):
        loader.load_all_defs(defs_dir)
        world = loader.create_world_from_scenario(args.scenario)

    app = RPGSimulatorApp(world=world)
    app.run()


if __name__ == "__main__":
    main()
