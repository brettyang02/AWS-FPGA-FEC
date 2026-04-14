import math
import os

def generate_pam6_noise(target_snr_db, filename, symbol_separation=24.0):
    """
    Generates a 64-line .mem file for FPGA Gaussian Noise Generator.
    Tailored for PAM-6 with specific Symbol Separation.
    """
    
    # 1. PARAMETERS
    # d is half the distance between symbol centers (e.g. distance from 0 to first symbol)
    d = symbol_separation / 2.0  
    
    # 2. CALCULATE SIGNAL ENERGY (Es) FOR PAM-6
    # PAM-6 Levels: +/- d, +/- 3d, +/- 5d
    # Energy = Average( levels^2 )
    # Es = [ 2*(1d)^2 + 2*(3d)^2 + 2*(5d)^2 ] / 6
    # Es = [ 1 + 9 + 25 ] * d^2 / 3
    # Es = (35 / 3) * d^2
    
    Es = (35.0 / 3.0) * (d**2)
    
    # Debug info
    print(f"--- Configuration: {filename} ---")
    print(f"  > Modulation: PAM-6")
    print(f"  > Separation: {symbol_separation} (d={d})")
    print(f"  > Signal Energy (Es): {Es:.2f}")
    
    # 3. CALCULATE REQUIRED NOISE SIGMA
    # SNR_dB = 10 * log10( Es / Noise_Power )
    # Noise_Power (Variance) = Es / 10^(SNR/10)
    
    # Special Case: Infinite SNR (Zero Noise)
    if target_snr_db > 99:
        sigma = 0.000001 # Effectively zero
        print(f"  > SNR: Zero Noise (Infinity dB)")
    else:
        noise_variance = Es / (10**(target_snr_db / 10.0))
        sigma = math.sqrt(noise_variance)
        print(f"  > SNR: {target_snr_db} dB")
        print(f"  > Noise Sigma: {sigma:.4f}")

    # 4. GENERATE CDF TABLE (Inverse Transform Sampling)
    # We map the probability CDF of a Folded Normal distribution to 0..2^64-1
    max_uint64 = (2**64) - 1
    
    with open(filename, 'w') as f:
        for i in range(64):
            # The bin boundary for integer 'i' is 'i + 0.5'
            boundary = i + 0.5
            
            if sigma < 0.0001: 
                # Zero noise case: All probabilities are 1.0 (noise is always 0)
                # except we strictly saturate index 0 to MAX.
                val_int = max_uint64
            else:
                # Calculate CDF: P(|N| < boundary)
                # Formula: erf( boundary / (sigma * sqrt(2)) )
                cdf_prob = math.erf(boundary / (sigma * math.sqrt(2)))
                
                # Scale to 64-bit integer
                if cdf_prob >= 1.0:
                    val_int = max_uint64
                else:
                    val_int = int(cdf_prob * max_uint64)
            
            # Write as 16-character hex string (64 bits)
            f.write(f"{val_int:016x}\n")
            
    print(f"  ✅ Generated {filename}\n")

if __name__ == "__main__":
    # --- BATCH GENERATE FILES FOR SEPARATION = 24 ---
    
    # 1. Zero Noise (Control Group)
    generate_pam6_noise(100.0, "noise_zero_sep24.mem", symbol_separation=24)

    # 2. High SNR (Clean Signal)
    generate_pam6_noise(25.0, "noise25dB_sep24.mem", symbol_separation=24)
    generate_pam6_noise(20.0, "noise20dB_sep24.mem", symbol_separation=24)

    # 3. Medium SNR (Typical Test)
    generate_pam6_noise(15.0, "noise15dB_sep24.mem", symbol_separation=24)
    
    # 4. Low SNR (Noisy)
    generate_pam6_noise(10.0, "noise10dB_sep24.mem", symbol_separation=24)
    generate_pam6_noise(5.0,  "noise05dB_sep24.mem", symbol_separation=24)