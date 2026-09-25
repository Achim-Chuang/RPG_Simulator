"""
Five-Tier Organization System, Hierarchical Subordination, and Territorial Economic Cycles.
"""

from enum import IntEnum
from typing import Dict, List, Optional, Tuple, Any
from .social import SocialNetwork


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
            "sub_org_ids": self.sub_org_ids
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
