# CI Backend Test Fix Receipt

eceipt_id=ci-backend-test-fix-20260706

## Scope

MEASURED_ACER_LOCAL repair for GitHub PR #242 after the clinical-boundary patch was byte-verified but the backend 	ests job failed.

## Root Causes

- ackend/middleware/input_validation.py used os.getenv without importing os.
- Legacy-route service-missing tests inspected pp.routes directly, while included routers now expose effective route contexts.
- Adapter and stats tests omitted auth headers for endpoints protected by uth_dependency.
- Integration tests used a real OpenAI-backed LLMEngine whenever OPENAI_API_KEY existed, making normal CI sensitive to external network/model behavior.

## Fixes

- Added import os to the input-validation middleware.
- Resolved legacy route auth dependency through ffective_route_contexts, preserving dependency override behavior without demo-mode side effects.
- Added authenticated request headers to adapter and stats endpoint tests.
- Made real LLM integration opt-in through ALLOW_REAL_LLM_IN_TESTS=true; default CI/test behavior uses the high-fidelity local mock.

## Verification

- Targeted slice: 10 passed, 23 warnings.
- Workflow-shaped no-coverage backend selection: 421 passed, 8 skipped, 24 deselected, 230 warnings.
- Workflow-shaped backend command with coverage/junit: 421 passed, 8 skipped, 24 deselected, 230 warnings.

## Boundary

Local verification ran on Windows Python 3.13. GitHub Actions remains the source-of-truth gate on Ubuntu Python 3.11 after push. This receipt does not claim clinical readiness or live provider/model completion.