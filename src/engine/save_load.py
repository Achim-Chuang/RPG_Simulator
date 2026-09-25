"""
Unified JSON Save/Load System for WorldState.
"""

import json
import os
from typing import Tuple
from .world import WorldState


class SaveLoadManager:
    @staticmethod
    def save_to_file(world: WorldState, filepath: str, indent: int = 2) -> Tuple[bool, str]:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            data = world.to_dict()
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=indent)
            return True, f"存檔成功：已寫入至 {filepath}"
        except Exception as e:
            return False, f"存檔失敗：{str(e)}"

    @staticmethod
    def load_from_file(filepath: str) -> Tuple[bool, str, WorldState]:
        try:
            if not os.path.exists(filepath):
                return False, f"讀檔失敗：檔案 {filepath} 不存在！", None

            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            world = WorldState.from_dict(data)
            return True, f"讀檔成功：已自 {filepath} 還原世界狀態！", world
        except Exception as e:
            return False, f"讀檔失敗：{str(e)}", None
