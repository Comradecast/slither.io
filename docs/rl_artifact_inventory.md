# RL Artifact Inventory

## Scope
Read-only inventory of prior ML/RL artifacts. No live bot behavior was changed.

This inventory inspected repository files, ignored artifacts, and small metadata from cached bytecode and evaluation logs. It did not run training, load live steering policies, delete files, or modify Controller, Strategy, or SafetyGate behavior.

## Repository State
- Current HEAD: `6599fdb (HEAD -> main, tag: v0.12.0-enemy-path-prediction) Add enemy path prediction`
- Current tags: `v0.12.0-enemy-path-prediction`, `v0.11.0-heading-aware-boundary-risk`, `v0.10.0-live-gate-validation-harness`, `v0.9.0-size-aware-survival-physics`, `v0.8.0-scenario-benchmark-harness`, `v0.7.0-evaluation-runner`, `v0.6.0-food-targeting-v1`, `v0.5.3-food-vacuum-fidelity`, `v0.5.2-food-collection-fidelity`, `v0.5.1-sandbox-fidelity-review`
- Untracked artifacts relevant to RL:
  - `live_telemetry.jsonl`, 1,515,394,163 bytes, 32,136 JSONL records counted on 2026-05-25
  - `sandbox/rl/__pycache__/*.pyc`, ignored by `__pycache__/`
  - `models/ppo_slither/logs/evaluations.npz`, ignored by `logs/`
  - `models/ppo_slither_ga_student/logs/evaluations.npz`, ignored by `logs/`
  - Root recovery/scratch files: `recover_all.py`, `recover_strategy.py.txt`, `found_strategy.py.txt`, `found_safety_gate.txt`, `found_strategy_662.txt`, `evaluate_heading_dump.txt`, `safety_gate_matches.txt`, `test_gate60.py.bak`

## Findings Summary
- Training scripts: Source files are missing from `sandbox/rl`, but bytecode caches identify prior scripts: `train.py`, `bc_train.py`, `collect_data.py`, `validate_data.py`, `validate_loop.py`, `arena.py`, `bc_eval.py`, and `env.py`.
- Environment definitions: `sandbox/rl/__pycache__/env.cpython-313.pyc` indicates a Gymnasium `SlitherEnv` wrapper with discrete actions and a 49-dimensional observation vector.
- Model artifacts: No loadable `.zip`, `.pt`, `.pth`, `.pkl`, or `.pickle` model checkpoints were found in the project tree. PPO-named directories contain only evaluation `.npz` logs.
- Logs/metrics: Two Stable-Baselines-style `evaluations.npz` files were found under `models/*/logs`.
- Scenario/replay data: `live_telemetry.jsonl` exists and contains live-style state/action records. No `demonstrations.jsonl` behavior-cloning dataset was found.

## Training Pipeline

### `sandbox/rl/train.py`
- Path: Source missing; bytecode present at `sandbox/rl/__pycache__/train.cpython-313.pyc`.
- Purpose: PPO training/fine-tuning for `SlitherEnv`.
- Algorithm: Stable-Baselines3 PPO with `MlpPolicy`.
- Entry command: Inferred from bytecode: `python -m sandbox.rl.train [total_timesteps]`.
- Inputs: `sandbox.rl.env.SlitherEnv`, scenario `rl_training_ground`, optional `models/ppo_slither/bc_model.zip`.
- Outputs: `models/ppo_slither/rl_model_*` checkpoints, `models/ppo_slither/best_model`, `models/ppo_slither/logs`, `models/ppo_slither/tensorboard`, `models/ppo_slither/final_model`.
- Reproducibility notes: Not runnable now because `sandbox/rl/train.py` and `sandbox/rl/env.py` source files are absent. It also references Stable-Baselines3, which is installed in the local `.venv` but not listed in `requirements.txt`.

### `sandbox/rl/bc_train.py`
- Path: Source missing; bytecode present at `sandbox/rl/__pycache__/bc_train.cpython-313.pyc`.
- Purpose: Behavior cloning from demonstration JSONL data into a PPO policy.
- Algorithm: Supervised imitation using Stable-Baselines3 PPO policy network and PyTorch loss over actions.
- Entry command: Inferred from bytecode: `python -m sandbox.rl.bc_train [epochs] [batch_size] [lr] [data_file]`.
- Inputs: Default `demonstrations.jsonl`, `SlitherEnv`, records with `observation.rl_obs` and `teacher_action`.
- Outputs: `models/ppo_slither/bc_model.zip`.
- Reproducibility notes: Not runnable now because source and `demonstrations.jsonl` are absent.

### `sandbox/rl/collect_data.py`
- Path: Source missing; bytecode present at `sandbox/rl/__pycache__/collect_data.cpython-313.pyc`.
- Purpose: Generate behavior-cloning demonstrations from a teacher bot profile.
- Algorithm: Deterministic teacher rollout, not RL training.
- Entry command: Inferred from bytecode: `python -m sandbox.rl.collect_data [num_runs] [max_ticks_per_run]`.
- Inputs: Scenario `rl_training_ground`, teacher profile `evolved_elite_gen090`.
- Outputs: Default `demonstrations.jsonl`.
- Reproducibility notes: Not runnable now because source is absent and `sandbox.bot.profiles` / `get_profile` are not present in the current tracked bot package.

### `sandbox/rl/validate_data.py`
- Path: Source missing; bytecode present at `sandbox/rl/__pycache__/validate_data.cpython-313.pyc`.
- Purpose: Validate behavior-cloning dataset records.
- Algorithm: JSONL schema validation.
- Entry command: Inferred from bytecode: `python -m sandbox.rl.validate_data [filepath]`.
- Inputs: Default `demonstrations.jsonl`.
- Outputs: Console pass/fail summary.
- Reproducibility notes: Not runnable now because source and dataset are absent.

### `sandbox/rl/validate_loop.py`
- Path: Source missing; bytecode present at `sandbox/rl/__pycache__/validate_loop.cpython-313.pyc`.
- Purpose: Smoke-test the full RL loop.
- Algorithm: Runs data collection, validation, one-epoch BC training, BC eval, short PPO fine-tune, and arena gate.
- Entry command: Inferred from bytecode: `python -m sandbox.rl.validate_loop`.
- Inputs: The `sandbox.rl.*` source modules.
- Outputs: Smoke-test console output and model/log artifacts.
- Reproducibility notes: Not runnable now because source files are absent.

### `sandbox/rl/arena.py`
- Path: Source missing; bytecode present at `sandbox/rl/__pycache__/arena.cpython-313.pyc`.
- Purpose: Promotion gate / arena evaluation for random, safety baseline, GA teacher, current champion, and PPO candidate.
- Algorithm: Evaluation only; loads PPO candidates if checkpoints exist.
- Entry command: Inferred from bytecode: `python -m sandbox.rl.arena`.
- Inputs: `models/ppo_slither/champion.zip`, `models/ppo_slither/final_model.zip`, `SlitherEnv`, bot profiles.
- Outputs: Console promotion decision; may copy candidate to champion.
- Reproducibility notes: Not runnable now because source, profile system, and checkpoint files are absent.

### `sandbox/rl/bc_eval.py`
- Path: Source missing; bytecode present at `sandbox/rl/__pycache__/bc_eval.cpython-313.pyc`.
- Purpose: Evaluate behavior-cloned student against teacher.
- Algorithm: Evaluation only.
- Entry command: Inferred from bytecode: `python -m sandbox.rl.bc_eval`.
- Inputs: `models/ppo_slither/bc_model.zip`, `SlitherEnv`, teacher profile `evolved_elite_gen090`.
- Outputs: Console comparison.
- Reproducibility notes: Not runnable now because source and model checkpoint are absent.

## Environment Contract
- Observation space: Inferred from bytecode as `spaces.Box` with shape `(49,)`, dtype `np.float32`.
- Action space: Inferred from bytecode as `spaces.Discrete(6)`.
- Action meaning: Inferred action mapping uses steering-rate steps around `-0.2`, `0`, and `0.2`, plus boost variants. Exact labels require source recovery.
- Reward: Inferred from bytecode as a combination of mass delta, small per-tick survival reward, food/mass reward scaling, and death penalty near `-50.0`. Exact formula requires source recovery.
- Termination: Bot death terminates. `max_ticks` inferred as `1500`; reaching it truncates.
- Scenario/randomization logic: Default scenario inferred as `rl_training_ground`; data collection used seeds derived from run number and scenario IDs like `gen090_seed_####`.
- Known mismatch with current deterministic bot:
  - Current repository has no `sandbox.bot.profiles` or `evolved_elite_gen090` profile.
  - Current deterministic bot has evolved through v0.9-v0.12 safety primitives after the cached RL code was produced.
  - The RL observation code duplicated older ray/body/food features and does not automatically include the current `SafetyGate` heading-aware boundary and projected enemy intercept internals.
  - `requirements.txt` lists only `pygame` and `numpy`; RL dependencies are present locally in `.venv` but not declared.

## Model Artifacts

### `models/ppo_slither/logs/evaluations.npz`
- Path: `models/ppo_slither/logs/evaluations.npz`
- Type: Stable-Baselines evaluation log, not a model checkpoint.
- Size: 10,418 bytes.
- Modified: 2026-05-23 15:44:57.
- Load risk: Low for metadata with `numpy.load(..., allow_pickle=False)`. Not a policy artifact.
- Notes: 201 evaluation points, 5 episodes per point, timesteps 10,000 through 2,010,000. First mean reward 36.08, last mean reward 159.66, best mean reward 267.75 at 910,000 timesteps. Episode length rose from 835 to 1500.

### `models/ppo_slither_ga_student/logs/evaluations.npz`
- Path: `models/ppo_slither_ga_student/logs/evaluations.npz`
- Type: Stable-Baselines evaluation log, not a model checkpoint.
- Size: 10,418 bytes.
- Modified: 2026-05-23 12:36:49.
- Load risk: Low for metadata with `numpy.load(..., allow_pickle=False)`. Not a policy artifact.
- Notes: 201 evaluation points, 5 episodes per point, timesteps 10,000 through 2,010,000. First mean reward 152.61, last mean reward 168.83, best mean reward 255.33 at 550,000 timesteps. Episode length was 1500 at first and last eval.

### Missing but referenced checkpoint paths
- `models/ppo_slither/final_model.zip`
- `models/ppo_slither/best_model`
- `models/ppo_slither/bc_model.zip`
- `models/ppo_slither/champion.zip`
- `models/ppo_slither/rl_model_*`
- Load risk: Cannot assess because files are absent.
- Notes: These names appear in bytecode strings but no matching files were found.

## Logs and Metrics
- Path: `models/ppo_slither/logs/evaluations.npz`
  - Metric summary: PPO candidate evaluation log over 2.01M timesteps.
  - Any reported evaluation result: Best mean reward 267.75 at timestep 910,000.
- Path: `models/ppo_slither_ga_student/logs/evaluations.npz`
  - Metric summary: PPO/BC student evaluation log over 2.01M timesteps.
  - Any reported evaluation result: Best mean reward 255.33 at timestep 550,000.
- Path: `live_telemetry.jsonl`
  - Metric summary: 32,136 records, 1.5GB. Records contain `timestamp`, `raw_data`, and `action`. `raw_data` contains `my_snake`, `snakes`, `foods`, and `map_radius`.
  - Any reported evaluation result: None directly; this is telemetry/state-action data, not an evaluation summary.
- Path: `reports/harness_results.jsonl`
  - Metric summary: Current deterministic validation harness output. Ignored under `reports/`.
  - Any reported evaluation result: All current harness scenarios passed in the latest run, but this is not an RL artifact.

## Scenario Datasets / Replay Data
- `live_telemetry.jsonl` is the only large replay-like dataset found. It may be convertible into deterministic validation scenarios because each record includes player/enemy/food state plus an action.
- `demonstrations.jsonl` is referenced by bytecode but was not found.
- No replay directory, W&B run directory, TensorBoard event files, CSV progress logs, or checkpoint archives were found outside `.venv`.
- The recalled 6-million-instance run cannot be verified from files currently present. The user notes Gemini described the training scale as 2 million sessions/runs per training event, and possibly three such events. The files available here verify two PPO-style evaluation logs ending at 2,010,000 timesteps each, plus a 32,136-record telemetry JSONL file. No artifact found so far proves 6 million sessions/runs or training instances.

## Safe Reuse Plan
Ranked safest to riskiest:

1. Scenario generator
   - Safest immediate use. Convert selected `live_telemetry.jsonl` frames into static deterministic harness scenarios, especially boundary, crossing, crowding, and food-density cases.
2. Evaluation opponent/stressor
   - Recreate simple stressors from telemetry patterns or inferred RL environment scenarios, but keep deterministic Strategy/SafetyGate as the system under test.
3. Offline advisor
   - Use RL logs or recovered observations only as offline analysis hints. Do not feed predictions into live steering.
4. Safe-heading tie-breaker
   - Possible later only after a strict SafetyGate wrapper, deterministic replay tests, declared dependencies, and reproducible model checkpoints.
5. Full controller replacement
   - Not safe now. Current model checkpoints are absent, training source is missing, reward contract is stale, and the deterministic safety stack is still being rebuilt.

## Recommended Next Milestone
`v0.14.0-telemetry-to-harness-scenarios`: build a read-only converter that samples `live_telemetry.jsonl` into small, reviewed deterministic scenario fixtures under `reports/` or a dedicated test fixture path. Start with a tiny candidate set and require human review before promoting any case into tracked tests.

## Remaining Unknowns
- The original `sandbox/rl/*.py` source files are missing; only `.pyc` caches remain.
- The original behavior-cloning dataset `demonstrations.jsonl` is missing.
- No actual PPO/BC checkpoint zip files were found, only evaluation logs.
- `sandbox.bot.profiles`, `get_profile`, and `evolved_elite_gen090` are referenced by bytecode but absent in the current repository.
- The exact reward formula and action mapping require source recovery or careful bytecode decompilation.
- The 6-million-instance training claim is attributable to Gemini/Antigravity session context, but is not verifiable from present files.
- The local `.venv` contains RL dependencies, but project dependency files do not declare them.
- `live_telemetry.jsonl` is large and untracked; any conversion should be streaming, sampled, and reviewed.
