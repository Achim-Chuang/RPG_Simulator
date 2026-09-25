"""
The Transcendent Rank, The First Awakened (Il), and the Meta-Truth of World Cycles.
Handles the climax encounter and the four ending paths:
1. Combat Victory -> Ascend to Transcendent (Omni-Weave Sandbox Mode)
2. Debate / Persuasion -> Willingly inherit Transcendent mantle
3. Refusal -> Walk away as Rank 5 Hutuktu
4. Shatter the Cycle -> Destroy the essence matrix forever
"""

from enum import Enum
from typing import Tuple, List, Optional
from .character import Character
from .combat import Combatant, PersonalCombatEngine
from .actions import ActionCheckEngine


class EndingChoice(Enum):
    COMBAT = "武力弒神 (以力量征服原初覺醒者)"
    PERSUADE = "哲學說服 (以理智與信念化解萬年心結)"
    REFUSE = "轉身抽離 (拒絕真相，逍遙人間)"
    SHATTER = "碎道絕陣 (承接神格，並徹底粉碎輪迴之環)"


class TranscendentEncounter:
    @staticmethod
    def get_first_awakened() -> Character:
        il = Character(
            char_id="npc_first_awakened_il",
            name="原初覺醒者·伊爾",
            rank_key="Transcendent",
            is_awakened=True,
            gold=99999.0
        )
        return il

    @staticmethod
    def can_trigger_encounter(hero: Character) -> Tuple[bool, str]:
        # 必須達到第四階 Nomenkhan，且累計互動豐富
        if hero.rank_key not in ("Nomenkhan", "Hutuktu"):
            return False, f"當前位階【{hero.rank_def.name}】尚未觸及因果邊界，無法感應原初神廟的召喚。"
        return True, "星界因果共鳴達成，古老時空的大門已為你敞開！"

    @staticmethod
    def get_prologue_dialogue() -> str:
        return (
            "【原初覺醒者·伊爾的嘆息】\n"
            "「你以為你是這個世上的『第二位』覺醒者嗎？\n"
            "  不……在你之前，已經有過數萬、數十萬個你。\n"
            "  每一個如你般覺醒了『洞悉與篡改本質』之人，都曾君臨天下，隨心所欲地改寫王朝、點石成金。\n"
            "  但當這個世界被隨意塗抹的因果徹底壓垮後，它就會崩解、重啟，從零再度輪迴……\n"
            "  世間遍佈的無數遠古遺跡，不是神話，而是過去無數個『你』通關後留下的荒塚！\n"
            "  我早已厭倦了這永無止境的毀滅與重塑，所以我編造了獵巫的歷史，將魔法封為禁忌……\n"
            "  然而，你終究還是走到了我的面前。\n"
            "  現在，告訴我——這一次，你想怎麼做？」"
        )

    @classmethod
    def resolve_choice(
        cls,
        hero: Character,
        choice: EndingChoice,
        seed: Optional[int] = None
    ) -> Tuple[bool, str, List[str]]:
        """
        結算玩家的終局選擇
        """
        logs = []
        logs.append(f"【玩家抉擇】: {choice.value}")

        if choice == EndingChoice.COMBAT:
            logs.append("你拔出了兵刃，決定用純粹的力量挑戰這片天地最初的意志！")
            hero_fighter = Combatant(
                id=hero.char_id,
                name=hero.name,
                side="A",
                hp=180,
                max_hp=180,
                atk=42,
                defense=18,
                spd=16,
                traits=["無所畏懼"]  # 弒神決戰，背水一戰絕不投降
            )
            il_boss = Combatant(
                id="boss_il",
                name="原初覺醒者·伊爾 (化身)",
                side="B",
                hp=130,
                max_hp=130,
                atk=28,
                defense=12,
                spd=12,
                traits=["百戰直覺", "無所畏懼"]
            )

            reason, _, combat_logs = PersonalCombatEngine.run_combat(
                side_a=[hero_fighter],
                side_b=[il_boss],
                attacker_side="A",
                attacker_ap=10
            )
            logs.extend(combat_logs)

            if hero_fighter.is_active:
                hero.rank_key = "Transcendent"
                msg = (
                    "★【武力登頂·超凡者誕生】！\n"
                    "伊爾的化身化作點點星光消散，世間唯一的『超凡者』神格灌注於你的靈魂！\n"
                    "你解鎖了【全知編織 (Omni-Weave)】！\n"
                    "精神力消耗清零，維持負荷歸零，你可在此刻的世界沙盒中任意修改任何物件的本質！"
                )
                logs.append(msg)
                return True, "ASCENDED_COMBAT", logs
            else:
                logs.append("✗ 挑戰失敗！你在伊爾浩瀚如星海的意志面前落敗，被時空風暴彈回凡世。")
                return False, "DEFEAT", logs

        elif choice == EndingChoice.PERSUADE:
            logs.append("你收起了兵刃，直視伊爾疲憊的眼眸，開始展開靈魂深處的哲學辯駁（嘴砲三連檢定）！")
            
            trait_names = [t.name for t in hero.innate_traits + hero.acquired_traits + hero.imprinted_traits]
            phil_mod = 5 if "博雅哲學真知" in trait_names else 3
            will_mod = 4 if "因果織命者" in trait_names or "野心家" in trait_names else 2

            # 第一輪：共情萬年孤寂 (Empathy)
            s1, l1 = ActionCheckEngine.execute_action(
                "辯駁第一階：理解並同理其萬年輪迴的疲憊",
                is_challenging=True,
                modifiers={"主角持有人性之光": phil_mod, "伊爾心防戒備": -1},
                seed=seed
            )
            logs.append(l1)
            if not s1:
                logs.append("伊爾冷笑著打斷了你：『未曾歷經永生者，豈知枯寂之重？』說服失敗。")
                return False, "PERSUADE_FAILED", logs

            # 第二輪：論證自由意志非徒勞 (Philosophy)
            s2, l2 = ActionCheckEngine.execute_action(
                "辯駁第二階：論證每一次重啟中眾生真摯的喜怒哀樂皆有意義",
                is_challenging=True,
                modifiers={"博雅哲學宏論": phil_mod, "眾生因果印記": +2},
                seed=(seed + 10) if seed else None
            )
            logs.append(l2)
            if not s2:
                logs.append("伊爾搖了搖頭：『一切皆是虛妄。』說服失敗。")
                return False, "PERSUADE_FAILED", logs

            # 第三輪：承諾承擔未來的重量 (Willpower)
            s3, l3 = ActionCheckEngine.execute_action(
                "辯駁第三階：向其許下承諾，接替他的重負，走出新的可能性",
                is_challenging=True,
                modifiers={"主角堅定道心": will_mod, "破局宿命感召": +3},
                seed=(seed + 20) if seed else None
            )
            logs.append(l3)
            if not s3:
                logs.append("說服在最後一刻功虧一簣。")
                return False, "PERSUADE_FAILED", logs

            hero.rank_key = "Transcendent"

            msg = (
                "★【心道解脫·平和傳承】！\n"
                "伊爾長長地舒了一口氣，露出了萬年來的第一抹微笑。\n"
                "『那麼……這座沙盒的下一頁，就交給你來執筆了。』\n"
                "他主動將超凡神格注入你的心識，安詳化道。你晉升為唯一【超凡者】，獲得任意修改全知權柄！"
            )
            logs.append(msg)
            return True, "ASCENDED_PERSUADE", logs

        elif choice == EndingChoice.REFUSE:
            hero.rank_key = "Hutuktu"
            msg = (
                "【轉身離去·大隱於市】\n"
                "你對伊爾笑了笑：『世界的真相如何，與我何干？我只想回到人間，喝我的酒，愛我的人。』\n"
                "伊爾愕然片刻，隨即放聲大笑。他為你打開了回歸之路。\n"
                "你維持著第五階【呼圖克圖】的不朽力量返回世俗，成為大陸傳說中來去無蹤的神秘仙客。"
            )
            logs.append(msg)
            return True, "WALK_AWAY", logs

        elif choice == EndingChoice.SHATTER:
            hero.rank_key = "Chorji"
            hero.is_awakened = False
            msg = (
                "★【碎道絕仙·終破輪迴】！\n"
                "在接過超凡權柄的剎那，你沒有重塑世界，而是以無上神念捏碎了整個『詞條法則』！\n"
                "天穹泛起璀璨無比的琉璃碎光，所有魔法本質隨風消逝，世間不再有覺醒者，亦不再有神明。\n"
                "世界徹底掙脫了被反覆重啟的詛咒，真正邁向了生老病死、踏實自由的凡人歷史時代。"
            )
            logs.append(msg)
            return True, "CYCLE_SHATTERED", logs

        return False, "UNKNOWN", logs
