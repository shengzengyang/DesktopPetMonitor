import os
from pathlib import Path


_ROOT = Path(__file__).resolve().parent


PETS = {
    'haru': {
        'name': 'Haru (Live2D 示例)',
        'model_rel': 'assets/haru/Haru.model3.json',
        'size': (220, 340),
        'hit_head_motion': ('TapBody', 0),
        'hit_body_motion': ('TapBody', 1),
        'idle_group': 'Idle',
        'expressions': {
            'happy': 'F01',
            'smile': 'F02',
            'wink': 'F03',
            'blush': 'F04',
            'sad': 'F05',
            'cry': 'F06',
            'alert': 'F07',
            'angry': 'F08',
        },
        'tap_motions': ('TapBody', 4),
        'named_motions': [],
        'chats': {
            'idle': ["今天也辛苦啦~", "主人在忙什么呢?", "陪着你哦!", "要不要休息一下?"],
            'happy': ["好耶!", "嘿嘿~", "主人最好了~"],
            'love': ["喜欢你~♥", "主人~!"],
            'wake': ["唔...叫我吗?", "再睡一会~"],
            'drag': ["哇~", "小心点啦!", "(>﹏<)"],
            'alert': ["主人!CPU 太高啦!", "内存快满了!", "电脑要扛不住了~"],
            'pomodoro_start': ["专注时间,一起加油!", "我们开始吧!"],
            'pomodoro_break': ["休息一下~", "伸个懒腰!"],
            'sit': ["久坐啦,起来动动吧~", "记得喝水哦~"],
        },
    },
    'dororong': {
        'name': 'doro (Dororong)',
        'model_rel': 'assets/dororong/Doro/Doro.model3.json',
        'size': (200, 260),
        'hit_head_motion': ('Nod', 0),
        'hit_body_motion': ('Surprised', 0),
        'idle_group': 'Idle',
        # Semantic hooks used by code (alert, etc.) — kept minimal after the
        # state system was removed. No feed/pet/rest anymore.
        'expressions': {
            'happy':  'Exp8',       # star eyes — super excited
            'alert':  'Exp3',       # antenna alert (CPU/mem warning)
            'tongue': 'TongueOut',
        },
        # Menu entries for right-click 表情 submenu; labels describe the real visual.
        'named_expressions': [
            ('nervous',      '😅 紧张冒汗',   'Exp1'),
            ('loading',      '💭 加载中',     'Exp2'),
            ('alert',        '❗ 警觉天线',   'Exp3'),
            ('question',     '❓ 疑惑问号',   'Exp4'),
            ('sunglasses',   '🕶️ 酷墨镜',     'Exp5'),
            ('eating',       '🍪 叼饼干',     'Exp6'),
            ('confused',     '🤔 思考混乱',   'Exp7'),
            ('star_eyes',    '✨ 星星眼',     'Exp8'),
            ('tongue',       '😛 吐舌头',     'TongueOut'),
            ('no_highlight', '🌑 眼无高光',   'HighlightOff'),
            ('__reset__',    '🔄 恢复默认',   ''),
        ],
        'tap_motions': ('Nod', 1),
        'named_motions': [
            ('nod',       '✅ 点头',     'Nod',       0),
            ('shake',     '❌ 摇头',     'Shake',     0),
            ('dance',     '💃 跳舞',     'Dance',     0),
            ('surprised', '😲 惊讶',     'Surprised', 0),
            ('run',       '🏃 跑步',     'Run',       0),
            ('standup',   '🙆 伸懒腰',   'Standup',   0),
            ('struggle',  '😵 挣扎',     'Struggle',  0),
        ],
        'chats': {
            'idle': ["doro~", "哒哒哒~", "doro doro~", "(◡ ‿ ◡)"],
            'happy': ["doro!", "耶~", "doro嘿嘿"],
            'love': ["doro♥", "爱你~"],
            'wake': ["doro...?", "doro zzz~"],
            'drag': ["doro~?!", "(ˊ•͈ ◡ •͈ˋ)!"],
            'alert': ["doro!!!", "doro 警告!"],
            'pomodoro_start': ["doro 专心!", "一起 doro!"],
            'pomodoro_break': ["doro 休息~", "biubiu~"],
            'sit': ["doro 动动~", "起来 doro 一下!"],
        },
    },
}


DEFAULT_KIND = 'haru'


def get(kind):
    return PETS.get(kind, PETS[DEFAULT_KIND])


def list_kinds():
    return [(k, v['name']) for k, v in PETS.items()]


def resolve_model_path(kind):
    pet = get(kind)
    path = _ROOT / pet['model_rel']
    return str(path) if path.exists() else None


def available_kinds():
    kinds = []
    for k, v in PETS.items():
        p = _ROOT / v['model_rel']
        kinds.append((k, v['name'], p.exists()))
    return kinds
