# Edge-level GNN anomaly detector — pre-Asolaria lineage

This directory is the public pre-Asolaria origin of the edge-level graph-neural-network family that
was later absorbed into the Asolaria GNN sidecar, BigPickle scorer, Hookwall, forward/reverse GNN
planes, and white-room pipeline.

The important abstraction appeared here first:

```text
classify and explain the RELATIONSHIP between two nodes
rather than classify an isolated row or node
```

In this healthcare/security context, an edge can represent an API/FHIR interaction, a clinical
relationship, or a network flow. In Asolaria the same abstraction is reused for agent messages,
PID routes, device signals, Hookwall envelopes, and graph paths.

## Model family

| model | mechanism | repository-reported result |
|---|---|---:|
| `EdgeLevelGNN` | two-layer GCN node encoder + source/target edge MLP | 91.87% accuracy |
| `PrototypeGNN` | edge embeddings classified by distance to learned class prototypes | 94.24% accuracy |
| `ContrastiveGNN` | edge classifier plus supervised contrastive projection/loss | 94.71% accuracy |
| `GSLGNN` | learned adjacency branch + original-graph branch + combined classifier | 96.66% accuracy; 99.70% ROC-AUC; 1.5% FPR |

These numbers are preserved in the model source/docstrings and README and should be described as
**repository-reported training results** unless a separate reproducible dataset/checkpoint run is
attached. The unit tests in this repository verify architecture, output shapes, probability ranges,
prototype distances, projection normalization, contrastive loss behavior, learned adjacency shape,
and both GSL branches; they do not independently reproduce the quoted benchmark metrics.

## Training evidence and runtime boundary

The model implementations are training-capable, not inference-only stubs:

- `PrototypeGNN` contains learnable class prototypes and a prototype cross-entropy objective.
- `ContrastiveGNN` contains a projection head and `SupervisedContrastiveLoss`.
- `GSLGNN` learns a sparsified adjacency matrix and combines learned-graph and original-graph
  encoders.
- the source records the comparative results of the edge-level architecture study.

However, `service.py` currently instantiates the selected architecture and puts it into evaluation
mode while the block that loads `weights/{model_type}_model.pt` is commented out. Therefore:

```text
pre-Asolaria healthcare repo proves:
  architecture family
  training objectives
  model factory
  clinical graph integration
  repository-reported trained metrics

pre-Asolaria healthcare service does NOT by itself prove:
  that a trained checkpoint is automatically loaded in the checked-in runtime
```

The later `Asolaria-fnns-trained-and-reverse-gnns-many` repository contains the trained `.pt`
checkpoint/manifests for the subsequent Asolaria stage. That later evidence should not be read
backward as though those exact files were loaded here, but it confirms that the lineage continued
into trained deployed artifacts.

## Byte-identical transfer into Asolaria

The transfer into `JesseBrown1980/asolaria-behcs-256/services/gnn-sidecar/models/` is proven at the
Git-object level. The corresponding files have identical blob SHAs:

| model file | healthcare blob SHA | Asolaria sidecar blob SHA | byte-identical |
|---|---|---|---:|
| `gnn_baseline.py` | `510f78890ec94b113f0610afbade8bafe6ca20e0` | `510f78890ec94b113f0610afbade8bafe6ca20e0` | yes |
| `prototype_gnn.py` | `99e3087a10ee58e90c0935f5ab63b72fd3cdd07e` | `99e3087a10ee58e90c0935f5ab63b72fd3cdd07e` | yes |
| `contrastive_gnn.py` | `56329e61eb3e6ddb3ee97b46f997dd8dd8c6b39f` | `56329e61eb3e6ddb3ee97b46f997dd8dd8c6b39f` | yes |
| `gsl_gnn.py` | `886b3b0c0cdbddba983fa8c3ae083c4520d38f0e` | `886b3b0c0cdbddba983fa8c3ae083c4520d38f0e` | yes |

This is direct code lineage, not an inference from similar class names.

## Evolution into the Asolaria stack

```text
AI healthcare / intrusion edges
  -> EdgeLevel / Prototype / Contrastive / GSL model family
  -> byte-identical Asolaria Python sidecar import
  -> L0 EdgeLevelGNN :4792 + L4 GSLGNN :4793
  -> live agent/message graph watcher
  -> BigPickle 7-GNN score surface
  -> G1 edge-mining
  -> G2 forward-genius
  -> G3 reverse-gain
  -> G4 GLSM
  -> Fischer anti-blunder
  -> Shannon / OmniShannon
  -> white rooms
  -> GULP / cube mint / supervisor proposal
```

The domain changed, but the learned object stayed the same: an edge whose meaning, importance,
anomaly status, and structural context can be scored.

## BigPickle connection

`JesseBrown1980/bigpickle-rebuild/src/asolaria-score.mjs` explicitly orchestrates:

- L0 `EdgeLevelGNN` on `:4792`;
- L4 `GSLGNN` on `:4793`;
- G1 edge mining;
- G2 forward-genius path scoring;
- G3 reverse-gain;
- G4 GLSM state;
- OmniShannon;
- deterministic SHA fallback.

BigPickle therefore contains the system-level continuation of these pre-Asolaria GNNs even though
it does not duplicate every PyTorch model file. It treats the Python models as sidecar endpoints and
adds the graph, gating, anti-blunder, receipt, and storage civilization around them.

## Applicability to storage-rich / low-GPU machines

The original PyTorch models may use CPU or GPU for training/inference. The later Asolaria system
separates that neural scorer from the rest of the control plane:

```text
GPU/accelerator optional sidecar:
  trained GNN / LLM tensor inference

CPU + HDD/SSD control plane:
  graph ledgers
  HBP/HBI/SHA receipts
  content-addressed cubes
  queues and PID tables
  BEHCS representation rebasing
  CRT Path-2 recovery
  white-room compaction
  bounded 2,000-message active windows
```

This lets commodity or storage-heavy machines participate as graph collectors, disk-backed memory
nodes, dispatchers, white rooms, recovery poles, and verifiers without keeping the whole system in
GPU memory. It does not mean a hard drive performs the neural matrix multiplications.

## Verification provenance — 2026-07-11

`AUDITED_GPT_5_6_PRO`:

- inspected all four model implementations, their test surface, model factory, clinical anomaly
  path, and checkpoint-load boundary;
- compared each Git blob SHA against the Asolaria sidecar;
- inspected BigPickle's scorer and Fischer integration;
- traced the later trained-checkpoint, Hookwall, OmniShannon, white-room, Path-1, Path-2, and
  Q-PRISM watcher repositories.

No new healthcare benchmark is claimed by this documentation-only change. The correct result is the
proven code lineage plus the repository-reported pre-Asolaria metrics and the later separately
preserved trained checkpoints.

## Claim ledger

- `MEASURED`: four model implementations; training-specific objectives; shape/forward/loss tests;
  model factory; clinical graph integration; byte-identical transfer into the Asolaria sidecar.
- `REPOSITORY_REPORTED_TRAINING`: 91.87%, 94.24%, 94.71%, and 96.66% comparative metrics.
- `MEASURED_LATER_STAGE`: trained `.pt` artifacts/manifests in the later Asolaria trained-model repo.
- `BOUNDARY`: the checked-in healthcare service does not currently load those weights automatically.
- `AUDITED_GPT_5_6_PRO`: complete lineage and source audit described above.
