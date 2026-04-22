import time
import psutil

try:
    import pynvml
    pynvml.nvmlInit()
    _GPU_COUNT = pynvml.nvmlDeviceGetCount()
    GPU_AVAILABLE = _GPU_COUNT > 0
except Exception:
    GPU_AVAILABLE = False
    _GPU_COUNT = 0


class SystemMonitor:
    def __init__(self):
        self._last_net = psutil.net_io_counters()
        self._last_time = time.time()
        psutil.cpu_percent(interval=None)

    def cpu(self):
        percent = psutil.cpu_percent(interval=None)
        count = psutil.cpu_count(logical=True)
        freq = psutil.cpu_freq()
        return {
            'percent': percent,
            'cores': count,
            'freq_ghz': (freq.current / 1000.0) if freq else 0.0,
        }

    def memory(self):
        m = psutil.virtual_memory()
        return {
            'percent': m.percent,
            'used_gb': m.used / (1024 ** 3),
            'total_gb': m.total / (1024 ** 3),
        }

    def gpu(self):
        if not GPU_AVAILABLE:
            return None
        try:
            h = pynvml.nvmlDeviceGetHandleByIndex(0)
            name = pynvml.nvmlDeviceGetName(h)
            if isinstance(name, bytes):
                name = name.decode('utf-8', errors='ignore')
            util = pynvml.nvmlDeviceGetUtilizationRates(h)
            mem = pynvml.nvmlDeviceGetMemoryInfo(h)
            try:
                temp = pynvml.nvmlDeviceGetTemperature(h, pynvml.NVML_TEMPERATURE_GPU)
            except Exception:
                temp = None
            return {
                'name': name,
                'percent': util.gpu,
                'mem_percent': mem.used / mem.total * 100,
                'mem_used_gb': mem.used / (1024 ** 3),
                'mem_total_gb': mem.total / (1024 ** 3),
                'temp': temp,
            }
        except Exception:
            return None

    def network(self):
        now = psutil.net_io_counters()
        t = time.time()
        dt = max(t - self._last_time, 1e-6)
        up = (now.bytes_sent - self._last_net.bytes_sent) / dt
        down = (now.bytes_recv - self._last_net.bytes_recv) / dt
        self._last_net = now
        self._last_time = t
        return {'up': max(up, 0), 'down': max(down, 0)}

    @staticmethod
    def fmt_speed(bps):
        if bps < 1024:
            return f"{bps:.0f} B/s"
        if bps < 1024 ** 2:
            return f"{bps / 1024:.1f} KB/s"
        if bps < 1024 ** 3:
            return f"{bps / (1024 ** 2):.1f} MB/s"
        return f"{bps / (1024 ** 3):.2f} GB/s"
