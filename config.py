import json
import os
import copy
from pathlib import Path


CONFIG_DIR = Path(os.environ.get('APPDATA', os.path.expanduser('~'))) / 'DesktopPetMonitor'
CONFIG_FILE = CONFIG_DIR / 'config.json'


DEFAULTS = {
    'pet_kind': 'haru',
    'pet_pos': None,
    'pet_opacity': 1.0,
    'pet_scale': 1.0,
    'panel_opacity': 0.93,
    'animate_fps': 25,
    'panel_refresh_ms': 1000,
    'ip_refresh_sec': 300,
    'enable_ip_proxy_check': True,
    'edge_snap': True,
    'edge_snap_dist': 18,
    'follow_mouse': False,
    'pomodoro_work_min': 25,
    'pomodoro_break_min': 5,
    'sit_reminder_min': 45,
    'alert_cpu_percent': 90,
    'alert_mem_percent': 92,
    'alert_enable': True,
    'random_behavior_sec': 8,
    'show_particles': True,
    'stats': {
        'interactions': 0,
        'runtime_sec': 0,
        'pomodoros_completed': 0,
        'last_run': None,
    },
    'quick_launch': [],

    'llm_enabled': False,
    'llm_api_key': '',
    'llm_base_url': 'https://api.openai.com/v1',
    'llm_model': 'gpt-4o-mini',
    'llm_max_tokens': 300,
    'llm_system_prompt': '你是 doro,一只来自《胜利女神:NIKKE》的超萌粉色小精灵,陪伴主人使用电脑。语气活泼、短句、偶尔加 "doro~" 拟声。每次回答不超过 40 个字。',
    'llm_history_limit': 8,

    'wander_enable': True,
    'wander_chance': 0.35,
    'wander_speed_px': 2,
    'wander_min_dist': 120,
    'wander_max_dist': 420,

    'pet_scale_factor': 0.4,

    # i18n
    'language': 'zh',

    # IP alert — pet yells if detected IP doesn't match any expected value.
    # Values can be exact IPs ("203.0.113.42") or prefixes ("203.0.113.").
    # A match on EITHER direct or proxy IP against EITHER expected slot is OK.
    'ip_alert_enable': False,
    'ip_alert_expected_1': '',
    'ip_alert_expected_2': '',
}


class Config:
    def __init__(self):
        self._data = copy.deepcopy(DEFAULTS)
        self.load()

    def load(self):
        if not CONFIG_FILE.exists():
            return
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
        except Exception:
            return
        for k, default_v in DEFAULTS.items():
            v = loaded.get(k, default_v)
            if isinstance(default_v, dict) and isinstance(v, dict):
                merged = copy.deepcopy(default_v)
                merged.update(v)
                self._data[k] = merged
            else:
                self._data[k] = v

    def save(self):
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def get(self, key, default=None):
        return self._data.get(key, default if default is not None else DEFAULTS.get(key))

    def set(self, key, value):
        self._data[key] = value
        self.save()

    def update(self, mapping):
        self._data.update(mapping)
        self.save()

    def bump_stat(self, key, delta=1):
        stats = self._data.setdefault('stats', {})
        stats[key] = stats.get(key, 0) + delta
        self.save()

    def all(self):
        return copy.deepcopy(self._data)


_singleton = None


def get_config():
    global _singleton
    if _singleton is None:
        _singleton = Config()
    return _singleton
