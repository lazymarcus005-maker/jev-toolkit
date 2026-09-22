import os

import pytest

from jev.config import ProviderConfig
from jev.models import DecisionRequest
from jev.providers.laya import LayaLocalProvider


@pytest.mark.skipif(os.environ.get("RUN_LAYA_INTEGRATION") != "1", reason="set RUN_LAYA_INTEGRATION=1 to download and run Laya")
def test_real_laya_cpu_decision():
    pytest.importorskip("laya")
    provider = LayaLocalProvider(ProviderConfig("laya", "laya", model="typed-decisions", device="cpu", preload=True, timeout_ms=30000))
    result = provider.decide(DecisionRequest("next", "choose the next bounded step", {"finding": "latency rose"}, ("inspect", "conclude")))
    assert result.choice in {"inspect", "conclude"}
    assert 0 <= result.confidence <= 1
