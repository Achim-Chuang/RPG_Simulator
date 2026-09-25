"""
Five-Tier Organization System, Hierarchical Subordination, and Territorial Economic Cycles.
"""

from enum import IntEnum, Enum
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from .social import SocialNetwork


class Authority(str, Enum):
    """底層六大核心不可變權能原子 (Functional Primitives)"""
    MILITARY = "military"          # 軍事統帥 (出征、布防、戰力加乘、警備)
    TREASURY = "treasury"          # 財政金庫 (徵稅、商隊撥款、貿易獲利)
    DIPLOMACY = "diplomacy"        # 外交使節 (宣戰、結盟、媾和、朝貢條約)
    INTRIGUE = "intrigue"          # 諜報密網 (防範暗殺、反叛策動、情報刺探)
    INTERNAL_LAW = "internal_law"  # 民政法度 (治安維穩、作坊督導、災荒救濟)
    DOCTRINE = "doctrine"          # 信仰道統 (意識形態、忠誠宣教、腐化淨化)


@dataclass
class Office:
    """
    組織職能槽位 (Office / Position)
    表現層名稱隨劇本/文化動態替換，底層綁定一至多個權能原子
    """
    office_id: str
    title: str                               # 隨文化/劇本顯示之職稱 (例如: "王國大元帥", "星區戰帥", "戶部尚書")
    authorities: List[Authority] = field(default_factory=list)
    incumbent_id: Optional[str] = None       # 當前任職者 Character ID (若為 None 則為懸缺)
    monthly_stipend: float = 0.0             # 每月由組織金庫發放之俸祿

    def to_dict(self) -> Dict[str, Any]:
        return {
            "office_id": self.office_id,
            "title": self.title,
            "authorities": [a.value for a in self.authorities],
            "incumbent_id": self.incumbent_id,
            "monthly_stipend": self.monthly_stipend
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Office':
        auth_list = [Authority(a) for a in data.get("authorities", [])]
        return cls(
            office_id=data["office_id"],
            title=data["title"],
            authorities=auth_list,
            incumbent_id=data.get("incumbent_id"),
            monthly_stipend=float(data.get("monthly_stipend", 0.0))
        )


class OrgTier(IntEnum):
    PERSONAL = 1     # 個人組織（小隊）
    LARGE = 2        # 大型組織（公會、傭兵團、商會）
    CHARTERED = 3    # 授銜組織（騎士團、親衛軍團，上級發餉）
    LOCAL = 4        # 地方勢力（城主、分封領主，有地盤，向上進貢）
    INDEPENDENT = 5  # 獨立勢力（王國、獨立大名，有地盤，無上級）

    def __str__(self):
        names = {
            1: "個人組織 (Personal)",
            2: "大型組織 (Large)",
            3: "授銜組織 (Chartered)",
            4: "地方勢力 (Local)",
            5: "獨立勢力 (Independent)"
        }
        return names[self.value]


class Organization:
    def __init__(
        self,
        org_id: str,
        name: str,
        tier: OrgTier,
        leader_id: str,
        members: Optional[List[str]] = None,
        fief_name: Optional[str] = None,
        fief_monthly_income: float = 0.0,
        treasury: float = 0.0,
        tribute_rate_to_parent: float = 0.0,
        stipend_from_parent: float = 0.0,
        parent_id: Optional[str] = None
    ):
        self.org_id = org_id
        self.name = name
        self.tier = tier
        self.leader_id = leader_id
        self.members: List[str] = members if members is not None else []
        self.fief_name = fief_name
        self.fief_monthly_income = fief_monthly_income
        self.treasury = treasury
        self.tribute_rate_to_parent = tribute_rate_to_parent
        self.stipend_from_parent = stipend_from_parent
        self.parent_id = parent_id
        self.sub_org_ids: List[str] = []
        # 動態內閣職能槽位 (Offices)
        self.offices: Dict[str, Office] = {}

    def add_office(self, office: Office) -> None:
        """為組織設立新的職能席位"""
        self.offices[office.office_id] = office

    def appoint_office(self, office_id: str, character_id: str) -> Tuple[bool, str]:
        """冊封/任命成員擔任特定職位"""
        if office_id not in self.offices:
            return False, f"任命失敗：組織「{self.name}」不存在職位 ID「{office_id}」！"
        
        # 自動將成員納入組織清單 (若尚未在其中)
        if character_id not in self.members:
            self.members.append(character_id)

        office = self.offices[office_id]
        old_incumbent = office.incumbent_id
        office.incumbent_id = character_id
        
        auth_names = [a.value for a in office.authorities]
        return True, (
            f"【官職冊封】「{self.name}」已正式任命 {character_id} 擔任「{office.title}」！\n"
            f"  - 執掌權能: {auth_names}\n"
            f"  - 前任長官: {old_incumbent if old_incumbent else '無 (自懸缺任命)'}"
        )

    def vacate_office(self, office_id: str) -> Tuple[bool, str]:
        """解除/罷免職位任命，使該職位處於懸缺狀態"""
        if office_id not in self.offices:
            return False, f"罷免失敗：組織中無此職位 ID「{office_id}」！"
        office = self.offices[office_id]
        old_incumbent = office.incumbent_id
        office.incumbent_id = None
        return True, f"【官職罷黜】已解除 {old_incumbent} 之「{office.title}」職務，該職位目前懸缺。"

    def get_authority_holder(self, authority: Authority) -> Optional[str]:
        """
        獲取特定權能之實際執行者：
        若有官員擔任該權能，返回該官員；若懸缺，退回由組織最高領袖 (leader_id) 代管
        """
        for office in self.offices.values():
            if authority in office.authorities and office.incumbent_id:
                return office.incumbent_id
        return self.leader_id

    def get_authority_efficiency(
        self,
        authority: Authority,
        characters_map: Optional[Dict[str, Any]] = None
    ) -> Tuple[float, str]:
        """
        計算組織在特定權能上的運作效率 (受任職者詞條與懸缺狀態影響)
        """
        holder_id = None
        is_vacant = True
        matched_office = None

        for office in self.offices.values():
            if authority in office.authorities:
                matched_office = office
                if office.incumbent_id:
                    holder_id = office.incumbent_id
                    is_vacant = False
                    break

        if is_vacant:
            # 懸缺懲罰：領袖兼管，精力分散，效率折損至 50%
            title = matched_office.title if matched_office else authority.value
            return 0.50, f"【職務懸缺】「{title}」無專任長官，由領袖兼管，運作效率折損 50%。"

        # 若有指定專任長官
        base_eff = 1.0
        bonus_factors = []

        if characters_map and holder_id in characters_map:
            holder = characters_map[holder_id]
            holder_trait_ids = [t.id for t in getattr(holder, "all_traits", getattr(holder, "imprinted_traits", []))]

            if authority == Authority.MILITARY:
                if any("tactician" in tid or "grandmaster" in tid for tid in holder_trait_ids):
                    base_eff += 0.35
                    bonus_factors.append("統帥神威(+35%)")
                if any("veteran" in tid for tid in holder_trait_ids):
                    base_eff += 0.15
                    bonus_factors.append("百戰經驗(+15%)")

            elif authority == Authority.TREASURY:
                if any("monopoly" in tid or "baron" in tid for tid in holder_trait_ids):
                    base_eff += 0.30
                    bonus_factors.append("寡頭手腕(+30%)")
                if any("street_smart" in tid or "arithmetic" in tid for tid in holder_trait_ids):
                    base_eff += 0.15
                    bonus_factors.append("精明算術(+15%)")

            elif authority == Authority.INTRIGUE:
                if any("shadow" in tid or "assassin" in tid for tid in holder_trait_ids):
                    base_eff += 0.30
                    bonus_factors.append("影襲暗殺(+30%)")
                if any("ambitious" in tid for tid in holder_trait_ids):
                    base_eff += 0.10
                    bonus_factors.append("野心私謀(+10%)")

        factor_str = f" ({', '.join(bonus_factors)})" if bonus_factors else ""
        return base_eff, f"「{matched_office.title}」由 {holder_id} 掌管，當前效率: {base_eff*100:.0f}%{factor_str}。"

    def apply_council_template(self, culture_template: str = "feudal_fantasy") -> List[Office]:
        """
        快速應用預設文化/劇本的內閣職能架構
        """
        self.offices.clear()
        created = []

        if culture_template == "feudal_fantasy":
            created = [
                Office("marshal", "王國大元帥", [Authority.MILITARY], monthly_stipend=150.0),
                Office("treasurer", "財政總管", [Authority.TREASURY], monthly_stipend=120.0),
                Office("chancellor", "首席外交御使", [Authority.DIPLOMACY], monthly_stipend=100.0),
                Office("spymaster", "暗影密探總管", [Authority.INTRIGUE], monthly_stipend=130.0),
                Office("steward", "民政大法官", [Authority.INTERNAL_LAW], monthly_stipend=90.0),
                Office("patriarch", "聖堂大主教", [Authority.DOCTRINE], monthly_stipend=80.0)
            ]
        elif culture_template == "scifi_empire":
            created = [
                Office("warmaster", "星區大戰帥", [Authority.MILITARY], monthly_stipend=200.0),
                Office("overseer", "內政部總理審計官", [Authority.TREASURY], monthly_stipend=160.0),
                Office("envoy", "星際全權公使", [Authority.DIPLOMACY], monthly_stipend=120.0),
                Office("inquisitor", "異端審判領主", [Authority.INTRIGUE, Authority.DOCTRINE], monthly_stipend=180.0),
                Office("prefect", "行星治安行政長官", [Authority.INTERNAL_LAW], monthly_stipend=110.0),
                Office("magos", "機械神教大賢者", [Authority.DOCTRINE], monthly_stipend=150.0)
            ]
        elif culture_template == "eastern_sect":
            created = [
                Office("marshal", "執法大長老", [Authority.MILITARY], monthly_stipend=150.0),
                Office("treasurer", "掌財堂堂主", [Authority.TREASURY], monthly_stipend=120.0),
                Office("chancellor", "迎賓外事長老", [Authority.DIPLOMACY], monthly_stipend=100.0),
                Office("spymaster", "影衛暗閣統領", [Authority.INTRIGUE], monthly_stipend=130.0),
                Office("steward", "內務執事堂主", [Authority.INTERNAL_LAW], monthly_stipend=90.0),
                Office("patriarch", "傳功大長老", [Authority.DOCTRINE], monthly_stipend=110.0)
            ]
        else:  # small_squad
            created = [
                Office("deputy", "副隊長", [Authority.MILITARY, Authority.INTERNAL_LAW], monthly_stipend=30.0),
                Office("quartermaster", "隨隊後勤管家", [Authority.TREASURY, Authority.DIPLOMACY], monthly_stipend=20.0)
            ]

        for off in created:
            self.add_office(off)
        return created

    def to_dict(self) -> Dict[str, Any]:
        return {
            "org_id": self.org_id,
            "name": self.name,
            "tier": int(self.tier),
            "leader_id": self.leader_id,
            "members": self.members,
            "fief_name": self.fief_name,
            "fief_monthly_income": self.fief_monthly_income,
            "treasury": self.treasury,
            "tribute_rate_to_parent": self.tribute_rate_to_parent,
            "stipend_from_parent": self.stipend_from_parent,
            "parent_id": self.parent_id,
            "sub_org_ids": self.sub_org_ids,
            "offices": [o.to_dict() for o in self.offices.values()]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Organization':
        org = cls(
            org_id=data["org_id"],
            name=data["name"],
            tier=OrgTier(data["tier"]),
            leader_id=data["leader_id"],
            members=data.get("members", []),
            fief_name=data.get("fief_name"),
            fief_monthly_income=data.get("fief_monthly_income", 0.0),
            treasury=data.get("treasury", 0.0),
            tribute_rate_to_parent=data.get("tribute_rate_to_parent", 0.0),
            stipend_from_parent=data.get("stipend_from_parent", 0.0),
            parent_id=data.get("parent_id")
        )
        org.sub_org_ids = data.get("sub_org_ids", [])
        for off_data in data.get("offices", []):
            office = Office.from_dict(off_data)
            org.add_office(office)
        return org


class OrgManager:
    def __init__(self, social_net: SocialNetwork):
        self.social_net = social_net
        self.all_orgs: Dict[str, Organization] = {}

    def get_org(self, org_id: str) -> Optional[Organization]:
        return self.all_orgs.get(org_id)

    def create_personal_org(self, founder_id: str, partner_id: str, name: str) -> Tuple[bool, str, Optional[Organization]]:
        rel = self.social_net.get_relationship(partner_id, founder_id)
        if rel.willingness < 30.0:
            return False, f"成立失敗：{partner_id} 對 {founder_id} 的意願值僅為 {rel.willingness:.1f}（需 >= 30.0），拒絕加入小隊！", None

        org = Organization(
            org_id=f"org_p_{founder_id}",
            name=name,
            tier=OrgTier.PERSONAL,
            leader_id=founder_id,
            members=[founder_id, partner_id]
        )
        self.all_orgs[org.org_id] = org
        return True, f"【成立成功】個人組織「{name}」已由 {founder_id} 與 {partner_id} 共同成立！", org

    def create_large_org(self, founder_id: str, candidate_ids: List[str], name: str, min_supporters: int = 5) -> Tuple[bool, str, Optional[Organization]]:
        supporters = [cid for cid in candidate_ids if self.social_net.get_relationship(cid, founder_id).willingness >= 30.0]
        if len(supporters) < min_supporters:
            return False, f"成立失敗：贊同人數不足！僅 {len(supporters)}/{min_supporters} 人同意聯署。", None

        org = Organization(
            org_id=f"org_l_{founder_id}",
            name=name,
            tier=OrgTier.LARGE,
            leader_id=founder_id,
            members=[founder_id] + supporters,
            treasury=500.0
        )
        self.all_orgs[org.org_id] = org
        return True, f"【成立成功】大型組織「{name}」由 {founder_id} 號召 {len(supporters)} 位成員正式立會！", org

    def create_chartered_org(self, superior_org: Organization, leader_id: str, name: str, monthly_stipend: float) -> Tuple[bool, str, Optional[Organization]]:
        if superior_org.tier not in (OrgTier.LOCAL, OrgTier.INDEPENDENT):
            return False, f"成立失敗：上級組織「{superior_org.name}」位階不足，無法授銜冊封！", None

        org = Organization(
            org_id=f"org_c_{leader_id}",
            name=name,
            tier=OrgTier.CHARTERED,
            leader_id=leader_id,
            members=[leader_id],
            stipend_from_parent=monthly_stipend,
            parent_id=superior_org.org_id
        )
        superior_org.sub_org_ids.append(org.org_id)
        self.all_orgs[org.org_id] = org
        return True, f"【授銜成功】「{superior_org.name}」正式頒發委任狀，組建授銜軍團「{name}」！", org

    def create_local_faction(
        self,
        superior_org: Organization,
        lord_id: str,
        name: str,
        fief_name: str,
        fief_income: float,
        tribute_rate: float = 0.20
    ) -> Tuple[bool, str, Optional[Organization]]:
        if superior_org.tier != OrgTier.INDEPENDENT:
            return False, f"成立失敗：只有獨立勢力才有權分封合法地方勢力！", None

        org = Organization(
            org_id=f"org_loc_{lord_id}",
            name=name,
            tier=OrgTier.LOCAL,
            leader_id=lord_id,
            members=[lord_id],
            fief_name=fief_name,
            fief_monthly_income=fief_income,
            tribute_rate_to_parent=tribute_rate,
            treasury=1000.0,
            parent_id=superior_org.org_id
        )
        superior_org.sub_org_ids.append(org.org_id)
        self.all_orgs[org.org_id] = org
        return True, f"【分封領地】「{superior_org.name}」分封 {fief_name} 予 {lord_id}，地方勢力「{name}」成立！", org

    def declare_independence(self, local_org: Organization) -> Tuple[bool, str]:
        if local_org.tier != OrgTier.LOCAL:
            return False, "無法自立：該組織不是地方割據勢力！"

        if local_org.parent_id and local_org.parent_id in self.all_orgs:
            parent = self.all_orgs[local_org.parent_id]
            if local_org.org_id in parent.sub_org_ids:
                parent.sub_org_ids.remove(local_org.org_id)

        local_org.tier = OrgTier.INDEPENDENT
        local_org.parent_id = None
        local_org.tribute_rate_to_parent = 0.0
        return True, f"【割據自立】「{local_org.name}」宣佈獨立，成為主權獨立君主勢力！"

    def monthly_economic_tick(self) -> List[str]:
        logs = []
        # 1. 領地稅收
        for org in self.all_orgs.values():
            if org.fief_name and org.fief_monthly_income > 0:
                org.treasury += org.fief_monthly_income
                logs.append(f"[稅收] 【{org.fief_name}】為「{org.name}」產生稅收: +{org.fief_monthly_income:.1f} 金")

        # 2. 地方奉貢
        for org in self.all_orgs.values():
            if org.tier == OrgTier.LOCAL and org.parent_id and org.parent_id in self.all_orgs:
                parent = self.all_orgs[org.parent_id]
                tribute = org.fief_monthly_income * org.tribute_rate_to_parent
                if org.treasury >= tribute:
                    org.treasury -= tribute
                    parent.treasury += tribute
                    logs.append(f"[進貢] 地方勢力「{org.name}」向「{parent.name}」上繳奉貢: -{tribute:.1f} 金")
                else:
                    logs.append(f"[拖欠] 地方勢力「{org.name}」金庫告罄，無法足額上繳奉貢！")

        # 3. 授銜軍餉
        for org in self.all_orgs.values():
            if org.tier == OrgTier.CHARTERED and org.parent_id and org.parent_id in self.all_orgs:
                parent = self.all_orgs[org.parent_id]
                stipend = org.stipend_from_parent
                if parent.treasury >= stipend:
                    parent.treasury -= stipend
                    org.treasury += stipend
                    logs.append(f"[軍餉] 宗主「{parent.name}」向軍團「{org.name}」撥付月餉: -{stipend:.1f} 金")
                else:
                    logs.append(f"[拖欠] 嚴重警告！「{parent.name}」拖欠軍團「{org.name}」軍餉！")

        # 4. 內閣長官俸祿發放 (Office Stipends)
        for org in self.all_orgs.values():
            for off in org.offices.values():
                if off.incumbent_id and off.monthly_stipend > 0:
                    if org.treasury >= off.monthly_stipend:
                        org.treasury -= off.monthly_stipend
                        logs.append(f"[俸祿] 「{org.name}」向「{off.title}」({off.incumbent_id}) 發放俸祿: -{off.monthly_stipend:.1f} 金")
                    else:
                        logs.append(f"[拖欠俸祿] 「{org.name}」金庫拮据，無法向「{off.title}」({off.incumbent_id}) 發放俸祿！")

        return logs

    def to_dict(self) -> List[Dict[str, Any]]:
        return [org.to_dict() for org in self.all_orgs.values()]

    @classmethod
    def from_dict(cls, data: List[Dict[str, Any]], social_net: SocialNetwork) -> 'OrgManager':
        mgr = cls(social_net)
        for item in data:
            org = Organization.from_dict(item)
            mgr.all_orgs[org.org_id] = org
        return mgr
