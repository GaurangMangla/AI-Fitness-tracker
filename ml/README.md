# ML

This folder is the boundary between **training** (done offline, in Google
Colab) and **inference** (the backend loading a finished artifact). The
backend never trains anything — it only loads a .joblib file.
ml/
├── notebooks/   generate_dataset.py + train_model.ipynb
├── data/        dataset.csv — 100,000 synthetic users, labeled by the real rule engine
├── models/      model.joblib, preprocessor.joblib, evaluation_report.md, metadata.json
└── ML_TRAINING.md   full writeup: dataset generation, training pipeline, evaluation, and a
real bug discovered in the rule engine along the way

See [ML_TRAINING.md](ML_TRAINING.md) for the complete story, and
[../docs/ML_ARCHITECTURE.md](../docs/ML_ARCHITECTURE.md) for the planned
backend integration (not yet implemented — the rule engine is still the
only active recommendation engine in production).
