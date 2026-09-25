"""
Interpersonal Interactive Actions System (Character-to-Character Interaction Framework).
Provides an extensible interaction registry, supporting:
1. Social & Diplomatic Interactions (Converse, Gift, Duel/Threaten)
2. Contractual & Office Interactions (Appoint Office, Recruit)
3. Essence Weaving Interactions (Scan Essence, Imprint Trait - Protagonist privileges)
4. Intrigue & Rebellion (Instigate Coup, Solicit Conspiracy)
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable
from .character import Character
from .social import SocialNetwork, Relationship
from .organization import Organization, Office, Authority, OrgTier
from .traits import Trait, Tier


class InteractionCategory(Enum):
    SOCIAL = "社交情感"
    CONTRACT = "職權契約"
    ESSENCE = "本質干涉"
    INTRIGUE = "密謀權術"


@dataclass
class InteractionResult:
    success: bool
    message: str
    ap_cost: int = 0
    mp_cost: float = 0.0
    gold_change: float = 0.0
    delta_affection: float = 0.0
    delta_respect: float = 0.0
    delta_obligation: float = 0.0
    extra_data: Dict[str, Any] = field(default_factory=dict)


class BaseInteraction:
    """可擴充之互動動作抽象基底類別"""
    id: str = "base"
    name: str = "基礎動作"
    category: InteractionCategory = InteractionCategory.SOCIAL
    ap_cost: int = 1
    description: str = ""

    def can_execute(
        self,
        actor: Character,
        target: Character,
        world_state: Any,
        **kwargs
    ) -> Tuple[bool, str]:
        if actor.current_ap < self.ap_cost:
            return False, f"行動點數 (AP) 不足！需要 {self.ap_cost} AP，當前剩餘 {actor.current_ap} AP。"
        if actor.char_id == target.char_id:
            return False, "無法對自己執行此項互動！"
        return True, "可以執行。"

    def execute(
        self,
        actor: Character,
        target: Character,
        world_state: Any,
        **kwargs
    ) -> InteractionResult:
        raise NotImplementedError


# ==============================================================================
# 1. 社交情感互動 (Social Interactions)
# ==============================================================================

class ConverseInteraction(BaseInteraction):
    """
    【攀談懇談】：透過言語交鋒與思想交流增進彼此關係。
    受口才、魅力詞條 (如天狐媚骨、博雅哲學真知、市井智慧) 影響。
    """
    id = "converse"
    name = "攀談懇談"
    category = InteractionCategory.SOCIAL
    ap_cost = 2
    description = "與目標促膝長談，交流見聞與世界局勢，改善彼此好感與認同。"

    def execute(
        self,
        actor: Character,
        target: Character,
        world_state: Any,
        **kwargs
    ) -> InteractionResult:
        can, reason = self.can_execute(actor, target, world_state, **kwargs)
        if not can:
            return InteractionResult(success=False, message=reason)

        actor.current_ap -= self.ap_cost
        actor.interaction_count += 1

        d_aff = 8.0
        d_resp = 4.0
        bonuses = []

        # 檢驗主動者持有的社交加成詞條
        actor_trait_ids = [t.id for t in getattr(actor, "all_traits", actor.imprinted_traits + actor.innate_traits)]
        if any("fox_charm" in tid for tid in actor_trait_ids):
            d_aff += 12.0
            bonuses.append("天狐媚骨(+12 好感)")
        if any("philosopher" in tid for tid in actor_trait_ids):
            d_resp += 10.0
            bonuses.append("博雅真知(+10 敬畏)")
        if any("street_smart" in tid for tid in actor_trait_ids):
            d_aff += 4.0
            bonuses.append("市井智慧(+4 好感)")

        # 更新社交網絡
        rel = world_state.social_network.modify(target.char_id, actor.char_id, d_aff=d_aff, d_resp=d_resp)
        bonus_str = f" [特性加成: {', '.join(bonuses)}]" if bonuses else ""

        msg = (
            f"【交談順暢】{actor.name} 與 {target.name} 相談甚歡{bonus_str}。\n"
            f"  --> {target.name} 對 {actor.name}：好感 +{d_aff:.1f} (當前: {rel.affection:.1f})，"
            f"敬畏 +{d_resp:.1f} (當前: {rel.respect:.1f})，合作意願: {rel.willingness:.1f}。"
        )
        return InteractionResult(
            success=True,
            message=msg,
            ap_cost=self.ap_cost,
            delta_affection=d_aff,
            delta_respect=d_resp
        )


class GiftGoldInteraction(BaseInteraction):
    """
    【饋贈金幣】：以實質財富資助目標，顯著提升目標好感與欠情值 (Obligation)。
    """
    id = "gift_gold"
    name = "厚禮賞賜"
    category = InteractionCategory.SOCIAL
    ap_cost = 1
    description = "贈送黃金資助目標，大幅建立人情債與好感度。"

    def can_execute(
        self,
        actor: Character,
        target: Character,
        world_state: Any,
        amount: float = 50.0,
        **kwargs
    ) -> Tuple[bool, str]:
        can, reason = super().can_execute(actor, target, world_state, **kwargs)
        if not can:
            return False, reason
        if actor.gold < amount:
            return False, f"金幣不足！需要 {amount:.1f} 金，當前僅有 {actor.gold:.1f} 金。"
        if amount <= 0:
            return False, "贈與金幣數量必須大於 0。"
        return True, "可以執行。"

    def execute(
        self,
        actor: Character,
        target: Character,
        world_state: Any,
        amount: float = 50.0,
        **kwargs
    ) -> InteractionResult:
        can, reason = self.can_execute(actor, target, world_state, amount=amount, **kwargs)
        if not can:
            return InteractionResult(success=False, message=reason)

        actor.current_ap -= self.ap_cost
        actor.gold -= amount
        target.gold += amount
        actor.interaction_count += 1

        d_aff = min(35.0, round(amount * 0.3, 1))
        d_ob = min(40.0, round(amount * 0.4, 1))

        rel = world_state.social_network.modify(target.char_id, actor.char_id, d_aff=d_aff, d_ob=d_ob)
        msg = (
            f"【重金饋贈】{actor.name} 贈與 {target.name} {amount:.1f} 枚金幣！\n"
            f"  --> {target.name} 甚為感激：好感 +{d_aff:.1f}，人情欠款 +{d_ob:.1f} (當前合作意願: {rel.willingness:.1f})。"
        )
        return InteractionResult(
            success=True,
            message=msg,
            ap_cost=self.ap_cost,
            gold_change=-amount,
            delta_affection=d_aff,
            delta_obligation=d_ob
        )


class ThreatenDuelInteraction(BaseInteraction):
    """
    【武力威懾 / 戰鬥切磋】：展現壓倒性力量或戰鬥本領，贏取對方的敬畏 (Respect)。
    """
    id = "threaten_duel"
    name = "武力威懾"
    category = InteractionCategory.SOCIAL
    ap_cost = 3
    description = "以氣勢與戰鬥實力震懾目標，大幅提高敬畏值，但可能微幅折損好感。"

    def execute(
        self,
        actor: Character,
        target: Character,
        world_state: Any,
        **kwargs
    ) -> InteractionResult:
        can, reason = self.can_execute(actor, target, world_state, **kwargs)
        if not can:
            return InteractionResult(success=False, message=reason)

        actor.current_ap -= self.ap_cost
        actor.interaction_count += 1

        d_resp = 22.0
        d_aff = -5.0

        rel = world_state.social_network.modify(target.char_id, actor.char_id, d_aff=d_aff, d_resp=d_resp)
        msg = (
            f"【氣魄震懾】{actor.name} 拔劍亮芒，展現出凌厲無匹的武道威勢！\n"
            f"  --> {target.name} 瞳孔收縮，深感心悸：敬畏 +{d_resp:.1f} (當前: {rel.respect:.1f})，"
            f"好感 {d_aff:.1f} (當前意願: {rel.willingness:.1f})。"
        )
        return InteractionResult(
            success=True,
            message=msg,
            ap_cost=self.ap_cost,
            delta_affection=d_aff,
            delta_respect=d_resp
        )


# ==============================================================================
# 2. 契約與職權互動 (Contractual & Office Interactions)
# ==============================================================================

class AppointOfficeInteraction(BaseInteraction):
    """
    【冊封官職 / 授予職能】：將目標任命為組織內的指定官位 (Office)。
    受封者敬畏與義務值上升，並獲得相應的職責與月俸。
    """
    id = "appoint_office"
    name = "冊封任命"
    category = InteractionCategory.CONTRACT
    ap_cost = 2
    description = "將目標任命為己方勢力之核心內閣職位 (如大元帥、財政總管等)。"

    def can_execute(
        self,
        actor: Character,
        target: Character,
        world_state: Any,
        org_id: Optional[str] = None,
        office_id: Optional[str] = None,
        **kwargs
    ) -> Tuple[bool, str]:
        can, reason = super().can_execute(actor, target, world_state, **kwargs)
        if not can:
            return False, reason

        if not org_id or not office_id:
            return False, "必須指定目標組織 ID (org_id) 與職位 ID (office_id)！"

        org: Optional[Organization] = world_state.org_manager.get_org(org_id)
        if not org:
            return False, f"組織 {org_id} 不存在！"
        if org.leader_id != actor.char_id:
            return False, f"權限不足！只有組織領袖（{org.leader_id}）才有權冊封官職。"
        if office_id not in org.offices:
            return False, f"組織「{org.name}」中不存在此職位 ID「{office_id}」！"

        # 檢驗目標是否願意接受任命
        rel = world_state.social_network.get_relationship(target.char_id, actor.char_id)
        if rel.willingness < 20.0:
            return False, f"任命受拒：{target.name} 對您的意願值僅為 {rel.willingness:.1f} (需 >= 20.0)，拒絕出仕！"

        return True, "可以執行。"

    def execute(
        self,
        actor: Character,
        target: Character,
        world_state: Any,
        org_id: Optional[str] = None,
        office_id: Optional[str] = None,
        **kwargs
    ) -> InteractionResult:
        can, reason = self.can_execute(actor, target, world_state, org_id=org_id, office_id=office_id, **kwargs)
        if not can:
            return InteractionResult(success=False, message=reason)

        actor.current_ap -= self.ap_cost
        actor.interaction_count += 1
        org = world_state.org_manager.get_org(org_id)

        succ, appoint_log = org.appoint_office(office_id, target.char_id)
        d_resp = 15.0
        d_ob = 25.0
        world_state.social_network.modify(target.char_id, actor.char_id, d_resp=d_resp, d_ob=d_ob)

        office = org.offices[office_id]
        full_msg = f"{appoint_log}\n  --> {target.name} 拜謝受任：敬畏 +{d_resp:.1f}，欠情 +{d_ob:.1f}，每月享有俸祿 {office.monthly_stipend:.1f} 金。"
        return InteractionResult(
            success=True,
            message=full_msg,
            ap_cost=self.ap_cost,
            delta_respect=d_resp,
            delta_obligation=d_ob,
            extra_data={"org_id": org_id, "office_id": office_id}
        )


# ==============================================================================
# 3. 本質與魔法干預 (Essence Weaving - 主角專屬特權)
# ==============================================================================

class ScanEssenceInteraction(BaseInteraction):
    """
    【洞察本質】：看穿目標靈魂深處隱藏的詞條、精神負荷與腐化狀態。
    主角金手指核心探查能力。
    """
    id = "scan_essence"
    name = "洞察本質"
    category = InteractionCategory.ESSENCE
    ap_cost = 1
    description = "以心識窺探對象的所有先天、後天與自創詞條，以及其靈魂腐化度。"

    def can_execute(
        self,
        actor: Character,
        target: Character,
        world_state: Any,
        **kwargs
    ) -> Tuple[bool, str]:
        can, reason = super().can_execute(actor, target, world_state, **kwargs)
        if not can:
            return False, reason
        if not actor.is_awakened:
            return False, f"{actor.name} 尚未覺醒，無法窺視因果本質！"
        if actor.current_mp < 5.0 and actor.rank_key != "Transcendent":
            return False, "精神力不足（需 5.0 MP）！"
        return True, "可以執行。"

    def execute(
        self,
        actor: Character,
        target: Character,
        world_state: Any,
        **kwargs
    ) -> InteractionResult:
        can, reason = self.can_execute(actor, target, world_state, **kwargs)
        if not can:
            return InteractionResult(success=False, message=reason)

        actor.current_ap -= self.ap_cost
        if actor.rank_key != "Transcendent":
            actor.current_mp -= 5.0

        actor.interaction_count += 1

        innate_names = [t.name for t in target.innate_traits]
        acquired_names = [t.name for t in target.acquired_traits]
        imprinted_names = [t.name for t in target.imprinted_traits]
        custom_names = [t.name for t in target.custom_traits.values()]
        state, state_desc = target.get_mental_state()

        msg = (
            f"【因果天眼·本質洞見】{actor.name} 成功窺探 {target.name}（境界: {target.rank_def.name}）的靈魂底層：\n"
            f"  - 先天稟賦: {innate_names if innate_names else '無'}\n"
            f"  - 後天積累: {acquired_names if acquired_names else '無'}\n"
            f"  - 當前刻印: {imprinted_names if imprinted_names else '無'}\n"
            f"  - 專屬自創: {custom_names if custom_names else '無'}\n"
            f"  - 心神負荷: {target.calculate_sustained_load():.1f}/{target.max_mp:.1f} MP ({target.stress_ratio*100:.1f}%) [{state.value}]\n"
            f"  - 靈魂腐化: {target.corruption:.1f}/100.0 [{target.get_corruption_state()[0].value}]"
        )
        return InteractionResult(
            success=True,
            message=msg,
            ap_cost=self.ap_cost,
            mp_cost=5.0,
            extra_data={
                "innate": innate_names,
                "acquired": acquired_names,
                "imprinted": imprinted_names,
                "corruption": target.corruption
            }
        )


class ImprintTargetTraitInteraction(BaseInteraction):
    """
    【本質刻印】：將自己掌握的一枚詞條強行刻印至目標靈魂上。
    可用於扶植心腹、提升部下戰力，或暗中給敵人植入【野心家】觸發宮鬥反噬。
    """
    id = "imprint_target_trait"
    name = "本質刻印"
    category = InteractionCategory.ESSENCE
    ap_cost = 3
    description = "消耗 MP 將一枚詞條刻印在目標身上，改變其能力、性格乃至精神狀態。"

    def can_execute(
        self,
        actor: Character,
        target: Character,
        world_state: Any,
        trait: Optional[Trait] = None,
        **kwargs
    ) -> Tuple[bool, str]:
        can, reason = super().can_execute(actor, target, world_state, **kwargs)
        if not can:
            return False, reason
        if not actor.is_awakened:
            return False, f"{actor.name} 尚未覺醒，無法干預因果刻印！"
        if not trait:
            return False, "必須指定欲刻印之詞條 (trait)！"
        if actor.current_mp < trait.instant_cost and actor.rank_key != "Transcendent":
            return False, f"精神力不足！刻印【{trait.tier}】需要 {trait.instant_cost:.1f} MP，當前僅剩 {actor.current_mp:.1f} MP。"
        return True, "可以執行。"

    def execute(
        self,
        actor: Character,
        target: Character,
        world_state: Any,
        trait: Optional[Trait] = None,
        **kwargs
    ) -> InteractionResult:
        can, reason = self.can_execute(actor, target, world_state, trait=trait, **kwargs)
        if not can:
            return InteractionResult(success=False, message=reason)

        actor.current_ap -= self.ap_cost
        cost = trait.instant_cost
        if actor.rank_key != "Transcendent":
            actor.current_mp -= cost

        actor.interaction_count += 1

        succ, imprint_msg = actor.imprint_trait(target, trait)
        return InteractionResult(
            success=succ,
            message=imprint_msg,
            ap_cost=self.ap_cost,
            mp_cost=cost
        )


class MutateTargetTraitInteraction(BaseInteraction):
    """
    【洗鍊變異目標詞條】：以因果神識沖刷重塑目標的某一項詞條。
    若詞條帶有深重腐化，將予以淨化；若屬性偏弱，則有機率突破至更高階層或激發新加成。
    """
    id = "mutate_target_trait"
    name = "洗鍊變異"
    category = InteractionCategory.ESSENCE
    ap_cost = 2
    description = "消耗 MP 洗鍊目標靈魂中的指定詞條，重塑其數值或淨化腐化。"

    def can_execute(
        self,
        actor: Character,
        target: Character,
        world_state: Any,
        trait: Optional[Trait] = None,
        **kwargs
    ) -> Tuple[bool, str]:
        can, reason = super().can_execute(actor, target, world_state, **kwargs)
        if not can:
            return False, reason
        if not actor.is_awakened:
            return False, f"{actor.name} 尚未覺醒，無法干預因果本質！"
        if not trait:
            return False, "必須指定欲洗鍊重塑之詞條 (trait)！"
        if actor.current_mp < 25.0 and actor.rank_key != "Transcendent":
            return False, f"精神力不足！洗鍊需要 25.0 MP，當前僅剩 {actor.current_mp:.1f} MP。"
        return True, "可以執行。"

    def execute(
        self,
        actor: Character,
        target: Character,
        world_state: Any,
        trait: Optional[Trait] = None,
        **kwargs
    ) -> InteractionResult:
        can, reason = self.can_execute(actor, target, world_state, trait=trait, **kwargs)
        if not can:
            return InteractionResult(success=False, message=reason)

        actor.current_ap -= self.ap_cost
        if actor.rank_key != "Transcendent":
            actor.current_mp -= 25.0
        actor.interaction_count += 1

        from src.core.trait_synthesizer import TraitSynthesizer
        mutated = TraitSynthesizer.mutate(trait, purify_corruption=True)

        # 替換目標身上的詞條
        replaced = False
        for slot_list in [target.innate_traits, target.acquired_traits, target.imprinted_traits]:
            for i, t in enumerate(slot_list):
                if t.id == trait.id:
                    slot_list[i] = mutated
                    replaced = True
                    break
            if replaced:
                break
        if not replaced and trait.id in target.custom_traits:
            target.custom_traits[trait.id] = mutated

        d_aff = 10.0 if mutated.corruption_delta < trait.corruption_delta else 5.0
        d_resp = 10.0
        world_state.social_network.modify(target.char_id, actor.char_id, d_aff=d_aff, d_resp=d_resp)

        msg = (
            f"【因果洗鍊成功】{actor.name} 消耗 25.0 MP，對 {target.name} 的「{trait.name}」進行靈魂洗鍊重塑！\n"
            f"  --> 重塑產物：【{mutated.tier}】「{mutated.name}」\n"
            f"  --> 屬性變動：{mutated.modifiers}\n"
            f"  --> 腐化淨化：{trait.corruption_delta:+.1f} -> {mutated.corruption_delta:+.1f}\n"
            f"  --> {target.name} 感受到了靈魂的淨化洗禮，對你感激敬佩。"
        )
        return InteractionResult(
            success=True,
            message=msg,
            ap_cost=self.ap_cost,
            mp_cost=25.0,
            delta_affection=d_aff,
            delta_respect=d_resp,
            extra_data={"mutated_trait": mutated}
        )


class ExtractTargetTraitInteraction(BaseInteraction):
    """
    【剝奪抽取本質】：從目標靈魂中強行抽離一枚詞條，據為己有（收納至主角自創詞條庫）。
    目標失去該詞條，常駐心神負荷下降，但會感到靈魂被撕裂，與主動者關係急劇惡化。
    """
    id = "extract_target_trait"
    name = "抽取本質"
    category = InteractionCategory.ESSENCE
    ap_cost = 3
    description = "消耗 MP 強行剝離目標的一枚詞條並據為己有，會對其造成嚴重驚駭與反感。"

    def can_execute(
        self,
        actor: Character,
        target: Character,
        world_state: Any,
        trait: Optional[Trait] = None,
        **kwargs
    ) -> Tuple[bool, str]:
        can, reason = super().can_execute(actor, target, world_state, **kwargs)
        if not can:
            return False, reason
        if not actor.is_awakened:
            return False, f"{actor.name} 尚未覺醒，無法干預因果本質！"
        if not trait:
            return False, "必須指定欲剝奪抽取之詞條 (trait)！"
        if actor.current_mp < 35.0 and actor.rank_key != "Transcendent":
            return False, f"精神力不足！抽取需要 35.0 MP，當前僅剩 {actor.current_mp:.1f} MP。"
        return True, "可以執行。"

    def execute(
        self,
        actor: Character,
        target: Character,
        world_state: Any,
        trait: Optional[Trait] = None,
        **kwargs
    ) -> InteractionResult:
        can, reason = self.can_execute(actor, target, world_state, trait=trait, **kwargs)
        if not can:
            return InteractionResult(success=False, message=reason)

        actor.current_ap -= self.ap_cost
        if actor.rank_key != "Transcendent":
            actor.current_mp -= 35.0
        actor.interaction_count += 1

        # 從目標槽位移除該詞條
        removed = False
        for slot_list in [target.imprinted_traits, target.acquired_traits, target.innate_traits]:
            for i, t in enumerate(slot_list):
                if t.id == trait.id:
                    slot_list.pop(i)
                    removed = True
                    break
            if removed:
                break
        if not removed and trait.id in target.custom_traits:
            del target.custom_traits[trait.id]
            removed = True

        # 將該詞條收納至主角自創詞條庫中
        import copy
        extracted_trait = copy.deepcopy(trait)
        extracted_trait.is_synthetic = True
        actor.custom_traits[extracted_trait.id] = extracted_trait

        d_aff = -30.0
        d_resp = 15.0  # 恐懼敬畏
        world_state.social_network.modify(target.char_id, actor.char_id, d_aff=d_aff, d_resp=d_resp)

        msg = (
            f"【抽取剝離成功】{actor.name} 施展因果神術，自 {target.name} 靈魂深處強行抽離了【{trait.tier}】「{trait.name}」！\n"
            f"  --> 該詞條已被編織入主角的專屬本質庫存之中。\n"
            f"  --> {target.name} 靈魂元氣大傷，對你的驚恐與仇恨劇增 (好感 {d_aff:+.0f}，敬畏 {d_resp:+.0f})！"
        )
        return InteractionResult(
            success=True,
            message=msg,
            ap_cost=self.ap_cost,
            mp_cost=35.0,
            delta_affection=d_aff,
            delta_respect=d_resp,
            extra_data={"extracted_trait": extracted_trait}
        )


# ==============================================================================
# 4. 密謀與權術互動 (Intrigue & Conspiracy)
# ==============================================================================

class InstigateRebellionInteraction(BaseInteraction):
    """
    【策動叛亂 / 策反宮鬥】：針對組織中手握重權（如掌管軍事或金庫）但對其領主不滿的長官發動策反。
    若目標帶有【野心家】或靈魂腐化較高，成功率大增！
    """
    id = "instigate_rebellion"
    name = "策動自立叛亂"
    category = InteractionCategory.INTRIGUE
    ap_cost = 4
    description = "秘密遊說握有實權的將領或大臣，煽動其背叛宗主並建立自立政權。"

    def can_execute(
        self,
        actor: Character,
        target: Character,
        world_state: Any,
        target_org_id: Optional[str] = None,
        **kwargs
    ) -> Tuple[bool, str]:
        can, reason = super().can_execute(actor, target, world_state, **kwargs)
        if not can:
            return False, reason
        if not target_org_id:
            return False, "必須指定目標組織 ID (target_org_id)！"

        org = world_state.org_manager.get_org(target_org_id)
        if not org:
            return False, f"目標組織 {target_org_id} 不存在！"
        if org.leader_id == target.char_id:
            return False, "目標已是該組織的最高領袖，無法向自己發動叛亂！"

        return True, "可以執行。"

    def execute(
        self,
        actor: Character,
        target: Character,
        world_state: Any,
        target_org_id: Optional[str] = None,
        **kwargs
    ) -> InteractionResult:
        can, reason = self.can_execute(actor, target, world_state, target_org_id=target_org_id, **kwargs)
        if not can:
            return InteractionResult(success=False, message=reason)

        actor.current_ap -= self.ap_cost
        actor.interaction_count += 1
        org = world_state.org_manager.get_org(target_org_id)
        leader_id = org.leader_id

        # 檢驗目標對其宗主的意願 (Willingness) 與持有的詞條
        rel_to_leader = world_state.social_network.get_relationship(target.char_id, leader_id)
        target_trait_ids = [t.id for t in getattr(target, "all_traits", target.imprinted_traits + target.acquired_traits)]

        # 計算叛亂傾向分數 (Coup Affinity Score)
        coup_score = 40.0 - rel_to_leader.willingness  # 對宗主好感越低，分數越高
        if any("ambitious" in tid for tid in target_trait_ids):
            coup_score += 35.0  # 野心家大幅渴望上位
        if any("faithful" in tid for tid in target_trait_ids):
            coup_score -= 40.0  # 忠厚本分排斥背叛
        if target.corruption >= 50.0:
            coup_score += 20.0  # 混沌腐化加深叛意

        # 檢驗其掌管的權能 (若掌軍或掌財，政變威力極大)
        held_authorities = []
        for off in org.offices.values():
            if off.incumbent_id == target.char_id:
                held_authorities.extend([a.value for a in off.authorities])

        if coup_score >= 45.0:
            # 策反成功！提高對主角好感，準備倒戈
            world_state.social_network.modify(target.char_id, actor.char_id, d_aff=20.0, d_ob=25.0)
            msg = (
                f"【策反成功！】{actor.name} 戳中 {target.name} 的野心痛點！\n"
                f"  - 目標握有職能: {held_authorities if held_authorities else '普通幕僚'}\n"
                f"  - 叛亂傾向得分: {coup_score:.1f} (門檻 >= 45.0)\n"
                f"  - {target.name} 誓言與 {actor.name} 密謀聯盟，靜待時機奪取「{org.name}」大權！"
            )
            return InteractionResult(success=True, message=msg, ap_cost=self.ap_cost, extra_data={"coup_ready": True})
        else:
            # 策反失敗，引發警覺
            world_state.social_network.modify(target.char_id, actor.char_id, d_aff=-15.0, d_resp=-10.0)
            msg = (
                f"【策反失敗】{target.name} 嚴詞斥責 {actor.name} 的大逆不道之舉！\n"
                f"  - 叛亂傾向得分僅為 {coup_score:.1f} (門檻 45.0)，目標對現任領主依然效忠。\n"
                f"  - 目標對您的好感顯著惡化 (-15.0)！"
            )
            return InteractionResult(success=False, message=msg, ap_cost=self.ap_cost, delta_affection=-15.0)


# ==============================================================================
# 5. 互動動作總冊 (Interaction Registry)
# ==============================================================================

class InteractionRegistry:
    """可擴充之互動動作登記冊"""
    _registry: Dict[str, BaseInteraction] = {}

    @classmethod
    def register(cls, interaction: BaseInteraction) -> None:
        cls._registry[interaction.id] = interaction

    @classmethod
    def get(cls, interaction_id: str) -> Optional[BaseInteraction]:
        return cls._registry.get(interaction_id)

    @classmethod
    def list_all(cls) -> List[BaseInteraction]:
        return list(cls._registry.values())

    @classmethod
    def get_available_for_pair(
        cls,
        actor: Character,
        target: Character,
        world_state: Any,
        **kwargs
    ) -> List[Tuple[BaseInteraction, bool, str]]:
        """回傳當前針對該目標角色，所有動作的可用性評估"""
        results = []
        for act in cls._registry.values():
            can, reason = act.can_execute(actor, target, world_state, **kwargs)
            results.append((act, can, reason))
        return results


# 預設註冊所有核心互動
InteractionRegistry.register(ConverseInteraction())
InteractionRegistry.register(GiftGoldInteraction())
InteractionRegistry.register(ThreatenDuelInteraction())
InteractionRegistry.register(AppointOfficeInteraction())
InteractionRegistry.register(ScanEssenceInteraction())
InteractionRegistry.register(ImprintTargetTraitInteraction())
InteractionRegistry.register(MutateTargetTraitInteraction())
InteractionRegistry.register(ExtractTargetTraitInteraction())
InteractionRegistry.register(InstigateRebellionInteraction())
