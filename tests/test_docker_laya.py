from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_docker_build_installs_laya_as_an_optional_cpu_extra():
    dockerfile = (ROOT / "Dockerfile").read_text()
    assert "INSTALL_LAYA" in dockerfile
    assert '"laya==${LAYA_VERSION}"' in dockerfile
    assert "download.pytorch.org/whl/cpu" in dockerfile
    assert "TORCH_CPU_VERSION" in dockerfile
    assert "cuda" not in dockerfile.lower()
    assert "HF_HOME=/models" in dockerfile
    assert "USER jev" in dockerfile


def test_compose_persists_the_huggingface_cache_without_privileges():
    compose = (ROOT / "docker" / "docker-compose.example.yml").read_text()
    assert "HF_HOME: /models" in compose
    assert "laya-model-cache:/models" in compose
    assert "read_only: true" in compose
    assert "no-new-privileges:true" in compose
