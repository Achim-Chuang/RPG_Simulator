"""
Pairwise Social Network (Directed Dyadic Graph) with Affection, Respect, and Obligation.
"""

from dataclasses import dataclass
from typing import Dict, Tuple, Any, List


@dataclass
class Relationship:
    from_id: str
    to_id: str
    affection: float = 0.0   # -100.0 ~ +100.0
    respect: float = 0.0     # -100.0 ~ +100.0
    obligation: float = 0.0  # -100.0 ~ +100.0

    @property
    def willingness(self) -> float:
        """
        Willingness to cooperate/obey:
        Willingness = 0.5 * Affection + 0.3 * Respect + 0.2 * Obligation
        """
        return 0.5 * self.affection + 0.3 * self.respect + 0.2 * self.obligation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_id": self.from_id,
            "to_id": self.to_id,
            "affection": self.affection,
            "respect": self.respect,
            "obligation": self.obligation
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Relationship':
        return cls(
            from_id=data["from_id"],
            to_id=data["to_id"],
            affection=data.get("affection", 0.0),
            respect=data.get("respect", 0.0),
            obligation=data.get("obligation", 0.0)
        )


class SocialNetwork:
    def __init__(self):
        self.matrix: Dict[Tuple[str, str], Relationship] = {}

    def get_relationship(self, from_id: str, to_id: str) -> Relationship:
        pair = (from_id, to_id)
        if pair not in self.matrix:
            self.matrix[pair] = Relationship(from_id=from_id, to_id=to_id)
        return self.matrix[pair]

    def modify(
        self,
        from_id: str,
        to_id: str,
        d_aff: float = 0.0,
        d_resp: float = 0.0,
        d_ob: float = 0.0
    ):
        rel = self.get_relationship(from_id, to_id)
        rel.affection = max(-100.0, min(100.0, rel.affection + d_aff))
        rel.respect = max(-100.0, min(100.0, rel.respect + d_resp))
        rel.obligation = max(-100.0, min(100.0, rel.obligation + d_ob))

    def to_dict(self) -> List[Dict[str, Any]]:
        return [rel.to_dict() for rel in self.matrix.values()]

    @classmethod
    def from_dict(cls, data: List[Dict[str, Any]]) -> 'SocialNetwork':
        net = cls()
        for item in data:
            rel = Relationship.from_dict(item)
            net.matrix[(rel.from_id, rel.to_id)] = rel
        return net
