# usage (AWS Linux): sudo -E python3 gui_noise_sep24.py noise11dB_sep24.mem
# usage (Windows Local): python gui_noise_sep24.py noise11dB_sep24.mem
import os
import mmap
import time
import struct
import sys
import tkinter as tk
from tkinter import ttk

# ==============================================================================
# 1. CONSTANTS & ADDRESS MAP
# ==============================================================================
# Control Registers
ADDR_CTRL       = 0x500
ADDR_N_INT      = 0x504
ADDR_PROB_IDX   = 0x508
ADDR_PROB_LO    = 0x510
ADDR_PROB_HI    = 0x514

# Read-Only Stats
ADDR_BITS_LO    = 0x600
ADDR_BITS_HI    = 0x604
ADDR_ERR_PRE_LO = 0x610
ADDR_ERR_PRE_HI = 0x614
ADDR_ERR_POST_LO= 0x620
ADDR_ERR_POST_HI= 0x624
ADDR_CORE_HB    = 0x638

# Control Bits
CTRL_SYNC_EN     = (1 << 0)  # Bit 0
CTRL_SOFT_RST    = (1 << 1)  # Bit 1
CTRL_SNAP_REQ    = (1 << 2)  # Bit 2

# ==============================================================================
# 2. CROSS-PLATFORM FPGA DRIVER
# ==============================================================================
class FpgaDriver:
    def __init__(self, mock_mode=False):
        if mock_mode:
            self.resource_path = "mock_fpga.bin"
        else:
            self.resource_path = self._find_fpga_bar0()
            
        # os.O_SYNC is not supported on Windows
        flags = os.O_RDWR
        if sys.platform != "win32":
            flags |= getattr(os, 'O_SYNC', 0)
            
        self.fd = os.open(self.resource_path, flags)
        
        # Windows and Linux handle mmap parameters differently
        if sys.platform == "win32":
            self.mm = mmap.mmap(self.fd, 4096, access=mmap.ACCESS_WRITE)
        else:
            self.mm = mmap.mmap(self.fd, 4096, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE)

    def _find_fpga_bar0(self):
        pci_root = "/sys/bus/pci/devices"
        if not os.path.exists(pci_root):
            print("❌ ERROR: PCI bus not found (are you on an F1/F2 instance?)")
            sys.exit(1)
            
        for device in sorted(os.listdir(pci_root)):
            try:
                with open(os.path.join(pci_root, device, "vendor"), "r") as f:
                    if "0x1d0f" not in f.read().strip().lower(): continue
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
# 3. PROBABILITY LOADER 
# ==============================================================================
def load_probabilities(fpga, filename):
    print(f"-> Loading probabilities from {filename}...")
    
    if not os.path.exists(filename):
        print(f"⚠️  WARNING: File '{filename}' not found! Skipping load.")
        return

    try:
        with open(filename, 'r') as f:
            lines = [l.split('//')[0].strip() for l in f.readlines()]
            lines = [l for l in lines if l]
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return

    count = 0
    for i, line in enumerate(lines):
        if i >= 64: break 
        try:
            val_64 = int(line.replace("_", ""), 16)
        except ValueError:
            continue

        val_lo = val_64 & 0xFFFFFFFF
        val_hi = (val_64 >> 32) & 0xFFFFFFFF

        fpga.poke(ADDR_PROB_LO, val_lo)
        fpga.poke(ADDR_PROB_HI, val_hi)
        fpga.poke(ADDR_PROB_IDX, i)
        time.sleep(0.001) 
        fpga.poke(ADDR_PROB_IDX, 0xFFFFFFFF)
        count += 1

    print(f"-> Successfully loaded {count} probability entries.")

# ==============================================================================
# 4. GUI APPLICATION
# ==============================================================================
class FpgaMonitorApp:
    def __init__(self, root, fpga, mem_file):
        self.root = root
        self.fpga = fpga
        self.mem_file = mem_file
        
        self.root.title("FPGA BER Monitor")
        self.root.geometry("450x350")
        self.root.configure(padx=20, pady=20)

        # UI Variables
        self.var_time = tk.StringVar(value="0.00")
        self.var_total_bits = tk.StringVar(value="0")
        self.var_err_pre = tk.StringVar(value="0")
        self.var_ber_pre = tk.StringVar(value="0.00e+00")
        self.var_err_post = tk.StringVar(value="0")
        self.var_ber_post = tk.StringVar(value="0.00e+00")
        self.var_core_clk = tk.StringVar(value="0")

        self._build_ui()
        
        self.start_time = time.time()
        self.init_fpga()
        
        print("\nStarting GUI Stats Monitor...")
        self.poll_fpga()

    def _build_ui(self):
        metrics = [
            ("Time (s):", self.var_time),
            ("Total Bits:", self.var_total_bits),
            ("Pre-FEC Errors:", self.var_err_pre),
            ("BER (Pre):", self.var_ber_pre),
            ("Post-FEC Errors:", self.var_err_post),
            ("BER (Post):", self.var_ber_post),
            ("Core Clk (HB):", self.var_core_clk)
        ]

        frame = ttk.Frame(self.root)
        frame.pack(fill=tk.BOTH, expand=True)

        for i, (label_text, var) in enumerate(metrics):
            ttk.Label(frame, text=label_text, font=("Arial", 12, "bold")).grid(row=i, column=0, sticky="w", pady=5)
            ttk.Label(frame, textvariable=var, font=("Courier", 12)).grid(row=i, column=1, sticky="e", pady=5, padx=20)

        reset_btn = ttk.Button(self.root, text="[ Reset & Reload Core ]", command=self.reset_core_from_ui)
        reset_btn.pack(pady=15, fill=tk.X)

    def init_fpga(self):
        print("-> Holding Reset & Disabling Core...")
        self.fpga.poke(ADDR_CTRL, CTRL_SOFT_RST)
        time.sleep(0.1)
        
        load_probabilities(self.fpga, self.mem_file)
        self.fpga.poke(ADDR_N_INT, 1)
        
        print("-> Releasing Reset & Enabling Core...")
        self.fpga.poke(ADDR_CTRL, CTRL_SYNC_EN)

    def reset_core_from_ui(self):
        print("\n--- Manual Reset Triggered via GUI ---")
        self.init_fpga()
        self.start_time = time.time()

    def poll_fpga(self):
        self.fpga.poke(ADDR_CTRL, CTRL_SYNC_EN | CTRL_SNAP_REQ)
        self.fpga.poke(ADDR_CTRL, CTRL_SYNC_EN)

        total_bits = self.fpga.read64(ADDR_BITS_LO, ADDR_BITS_HI)
        err_pre    = self.fpga.read64(ADDR_ERR_PRE_LO, ADDR_ERR_PRE_HI)
        err_post   = self.fpga.read64(ADDR_ERR_POST_LO, ADDR_ERR_POST_HI)
        hb_core    = self.fpga.peek(ADDR_CORE_HB)

        ber_pre  = err_pre / total_bits if total_bits > 0 else 0.0
        ber_post = err_post / total_bits if total_bits > 0 else 0.0
        elapsed  = time.time() - self.start_time

        self.var_time.set(f"{elapsed:.2f}")
        self.var_total_bits.set(f"{total_bits:,}")
        self.var_err_pre.set(f"{err_pre:,}")
        self.var_ber_pre.set(f"{ber_pre:.2e}")
        self.var_err_post.set(f"{err_post:,}")
        self.var_ber_post.set(f"{ber_post:.2e}")
        self.var_core_clk.set(f"{hb_core}")

        # Schedule next update in 1 second
        self.root.after(1000, self.poll_fpga)

# ==============================================================================
# 5. MAIN EXECUTION
# ==============================================================================
def main():
    # --- TOGGLE THIS ---
    # Set to True when running locally on Windows with fake_fpga.py
    # Set to False when deploying to your PAM6 AWS instance
    MOCK_MODE = True 

    if not MOCK_MODE and os.geteuid() != 0:
        print("⚠️  Please run with sudo.")
        return

    mem_file = "no_noise.mem"
    if len(sys.argv) > 1:
        mem_file = sys.argv[1]

    fpga = FpgaDriver(mock_mode=MOCK_MODE)
    print(f"✅ Connected to FPGA at {fpga.resource_path}")

    root = tk.Tk()
    app = FpgaMonitorApp(root, fpga, mem_file)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        fpga.close()

if __name__ == "__main__":
    main()