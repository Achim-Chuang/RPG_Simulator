"""
RPG Simulator - Textual Modern TUI Application.
Combines 'Eye of the Beholder' First-Person Viewport with Contextual Action Deck & Interactive Modals.
"""

import os
import sys
import copy
from typing import Optional, List, Dict, Any, Tuple

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Static, Button, RichLog
from textual.binding import Binding
from textual.screen import ModalScreen

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
    min-height: 12;
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
    height: 4;
    border-top: heavy #30363d;
    background: #0d1117;
    color: #8b949e;
}

#bottom_command_deck {
    dock: bottom;
    height: 3;
    background: #161b22;
    border-top: double #58a6ff;
    padding: 0;
    align: center middle;
}

.cmd_row {
    height: 1;
    align: center middle;
    margin: 0;
}

.cmd_btn {
    height: 1;
    min-width: 11;
    padding: 0 1;
    margin: 0 1;
    border: none;
    background: #21262d;
    text-style: bold;
    color: #c9d1d9;
}

.cmd_btn:hover {
    background: #30363d;
    color: #58a6ff;
}

#btn_loc { color: #7ee787; }
#btn_interact { color: #79c0ff; }
#btn_synth { color: #d2a8ff; }
#btn_lens { color: #ffa657; }
#btn_council { color: #e3b341; }
#btn_next_slot { color: #ff7b72; }
#btn_inspect { color: #58a6ff; }
#btn_modify { color: #f0883e; }
#btn_cycle { color: #56d364; }
#btn_quit { color: #8b949e; }

/* 模態視窗樣式 */
ModalScreen {
    align: center middle;
    background: rgba(0, 0, 0, 0.75);
}

.modal_dialog {
    width: 72;
    max-height: 85%;
    background: #161b22;
    border: heavy #58a6ff;
    padding: 1 2;
}

.modal_title {
    text-align: center;
    text-style: bold;
    color: #58a6ff;
    border-bottom: solid #30363d;
    padding-bottom: 1;
    margin-bottom: 1;
}

.modal_scroll {
    height: 1fr;
    max-height: 18;
    overflow-y: auto;
}

.modal_btn_row {
    height: 3;
    margin-top: 1;
    align: center middle;
}

.modal_action_btn {
    margin: 0 1;
    height: 2;
    background: #238636;
    color: white;
}

.modal_cancel_btn {
    margin: 0 1;
    height: 2;
    background: #da3633;
    color: white;
}

.modal_select_btn {
    margin: 0 0 1 0;
    width: 100%;
    height: 2;
    content-align: left middle;
    background: #21262d;
    border: none;
}

.modal_select_btn:hover {
    background: #388bfd;
    color: white;
}
"""


# ==============================================================================
# 互動彈窗 1：前往地區 / 快速移動導航 (LocationSelectModal)
# ==============================================================================

class LocationSelectModal(ModalScreen[Optional[int]]):
    """大地圖快速巡行與地區前往彈窗"""
    BINDINGS = [
        Binding("escape", "cancel", "取消", show=True, priority=True),
        Binding("1", "sel_0", "1", show=False, priority=True),
        Binding("2", "sel_1", "2", show=False, priority=True),
        Binding("3", "sel_2", "3", show=False, priority=True),
        Binding("4", "sel_3", "4", show=False, priority=True),
    ]

    def __init__(self, current_idx: int, world: WorldState):
        super().__init__()
        self.current_idx = current_idx
        self.world = world

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal_dialog"):
            yield Static("🧭【大地圖快速巡行：選擇欲前往的地區】", classes="modal_title")
            with ScrollableContainer(classes="modal_scroll"):
                for i, loc in enumerate(LOCATIONS):
                    is_cur = (i == self.current_idx % len(LOCATIONS))
                    tag = " [bold green]【當前所處地點】[/bold green]" if is_cur else " [cyan](消耗 1 AP)[/cyan]"
                    npcs = [self.world.get_character(nid).name for nid in loc["npc_ids"] if self.world.get_character(nid)]
                    npc_str = "、".join(npcs) if npcs else "無"
                    desc_text = f"[bold yellow][{i+1}] {loc['name']}[/bold yellow]{tag}\n  {loc['desc']}\n  👥 常駐居民: {npc_str}\n"
                    yield Static(desc_text)
            with Horizontal(classes="modal_btn_row"):
                for i, loc in enumerate(LOCATIONS):
                    yield Button(f"[{i+1}] {loc['name'][:4]}", id=f"btn_loc_{i}", classes="modal_action_btn")
                yield Button("[Esc] 取消", id="btn_cancel_loc", classes="modal_cancel_btn")

    def action_cancel(self): self.dismiss(None)
    def action_sel_0(self): self.dismiss(0)
    def action_sel_1(self): self.dismiss(1)
    def action_sel_2(self): self.dismiss(2)
    def action_sel_3(self): self.dismiss(3)

    def on_button_pressed(self, event: Button.Pressed):
        bid = event.button.id
        if bid and bid.startswith("btn_loc_"):
            idx = int(bid.replace("btn_loc_", ""))
            self.dismiss(idx)
        else:
            self.dismiss(None)


# ==============================================================================
# 互動彈窗 2：角色修為狀態、詞條百科與行囊全覽 (InspectModal)
# ==============================================================================

class InspectModal(ModalScreen[None]):
    """主角詳細狀態、詞條百科與行囊檢視彈窗"""
    BINDINGS = [
        Binding("escape", "close", "關閉", show=True, priority=True),
        Binding("enter", "close", "關閉", show=True, priority=True),
        Binding("i", "close", "關閉", show=True, priority=True),
    ]

    def __init__(self, hero: Character):
        super().__init__()
        self.hero = hero

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal_dialog"):
            yield Static("📜【主角修為、靈魂詞條本相與行囊全覽】", classes="modal_title")
            with ScrollableContainer(classes="modal_scroll"):
                ratio = self.hero.stress_ratio
                state, state_desc = self.hero.get_mental_state()
                corr_state, _ = self.hero.get_corruption_state()

                # 1. 角色修為狀態
                status_block = f"""[bold yellow]★ {self.hero.name}[/bold yellow] (ID: {self.hero.char_id})
• 境界位階: [cyan]{self.hero.rank_def.name} ({self.hero.rank_key})[/cyan]  │  行動點數: [green]{self.hero.current_ap}/10 AP[/green]
• 精神法力 (MP): [bold cyan]{self.hero.current_mp:.1f} / {self.hero.max_mp:.1f}[/bold cyan]
• 心神維持負荷: [bold red]{self.hero.calculate_sustained_load():.1f} MP ({ratio*100:.1f}%)[/bold red]  --> 狀態: [{state.value}]
  [dim]{state_desc}[/dim]
• 靈魂腐化度: [magenta]{self.hero.corruption:.1f} / 100.0[/magenta]  --> 靈性境界: [{corr_state.value}]
• 金庫持有金幣: [bold gold1]{self.hero.gold:.1f} 枚金幣[/bold gold1]
----------------------------------------------------------------------"""
                yield Static(status_block)

                # 2. 掌握詞條詳細條目解析
                yield Static("[bold green]🧬【掌握本質詞條詳細條目 (含數值修正與親代溯源)】[/bold green]")
                all_traits = self.hero.all_traits
                if not all_traits:
                    yield Static("[dim]當前尚未掌握任何本質詞條。[/dim]")
                else:
                    for i, t in enumerate(all_traits):
                        cat_name = "專屬自創" if getattr(t, "is_synthetic", False) else t.category.value
                        tags_str = ", ".join(t.tags) if t.tags else "無標籤"

                        mods_list = []
                        for k, v in t.modifiers.items():
                            val_str = f"+{v*100:.0f}%" if isinstance(v, float) and v < 5.0 else f"{v:+.1f}"
                            mods_list.append(f"{k}: {val_str}")
                        mods_str = " | ".join(mods_list) if mods_list else "無直接屬性修正"

                        parents_info = f" [親代溯源: {', '.join(t.parents)}]" if getattr(t, 'parents', None) else ""

                        t_card = f"""[bold white]{i+1}. 【{str(t.tier)}】「{t.name}」[/bold white] [{cat_name}] {parents_info}
   • 靈魂標籤: [cyan]{tags_str}[/cyan]
   • 描述說明: {t.description}
   • 屬性增益: [green]{mods_str}[/green]
   • 心神常駐維持: [yellow]{t.base_load:.1f} MP[/yellow]  │  靈魂腐化變動: [magenta]{t.corruption_delta:+.1f}[/magenta]"""
                        yield Static(t_card)

                # 3. 行囊裝備與器物
                yield Static("\n----------------------------------------------------------------------")
                yield Static("[bold yellow]🎒【行囊與持有器物 (Artifacts)】[/bold yellow]")
                artifacts = [t for t in all_traits if t.category == Category.ARTIFACT]
                if not artifacts:
                    yield Static("[dim]行囊中目前無任何器物法寶，僅隨身攜帶金幣與靈魂本質。[/dim]")
                else:
                    for a in artifacts:
                        yield Static(f"• 📦【{str(a.tier)}】「{a.name}」 - {a.description}")

            with Horizontal(classes="modal_btn_row"):
                yield Button("[Enter / Esc] 關閉面板", id="btn_close_inspect", classes="modal_action_btn")

    def action_close(self):
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed):
        self.dismiss(None)


# ==============================================================================
# 互動彈窗 3：自選原料編織自創詞條 (TraitSynthesizeModal)
# ==============================================================================

class TraitSynthesizeModal(ModalScreen[Optional[Tuple[Trait, Trait]]]):
    """自選原料編織自創詞條彈窗"""
    BINDINGS = [
        Binding("escape", "cancel", "取消", show=True, priority=True),
        Binding("1", "sel_1", "1", show=False, priority=True),
        Binding("2", "sel_2", "2", show=False, priority=True),
        Binding("3", "sel_3", "3", show=False, priority=True),
        Binding("4", "sel_4", "4", show=False, priority=True),
        Binding("5", "sel_5", "5", show=False, priority=True),
        Binding("6", "sel_6", "6", show=False, priority=True),
        Binding("7", "sel_7", "7", show=False, priority=True),
        Binding("8", "sel_8", "8", show=False, priority=True),
        Binding("9", "sel_9", "9", show=False, priority=True),
    ]

    def __init__(self, hero: Character):
        super().__init__()
        self.hero = hero
        self.traits = hero.all_traits
        self.selected_p1: Optional[int] = None
        self.selected_p2: Optional[int] = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal_dialog"):
            yield Static("✨【本質編織者：自主選擇兩枚原料進行靈魂重構】", classes="modal_title")
            with ScrollableContainer(classes="modal_scroll"):
                yield Static(id="synthesize_instruction")
                for i, t in enumerate(self.traits[:9]):
                    tags = ", ".join(t.tags) if t.tags else "無"
                    yield Button(
                        f"[{i+1}] 【{str(t.tier)}】「{t.name}」 (標籤: {tags})",
                        id=f"btn_trait_{i}",
                        classes="modal_select_btn"
                    )
            with Horizontal(classes="modal_btn_row"):
                yield Button("重選第一枚", id="btn_reset_selection", classes="modal_cancel_btn")
                yield Button("[Esc] 取消", id="btn_cancel_synth", classes="modal_cancel_btn")

    def on_mount(self):
        self.update_step_view()

    def update_step_view(self):
        instr = self.query_one("#synthesize_instruction", Static)
        if self.selected_p1 is None:
            instr.update("[bold cyan]步驟 1/2：請點擊或按數字鍵選擇【第一枚原料詞條】[/bold cyan]")
        elif self.selected_p2 is None:
            t1 = self.traits[self.selected_p1]
            instr.update(f"[bold green]已選原料一：【{str(t1.tier)}】「{t1.name}」[/bold green]\n[bold yellow]步驟 2/2：請點擊或按數字鍵選擇【第二枚原料詞條】進行交融[/bold yellow]")

    def handle_select_idx(self, idx: int):
        if idx >= len(self.traits):
            return
        if self.selected_p1 is None:
            self.selected_p1 = idx
            self.update_step_view()
        elif self.selected_p2 is None:
            if idx == self.selected_p1:
                return
            self.selected_p2 = idx
            t1 = self.traits[self.selected_p1]
            t2 = self.traits[self.selected_p2]
            self.dismiss((t1, t2))

    def action_cancel(self): self.dismiss(None)
    def action_sel_1(self): self.handle_select_idx(0)
    def action_sel_2(self): self.handle_select_idx(1)
    def action_sel_3(self): self.handle_select_idx(2)
    def action_sel_4(self): self.handle_select_idx(3)
    def action_sel_5(self): self.handle_select_idx(4)
    def action_sel_6(self): self.handle_select_idx(5)
    def action_sel_7(self): self.handle_select_idx(6)
    def action_sel_8(self): self.handle_select_idx(7)
    def action_sel_9(self): self.handle_select_idx(8)

    def on_button_pressed(self, event: Button.Pressed):
        bid = event.button.id
        if bid and bid.startswith("btn_trait_"):
            idx = int(bid.replace("btn_trait_", ""))
            self.handle_select_idx(idx)
        elif bid == "btn_reset_selection":
            self.selected_p1 = None
            self.selected_p2 = None
            self.update_step_view()
        else:
            self.dismiss(None)


# ==============================================================================
# 互動彈窗 4：篡改/編織/修改他人詞條 (ModifyTargetTraitModal)
# ==============================================================================

class ModifyTargetTraitModal(ModalScreen[Optional[Dict[str, Any]]]):
    """篡改/編織/修改他人詞條彈窗"""
    BINDINGS = [
        Binding("escape", "cancel", "取消", show=True, priority=True),
        Binding("1", "sel_1", "1", show=False, priority=True),
        Binding("2", "sel_2", "2", show=False, priority=True),
        Binding("3", "sel_3", "3", show=False, priority=True),
    ]

    def __init__(self, actor: Character, target: Character):
        super().__init__()
        self.actor = actor
        self.target = target
        self.target_traits = target.all_traits

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal_dialog"):
            yield Static(f"👁【因果神術：篡改 {self.target.name} 的靈魂本相】", classes="modal_title")
            with ScrollableContainer(classes="modal_scroll"):
                t_names = [f"【{str(t.tier)}】「{t.name}」" for t in self.target_traits]
                t_list_str = "、".join(t_names) if t_names else "無任何詞條"

                info = f"""[bold yellow]目標對象：{self.target.name}[/bold yellow] ({self.target.profession_id.replace('prof_', '')})
境界: {self.target.rank_def.name}  │  常駐負荷: {self.target.stress_ratio*100:.1f}%  │  腐化: {self.target.corruption:.1f}/100
當前持有詞條: {t_list_str}

[bold cyan]請選擇欲施展的因果靈魂權能：[/bold cyan]"""
                yield Static(info)

                yield Button(
                    f"[1] 強行灌注刻印 (Imprint)\n    將你自創的專屬本質注入其靈魂 (需 3 AP, 精神力)",
                    id="btn_mode_imprint",
                    classes="modal_select_btn"
                )
                yield Button(
                    f"[2] 洗鍊重塑變異 (Mutate/Refine)\n    以神識沖刷其現有詞條，重塑數值並淨化腐化 (需 2 AP, 25 MP)",
                    id="btn_mode_mutate",
                    classes="modal_select_btn"
                )
                yield Button(
                    f"[3] 抽取剝離本質 (Extract/Strip)\n    強行奪取其一項詞條收為己有，大幅降低好感 (需 3 AP, 35 MP)",
                    id="btn_mode_extract",
                    classes="modal_select_btn"
                )
            with Horizontal(classes="modal_btn_row"):
                yield Button("[Esc] 取消", id="btn_cancel_modify", classes="modal_cancel_btn")

    def action_cancel(self): self.dismiss(None)
    def action_sel_1(self): self.dismiss({"action": "imprint"})
    def action_sel_2(self): self.dismiss({"action": "mutate"})
    def action_sel_3(self): self.dismiss({"action": "extract"})

    def on_button_pressed(self, event: Button.Pressed):
        bid = event.button.id
        if bid == "btn_mode_imprint":
            self.dismiss({"action": "imprint"})
        elif bid == "btn_mode_mutate":
            self.dismiss({"action": "mutate"})
        elif bid == "btn_mode_extract":
            self.dismiss({"action": "extract"})
        else:
            self.dismiss(None)


# ==============================================================================
# 主應用程式：RPGSimulatorApp
# ==============================================================================

class RPGSimulatorApp(App):
    """
    RPG Simulator 現代終端 TUI 主程式
    魔眼殺機主視界 + 因果之眼透視 + 精簡指令列與全套互動彈窗
    """
    CSS = APP_CSS
    TITLE = "RPG Simulator: The Essence Weaver"

    BINDINGS = [
        Binding("1", "open_travel", "前往地區", show=True),
        Binding("2", "interact", "角色互動", show=True),
        Binding("3", "open_synthesize", "本質編織", show=True),
        Binding("4", "toggle_lens", "因果之眼", show=True),
        Binding("5", "council", "組織政務", show=True),
        Binding("6", "advance_slot", "時段推進", show=True),
        Binding("i", "open_inspect", "狀態行囊", show=True),
        Binding("m", "open_modify_target", "修改他人", show=True),
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
        thomas = world.get_character("npc_caravan_thomas")
        if thomas:
            thomas.profession_id = "prof_merchant"
            thomas.gender = "male"
            thomas.age = 46
            if "rare_monopoly_baron" in world.trait_registry and world.trait_registry["rare_monopoly_baron"] not in thomas.acquired_traits:
                thomas.acquired_traits.append(world.trait_registry["rare_monopoly_baron"])

        if "npc_guard_elena" not in world.characters:
            elena = Character("npc_guard_elena", "治安衛士·艾蓮娜", rank_key="Chorji", gold=80.0)
            elena.profession_id = "prof_guard"
            elena.gender = "female"
            elena.age = 24
            for tid in ["reg_human_body", "unc_veteran_instinct", "unc_iron_will"]:
                if tid in world.trait_registry:
                    elena.innate_traits.append(world.trait_registry[tid])
            world.add_character(elena)

        if "npc_scholar_cyrus" not in world.characters:
            cyrus = Character("npc_scholar_cyrus", "奧秘學者·賽勒斯", rank_key="Acolyte", is_awakened=True, gold=200.0)
            cyrus.profession_id = "prof_scholar"
            cyrus.gender = "male"
            cyrus.age = 42
            for tid in ["reg_human_body", "rare_philosopher_reason", "rare_quantum_intuition"]:
                if tid in world.trait_registry:
                    cyrus.innate_traits.append(world.trait_registry[tid])
            world.add_character(cyrus)

        if "npc_artisan_bruno" not in world.characters:
            bruno = Character("npc_artisan_bruno", "巧手工匠·布魯諾", rank_key="Chorji", gold=120.0)
            bruno.profession_id = "prof_artisan"
            bruno.gender = "male"
            bruno.age = 35
            for tid in ["reg_human_body", "unc_dwarf_forge_heart", "reg_iron_buckler"]:
                if tid in world.trait_registry:
                    bruno.innate_traits.append(world.trait_registry[tid])
            world.add_character(bruno)

        if "npc_adventurer_kira" not in world.characters:
            kira = Character("npc_adventurer_kira", "邊境遊俠·琪拉", rank_key="Chorji", gold=95.0)
            kira.profession_id = "prof_adventurer"
            kira.gender = "female"
            kira.age = 22
            for tid in ["reg_human_body", "unc_half_elf_vision", "unc_shadow_assassin"]:
                if tid in world.trait_registry:
                    kira.innate_traits.append(world.trait_registry[tid])
            world.add_character(kira)

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

        # 底部指令艙 (精簡 2 列指令條，永不被視窗遮蔽)
        with Vertical(id="bottom_command_deck"):
            with Horizontal(classes="cmd_row"):
                yield Button("[1] 前往地區", id="btn_loc", classes="cmd_btn")
                yield Button("[2] 角色互動", id="btn_interact", classes="cmd_btn")
                yield Button("[3] 本質編織", id="btn_synth", classes="cmd_btn")
                yield Button("[4] 因果之眼", id="btn_lens", classes="cmd_btn")
                yield Button("[5] 組織政務", id="btn_council", classes="cmd_btn")
            with Horizontal(classes="cmd_row"):
                yield Button("[6] 推進時段", id="btn_next_slot", classes="cmd_btn")
                yield Button("[I] 狀態行囊", id="btn_inspect", classes="cmd_btn")
                yield Button("[M] 修改他人", id="btn_modify", classes="cmd_btn")
                yield Button("[C] 切換目標", id="btn_cycle", classes="cmd_btn")
                yield Button("[Q] 離開遊戲", id="btn_quit", classes="cmd_btn")

    def on_mount(self) -> None:
        self.update_all_views()
        self.log_event("[green]✦ 世界初始化完成！歡迎踏入因果與本質的世界。[/green]")

    def get_current_location(self) -> Dict[str, Any]:
        return LOCATIONS[self.current_location_idx % len(LOCATIONS)]

    def get_present_npcs(self) -> List[Character]:
        loc = self.get_current_location()
        npc_ids = loc.get("npc_ids", [])
        npcs = []
        for nid in npc_ids:
            c = self.world.get_character(nid)
            if c and c.is_alive:
                npcs.append(c)
        return npcs

    def get_facing_character(self) -> Optional[Character]:
        npcs = self.get_present_npcs()
        if not npcs:
            return None
        idx = self.current_facing_target_idx % len(npcs)
        return npcs[idx]

    def update_all_views(self) -> None:
        # 1. 頂部列
        cal = self.world.calendar
        loc = self.get_current_location()
        top_text = f"📅 第 {cal.current_day} 天 【{cal.current_slot.value}】 (10 AP/時段)  │  📍 {loc['name']}  │  🌤 晨風拂面"
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
{chr(10).join(['• ' + t.name for t in all_t[:4]]) if all_t else '• 暫無'}
[dim](按 I 鍵檢視完整百科與屬性)[/dim]"""
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
        log = self.query_one("#event_log_panel", RichLog)
        log.write(text)

    # ==========================================================================
    # 按鈕與指令動作處理
    # ==========================================================================

    def action_open_travel(self) -> None:
        """[1] 前往地區：打開地區選擇彈窗，由玩家自由選擇前往，避免浪費 AP"""
        def on_travel_selected(target_idx: Optional[int]):
            if target_idx is None:
                return
            if target_idx == self.current_location_idx % len(LOCATIONS):
                self.dialogue_text = f"你已經身處【{LOCATIONS[target_idx]['name']}】。"
                self.update_all_views()
                return

            if self.hero.current_ap < 1:
                self.dialogue_text = "行動點數不足（前往該地區需消耗 1 AP）！"
                self.update_all_views()
                return

            self.hero.current_ap -= 1
            self.current_location_idx = target_idx
            self.current_facing_target_idx = 0
            loc = self.get_current_location()
            self.dialogue_text = f"你消耗 1 AP 前往了【{loc['name']}】。{loc['desc']}"
            self.log_event(f"[dim]主角消耗 1 AP 前往【{loc['name']}】。[/dim]")
            self.update_all_views()

        self.push_screen(LocationSelectModal(self.current_location_idx, self.world), on_travel_selected)

    def action_open_inspect(self) -> None:
        """[I] 狀態行囊：打開主角屬性、掌握詞條完整百科與背包詳情"""
        self.push_screen(InspectModal(self.hero))

    def action_open_synthesize(self) -> None:
        """[3] 本質編織：打開自選原料彈窗，由玩家自主挑選兩枚詞條進行融合"""
        traits = self.hero.all_traits
        if len(traits) < 2:
            self.dialogue_text = "掌握的詞條數量不足 2 枚，無法進行本質重組！"
            self.update_all_views()
            return

        def on_traits_selected(pair: Optional[Tuple[Trait, Trait]]):
            if not pair:
                return
            t1, t2 = pair
            succ, fuse_msg, new_t = TraitSynthesizer.execute_hero_fusion(self.hero, t1, t2)
            if succ and new_t:
                self.dialogue_text = f"【本質融合成功】融合「{t1.name}」與「{t2.name}」，誕生自創專屬詞條：【{str(new_t.tier)}】「{new_t.name}」！"
                self.log_event(f"[bold purple]✨ 本質編織成功！誕生自創詞條：【{str(new_t.tier)}】「{new_t.name}」[/bold purple]")
                self.hero.imprint_trait(self.hero, new_t)
            else:
                self.dialogue_text = fuse_msg
            self.update_all_views()

        self.push_screen(TraitSynthesizeModal(self.hero), on_traits_selected)

    def action_open_modify_target(self) -> None:
        """[M] 修改他人：對眼前 NPC 施展因果本質編織（刻印、洗鍊或剝奪）"""
        target = self.get_facing_character()
        if not target:
            self.dialogue_text = "前方空無一人，無法進行因果本質干涉。"
            self.update_all_views()
            return

        def on_modify_selected(res: Optional[Dict[str, Any]]):
            if not res:
                return
            act_type = res.get("action")

            if act_type == "imprint":
                # 選擇主角詞條刻印給目標
                if not self.hero.all_traits:
                    self.dialogue_text = "你自身尚未掌握任何本質詞條，無法灌注刻印！"
                    self.update_all_views()
                    return
                # 取主角最新掌握或自創詞條
                trait_to_imprint = list(self.hero.custom_traits.values())[-1] if self.hero.custom_traits else self.hero.all_traits[-1]
                res_imp = self.world.execute_interaction("imprint_target_trait", self.hero.char_id, target.char_id, trait=trait_to_imprint)
                self.dialogue_text = res_imp.message.splitlines()[0]
                self.log_event(f"[magenta]🔮 {res_imp.message.replace(chr(10), ' ')}[/magenta]")

            elif act_type == "mutate":
                if not target.all_traits:
                    self.dialogue_text = f"{target.name} 體內無任何詞條可供洗鍊！"
                    self.update_all_views()
                    return
                trait_to_mutate = target.all_traits[0]
                res_mut = self.world.execute_interaction("mutate_target_trait", self.hero.char_id, target.char_id, trait=trait_to_mutate)
                self.dialogue_text = res_mut.message.splitlines()[0]
                self.log_event(f"[green]✨ {res_mut.message.replace(chr(10), ' ')}[/green]")

            elif act_type == "extract":
                if not target.all_traits:
                    self.dialogue_text = f"{target.name} 體內無任何詞條可供剝奪！"
                    self.update_all_views()
                    return
                trait_to_extract = target.all_traits[0]
                res_ext = self.world.execute_interaction("extract_target_trait", self.hero.char_id, target.char_id, trait=trait_to_extract)
                self.dialogue_text = res_ext.message.splitlines()[0]
                self.log_event(f"[red]⚡ {res_ext.message.replace(chr(10), ' ')}[/red]")

            self.update_all_views()

        self.push_screen(ModifyTargetTraitModal(self.hero, target), on_modify_selected)

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
        if btn_id == "btn_loc":
            self.action_open_travel()
        elif btn_id == "btn_interact":
            self.action_interact()
        elif btn_id == "btn_synth":
            self.action_open_synthesize()
        elif btn_id == "btn_lens":
            self.action_toggle_lens()
        elif btn_id == "btn_council":
            self.action_council()
        elif btn_id == "btn_next_slot":
            self.action_advance_slot()
        elif btn_id == "btn_inspect":
            self.action_open_inspect()
        elif btn_id == "btn_modify":
            self.action_open_modify_target()
        elif btn_id == "btn_cycle":
            self.action_cycle_target()
        elif btn_id == "btn_quit":
            self.action_quit()


def main():
    app = RPGSimulatorApp()
    app.run()


if __name__ == "__main__":
    main()
