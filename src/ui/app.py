"""
RPG Simulator - Textual Modern TUI Application.
Combines 'Eye of the Beholder' First-Person Viewport with 'Undertale'-style contextual action buttons.
"""

import os
import sys
from typing import Optional, List, Dict, Any

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Button, RichLog
from textual.binding import Binding

# 確保搜尋路徑包含專案根目錄
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.core.traits import Trait, Tier, Category
from src.core.character import Character
from src.core.organization import Organization, OrgTier, Authority
from src.core.calendar import TimeSlot
from src.core.trait_synthesizer import TraitSynthesizer
from src.core.interactions import InteractionRegistry, InteractionResult
from src.engine.world import WorldState
from src.engine.def_loader import DefLoader
from src.ui.vignettes import render_viewport_ascii


# 場景定義
LOCATIONS = [
    {
        "id": "loc_market",
        "name": "奧斯提亞海灣長街",
        "type": "city",
        "desc": "繁華海港石造長街，商貿鼎盛，微風送來鹹澀的海水氣息。",
        "npc_ids": ["npc_caravan_thomas", "npc_artisan_bruno"],
    },
    {
        "id": "loc_garrison",
        "name": "治安戍衛守備所",
        "type": "fortress",
        "desc": "重甲哨兵肅立於城垛箭樓之上，精鋼刀戟在晨光下泛著森寒光芒。",
        "npc_ids": ["npc_guard_elena"],
    },
    {
        "id": "loc_ruins",
        "name": "古城秘術石殿殘址",
        "type": "ruins",
        "desc": "斷壁殘垣間，石壁上刻印著未知的因果真理銘文與幽幽靈光。",
        "npc_ids": ["npc_scholar_cyrus"],
    },
    {
        "id": "loc_gate",
        "name": "黑石荒原邊境隘口",
        "type": "wasteland",
        "desc": "天地蒼茫，狂風卷起黃沙，遠方地平線連接著無垠的未知危險荒域。",
        "npc_ids": ["npc_adventurer_kira"],
    },
]


APP_CSS = """
Screen {
    background: #0d1117;
    color: #c9d1d9;
}

#top_bar {
    dock: top;
    height: 3;
    background: #161b22;
    border-bottom: heavy #30363d;
    align: center middle;
    content-align: center middle;
    text-style: bold;
    color: #58a6ff;
}

#main_layout {
    height: 1fr;
    min-height: 15;
}

#left_hud {
    width: 28;
    background: #161b22;
    border-right: heavy #30363d;
    padding: 0 1;
}

#center_viewport_container {
    width: 1fr;
    background: #090d13;
    padding: 0 1;
}

#viewport_display {
    height: 1fr;
    border: round #388bfd;
    background: #040d1a;
    color: #79c0ff;
    padding: 0 1;
}

#viewport_display.lens_active {
    border: double #d2a8ff;
    background: #160a29;
    color: #e2c5ff;
}

#dialogue_box {
    height: 4;
    border: solid #30363d;
    background: #161b22;
    color: #f0f6fc;
    padding: 0 1;
    margin-top: 1;
}

#right_sidebar {
    width: 30;
    background: #161b22;
    border-left: heavy #30363d;
    padding: 0 1;
}

#event_log_panel {
    height: 5;
    border-top: heavy #30363d;
    background: #0d1117;
    color: #8b949e;
}

#bottom_command_deck {
    dock: bottom;
    height: 3;
    background: #161b22;
    border-top: double #58a6ff;
    align: center middle;
    padding: 0;
    overflow-x: auto;
}

.undertale_btn {
    margin: 0 1;
    padding: 0 1;
    height: 3;
    min-width: 12;
    text-style: bold;
    border: tall #8b949e;
}

.undertale_btn:hover {
    border: tall #ff7b72;
    background: #21262d;
}

#btn_move { color: #7ee787; border: tall #238636; }
#btn_interact { color: #79c0ff; border: tall #1f6feb; }
#btn_fuse { color: #d2a8ff; border: tall #8957e5; }
#btn_lens { color: #ffa657; border: tall #bd561d; }
#btn_council { color: #e3b341; border: tall #9e6a03; }
#btn_next_slot { color: #ff7b72; border: tall #da3633; }
"""


class RPGSimulatorApp(App):
    """
    RPG Simulator 現代終端 TUI 主程式
    魔眼殺機主視界 + 因果之眼透視 + Undertale 式底部互動艙
    """
    CSS = APP_CSS
    TITLE = "RPG Simulator: The Essence Weaver"

    BINDINGS = [
        Binding("1", "move", "換向探索", show=True),
        Binding("2", "interact", "角色互動", show=True),
        Binding("3", "fuse", "本質編織", show=True),
        Binding("4", "toggle_lens", "因果之眼", show=True),
        Binding("5", "council", "組織政務", show=True),
        Binding("6", "advance_slot", "時段推進", show=True),
        Binding("c", "cycle_target", "切換對象", show=True),
        Binding("tab", "toggle_lens", "因果之眼", show=False, priority=True),
        Binding("space", "advance_slot", "推進時段", show=False, priority=True),
        Binding("q", "quit", "離開遊戲", show=True),
    ]

    def __init__(self, world: Optional[WorldState] = None):
        super().__init__()
        self.world = world if world is not None else self._init_default_world()
        self.hero = (
            self.world.get_character("player_hero")
            or self.world.get_character("hero_01")
        )
        if not self.hero:
            self.hero = Character("player_hero", "無名少年 (主角)", rank_key="Chorji", is_awakened=True, gold=150.0)
            self.world.add_character(self.hero)

        self.current_location_idx = 0
        self.current_facing_target_idx = 0
        self.essence_lens_active = False
        self.dialogue_text = "你深吸一口氣，站在繁榮的奧斯提亞海灣長街上。眼前人流如織，微風送來鹹澀的海水氣息。"

    def _init_default_world(self) -> WorldState:
        """載入劇本並填充完整世界生態"""
        loader = DefLoader()
        defs_dir = os.path.join(ROOT_DIR, "defs")
        world = None
        if os.path.exists(defs_dir):
            loader.load_all_defs(defs_dir)
            world = loader.create_world_from_scenario("scenario_free_city_awakening")

        if world is None:
            world = WorldState()

        self._populate_city_world(world)
        return world

    def _populate_city_world(self, world: WorldState) -> None:
        """豐富世界 NPC、官職體系與社會關係"""
        # 1. 確保商隊托馬斯設定
        thomas = world.get_character("npc_caravan_thomas")
        if thomas:
            thomas.profession_id = "prof_merchant"
            thomas.gender = "male"
            thomas.age = 46
            if "rare_monopoly_baron" in world.trait_registry and world.trait_registry["rare_monopoly_baron"] not in thomas.acquired_traits:
                thomas.acquired_traits.append(world.trait_registry["rare_monopoly_baron"])

        # 2. 衛隊長艾蓮娜
        if "npc_guard_elena" not in world.characters:
            elena = Character("npc_guard_elena", "治安衛士·艾蓮娜", rank_key="Chorji", gold=80.0)
            elena.profession_id = "prof_guard"
            elena.gender = "female"
            elena.age = 24
            for tid in ["reg_human_body", "unc_veteran_instinct", "unc_iron_will"]:
                if tid in world.trait_registry:
                    elena.innate_traits.append(world.trait_registry[tid])
            world.add_character(elena)

        # 3. 奧秘學者賽勒斯
        if "npc_scholar_cyrus" not in world.characters:
            cyrus = Character("npc_scholar_cyrus", "奧秘學者·賽勒斯", rank_key="Acolyte", is_awakened=True, gold=200.0)
            cyrus.profession_id = "prof_scholar"
            cyrus.gender = "male"
            cyrus.age = 42
            for tid in ["reg_human_body", "rare_philosopher_reason", "rare_quantum_intuition"]:
                if tid in world.trait_registry:
                    cyrus.innate_traits.append(world.trait_registry[tid])
            world.add_character(cyrus)

        # 4. 鐵匠布魯諾
        if "npc_artisan_bruno" not in world.characters:
            bruno = Character("npc_artisan_bruno", "巧手工匠·布魯諾", rank_key="Chorji", gold=120.0)
            bruno.profession_id = "prof_artisan"
            bruno.gender = "male"
            bruno.age = 35
            for tid in ["reg_human_body", "unc_dwarf_forge_heart", "reg_iron_buckler"]:
                if tid in world.trait_registry:
                    bruno.innate_traits.append(world.trait_registry[tid])
            world.add_character(bruno)

        # 5. 荒野遊俠琪拉
        if "npc_adventurer_kira" not in world.characters:
            kira = Character("npc_adventurer_kira", "邊境遊俠·琪拉", rank_key="Chorji", gold=95.0)
            kira.profession_id = "prof_adventurer"
            kira.gender = "female"
            kira.age = 22
            for tid in ["reg_human_body", "unc_half_elf_vision", "unc_shadow_assassin"]:
                if tid in world.trait_registry:
                    kira.innate_traits.append(world.trait_registry[tid])
            world.add_character(kira)

        # 6. 套用內閣體系架構
        free_city = world.org_manager.get_org("org_free_city")
        if free_city and not free_city.offices:
            free_city.apply_council_template("feudal_fantasy")
            free_city.appoint_office("marshal", "npc_guard_elena")
            free_city.appoint_office("steward", "npc_scholar_cyrus")

        guild = world.org_manager.get_org("org_caravan_guild")
        if guild and not guild.offices:
            guild.apply_council_template("small_squad")
            guild.appoint_office("treasurer", "npc_caravan_thomas")

    def compose(self) -> ComposeResult:
        # 頂部狀態列
        yield Static("", id="top_bar")

        with Horizontal(id="main_layout"):
            # 左側面板 (主角屬性 HUD)
            with Vertical(id="left_hud"):
                yield Static(id="hud_hero_info")
                yield Static(id="hud_ap_mp")
                yield Static(id="hud_corruption_gold")
                yield Static(id="hud_traits")

            # 中央主視界 (魔眼殺機 第一人稱向前看)
            with Vertical(id="center_viewport_container"):
                yield Static(id="viewport_display")
                yield Static(id="dialogue_box")

            # 右側面板 (環境雷達與人物)
            with Vertical(id="right_sidebar"):
                yield Static(id="sidebar_location_info")
                yield Static(id="sidebar_npcs_present")
                yield Static(id="sidebar_council_status")

        # 事件日誌面板
        yield RichLog(id="event_log_panel", auto_scroll=True, markup=True)

        # 底部指令艙 (Undertale 風格按鈕)
        with Horizontal(id="bottom_command_deck"):
            yield Button("[1] 換向探索", id="btn_move", classes="undertale_btn")
            yield Button("[2] 角色互動", id="btn_interact", classes="undertale_btn")
            yield Button("[3] 本質編織", id="btn_fuse", classes="undertale_btn")
            yield Button("[4] 因果之眼", id="btn_lens", classes="undertale_btn")
            yield Button("[5] 組織政務", id="btn_council", classes="undertale_btn")
            yield Button("[6] 時段推進", id="btn_next_slot", classes="undertale_btn")

        yield Footer()

    def on_mount(self) -> None:
        """介面掛載完畢初始化渲染"""
        self.update_all_views()
        self.log_event("[green]✦ 世界初始化完成！歡迎踏入因果與本質的世界。[/green]")

    def get_current_location(self) -> Dict[str, Any]:
        """獲取當前所處場景"""
        return LOCATIONS[self.current_location_idx % len(LOCATIONS)]

    def get_present_npcs(self) -> List[Character]:
        """獲取當前場景中存活的 NPC 清單"""
        loc = self.get_current_location()
        npc_ids = loc.get("npc_ids", [])
        npcs = []
        for nid in npc_ids:
            c = self.world.get_character(nid)
            if c and c.is_alive:
                npcs.append(c)
        return npcs

    def get_facing_character(self) -> Optional[Character]:
        """獲取當前正對著的 NPC"""
        npcs = self.get_present_npcs()
        if not npcs:
            return None
        idx = self.current_facing_target_idx % len(npcs)
        return npcs[idx]

    def update_all_views(self) -> None:
        """全面刷新所有 UI 視窗"""
        # 1. 頂部列
        cal = self.world.calendar
        loc = self.get_current_location()
        top_text = f"📅 第 {cal.current_day} 天 【{cal.current_slot.value}】 (10 AP/時段)  │  📍 {loc['name']}  │  🌤 晨風吹拂，人流漸盛"
        self.query_one("#top_bar", Static).update(top_text)

        # 2. 左側主角 HUD
        ratio = self.hero.stress_ratio
        state, state_desc = self.hero.get_mental_state()
        corr_state = self.hero.get_corruption_state()[0]

        ap_bar = "■" * self.hero.current_ap + "□" * (10 - self.hero.current_ap)
        hero_info = f"""[bold yellow]★ {self.hero.name}[/bold yellow]
境界: [cyan]{self.hero.rank_def.name}[/cyan]
行動點: [{ap_bar}] {self.hero.current_ap}/10 AP"""
        self.query_one("#hud_hero_info", Static).update(hero_info)

        mp_info = f"""
[bold cyan]【心神維持負荷】[/bold cyan]
當前 MP: {self.hero.current_mp:.1f} / {self.hero.max_mp:.1f}
常駐負荷: {self.hero.calculate_sustained_load():.1f} ({ratio*100:.1f}%)
心識境界: [{state.value}]"""
        self.query_one("#hud_ap_mp", Static).update(mp_info)

        corr_info = f"""
[bold magenta]【靈魂腐化度】[/bold magenta]
腐化指數: {self.hero.corruption:.1f} / 100.0
心靈狀態: [{corr_state.value}]
金庫財富: [bold gold1]{self.hero.gold:.1f} 金[/bold gold1]"""
        self.query_one("#hud_corruption_gold", Static).update(corr_info)

        all_t = self.hero.all_traits
        traits_summary = f"""
[bold green]【掌握本質詞條 ({len(all_t)})】[/bold green]
{chr(10).join(['• ' + t.name for t in all_t[:4]]) if all_t else '• 暫無'}"""
        self.query_one("#hud_traits", Static).update(traits_summary)

        # 3. 中央主視界渲染
        facing_npc = self.get_facing_character()
        viewport = self.query_one("#viewport_display", Static)
        
        if self.essence_lens_active:
            viewport.add_class("lens_active")
        else:
            viewport.remove_class("lens_active")

        char_name = facing_npc.name if facing_npc else None
        char_prof = facing_npc.profession_id if facing_npc else "prof_merchant"
        char_traits = [t.name for t in facing_npc.all_traits] if facing_npc else []
        stress = facing_npc.stress_ratio if facing_npc else 0.0
        corr = facing_npc.corruption if facing_npc else 0.0

        ascii_art = render_viewport_ascii(
            location_type=loc["type"],
            location_name=loc["name"],
            facing_char_name=char_name,
            facing_char_prof=char_prof,
            essence_lens_active=self.essence_lens_active,
            char_traits=char_traits,
            stress_ratio=stress,
            corruption_val=corr
        )
        viewport.update(ascii_art)
        self.query_one("#dialogue_box", Static).update(f"[bold white]💬 對白旁白：[/bold white] {self.dialogue_text}")

        # 4. 右側資訊欄
        present_npcs = self.get_present_npcs()
        npc_lines = []
        for i, p in enumerate(present_npcs):
            is_facing = facing_npc and p.char_id == facing_npc.char_id
            prefix = "[bold green]▶[/bold green] " if is_facing else "  "
            prof_label = p.profession_id.replace("prof_", "")
            npc_lines.append(f"{prefix}{p.name} [{prof_label}]")
        if not npc_lines:
            npc_lines.append("[dim]  四下無人，唯見風塵...[/dim]")

        routes = []
        for i, l in enumerate(LOCATIONS):
            mark = "●" if i == (self.current_location_idx % len(LOCATIONS)) else "○"
            routes.append(f"{mark} {l['name']}")

        self.query_one("#sidebar_location_info", Static).update(
            "[bold yellow]🧭【周遭地圖方位】[/bold yellow]\n" + "\n".join(routes)
        )
        self.query_one("#sidebar_npcs_present", Static).update(
            f"[bold cyan]👥【眼前所見之人】[/bold cyan]\n" + "\n".join(npc_lines)
        )

        # 內閣職能概覽
        org_lines = ["[bold magenta]🏛【組織與內閣職能】[/bold magenta]"]
        for org in list(self.world.org_manager.all_orgs.values())[:2]:
            org_lines.append(f"• [bold]{org.name}[/bold]")
            if org.offices:
                for off in list(org.offices.values())[:2]:
                    holder = self.world.get_character(off.incumbent_id) if off.incumbent_id else None
                    h_name = holder.name if holder else "[dim]懸缺[/dim]"
                    org_lines.append(f"  └ {off.title}: {h_name}")
        self.query_one("#sidebar_council_status", Static).update("\n".join(org_lines))

    def log_event(self, text: str) -> None:
        """輸出至事件日誌面板"""
        log = self.query_one("#event_log_panel", RichLog)
        log.write(text)

    # ==========================================================================
    # 按鈕與指令動作處理
    # ==========================================================================

    def action_toggle_lens(self) -> None:
        """[Tab / 4] 切換因果之眼 (Essence Lens)"""
        self.essence_lens_active = not self.essence_lens_active
        if self.essence_lens_active:
            self.dialogue_text = "【因果之眼開啟】世間萬物的因果絲線與靈魂詞條在你的瞳孔中驟然點亮！"
            self.log_event("[magenta]👁 你開啟了因果之眼！看破了世間萬物的真實詞條本相。[/magenta]")
        else:
            self.dialogue_text = "【因果之眼關閉】視界恢復為凡俗肉眼所見之景。"
            self.log_event("[cyan]因果之眼已收斂，回歸凡人視界。[/cyan]")
        self.update_all_views()

    def action_cycle_target(self) -> None:
        """[c] 切換正對的 NPC 目標"""
        npcs = self.get_present_npcs()
        if not npcs:
            self.dialogue_text = "眼前此處並無其他人物，無法切換目光焦點。"
            self.update_all_views()
            return
        self.current_facing_target_idx += 1
        target = self.get_facing_character()
        if target:
            self.dialogue_text = f"你轉移視線，目光投向了站在前方的【{target.name}】。"
        self.update_all_views()

    def action_move(self) -> None:
        """[1] 換向探索 / 前往下一處城區或地標"""
        if self.hero.current_ap < 1:
            self.dialogue_text = "你的行動點數 (AP) 不足，無法在此時段繼續大範圍巡視！"
            self.update_all_views()
            return
        self.hero.current_ap -= 1
        self.current_location_idx += 1
        self.current_facing_target_idx = 0
        loc = self.get_current_location()
        self.dialogue_text = f"你邁步巡行抵達【{loc['name']}】。{loc['desc']}"
        self.log_event(f"[dim]主角消耗 1 AP 抵達【{loc['name']}】。[/dim]")
        self.update_all_views()

    def action_interact(self) -> None:
        """[2] 角色互動：與當前正對的 NPC 攀談問候"""
        target = self.get_facing_character()
        if not target:
            self.dialogue_text = "前方空無一人，無法進行互動。"
            self.update_all_views()
            return

        if self.hero.current_ap < 2:
            self.dialogue_text = "行動點數不足（交談需 2 AP），請推進時段或稍候！"
            self.update_all_views()
            return

        res: InteractionResult = self.world.execute_interaction("converse", self.hero.char_id, target.char_id)
        self.dialogue_text = res.message.splitlines()[0]
        self.log_event(f"[blue]💬 {res.message.replace(chr(10), ' ')}[/blue]")
        self.update_all_views()

    def action_fuse(self) -> None:
        """[3] 本質編織：融合自創詞條"""
        traits = self.hero.all_traits
        if len(traits) < 2:
            self.dialogue_text = "掌握的詞條數量不足 2 枚，無法進行本質重組！"
            self.update_all_views()
            return

        # 挑選前兩枚非同源詞條
        t1, t2 = traits[0], traits[1]
        succ, fuse_msg, new_t = TraitSynthesizer.execute_hero_fusion(self.hero, t1, t2)
        if succ and new_t:
            self.dialogue_text = f"【本質融合成功】誕生全新專屬詞條：【{str(new_t.tier)}】「{new_t.name}」！"
            self.log_event(f"[bold purple]✨ 本質編織成功！誕生自創詞條：【{str(new_t.tier)}】「{new_t.name}」[/bold purple]")
            # 自動嘗試刻印
            self.hero.imprint_trait(self.hero, new_t)
        else:
            self.dialogue_text = fuse_msg
        self.update_all_views()

    def action_council(self) -> None:
        """[5] 組織政務：檢視各職能效率，若正對 NPC 且符合條件可委任席位"""
        primary_org = self.world.org_manager.get_org("org_free_city") or (
            list(self.world.org_manager.all_orgs.values())[0] if self.world.org_manager.all_orgs else None
        )
        if not primary_org:
            self.dialogue_text = "當前世界尚無註冊之官僚勢力組織。"
            self.update_all_views()
            return

        facing_npc = self.get_facing_character()
        # 若正對著未任官之 NPC 且有懸缺，嘗試封官授爵
        if facing_npc:
            vacant = [o for o in primary_org.offices.values() if not o.incumbent_id]
            if vacant:
                office = vacant[0]
                succ, msg = primary_org.appoint_office(office.office_id, facing_npc.char_id)
                if succ:
                    self.dialogue_text = f"【公務任命】你代表城邦，委任 {facing_npc.name} 擔任「{office.title}」之職！"
                    self.log_event(f"[green]🏛 {msg}[/green]")
                    self.update_all_views()
                    return

        # 否則檢視內閣各權能運作效率
        eff_reports = []
        for auth in [Authority.MILITARY, Authority.TREASURY, Authority.INTERNAL_LAW]:
            eff, eff_msg = primary_org.get_authority_efficiency(auth, self.world.characters)
            eff_reports.append(f"{auth.value}: {eff*100:.0f}%")

        self.dialogue_text = f"【內閣政務】{primary_org.name} 國庫: {primary_org.treasury:.0f} 金 │ 效率: {' │ '.join(eff_reports)}"
        self.log_event(f"[cyan]🏛 {primary_org.name} 政務公文呈報完成。[/cyan]")
        self.update_all_views()

    def action_advance_slot(self) -> None:
        """[Space / 6] 推進時段 (早晨 -> 午後 -> 夜間 -> 晨曦跨日)"""
        logs = self.world.advance_time_slot()
        cal = self.world.calendar
        self.dialogue_text = f"鐘聲響徹海港，時序推進至 第 {cal.current_day} 天【{cal.current_slot.value}】！全員 AP 已重設。"
        for l in logs[:3]:
            self.log_event(f"[yellow]⏳ {l}[/yellow]")
        self.update_all_views()

    # 按鈕點擊綁定
    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn_move":
            self.action_move()
        elif btn_id == "btn_interact":
            self.action_interact()
        elif btn_id == "btn_fuse":
            self.action_fuse()
        elif btn_id == "btn_lens":
            self.action_toggle_lens()
        elif btn_id == "btn_council":
            self.action_council()
        elif btn_id == "btn_next_slot":
            self.action_advance_slot()


def main():
    app = RPGSimulatorApp()
    app.run()


if __name__ == "__main__":
    main()
