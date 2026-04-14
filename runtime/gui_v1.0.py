# usage: python gui_matplotlib_sep24.py noise11dB_sep24.mem
import os
import mmap
import time
import struct
import sys
import tkinter as tk
import customtkinter as ctk

# Matplotlib imports for Tkinter embedding
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ==============================================================================
# 1. CONSTANTS & ADDRESS MAP
# ==============================================================================
ADDR_CTRL       = 0x500
ADDR_N_INT      = 0x504
ADDR_PROB_IDX   = 0x508
ADDR_PROB_LO    = 0x510
ADDR_PROB_HI    = 0x514

ADDR_BITS_LO    = 0x600
ADDR_BITS_HI    = 0x604
ADDR_ERR_PRE_LO = 0x610
ADDR_ERR_PRE_HI = 0x614
ADDR_ERR_POST_LO= 0x620
ADDR_ERR_POST_HI= 0x624
ADDR_CORE_HB    = 0x638

CTRL_SYNC_EN     = (1 << 0)
CTRL_SOFT_RST    = (1 << 1)
CTRL_SNAP_REQ    = (1 << 2)

# ==============================================================================
# 2. CROSS-PLATFORM FPGA DRIVER
# ==============================================================================
class FpgaDriver:
    def __init__(self, mock_mode=False):
        if mock_mode:
            self.resource_path = "mock_fpga.bin"
        else:
            self.resource_path = self._find_fpga_bar0()
            
        flags = os.O_RDWR
        if sys.platform != "win32":
            flags |= getattr(os, 'O_SYNC', 0)
            
        self.fd = os.open(self.resource_path, flags)
        
        if sys.platform == "win32":
            self.mm = mmap.mmap(self.fd, 4096, access=mmap.ACCESS_WRITE)
        else:
            self.mm = mmap.mmap(self.fd, 4096, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE)

    def _find_fpga_bar0(self):
        pci_root = "/sys/bus/pci/devices"
        if not os.path.exists(pci_root):
            print("❌ ERROR: PCI bus not found.")
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
        fpga.poke(ADDR_PROB_LO, val_64 & 0xFFFFFFFF)
        fpga.poke(ADDR_PROB_HI, (val_64 >> 32) & 0xFFFFFFFF)
        fpga.poke(ADDR_PROB_IDX, i)
        time.sleep(0.001) 
        fpga.poke(ADDR_PROB_IDX, 0xFFFFFFFF)
        count += 1
    print(f"-> Successfully loaded {count} probability entries.")

# ==============================================================================
# 4. GUI APPLICATION
# ==============================================================================
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class FpgaMonitorApp:
    def __init__(self, root, fpga, mem_file):
        self.root = root
        self.fpga = fpga
        self.mem_file = mem_file
        
        self.root.title("PAM6 Live Monitor")
        self.root.geometry("900x600")

        # Data arrays for graphing
        self.time_data = []
        self.pre_ber_data = []
        self.post_ber_data = []
        
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
        # Create a grid layout: Left for stats, Right for graph
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=2)
        self.root.grid_rowconfigure(0, weight=1)

        # --- LEFT PANEL (Stats) ---
        stats_frame = ctk.CTkFrame(self.root, corner_radius=15)
        stats_frame.grid(row=0, column=0, padx=(20, 10), pady=20, sticky="nsew")

        ctk.CTkLabel(stats_frame, text="PAM6 Metrics", font=("Roboto", 20, "bold")).pack(pady=15)

        metrics = [
            ("Time (s):", self.var_time),
            ("Total Bits:", self.var_total_bits),
            ("Pre-FEC Errors:", self.var_err_pre),
            ("BER (Pre):", self.var_ber_pre),
            ("Post-FEC Errors:", self.var_err_post),
            ("BER (Post):", self.var_ber_post),
            ("Core Clk (HB):", self.var_core_clk)
        ]

        grid_frame = ctk.CTkFrame(stats_frame, fg_color="transparent")
        grid_frame.pack(pady=10, fill="x")

        for i, (label_text, var) in enumerate(metrics):
            ctk.CTkLabel(grid_frame, text=label_text, font=("Roboto", 13, "bold"), text_color="gray70").grid(row=i, column=0, sticky="w", pady=8, padx=10)
            ctk.CTkLabel(grid_frame, textvariable=var, font=("Consolas", 14), text_color="#3498db").grid(row=i, column=1, sticky="e", pady=8, padx=10)
            grid_frame.grid_columnconfigure(1, weight=1)

        reset_btn = ctk.CTkButton(stats_frame, text="Soft Reset Core", command=self.reset_core_from_ui, font=("Roboto", 14, "bold"), height=40)
        reset_btn.pack(side="bottom", pady=20, padx=20, fill="x")

        # --- RIGHT PANEL (Graph) ---
        graph_frame = ctk.CTkFrame(self.root, corner_radius=15)
        graph_frame.grid(row=0, column=1, padx=(10, 20), pady=20, sticky="nsew")
        
        # Setup Matplotlib Figure (Styled for Dark Mode)
        self.fig, self.ax = plt.subplots(figsize=(6, 4), dpi=100)
        self.fig.patch.set_facecolor('#2b2b2b')
        self.ax.set_facecolor('#2b2b2b')
        self.ax.tick_params(colors='white')
        self.ax.xaxis.label.set_color('white')
        self.ax.yaxis.label.set_color('white')
        self.ax.title.set_color('white')
        for spine in self.ax.spines.values():
            spine.set_edgecolor('#555555')

        self.ax.set_title("Live Bit Error Rate")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("BER")
        self.ax.grid(True, color='#444444', linestyle='--', alpha=0.7)

        # Create empty lines
        self.line_pre, = self.ax.plot([], [], color='#e74c3c', label='Pre-FEC BER', linewidth=2)
        self.line_post, = self.ax.plot([], [], color='#2ecc71', label='Post-FEC BER', linewidth=2)
        self.ax.legend(facecolor='#2b2b2b', edgecolor='#555555', labelcolor='white')

        # Embed into CustomTkinter
        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

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
        self.time_data.clear()
        self.pre_ber_data.clear()
        self.post_ber_data.clear()

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

        # Update Text UI
        self.var_time.set(f"{elapsed:.2f}")
        self.var_total_bits.set(f"{total_bits:,}")
        self.var_err_pre.set(f"{err_pre:,}")
        self.var_ber_pre.set(f"{ber_pre:.2e}")
        self.var_err_post.set(f"{err_post:,}")
        self.var_ber_post.set(f"{ber_post:.2e}")
        self.var_core_clk.set(f"{hb_core}")

        # Update Graph Data
        self.time_data.append(elapsed)
        self.pre_ber_data.append(ber_pre)
        self.post_ber_data.append(ber_post)

        if len(self.time_data) > 60:
            self.time_data.pop(0)
            self.pre_ber_data.pop(0)
            self.post_ber_data.pop(0)

        # Redraw Graph
        self.line_pre.set_data(self.time_data, self.pre_ber_data)
        self.line_post.set_data(self.time_data, self.post_ber_data)
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw()

        self.root.after(1000, self.poll_fpga)

# ==============================================================================
# 5. MAIN EXECUTION
# ==============================================================================
def main():
    MOCK_MODE = True 

    if not MOCK_MODE and sys.platform != "win32" and os.geteuid() != 0:
        print("⚠️  Please run with sudo.")
        return

    mem_file = "no_noise.mem"
    if len(sys.argv) > 1:
        mem_file = sys.argv[1]

    fpga = FpgaDriver(mock_mode=MOCK_MODE)
    print(f"✅ Connected to FPGA at {fpga.resource_path}")

    root = ctk.CTk()
    app = FpgaMonitorApp(root, fpga, mem_file)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        fpga.close()

if __name__ == "__main__":
    main()