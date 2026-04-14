import os
import mmap
import time
import struct
import sys

# ==============================================================================
# CONFIGURATION
# ==============================================================================
SHARED_MEM_FILE = "mock_fpga.bin"
MEM_SIZE = 4096

ADDR_CTRL       = 0x500
ADDR_BITS_LO    = 0x600
ADDR_BITS_HI    = 0x604
ADDR_ERR_PRE_LO = 0x610
ADDR_ERR_PRE_HI = 0x614
ADDR_ERR_POST_LO= 0x620
ADDR_ERR_POST_HI= 0x624
ADDR_CORE_HB    = 0x638

CTRL_SYNC_EN    = (1 << 0)
CTRL_SOFT_RST   = (1 << 1)

def main():
    print("🔧 Starting Fake FPGA Hardware Simulator...")
    
    # 1. Create a 4KB file filled with zeros to act as our "Hardware Memory"
    with open(SHARED_MEM_FILE, "wb") as f:
        f.write(b'\x00' * MEM_SIZE)
        
    # 2. Memory-map the file safely across OS types
    fd = os.open(SHARED_MEM_FILE, os.O_RDWR)
    
    if sys.platform == "win32":
        mm = mmap.mmap(fd, MEM_SIZE, access=mmap.ACCESS_WRITE)
    else:
        mm = mmap.mmap(fd, MEM_SIZE, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE)
    
    print(f"✅ Hardware mapped at {SHARED_MEM_FILE}")
    print("⏳ Waiting for client to poke registers...\n")

    # Simulation State
    is_enabled = False
    enable_time = 0.0
    
    # Simulated Specs
    bits_per_sec = 250_000_000
    pre_err_rate = 0.0951 # Starting BER (~9.5e-2)
    clk_freq = 125_000_000

    try:
        while True:
            # Read the Control Register (Address 0x500) poked by the client
            mm.seek(ADDR_CTRL)
            ctrl_reg = struct.unpack('<I', mm.read(4))[0]
            
            # Hardware Reset Logic
            if ctrl_reg & CTRL_SOFT_RST:
                if is_enabled:
                    print("🛑 HARDWARE RESET: Core disabled. Clearing stats...")
                    is_enabled = False
                    
                    # --- DYNAMIC SWEEP SIMULATION ---
                    # Drop the BER by half every time the core is reset
                    pre_err_rate *= 0.5 
                    
                    if pre_err_rate < 1e-12:
                        pre_err_rate = 0.0 # Bottom out
                        
                    print(f"📉 SIMULATION: Next run configured for Pre-FEC BER: {pre_err_rate:.2e}")
                    
                # Zero out the stat registers in memory
                for addr in [ADDR_BITS_LO, ADDR_BITS_HI, ADDR_ERR_PRE_LO, ADDR_ERR_PRE_HI, 
                             ADDR_ERR_POST_LO, ADDR_ERR_POST_HI, ADDR_CORE_HB]:
                    mm.seek(addr)
                    mm.write(struct.pack('<I', 0))

            # Hardware Enable Logic
            elif ctrl_reg & CTRL_SYNC_EN:
                if not is_enabled:
                    print("▶️ HARDWARE ENABLED: Starting clock and counters...")
                    is_enabled = True
                    enable_time = time.time()
                
                # Generate increasing fake stats
                elapsed = time.time() - enable_time
                total_bits = int(elapsed * bits_per_sec)
                
                # Calculate Pre-FEC
                err_pre = int(total_bits * pre_err_rate)
                
                # Calculate Post-FEC (Simulate steep FEC waterfall drop)
                post_err_rate = pre_err_rate ** 2.5 if pre_err_rate > 0 else 0
                err_post = int(total_bits * post_err_rate)
                
                core_clk = int(elapsed * clk_freq)

                # Write 64-bit Total Bits
                mm.seek(ADDR_BITS_LO)
                mm.write(struct.pack('<I', total_bits & 0xFFFFFFFF))
                mm.seek(ADDR_BITS_HI)
                mm.write(struct.pack('<I', (total_bits >> 32) & 0xFFFFFFFF))

                # Write 64-bit Pre-FEC Errors
                mm.seek(ADDR_ERR_PRE_LO)
                mm.write(struct.pack('<I', err_pre & 0xFFFFFFFF))
                mm.seek(ADDR_ERR_PRE_HI)
                mm.write(struct.pack('<I', (err_pre >> 32) & 0xFFFFFFFF))

                # Write 64-bit Post-FEC Errors
                mm.seek(ADDR_ERR_POST_LO)
                mm.write(struct.pack('<I', err_post & 0xFFFFFFFF))
                mm.seek(ADDR_ERR_POST_HI)
                mm.write(struct.pack('<I', (err_post >> 32) & 0xFFFFFFFF))

                # Write 32-bit Heartbeat
                mm.seek(ADDR_CORE_HB)
                mm.write(struct.pack('<I', core_clk & 0xFFFFFFFF))

            # Run at ~60Hz update rate
            time.sleep(0.016)

    except KeyboardInterrupt:
        print("\nPowering down Fake FPGA...")
    finally:
        mm.close()
        os.close(fd)
        os.remove(SHARED_MEM_FILE) 

if __name__ == "__main__":
    main()