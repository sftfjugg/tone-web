import threading


class ToneThread(threading.Thread):
    def __init__(self, func, args=()):
        super(ToneThread, self).__init__()
        self.func = func
        self.args = args
        self.result = []

    def run(self):
        self.result = self.func(*self.args)

    def get_result(self):
        try:
            return self.result
        except Exception:
            return None
