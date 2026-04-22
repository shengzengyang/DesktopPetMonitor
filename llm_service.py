import json
import time
import traceback
import requests

from PyQt5.QtCore import QObject, QThread, pyqtSignal

from logger import log


def _is_responses_api_model(model_name):
    """Models that REQUIRE /v1/responses (OpenAI's reasoning-models endpoint).
    Everything else (Claude, gpt-4o, gpt-3.5, etc.) goes to /v1/chat/completions.
    """
    m = (model_name or '').lower().strip()
    return (m.startswith('gpt-5') or m.startswith('o1') or m.startswith('o3')
            or m.startswith('o4'))


def _extract_reply_text(data):
    """Return a string reply from a chat-completions response body, tolerating
    the various shapes returned by proxies and reasoning models.
    """
    try:
        choices = data.get('choices') if isinstance(data, dict) else None
        if choices:
            first = choices[0] or {}
            msg = first.get('message') or {}
            for k in ('content', 'reasoning_content'):
                v = msg.get(k)
                if isinstance(v, str) and v.strip():
                    return v.strip()
            v = first.get('text')
            if isinstance(v, str) and v.strip():
                return v.strip()
            delta = first.get('delta') or {}
            v = delta.get('content')
            if isinstance(v, str) and v.strip():
                return v.strip()
        if isinstance(data, dict):
            for k in ('content', 'text', 'output', 'response'):
                v = data.get(k)
                if isinstance(v, str) and v.strip():
                    return v.strip()
    except Exception:
        log.exception('extract_reply_text parser error')
    return None


def _parse_sse_stream(raw_text):
    """Parse a Server-Sent Events response body from chat-completions streaming.
    Concatenates every `delta.content` chunk across events into one string.
    Returns None if nothing usable was found.
    """
    if not raw_text:
        return None
    parts = []
    for line in raw_text.splitlines():
        line = line.strip()
        if not line.startswith('data:'):
            continue
        payload = line[5:].strip()
        if not payload or payload == '[DONE]':
            continue
        try:
            chunk = json.loads(payload)
        except Exception:
            continue
        try:
            choices = chunk.get('choices') or []
            if not choices:
                continue
            delta = choices[0].get('delta') or {}
            c = delta.get('content')
            if isinstance(c, str):
                parts.append(c)
                continue
            # Some reasoning proxies put it in reasoning_content:
            c = delta.get('reasoning_content')
            if isinstance(c, str):
                parts.append(c)
                continue
            # Or the whole message was sent in one chunk:
            msg = choices[0].get('message') or {}
            c = msg.get('content')
            if isinstance(c, str):
                parts.append(c)
        except Exception:
            continue
    if not parts:
        return None
    return ''.join(parts).strip() or None


class LLMWorker(QThread):
    replied = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, cfg, messages, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.messages = messages

    def run(self):
        model = self.cfg.get('llm_model')
        try:
            if _is_responses_api_model(model):
                self._run_responses(model)
            else:
                self._run_chat_completions(model)
        except Exception:
            log.exception('LLM worker crashed')
            self.failed.emit("LLM 内部错误,看 doro.log")

    # ------------------------------------------------------------------
    # OpenAI Responses API (/v1/responses) — reasoning models only
    # ------------------------------------------------------------------
    def _run_responses(self, model):
        t0 = time.monotonic()
        url = None
        try:
            url = self.cfg.get('llm_base_url').rstrip('/') + '/responses'
            headers = {
                'Authorization': f"Bearer {self.cfg.get('llm_api_key')}",
                'Content-Type': 'application/json',
            }
            # Convert chat messages → Responses API shape:
            # - pull the system prompt out into `instructions`
            # - pass the remainder as `input` array (same role/content keys).
            system_instructions = ''
            input_msgs = []
            for m in self.messages:
                role = m.get('role')
                content = m.get('content') or ''
                if role == 'system' and not system_instructions:
                    system_instructions = content
                else:
                    input_msgs.append({'role': role, 'content': content})
            body = {
                'model': model,
                'input': input_msgs,
                'max_output_tokens': int(self.cfg.get('llm_max_tokens')),
                'stream': True,  # stream is how this proxy delivers text reliably
            }
            if system_instructions:
                body['instructions'] = system_instructions
            log.info('LLM request → %s  model=%s  msgs=%d  max_tok=%d  stream=True',
                     url, model, len(input_msgs), body['max_output_tokens'])
            r = requests.post(url, headers=headers, json=body, timeout=60, stream=True)
            # SSE responses often don't set charset; requests defaults to Latin-1
            # which garbles UTF-8 multibyte (Chinese, emoji). Force UTF-8.
            r.encoding = 'utf-8'
            dt_ms = int((time.monotonic() - t0) * 1000)
            ctype = r.headers.get('Content-Type', '')
            log.info('LLM response: status=%d  %dms  ctype=%s',
                     r.status_code, dt_ms, ctype)
            if r.status_code != 200:
                body_text = r.text
                log.warning('LLM non-200 body (first 500): %s', body_text[:500])
                self.failed.emit(f"HTTP {r.status_code}: {body_text[:120]}")
                return

            # Iterate the SSE stream line by line. Responses API emits events
            # like `event: response.output_text.delta` with `data: {...}`.
            text_parts = []
            event_counts = {}
            full_text_from_done = None
            try:
                for raw_line in r.iter_lines(decode_unicode=True, chunk_size=1):
                    if raw_line is None:
                        continue
                    line = raw_line.strip()
                    if not line or line.startswith(':'):
                        continue  # heartbeat / comment
                    if line.startswith('event:'):
                        ev = line.split(':', 1)[1].strip()
                        event_counts[ev] = event_counts.get(ev, 0) + 1
                        continue
                    if not line.startswith('data:'):
                        continue
                    payload = line[5:].strip()
                    if not payload or payload == '[DONE]':
                        continue
                    try:
                        chunk = json.loads(payload)
                    except Exception:
                        continue
                    # Responses API: stream events include a `delta` string
                    # on output_text.delta events, plus a final
                    # response.completed event carrying the full response.
                    delta = chunk.get('delta')
                    if isinstance(delta, str):
                        text_parts.append(delta)
                        continue
                    # Final "response.completed" event carries the full
                    # Responses object under `response`.
                    resp_obj = chunk.get('response') or chunk
                    out_text = resp_obj.get('output_text') if isinstance(resp_obj, dict) else None
                    if isinstance(out_text, str) and out_text.strip():
                        full_text_from_done = out_text
                        continue
                    # Also handle chat/completions-style SSE payloads in case
                    # the proxy mixes formats.
                    for c in (chunk.get('choices') or []):
                        d = (c.get('delta') or {})
                        v = d.get('content')
                        if isinstance(v, str):
                            text_parts.append(v)
            except Exception:
                log.exception('SSE iter_lines failed')

            log.info('LLM stream events: %s', event_counts)
            text = full_text_from_done or (''.join(text_parts).strip() or None)
            if not text:
                log.error('LLM stream produced no text.  parts=%d  full_from_done=%s',
                          len(text_parts), bool(full_text_from_done))
                self.failed.emit("模型返回空内容,看 doro.log 了解详细响应")
                return
            log.info('LLM reply text_len=%d preview=%r', len(text), text[:80])
            self.replied.emit(text)
        except requests.exceptions.Timeout:
            log.warning('LLM timeout after %dms  url=%s', int((time.monotonic()-t0)*1000), url)
            self.failed.emit("请求超时 (60s)")
        except requests.exceptions.ConnectionError as e:
            log.error('LLM connection error: %s  url=%s', e, url)
            self.failed.emit(f"连接失败: {str(e)[:120]}")

    # ------------------------------------------------------------------
    # Chat Completions API (/v1/chat/completions) — standard OpenAI + Claude
    # + any OpenAI-compatible proxy. Uses streaming since it's universally
    # supported and dodges "null content on non-stream" proxy bugs.
    # ------------------------------------------------------------------
    def _run_chat_completions(self, model):
        t0 = time.monotonic()
        url = None
        try:
            url = self.cfg.get('llm_base_url').rstrip('/') + '/chat/completions'
            headers = {
                'Authorization': f"Bearer {self.cfg.get('llm_api_key')}",
                'Content-Type': 'application/json',
            }
            body = {
                'model': model,
                'messages': self.messages,
                'max_tokens': int(self.cfg.get('llm_max_tokens')),
                'temperature': 0.8,
                'stream': True,
            }
            log.info('LLM request → %s  model=%s  msgs=%d  max_tok=%d  stream=True',
                     url, model, len(self.messages), body['max_tokens'])
            r = requests.post(url, headers=headers, json=body, timeout=60, stream=True)
            # Force UTF-8: SSE content-type often omits charset and requests
            # falls back to Latin-1, which mangles Chinese/emoji.
            r.encoding = 'utf-8'
            dt_ms = int((time.monotonic() - t0) * 1000)
            ctype = r.headers.get('Content-Type', '')
            log.info('LLM response: status=%d  %dms  ctype=%s',
                     r.status_code, dt_ms, ctype)
            if r.status_code != 200:
                body_text = r.text
                log.warning('LLM non-200 body (first 500): %s', body_text[:500])
                self.failed.emit(f"HTTP {r.status_code}: {body_text[:120]}")
                return

            text_parts = []
            try:
                for raw_line in r.iter_lines(decode_unicode=True, chunk_size=1):
                    if raw_line is None:
                        continue
                    line = raw_line.strip()
                    if not line or line.startswith(':') or line.startswith('event:'):
                        continue
                    if not line.startswith('data:'):
                        continue
                    payload = line[5:].strip()
                    if not payload or payload == '[DONE]':
                        continue
                    try:
                        chunk = json.loads(payload)
                    except Exception:
                        continue
                    for c in (chunk.get('choices') or []):
                        d = c.get('delta') or {}
                        v = d.get('content')
                        if isinstance(v, str):
                            text_parts.append(v)
                            continue
                        v = d.get('reasoning_content')
                        if isinstance(v, str):
                            text_parts.append(v)
                            continue
                        # Some proxies send the full message in one chunk.
                        msg = c.get('message') or {}
                        v = msg.get('content')
                        if isinstance(v, str):
                            text_parts.append(v)
            except Exception:
                log.exception('chat/completions SSE iter failed')

            text = (''.join(text_parts).strip() or None)
            if not text:
                # Fallback: some proxies ignore stream=true and return full JSON.
                # Re-read body (it's already consumed by iter_lines, but r.content
                # may still be empty). Try one more non-stream request? No — to
                # avoid double-charging, just surface the empty result with context.
                log.error('chat/completions stream produced no text. parts=%d', len(text_parts))
                self.failed.emit("模型返回空内容,看 doro.log 了解详细响应")
                return
            log.info('LLM reply text_len=%d preview=%r', len(text), text[:80])
            self.replied.emit(text)
        except requests.exceptions.Timeout:
            log.warning('LLM timeout after %dms  url=%s', int((time.monotonic()-t0)*1000), url)
            self.failed.emit("请求超时 (60s)")
        except requests.exceptions.ConnectionError as e:
            log.error('LLM connection error: %s  url=%s', e, url)
            self.failed.emit(f"连接失败: {str(e)[:120]}")


class LLMService(QObject):
    replied = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self._history = []
        self._worker = None

    def reset_history(self):
        self._history.clear()

    def is_configured(self):
        return bool(self.cfg.get('llm_enabled') and self.cfg.get('llm_api_key'))

    def ask(self, user_text, extra_context=""):
        if not self.is_configured():
            log.warning('LLM.ask called but not configured')
            self.failed.emit("LLM 还没配置 API key,请去设置里开启")
            return
        sys_prompt = self.cfg.get('llm_system_prompt') or ''
        if extra_context:
            sys_prompt = f"{sys_prompt}\n\n当前状态:{extra_context}"
        limit = int(self.cfg.get('llm_history_limit'))
        msgs = [{'role': 'system', 'content': sys_prompt}]
        msgs.extend(self._history[-limit:])
        msgs.append({'role': 'user', 'content': user_text})
        self._history.append({'role': 'user', 'content': user_text})

        if self._worker is not None and self._worker.isRunning():
            log.info('LLM.ask: previous worker still running, dropping new request')
            return
        self._worker = LLMWorker(self.cfg, msgs)
        self._worker.replied.connect(self._on_reply)
        self._worker.failed.connect(self._on_fail)
        self._worker.start()

    def _on_reply(self, text):
        self._history.append({'role': 'assistant', 'content': text})
        max_hist = int(self.cfg.get('llm_history_limit')) * 2
        if len(self._history) > max_hist:
            self._history = self._history[-max_hist:]
        log.debug('LLM._on_reply forwarding to pet (history=%d)', len(self._history))
        self.replied.emit(text)

    def _on_fail(self, msg):
        if self._history and self._history[-1]['role'] == 'user':
            self._history.pop()
        log.warning('LLM._on_fail: %s', msg)
        self.failed.emit(msg)
