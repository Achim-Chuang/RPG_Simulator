"""
RimWorld-style External Def Loader & Database.
Loads TraitDefs, ScenarioDefs, and other content dynamically from external JSON/YAML files.
Supports official PyYAML if installed, with a zero-dependency Pure-Python fallback parser.
"""

import os
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from ..core.traits import Trait, Tier, Category
from ..core.character import Character
from ..core.organization import Organization, OrgTier
from ..engine.world import WorldState


# ==============================================================================
# 1. 輕量級純 Python YAML 解析器 (Zero-Dependency Fallback Parser)
# ==============================================================================

class MiniYamlParser:
    @staticmethod
    def _coerce_value(val: str) -> Any:
        val = val.strip()
        if not val:
            return ""
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            return val[1:-1]
        if val.lower() in ("true", "yes", "on"):
            return True
        if val.lower() in ("false", "no", "off"):
            return False
        if val.lower() in ("null", "none", "~"):
            return None
        # 整數或浮點數
        if re.match(r"^-?\d+$", val):
            return int(val)
        if re.match(r"^-?\d+\.\d+$", val):
            return float(val)
        return val

    @classmethod
    def parse(cls, text: str) -> Any:
        """
        嘗試調用 PyYAML；若未安裝，使用輕量級行縮排解析。
        """
        try:
            import yaml
            return yaml.safe_load(text)
        except ImportError:
            pass

        # Pure Python Fallback 解析器
        lines = []
        for raw_line in text.splitlines():
            # 移除行尾註解
            if "#" in raw_line:
                # 簡單排除字串外的 #
                in_quote = False
                quote_char = ""
                comment_idx = -1
                for idx, ch in enumerate(raw_line):
                    if ch in ('"', "'"):
                        if not in_quote:
                            in_quote = True
                            quote_char = ch
                        elif quote_char == ch:
                            in_quote = False
                    elif ch == "#" and not in_quote:
                        comment_idx = idx
                        break
                if comment_idx != -1:
                    raw_line = raw_line[:comment_idx]

            stripped = raw_line.rstrip()
            if stripped.strip():
                indent = len(stripped) - len(stripped.lstrip())
                lines.append((indent, stripped.strip()))

        if not lines:
            return {}

        def parse_block(idx: int, current_indent: int) -> Tuple[Any, int]:
            # 判斷是 list 還是 dict
            if idx >= len(lines):
                return {}, idx

            first_indent, first_content = lines[idx]
            is_list = first_content.startswith("- ")

            if is_list:
                result_list = []
                while idx < len(lines):
                    indent, content = lines[idx]
                    if indent < current_indent:
                        break
                    if indent == current_indent and content.startswith("- "):
                        item_content = content[2:].strip()
                        if ":" in item_content and not (item_content.startswith("{") or item_content.startswith("[")):
                            # - key: value 型態的字典項
                            k, v = item_content.split(":", 1)
                            v = v.strip()
                            sub_dict = {k.strip(): cls._coerce_value(v) if v else None}
                            idx += 1
                            # 檢查是否有接續縮排的同項子鍵值
                            while idx < len(lines) and lines[idx][0] > indent and not lines[idx][1].startswith("- "):
                                sub_indent, sub_content = lines[idx]
                                if ":" in sub_content:
                                    sk, sv = sub_content.split(":", 1)
                                    sv = sv.strip()
                                    if sv:
                                        sub_dict[sk.strip()] = cls._coerce_value(sv)
                                        idx += 1
                                    else:
                                        nested, idx = parse_block(idx + 1, sub_indent + 2)
                                        sub_dict[sk.strip()] = nested
                                else:
                                    idx += 1
                            result_list.append(sub_dict)
                        elif item_content:
                            result_list.append(cls._coerce_value(item_content))
                            idx += 1
                        else:
                            # - 後面為縮排子結構
                            sub_block, idx = parse_block(idx + 1, indent + 2)
                            result_list.append(sub_block)
                    else:
                        break
                return result_list, idx
            else:
                result_dict = {}
                while idx < len(lines):
                    indent, content = lines[idx]
                    if indent < current_indent:
                        break
                    if ":" in content:
                        k, v = content.split(":", 1)
                        k = k.strip()
                        v = v.strip()
                        if v:
                            result_dict[k] = cls._coerce_value(v)
                            idx += 1
                        else:
                            # 往下讀取子區塊
                            if idx + 1 < len(lines) and lines[idx + 1][0] > indent:
                                next_indent = lines[idx + 1][0]
                                sub_val, idx = parse_block(idx + 1, next_indent)
                                result_dict[k] = sub_val
                            else:
                                result_dict[k] = None
                                idx += 1
                    else:
                        idx += 1
                return result_dict, idx

        res, _ = parse_block(0, lines[0][0])
        return res


# ==============================================================================
# 2. Def 資料庫 (DefDatabase)
# ==============================================================================

class DefDatabase:
    def __init__(self):
        self.trait_defs: Dict[str, Trait] = {}
        self.scenario_defs: Dict[str, Dict[str, Any]] = {}
        self.profession_defs: Dict[str, Dict[str, Any]] = {}

    def register_trait(self, trait: Trait):
        self.trait_defs[trait.id] = trait

    def register_scenario(self, scenario_data: Dict[str, Any]):
        s_id = scenario_data.get("id", scenario_data.get("scenario_id"))
        if s_id:
            self.scenario_defs[s_id] = scenario_data

    def register_profession(self, prof_data: Dict[str, Any]):
        p_id = prof_data.get("id")
        if p_id:
            self.profession_defs[p_id] = prof_data

    def get_trait(self, trait_id: str) -> Optional[Trait]:
        return self.trait_defs.get(trait_id)

    def get_scenario(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        return self.scenario_defs.get(scenario_id)

    def get_profession(self, prof_id: str) -> Optional[Dict[str, Any]]:
        return self.profession_defs.get(prof_id)


# ==============================================================================
# 3. 外部 Def 載入器 (DefLoader)
# ==============================================================================

class DefLoader:
    def __init__(self, database: Optional[DefDatabase] = None):
        self.db = database if database is not None else DefDatabase()

    def parse_file(self, filepath: str) -> Any:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        if filepath.endswith(".json"):
            return json.loads(content)
        elif filepath.endswith(".yaml") or filepath.endswith(".yml"):
            return MiniYamlParser.parse(content)
        return None

    def load_all_defs(self, root_dir: str) -> List[str]:
        """
        遞迴掃描目錄下所有 .json, .yaml, .yml 檔案並註冊
        """
        logs = []
        if not os.path.exists(root_dir):
            logs.append(f"[警告] 定義目錄 {root_dir} 不存在！")
            return logs

        for dirpath, _, filenames in os.walk(root_dir):
            for fname in sorted(filenames):
                if fname.endswith((".json", ".yaml", ".yml")):
                    fpath = os.path.join(dirpath, fname)
                    try:
                        raw_data = self.parse_file(fpath)
                        if not raw_data:
                            continue

                        # 支援單一物件或陣列清單
                        items = raw_data if isinstance(raw_data, list) else [raw_data]

                        for item in items:
                            if not isinstance(item, dict):
                                continue
                            def_type = item.get("def_type", "").lower()
                            
                            # 1. 優先檢驗職業定義
                            if def_type == "profession" or "professions" in dirpath.lower() or "base_daily_wage" in item or "routines" in item:
                                self.db.register_profession(item)
                                p_id = item.get("id", "unknown")
                                logs.append(f"[載入職業] 《{item.get('name', p_id)}》 (ID: {p_id}) 来自 {fname}")

                            # 2. 劇本定義
                            elif def_type == "scenario" or "scenarios" in dirpath.lower() or "starting_player" in item:
                                self.db.register_scenario(item)
                                s_id = item.get("id", item.get("scenario_id", "unknown"))
                                logs.append(f"[載入劇本] 《{item.get('name', s_id)}》 (ID: {s_id}) 来自 {fname}")

                            # 3. 詞條定義
                            elif def_type == "trait" or "traits" in dirpath.lower() or "base_load" in item or "tier" in item:
                                category_str = item.get("category", "ACQUIRED").upper()
                                category = Category[category_str] if category_str in Category.__members__ else Category.ACQUIRED
                                raw_tier = item.get("tier", 1)
                                if isinstance(raw_tier, str):
                                    tier_map = {"regular": 1, "uncommon": 2, "rare": 3, "mystic": 4, "epic": 5, "transcendent": 6}
                                    tier_val = tier_map.get(raw_tier.lower(), 1)
                                else:
                                    tier_val = int(raw_tier)

                                trait = Trait(
                                    id=item["id"],
                                    name=item["name"],
                                    category=category,
                                    tier=Tier(tier_val),
                                    description=item.get("description", ""),
                                    modifiers=item.get("modifiers", {}),
                                    corruption_delta=float(item.get("corruption_delta", 0.0)),
                                    tags=list(item.get("tags", []))
                                )
                                self.db.register_trait(trait)
                                logs.append(f"[載入詞條] 【{trait.tier}】{trait.name} (ID: {trait.id}) 来自 {fname}")

                    except Exception as e:
                        logs.append(f"[載入失敗] 檔案 {fname} 解析錯誤: {str(e)}")

        return logs

    def create_world_from_scenario(self, scenario_id: str) -> Optional[WorldState]:
        """
        根據載入的 ScenarioDef 動態初始化全新的 WorldState
        """
        sc_data = self.db.get_scenario(scenario_id)
        if not sc_data:
            print(f"錯誤：劇本 ID {scenario_id} 未找到！")
            return None

        world = WorldState()

        # 1. 注入已載入的所有詞條庫與職業庫
        for trait in self.db.trait_defs.values():
            world.register_trait(trait)
        for prof in self.db.profession_defs.values():
            world.register_profession(prof)

        # 2. 建立日曆
        cal_data = sc_data.get("calendar", {})
        world.calendar.current_day = cal_data.get("starting_day", 1)

        # 3. 建立玩家主角 (Player Character)
        p_data = sc_data["starting_player"]
        hero = Character(
            char_id=p_data["id"],
            name=p_data["name"],
            rank_key=p_data.get("mage_rank", "Chorji"),
            is_awakened=p_data.get("is_awakened", True),
            gold=float(p_data.get("starting_gold", 50.0))
        )
        # 掛載初始詞條
        for tid in p_data.get("innate_traits", []):
            if tid in world.trait_registry:
                hero.innate_traits.append(world.trait_registry[tid])
        for tid in p_data.get("acquired_traits", []):
            if tid in world.trait_registry:
                hero.acquired_traits.append(world.trait_registry[tid])
        for tid in p_data.get("imprinted_traits", []):
            if tid in world.trait_registry:
                hero.imprinted_traits.append(world.trait_registry[tid])

        world.add_character(hero)

        # 4. 建立初始 NPC 群
        for n_data in sc_data.get("starting_npcs", []):
            npc = Character(
                char_id=n_data["id"],
                name=n_data["name"],
                rank_key=n_data.get("mage_rank", "Chorji"),
                is_awakened=n_data.get("is_awakened", False),
                gold=float(n_data.get("gold", 20.0))
            )
            for tid in n_data.get("innate_traits", []):
                if tid in world.trait_registry:
                    npc.innate_traits.append(world.trait_registry[tid])
            for tid in n_data.get("acquired_traits", []):
                if tid in world.trait_registry:
                    npc.acquired_traits.append(world.trait_registry[tid])
            world.add_character(npc)

        # 5. 建立初始勢力與組織
        for o_data in sc_data.get("starting_organizations", []):
            org = Organization(
                org_id=o_data["id"],
                name=o_data["name"],
                tier=OrgTier(int(o_data["tier"])),
                leader_id=o_data["leader_id"],
                fief_name=o_data.get("fief_name"),
                fief_monthly_income=float(o_data.get("fief_monthly_income", 0.0)),
                treasury=float(o_data.get("treasury", 0.0))
            )
            world.org_manager.all_orgs[org.org_id] = org

        # 6. 初始雙向關係
        for r_data in sc_data.get("starting_relationships", []):
            world.social_network.modify(
                from_id=r_data["from_id"],
                to_id=r_data["to_id"],
                d_aff=float(r_data.get("affection", 0.0)),
                d_resp=float(r_data.get("respect", 0.0)),
                d_ob=float(r_data.get("obligation", 0.0))
            )

        world.event_logs.append(f"【世界創生】以劇本《{sc_data.get('name')}》為藍本初始化完成！")
        return world
