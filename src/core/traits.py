"""
Trait definitions, Mage ranks, and exponential load constants.
"""

from enum import IntEnum, Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List


class Tier(IntEnum):
    REGULAR = 1
    UNCOMMON = 2
    RARE = 3
    MYSTIC = 4
    EPIC = 5
    TRANSCENDENT = 6

    def __str__(self):
        return self.name.capitalize()


class Category(Enum):
    INNATE = "先天"
    ACQUIRED = "後天"
    ARTIFACT = "器物"


@dataclass
class MageRankDef:
    key: str
    name: str
    tier_cap: Tier
    slot_cap: int
    mp_multiplier: float
    required_interactions: int
    breakthrough_event: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "tier_cap": int(self.tier_cap),
            "slot_cap": self.slot_cap,
            "mp_multiplier": self.mp_multiplier,
            "required_interactions": self.required_interactions,
            "breakthrough_event": self.breakthrough_event
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MageRankDef':
        return cls(
            key=data["key"],
            name=data["name"],
            tier_cap=Tier(data["tier_cap"]),
            slot_cap=data["slot_cap"],
            mp_multiplier=data["mp_multiplier"],
            required_interactions=data["required_interactions"],
            breakthrough_event=data["breakthrough_event"]
        )


MAGE_RANKS: Dict[str, MageRankDef] = {
    "Chorji": MageRankDef(
        key="Chorji",
        name="綽爾濟 (Chorji)",
        tier_cap=Tier.REGULAR,
        slot_cap=3,
        mp_multiplier=1.0,
        required_interactions=0,
        breakthrough_event="【自我覺察】：看見萬物本質，初步干涉因果。"
    ),
    "Shabrung": MageRankDef(
        key="Shabrung",
        name="夏仲 (Shabrung)",
        tier_cap=Tier.UNCOMMON,
        slot_cap=5,
        mp_multiplier=2.0,
        required_interactions=100,
        breakthrough_event="【心識拓寬】：經歷瀕死或精神質變，神經網絡重組。"
    ),
    "Pandita": MageRankDef(
        key="Pandita",
        name="班智達 (Pandita)",
        tier_cap=Tier.RARE,
        slot_cap=10,
        mp_multiplier=4.0,
        required_interactions=500,
        breakthrough_event="【博學者之眼】：研讀《古源刻印手稿》，掌握詞條語法。"
    ),
    "Nomenkhan": MageRankDef(
        key="Nomenkhan",
        name="諾門罕 (Nomenkhan)",
        tier_cap=Tier.MYSTIC,
        slot_cap=20,
        mp_multiplier=8.0,
        required_interactions=1000,
        breakthrough_event="【法王冠冕】：達成世俗人生大事（立國/子嗣），悟透因果之重。"
    ),
    "Hutuktu": MageRankDef(
        key="Hutuktu",
        name="呼圖克圖 (Hutuktu)",
        tier_cap=Tier.EPIC,
        slot_cap=50,
        mp_multiplier=20.0,
        required_interactions=5000,
        breakthrough_event="【轉世與不朽】：覲見第一代永生覺醒者，重組生命法則。"
    ),
    "Transcendent": MageRankDef(
        key="Transcendent",
        name="超凡者 (Transcendent)",
        tier_cap=Tier.TRANSCENDENT,
        slot_cap=999,
        mp_multiplier=9999.0,
        required_interactions=99999,
        breakthrough_event="【全知編織·造物主之權】：登臨神格，超越因果限制，可任意改寫世間萬物本質。"
    )
}

TIER_BASE_LOAD = {
    Tier.REGULAR: 15.0,
    Tier.UNCOMMON: 28.0,
    Tier.RARE: 50.0,
    Tier.MYSTIC: 90.0,
    Tier.EPIC: 160.0,
    Tier.TRANSCENDENT: 0.0
}

TIER_BASE_INSTANT_COST = {
    Tier.REGULAR: 20.0,
    Tier.UNCOMMON: 40.0,
    Tier.RARE: 80.0,
    Tier.MYSTIC: 160.0,
    Tier.EPIC: 350.0,
    Tier.TRANSCENDENT: 0.0
}


LAMBDA_REPULSION = 0.08


@dataclass
class Trait:
    id: str
    name: str
    category: Category
    tier: Tier
    description: str
    modifiers: Dict[str, float] = field(default_factory=dict)
    corruption_delta: float = 0.0  # 刻印或啟用時影響的靈魂腐化變動值 (+為混沌/黑暗面, -為聖潔/光明面)
    tags: List[str] = field(default_factory=list)  # 語意標籤 (例如: ["melee", "fire", "psionic", "tech"])
    parents: List[str] = field(default_factory=list)  # 合成溯源 (紀錄由哪些母詞條 ID 融合而成)
    is_synthetic: bool = False  # 是否為動態即時生成之自創詞條

    @property
    def base_load(self) -> float:
        return TIER_BASE_LOAD[self.tier]

    @property
    def instant_cost(self) -> float:
        return TIER_BASE_INSTANT_COST[self.tier]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.name,
            "tier": int(self.tier),
            "description": self.description,
            "modifiers": self.modifiers,
            "corruption_delta": self.corruption_delta,
            "tags": self.tags,
            "parents": self.parents,
            "is_synthetic": self.is_synthetic
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Trait':
        return cls(
            id=data["id"],
            name=data["name"],
            category=Category[data["category"]],
            tier=Tier(data["tier"]),
            description=data["description"],
            modifiers=data.get("modifiers", {}),
            corruption_delta=float(data.get("corruption_delta", 0.0)),
            tags=list(data.get("tags", [])),
            parents=list(data.get("parents", [])),
            is_synthetic=bool(data.get("is_synthetic", False))
        )
