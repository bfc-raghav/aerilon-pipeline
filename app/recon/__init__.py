"""Problem 3: Old Port District route reconnaissance.
detector -> safety -> (LED ring, Arduino display, UDP telemetry)
Every module is import-safe: hardware/network acquired lazily, with
simulated fallbacks, so the SAME code runs in CI, on a laptop, on the Pi."""
