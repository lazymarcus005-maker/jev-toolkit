from examples.elastic_investigation import run_three_round_example


def test_elastic_example_runs_three_bounded_rounds():
    rounds = run_three_round_example()
    assert len(rounds) == 3
    assert [item["jev"]["choice"] for item in rounds] == ["inspect_instance", "inspect_downstream", "inspect_deployment"]
    assert all(item["evidence"]["finding"] for item in rounds)
