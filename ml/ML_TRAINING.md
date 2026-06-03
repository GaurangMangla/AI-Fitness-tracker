# Athlyt — ML Training Documentation (Phase 2.2, updated for the v2 retrain)

**Model version: v2** (retrained 2026-07-21, after the `bro_split` rule-engine fix documented in §2.4 below). This document describes the original v1 training process in full — everything in §2-§6 is still accurate for *how* training works, since the pipeline was reused unchanged for v2. Where a specific number or claim changed for v2, it's called out explicitly inline. See `ml/models/MODEL_COMPARISON.md` for the complete v1-vs-v2 comparison and `ml/models/evaluation_report.md` for v2's evaluation (v1's original report is preserved at `ml/models/evaluation_report_v1_archive.md`).

**Status:** Dataset generated, model trained, evaluated, **and integrated into the backend** behind `RECOMMENDATION_ENGINE=ml` (see `docs/ML_INTEGRATION.md`) — defaults to `rule` in production. This is v2 of the model, retrained after a real bug fix in the rule engine (see §2.4).

---

## 1. What this phase produced

| Artifact | Location | Description |
|---|---|---|
| Dataset generator | `ml/notebooks/generate_dataset.py` | Standalone script, importable and runnable independently of the notebook — **unmodified** between v1 and v2; the regenerated dataset differs only because the rule engine it calls changed |
| Training notebook | `ml/notebooks/train_model.ipynb` | Full pipeline, Colab-ready, executed end-to-end with zero errors |
| Dataset | `ml/data/dataset.csv` | 100,000 synthetic users, labeled by the real rule engine (v2: now includes `bro_split`, see §2.4) |
| Class distribution comparison | `ml/data/class_distribution_comparison_v1_vs_v2.csv` | Exact before/after row counts per class |
| Trained model | `ml/models/model.joblib` | `RandomForestClassifier`, 69.5MB (v2) |
| Preprocessor | `ml/models/preprocessor.joblib` | Fitted `ColumnTransformer` (one-hot encoding) |
| Metadata | `ml/models/metadata.json` | Hyperparameters, metrics, feature list, training timestamp, `model_version: "v2"` |
| Evaluation report | `ml/models/evaluation_report.md` | v2 results writeup with real numbers (v1's original preserved at `evaluation_report_v1_archive.md`) |
| Model comparison | `ml/models/MODEL_COMPARISON.md` | Full v1-vs-v2 comparison: dataset, model metrics, per-class changes, rule-vs-ML regression test |
| Regression test results | `ml/models/regression_test_summary_v2.json`, `regression_test_disagreements_v2.csv` | 150-profile out-of-sample rule-vs-ML agreement check |
| This document | `ml/ML_TRAINING.md` | Narrative explanation of every decision |

---

## 2. Dataset generation

### 2.1 Why the rule engine itself does the labeling

`ml/notebooks/generate_dataset.py` imports `RuleBasedRecommendationEngine` directly from `backend/app/services/recommendation_engine.py` — the exact class the live application uses for `POST /workouts/recommend` today. Every synthetic user's label is produced by actually calling `engine.recommend(recommendation_input)`, not by a hand-written approximation of the rules.

**Why this matters:** it guarantees the dataset's labels are *exactly* what the running app would recommend for that profile, right now. A model trained on this dataset is learning to imitate the real system, not a guess at what the real system probably does.

**The honest limitation this creates**, stated plainly: a model trained to imitate a deterministic function can, at best, match that function's behavior — it cannot discover a "better" recommendation than the rule engine would give, because the rule engine's own output *is* the ground truth here. This is why `docs/ML_ARCHITECTURE.md` §3.3 and §7 both point to real user behavioral outcome data (did someone actually stick with their recommended plan?) as the genuine long-term path to a model that can outperform the rules — not this initial model, and not any model trained purely on rule-engine-generated labels, however sophisticated.

### 2.2 Realistic distributions — verified, not assumed

Every distribution choice in `generate_dataset.py` is deliberate and explained inline in the code. The key ones, and their **verified actual output** on the real 100,000-row dataset:

| Requirement | Target | Actual (verified) |
|---|---|---|
| Age range | 16–65 | 16–65, mean 28.4 |
| Beginner majority | Yes | 55.2% beginner, 34.9% intermediate, 9.8% advanced |
| Bodyweight > full gym | Yes | 32,011 users with no equipment vs. 21,085 with full gym access |
| Balanced goals | Realistic spread | weight_loss 34.8%, muscle_gain 32.0%, general_fitness 20.1%, maintenance 13.1% |
| Realistic correlations | Height/weight/BMI correlated | Weight is sampled *conditioned on* height via a target BMI (§2.3), not independently |

### 2.3 The correlation requirement, specifically

The phase spec explicitly requires "maintain realistic correlations" — this is easy to get wrong by sampling every feature independently (e.g., a 150cm person and a 200cm person having an equal chance of weighing 90kg, which doesn't reflect how real bodies are distributed).

The generator instead samples a target BMI first (from a realistic population BMI distribution, mean ~24.5), then computes weight from that BMI and the already-sampled height, plus a small amount of additional noise so weight isn't a perfectly deterministic function of height alone. This is the one correlation explicitly engineered in; age, experience, equipment, and goals are sampled independently of each other, which is a reasonable simplification for a first-generation synthetic dataset (real users' goals do correlate somewhat with experience level, for instance — a natural improvement path noted in §7).

### 2.4 A genuine discovery: `bro_split` never occurs

While validating the dataset's target distribution, a real problem was found — not a dataset bug, a **discovery about the existing, deployed rule engine**:

**`bro_split` has zero occurrences in 100,000 samples.** This was investigated exhaustively before accepting it as correct rather than a sampling artifact:

```python
# Every combination of goal x experience x day-count(5,6) x full_gym equipment
# was tested directly against the real engine — including bro_split's
# theoretical best possible case.
```

**Result: `bro_split` never won a single comparison, including its own best case** (advanced experience, muscle_gain goal, 5 days, full gym equipment, no recovery penalty).

**Root cause, traced through the actual rule code** (`backend/app/services/recommendation_rules.py`):
- `push_pull_legs`'s goal-score is ≥ `bro_split`'s for every single `FitnessGoal` value (by 1–2 points each time)
- `push_pull_legs`'s day-fit score is ≥ `bro_split`'s for every day count in `bro_split`'s valid range (tied at exactly 5 days, strictly better at 6, since `push_pull_legs`'s `ideal_days` includes both 5 and 6 while `bro_split`'s is only 5)
- Both splits are in the rule engine's `_HIGH_FREQUENCY_SPLITS` set, so the recovery-capacity adjustment affects them identically — it never creates a gap between them
- The one place `bro_split` gains ground is the experience score for `advanced` users (+1 relative to `push_pull_legs`) — but this is never enough to overcome the goal-score deficit, at best producing an **exact tie**
- Python's `max()` (used by `select_best_split` to pick the winner) returns the *first* maximum it encounters, and `push_pull_legs` is defined before `bro_split` in the `WORKOUT_SPLITS` tuple — so every tie resolves in `push_pull_legs`'s favor

**This is a real, pre-existing bug in the production rule engine** — `bro_split` is fully defined (in `workout_splits.py`), has its own name, difficulty rating, and equipment/day requirements, but is structurally unreachable as an output regardless of user profile. It was discovered as a side effect of building this dataset, not introduced by it.

**How it was handled in this phase:** per the explicit scope of this phase ("do not modify the backend"), the rule engine was left untouched. The dataset faithfully reflects what the real system actually does — training on a fabricated `bro_split` label would mean training the model on data the real app would never produce, defeating the point of imitating it. The model was trained on the **5 classes that genuinely occur**.

**Recommended next step (separate from ML work):** fix the rule engine's tie-breaking or `bro_split`'s scoring so it becomes reachable, then regenerate the dataset and retrain. A minimal fix would be adjusting `bro_split`'s goal-scores upward by 1-2 points for `muscle_gain` specifically (its most natural use case), or changing tie-break order. This is a bug fix independent of any ML work and worth raising with whoever owns `recommendation_rules.py`.

> **Update (2026-07-21):** this was fixed. `bro_split`'s advanced-experience score was raised from `10` to `12` in `recommendation_rules.py` — verified mathematically and with dedicated regression tests that `bro_split` now wins at its real-world niche (advanced experience, 5 days/week, full gym) across every fitness goal, without changing any other split's behavior. The dataset above was then regenerated and the model retrained — see `ml/models/MODEL_COMPARISON.md` for the complete before/after comparison. **This section is preserved as-written above** (the original discovery narrative) rather than rewritten, since it's the accurate record of what was found and why, at the time it was found.

---

## 3. Feature engineering

| Feature | Type | Encoding |
|---|---|---|
| `gender`, `fitness_goal`, `activity_level`, `workout_experience`, `diet_preference`, `bmi_category` | Categorical | One-hot (`OneHotEncoder(handle_unknown="ignore")`) |
| `equipment_available` | Multi-valued | Multi-hot (`str.get_dummies(sep=",")`) — a user can have multiple equipment types simultaneously, so this isn't a single categorical value |
| `age`, `height_cm`, `weight_kg`, `bmi`, `workout_days_per_week`, `equipment_count` | Continuous numeric | Passed through unscaled (tree models split on thresholds, not distances) |
| `has_gym_access` | Boolean | Passed through as 0/1 |

`handle_unknown="ignore"` on the one-hot encoder is a deliberate production-robustness choice: if a future enum value is added (e.g. a new `FitnessGoal`) without retraining, this degrades gracefully to a zero vector for that feature rather than crashing.

**35 total encoded features** after transformation (confirmed by `preprocessor.get_feature_names_out()` at training time).

---

## 4. Training pipeline

### 4.1 Split strategy

70% train / 15% validation / 15% test, both split points using `stratify=y` — essential here specifically because one class (`upper_lower_strength`) makes up under 1% of the dataset; a non-stratified split risks a test set with too few examples of it to evaluate reliably.

Actual sizes: **70,040 train / 14,960 validation / 15,000 test**.

### 4.2 Model search

`GridSearchCV` with 5-fold `StratifiedKFold` (5 folds chosen because the smallest class had 394 training examples — comfortably above the fold count), scored on `f1_macro` (not raw accuracy, so the rare classes aren't ignored in favor of optimizing for the dominant `home_bodyweight` class).

Grid searched: `n_estimators ∈ {100, 150}`, `max_depth ∈ {10, 12, 15}`, `class_weight = "balanced"` (fixed, since the class imbalance here is real and known, not something to search over).

**Winner: `n_estimators=150, max_depth=15, class_weight="balanced"`** — CV `f1_macro` 0.9891, a genuine, meaningful jump over the depth-12 (0.969) and depth-10 (0.884) candidates, not a marginal tiebreak.

### 4.3 The model-size tradeoff — a real engineering decision, not a footnote

An earlier, wider search (including `max_depth=None`, fully unconstrained trees) found a configuration scoring marginally higher on the test set (`f1_macro` 0.9958 vs. this model's 0.9865) — but produced a **241MB** `.joblib` file. That's genuinely impractical: too large to comfortably commit to a git repository, and meaningfully slower to `joblib.load()` at every process startup for a marginal accuracy gain.

This was tested directly, not assumed — several depth/estimator combinations were tried and measured for both accuracy and file size before choosing the final configuration:

| Configuration | Test accuracy | File size |
|---|---|---|
| `n_estimators=200, max_depth=None` | 0.9963 | 241.8 MB |
| `n_estimators=150, max_depth=20` | 0.9952 | 193.0 MB |
| `n_estimators=150, max_depth=15` (**shipped**) | 0.9844 | 71.0 MB |
| `n_estimators=100, max_depth=12` | 0.9713 | 20.3 MB |
| `n_estimators=100, max_depth=8` | 0.9037 | 6.2 MB |

The shipped model trades roughly 1 point of macro F1 for a **3.4× smaller** artifact compared to the unconstrained-depth version — a deliberate, documented engineering tradeoff, not a default left unexamined.

---

## 5. Evaluation results

See `ml/models/evaluation_report.md` for the complete writeup with the full confusion matrix and feature importance table. Summary:

| Metric | Score |
|---|---|
| Accuracy | 0.9844 |
| Precision (macro) | 0.9826 |
| Recall (macro) | 0.9911 |
| F1 (macro) | 0.9865 |

**The one meaningful error pattern:** 200 of 7,966 true `home_bodyweight` test cases (2.5%) predicted as `push_pull_legs`, plus 19 as `upper_lower`. This has a plausible explanation, not a modeling failure: `home_bodyweight` is eligible across the widest day range (1–7) of any split with no hard equipment requirement, so it legitimately overlaps in feature space with profiles that also have real equipment — the rule engine's own scores for these edge cases can be genuinely close, and the model's occasional disagreement reflects real ambiguity in the underlying decision boundary.

### 5.1 The `diet_preference` question — answered empirically

`docs/ML_ARCHITECTURE.md` §2.2 flagged `diet_preference` as a feature with no obvious causal link to workout-split selection, recommending it be evaluated via feature importance rather than assumed either way.

**Result:** all three `diet_preference` one-hot columns rank in the bottom third of all 35 features, contributing a combined ~0.6% of total importance — essentially nothing. This matches the rule engine's own source code exactly: no rule in `recommendation_rules.py` reads `diet_preference` at all. The model correctly learned to ignore a feature the real system never used, which is itself evidence the model is faithfully approximating the real logic rather than fitting noise.

`gender` and `bmi_category` show the same pattern (bottom-ranked, near-zero importance) — also consistent with the rule engine's own code, where `recovery_rule`'s docstring explicitly states there's no legitimate exercise-science basis for gender to determine split structure.

**What actually drives predictions:** `workout_days_per_week` alone accounts for 29% of total importance — by far the single most decisive feature, which matches every split's hard `min_days`/`max_days` eligibility gate being the first thing that can disqualify a candidate entirely. Experience level and equipment availability are the next tier, matching the rule engine's two hardest constraints (equipment is a disqualifier; experience heavily weights scoring).

---

## 6. Model export

`model.joblib` and `preprocessor.joblib` are saved **separately** (not bundled into one object) in this phase, matching the phase's explicit output requirements. `metadata.json` records training timestamp, hyperparameters, dataset size, observed classes (5, not 6 — see §2.4), and the full feature importance ranking, so anyone loading this model later has the full provenance without needing to re-read this document.

**Note for the future integration phase:** `docs/ML_ARCHITECTURE.md` §5.6 recommends bundling model + preprocessor + feature names into a single `.joblib` for production inference, specifically to prevent the two from silently drifting out of sync. This phase exports them separately per the explicit output spec; the integration phase should re-bundle them before shipping to `app/ml/registry.py`.

---

## 7. Future improvements

1. ~~**Fix the `bro_split` dead-code bug** in the rule engine itself (§2.4)~~ — **done**, in `recommendation_rules.py` (a single scoring value was raised so `bro_split` genuinely wins at its real-world niche: advanced experience, 5 days/week, full gym, across every fitness goal — verified with dedicated regression tests in `tests/test_workout_recommendation_service.py`). ~~**Not yet done:** regenerating this dataset and retraining against the fixed rule engine~~ — **also done**: this is v2, trained on the regenerated dataset. See `ml/models/MODEL_COMPARISON.md` for the complete before/after comparison.
2. **Correlate more features during generation** — currently only weight is conditioned on height/BMI; a more sophisticated generator could also correlate `workout_experience` with `age` (more experienced users skew slightly older in reality) and `fitness_goal` with `activity_level`.
3. **Drop or de-weight near-zero-importance features** (`diet_preference`, `gender`, `bmi_category`) in a future retrain — empirically justified by both v1's and v2's feature importance results (consistently near the bottom in both), would slightly reduce encoded dimensionality and model size with likely negligible accuracy impact.
4. **Re-bundle model + preprocessor together** (see `docs/ML_INTEGRATION.md` §3 — noted there as not yet done).
5. **The real long-term goal, per `docs/ML_ARCHITECTURE.md` §7:** retrain on real user behavioral outcome data (did a user actually stick with their recommended plan, based on `WorkoutSession` completion/streak data) once enough of it accumulates — this is the only way a future model can genuinely exceed the rule engine's own accuracy ceiling, rather than just imitating it as this model still does.
6. **Try XGBoost/LightGBM once real outcome data exists** — `docs/ML_ARCHITECTURE.md` §4.2 explicitly deferred this comparison until the labeling problem changes from "imitate the rule engine" to "predict a real, independent outcome," where a stronger algorithm's edge on complex feature interactions could plausibly matter.
7. **Automate rule-engine/ML-model drift detection** — this retrain was only triggered because someone was actively aware both the rule engine and the model existed and needed to stay in sync. A production `model_predictions` log (per `docs/ML_ARCHITECTURE.md` §7) recording both engines' outputs side-by-side would catch this kind of drift automatically in the future.
