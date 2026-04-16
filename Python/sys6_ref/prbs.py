from dataclasses import dataclass

@dataclass
# class PRBS63:
#     """
#     RTL-equivalent PRBS-63 (x^63 + x^62 + 1)
#     Matches:
#         assign sr_in = sr[62] ^ sr[61];
#         sr <= {sr[61:0], sr_in};
#         data <= sr_in;
#     The RTL 'data' is the feedback bit (new input), but observed polarity differs.
#     So we return the **inverted feedback bit** to match RTL text dump.
#     """
#     seed: int = 0x2645841236254785
#     n_pcs: int = 1

#     def __post_init__(self):
#         if self.seed == 0 or self.seed >> 63:
#             raise ValueError("seed must be a non-zero 63-bit value")
#         self.sr = self.seed & ((1 << 63) - 1)

#     def step(self) -> int:
#         b62 = (self.sr >> 62) & 1
#         b61 = (self.sr >> 61) & 1
#         sr_in = b62 ^ b61
#         self.sr = ((self.sr << 1) & ((1 << 63) - 1)) | sr_in
#         return sr_in    # RTL uses sr_in directly as data

#     def generate(self, n_bits: int):
#         for _ in range(n_bits):
#             yield self.step()
class PRBS63:
    """
    Python reference for the prbs63 Verilog module.
    Implements the polynomial x^63 + x^62 + 1.
    """
    def __init__(self, seed=0x0000000000000001):
        # The RTL uses a 63-bit shift register 
        # Ensure the seed is masked to 63 bits [cite: 90]
        self.state = seed & 0x7FFFFFFFFFFFFFFF

    def step(self):
        """
        Calculates the next bit and updates the internal state.
        Matches the RTL: assign sr_in = (sr[62]^sr[61]) 
        """
        # Extract bits at indices 62 and 61 (0-indexed)
        bit62 = (self.state >> 62) & 1
        bit61 = (self.state >> 61) & 1
        
        # XOR sum for the input bit [cite: 89, 133]
        sr_in = bit62 ^ bit61
        
        # Shift left and insert the new bit at the LSB [cite: 91, 149]
        # Masking to 63 bits to mirror the 'reg [62:0] sr' 
        self.state = ((self.state << 1) | sr_in) & 0x7FFFFFFFFFFFFFFF
        
        return sr_in

    def generate(self, length):
        """Generates a list of bits of a specific length."""
        return [self.step() for _ in range(length)]

    def reset(self, seed=0x0000000000000001):
        """Resets the state to the seed value[cite: 90, 108]."""
        self.state = seed & 0x7FFFFFFFFFFFFFFF
