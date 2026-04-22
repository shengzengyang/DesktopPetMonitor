from PyQt5.QtCore import QObject, QTimer, pyqtSignal


class Pomodoro(QObject):
    WORK = 'work'
    BREAK = 'break'
    IDLE = 'idle'

    phaseChanged = pyqtSignal(str, int)  # phase, remaining_sec
    tick = pyqtSignal(str, int)           # phase, remaining_sec
    completed = pyqtSignal()

    def __init__(self, work_min=25, break_min=5, parent=None):
        super().__init__(parent)
        self.work_sec = work_min * 60
        self.break_sec = break_min * 60
        self.phase = self.IDLE
        self.remaining = 0
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_tick)

    def configure(self, work_min, break_min):
        self.work_sec = work_min * 60
        self.break_sec = break_min * 60

    def start_work(self):
        self.phase = self.WORK
        self.remaining = self.work_sec
        self._timer.start()
        self.phaseChanged.emit(self.phase, self.remaining)

    def start_break(self):
        self.phase = self.BREAK
        self.remaining = self.break_sec
        self._timer.start()
        self.phaseChanged.emit(self.phase, self.remaining)

    def stop(self):
        self._timer.stop()
        self.phase = self.IDLE
        self.remaining = 0
        self.phaseChanged.emit(self.phase, 0)

    def is_running(self):
        return self._timer.isActive()

    def _on_tick(self):
        self.remaining -= 1
        if self.remaining <= 0:
            if self.phase == self.WORK:
                self.completed.emit()
                self.start_break()
            elif self.phase == self.BREAK:
                self.start_work()
            return
        self.tick.emit(self.phase, self.remaining)

    @staticmethod
    def fmt(sec):
        sec = max(0, int(sec))
        return f"{sec // 60:02d}:{sec % 60:02d}"


class SitReminder(QObject):
    ping = pyqtSignal()

    def __init__(self, interval_min=45, parent=None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.ping.emit)
        self.set_interval(interval_min)

    def set_interval(self, interval_min):
        self.interval_min = interval_min
        self._timer.setInterval(max(1, interval_min) * 60 * 1000)

    def start(self):
        if self.interval_min > 0:
            self._timer.start()

    def stop(self):
        self._timer.stop()

    def reset(self):
        if self._timer.isActive():
            self._timer.start()
