from dataclasses import dataclass
from typing import Iterable, List, Tuple

@dataclass
class Noise:
    """Replicates RTL random_noise + noise_adder using urng_64 sequence."""
    mem_file: str = "Python/noise15dB.mem"
    signal_resolution: int = 8
    seed0: int = 0x1391A0B350391A0B
    seed1: int = 0x50391A0B0392A7D3
    seed2: int = 0x0392A7D350391A0B

    def __post_init__(self):
        self.urng = URNG64(self.seed0, self.seed1, self.seed2)
        self.prob = []
        for line in open(self.mem_file):
            s = line.strip()
            if not s or s.startswith("//"):
                continue
            self.prob.append(int(s, 16))
        self.prob.sort()
        self.RMAX = (1 << 64) - 1

    def _next_noise(self) -> int:
        """Generate one signed noise sample like RTL random_noise.noise_out"""
        rnd = self.urng.step()
        # Search smallest i where rnd <= probability[i]
        mag = 63
        for i, p in enumerate(self.prob):
            if rnd <= p:
                mag = i
                break
        sign = 1 if (rnd & 1) == 0 else -1
        return sign * mag

    def add_noise(self, signal: Iterable[float]) -> Tuple[List[float], List[float]]:
        noise_vals, noisy_out = [], []
        for x in signal:
            n = self._next_noise()
            # mimic noise_adder: divide by 2 and saturate
            noisy = x + n / 2
            noise_vals.append(n)
            noisy_out.append(noisy)
        return noise_vals, noisy_out

class URNG64:
    """Python clone of urng_64.sv"""
    def __init__(self,
                 seed0=0x1391A0B350391A0B,
                 seed1=0x50391A0B0392A7D3,
                 seed2=0x0392A7D350391A0B):
        self.z1 = seed0 & ((1<<64)-1)
        self.z2 = seed1 & ((1<<64)-1)
        self.z3 = seed2 & ((1<<64)-1)

    def step(self) -> int:
        """Generate next 64-bit random value (same bit ops as RTL)"""
        def mask64(x): return x & ((1<<64)-1)
        z1_next = mask64(((self.z1 >> 1) & ((1<<39)-1)) |
                         (((self.z1 >> 34) ^ (self.z1 >> 39)) << 39))
        z2_next = mask64(((self.z2 >> 6) & ((1<<50)-1)) |
                         (((self.z2 >> 26) ^ (self.z2 >> 45)) << 45))
        z3_next = mask64(((self.z3 >> 9) & ((1<<56)-1)) |
                         (((self.z3 >> 24) ^ (self.z3 >> 48)) << 48))
        self.z1, self.z2, self.z3 = z1_next, z2_next, z3_next
        return (z1_next ^ z2_next ^ z3_next) & ((1<<64)-1)
