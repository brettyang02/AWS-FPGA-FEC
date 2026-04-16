from dataclasses import dataclass
from typing import Iterable, List

def twos_complement_wrap(val: int, bits: int) -> int:
    """Wrap integer to signed two's complement with given bit width."""
    mask = (1 << bits) - 1
    val &= mask
    if val & (1 << (bits - 1)):
        val -= (1 << bits)
    return val


def rtl_quantize(val: float, bits: int) -> int:
    """
    Emulate Verilog constant folding:
    - evaluate expression
    - convert to integer
    - truncate toward zero
    - wrap to signed N bits
    """
    return twos_complement_wrap(int(val), bits)


def make_rtl_luts(symbol_sep: int, alpha: float, bits: int):
    base = [-2.5, -1.5, -0.5, 0.5, 1.5, 2.5]

    Y = [[0] * 6 for _ in range(6)]

    for nxt in range(6):
        for prv in range(6):
            raw = symbol_sep * base[nxt] + alpha * symbol_sep * base[prv]
            Y[nxt][prv] = rtl_quantize(raw, bits)

    return Y


@dataclass
class ISIChannelOneTapPAM6:
    symbol_sep: int = 48
    alpha: float = 0.5
    signal_resolution: int = 8
    prev_symbol: int = 2  # RTL reset

    def __post_init__(self):
        self.Y = make_rtl_luts(
            self.symbol_sep,
            self.alpha,
            self.signal_resolution
        )

    def process(self, symbols: Iterable[int], valids: Iterable[int] = None) -> List[int]:
        """
        symbols: PAM6 symbol stream
        valids: optional symbol_in_valid stream (1/0)
        """
        out: List[int] = []

        if valids is None:
            valids = [1] * len(list(symbols))

        for s, v in zip(symbols, valids):
            s = int(s) & 7  # match RTL bit width

            if v:
                y = self.Y[s][self.prev_symbol]
                out.append(y)
                self.prev_symbol = s
            else:
                out.append(None)  # no output when signal_out_valid=0

        return out
