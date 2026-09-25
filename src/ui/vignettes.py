"""
Procedural ASCII Viewport Vignettes for 'Eye of the Beholder' First-Person Views.
Provides atmospheric rendering for locations, architectural landmarks, and character silhouettes.
"""

from typing import Dict, List, Optional


LOCATION_VIGNETTES: Dict[str, str] = {
    "city": """
       ▲             /\\            ▲
     /---\\         /====\\        /---\\
    |  🏛  |       | 🚢⚓ |      |  🛒 |
    |_____|       |______|      |_____|
   =======================================
   [自由城邦·奧斯提亞] - 繁華海港石造長街
""",
    "fortress": """
    |___|___|___|___|___|___|___|___|___|
    |   [ ⚔ 黑石要塞·戍衛城垛 ⚔ ]     |
    |      /\\                  /\\       |
    |     |  |   [ 隘口大門 ] |  |      |
   =======|  |================|  |=======
   重甲哨兵肅立於箭樓之上，旌旗在寒風中獵獵作響
""",
    "ruins": """
            /\\
           /  \\      [ ✧ 遠古失落神殿 ✧ ]
          / 👁 \\
         /======\\
        / | ⏳ | \\     石柱坍塌，古老石壁上
       /__|____|__\\    刻印著未知的因果銘文與幽光
   =======================================
""",
    "wasteland": """
           .      .           .
      .          .     [ 荒原寂滅風沙 ]
         ____        _______
       /      \\    /         \\   枯骨半掩於風蝕岩下
   ___/________\\__/___________\\___________
   天地蒼茫，遠方地平線泛著暗紅色的霞光
"""
}

CHARACTER_SILHOUETTES: Dict[str, str] = {
    "prof_artisan": """
         [ ⚒ 鐵匠 / 巧手工匠 ⚒ ]
              ( o_o )
             / | ▨ | \\   肌肉虯結，手握厚重鐵錘
            (  | ▨ |  )  皮質圍裙沾滿炭灰與火星
              /     \\
    """,
    "prof_guard": """
         [ 🛡 城防衛兵·披甲戍衛 🛡 ]
              [ -_- ]
             / | ⚔ | \\   身披精鋼板甲，手持雙手戟
            /  | 🛡 |  \\  神色冷峻，警惕審視四周
              /     \\
    """,
    "prof_merchant": """
         [ ⚖ 坐堂商賈·鋪面掌櫃 ⚖ ]
              ( $‿$ )
             / | 🪙 | \\   身著錦繡絲袍，指戴寶石戒指
            (  | 📜 |  )  笑容可掬，手算盤撥動如飛
              /     \\
    """,
    "prof_official": """
         [ 👑 市務長官 / 貴族參事 👑 ]
              ( ಠ_ಠ )
             / | 🏛 | \\   胸佩金葉徽章，手握羊皮政令
            |  | ⚖ |  |  目光威嚴，氣度沉穩高傲
              /     \\
    """,
    "prof_adventurer": """
         [ 🏹 荒野遊俠 / 邊境傭兵 🏹 ]
              ( •_• )
             / | 🗡 | \\   兜帽遮面，背負獵弓與行囊
            /  | 🎒 |  \\  靴履沾滿荒原泥塵，殺氣隱現
              /     \\
    """,
    "prof_scholar": """
         [ 📖 博雅學者 / 圖書導師 📖 ]
              ( ◓_◓ )
             / | 🔮 | \\   長袍廣袖，手捧古源魔法手稿
            |  | 📜 |  |  眸中閃爍著窺測真理的微光
              /     \\
    """
}


def render_viewport_ascii(
    location_type: str = "city",
    location_name: str = "奧斯提亞海灣城",
    facing_char_name: Optional[str] = None,
    facing_char_prof: Optional[str] = "prof_merchant",
    essence_lens_active: bool = False,
    char_traits: Optional[List[str]] = None,
    stress_ratio: float = 0.0,
    corruption_val: float = 0.0
) -> str:
    """
    動態生成第一人稱主視界畫面 (包含因果之眼透視資訊)
    """
    base_bg = LOCATION_VIGNETTES.get(location_type, LOCATION_VIGNETTES["city"])
    
    char_block = ""
    if facing_char_name:
        prof_key = facing_char_prof if facing_char_prof in CHARACTER_SILHOUETTES else "prof_merchant"
        silhouette = CHARACTER_SILHOUETTES.get(prof_key, CHARACTER_SILHOUETTES["prof_merchant"])
        char_block = f"\n你正注視著前方站在街角的：【{facing_char_name}】\n{silhouette}"

    if essence_lens_active and facing_char_name:
        trait_str = "、".join(char_traits) if char_traits else "無特殊本質"
        lens_overlay = f"""
┌─────────────────────────────────────────────────────────────┐
│ 🔮【因果之眼 (Essence Lens) 靈魂深層透視】                   │
│   - 目標真名: {facing_char_name}                              │
│   - 靈魂詞條本質: {trait_str}                                │
│   - 心神維持負荷: {stress_ratio*100:.1f}%                     │
│   - 靈魂腐化度:   {corruption_val:.1f} / 100.0                │
└─────────────────────────────────────────────────────────────┘"""
        return base_bg + char_block + lens_overlay

    return base_bg + char_block
