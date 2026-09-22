# Laya Local CPU Provider

Laya is an optional local provider for Jev’s bounded decision contract. It
evaluates typed questions over compact state in one forward pass and returns a
choice with calibrated confidence. Jev remains the abstraction: skills call
`decide`, never `laya`, and the main agent remains responsible for reasoning,
actions, and final synthesis.

## Install

Remote-only installations do not pull the model runtime:

```bash
pip install jev-agent-toolkit
```

Install local CPU support when needed:

```bash
pip install 'jev-agent-toolkit[laya]'
```

The optional `laya` package loads the Apache-2.0 checkpoints from Hugging Face.
Weights are downloaded on first load and are not included in this repository.

## Configuration

```yaml
providers:
  laya:
    type: laya
    enabled: true
    model: typed-decisions
    device: cpu
    preload: true
    max_loaded_models: 2
    cache_dir: /models
    timeout_ms: 3000

routing:
  default: laya
  fallback:
    technical_error:
      - typesafe
  # low confidence returns to the main agent
```

Supported models are `typed-decisions`, `multilingual`, and `router`.
`multilingual` is appropriate for Thai, English, and mixed-language state.
`router` lets Laya choose a checkpoint. Laya V1 accepts only `device: cpu`; it
does not require CUDA, Metal, ROCm, GPU passthrough, or a privileged container.

The equivalent environment overrides are `LAYA_DEVICE`, `LAYA_MODEL`,
`LAYA_PRELOAD`, `LAYA_MAX_LOADED_MODELS`, and `LAYA_CACHE_DIR`.

## Lifecycle and cache

With `preload: true`, model loading occurs during provider initialization and
readiness reports `status: ready` only after success. With `preload: false`, the
first decision loads lazily. Initialization is guarded so concurrent first
requests share one model load. Load and inference failures become normal Jev
technical fallback results.

Docker sets `HF_HOME=/models` and mounts the named `laya-model-cache` volume.
This keeps model weights across container restarts without making the root
filesystem writable. The Docker build pins a PyTorch CPU wheel and installs no
CUDA/NVIDIA packages. A missing model cache may make `/ready` return 503 while
the model downloads; the response includes a safe provider diagnostic.

## Commands and benchmark

```bash
jev providers list --config config/jev.yaml
jev providers test laya --config config/jev.yaml
jev benchmark laya --runs 20 --warmup 3 --config config/jev.yaml
```

Benchmark output reports model, device, warmup/runs, mean, p50, p95, min, max,
and success rate. It measures the current machine; no latency number in the
model card is treated as a Jev Toolkit SLA. For a real download/inference test,
run `RUN_LAYA_INTEGRATION=1 pytest tests/integration/test_laya.py` explicitly.

## Fallback and readiness

Valid, confident Laya results use `provider: laya`. Invalid choices, malformed
responses, load failures, and inference timeouts try the configured technical
fallback. Low confidence goes directly to the main agent and is never retried
repeatedly to force a preferred answer. `/health` checks only the process;
`/ready` reports provider/model readiness without secrets or stack traces.

## Agent integration

Claude Code, Codex, Pi, and Hermes can use the existing Jev MCP server, CLI, or
HTTP adapter. Their skills remain unchanged:

```text
skill -> jev_decide -> routing -> laya or typesafe -> bounded result
```

The Elastic example uses compact counts, distributions, findings, and
completed checks. It never sends raw logs to Laya. Switching `routing.default`
between `laya` and `typesafe` requires no skill change.

## Troubleshooting and limitations

- `Laya is not installed`: install the `[laya]` extra in the same environment
  running `jev`.
- `/ready` is not ready: inspect the provider error, network access to Hugging
  Face, disk space, and write permission for `HF_HOME`.
- Slow or timed-out CPU inference: reduce state size, use a bounded choice set,
  increase `timeout_ms`, or allow the configured remote fallback.
- Laya checkpoints are CPU-capable but still require substantial memory and
  initial download time. The shipped base checkpoints can be overconfident and
  are not a substitute for domain calibration.
- High-cardinality choice sets may exceed Laya’s option budget; pre-filter or
  split them before calling Jev.

Reference: [Laya model card](https://huggingface.co/convaiinnovations/laya).
