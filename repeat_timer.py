import threading
# from logging import getLogger
# logger = getLogger("repeattimer")

class RepeatTimer(threading.Thread):

    def __init__(self, interval, callable, args=[], kwargs={}):
        threading.Thread.__init__(self)
        # interval_current shows milliseconds in current <tick>
        self.interval_current = interval
        # interval_new shows milliseconds for next <tick>
        self.interval_new = interval
        self.callable = callable
        self.args = args
        self.kwargs = kwargs
        self.event = threading.Event()
        self.event.set()
        self.activation_dt = None
        self.__timer = None

    def run(self):
        while self.event.is_set():
            # self.activation_dt = datetime.utcnow()
            self.__timer = threading.Timer(self.interval_new,
                                           self.callable,
                                           self.args,
                                           self.kwargs)
            self.interval_current = self.interval_new
            self.__timer.start()
            self.__timer.join()

    def cancel(self):
        self.event.clear()
        if self.__timer is not None:
            self.__timer.cancel()

    def trigger(self):
        self.callable(*self.args, **self.kwargs)
        if self.__timer is not None:
            self.__timer.cancel()

    def change_interval(self, value):
        self.interval_new = value
