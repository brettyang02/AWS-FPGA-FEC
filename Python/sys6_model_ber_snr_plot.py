import argparse
import os
import sys
from pathlib import Path
import time
import matplotlib.pyplot as plt

# Maintaining your specific imports
from syscommon_ref.prbs import PRBS63
from syscommon_ref.io import read_bit_file, read_int_file, align_streams
from syscommon_ref.gray_pam6 import GrayEncodePAM6, GrayDecodePAM6
from sys6_ref.isi_pam6 import ISIChannelOneTapPAM6
from sys6_ref.mlse_pam6 import MLSEPAM6
from syscommon_ref.noise import Noise
from syscommon_ref.fec_checker import IL_FEC_Checker 

# ==============================================================================
# LOGGING UTILITY
# ==============================================================================
class Logger(object):
    """Redirects stdout to both the console and a file."""
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "w", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()

    def flush(self):
        self.terminal.flush()
        self.log.flush()

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================
def apply_8bit_wrap(val):
    """Simulates 8-bit signed integer overflow."""
    return ((int(val) + 128) % 256) - 128

# ==============================================================================
# MAIN SIMULATION
# ==============================================================================
if __name__ == "__main__":
    # Initialize Logger
    log_filename = "ber_sweep_10dB_20dB_100k_errors.txt"
    sys.stdout = Logger(log_filename)

    # --- UPDATED: SNR Sweep Range 10dB to 20dB ---
    snr_range = range(10, 21) 
    
    snr_list = []
    py_ber_pre_list = []
    py_ber_post_list = []

    # Setup Plot
    plt.ion()
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.set_yscale('log')
    ax.set_xlabel('SNR (dB)')
    ax.set_ylabel('Bit Error Rate (BER)')
    ax.set_title('Python Reference: BER vs SNR (Target: 100k Post-FEC Errors)')
    ax.grid(True, which="both", ls="-", alpha=0.5)

    for snr in snr_range:
        print(f"\n{'='*60}")
        print(f"STARTING SNR: {snr} dB")
        print(f"{'='*60}")

        CHUNK_SIZE = 100000 
        seed_val = 0x2645841236254785
        
        prbs = PRBS63(seed=seed_val)
        enc = GrayEncodePAM6()
        isi = ISIChannelOneTapPAM6(symbol_sep=24.0, alpha=0.5)
        
        # Ensure these memory files exist for the expanded range
        noise_file = f"noise/noise{snr}dB_sep24.mem"
        noise = Noise(mem_file=noise_file)
        
        mlse = MLSEPAM6(SYMBOL_SEPARATION=24, SIGNAL_RESOLUTION=8, ALPHA=0.5, TRACEBACK=10, METRIC_RESOLUTION=20)
        dec = GrayDecodePAM6()
        fec = IL_FEC_Checker(seed=seed_val, n=544, t=15, m=10, n_interleave=1)

        start_time = time.time()
        
        # --- UPDATED: Target 100,000 Errors ---
        target_errors = 100000 
        
        while fec.total_bit_errors_post < target_errors:
            py_bits = list(prbs.generate(CHUNK_SIZE))
            syms = enc.encode(py_bits)
            ch_out = isi.process(syms)
            noise_vals, noisy, _, _, _, valids = noise.add_noise_burst_mode(ch_out)

            dec_syms = []
            for i in range(len(noisy)):
                if valids[i]:
                    x8 = apply_8bit_wrap(int(noisy[i]))
                    sym, valid = mlse.step(signal_in=x8, signal_in_valid=1, rstn=1)
                    if valid:
                        dec_syms.append(sym)

            py_post_bits = dec.decode(dec_syms)

            for bit in py_post_bits:
                fec.step(bit)
            
            # Print progress to both console and file
            print(f"  [Progress] SNR {snr}dB | Total Bits: {fec.total_bits:,} | Post-FEC Errors: {fec.total_bit_errors_post:,}", end='\r')

            # Safety Break: 10 Billion bits
            if fec.total_bits > 10000000000:
                print(f"\n  ⚠️ Safety limit reached (10Bil bits). Stopping for {snr}dB.")
                break

        # Final Calculation for this SNR
        ber_pre = fec.total_bit_errors_pre / max(1, fec.total_bits)
        ber_post = fec.total_bit_errors_post / max(1, fec.total_bits)

        snr_list.append(snr)
        py_ber_pre_list.append(ber_pre)
        py_ber_post_list.append(ber_post)

        print(f"\n\nFINALIZED {snr} dB:")
        print(f"{'TOTAL BITS':<15} | {'PRE-FEC ERR':<12} | {'BER (PRE)':<10} | {'POST-FEC ERR':<12} | {'BER (POST)':<10}")
        print("-" * 75)
        print(f"{fec.total_bits:<15,} | {fec.total_bit_errors_pre:<12,} | {ber_pre:<10.2e} | {fec.total_bit_errors_post:<12,} | {ber_post:<10.2e}")

        # Update Plot Live
        ax.plot(snr, ber_pre, 'bo', markersize=8, label='Pre-FEC' if snr == 10 else "")
        ax.plot(snr, ber_post, 'rs', markersize=8, label='Post-FEC' if snr == 10 else "")
        plt.draw()
        plt.pause(0.1)

        print(f"Time for this dB: {time.time() - start_time:.2f} seconds")

    # Final Plot Styling
    plt.ioff()
    ax.plot(snr_list, py_ber_pre_list, 'b-', alpha=0.4)
    ax.plot(snr_list, py_ber_post_list, 'r-', alpha=0.4)
    ax.legend()
    
    print(f"\nSweep Complete. Results logged to {log_filename}")
    plt.show()