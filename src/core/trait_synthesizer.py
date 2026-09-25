"""
Procedural Trait Synthesizer & Mutation Engine.
Allows the Protagonist (Essence Weaver) to dynamically fuse, mutate, and refine traits
on-the-fly without hardcoded combinatorial explosions.
Generated traits are strictly bound to the character's local registry/savegame.
"""

import uuid
import random
from typing import List, Dict, Tuple, Optional, Set
from .traits import Trait, Tier, Category, TIER_BASE_LOAD, TIER_BASE_INSTANT_COST
from .character import Character


# 語意前綴與核心語素映射庫 (基於 Tags 與風格)
TAG_FLAVOR_PREFIXES: Dict[str, List[str]] = {
    "fire": ["熾焰", "焚天", "業火", "曜陽"],
    "ice": ["玄冰", "極寒", "霜華", "凜冬"],
    "lightning": ["驚雷", "天劫", "磁暴", "紫電"],
    "void": ["虛空", "幽影", "湮滅", "微觀奇點"],
    "psionic": ["念動", "心識", "星靈", "靈能"],
    "warp": ["亞空間", "混沌", "狂亂", "古神"],
    "tech": ["量子", "超頻", "鈦合金", "奈米核心"],
    "cyber": ["神經接駁", "生化義體", "基質重組"],
    "melee": ["百戰", "修羅", "斬魄", "破軍"],
    "defense": ["不墜", "金剛", "天塹", "壁壘"],
    "divine": ["聖輝", "天啟", "純潔", "裁決"],
    "dark": ["嗜血", "蝕魂", "九幽", "寂滅"],
    "beast": ["蠻荒", "天狐", "兇獸", "狂暴"],
    "social": ["權謀", "捭闔", "洞察", "梟雄"],
    "qi": ["太極", "真元", "混元", "造化"],
    "star": ["星神", "恆星", "天樞", "原力"]
}

DEFAULT_PREFIXES = ["真源", "共鳴", "昇華", "造化", "極意", "玄妙", "混元"]


class TraitSynthesizer:
    """
    動態即時詞條反應爐 (Procedural Trait Generator)
    提供：
    1. 雙詞條/多詞條融合 (Fusion)
    2. 詞條變異與數值洗鍊 (Mutation / Refine)
    3. 詞條淨化/消除詛咒 (Purify)
    """

    @classmethod
    def fuse(
        cls,
        t1: Trait,
        t2: Trait,
        hero: Optional[Character] = None,
        seed: Optional[int] = None
    ) -> Trait:
        """
        融合兩枚詞條，動態推演新詞條的階級、語意名稱、修飾符加權與靈魂腐化變動
        """
        rng = random.Random(seed) if seed is not None else random.Random()

        # 1. 決定新階級 (Tier)
        base_tier_val = max(int(t1.tier), int(t2.tier))
        
        # 同階融合或主角高位階加持時，有 35% 機率產生「階級昇華 (Tier Breakthrough)」
        tier_breakthrough = False
        if t1.tier == t2.tier and base_tier_val < int(Tier.TRANSCENDENT):
            if rng.random() < 0.35:
                base_tier_val += 1
                tier_breakthrough = True
        elif hero and hero.rank_def.tier_cap > Tier(base_tier_val):
            # 若主角階級上限高於當前，且擲骰成功
            if rng.random() < 0.20:
                base_tier_val += 1
                tier_breakthrough = True

        new_tier = Tier(min(base_tier_val, int(Tier.TRANSCENDENT)))

        # 2. 決定分類 (Category)
        # 器物優先保留器物，否則先天優先，最後為後天
        if t1.category == Category.ARTIFACT or t2.category == Category.ARTIFACT:
            new_category = Category.ARTIFACT
        elif t1.category == Category.INNATE or t2.category == Category.INNATE:
            new_category = Category.INNATE
        else:
            new_category = Category.ACQUIRED

        # 3. 合併 Tags
        all_tags: Set[str] = set(t1.tags).union(set(t2.tags))
        
        # 4. 生成動態語意名稱
        new_name = cls._generate_fused_name(t1, t2, all_tags, tier_breakthrough, rng)

        # 5. 修飾符加權運算 (Modifiers Blending with Synergies)
        new_modifiers: Dict[str, float] = {}
        all_keys = set(t1.modifiers.keys()).union(set(t2.modifiers.keys()))

        # 昇華階級加乘係數
        tier_scale = 1.0 + 0.15 * (int(new_tier) - min(int(t1.tier), int(t2.tier)))

        for k in all_keys:
            v1 = t1.modifiers.get(k, 0.0)
            v2 = t2.modifiers.get(k, 0.0)
            if k in t1.modifiers and k in t2.modifiers:
                # 雙重共鳴：若兩者皆具備該屬性，產生 1.25 倍共鳴加成
                combined = (v1 + v2) * 1.25 * tier_scale
            else:
                # 單一繼承
                combined = (v1 if k in t1.modifiers else v2) * tier_scale
            new_modifiers[k] = round(combined, 2)

        # 檢查特殊標籤共鳴 (額外賜予隱藏加成)
        if "fire" in all_tags and "melee" in all_tags and "flame_strike" not in new_modifiers:
            new_modifiers["flame_strike"] = round(15.0 * int(new_tier), 1)
        if "void" in all_tags and "psionic" in all_tags and "warp_penetration" not in new_modifiers:
            new_modifiers["warp_penetration"] = round(0.12 * int(new_tier), 2)
        if "tech" in all_tags and "cyber" in all_tags and "overclock_ratio" not in new_modifiers:
            new_modifiers["overclock_ratio"] = round(0.10 * int(new_tier), 2)

        # 6. 靈魂腐化變動值 (平衡或加成)
        # 光明 (-delta) 與 混沌 (+delta) 相互抵銷與重組
        new_corruption = round(t1.corruption_delta + t2.corruption_delta, 2)

        # 7. 描述文字動態生成
        breakthrough_str = "【本質昇華突破！】" if tier_breakthrough else ""
        desc = (
            f"由【{t1.name}】與【{t2.name}】經編織者心識拆解重組而成的專屬本質。"
            f"{breakthrough_str}融合了 {list(all_tags) if all_tags else ['造化']} 特質。"
        )

        # 8. 建立新詞條實例
        new_id = f"syn_{uuid.uuid4().hex[:8]}"
        synthetic_trait = Trait(
            id=new_id,
            name=new_name,
            category=new_category,
            tier=new_tier,
            description=desc,
            modifiers=new_modifiers,
            corruption_delta=new_corruption,
            tags=sorted(list(all_tags)),
            parents=[t1.id, t2.id],
            is_synthetic=True
        )

        return synthetic_trait

    @classmethod
    def mutate(
        cls,
        trait: Trait,
        focus_modifier: Optional[str] = None,
        purify_corruption: bool = False,
        seed: Optional[int] = None
    ) -> Trait:
        """
        對現有詞條進行洗鍊、強化或靈魂淨化
        """
        rng = random.Random(seed) if seed is not None else random.Random()
        new_modifiers = dict(trait.modifiers)

        if focus_modifier and focus_modifier in new_modifiers:
            # 指定屬性強化 20% ~ 40%
            boost = rng.uniform(1.20, 1.40)
            new_modifiers[focus_modifier] = round(new_modifiers[focus_modifier] * boost, 2)
            prefix = "凝練·"
        elif new_modifiers:
            # 隨機挑選一項屬性洗鍊提升
            target_k = rng.choice(list(new_modifiers.keys()))
            boost = rng.uniform(1.15, 1.35)
            new_modifiers[target_k] = round(new_modifiers[target_k] * boost, 2)
            prefix = "極意·"
        else:
            # 若無修飾符，新增一項基礎精神力加成
            new_modifiers["bonus_mp"] = round(15.0 * int(trait.tier), 1)
            prefix = "覺醒·"

        new_corruption = trait.corruption_delta
        if purify_corruption:
            # 淨化負面混沌值
            new_corruption = min(0.0, new_corruption - 5.0)
            prefix = "淨化·"

        new_name = f"{prefix}{trait.name}"
        new_id = f"syn_{uuid.uuid4().hex[:8]}"

        mutated_trait = Trait(
            id=new_id,
            name=new_name,
            category=trait.category,
            tier=trait.tier,
            description=f"自【{trait.name}】洗鍊重組而來，本質更加純粹凝練。",
            modifiers=new_modifiers,
            corruption_delta=new_corruption,
            tags=list(trait.tags),
            parents=[trait.id],
            is_synthetic=True
        )
        return mutated_trait

    @classmethod
    def _generate_fused_name(
        cls,
        t1: Trait,
        t2: Trait,
        tags: Set[str],
        tier_breakthrough: bool,
        rng: random.Random
    ) -> str:
        """根據雙方標籤與詞性語素合成名稱"""
        matched_prefixes = []
        for tag in tags:
            if tag in TAG_FLAVOR_PREFIXES:
                matched_prefixes.extend(TAG_FLAVOR_PREFIXES[tag])

        chosen_prefix = rng.choice(matched_prefixes) if matched_prefixes else rng.choice(DEFAULT_PREFIXES)

        # 提取核心語素 (去除常見詞綴)
        def clean_core(name: str) -> str:
            for remove_word in ["之軀", "血統", "經驗", "天賦", "直覺", "常態", "重裝甲"]:
                if name.endswith(remove_word) and len(name) > len(remove_word):
                    return name[:-len(remove_word)]
            return name

        c1 = clean_core(t1.name)
        c2 = clean_core(t2.name)

        if tier_breakthrough:
            style = rng.choice([1, 2, 3])
            if style == 1:
                return f"{chosen_prefix}·{c1}{c2[-2:]}造化相"
            elif style == 2:
                return f"天樞·{c1}與{c2}之極"
            else:
                return f"{chosen_prefix}萬象·{c2}"
        else:
            style = rng.choice([1, 2])
            if style == 1:
                return f"{chosen_prefix}·{c1}{c2[-2:]}"
            else:
                return f"{c1}·{chosen_prefix}{c2[-2:]}"

    @classmethod
    def execute_hero_fusion(
        cls,
        hero: Character,
        t1: Trait,
        t2: Trait,
        seed: Optional[int] = None
    ) -> Tuple[bool, str, Optional[Trait]]:
        """
        主角執行本質融合核心動作：
        1. 檢查是否覺醒
        2. 消耗精神力
        3. 產出自創詞條並登記於主角專屬 custom_traits 中
        """
        if not hero.is_awakened:
            return False, f"{hero.name} 尚未覺醒，無法窺視因果本質並重組詞條！", None

        # 計算融合所需瞬時 MP 消耗
        cost = (t1.instant_cost + t2.instant_cost) * 0.4
        if hero.current_mp < cost and hero.rank_key != "Transcendent":
            return False, f"精神力不足！融合需要 {cost:.1f} MP，當前僅剩 {hero.current_mp:.1f} MP。", None

        if hero.rank_key != "Transcendent":
            hero.current_mp -= cost

        hero.interaction_count += 1

        # 執行生成
        synthetic_trait = cls.fuse(t1, t2, hero=hero, seed=seed)

        # 註冊於主角專屬庫 (不污染外部 Defs)
        hero.register_custom_trait(synthetic_trait)

        msg = (
            f"【本質融合成功】{hero.name} 消耗 {cost:.1f} MP，將「{t1.name}」與「{t2.name}」解構重組！\n"
            f"  --> 誕生全新自創詞條：【{synthetic_trait.tier}】「{synthetic_trait.name}」\n"
            f"  --> 屬性：{synthetic_trait.modifiers}\n"
            f"  --> 標籤：{synthetic_trait.tags}\n"
            f"  --> 靈魂腐化變動: {synthetic_trait.corruption_delta:+0.1f}\n"
            f"  --> 已持久化存入 {hero.name} 的專屬詞條庫。"
        )
        return True, msg, synthetic_trait
