from dataclasses import dataclass
from typing import List

def wrap(val, bits):
    mask = (1 << bits) - 1
    val &= mask
    if val & (1 << (bits - 1)):
        val -= (1 << bits)
    return val

def wrap_u(val, bits):
    return val & ((1 << bits) - 1)

def verilog_trunc(x):
    """Match Verilog constant truncation (toward zero)."""
    return int(x)

@dataclass
class MLSEPAM6:
    SYMBOL_SEPARATION: int = 48
    SIGNAL_RESOLUTION: int = 8
    ALPHA: float = 0.1
    TRACEBACK: int = 10
    METRIC_RESOLUTION: int = 20

    def __post_init__(self):
        self.delay = 0
        self.valid = 0
        self.symbol_out = 0

        self.survivor_metrics = [0] * 6
        self.prev_state = [0] * 6

        # survivors[state][0] == oldest symbol
        self.survivors = [[0]*self.TRACEBACK for _ in range(6)]

        self._build_y_tables()

    def _build_y_tables(self):
        S = self.SYMBOL_SEPARATION
        A = self.ALPHA * S

        # Reordered to match the RTL output
        base = [-2.5, -1.5, -0.5, 0.5, 1.5, 2.5]
        tap  = [2.5, 1.5, 0.5, -0.5, -1.5, -2.5]

        # Reorder the inner loop to match RTL dump
        self.y = []
        for b in base:
            row = []
            for t in reversed(tap):
                v = int(b*S + A*t)
                row.append(wrap(v, self.SIGNAL_RESOLUTION))
            self.y.append(row)

        # --- dump y0..y5 for debug ---
        # with open("debug_dump_build_y_tables.txt", "w") as f:
        #     for i, row in enumerate(self.y):
        #         f.write(f"{i}: " + " ".join(str(v) for v in row) + "\n")

    def step(self, signal_in: int, signal_in_valid: int, rstn: int, dump_file="debug_dump_step.txt"):
        if not hasattr(self, "_dump_count"):
            self._dump_count = 0

        if not rstn:
            self.__post_init__()
            self._dump_count = 0
            return 0, 0

        self.valid = 0

        if not signal_in_valid:
            return self.symbol_out, self.valid

        # --- Compute branch metrics ---
        e = [[0]*6 for _ in range(6)]
        for s in range(6):
            for p in range(6):
                d = signal_in - self.y[s][p]
                e[s][p] = d*d

        # --- Save current survivors BEFORE update for output ---
        old_survivors = [row[:] for row in self.survivors]

        # --- Compute new metrics and prev_state ---
        new_metrics = [0]*6
        new_prev = [0]*6
        for s in range(6):
            candidates = [e[s][p] + self.survivor_metrics[p] for p in range(6)]
            min_val = candidates[0]
            min_idx = 0
            for i in range(1,6):
                if candidates[i] < min_val:
                    min_val = candidates[i]
                    min_idx = i
            new_metrics[s] = min_val
            new_prev[s] = min_idx

        # # debug
        # if self.delay < 10:
        #     current_min_state = new_metrics.index(min(new_metrics))
        #     print(f"Step {self.delay + 1}: min_state={current_min_state}")

        # --- Update survivor paths ---
        new_survivors = []
        for s in range(6):
            src = new_prev[s]
            new_survivors.append(self.survivors[src][1:] + [s])

        # --- Delay logic: output only after TRACEBACK ---
        if self.delay > self.TRACEBACK: # FIXME: self.delay >= self.TRACEBACK works with .noise_in(0)
            # Select survivor with minimum metric
            min_metric = new_metrics[0]
            min_state = 0
            for i in range(1,6):
                if new_metrics[i] < min_metric:
                    min_metric = new_metrics[i]
                    min_state = i

            # --- OUTPUT: take from old survivors, not new_survivors ---
            self.symbol_out = old_survivors[min_state][0]
            self.valid = 1

        # --- Update internal state ---
        self.survivor_metrics = new_metrics
        self.prev_state = new_prev
        self.survivors = new_survivors
        self.delay += 1

        # --- Optional debug dump ---
        if self._dump_count < 10:
            # with open(dump_file, "a") as f:
            #     f.write(f"Step {self._dump_count} (delay {self.delay}): signal_in={signal_in}, survivor_metrics={self.survivor_metrics}, prev_state={self.prev_state}, symbol_out={self.symbol_out}, valid={self.valid}\n")
            self._dump_count += 1

        return self.symbol_out, self.valid

