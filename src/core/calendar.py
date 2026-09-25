"""
World Calendar, Three Daily Time Slots (10 AP each), and Rest conversion.
"""

from enum import Enum
from typing import List, Tuple, Dict, Any
from .character import Character


class TimeSlot(Enum):
    MORNING = "早晨"
    AFTERNOON = "午後"
    NIGHT = "夜間"

    def next_slot(self) -> Tuple['TimeSlot', bool]:
        """返回下一個時段以及是否跨日 (day_advanced)"""
        if self == TimeSlot.MORNING:
            return TimeSlot.AFTERNOON, False
        elif self == TimeSlot.AFTERNOON:
            return TimeSlot.NIGHT, False
        else:
            return TimeSlot.MORNING, True


class WorldCalendar:
    def __init__(self, current_day: int = 1, current_slot: TimeSlot = TimeSlot.MORNING):
        self.current_day = current_day
        self.current_slot = current_slot

    def advance_slot(self, characters: List[Character]) -> List[str]:
        """
        推進時段：
        1. 所有角色剩餘未用 AP 結算為休息放鬆 (rest_accumulated)
        2. AP 重設為固定 10 點
        3. 時段推進（若夜間結束則 day + 1）
        """
        logs = []
        for char in characters:
            unused = char.current_ap
            if unused > 0:
                char.rest_accumulated += unused
            char.current_ap = 10  # 重新獲得固定 10 AP

        next_slot, is_new_day = self.current_slot.next_slot()
        if is_new_day:
            self.current_day += 1
            logs.append(f"【新的一天】晨光破曉，進入第 {self.current_day} 天！")

        self.current_slot = next_slot
        logs.append(f"時段更替：當前為 第 {self.current_day} 天【{self.current_slot.value}】。全員重獲 10 AP！")
        return logs

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_day": self.current_day,
            "current_slot": self.current_slot.name
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorldCalendar':
        return cls(
            current_day=data.get("current_day", 1),
            current_slot=TimeSlot[data.get("current_slot", "MORNING")]
        )
