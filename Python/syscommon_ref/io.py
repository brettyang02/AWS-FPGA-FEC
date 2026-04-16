
from pathlib import Path
from typing import List, Iterable

def read_bit_file(path: str) -> List[int]:
    """Reads a text file with one bit per line (0/1). Ignores blank lines and comments."""
    bits = []
    for line in Path(path).read_text().splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("//"):
            continue
        if s not in ("0","1"):
            # allow whitespace-separated sequences too
            for tok in s.split():
                if tok in ("0","1"):
                    bits.append(int(tok))
            continue
        bits.append(int(s))
    return bits

def read_int_file(path: str) -> List[int]:
    """Reads a text file and extracts all integers. Ignores comments and non-numeric text."""
    numbers = []
    
    # read_text().splitlines() handles the file opening and line breaks
    for line in Path(path).read_text().splitlines():
        # Remove comments (standardize to #)
        clean_line = line.split('#')[0].split('//')[0].strip()
        
        if not clean_line:
            continue
            
        # Split by whitespace to catch multiple numbers on one line
        for token in clean_line.split():
            try:
                # Convert to integer (handles "12", "84", etc.)
                numbers.append(int(token))
            except ValueError:
                # This skips tokens that aren't numbers (like "Error" or "??")
                continue
                
    return numbers

def write_bit_file(path: str, bits: Iterable[int]) -> None:
    Path(path).write_text("".join(f"{int(b)}\n" for b in bits))

def align_streams(a: list, b: list, search_window: int = 256) -> int:
    """Find a small offset that best aligns stream b to a by minimizing mismatches.
    Returns offset k such that b[k:] aligns to a[:]. If no improvement found, returns 0.
    """
    best_k = 0
    best_err = None
    N = min(len(a), len(b))
    for k in range(min(search_window, N)):
        mism = sum((a[i] ^ b[i+k]) for i in range(N-k))
        if best_err is None or mism < best_err:
            best_err = mism
            best_k = k
    return best_k
