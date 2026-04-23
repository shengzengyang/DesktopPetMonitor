"""Simple dict-based i18n. All UI strings go through `t('key')`.

Add new languages by appending to _CATALOG with the same keys. Missing keys
fall back to the Chinese catalog, then to the key itself, so partial
translations still render something sensible.
"""
from logger import log


DEFAULT_LANG = 'zh'
_current_lang = DEFAULT_LANG


_CATALOG = {
    'zh': {
        # ---- top-level ----
        'app.title': '桌面监视器',
        'app.language_changed_restart': '语言已切换,重启 doro 后界面完全生效',

        # ---- tray / menu ----
        'tray.show_pet': '显示/隐藏桌宠',
        'tray.show_panel': '显示/隐藏面板',
        'tray.switch_pet': '切换模型',
        'tray.settings': '设置...',
        'tray.quit': '退出',

        # ---- pet context menu ----
        'menu.chat': '💬 对 doro 说...  (Ctrl+Space)',
        'menu.panel': '📊 显示/隐藏面板',
        'menu.expressions': '😀 表情',
        'menu.motions': '🎬 动作',
        'menu.sizes': '📐 大小',
        'menu.switch_pet': '🧸 切换模型',
        'menu.settings': '⚙ 设置...',
        'menu.quit': '❌ 退出',
        'menu.motion_random': '🎲 随机动作',
        'menu.motion_idle': '🧘 待机',
        'menu.wander': '🚶 出去溜达',
        'menu.stop_wander': '回来',
        'menu.size_xs': '超小 50%',
        'menu.size_s': '小 75%',
        'menu.size_m': '默认 100%',
        'menu.size_l': '大 125%',
        'menu.size_xl': '超大 150%',
        'menu.size_shrink': '缩小 (滚轮下)',
        'menu.size_grow': '放大 (滚轮上)',
        'menu.no_expression': '(该模型无表情)',

        # ---- info panel ----
        'panel.title': '桌面监视器',
        'panel.direct_ip': '真实 IP:',
        'panel.proxy_ip': '代理 IP:',
        'panel.network': '网速:',
        'panel.cpu': 'CPU',
        'panel.memory': '内存',
        'panel.gpu': 'GPU',
        'panel.vram': '显存',
        'panel.pomodoro_btn_start': '▶ 番茄钟',
        'panel.pomodoro_btn_stop': '■ 停止',
        'panel.chat_btn': '💬 对话',
        'panel.refresh_ip_btn': '刷新 IP',
        'panel.tip': '单击 · 双击 · 拖动 · 右键菜单 · Ctrl+Space 对话',
        'panel.pomo_work': '专注',
        'panel.pomo_break': '休息',
        'panel.no_gpu': '无 NVIDIA GPU',

        # ---- chat input ----
        'chat.hint': '💬 对 doro 说点什么(回车发送,Esc 取消)',
        'chat.placeholder': '例如:doro,今天天气怎么样?',
        'chat.send': '发送',
        'chat.thinking': '让我想想~',
        'chat.not_configured': 'doro 还没配置 GPT,正在打开设置...',
        'chat.llm_fail_prefix': 'doro 没听懂:',

        # ---- settings dialog ----
        'settings.title': '桌宠设置',
        'settings.cancel': '取消',
        'settings.ok': '保存并应用',
        'settings.tab_general': '通用',
        'settings.tab_behavior': '行为',
        'settings.tab_llm': '对话 (GPT)',
        'settings.tab_monitor': '监控',
        'settings.tab_stats': '统计',
        'settings.pet_model': 'Live2D 模型:',
        'settings.pet_not_installed': '  (未安装)',
        'settings.opacity': '桌宠透明度:',
        'settings.scale': '桌宠大小:',
        'settings.panel_opacity': '面板不透明:',
        'settings.animate_fps': '动画帧率:',
        'settings.show_particles': '显示粒子特效',
        'settings.autostart': '开机自启动(登录时自动打开 doro)',
        'settings.language': '语言 / Language:',
        'settings.edge_snap': '拖动后吸附屏幕边缘',
        'settings.follow_mouse': '空闲时跟随鼠标',
        'settings.wander_enable': '允许闲逛(在桌面随机走动)',
        'settings.wander_speed': '闲逛速度:',
        'settings.wander_chance': '随机闲逛概率:',
        'settings.random_interval': '随机行为间隔:',
        'settings.pomo_work': '番茄钟 · 专注:',
        'settings.pomo_break': '番茄钟 · 休息:',
        'settings.sit_reminder': '久坐提醒:',
        'settings.llm_enable': '启用 GPT 对话 (Ctrl+Space 唤出输入框)',
        'settings.llm_api_key': 'API Key:',
        'settings.llm_base_url': 'Base URL:',
        'settings.llm_model': '模型:',
        'settings.llm_max_tokens': '最大回复 token:',
        'settings.llm_history': '对话历史保留轮次:',
        'settings.llm_system_prompt': '人设 prompt:',
        'settings.ip_refresh': 'IP 刷新间隔:',
        'settings.panel_refresh': '面板刷新周期:',
        'settings.alert_enable': '启用性能警报(让桌宠提醒)',
        'settings.cpu_alert': 'CPU 警报阈值:',
        'settings.mem_alert': '内存警报阈值:',
        'settings.ip_alert_enable': '启用 IP 检测告警(不匹配时提醒)',
        'settings.ip_alert_expected_1': '期望 IP 1:',
        'settings.ip_alert_expected_2': '期望 IP 2:',
        'settings.ip_alert_hint': '提示:两个框任一匹配即视为正常。可填 IP 前缀(如 "203.0.113.") 做段匹配',
        'settings.stats_interactions': '🐾 累计互动次数',
        'settings.stats_pomodoros': '🍅 完成番茄钟',
        'settings.stats_runtime': '⏱ 历史运行',
        'settings.stats_last_run': '📅 上次启动',
        'settings.stats_first_run': '首次运行',
        'settings.suffix_seconds': ' 秒',
        'settings.suffix_minutes': ' 分钟',
        'settings.suffix_minutes_zero_off': ' 分钟 (0=关闭)',
        'settings.suffix_ms': ' ms',
        'settings.suffix_pct': ' %',
        'settings.suffix_px_per_frame': ' px/帧',

        # ---- speech bubble / notices ----
        'notice.ip_alert': '⚠️ IP 不对!请注意,不要打开 Claude({got})',
        'notice.ip_cleared': '✅ IP 恢复正常',

        # ---- pet short sayings shown directly to the user ----
        'pet.i_am': '我是 {name}!',
        'pet.not_ready': '{name} 模型还没准备好~',
        'pet.wander_out': '出去溜达~',
        'pet.size_set': '大小:{pct}%',
    },
    'en': {
        'app.title': 'Desktop Monitor',
        'app.language_changed_restart': 'Language switched. Restart doro for full effect.',

        'tray.show_pet': 'Show / Hide Pet',
        'tray.show_panel': 'Show / Hide Panel',
        'tray.switch_pet': 'Switch Model',
        'tray.settings': 'Settings...',
        'tray.quit': 'Quit',

        'menu.chat': '💬 Talk to doro...  (Ctrl+Space)',
        'menu.panel': '📊 Toggle panel',
        'menu.expressions': '😀 Expression',
        'menu.motions': '🎬 Motion',
        'menu.sizes': '📐 Size',
        'menu.switch_pet': '🧸 Switch model',
        'menu.settings': '⚙ Settings...',
        'menu.quit': '❌ Quit',
        'menu.motion_random': '🎲 Random motion',
        'menu.motion_idle': '🧘 Idle',
        'menu.wander': '🚶 Wander around',
        'menu.stop_wander': 'Come back',
        'menu.size_xs': 'XS 50%',
        'menu.size_s': 'S 75%',
        'menu.size_m': 'Default 100%',
        'menu.size_l': 'L 125%',
        'menu.size_xl': 'XL 150%',
        'menu.size_shrink': 'Shrink (wheel down)',
        'menu.size_grow': 'Grow (wheel up)',
        'menu.no_expression': '(No expressions on this model)',

        'panel.title': 'Desktop Monitor',
        'panel.direct_ip': 'Real IP:',
        'panel.proxy_ip': 'Proxy IP:',
        'panel.network': 'Network:',
        'panel.cpu': 'CPU',
        'panel.memory': 'Memory',
        'panel.gpu': 'GPU',
        'panel.vram': 'VRAM',
        'panel.pomodoro_btn_start': '▶ Pomodoro',
        'panel.pomodoro_btn_stop': '■ Stop',
        'panel.chat_btn': '💬 Chat',
        'panel.refresh_ip_btn': 'Refresh IP',
        'panel.tip': 'Click · Double-click · Drag · Right-click · Ctrl+Space',
        'panel.pomo_work': 'Focus',
        'panel.pomo_break': 'Break',
        'panel.no_gpu': 'No NVIDIA GPU',

        'chat.hint': '💬 Say something to doro (Enter to send, Esc to cancel)',
        'chat.placeholder': 'e.g. doro, how is the weather today?',
        'chat.send': 'Send',
        'chat.thinking': 'Let me think~',
        'chat.not_configured': 'GPT is not configured. Opening settings...',
        'chat.llm_fail_prefix': 'doro didn\'t catch that:',

        'settings.title': 'Pet Settings',
        'settings.cancel': 'Cancel',
        'settings.ok': 'Save & Apply',
        'settings.tab_general': 'General',
        'settings.tab_behavior': 'Behavior',
        'settings.tab_llm': 'Chat (GPT)',
        'settings.tab_monitor': 'Monitor',
        'settings.tab_stats': 'Stats',
        'settings.pet_model': 'Live2D Model:',
        'settings.pet_not_installed': '  (not installed)',
        'settings.opacity': 'Pet Opacity:',
        'settings.scale': 'Pet Size:',
        'settings.panel_opacity': 'Panel Opacity:',
        'settings.animate_fps': 'Animation FPS:',
        'settings.show_particles': 'Show particle effects',
        'settings.autostart': 'Start on Windows login (launch doro at boot)',
        'settings.language': 'Language / 语言:',
        'settings.edge_snap': 'Snap to screen edge after drag',
        'settings.follow_mouse': 'Follow mouse when idle',
        'settings.wander_enable': 'Allow wandering (roam the desktop)',
        'settings.wander_speed': 'Wander Speed:',
        'settings.wander_chance': 'Wander Chance:',
        'settings.random_interval': 'Random Behavior Interval:',
        'settings.pomo_work': 'Pomodoro · Focus:',
        'settings.pomo_break': 'Pomodoro · Break:',
        'settings.sit_reminder': 'Sit Reminder:',
        'settings.llm_enable': 'Enable GPT chat (Ctrl+Space opens input)',
        'settings.llm_api_key': 'API Key:',
        'settings.llm_base_url': 'Base URL:',
        'settings.llm_model': 'Model:',
        'settings.llm_max_tokens': 'Max reply tokens:',
        'settings.llm_history': 'History turns kept:',
        'settings.llm_system_prompt': 'System prompt:',
        'settings.ip_refresh': 'IP Refresh Interval:',
        'settings.panel_refresh': 'Panel Refresh Period:',
        'settings.alert_enable': 'Enable performance alert (pet notifies)',
        'settings.cpu_alert': 'CPU alert threshold:',
        'settings.mem_alert': 'Memory alert threshold:',
        'settings.ip_alert_enable': 'Enable IP check alert (notify on mismatch)',
        'settings.ip_alert_expected_1': 'Expected IP 1:',
        'settings.ip_alert_expected_2': 'Expected IP 2:',
        'settings.ip_alert_hint': 'Tip: either field matching is OK. Prefix match works too (e.g. "203.0.113.")',
        'settings.stats_interactions': '🐾 Total interactions',
        'settings.stats_pomodoros': '🍅 Pomodoros done',
        'settings.stats_runtime': '⏱ Total runtime',
        'settings.stats_last_run': '📅 Last run',
        'settings.stats_first_run': 'First run',
        'settings.suffix_seconds': ' sec',
        'settings.suffix_minutes': ' min',
        'settings.suffix_minutes_zero_off': ' min (0=off)',
        'settings.suffix_ms': ' ms',
        'settings.suffix_pct': ' %',
        'settings.suffix_px_per_frame': ' px/frame',

        'notice.ip_alert': '⚠️ IP mismatch! Do NOT open Claude ({got})',
        'notice.ip_cleared': '✅ IP back to expected',

        'pet.i_am': "I'm {name}!",
        'pet.not_ready': '{name} model not ready yet~',
        'pet.wander_out': 'Going for a walk~',
        'pet.size_set': 'Size: {pct}%',
    },
}


def set_language(lang):
    global _current_lang
    if lang in _CATALOG:
        _current_lang = lang
        log.info('i18n: language set to %s', lang)
    else:
        log.warning('i18n: unknown language %r, falling back to %s', lang, DEFAULT_LANG)
        _current_lang = DEFAULT_LANG


def current_language():
    return _current_lang


def available_languages():
    """Returns list of (code, display_name) tuples."""
    return [('zh', '中文 (简体)'), ('en', 'English')]


def t(key, **kwargs):
    catalog = _CATALOG.get(_current_lang, _CATALOG[DEFAULT_LANG])
    s = catalog.get(key)
    if s is None:
        s = _CATALOG[DEFAULT_LANG].get(key, key)
    if kwargs:
        try:
            return s.format(**kwargs)
        except Exception:
            return s
    return s
