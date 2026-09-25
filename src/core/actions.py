"""
Action Suites (Composite Actions), Action Check Engine (50% +/- 5%), and Utility AI.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any, Callable
import random
from .character import Character


@dataclass
class SubAction:
    name: str
    ap_cost: int

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "ap_cost": self.ap_cost}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SubAction':
        return cls(name=data["name"], ap_cost=data["ap_cost"])


class ActionSuite:
    def __init__(
        self,
        suite_id: str,
        name: str,
        category: str,
        steps: List[SubAction],
        current_step_idx: int = 0,
        is_completed: bool = False,
        repeatable: bool = True,
        on_complete: Optional[Callable[[Character], None]] = None
    ):
        self.suite_id = suite_id
        self.name = name
        self.category = category
        self.steps = steps
        self.current_step_idx = current_step_idx
        self.is_completed = is_completed
        self.repeatable = repeatable
        self.on_complete = on_complete

    @property
    def total_ap_cost(self) -> int:
        return sum(s.ap_cost for s in self.steps)

    @property
    def current_step(self) -> Optional[SubAction]:
        if self.current_step_idx < len(self.steps):
            return self.steps[self.current_step_idx]
        return None

    def advance(self, character: Character) -> Tuple[bool, str]:
        step = self.current_step
        if not step:
            return False, "無剩餘步驟"

        if character.current_ap < step.ap_cost:
            return False, f"AP不足（需 {step.ap_cost}，剩餘 {character.current_ap}）"

        character.current_ap -= step.ap_cost
        self.current_step_idx += 1
        log_msg = f"{character.name} 消耗 {step.ap_cost} AP 執行「{self.name}」步驟 [{self.current_step_idx}/{len(self.steps)}]: 【{step.name}】 (剩餘AP: {character.current_ap})"

        if self.current_step_idx >= len(self.steps):
            self.is_completed = True
            log_msg += f"\n  ★ 「{self.name}」全部步驟達成！進行最終結算！"
            if self.on_complete:
                self.on_complete(character)
            if self.repeatable:
                self.current_step_idx = 0
                self.is_completed = False

        return True, log_msg

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suite_id": self.suite_id,
            "name": self.name,
            "category": self.category,
            "steps": [s.to_dict() for s in self.steps],
            "current_step_idx": self.current_step_idx,
            "is_completed": self.is_completed,
            "repeatable": self.repeatable
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], on_complete: Optional[Callable[[Character], None]] = None) -> 'ActionSuite':
        steps = [SubAction.from_dict(s) for s in data["steps"]]
        return cls(
            suite_id=data["suite_id"],
            name=data["name"],
            category=data["category"],
            steps=steps,
            current_step_idx=data.get("current_step_idx", 0),
            is_completed=data.get("is_completed", False),
            repeatable=data.get("repeatable", True),
            on_complete=on_complete
        )


class ActionCheckEngine:
    @staticmethod
    def execute_action(
        action_name: str,
        is_challenging: bool = False,
        modifiers: Optional[Dict[str, int]] = None,
        seed: Optional[int] = None
    ) -> Tuple[bool, str]:
        if not is_challenging:
            return True, f"【常規行動·自動成功】「{action_name}」無需投骰，穩步達成。"

        if seed is not None:
            random.seed(seed)

        base_rate = 0.50
        mod_sum = 0
        details = []

        if modifiers:
            for reason, val in modifiers.items():
                mod_sum += val
                pct = val * 5
                sign = "+" if pct >= 0 else ""
                details.append(f"{reason} ({sign}{pct}%)")

        final_rate = max(0.05, min(0.95, base_rate + (mod_sum * 0.05)))
        roll = random.random()
        success = roll <= final_rate

        detail_str = "、".join(details) if details else "無額外修正"
        log = (
            f"【挑戰行動檢定】「{action_name}」\n"
            f"  - 基準成功率: 50%\n"
            f"  - 因果修正項: {detail_str} (淨修正: {mod_sum * 5:+d}%)\n"
            f"  - 最終判定機率: {final_rate * 100:.1f}%\n"
            f"  - 投骰結果: {roll * 100:.1f}% -> {'【★ 檢定成功】' if success else '【✗ 檢定失敗】'}"
        )
        return success, log


class UtilityAI:
    @staticmethod
    def evaluate_priority(character: Character, suite: ActionSuite, in_progress_suite: Optional[ActionSuite] = None) -> float:
        score = 50.0
        if in_progress_suite == suite:
            score += 40.0

        trait_names = [t.name for t in character.innate_traits + character.acquired_traits + character.imprinted_traits]

        if suite.category == "business":
            if "勤勉" in trait_names:
                score += 50.0
            if "貪婪" in trait_names:
                score += 35.0
            if "極度懶散" in trait_names:
                score -= 60.0

        elif suite.category == "security":
            if "忠厚本分" in trait_names:
                score += 60.0
            if "野心家" in trait_names:
                score -= 30.0

        elif suite.category == "conspiracy":
            if "忠厚本分" in trait_names:
                return -999.0
            if "野心家" in trait_names:
                score += 80.0
            if "暗中欠債" in trait_names:
                score += 40.0

        return score
