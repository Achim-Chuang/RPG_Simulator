"""
Test Suite for RPG Simulator Textual TUI Application.
Verifies the 'Eye of the Beholder' First-Person Viewport, 'Undertale'-style Action Buttons,
Essence Lens Mode, Procedural Trait Synthesizer Trigger, and Calendar Slot Advance.
"""

import os
import sys
import asyncio
import unittest

# 加入根目錄到搜尋路徑
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.ui.app import RPGSimulatorApp, LOCATIONS


class TestRPGSimulatorUI(unittest.TestCase):
    """Textual TUI 介面全自動化測試套件"""

    def test_app_headless_workflow(self):
        """透過 Textual Pilot 模擬使用者點擊按鈕與快捷鍵操作"""
        async def run_scenario():
            app = RPGSimulatorApp()
            async with app.run_test(size=(120, 36)) as pilot:
                # 1. 介面初始化驗證
                self.assertIsNotNone(app.hero)
                self.assertEqual(app.hero.current_ap, 10)
                self.assertEqual(app.get_current_location()["id"], "loc_market")
                initial_npc = app.get_facing_character()
                self.assertIsNotNone(initial_npc)
                self.assertEqual(initial_npc.name, "商隊首領·托馬斯")

                # 2. 測試按鈕 [1] 換向探索 / 移動巡視
                await pilot.click("#btn_move")
                self.assertEqual(app.hero.current_ap, 9)
                self.assertEqual(app.get_current_location()["id"], "loc_garrison")
                guard_npc = app.get_facing_character()
                self.assertIsNotNone(guard_npc)
                self.assertEqual(guard_npc.name, "治安衛士·艾蓮娜")

                # 3. 測試按鈕 [4] 因果之眼 (Essence Lens)
                self.assertFalse(app.essence_lens_active)
                await pilot.click("#btn_lens")
                self.assertTrue(app.essence_lens_active)
                await asyncio.sleep(0.3)
                await pilot.click("#btn_lens")
                self.assertFalse(app.essence_lens_active)

                # 4. 測試按鈕 [2] 角色互動 (Converse)
                prev_ap = app.hero.current_ap
                await pilot.click("#btn_interact")
                # 交談消耗 2 AP
                self.assertEqual(app.hero.current_ap, prev_ap - 2)
                self.assertIn("艾蓮娜", app.dialogue_text)

                # 5. 測試按鈕 [3] 本質編織 (Trait Synthesizer)
                prev_trait_count = len(app.hero.all_traits)
                await pilot.click("#btn_fuse")
                self.assertIn("本質融合成功", app.dialogue_text)
                self.assertGreater(len(app.hero.all_traits), prev_trait_count)

                # 6. 測試按鈕 [5] 組織政務 (Council Administration)
                await pilot.click("#btn_council")
                self.assertIn("代表城邦", app.dialogue_text)

                # 7. 測試按鈕 [6] 時段推進 (Advance Slot)
                cal = app.world.calendar
                initial_slot = cal.current_slot
                await pilot.click("#btn_next_slot")
                self.assertNotEqual(cal.current_slot, initial_slot)
                self.assertEqual(app.hero.current_ap, 10)  # 時段推進 AP 重設為 10

                # 8. 測試全套鍵盤快捷鍵 (1-6, c, tab, space)
                await pilot.press("c")      # 切換目標
                await pilot.press("1")      # 換向探索
                await pilot.press("4")      # 切換因果之眼
                self.assertTrue(app.essence_lens_active)
                await pilot.press("tab")    # Tab 再次切換因果之眼
                self.assertFalse(app.essence_lens_active)
                await pilot.press("space")  # Space 推進時段
                await pilot.press("5")      # 組織政務

        asyncio.run(run_scenario())


def run_tests():
    print("=" * 75)
    print("      【RPG Simulator: Textual 現代終端 TUI 實機自動化測試】")
    print("=" * 75)

    suite = unittest.TestLoader().loadTestsFromTestCase(TestRPGSimulatorUI)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if result.wasSuccessful():
        print("\n" + "=" * 75)
        print("  ★ 魔眼殺機主視界、因果之眼透視、Undertale 式按鈕與全部快捷鍵測試 100% 通過！")
        print("=" * 75)
        return True
    else:
        print("\n" + "=" * 75)
        print("  ❌ 測試未通過，請檢查錯誤紀錄。")
        print("=" * 75)
        return False


if __name__ == "__main__":
    success = run_tests()
    if not success:
        sys.exit(1)
