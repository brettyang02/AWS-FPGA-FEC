from dataclasses import dataclass
from typing import Iterable, List, Tuple

@dataclass
class Noise:
    """Replicates RTL random_noise + noise_adder using urng_64 sequence."""
    mem_file: str = "Python/noise15dB.mem"
    signal_resolution: int = 8
    """
    Verilog: 
    RANDOM_64[3]	64'h2629488426294884	
    RANDOM_64[2]	64'h588f503226294884	
    RANDOM_64[1]	64'h2629188426294884	
    RANDOM_64[0]	64'h2645841236254785
    """
    seed0: int = 0x2629188426294884  # RANDOM_64[1]
    seed1: int = 0x588f503226294884  # RANDOM_64[2]
    seed2: int = 0x2629488426294884  # RANDOM_64[3]
    

    def __post_init__(self):
        self.urng = URNG64(self.seed0, self.seed1, self.seed2)
        # print(f"urng seed0: 0x{self.seed0:016X}, seed1: 0x{self.seed1:016X}, seed2: 0x{self.seed0:016X} ") # debug: check seed
        self.prob = []
        for line in open(self.mem_file):
            s = line.strip()
            if not s or s.startswith("//"):
                continue
            self.prob.append(int(s, 16))
        self.prob.sort()
        self.RMAX = (1 << 64) - 1

        # Initialize the magnitude register to match the RTL's reset state
        self._noise_mag_reg = 0

    def _next_noise_cycle_accurate(self) -> int:
        """Generate one signed noise sample like RTL random_noise.noise_out"""
        rnd = self.urng.step()
        # Search smallest i where rnd <= probability[i]
        mag = 63
        for i, p in enumerate(self.prob):
            if rnd <= p:
                mag = i
                break
        # sign = 1 if (rnd & 1) == 0 else -1
        multiplier = -1 if (rnd & 1) else 1
        # noise_out = multiplier * mag
        noise_out = self._noise_mag_reg * multiplier
        self._noise_mag_reg = mag
        # return sign * mag, rnd
        return noise_out, rnd

    def _noise_adder_logic(self, signal_val: int, noise_val: int) -> int:
        """
        Replicates the Verilog noise_adder module logic:
        1. Signed addition (9-bit).
        2. Saturation logic based on sum[8] and sum[7].
        3. sum_shift bit-discarding.
        """
        res = self.signal_resolution # 8
        
        # RTL: assign sum = signal_in + noise_in;
        raw_sum = int(signal_val) + noise_val
        
        # 1. Capture the 9-bit bitmask to mimic sum[8:0]
        mask_9bit = (1 << (res + 1)) - 1 # 0x1FF
        sum_bits_unsigned = raw_sum & mask_9bit
        
        # 2. Convert unsigned 9-bit mask to signed to match 'wire signed [8:0] sum'
        # This ensures -5 stays -5 in your debug prints instead of 507
        if sum_bits_unsigned & (1 << res): # Check bit 8 (sign bit)
            sum_bits_signed = sum_bits_unsigned - (1 << (res + 1))
        else:
            sum_bits_signed = sum_bits_unsigned

        # 3. Extract bits for saturation logic (sum[8] and sum[7])
        msb = (sum_bits_unsigned >> res) & 1          # sum[8]
        msb_minus_1 = (sum_bits_unsigned >> (res - 1)) & 1 # sum[7]

        max_pos = (1 << (res - 1)) - 1  # 127
        max_neg = -(1 << (res - 1))     # -128

        # 4. RTL Saturation Logic
        if msb == 0 and msb_minus_1 == 1:
            # Positive Overflow: signal_out <= 8'sb01111111
            data = max_pos
        elif msb == 1 and msb_minus_1 == 0:
            # Negative Overflow: signal_out <= 8'sb10000000
            data = max_neg
        else:
            # 5. RTL: signal_out <= {sum[8], sum[6:0]} (sum_shift)
            # This drops sum[7]
            lower_bits = sum_bits_unsigned & ((1 << (res - 1)) - 1) # sum[6:0]
            final_bits = (msb << (res - 1)) | lower_bits           # {sum[8], sum[6:0]}
            
            # Convert 8-bit result back to signed Python int
            if final_bits & (1 << (res - 1)):
                data = final_bits - (1 << res)
            else:
                data = final_bits

        return data, raw_sum, sum_bits_signed

    # def add_noise(self, signal: Iterable[float]) -> Tuple[List[float], List[float]]:
    #     noise_vals, noisy_out = [], []
    #     urng_rnd_vals, raw_sum_vals, sum_bits_vals = [], [], []
        
    #     for x in signal:
    #         n, urng_rnd = self._next_noise()

    #         # mimic noise_adder: divide by 2 and saturate
    #         # noisy = x + n / 2
    #         noisy, raw_sum, sum_bits = self._noise_adder_logic(x, n) # signal, noise

    #         # imtermediate signals
    #         urng_rnd_vals.append(urng_rnd)
    #         raw_sum_vals.append(raw_sum)
    #         sum_bits_vals.append(sum_bits)

    #         # noise, signal with noise 
    #         noise_vals.append(n)
    #         noisy_out.append(noisy)
            
    #     return noise_vals, noisy_out, urng_rnd_vals, raw_sum_vals, sum_bits_vals

    def add_noise_burst_mode(self, signal: List[float], initial_latency: int = 8) -> Tuple[List[float], ...]:
        """
        Matches RTL burst pattern: 2 samples processed, then 3 URNG cycles skipped.
        """
        noise_vals, noisy_out = [], []
        urng_rnd_vals, raw_sum_vals, sum_bits_vals = [], [], []
        valid_flags = []
        
        # 1. Hardware "Warm-up": Advance URNG by initial latency (8 cycles)
        for _ in range(initial_latency):
            self._next_noise_cycle_accurate()

        # 2. Sequential Register: noise_adder signal_out delay
        prev_noisy = 0 
        
        # We use an index for the signal to handle the burst skipping
        sig_idx = 0
        cycle_in_burst = 0 # 0 or 1 for data, 2, 3, 4 for gap
        
        # Continue until all signal samples are processed
        while sig_idx < len(signal):
            # Always step the URNG every cycle
            n, urng_rnd = self._next_noise_cycle_accurate()

            if cycle_in_burst < 2:
                # DATA WINDOW: Process current signal sample
                x = signal[sig_idx]
                current_noisy, raw_sum, sum_bits = self._noise_adder_logic(x, n)
                
                urng_rnd_vals.append(urng_rnd)
                noise_vals.append(n)
                raw_sum_vals.append(raw_sum)
                sum_bits_vals.append(sum_bits)
                
                # Sequential output (1-cycle delay)
                noisy_out.append(prev_noisy)
                valid_flags.append(1) # Mimic signal_in_valid
                
                prev_noisy = current_noisy
                sig_idx += 1
            else:
                # GAP WINDOW: URNG runs, but no signal is added
                # In RTL, signal_in_valid would be 0 here
                pass

            # Update burst counter: 2 cycles of data + 3 cycles of gap = 5 cycle period
            cycle_in_burst = (cycle_in_burst + 1) % 5
            
        return noise_vals, noisy_out, urng_rnd_vals, raw_sum_vals, sum_bits_vals, valid_flags

class URNG64:
    """Python clone of urng_64.sv"""
    def __init__(self,
                 seed0=0x2629188426294884,
                 seed1=0x588F503226294884,
                 seed2=0x2629188426294884):
        # self.z1 = seed0 & ((1<<64)-1)
        # self.z2 = seed1 & ((1<<64)-1)
        # self.z3 = seed2 & ((1<<64)-1)
        self.z1 = seed0 & 0xFFFFFFFFFFFFFFFF
        self.z2 = seed1 & 0xFFFFFFFFFFFFFFFF
        self.z3 = seed2 & 0xFFFFFFFFFFFFFFFF

    def step(self) -> int:
        # # RTL: z1_next = {z1[39:1], z1[58:34] ^ z1[63:39]}
        # # Slice [39:1] is 39 bits wide. XOR slice is 25 bits wide.
        # z1_upper = (self.z1 >> 1) & 0x7FFFFFFFFF        # Extract z1[39:1]
        # z1_lower = ((self.z1 >> 34) ^ (self.z1 >> 39)) & 0x1FFFFFF # XOR feedback
        # z1_next = (z1_upper << 25) | z1_lower

        # # RTL: z2_next = {z2[50:6], z2[44:26] ^ z2[63:45]}
        # # Slice [50:6] is 45 bits wide. XOR slice is 19 bits wide.
        # z2_upper = (self.z2 >> 6) & 0x1FFFFFFFFFFF      # Extract z2[50:6]
        # z2_lower = ((self.z2 >> 26) ^ (self.z2 >> 45)) & 0x7FFFF   # XOR feedback
        # z2_next = (z2_upper << 19) | z2_lower

        # # RTL: z3_next = {z3[56:9], z3[39:24] ^ z3[63:48]}
        # # Slice [56:9] is 48 bits wide. XOR slice is 16 bits wide.
        # z3_upper = (self.z3 >> 9) & 0xFFFFFFFFFFFF       # Extract z3[56:9]
        # z3_lower = ((self.z3 >> 24) ^ (self.z3 >> 48)) & 0xFFFF    # XOR feedback
        # z3_next = (z3_upper << 16) | z3_lower

        # # RTL Update State: z1 <= z1_next ...
        # self.z1, self.z2, self.z3 = z1_next, z2_next, z3_next
        
        # # RTL Data Out: data_out <= (z1_next ^ z2_next ^ z3_next)
        # # Note: Return XOR of new states to match single-cycle update
        # return (z1_next ^ z2_next ^ z3_next) & 0xFFFFFFFFFFFFFFFF


        # 1. Calculate the 'next' wires based on CURRENT state
        z1_next = (((self.z1 >> 1) & 0x7FFFFFFFFF) << 25) | \
                  (((self.z1 >> 34) ^ (self.z1 >> 39)) & 0x1FFFFFF)
        
        z2_next = (((self.z2 >> 6) & 0x1FFFFFFFFFFF) << 19) | \
                  (((self.z2 >> 26) ^ (self.z2 >> 45)) & 0x7FFFF)
        
        z3_next = (((self.z3 >> 9) & 0xFFFFFFFFFFFF) << 16) | \
                  (((self.z3 >> 24) ^ (self.z3 >> 48)) & 0xFFFF)

        # 2. Update registers (simulating the posedge clk non-blocking assignment)
        self.z1, self.z2, self.z3 = z1_next, z2_next, z3_next
        
        # 3. Return the XOR of the NEW state (matching RTL data_out assignment)
        return (self.z1 ^ self.z2 ^ self.z3) & 0xFFFFFFFFFFFFFFFF
