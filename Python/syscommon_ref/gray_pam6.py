# Auto-generated from gray_codec_PAM6.sv
from dataclasses import dataclass, field
from typing import List, Tuple, Iterable, Optional


# Exact mapping tables extracted from RTL
ENCODE_TABLE = {'00000': (0, 0), '00100': (0, 1), '00101': (0, 2), '10101': (0, 3), '10100': (0, 4), '10000': (0, 5), '00001': (1, 0), '00111': (1, 2), '10111': (1, 3), '10001': (1, 5), '00011': (2, 0), '00010': (2, 1), '00110': (2, 2), '10110': (2, 3), '10010': (2, 4), '10011': (2, 5), '01011': (3, 0), '01010': (3, 1), '01110': (3, 2), '11110': (3, 3), '11010': (3, 4), '11011': (3, 5), '01001': (4, 0), '01111': (4, 2), '11111': (4, 3), '11001': (4, 5), '01000': (5, 0), '01100': (5, 1), '01101': (5, 2), '11101': (5, 3), '11100': (5, 4), '11000': (5, 5)}
DECODE_TABLE = {(0, 0): '00000', (0, 1): '00100', (0, 2): '00101', (0, 3): '10101', (0, 4): '10100', (0, 5): '10000', (1, 0): '00001', (1, 2): '00111', (1, 3): '10111', (1, 5): '10001', (2, 0): '00011', (2, 1): '00010', (2, 2): '00110', (2, 3): '10110', (2, 4): '10010', (2, 5): '10011', (3, 0): '01011', (3, 1): '01010', (3, 2): '01110', (3, 3): '11110', (3, 4): '11010', (3, 5): '11011', (4, 0): '01001', (4, 2): '01111', (4, 3): '11111', (4, 5): '11001', (5, 0): '01000', (5, 1): '01100', (5, 2): '01101', (5, 3): '11101', (5, 4): '11100', (5, 5): '11000'}

@dataclass
class GrayEncodePAM6:
    """Consumes serial bits and emits (I,Q) symbol stream alternating per RTL."""
    phaseI: bool = True
    _shift: int = 0
    _count: int = 0
    _pending_pair: Optional[Tuple[int,int]] = None


    def push_bit(self, b: int) -> List[Tuple[int,int]]:
        """Feed one bit. Returns zero or more emitted (I,Q) pairs as a list of tuples (one pair => [(I,Q)])."""
        b = 1 if b else 0
        self._shift = ((self._shift & 0b1111) << 1) | b  # 5-bit shift reg, MSB-first per RTL table usage
        self._count += 1
        out = []
        if self._count == 5:
            # Look up (I,Q)
            bits = f"{self._shift:05b}"
            I,Q = ENCODE_TABLE[bits]
            # Per RTL, it outputs I then Q in consecutive cycles
            out.append((I,Q))
            self._shift = 0
            self._count = 0
        return out

    def encode(self, bits: Iterable[int]) -> List[int]:
        """Convenience: return a flat symbol stream [I0,Q0,I1,Q1,...]."""
        syms: List[int] = []
        for b in bits:
            pairs = self.push_bit(b)
            for I,Q in pairs:
                syms.extend([I,Q])
        return syms

@dataclass
class GrayDecodePAM6:
    """Consumes symbol stream (I,Q interleaved) and reconstructs 5-bit chunks -> serial bits (MSB first)."""
    phaseI: bool = True
    _I: int = 0
    _collect_q: bool = False

    def push_symbol(self, s: int) -> List[int]:
        """Feed one 3-bit symbol. Returns 0 or 5 output bits when a (I,Q) pair is complete."""
        out: List[int] = []
        if self.phaseI:
            self._I = s & 7
            self.phaseI = False
        else:
            Q = s & 7
            self.phaseI = True
            bits = DECODE_TABLE.get((self._I, Q))
            if bits is None:
                # print(f"⚠️ Invalid Gray pair {(self._I, Q)}, forcing zeros")
                bits = "00000"
            out = [int(c) for c in bits]
        return out

    def decode(self, syms: Iterable[int]) -> List[int]:
        out: List[int] = []
        for s in syms:
            out.extend(self.push_symbol(int(s)))
        return out
