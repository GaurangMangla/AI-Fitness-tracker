# ML inference

Loads the exported `.joblib` workout-recommendation model and exposes a typed
`predict(features) -> recommendation` function for the workout service to call.
Training happens entirely outside the app, in the Colab notebook under
`/ml/notebooks` at the repo root — this module only ever reads a finished
artifact from `/ml/models`, it never trains anything.

Empty for now — populated when the Machine Learning feature is built (after
the rule-based workout generator is in place).
