"""
Graph-based World Map topology: Nodes (Cities, Towns, Outposts, Wilderness, Ruins)
and Edges (Highways, Trails, Dangerous Paths) with AP costs and pathfinding.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
from collections import deque
from .economy import LocalMarket


class WorldTheme(Enum):
    FANTASY = "中世紀奇幻"
    SCI_FI = "星際科幻/太空"


class NodeType(Enum):
    CITY = "城邦大都"
    OUTPOST = "要塞哨所"
    TOWN = "商貿城鎮"
    WILDERNESS = "荒野節點"
    RUIN = "遠古遺跡"


class RoadType(Enum):
    HIGHWAY = "商貿官道"        # AP: 1, 危險係數: 0.10
    TRAIL = "荒野小徑"          # AP: 2, 危險係數: 0.30
    DANGEROUS_PATH = "險峻絕徑" # AP: 3, 危險係數: 0.55

    @property
    def default_ap(self) -> int:
        if self == RoadType.HIGHWAY:
            return 1
        elif self == RoadType.TRAIL:
            return 2
        else:
            return 3

    @property
    def default_danger(self) -> float:
        if self == RoadType.HIGHWAY:
            return 0.10
        elif self == RoadType.TRAIL:
            return 0.30
        else:
            return 0.55


THEME_ALIASES = {
    WorldTheme.FANTASY: {
        NodeType.CITY: "城邦大都",
        NodeType.OUTPOST: "要塞哨所",
        NodeType.TOWN: "商貿城鎮",
        NodeType.WILDERNESS: "荒野節點",
        NodeType.RUIN: "遠古遺跡",
        RoadType.HIGHWAY: "商貿官道",
        RoadType.TRAIL: "荒野小徑",
        RoadType.DANGEROUS_PATH: "險峻絕徑",
    },
    WorldTheme.SCI_FI: {
        NodeType.CITY: "核心大都行星 (Core Planet)",
        NodeType.OUTPOST: "軌道防禦空間站 (Orbital Station)",
        NodeType.TOWN: "礦業殖民前哨 (Colony Outpost)",
        NodeType.WILDERNESS: "深空無人星域 (Deep Space Void)",
        NodeType.RUIN: "太空廢船/遠古巨構 (Derelict Hulk / Ancient Megastructure)",
        RoadType.HIGHWAY: "超空間巡邏跳躍線 (Patrolled Hyperspace Route)",
        RoadType.TRAIL: "偏遠未測繪跳躍道 (Uncharted Sub-space Lane)",
        RoadType.DANGEROUS_PATH: "狂暴亞空間風暴裂隙 (Volatile Warp Storm Rift)",
    }
}


@dataclass
class MapNode:
    node_id: str
    name: str
    node_type: NodeType
    coords: Tuple[int, int] = (0, 0)
    fief_or_org_id: Optional[str] = None
    ruin_id: Optional[str] = None
    market: Optional[LocalMarket] = None
    theme_label: Optional[str] = None
    orbital_type: Optional[str] = None  # 如 "Hive World", "Forge World", "Agri-World"

    def __post_init__(self):
        if self.market is None:
            self.market = LocalMarket(self.node_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "node_type": self.node_type.name,
            "coords": list(self.coords),
            "fief_or_org_id": self.fief_or_org_id,
            "ruin_id": self.ruin_id,
            "market": self.market.to_dict() if self.market else None,
            "theme_label": self.theme_label,
            "orbital_type": self.orbital_type
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MapNode':
        market = None
        if "market" in data and data["market"] is not None:
            market = LocalMarket.from_dict(data["market"])
        return cls(
            node_id=data["node_id"],
            name=data["name"],
            node_type=NodeType[data["node_type"]],
            coords=tuple(data.get("coords", [0, 0])),
            fief_or_org_id=data.get("fief_or_org_id"),
            ruin_id=data.get("ruin_id"),
            market=market,
            theme_label=data.get("theme_label"),
            orbital_type=data.get("orbital_type")
        )


@dataclass
class MapEdge:
    from_node_id: str
    to_node_id: str
    road_type: RoadType
    ap_cost: int
    danger_rating: float
    theme_label: Optional[str] = None
    warp_instability: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_node_id": self.from_node_id,
            "to_node_id": self.to_node_id,
            "road_type": self.road_type.name,
            "ap_cost": self.ap_cost,
            "danger_rating": self.danger_rating,
            "theme_label": self.theme_label,
            "warp_instability": self.warp_instability
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MapEdge':
        return cls(
            from_node_id=data["from_node_id"],
            to_node_id=data["to_node_id"],
            road_type=RoadType[data["road_type"]],
            ap_cost=data.get("ap_cost", 1),
            danger_rating=data.get("danger_rating", 0.1),
            theme_label=data.get("theme_label"),
            warp_instability=float(data.get("warp_instability", 0.0))
        )


class WorldMap:
    def __init__(self, theme: WorldTheme = WorldTheme.FANTASY):
        self.theme: WorldTheme = theme
        self.nodes: Dict[str, MapNode] = {}
        self.edges: List[MapEdge] = []
        self.adjacency: Dict[str, List[Tuple[str, MapEdge]]] = {}

    def get_node_label(self, node: MapNode) -> str:
        if node.theme_label:
            return node.theme_label
        theme_map = THEME_ALIASES.get(self.theme, THEME_ALIASES[WorldTheme.FANTASY])
        return theme_map.get(node.node_type, node.node_type.value)

    def get_edge_label(self, edge: MapEdge) -> str:
        if edge.theme_label:
            return edge.theme_label
        theme_map = THEME_ALIASES.get(self.theme, THEME_ALIASES[WorldTheme.FANTASY])
        return theme_map.get(edge.road_type, edge.road_type.value)

    def add_node(self, node: MapNode):
        self.nodes[node.node_id] = node
        if node.node_id not in self.adjacency:
            self.adjacency[node.node_id] = []

    def add_edge(
        self,
        from_id: str,
        to_id: str,
        road_type: RoadType = RoadType.TRAIL,
        ap_cost: Optional[int] = None,
        danger_rating: Optional[float] = None,
        bidirectional: bool = True,
        theme_label: Optional[str] = None,
        warp_instability: float = 0.0
    ):
        cost = ap_cost if ap_cost is not None else road_type.default_ap
        danger = danger_rating if danger_rating is not None else road_type.default_danger

        edge1 = MapEdge(from_id, to_id, road_type, cost, danger, theme_label=theme_label, warp_instability=warp_instability)
        self.edges.append(edge1)
        if from_id not in self.adjacency:
            self.adjacency[from_id] = []
        self.adjacency[from_id].append((to_id, edge1))

        if bidirectional:
            edge2 = MapEdge(to_id, from_id, road_type, cost, danger, theme_label=theme_label, warp_instability=warp_instability)
            self.edges.append(edge2)
            if to_id not in self.adjacency:
                self.adjacency[to_id] = []
            self.adjacency[to_id].append((from_id, edge2))

    def get_node(self, node_id: str) -> Optional[MapNode]:
        return self.nodes.get(node_id)

    def get_neighbors(self, node_id: str) -> List[Tuple[MapNode, MapEdge]]:
        result = []
        for neighbor_id, edge in self.adjacency.get(node_id, []):
            if neighbor_id in self.nodes:
                result.append((self.nodes[neighbor_id], edge))
        return result

    def get_edge(self, from_id: str, to_id: str) -> Optional[MapEdge]:
        for neighbor_id, edge in self.adjacency.get(from_id, []):
            if neighbor_id == to_id:
                return edge
        return None

    def find_path(self, from_id: str, to_id: str) -> Optional[List[str]]:
        """廣度優先搜尋 (BFS) 尋找最短路徑節點清單"""
        if from_id not in self.nodes or to_id not in self.nodes:
            return None
        if from_id == to_id:
            return [from_id]

        queue = deque([[from_id]])
        visited = {from_id}

        while queue:
            path = queue.popleft()
            curr = path[-1]

            for neighbor_id, _ in self.adjacency.get(curr, []):
                if neighbor_id == to_id:
                    return path + [neighbor_id]
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append(path + [neighbor_id])
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "theme": self.theme.name,
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorldMap':
        theme_name = data.get("theme", "FANTASY")
        theme = WorldTheme[theme_name] if theme_name in WorldTheme.__members__ else WorldTheme.FANTASY
        wmap = cls(theme=theme)
        for ndata in data.get("nodes", []):
            wmap.add_node(MapNode.from_dict(ndata))
        for edata in data.get("edges", []):
            edge = MapEdge.from_dict(edata)
            wmap.edges.append(edge)
            if edge.from_node_id not in wmap.adjacency:
                wmap.adjacency[edge.from_node_id] = []
            wmap.adjacency[edge.from_node_id].append((edge.to_node_id, edge))
        return wmap
