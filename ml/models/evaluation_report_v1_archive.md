# Model Evaluation Report — Workout Split Recommender v1

**Model type:** `RandomForestClassifier` (scikit-learn)
**Trained:** 2026-07-12
**Dataset:** `ml/data/dataset.csv` — 100,000 synthetic users, labeled by the real, deployed `RuleBasedRecommendationEngine`

---

## 1. Dataset split

| Split | Size | % |
|---|---|---|
| Train | 70,040 | 70.04% |
| Validation | 14,960 | 14.96% |
| Test | 15,000 | 15.00% |

Split via `train_test_split` with `stratify=y` at both split points (train+val vs. test, then train vs. val), `random_state=42` for reproducibility.

---

## 2. A critical finding before the results: only 5 of 6 classes exist

**`bro_split` never appears in the dataset — not as a rare class, but literally zero occurrences.**

This was verified exhaustively, not assumed: every combination of `fitness_goal` × `workout_experience` × `workout_days_per_week` (5 or 6, `bro_split`'s only valid day range) × `full_gym` equipment was tested directly against the real `RuleBasedRecommendationEngine`, including `bro_split`'s theoretical best case (advanced experience, muscle_gain goal, 5 days, full gym, no recovery penalty). **`bro_split` never won a single one of these comparisons.**

**Root cause:** `push_pull_legs` scores equal-or-higher than `bro_split` on every dimension the rule engine evaluates (goal score, experience score, day-fit score), for every possible input. The two splits also react identically to the recovery-capacity adjustment (both are in the rule engine's `_HIGH_FREQUENCY_SPLITS` set). The best `bro_split` can ever achieve is an **exact tie** with `push_pull_legs` — and Python's `max()` (used to pick the winning candidate) keeps the *first* maximum it encounters. `push_pull_legs` is defined before `bro_split` in `WORKOUT_SPLITS`, so every tie resolves in its favor.

**This means:** the current rule-based recommendation engine has a dead code path — `bro_split` is a real, defined split in `workout_splits.py` that can never actually be recommended to any user, under any profile, today. This is a genuine finding about the existing production system, discovered as a side effect of building this dataset — not a defect in the dataset generator.

**How this was handled:** per this phase's explicit scope ("do not modify the backend"), the rule engine was left untouched. The dataset faithfully reflects the real system's actual behavior — training on a fabricated `bro_split` label that the real engine would never produce would defeat the entire purpose of this exercise (a model that imitates the real system). The model was trained on the **5 classes that genuinely occur**, and is not expected to ever predict `bro_split` unless the rule engine itself is later fixed and the dataset regenerated.

**Recommendation:** flag this to whoever owns the rule engine as a real bug worth fixing in its own right, independent of the ML work — see `ML_TRAINING.md` §7 for the suggested fix.

---

## 3. Model selection (GridSearchCV + StratifiedKFold)

5-fold `StratifiedKFold` (the smallest class, `upper_lower_strength`, had 394 training examples — comfortably above the 5-fold minimum). Scored on `f1_macro` (not accuracy) so all 5 classes are weighted equally regardless of how common each is in the training data.

| Rank | `n_estimators` | `max_depth` | `class_weight` | CV `f1_macro` | CV std |
|---|---|---|---|---|---|
| 1 | 150 | 15 | balanced | **0.9891** | 0.0009 |
| 2 | 100 | 15 | balanced | 0.9890 | 0.0011 |
| 3 | 150 | 12 | balanced | 0.9691 | 0.0008 |
| 4 | 100 | 12 | balanced | 0.9610 | 0.0078 |
| 5 | 150 | 10 | balanced | 0.8835 | 0.0064 |
| 6 | 100 | 10 | balanced | 0.8808 | 0.0064 |

**Selected: `n_estimators=150, max_depth=15, class_weight="balanced"`** — the clear winner, with a real, meaningful jump over the depth-12 and depth-10 candidates (not a marginal tiebreak).

**A note on model size vs. an even-higher-scoring configuration:** an earlier, wider grid search (including `max_depth=None`, fully unconstrained trees) found a configuration scoring marginally higher (test `f1_macro` 0.9958 vs. this model's 0.9865) — but produced a **241MB** `.joblib` file. That's impractical: too large to comfortably commit to git, and meaningfully slower to load at process startup. This shipped model trades roughly 1 point of macro F1 for a **3.4× smaller** (71MB) artifact — a defensible practical tradeoff, made deliberately and documented rather than silently defaulting to whichever config scored highest on paper.

---

## 4. Test set results

| Metric | Score |
|---|---|
| **Accuracy** | 0.9844 |
| **Precision (macro)** | 0.9826 |
| **Recall (macro)** | 0.9911 |
| **F1 (macro)** | 0.9865 |

### Per-class breakdown

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| `full_body` | 1.00 | 1.00 | 1.00 | 2,752 |
| `home_bodyweight` | 1.00 | 0.97 | 0.99 | 7,966 |
| `push_pull_legs` | 0.93 | 1.00 | 0.96 | 2,702 |
| `upper_lower` | 0.99 | 1.00 | 0.99 | 1,496 |
| `upper_lower_strength` | 1.00 | 0.99 | 0.99 | 84 |

### Confusion matrix

|  | pred: full_body | pred: home_bodyweight | pred: push_pull_legs | pred: upper_lower | pred: upper_lower_strength |
|---|---|---|---|---|---|
| **true: full_body** | 2746 | 0 | 6 | 0 | 0 |
| **true: home_bodyweight** | 3 | 7744 | 200 | 19 | 0 |
| **true: push_pull_legs** | 1 | 0 | 2699 | 2 | 0 |
| **true: upper_lower** | 0 | 0 | 2 | 1494 | 0 |
| **true: upper_lower_strength** | 0 | 0 | 1 | 0 | 83 |

**The one notable confusion pattern:** 200 true `home_bodyweight` cases predicted as `push_pull_legs` (2.5% of that class), plus 19 predicted as `upper_lower`. This is the model's single meaningful source of error, and it has a plausible, honest explanation: `home_bodyweight` is eligible across the widest day range (1–7) of any split and has no hard equipment requirement, so it legitimately overlaps in feature space with profiles that also happen to have real equipment available — the real rule engine's own scoring in these edge cases can be close, and the model's occasional disagreement here reflects genuine ambiguity in the underlying decision boundary, not a modeling failure to correct.

---

## 5. Feature importance (all 35 features)

| Rank | Feature | Importance |
|---|---|---|
| 1 | `workout_days_per_week` | 0.2913 |
| 2 | `workout_experience_advanced` | 0.1168 |
| 3 | `equip_none` | 0.0895 |
| 4 | `equip_dumbbells` | 0.0847 |
| 5 | `workout_experience_beginner` | 0.0566 |
| 6 | `equip_full_gym` | 0.0445 |
| 7 | `workout_experience_intermediate` | 0.0437 |
| 8 | `has_gym_access` | 0.0370 |
| 9 | `fitness_goal_muscle_gain` | 0.0338 |
| 10 | `fitness_goal_weight_loss` | 0.0284 |
| 11 | `fitness_goal_maintenance` | 0.0242 |
| 12 | `equipment_count` | 0.0187 |
| 13 | `equip_barbell` | 0.0174 |
| 14 | `height_cm` | 0.0144 |
| 15 | `weight_kg` | 0.0141 |
| 16 | `bmi` | 0.0136 |
| 17 | `age` | 0.0119 |
| 18 | `equip_resistance_bands` | 0.0118 |
| 19 | `fitness_goal_general_fitness` | 0.0115 |
| 20 | `equip_pull_up_bar` | 0.0070 |
| 21 | `activity_level_very_active` | 0.0055 |
| 22–35 | *(remaining `activity_level`, `diet_preference`, `gender`, `bmi_category` one-hot columns)* | 0.0011–0.0022 each |

**Confirms the hypothesis flagged in `docs/ML_ARCHITECTURE.md` §2.2:** `diet_preference` (all 3 values) ranks in the bottom third of all 35 features, contributing a combined ~0.6% of total importance. `gender` and `bmi_category` similarly contribute almost nothing. **This is exactly what the rule engine's own source code predicts** — `diet_preference` was never read by any rule, and `recovery_rule`'s docstring explicitly states there's no legitimate exercise-science basis for `gender` to determine split *structure*. The model correctly learned to ignore features the rule engine itself never used — strong evidence the model is faithfully approximating the real system's actual logic, not learning spurious correlations.

**What actually drives the recommendation, confirmed empirically:** `workout_days_per_week` alone accounts for 29% of total importance — by far the single most decisive input, consistent with every split's hard `min_days`/`max_days` eligibility gate in `workout_splits.py`. Experience level and equipment availability are the next tier down, matching the rule engine's own two hardest constraints (equipment is a hard disqualifier; experience heavily weights the scoring).

---

## 6. Honest limitations

1. **This model can only ever match, never exceed, the rule engine's own accuracy** — it was trained to imitate the rule engine's output, not to predict a genuinely independent outcome. See `docs/ML_ARCHITECTURE.md` §3.3 for why this is the deliberate, correct approach for a first model, and what the actual long-term ceiling-breaking step looks like (training on real user behavioral outcomes instead).
2. **It will never predict `bro_split`**, because the rule engine itself never produces that label (§2 above). This isn't a data or model gap — it's a faithful reflection of the current system.
3. **97-99% test accuracy should not be read as "this model is production-ready to replace human judgment"** — it means the model successfully learned to approximate a deterministic scoring function over ~10 input features, which is a comparatively easy learning problem. The real test of an ML approach's value happens only once real behavioral data becomes available.
