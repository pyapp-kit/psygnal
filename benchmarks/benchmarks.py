# type: ignore


class TimeSuite:
    def setup(self):
        self.d = {}
        for x in range(500):
            self.d[x] = None

    def time_keys(self):
        for _ in self.d.keys():
            pass

    def time_iterkeys(self):
        for _ in self.d.items():
            pass

    def time_range(self):
        d = self.d
        for key in range(500):
            _ = d[key]

    def time_xrange(self):
        d = self.d
        for key in range(500):
            _ = d[key]


class MemSuite:
    def mem_list(self):
        return [0] * 256
