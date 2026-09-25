"""
Physical Multi-tier Economy, Dynamic Pricing, Supply Chains, and Emergent Strategic Commerce.
Simulates primary production (farms, mines, lumber), secondary processing (bakeries, smithies),
specialties, local inventories, non-linear pricing, merchant caravans, and strategic warfare
(blockade, embargo, commerce raiding, arbitrage).
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import math


class CommodityType(Enum):
    RAW = "一級原物料"
    PROCESSED = "二級加工品"
    SPECIALTY = "三級特產"


@dataclass
class Commodity:
    id: str
    name: str
    commodity_type: CommodityType
    base_price: float
    is_essential: bool = False
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "commodity_type": self.commodity_type.name,
            "base_price": self.base_price,
            "is_essential": self.is_essential,
            "description": self.description
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Commodity':
        return cls(
            id=data["id"],
            name=data["name"],
            commodity_type=CommodityType[data["commodity_type"]],
            base_price=float(data["base_price"]),
            is_essential=data.get("is_essential", False),
            description=data.get("description", "")
        )


STANDARD_COMMODITIES: Dict[str, Commodity] = {
    # 一級原物料
    "raw_grain": Commodity("raw_grain", "小麥原糧", CommodityType.RAW, 5.0, is_essential=True, description="生存基石，麵包坊與釀造坊核心原料"),
    "raw_iron_ore": Commodity("raw_iron_ore", "精鍊鐵礦", CommodityType.RAW, 12.0, is_essential=False, description="山脈礦區產出，鍛造兵刃甲冑的軍工物資"),
    "raw_timber": Commodity("raw_timber", "硬木原木", CommodityType.RAW, 8.0, is_essential=False, description="森林林場產出，建築、車架與兵刃握柄原料"),
    "raw_herbs": Commodity("raw_herbs", "野生草藥", CommodityType.RAW, 15.0, is_essential=True, description="沼澤荒野採集，煉製療傷膏劑原料"),

    # 二級加工品
    "good_bread": Commodity("good_bread", "補給麵包", CommodityType.PROCESSED, 18.0, is_essential=True, description="居民口糧與軍隊行軍口糧，由小麥烘焙而成"),
    "good_weapons": Commodity("good_weapons", "鍛鐵兵刃", CommodityType.PROCESSED, 55.0, is_essential=False, description="由鐵礦與原木鍛造，軍團列裝與武裝防衛必需"),
    "good_medicine": Commodity("good_medicine", "金創膏劑", CommodityType.PROCESSED, 45.0, is_essential=True, description="由草藥萃取提煉，治療重創與戰後恢復"),

    # 三級特產
    "spec_ostia_vintage": Commodity("spec_ostia_vintage", "奧斯提亞·海灣烈焰名酒", CommodityType.SPECIALTY, 130.0, is_essential=False, description="自由城邦特產名酒，豪奢商賈與貴族追捧的極品"),
    "spec_damascus_steel": Commodity("spec_damascus_steel", "大馬士革·精鋼重劍", CommodityType.SPECIALTY, 190.0, is_essential=False, description="鐵血騎士大公國秘傳鍛爐打造的削鐵如泥寶刃")
}


@dataclass
class ProductionRecipe:
    recipe_id: str
    name: str
    inputs: Dict[str, int]     # 如 {"raw_grain": 2}，一級原物料開採為空 {}
    outputs: Dict[str, int]    # 如 {"good_bread": 1}
    labor_cost: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recipe_id": self.recipe_id,
            "name": self.name,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "labor_cost": self.labor_cost
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProductionRecipe':
        return cls(
            recipe_id=data["recipe_id"],
            name=data["name"],
            inputs=dict(data.get("inputs", {})),
            outputs=dict(data.get("outputs", {})),
            labor_cost=float(data.get("labor_cost", 0.0))
        )


STANDARD_RECIPES: Dict[str, ProductionRecipe] = {
    # 一級產業開採
    "recipe_grain_farm": ProductionRecipe("recipe_grain_farm", "沃土農莊墾殖", {}, {"raw_grain": 20}),
    "recipe_iron_mine": ProductionRecipe("recipe_iron_mine", "山嶽礦井開採", {}, {"raw_iron_ore": 10}),
    "recipe_lumberyard": ProductionRecipe("recipe_lumberyard", "密林伐木作業", {}, {"raw_timber": 12}),
    "recipe_herb_garden": ProductionRecipe("recipe_herb_garden", "荒野草藥採集", {}, {"raw_herbs": 8}),

    # 二級作坊加工
    "recipe_bakery": ProductionRecipe("recipe_bakery", "烘焙工坊", {"raw_grain": 2}, {"good_bread": 1}),
    "recipe_blacksmith": ProductionRecipe("recipe_blacksmith", "鐵匠鋪鍛造", {"raw_iron_ore": 2, "raw_timber": 1}, {"good_weapons": 1}),
    "recipe_apothecary": ProductionRecipe("recipe_apothecary", "藥劑師工房", {"raw_herbs": 2}, {"good_medicine": 1}),

    # 三級特產工房
    "recipe_winery": ProductionRecipe("recipe_winery", "海灣釀酒莊園", {"raw_grain": 3}, {"spec_ostia_vintage": 1}),
    "recipe_damascus_forge": ProductionRecipe("recipe_damascus_forge", "大公近衛密傳鍛爐", {"raw_iron_ore": 3}, {"spec_damascus_steel": 1})
}


@dataclass
class Workshop:
    workshop_id: str
    name: str
    recipe: ProductionRecipe
    owner_org_id: Optional[str] = None
    is_active: bool = True
    stalled: bool = False
    stalled_reason: str = ""
    daily_batches: int = 1

    def produce(self, market: 'LocalMarket') -> Tuple[bool, str]:
        """
        執行每日生產：
        1. 檢驗 market.inventory 是否擁有足夠輸入物料 (inputs * daily_batches)
        2. 若原料不足，標記 stalled = True，記錄日誌並返回 False
        3. 若原料齊全，實體扣除原料，產出成品至 market.inventory
        """
        if not self.is_active:
            self.stalled = True
            self.stalled_reason = "作坊停業中"
            return False, f"【{self.name}】作坊停業中，未運作。"

        # 檢驗原料
        for item_id, req_amt in self.recipe.inputs.items():
            total_needed = req_amt * self.daily_batches
            current_amt = market.inventory.get(item_id, 0)
            if current_amt < total_needed:
                self.stalled = True
                item_name = STANDARD_COMMODITIES.get(item_id, Commodity(item_id, item_id, CommodityType.RAW, 1.0)).name
                self.stalled_reason = f"原料短缺: 缺少 {item_name} (需 {total_needed}, 現有 {current_amt})"
                return False, f"【{self.name}】生產停擺！原因：缺少原料【{item_name}】(需 {total_needed}，在庫僅 {current_amt})"

        # 原料齊全，實體扣除
        for item_id, req_amt in self.recipe.inputs.items():
            market.inventory[item_id] -= req_amt * self.daily_batches

        # 成品產出
        produced_names = []
        for out_id, out_amt in self.recipe.outputs.items():
            total_out = out_amt * self.daily_batches
            market.inventory[out_id] = market.inventory.get(out_id, 0) + total_out
            out_name = STANDARD_COMMODITIES.get(out_id, Commodity(out_id, out_id, CommodityType.PROCESSED, 1.0)).name
            produced_names.append(f"{out_name} x{total_out}")

        self.stalled = False
        self.stalled_reason = ""
        return True, f"【{self.name}】運作順暢，產出：{', '.join(produced_names)}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workshop_id": self.workshop_id,
            "name": self.name,
            "recipe": self.recipe.to_dict(),
            "owner_org_id": self.owner_org_id,
            "is_active": self.is_active,
            "stalled": self.stalled,
            "stalled_reason": self.stalled_reason,
            "daily_batches": self.daily_batches
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Workshop':
        return cls(
            workshop_id=data["workshop_id"],
            name=data["name"],
            recipe=ProductionRecipe.from_dict(data["recipe"]),
            owner_org_id=data.get("owner_org_id"),
            is_active=data.get("is_active", True),
            stalled=data.get("stalled", False),
            stalled_reason=data.get("stalled_reason", ""),
            daily_batches=data.get("daily_batches", 1)
        )


class LocalMarket:
    """
    節點在地市場：包含在地實體庫存、常態安全庫存、人口消耗、作坊、動態供需價格與圍城/禁運狀態。
    """
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.inventory: Dict[str, int] = {}
        self.target_stock: Dict[str, int] = {}
        self.daily_consumption: Dict[str, int] = {}
        self.workshops: List[Workshop] = []
        self.embargo_list: List[str] = []   # 受禁運組織/勢力清單
        self.is_blockaded: bool = False     # 是否被圍城/封鎖中
        self.crisis_logs: List[str] = []

    def get_price(self, commodity_id: str) -> float:
        """
        動態物價公式：
        P = P_base * (TargetStock / max(1, CurrentStock)) ^ 0.65
        價格區間限制在 [0.2 * P_base, 8.0 * P_base]
        """
        comm = STANDARD_COMMODITIES.get(commodity_id)
        if not comm:
            return 10.0

        p_base = comm.base_price
        target = max(1, self.target_stock.get(commodity_id, 10))
        current = max(1, self.inventory.get(commodity_id, 0))

        ratio = target / current
        dynamic_factor = math.pow(ratio, 0.65)

        price = p_base * dynamic_factor
        min_p = p_base * 0.20
        max_p = p_base * 8.00
        price = max(min_p, min(max_p, price))
        return round(price, 1)

    def consume_daily(self) -> List[str]:
        """
        城鎮人口每日生存消耗。
        若庫存耗盡且為必需品，觸發暴動與生存危機！
        """
        logs = []
        for comm_id, amt in self.daily_consumption.items():
            current = self.inventory.get(comm_id, 0)
            comm_name = STANDARD_COMMODITIES.get(comm_id, Commodity(comm_id, comm_id, CommodityType.RAW, 1.0)).name

            if current >= amt:
                self.inventory[comm_id] = current - amt
            else:
                self.inventory[comm_id] = 0
                shortage = amt - current
                alert = f"【物資告急】節點 {self.node_id} 必需物資【{comm_name}】斷供！缺額 {shortage} 份！民怨沸騰！"
                self.crisis_logs.append(alert)
                logs.append(alert)
        return logs

    def execute_workshops(self) -> List[str]:
        logs = []
        for ws in self.workshops:
            success, msg = ws.produce(self)
            logs.append(msg)
        return logs

    def buy_from_market(self, commodity_id: str, quantity: int, buyer_gold: float) -> Tuple[bool, int, float, str]:
        """
        買入：檢查市場現有庫存與買家黃金。
        """
        if self.is_blockaded:
            return False, 0, 0.0, f"節點 {self.node_id} 正處於【圍城封鎖】中，商路斷絕，市場停止對外交易！"

        avail = self.inventory.get(commodity_id, 0)
        if avail <= 0:
            return False, 0, 0.0, f"市場無現貨存量。"

        actual_qty = min(avail, quantity)
        unit_price = self.get_price(commodity_id)
        total_cost = round(unit_price * actual_qty, 1)

        if buyer_gold < total_cost:
            # 依現有資金能買多少
            max_can_afford = int(buyer_gold // unit_price)
            if max_can_afford <= 0:
                return False, 0, 0.0, f"買方資金不足 (單價 {unit_price}, 持有 {buyer_gold})。"
            actual_qty = min(actual_qty, max_can_afford)
            total_cost = round(unit_price * actual_qty, 1)

        self.inventory[commodity_id] -= actual_qty
        comm_name = STANDARD_COMMODITIES.get(commodity_id, Commodity(commodity_id, commodity_id, CommodityType.RAW, 1.0)).name
        return True, actual_qty, total_cost, f"成功自市場購得【{comm_name}】x{actual_qty}，花費 {total_cost} 金幣 (單價 {unit_price})。"

    def sell_to_market(self, commodity_id: str, quantity: int) -> Tuple[bool, int, float, str]:
        """
        賣出：賣給市場增加庫存，市場出價為市價的 85%（扣除商稅與盤商利潤）
        """
        if self.is_blockaded:
            return False, 0, 0.0, f"節點 {self.node_id} 正處於【圍城封鎖】中，無法接收外來物資！"

        unit_sell_price = round(self.get_price(commodity_id) * 0.85, 1)
        total_payout = round(unit_sell_price * quantity, 1)
        self.inventory[commodity_id] = self.inventory.get(commodity_id, 0) + quantity
        comm_name = STANDARD_COMMODITIES.get(commodity_id, Commodity(commodity_id, commodity_id, CommodityType.RAW, 1.0)).name
        return True, quantity, total_payout, f"成功向市場售出【{comm_name}】x{quantity}，獲得 {total_payout} 金幣 (結算單價 {unit_sell_price})。"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "inventory": dict(self.inventory),
            "target_stock": dict(self.target_stock),
            "daily_consumption": dict(self.daily_consumption),
            "workshops": [w.to_dict() for w in self.workshops],
            "embargo_list": list(self.embargo_list),
            "is_blockaded": self.is_blockaded,
            "crisis_logs": self.crisis_logs[-50:]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LocalMarket':
        market = cls(node_id=data["node_id"])
        market.inventory = dict(data.get("inventory", {}))
        market.target_stock = dict(data.get("target_stock", {}))
        market.daily_consumption = dict(data.get("daily_consumption", {}))
        market.workshops = [Workshop.from_dict(w) for w in data.get("workshops", [])]
        market.embargo_list = list(data.get("embargo_list", []))
        market.is_blockaded = data.get("is_blockaded", False)
        market.crisis_logs = list(data.get("crisis_logs", []))
        return market


@dataclass
class MerchantCaravan:
    """
    實體行商車隊：攜帶實體貨物與黃金穿梭於地圖節點之間。
    支援破交伏擊（貨物全掉落）、商人自主低買高賣套利。
    """
    caravan_id: str
    name: str
    owner_id: str
    current_node_id: str
    destination_node_id: Optional[str] = None
    route: List[str] = field(default_factory=list)
    cargo: Dict[str, int] = field(default_factory=dict)
    gold: float = 500.0
    capacity: int = 150
    status: str = "IDLE"  # IDLE, TRAVELING, RAIDED, ARRIVED

    @property
    def current_load(self) -> int:
        return sum(self.cargo.values())

    def load_cargo(self, commodity_id: str, amount: int) -> int:
        free_space = max(0, self.capacity - self.current_load)
        actual = min(amount, free_space)
        if actual > 0:
            self.cargo[commodity_id] = self.cargo.get(commodity_id, 0) + actual
        return actual

    def unload_cargo(self, commodity_id: str, amount: int) -> int:
        current = self.cargo.get(commodity_id, 0)
        actual = min(current, amount)
        if actual > 0:
            self.cargo[commodity_id] -= actual
            if self.cargo[commodity_id] <= 0:
                del self.cargo[commodity_id]
        return actual

    def step_travel(self) -> Tuple[bool, str]:
        """在預定路徑上推進一格節點"""
        if self.status != "TRAVELING" or not self.route:
            return False, f"車隊【{self.name}】未處於行進狀態。"

        next_node = self.route.pop(0)
        self.current_node_id = next_node

        if not self.route:
            self.status = "ARRIVED"
            return True, f"車隊【{self.name}】已順利抵達目的地節點【{next_node}】！"
        else:
            return True, f"車隊【{self.name}】抵達中繼節點【{next_node}】，距離目的地尚餘 {len(self.route)} 站。"

    def raid(self, raider_name: str) -> Tuple[Dict[str, int], float, str]:
        """
        破交截擊：車隊遭到伏擊！貨物被掠奪一空，車隊狀態變為 RAIDED。
        """
        looted_cargo = dict(self.cargo)
        looted_gold = round(self.gold * 0.7, 1)

        self.cargo.clear()
        self.gold -= looted_gold
        self.status = "RAIDED"

        loot_summary = ", ".join([f"{STANDARD_COMMODITIES[k].name} x{v}" for k, v in looted_cargo.items() if k in STANDARD_COMMODITIES])
        msg = f"【破交截擊大捷】{raider_name} 攔截了【{self.name}】！繳獲貨物：[{loot_summary}] 與 {looted_gold} 金幣！車隊癱瘓！"
        return looted_cargo, looted_gold, msg

    def to_dict(self) -> Dict[str, Any]:
        return {
            "caravan_id": self.caravan_id,
            "name": self.name,
            "owner_id": self.owner_id,
            "current_node_id": self.current_node_id,
            "destination_node_id": self.destination_node_id,
            "route": list(self.route),
            "cargo": dict(self.cargo),
            "gold": self.gold,
            "capacity": self.capacity,
            "status": self.status
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MerchantCaravan':
        return cls(
            caravan_id=data["caravan_id"],
            name=data["name"],
            owner_id=data["owner_id"],
            current_node_id=data["current_node_id"],
            destination_node_id=data.get("destination_node_id"),
            route=list(data.get("route", [])),
            cargo=dict(data.get("cargo", {})),
            gold=float(data.get("gold", 500.0)),
            capacity=data.get("capacity", 150),
            status=data.get("status", "IDLE")
        )
