from types import SimpleNamespace

import pytest

from pollyxt_pipelines import scc_access
from pollyxt_pipelines.scc_access import SCC
from pollyxt_pipelines.scc_access.types import Product, ProductStatus


def measurement(queued=False, processing=False, eldec=ProductStatus.OK):
    return SimpleNamespace(
        is_queued=queued, is_processing=processing, eldec=Product(eldec)
    )


class FakeSCC(SCC):
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def get_measurement(self, measurement_id):
        self.calls += 1
        return self.responses.pop(0)


@pytest.fixture
def no_sleep(monkeypatch):
    sleeps = []
    monkeypatch.setattr(scc_access.time, "sleep", sleeps.append)
    return sleeps


def test_wait_returns_when_done(no_sleep):
    scc = FakeSCC(
        [
            None,
            measurement(queued=True),
            measurement(processing=True),
            measurement(eldec=ProductStatus.ERROR),
        ]
    )

    result = scc.wait_for_product("x", timeout=60, poll=30)

    assert result.eldec.status == ProductStatus.ERROR
    assert scc.calls == 4
    assert no_sleep == [30, 30, 30]


def test_wait_busy_time_does_not_count(no_sleep):
    # Busy for much longer than the timeout
    scc = FakeSCC([measurement(processing=True)] * 50 + [measurement()])

    result = scc.wait_for_product("x", timeout=60, poll=30)

    assert result.eldec.status == ProductStatus.OK


def test_wait_times_out_when_missing(no_sleep):
    scc = FakeSCC([None] * 10)

    with pytest.raises(TimeoutError):
        scc.wait_for_product("x", timeout=60, poll=30)

    assert scc.calls == 3


def test_wait_unknown_product():
    with pytest.raises(ValueError):
        FakeSCC([]).wait_for_product("x", product="nope")
