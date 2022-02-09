from psygnal.containers import EventedObjectProxy


def test_evented_proxy():
    class T:
        def __init__(self) -> None:
            self.x = 1
            self.f = "f"

    t = EventedObjectProxy(T())
    assert t.x == 1
