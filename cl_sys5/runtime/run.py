import os
import mmap
import time
import struct
import sys

# ==============================================================================
# 1. CONSTANTS & ADDRESS MAP
# ==============================================================================
# Control Registers
ADDR_CTRL       = 0x500
ADDR_N_INT      = 0x504
ADDR_PROB_IDX   = 0x508
ADDR_PROB_LO    = 0x510
ADDR_PROB_HI    = 0x514

# Read-Only Stats (Snapshot & Live)
ADDR_BITS_LO    = 0x600
ADDR_BITS_HI    = 0x604
ADDR_ERR_PRE_LO = 0x610
ADDR_ERR_PRE_HI = 0x614
ADDR_ERR_POST_LO= 0x620
ADDR_ERR_POST_HI= 0x624
ADDR_SNAP_HB    = 0x630
ADDR_MAIN_HB    = 0x634
ADDR_CORE_HB    = 0x638
ADDR_CORE_HB_NR = 0x63C

# Control Bits
CTRL_SYNC_EN     = (1 << 0)  # Bit 0
CTRL_SOFT_RST    = (1 << 1)  # Bit 1
CTRL_SNAP_REQ    = (1 << 2)  # Bit 2

# ==============================================================================
# 2. HELPER CLASSES
# ==============================================================================
class FpgaDriver:
    def __init__(self):
        self.resource_path = self._find_fpga_bar0()
        self.fd = os.open(self.resource_path, os.O_RDWR | os.O_SYNC)
        self.mm = mmap.mmap(self.fd, 4096, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE)

    def _find_fpga_bar0(self):
        pci_root = "/sys/bus/pci/devices"
        if not os.path.exists(pci_root):
            print("❌ ERROR: PCI bus not found (are you on an F1 instance?)")
            sys.exit(1)
            
        for device in sorted(os.listdir(pci_root)):
            try:
                # Check Vendor (Amazon 0x1d0f)
                with open(os.path.join(pci_root, device, "vendor"), "r") as f:
                    if "0x1d0f" not in f.read().strip().lower(): continue
                
                # Check Device (0xf010, 0xf000)
                with open(os.path.join(pci_root, device, "device"), "r") as f:
                    did = f.read().strip().lower()
                
                if "0xf010" in did or "0xf000" in did:
                    path = os.path.join(pci_root, device, "resource0")
                    if os.path.getsize(path) >= 4096:
                        return path
            except: continue
            
        print("❌ ERROR: FPGA AppPF not found.")
        sys.exit(1)

    def peek(self, offset):
        self.mm.seek(offset)
        return struct.unpack('<I', self.mm.read(4))[0]

    def poke(self, offset, value):
        self.mm.seek(offset)
        self.mm.write(struct.pack('<I', value))

    def read64(self, addr_lo, addr_hi):
        lo = self.peek(addr_lo)
        hi = self.peek(addr_hi)
        return (hi << 32) | lo

    def close(self):
        self.mm.close()
        os.close(self.fd)

# ==============================================================================
# 3. PROBABILITY LOADER (Mimics Testbench Logic)
# ==============================================================================
def load_probabilities(fpga, filename="noise15dB.mem"):
    print(f"-> Loading probabilities from {filename}...")
    
    if not os.path.exists(filename):
        print(f"⚠️  WARNING: File {filename} not found! Skipping probability load.")
        return

    try:
        with open(filename, 'r') as f:
            # Read lines, filter out comments (//) and empty lines
            lines = [l.split('//')[0].strip() for l in f.readlines()]
            lines = [l for l in lines if l]
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return

    count = 0
    # We expect up to 64 entries
    for i, line in enumerate(lines):
        if i >= 64: break 

        try:
            # Parse 64-bit Hex string (remove '0x' or '_' if present)
            val_64 = int(line.replace("_", ""), 16)
        except ValueError:
            print(f"⚠️  Skipping invalid line: {line}")
            continue

        # Split into Low and High 32-bit words
        val_lo = val_64 & 0xFFFFFFFF
        val_hi = (val_64 >> 32) & 0xFFFFFFFF

        # 1. Write Data to registers
        fpga.poke(ADDR_PROB_LO, val_lo)
        fpga.poke(ADDR_PROB_HI, val_hi)

        # 2. Commit to Index 'i' (This triggers the write in hardware)
        fpga.poke(ADDR_PROB_IDX, i)
        
        # Small delay to ensure hardware catches the toggle
        time.sleep(0.001) 

        # 3. Clear Index (Safety)
        fpga.poke(ADDR_PROB_IDX, 0xFFFFFFFF)
        count += 1

    print(f"-> Successfully loaded {count} probability entries.")

# ==============================================================================
# 4. MAIN STATS LOOP
# ==============================================================================
def main():
    if os.geteuid() != 0:
        print("⚠️  Please run with sudo.")
        return

    fpga = FpgaDriver()
    print(f"✅ Connected to FPGA at {fpga.resource_path}")

    # --- INITIALIZATION ---
    print("-> Holding Reset & Disabling Core...")
    # Matches TB: en <= 0; rstn <= 0;
    # Bit 1 (RST) = 1 (Active High Soft Reset), Bit 0 (EN) = 0
    fpga.poke(ADDR_CTRL, CTRL_SOFT_RST) 
    time.sleep(0.1)

    # --- LOAD PROBABILITIES ---
    # Matches TB: Loading loop happens while en=0
    load_probabilities(fpga, "noise15dB.mem")
    
    # Optional: Set Interleaving if needed (default 0)
    fpga.poke(ADDR_N_INT, 1) 

    # --- START ---
    print("-> Releasing Reset & Enabling Core...")
    # Matches TB: en <= 1; rstn <= 1;
    # Bit 1 (RST) = 0, Bit 0 (EN) = 1
    fpga.poke(ADDR_CTRL, CTRL_SYNC_EN)
    
    print("\nStarting Stats Monitor... (Press Ctrl+C to stop)\n")
    print(f"{'TIME':<10} | {'TOTAL BITS':<15} | {'PRE-FEC ERR':<12} | {'BER (PRE)':<10} | {'POST-FEC ERR':<12} | {'BER (POST)':<10} | {'CORE CLK'}")
    print("-" * 105)

    start_time = time.time()

    try:
        while True:
            # 1. TRIGGER SNAPSHOT
            # We toggle Bit 2 (SNAP_REQ) High then Low
            # Current State: Enable=1 (0x1) -> Pulse 0x5 -> 0x1
            fpga.poke(ADDR_CTRL, CTRL_SYNC_EN | CTRL_SNAP_REQ)
            # time.sleep(0.001) # Optional CDC wait
            fpga.poke(ADDR_CTRL, CTRL_SYNC_EN)

            # 2. READ 64-BIT STATS
            total_bits = fpga.read64(ADDR_BITS_LO, ADDR_BITS_HI)
            err_pre    = fpga.read64(ADDR_ERR_PRE_LO, ADDR_ERR_PRE_HI)
            err_post   = fpga.read64(ADDR_ERR_POST_LO, ADDR_ERR_POST_HI)
            
            # 3. READ HEARTBEAT
            hb_core    = fpga.peek(ADDR_CORE_HB)

            # 4. CALCULATE BER
            if total_bits > 0:
                ber_pre  = err_pre / total_bits
                ber_post = err_post / total_bits
            else:
                ber_pre  = 0.0
                ber_post = 0.0

            # 5. PRINT ROW
            elapsed = time.time() - start_time
            print(f"{elapsed:<10.2f} | {total_bits:<15,} | {err_pre:<12,} | {ber_pre:<10.2e} | {err_post:<12,} | {ber_post:<10.2e} | {hb_core:<10}")

            time.sleep(1.0)

    except KeyboardInterrupt:
        print("\nStopping...")
        # Optional: Disable on exit
        # fpga.poke(ADDR_CTRL, CTRL_SOFT_RST) 
        fpga.close()

if __name__ == "__main__":
    main()
