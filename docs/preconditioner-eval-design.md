# Android Preconditioner Agent — Outcome-Grounded Eval Design

Side project to practice agent-skill evaluation (Claude + GPT) on a realistic
agent: an **Android preconditioner** that takes a natural-language intent,
generates a provisioning **template**, finds a device, and provisions it.

Core premise (and the thing this project exists to prove out): **template
quality can only be fully verified after provisioning**, so the eval is
grounded in captured provision results and post-provision device state —
not in an LLM reviewing the template text.

---

## 1. The core insight, sharpened

"Eval on provision outcome instead of agent-review of the template" is the
outcome-grounded eval principle. Three refinements make it much stronger:

### 1.1 The template is a plan; plans are proxies
A template can look perfect and still fail on a real device (wrong API level
behavior, missing dependency ordering, a setting that needs a reboot). And a
template can look wrong to a reviewer and work fine. The only ground truth is:
*after provisioning, is the device in the intended state?*

### 1.2 Outcome eval is gold but expensive — so build a calibrated pyramid
Outcome eval is slow (minutes per case), flaky (devices), and costly. Don't
throw away cheap signals; **calibrate them against the outcome layer**:

| Layer | Signal | Cost | Role |
|---|---|---|---|
| L0 | Template static validation (schema, lint, dry-run plan) | ms | Prefilter garbage; hard gate |
| L1 | Provision execution result (per-step exit status, retries, duration) | minutes | Did the plan *run*? |
| L2 | **Post-provision device state vs. intended state** | minutes | **Ground truth: did the plan *work*?** |
| L3 | Downstream task success (the app/test the precondition was *for* actually runs) | minutes+ | Did the plan *matter*? (later phase) |

This turns "agent review of templates is less useful" from an opinion into a
**measurable claim**: run an LLM judge over templates, run the outcome eval,
and measure judge–outcome agreement (precision/recall of the judge predicting
provision success). If agreement is high in some categories, the judge becomes
a trusted cheap prefilter there; where it's low, you've quantified exactly why
outcome eval is necessary. This calibration study is itself a great
"auto-research" seed.

### 1.3 Declarative templates make verification cheap
**Design decision #1, and the most load-bearing one:** the template DSL is
*desired state*, not a command script.

- Imperative template (`adb shell settings put ...` list): verifying it means
  re-deriving intent from commands — you're back to reviewing text.
- Declarative template (Terraform/K8s style): verification is mechanical —
  read device state, diff against spec.

```yaml
# template: desired device state
apiVersion: precond/v1
requires:
  min_sdk: 33
state:
  locale: "ja-JP"
  settings:
    system: { screen_off_timeout: 600000 }
    global: { airplane_mode_on: 0 }
  apps:
    - package: com.example.app
      source: apks/example-1.2.3.apk
      permissions_granted: [android.permission.CAMERA]
      app_data: cleared
  wifi: { enabled: true }
files:
  - push: fixtures/photos/
    to: /sdcard/DCIM/
```

The provisioner compiles this to adb operations; the verifier reads state back
and diffs. The agent's job is intent → desired state, which is also the part
worth evaluating.

---

## 2. Failure attribution — the central enemy is flakiness

A failed provision has three possible causes, and an eval that can't tell them
apart produces noise, not signal:

| Cause | Whose fault | Detection mechanism |
|---|---|---|
| Template wrong (bad intent mapping, invalid state, missing dependency) | **Agent** — this is the eval signal | Fails deterministically across retries; golden template for same intent passes |
| Provisioner bug (compiler/executor defect) | Harness | Golden **canary templates** (hand-written, known-good) fail too |
| Environment flake (emulator hiccup, adb timeout) | Infra | Passes on retry from clean snapshot; canary flake rate |

Mechanisms to build in from day 1:

1. **Hermetic resets** — Android emulator snapshots give restore-to-clean in
   seconds. Every attempt starts from the same snapshot. This is a superpower
   real-device labs don't have; exploit it.
2. **Canaries** — a small set of hand-written golden templates runs in every
   eval batch. Canary failure ⇒ quarantine the batch (infra problem, not agent
   problem).
3. **Retries with attribution** — a case failing 1/3 attempts is *flaky*, not
   *failed*. Record all attempts; report `pass^k` (passes all k attempts) as
   the reliability metric alongside plain pass rate.
4. **Step-level structured results** — every provisioner step emits
   `{step, operation, status, stdout, stderr, duration, device_serial}` so
   failures localize themselves.

---

## 3. The verifier — independent by construction

The verifier is the "unit test" for the agent, so it must not share a pen with
the thing it grades:

- **Assertions are ground truth written per eval case by a human** (or a
  separate offline process) — never derived from the agent's template.
- **Read through a different path than the provisioner writes.** If the
  provisioner used `settings put`, the verifier uses `settings get` *and*
  `dumpsys` where possible. Catches write-succeeded-but-didn't-stick cases.
- **Partial credit** — each case has N assertions; score = assertions passed.
  A template that got locale right but permissions wrong is 80% wrong in a
  specific, categorizable way, not just "failed".
- **Minimality / side-effect check** — snapshot full readable device state
  before and after provisioning; the diff must be a subset of the intended
  changes. Catches over-provisioning (agent toggled airplane mode "to be
  safe") that positive assertions can never see. Report side-effect
  violations as their own metric.

---

## 4. The result schema IS the foundation

The "eval → prod analysis → auto research" ambition rests on one artifact:
**a single `ProvisionResult` event schema shared by eval runs and real runs.**

```
EvalRun(id, models[], dataset_version, git_sha, started_at)
 └── CaseResult(case_id, model, attempt_n, verdict, attribution)
      ├── template(text, template_hash, tokens_in/out, cost, latency)
      ├── ProvisionResult(status, duration, device_fingerprint)
      │    └── StepResult(op, status, stdout, stderr, duration)
      └── VerificationResult
           ├── AssertionResult(key, expected, actual, pass)
           └── StateDiff(before_hash, after_hash, unexpected_changes[])
```

Because prod (or "prod": your own ad-hoc use of the agent) emits the same
schema:

- **Prod analysis** = queries over the same tables the eval dashboard reads.
- **Replay** = a prod failure's intent + captured state becomes an eval case
  with one insert — the **failure → eval-case flywheel**.
- **Auto research** = jobs that read this store and write back to it
  (clustering, mutation, judge calibration — §7).

Invest in this schema early; version it; migrate it carefully. Everything
else can be rewritten cheaply as long as the results store is stable.

---

## 5. Architecture

```
dashboard (later)         core (Python)                     device layer
┌──────────────┐   ┌────────────────────────────┐   ┌─────────────────────┐
│ Eval dashboard│──│ eval runner  ─ agent client │──│ adb adapter          │
│ Run browser   │  │ (dataset,    (Claude / GPT  │  │  ├─ EmulatorDevice   │
│ Case drilldown│  │  seeds,       common iface) │  │  │  (Docker AVD +    │
│ Diff viewer   │  │  canaries)                  │  │  │   snapshots)      │
└──────────────┘   │ provisioner  verifier       │  │  └─ FakeDevice       │
                   │ (DSL→adb ops) (read+assert) │  │     (in-mem state,   │
                   │     results store (SQL)     │  │      for harness dev)│
                   └────────────────────────────┘   └─────────────────────┘
```

- **Fresh repo, boring stack**: a FastAPI (or plain Python) backend with
  modules `dsl/`, `agent/`, `provisioner/`, `verifier/`, `evalrunner/`;
  Postgres (or even SQLite at first) for the results store; a small React
  dashboard later. Start as a CLI + library — the dashboard is Phase 2.
- **Device abstraction with a `FakeDevice`** — an in-memory dict implementing
  the same `get_state/apply_op/snapshot/restore` interface as the emulator.
  Lets you build and unit-test the entire harness (DSL, provisioner, verifier,
  runner, dashboard) with zero emulator dependency, then swap in the real
  emulator. Also gives you fast CI.
- **Emulator**: headless AVD in Docker (e.g. `android-emulator` images or
  `budtmo/docker-android`), adb over TCP, `avd snapshot save/load` for resets.
- **Agent interface**: `generate_template(intent, device_profile) ->
  (template, trace)` — one implementation per provider so Claude vs GPT is a
  config change, and traces (tokens, latency, cost) land in the results store.

### What NOT to build (anti-goals for now)
- **Device-finding eval** — inventory matching is mostly deterministic
  constraint satisfaction; low eval value. Stub it (one emulator profile).
  Revisit in Phase 3+ as a scheduling/constraint eval if interesting.
- **Multi-device fleet** — one emulator, serialized runs, until eval runtime
  actually hurts.
- **Judge investment before ground truth exists** — the judge's job (§1.2)
  is to be *measured against* outcomes; build outcomes first.

---

## 6. Dataset design

An eval case:

```yaml
id: locale-ja-with-camera-app-003
category: compound        # settings | apps | permissions | files | compound
difficulty: 2             # 1 single-verb … 4 underspecified
intent: >
  Set the device to Japanese locale, install the demo camera app with
  camera permission pre-granted, and make sure screen stays on 10 minutes.
assertions:
  - { key: persist.sys.locale,                 expect: "ja-JP" }
  - { key: pm.package[com.example.camera],     expect: installed }
  - { key: pm.grant[com.example.camera, CAMERA], expect: granted }
  - { key: settings.system.screen_off_timeout, expect: "600000" }
max_side_effects: []      # nothing outside assertion scope may change
```

- **Start with 30–50 hand-written cases**, ~evenly across 5 verb categories:
  settings, app install/data, permissions, files/fixtures, compound.
- **Difficulty tiers**: (1) single-verb, (2) multi-verb, (3) constrained —
  ordering/dependencies matter (install before grant; some settings need the
  app present), (4) **underspecified** — intent leaves choices open; grade
  against an *acceptable set* of states, and track whether the agent's
  defaults are sane. Tier 4 is where model differences usually show up.
- Version the dataset (`dataset_version` on every run) so numbers stay
  comparable as cases are added from the prod flywheel.

### Metrics
- **Assertion pass rate** (partial credit) and **case pass rate**, sliced by
  category × difficulty × model.
- **pass^k** (all k seeds/attempts pass) — reliability, the metric that
  matters for an agent you'd trust in a pipeline.
- **Side-effect violation rate** (§3).
- **Attribution split** — of failures, % template / % harness / % flake. If
  flake share grows, fix infra before reading any model comparison.
- **Cost & latency per case** — tokens, $ per successful provision.
- **Judge–outcome agreement** (once the judge exists) — the §1.2 study.

---

## 7. Phasing

### Phase 0 — Harness without an agent (prove capture)
DSL schema + provisioner + verifier + results store, driven by **hand-written
golden templates** against FakeDevice, then one real emulator with snapshot
reset. Exit criteria: a golden template run produces a complete
`ProvisionResult` + `VerificationResult` row, and a deliberately broken
template produces a correctly-attributed failure. *No LLM anywhere yet.*

### Phase 1 — Agent + baseline eval
Agent client (Claude + GPT), 30–50 case dataset, eval runner with canaries
and retries. Deliverable: first baseline report — per-category pass rates,
pass^k, cost — for 2+ models. This is the "practice what I did at work" core.

### Phase 2 — Eval pipeline
Make it a pipeline, not a script: seeds, run history, regression gating
(fail CI if pass rate drops vs. baseline on same dataset_version), the React
dashboard (run browser → case drilldown → step logs + state diff viewer),
scheduled runs.

### Phase 3 — Prod analysis
Use the agent for real (your own ad-hoc preconditioning = "prod"). Prod runs
emit the same schema into the same store. Build: failure clustering
(embed intent + failure signature, cluster), prod↔eval drift view (are prod
intents covered by the dataset?), and **one-click replay: prod failure →
eval case**.

### Phase 4 — Auto research
Jobs over the results store:
- **Auto case generation** — mutate existing cases (swap values, compose
  verbs, perturb phrasing); keep mutants that are valid (golden template
  passes them) but that the agent fails — automatic hard-case mining.
- **Judge calibration** (§1.2) — train/prompt a template judge, measure
  agreement vs. outcomes, deploy it as a prefilter only where calibrated.
- **Prompt/strategy search** — variants of the generation prompt evaluated
  on the frozen dataset with regression gating; the eval becomes the fitness
  function.

Each phase has a working deliverable, and each is a portfolio-worthy artifact
on its own.

---

## 8. Risks / open questions

- **Emulator ops burden** — snapshots occasionally corrupt; adb over TCP
  drops. Mitigation: FakeDevice for all harness dev, canaries + quarantine
  for real runs, recreate-AVD-from-scratch script as the escape hatch.
- **DSL scope creep** — every new verb costs provisioner + verifier + cases.
  Hold the line at 5 categories until Phase 3 demand says otherwise.
- **Underspecified-intent grading** — acceptable-set grading is hand-wavy;
  may need a rubric or (calibrated) judge for tier-4 cases. Fine to defer.
- **L3 (downstream task success)** — the truest signal, but needs a consumer
  workload (e.g., an instrumented test that runs after provisioning). Park it
  until Phase 3; the schema already has room for it.
