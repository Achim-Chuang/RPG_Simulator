"""
Pairwise Social Network & 5-Tier Taikou-style Organization Prototype
Models:
1. Directed Dyadic Graph (Affection, Respect, Obligation)
2. Five Org Tiers: Personal, Large, Chartered, Local, Independent
3. Hierarchical subordination, territorial revenue, tribute, and payroll/stipends.
"""

from enum import IntEnum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


class OrgTier(IntEnum):
    PERSONAL = 1     # 個人組織（小隊、搭檔）
    LARGE = 2        # 大型組織（公會、傭兵團、商會）
    CHARTERED = 3    # 授銜組織（騎士團、親衛軍團，上級撥款發餉）
    LOCAL = 4        # 地方勢力（城主、分封領主，有地盤，需進貢上級）
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


# ==============================================================================
# 1. 倆倆雙向社交網絡 (Pairwise Social Network)
# ==============================================================================

@dataclass
class Relationship:
    from_id: str
    to_id: str
    affection: float = 0.0   # 好感度 (-100 ~ +100)
    respect: float = 0.0     # 敬畏度 (-100 ~ +100)
    obligation: float = 0.0  # 恩怨值 (-100 ~ +100，正為欠人情/感恩，負為結仇)

    @property
    def willingness(self) -> float:
        """
        對目標的配合意願綜合評分:
        Willingness = 0.5 * Affection + 0.3 * Respect + 0.2 * Obligation
        門檻: > 30 為願意結伴或入隊，> 50 為忠誠擁戴
        """
        return 0.5 * self.affection + 0.3 * self.respect + 0.2 * self.obligation


class SocialNetwork:
    def __init__(self):
        # 鍵值: (from_char_id, to_char_id) -> Relationship
        self.matrix: Dict[Tuple[str, str], Relationship] = {}

    def get_relationship(self, from_id: str, to_id: str) -> Relationship:
        pair = (from_id, to_id)
        if pair not in self.matrix:
            self.matrix[pair] = Relationship(from_id=from_id, to_id=to_id)
        return self.matrix[pair]

    def modify(self, from_id: str, to_id: str, d_aff: float = 0.0, d_resp: float = 0.0, d_ob: float = 0.0):
        rel = self.get_relationship(from_id, to_id)
        rel.affection = max(-100.0, min(100.0, rel.affection + d_aff))
        rel.respect = max(-100.0, min(100.0, rel.respect + d_resp))
        rel.obligation = max(-100.0, min(100.0, rel.obligation + d_ob))


# ==============================================================================
# 2. 五階組織實體 (Organization Entity)
# ==============================================================================

@dataclass
class Organization:
    org_id: str
    name: str
    tier: OrgTier
    leader_id: str
    members: List[str] = field(default_factory=list)

    # 樹狀上下級關係
    parent_org: Optional['Organization'] = None
    sub_orgs: List['Organization'] = field(default_factory=list)

    # 地盤與財政
    fief_name: Optional[str] = None          # 統治地盤名稱 (地方/獨立勢力必備)
    fief_monthly_income: float = 0.0         # 地盤每月稅收
    treasury: float = 0.0                    # 組織金庫儲備

    # 經濟流動合約
    tribute_rate_to_parent: float = 0.0      # 地方勢力向獨立勢力的進貢比例 (如 0.20 = 20%)
    stipend_from_parent: float = 0.0         # 授銜組織每月從上級領取的軍餉/預算

    def add_sub_org(self, sub: 'Organization'):
        sub.parent_org = self
        if sub not in self.sub_orgs:
            self.sub_orgs.append(sub)

    def remove_sub_org(self, sub: 'Organization'):
        if sub in self.sub_orgs:
            self.sub_orgs.remove(sub)
        sub.parent_org = None


# ==============================================================================
# 3. 組織成立與晉升系統 (Org Management & Lifecycle)
# ==============================================================================

class OrgManager:
    def __init__(self, social_net: SocialNetwork):
        self.social_net = social_net
        self.all_orgs: Dict[str, Organization] = {}

    def create_personal_org(self, founder_id: str, partner_id: str, name: str) -> Tuple[bool, str, Optional[Organization]]:
        """
        個人組織：任何人皆可發起，但至少需 1 人同意共同加入。
        檢定 partner 對 founder 的意願值 (Willingness >= 30.0)。
        """
        rel = self.social_net.get_relationship(partner_id, founder_id)
        w = rel.willingness
        if w < 30.0:
            return False, f"成立失敗：{partner_id} 對 {founder_id} 的意願值僅為 {w:.1f}（需 >= 30.0），拒絕加入小隊！", None

        org = Organization(
            org_id=f"org_p_{founder_id}",
            name=name,
            tier=OrgTier.PERSONAL,
            leader_id=founder_id,
            members=[founder_id, partner_id]
        )
        self.all_orgs[org.org_id] = org
        return True, f"【成立成功】個人組織「{name}」已由 {founder_id} 與 {partner_id} 共同成立！(意願值: {w:.1f})", org

    def create_large_org(self, founder_id: str, candidate_ids: List[str], name: str, min_supporters: int = 5) -> Tuple[bool, str, Optional[Organization]]:
        """
        大型組織：需要達到法定人數（如 >= 5 人）同意聯署成立。
        """
        supporters = []
        for cid in candidate_ids:
            rel = self.social_net.get_relationship(cid, founder_id)
            if rel.willingness >= 30.0:
                supporters.append(cid)

        if len(supporters) < min_supporters:
            return False, f"成立失敗：贊同人數不足！僅 {len(supporters)}/{min_supporters} 人同意聯署。", None

        all_members = [founder_id] + supporters
        org = Organization(
            org_id=f"org_l_{founder_id}",
            name=name,
            tier=OrgTier.LARGE,
            leader_id=founder_id,
            members=all_members,
            treasury=500.0  # 初始眾籌會費
        )
        self.all_orgs[org.org_id] = org
        return True, f"【成立成功】大型組織「{name}」由 {founder_id} 號召 {len(supporters)} 位成員正式立會！初始會費: 500 金", org

    def create_chartered_org(self, superior_org: Organization, leader_id: str, name: str, monthly_stipend: float) -> Tuple[bool, str, Optional[Organization]]:
        """
        授銜組織：需要上級組織（地方勢力或獨立勢力）授權，上級定期由金庫發餉。
        """
        if superior_org.tier not in (OrgTier.LOCAL, OrgTier.INDEPENDENT):
            return False, f"成立失敗：上級組織「{superior_org.name}」位階不足，無法授銜冊封！", None

        org = Organization(
            org_id=f"org_c_{leader_id}",
            name=name,
            tier=OrgTier.CHARTERED,
            leader_id=leader_id,
            members=[leader_id],
            stipend_from_parent=monthly_stipend
        )
        superior_org.add_sub_org(org)
        self.all_orgs[org.org_id] = org
        return True, f"【授銜成功】「{superior_org.name}」正式頒發委任狀，組建授銜軍團「{name}」，月俸額度: {monthly_stipend} 金！", org

    def create_local_faction(self, superior_org: Organization, lord_id: str, name: str, fief_name: str, fief_income: float, tribute_rate: float = 0.20) -> Tuple[bool, str, Optional[Organization]]:
        """
        地方勢力：由獨立勢力或高級領主賜予地盤（或佔領地盤得到承認），自負盈虧並向上繳納奉貢。
        """
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
            treasury=1000.0  # 領地初始金庫
        )
        superior_org.add_sub_org(org)
        self.all_orgs[org.org_id] = org
        return True, f"【分封領地】「{superior_org.name}」分封 {fief_name} 予 {lord_id}，地方勢力「{name}」成立！(月產出: {fief_income} 金，進貢率: {tribute_rate*100:.0f}%)", org

    def declare_independence(self, local_org: Organization) -> Tuple[bool, str]:
        """
        割據自立：地方勢力脫離上級獨立勢力，晉升為【獨立勢力】。
        停止進貢，保留自身地盤與下屬組織。
        """
        if local_org.tier != OrgTier.LOCAL:
            return False, f"無法自立：該組織不是地方割據勢力！"

        old_parent = local_org.parent_org
        if old_parent:
            old_parent.remove_sub_org(local_org)

        local_org.tier = OrgTier.INDEPENDENT
        local_org.tribute_rate_to_parent = 0.0

        return True, f"【天下震動·割據自立】「{local_org.name}」宣佈撕毀與「{old_parent.name if old_parent else '舊宗主'}」的臣服條約，自立為獨立君主勢力！"

    def monthly_economic_tick(self):
        """
        月度經濟結算循環：
        1. 地盤收益產生（地方 / 獨立勢力）
        2. 地方勢力向上級進貢
        3. 上級勢力向下轄授銜組織撥發軍餉
        """
        print("\n" + "=" * 65)
        print("          【月度經濟與組織金流結算 (Monthly Tick)】")
        print("=" * 65)

        # 1. 產生領地稅收
        for org in self.all_orgs.values():
            if org.fief_name and org.fief_monthly_income > 0:
                org.treasury += org.fief_monthly_income
                print(f"[稅收產出] 領地【{org.fief_name}】為「{org.name}」注入收入: +{org.fief_monthly_income:.1f} 金 (金庫: {org.treasury:.1f})")

        # 2. 地方勢力向上繳納奉貢
        for org in self.all_orgs.values():
            if org.tier == OrgTier.LOCAL and org.parent_org:
                tribute = org.fief_monthly_income * org.tribute_rate_to_parent
                if org.treasury >= tribute:
                    org.treasury -= tribute
                    org.parent_org.treasury += tribute
                    print(f"[奉貢繳納] 地方勢力「{org.name}」向宗主「{org.parent_org.name}」上繳奉貢: -{tribute:.1f} 金 (剩餘: {org.treasury:.1f} | 宗主入帳: +{tribute:.1f})")
                else:
                    print(f"[奉貢拖欠] 警告！地方勢力「{org.name}」金庫告罄，無法足額上繳奉貢！宗主好感下降！")

        # 3. 授銜組織軍餉撥發
        for org in self.all_orgs.values():
            if org.tier == OrgTier.CHARTERED and org.parent_org:
                stipend = org.stipend_from_parent
                parent = org.parent_org
                if parent.treasury >= stipend:
                    parent.treasury -= stipend
                    org.treasury += stipend
                    print(f"[軍餉撥發] 宗主「{parent.name}」向授銜軍團「{org.name}」撥付月餉: -{stipend:.1f} 金 (軍團金庫: {org.treasury:.1f})")
                else:
                    print(f"[軍餉拖欠] 嚴重警告！「{parent.name}」財政崩潰，拖欠「{org.name}」軍餉！軍團士氣大跌！")

        print("=" * 65 + "\n")


# ==============================================================================
# 4. 完整模擬演練：主角的太閣式立志傳
# ==============================================================================

def run_simulation():
    print("*" * 70)
    print("      太閣立志式：倆倆社交與五階組織系統演練 (Taikou Social & Org)")
    print("*" * 70)

    social = SocialNetwork()
    manager = OrgManager(social)

    # 角色定義
    hero = "無名孤兒(主角)"
    veteran = "受傷老兵(加拉哈)"
    mercs = [f"雇傭兵_{i}號" for i in range(1, 8)]
    king = "奧古斯都三世(聖王國君主)"

    # 1. 創立最頂層獨立勢力：神聖帝國
    empire = Organization(
        org_id="org_empire",
        name="神聖洛蘭王國",
        tier=OrgTier.INDEPENDENT,
        leader_id=king,
        fief_name="王都·黃金城",
        fief_monthly_income=5000.0,
        treasury=20000.0
    )
    manager.all_orgs[empire.org_id] = empire
    print(f"\n[世界格局背景]")
    print(f"頂級獨立勢力: {empire.name} | 君主: {king} | 金庫: {empire.treasury} 金")

    # 2. 階段一：個人組織（小隊建立）
    print("\n" + "-" * 70)
    print("【階段一：個人小隊成立】")
    # 初始未培養感情
    success, msg, squad = manager.create_personal_org(hero, veteran, "破曉二人小隊")
    print(msg)

    # 主角救治老兵、贈酒，建立深厚羈絆
    print("\n--> 主角為老兵治療骨折，並長談天下大勢 (增加好感與敬畏)...")
    social.modify(veteran, hero, d_aff=60.0, d_resp=40.0, d_ob=30.0)
    rel = social.get_relationship(veteran, hero)
    print(f"老兵對主角態度更新: 好感={rel.affection}, 敬畏={rel.respect}, 恩怨={rel.obligation} (綜合意願={rel.willingness:.1f})")

    success, msg, squad = manager.create_personal_org(hero, veteran, "破曉二人小隊")
    print(msg)

    # 3. 階段二：大型組織（傭兵公會）
    print("\n" + "-" * 70)
    print("【階段二：號召群雄，成立大型公會】")
    # 培養 5 個傭兵的意願（贈禮與立威）
    for m in mercs[:5]:
        social.modify(m, hero, d_aff=40.0, d_resp=40.0, d_ob=10.0)

    success, msg, guild = manager.create_large_org(hero, mercs, "黑水傭兵公會", min_supporters=5)
    print(msg)

    # 4. 階段三：獲取封地，晉升地方勢力
    print("\n" + "-" * 70)
    print("【階段三：立下戰功，受封邊境城主 (地方勢力)】")
    print("主角率黑水傭兵公會平定北方邊患，國王奧古斯都三世正式敕封...")
    success, msg, fief = manager.create_local_faction(
        superior_org=empire,
        lord_id=hero,
        name="鐵拳領·北境守護府",
        fief_name="黑岩要塞群",
        fief_income=1200.0,
        tribute_rate=0.20 # 20% 奉貢
    )
    print(msg)

    # 5. 階段四：授銜組織（特許成立霜狼親衛軍團）
    print("\n" + "-" * 70)
    print("【階段四：建立授銜武裝 (地方授權騎士團)】")
    success, msg, legion = manager.create_chartered_org(
        superior_org=fief,
        leader_id=veteran,
        name="北境霜狼近衛軍",
        monthly_stipend=250.0 # 每月由鐵拳領撥款
    )
    print(msg)

    # 6. 運轉月度財政循環
    manager.monthly_economic_tick()

    # 7. 階段五：自立稱霸（獨立勢力）
    print("-" * 70)
    print("【階段五：野心膨脹，割據自立！】")
    success, msg = manager.declare_independence(fief)
    print(msg)
    print(f"鐵拳領新位階: {fief.tier} (已無上級組織，進貢率: {fief.tribute_rate_to_parent}%)")

    # 再次結算月度財政，驗證不再向上級進貢
    manager.monthly_economic_tick()


if __name__ == "__main__":
    run_simulation()
