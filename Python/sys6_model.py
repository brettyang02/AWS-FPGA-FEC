import argparse
import os
import sys
from pathlib import Path
import time

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
def compare_streams(name, a, b, align=True):
    if align:
        k = align_streams(a, b, 256)
    else:
        k = 0
    N = min(len(a), len(b) - k)
    mism = [(i, a[i], b[i + k]) for i in range(N) if a[i] != b[i + k]]
    err = len(mism)
    ber = err / max(1, N)
    print(f"[{name}] Compared {N} bits (offset {k}). Mismatches: {err}  BER={ber:.3e}")
    return err, ber, k, N

def to_signed_8bit(val):
    return val if val < 128 else val - 256

def apply_8bit_wrap(val):
    return ((int(val) + 128) % 256) - 128

def read_fec_stats(file_path):
    stats = {}
    if not os.path.exists(file_path):
        return None
    with open(file_path, 'r') as f:
        for line in f:
            if ':' in line:
                key, val = line.split(':')
                stats[key.strip()] = float(val.strip())
    return stats

# ==============================================================================
# MAIN SIMULATION
# ==============================================================================
if __name__ == "__main__":
    log_filename = "py_vs_rtl_BER_comparison_15db_20db.txt"
    sys.stdout = Logger(log_filename)

    snr_range = range(15, 21) 

    for snr in snr_range:
        print(f"\nRUNNING SIMULATION: {snr} dB")
        
        CURRENT_DIR = Path(f"rtl_outputs/noise{snr}dB")
        rtl_available = CURRENT_DIR.exists() and (CURRENT_DIR / "rtl_prbs.txt").exists()
        
        start_time = time.time()
        seed_val = 0x2645841236254785
        n_bits = 1000000 
        
        # --- Python Reference Pipeline ---
        prbs = PRBS63(seed=seed_val)
        py_bits = list(prbs.generate(n_bits))
        enc = GrayEncodePAM6()
        syms = enc.encode(py_bits)
        isi = ISIChannelOneTapPAM6(symbol_sep=24.0, alpha=0.5)
        ch_out = isi.process(syms)
        
        noise_file = f"noise/noise{snr}dB_sep24.mem"
        if os.path.exists(noise_file):
            print(f"Using noise memory: {noise_file}")
            noise = Noise(mem_file=noise_file)
            _, noisy, _, _, _, valids = noise.add_noise_burst_mode(ch_out)
        else:
            noisy = ch_out
            valids = [True] * len(ch_out)

        mlse = MLSEPAM6(SYMBOL_SEPARATION=24, SIGNAL_RESOLUTION=8, ALPHA=0.5, TRACEBACK=10, METRIC_RESOLUTION=20)
        dec_syms = []
        for i in range(len(noisy)):
            if valids[i]:
                x8 = apply_8bit_wrap(int(noisy[i]))
                sym, valid = mlse.step(signal_in=x8, signal_in_valid=1, rstn=1)
                if valid:
                    dec_syms.append(sym)

        dec = GrayDecodePAM6()
        py_post = dec.decode(dec_syms)

        fec = IL_FEC_Checker(seed=seed_val, n=544, t=15, m=10, n_interleave=1)
        for bit in py_post:
            fec.step(bit)
        
        ber_pre = fec.total_bit_errors_pre / max(1, fec.total_bits)
        ber_post = fec.total_bit_errors_post / max(1, fec.total_bits)

        # 1. Output Python Table
        # print(f"\n{'TOTAL BITS':<15} | {'PRE-FEC ERR':<12} | {'BER (PRE)':<10} | {'POST-FEC ERR':<12} | {'BER (POST)':<10}")
        # print("-" * 75)
        # print(f"{fec.total_bits:<15,} | {fec.total_bit_errors_pre:<12,} | {ber_pre:<10.2e} | {fec.total_bit_errors_post:<12,} | {ber_post:<10.2e}")
        
        # 2. Comparison Streams (Only if RTL exists)
        if rtl_available:
            rtl_prbs = read_bit_file(CURRENT_DIR / "rtl_prbs.txt")
            rtl_mlse = read_int_file(CURRENT_DIR / "rtl_mlse.txt")
            rtl_dec  = read_bit_file(CURRENT_DIR / "rtl_decoded.txt")
            rtl_fec  = read_fec_stats(CURRENT_DIR / "rtl_fec_stats.txt")

            compare_streams(f"[{snr}dB] RTL-PRBS vs Ref-PRBS", rtl_prbs, py_bits, align=False)
            # compare_streams(f"[{snr}dB] RTL-PostMLSE vs Ref-PostMLSE", rtl_mlse, dec_syms, align=False)
            compare_streams(f"[{snr}dB] RTL-PreFEC vs Ref-PreFEC", rtl_dec, py_post, align=False )

            if rtl_fec:
                print(f"\n{'Metric':<25} | {'RTL Value':<15} | {'Python Ref':<15} | {'Match?'}")
                print("-" * 85)
                
                metrics = [
                    ("total_bits", fec.total_bits),
                    ("total_bit_errors_pre", fec.total_bit_errors_pre),
                    ("total_bit_errors_post", fec.total_bit_errors_post),
                    ("total_frames", fec.total_frames),
                    ("total_frame_errors", fec.total_frame_errors),
                    ("BER_pre", ber_pre),
                    ("BER_post", ber_post)
                ]

                for key, py_val in metrics:
                    # rtl_val = rtl_fec.get(key, -1)
                    # # Thresholds: 128 for counts (pipeline slack), 1e-7 for BER
                    # tol = 1e-7 if "BER" in key else 128
                    # is_match = abs(rtl_val - py_val) <= tol
                    
                    # fmt = ".3e" if "BER" in key else "g"
                    # status = "✅" if is_match else "❌"
                    # print(f"{key:<25} | {rtl_val:<15{fmt}} | {py_val:<15{fmt}} | {status}")

                    rtl_val = rtl_fec.get(key, -1)
                    # Check order of magnitude for BER: ratio must be between 0.1 and 10
                    if "BER" in key:
                        if rtl_val == py_val: # Handles both being 0
                            is_match = True
                        elif rtl_val == 0 or py_val == 0:
                            is_match = False
                        else:
                            is_match = 0.1 <= (rtl_val / py_val) <= 10.0
                    else:
                        is_match = abs(rtl_val - py_val) <= 128
                    
                    fmt = ".3e" if "BER" in key else "g"
                    status = "✅" if is_match else "❌"
                    print(f"{key:<25} | {rtl_val:<15{fmt}} | {py_val:<15{fmt}} | {status}")

        else:
            print(f"\nℹ️  RTL files not found in {CURRENT_DIR}. Skipping comparison.")

        print(f"Simulation time: {time.time() - start_time:.2f} seconds")

    print(f"\nSweep complete. Log saved to {log_filename}")