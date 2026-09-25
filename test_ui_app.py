"""
Test Suite for RPG Simulator Textual TUI Application.
Verifies the 'Eye of the Beholder' First-Person Viewport, Compact Command Bar,
Essence Lens Mode, Location Travel Modal, Trait Inspection Modal,
Player-Chosen Synthesis Modal, Target Trait Modification Modal, and Time Slot Advancement.
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
        """透過 Textual Pilot 模擬使用者點擊按鈕、彈窗互動與快捷鍵操作"""
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

                # 2. 測試地點選擇彈窗 (LocationSelectModal) - 自選前往目的地，不盲目浪費 AP
                await pilot.press("1")
                await pilot.pause()
                self.assertGreater(len(app.screen_stack), 1)
                await pilot.press("2")  # 選擇前往第 2 處: 治安戍衛守備所
                await pilot.pause()
                self.assertEqual(app.hero.current_ap, 9)
                self.assertEqual(app.get_current_location()["id"], "loc_garrison")
                guard_npc = app.get_facing_character()
                self.assertIsNotNone(guard_npc)
                self.assertEqual(guard_npc.name, "治安衛士·艾蓮娜")

                # 3. 測試主角狀態與詞條百科、行囊檢視彈窗 (InspectModal)
                await pilot.press("i")
                await pilot.pause()
                self.assertGreater(len(app.screen_stack), 1)
                await pilot.press("escape")
                await pilot.pause()
                self.assertEqual(len(app.screen_stack), 1)

                # 4. 測試自選原料之本質編織彈窗 (TraitSynthesizeModal)
                prev_trait_count = len(app.hero.all_traits)
                await pilot.press("3")
                await pilot.pause()
                self.assertGreater(len(app.screen_stack), 1)
                await pilot.press("1")  # 選擇原料一
                await pilot.pause()
                await pilot.press("2")  # 選擇原料二並啟動融合
                await pilot.pause()
                self.assertIn("本質融合成功", app.dialogue_text)
                self.assertGreater(len(app.hero.all_traits), prev_trait_count)
                self.assertGreater(len(app.hero.custom_traits), 0)

                # 5. 測試修改他人詞條彈窗 (ModifyTargetTraitModal)
                await pilot.press("m")
                await pilot.pause()
                self.assertGreater(len(app.screen_stack), 1)
                await pilot.press("2")  # 選擇 [2] 洗鍊重塑變異
                await pilot.pause()
                self.assertIn("因果洗鍊成功", app.dialogue_text)

                # 6. 測試按鈕點擊：因果之眼 (Essence Lens)
                self.assertFalse(app.essence_lens_active)
                await pilot.click("#btn_lens")
                self.assertTrue(app.essence_lens_active)
                await asyncio.sleep(0.3)
                await pilot.click("#btn_lens")
                self.assertFalse(app.essence_lens_active)

                # 7. 測試角色交談 (Converse)
                prev_ap = app.hero.current_ap
                await pilot.click("#btn_interact")
                self.assertEqual(app.hero.current_ap, prev_ap - 2)
                self.assertIn("艾蓮娜", app.dialogue_text)

                # 8. 測試組織政務 (Council)
                await pilot.click("#btn_council")
                self.assertIn("代表城邦", app.dialogue_text)

                # 9. 測試推進時段 (Advance Slot)
                cal = app.world.calendar
                initial_slot = cal.current_slot
                await pilot.click("#btn_next_slot")
                self.assertNotEqual(cal.current_slot, initial_slot)
                self.assertEqual(app.hero.current_ap, 10)  # 時段推進 AP 重設為 10

                # 10. 測試切換目標與快捷鍵
                await pilot.press("c")
                await pilot.press("tab")  # Tab 開啟因果之眼
                self.assertTrue(app.essence_lens_active)
                await pilot.press("tab")  # Tab 關閉因果之眼
                self.assertFalse(app.essence_lens_active)

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
        print("  ★ 地點自選、狀態百科、自選原料編織、篡改他人詞條與全部快捷鍵測試 100% 通過！")
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
