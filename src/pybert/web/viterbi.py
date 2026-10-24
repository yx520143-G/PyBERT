"""Bounded Native ISI decoding records and read-only trellis views."""

MAX_STATES = 256
MAX_STATE_SAMPLES = 2_000_000
MAX_DENSE_WORK = 25_000_000
MAX_TIME_SAMPLES = 2_000_000


def plan(config, *, execution=False):
    """Bound the existing dense decoder; never change N or the analysis window."""
    n = config["rx_viterbi_symbols"]
    if type(n) not in (int, float) or int(n) != n or n < 1:
        raise ValueError("rx_viterbi_symbols: positive integer symbol count required.")
    levels = {"NRZ": 2, "PAM-4": 4, "Duo-binary": 3}[config["mod_type"]]
    samples = config["eye_bits"] // (2 if config["mod_type"] == "PAM-4" else 1)
    # Avoid constructing an unbounded integer for an untrusted depth.
    states = levels ** int(n) if n <= 16 else None
    row = {"N": int(n), "L": levels, "states": states, "samples_upper_bound": samples,
           "max_states": MAX_STATES, "max_state_samples": MAX_STATE_SAMPLES,
           "max_dense_work": MAX_DENSE_WORK, "max_time_samples": MAX_TIME_SAMPLES}
    if not config["rx_use_viterbi"]:
        return {**row, "availability": "disabled"}
    reason = None
    if states is None or states > MAX_STATES:
        reason = "state count exceeds 256"
    elif samples * states > MAX_STATE_SAMPLES or samples * states * states > MAX_DENSE_WORK:
        reason = "full sample/state dense-work budget exceeded"
    elif config["nbits"] // (2 if levels == 4 else 1) * config["nspui"] > MAX_TIME_SAMPLES:
        reason = "native time grid exceeds 2,000,000 samples"
    elif samples < max(2, n):
        reason = "insufficient full analysis samples for native decoder/trellis"
    elif states < 3:
        reason = "native trellis producer requires at least three states"
    if reason and execution:
        raise ValueError(f"viterbi_budget_or_native_limit: {reason}; input retained, no reduction/fallback.")
    return {**row, "availability": "blocked" if reason else "available", "reason": reason}
