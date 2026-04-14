# usage: python gui_waterfall_sep24.py
import os
import mmap
import time
import struct
import sys
import tkinter as tk
import customtkinter as ctk

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
        print(f"⚠️  WARNING: File '{filename}' not found! Proceeding without load.")
        return False
    try:
        with open(filename, 'r') as f:
            lines = [l.split('//')[0].strip() for l in f.readlines()]
            lines = [l for l in lines if l]
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False
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
    return True

# ==============================================================================
# 4. GUI APPLICATION
# ==============================================================================
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class FpgaMonitorApp:
    def __init__(self, root, fpga):
        self.root = root
        self.fpga = fpga
        
        self.root.title("PAM6 Automated BER Waterfall")
        self.root.geometry("1050x700")

        # State Machine Variables
        self.is_sweeping = False
        self.current_snr = 10
        self.mem_file = f"noise{self.current_snr}dB_sep24.mem"
        
        # Dictionaries to hold the BER point for each SNR
        self.snr_ber_pre = {}
        self.snr_ber_post = {}
        
        # UI Variables
        self.var_time = tk.StringVar(value="0.00")
        self.var_total_bits = tk.StringVar(value="0")
        self.var_err_pre = tk.StringVar(value="0")
        self.var_ber_pre = tk.StringVar(value="0.00e+00")
        self.var_err_post = tk.StringVar(value="0")
        self.var_ber_post = tk.StringVar(value="0.00e+00")
        self.var_core_clk = tk.StringVar(value="0")
        self.var_status = tk.StringVar(value="Idle")

        self._build_ui()
        
        self.start_time = time.time()
        self.init_fpga()
        
        print("\nStarting GUI Stats Monitor...")
        self.poll_fpga()

    def _build_ui(self):
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=2)
        self.root.grid_rowconfigure(0, weight=1)

        # --- LEFT PANEL ---
        left_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        left_frame.grid(row=0, column=0, padx=(20, 10), pady=20, sticky="nsew")

        # 1. Stats Box
        stats_frame = ctk.CTkFrame(left_frame, corner_radius=15)
        stats_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(stats_frame, text="PAM6 Metrics", font=("Roboto", 18, "bold")).pack(pady=10)

        metrics = [
            ("Current SNR:", tk.StringVar(value=f"{self.current_snr} dB")),
            ("Time (s):", self.var_time),
            ("Total Bits:", self.var_total_bits),
            ("Pre-FEC Errors:", self.var_err_pre),
            ("BER (Pre):", self.var_ber_pre),
            ("Post-FEC Errors:", self.var_err_post),
            ("BER (Post):", self.var_ber_post)
        ]
        self.snr_display_var = metrics[0][1] 

        grid_frame = ctk.CTkFrame(stats_frame, fg_color="transparent")
        grid_frame.pack(pady=5, fill="x")

        for i, (label_text, var) in enumerate(metrics):
            ctk.CTkLabel(grid_frame, text=label_text, font=("Roboto", 12, "bold"), text_color="gray70").grid(row=i, column=0, sticky="w", pady=4, padx=10)
            ctk.CTkLabel(grid_frame, textvariable=var, font=("Consolas", 13), text_color="#3498db").grid(row=i, column=1, sticky="e", pady=4, padx=10)
            grid_frame.grid_columnconfigure(1, weight=1)

        reset_btn = ctk.CTkButton(stats_frame, text="Manual Reset Core", command=self.manual_reset_btn)
        reset_btn.pack(pady=15, padx=20, fill="x")

        # 2. Sweep Controls Box
        sweep_frame = ctk.CTkFrame(left_frame, corner_radius=15)
        sweep_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(sweep_frame, text="Automated SNR Sweep", font=("Roboto", 16, "bold")).pack(pady=(10, 5))

        input_grid = ctk.CTkFrame(sweep_frame, fg_color="transparent")
        input_grid.pack(pady=5, fill="x", padx=10)
        
        ctk.CTkLabel(input_grid, text="Start SNR:").grid(row=0, column=0, sticky="w", pady=5)
        self.entry_start = ctk.CTkEntry(input_grid, width=60)
        self.entry_start.insert(0, "10")
        self.entry_start.grid(row=0, column=1, sticky="e", pady=5)

        ctk.CTkLabel(input_grid, text="Stop SNR:").grid(row=1, column=0, sticky="w", pady=5)
        self.entry_stop = ctk.CTkEntry(input_grid, width=60)
        self.entry_stop.insert(0, "30")
        self.entry_stop.grid(row=1, column=1, sticky="e", pady=5)

        ctk.CTkLabel(input_grid, text="Step Size:").grid(row=2, column=0, sticky="w", pady=5)
        self.entry_step = ctk.CTkEntry(input_grid, width=60)
        self.entry_step.insert(0, "1")
        self.entry_step.grid(row=2, column=1, sticky="e", pady=5)
        
        input_grid.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(sweep_frame, textvariable=self.var_status, font=("Roboto", 12, "italic"), text_color="yellow").pack(pady=5)
        
        self.btn_sweep = ctk.CTkButton(sweep_frame, text="Start Sweep", fg_color="#27ae60", hover_color="#2ecc71", command=self.toggle_sweep)
        self.btn_sweep.pack(pady=15, padx=20, fill="x")

        # --- RIGHT PANEL (Graph) ---
        graph_frame = ctk.CTkFrame(self.root, corner_radius=15)
        graph_frame.grid(row=0, column=1, padx=(10, 20), pady=20, sticky="nsew")
        
        self.fig, self.ax = plt.subplots(figsize=(6, 4), dpi=100)
        self.fig.patch.set_facecolor('#2b2b2b')
        self.ax.set_facecolor('#2b2b2b')
        self.ax.tick_params(colors='white')
        self.ax.xaxis.label.set_color('white')
        self.ax.yaxis.label.set_color('white')
        self.ax.title.set_color('white')
        for spine in self.ax.spines.values():
            spine.set_edgecolor('#555555')

        self.ax.set_title("BER Waterfall Curve")
        self.ax.set_xlabel("SNR (dB)")
        self.ax.set_ylabel("Bit Error Rate (BER)")
        
        # Log Scale for BER!
        self.ax.set_yscale('log')
        self.ax.grid(True, which="both", color='#444444', linestyle='--', alpha=0.5)

        # Plot with markers so the discrete SNR steps are visible
        self.line_pre, = self.ax.plot([], [], color='#e74c3c', label='Pre-FEC BER', linewidth=2, marker='o')
        self.line_post, = self.ax.plot([], [], color='#2ecc71', label='Post-FEC BER', linewidth=2, marker='s')
        self.ax.legend(facecolor='#2b2b2b', edgecolor='#555555', labelcolor='white')

        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    # --- FPGA Logic ---
    def init_fpga(self):
        # Full Hardware Reset + Load Probabilities
        self.fpga.poke(ADDR_CTRL, CTRL_SOFT_RST)
        time.sleep(0.1)
        load_probabilities(self.fpga, self.mem_file)
        self.fpga.poke(ADDR_N_INT, 1)
        self.fpga.poke(ADDR_CTRL, CTRL_SYNC_EN)

    def manual_reset_btn(self):
        print("\n--- Manual Reset Triggered via GUI ---")
        self.init_fpga()
        self.start_time = time.time()
        self.snr_ber_pre.clear()
        self.snr_ber_post.clear()

    # --- Sweep Logic ---
    def toggle_sweep(self):
        if not self.is_sweeping:
            try:
                self.current_snr = int(self.entry_start.get())
                self.stop_snr = int(self.entry_stop.get())
                self.step_snr = int(self.entry_step.get())
            except ValueError:
                self.var_status.set("Error: Invalid Inputs")
                return

            # Clear old curve data before starting fresh sweep
            self.snr_ber_pre.clear()
            self.snr_ber_post.clear()
            
            self.is_sweeping = True
            self.btn_sweep.configure(text="Stop Sweep", fg_color="#c0392b", hover_color="#e74c3c")
            self.var_status.set(f"Sweeping... Target: 100k Errors")
            
            self._transition_to_current_snr()
        else:
            self.is_sweeping = False
            self.btn_sweep.configure(text="Start Sweep", fg_color="#27ae60", hover_color="#2ecc71")
            self.var_status.set("Sweep Halted")

    def _transition_to_current_snr(self):
        self.mem_file = f"noise{self.current_snr}dB_sep24.mem"
        self.snr_display_var.set(f"{self.current_snr} dB")
        print(f"\n--- SWEEP: Transitioning to {self.current_snr} dB ---")
        
        # Trigger full hardware reboot but DO NOT clear the graph dictionaries
        self.init_fpga()
        self.start_time = time.time()

    def poll_fpga(self):
        self.fpga.poke(ADDR_CTRL, CTRL_SYNC_EN | CTRL_SNAP_REQ)
        self.fpga.poke(ADDR_CTRL, CTRL_SYNC_EN)

        total_bits = self.fpga.read64(ADDR_BITS_LO, ADDR_BITS_HI)
        err_pre    = self.fpga.read64(ADDR_ERR_PRE_LO, ADDR_ERR_PRE_HI)
        err_post   = self.fpga.read64(ADDR_ERR_POST_LO, ADDR_ERR_POST_HI)

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

        # Update Graph Data
        # Log scales break if given a strict 0. We clamp 0 to 1e-10 to represent "Error Free" visually.
        plot_pre = ber_pre if ber_pre > 0 else 1e-10
        plot_post = ber_post if ber_post > 0 else 1e-10

        self.snr_ber_pre[self.current_snr] = plot_pre
        self.snr_ber_post[self.current_snr] = plot_post

        # Extract sorted data to plot the curve
        snrs = sorted(self.snr_ber_pre.keys())
        pre_bers = [self.snr_ber_pre[s] for s in snrs]
        post_bers = [self.snr_ber_post[s] for s in snrs]

        self.line_pre.set_data(snrs, pre_bers)
        self.line_post.set_data(snrs, post_bers)
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw()

        # ==========================================
        # AUTOMATED SWEEP CHECK
        # ==========================================
        if self.is_sweeping and err_pre > 100000:
            self.current_snr += self.step_snr
            
            if self.current_snr > self.stop_snr:
                self.is_sweeping = False
                self.btn_sweep.configure(text="Start Sweep", fg_color="#27ae60", hover_color="#2ecc71")
                self.var_status.set("Sweep Complete ✅")
                print("--- SWEEP COMPLETE ---")
            else:
                self._transition_to_current_snr()

        self.root.after(1000, self.poll_fpga)

def main():
    MOCK_MODE = True 

    if not MOCK_MODE and sys.platform != "win32" and os.geteuid() != 0:
        print("⚠️  Please run with sudo.")
        return

    fpga = FpgaDriver(mock_mode=MOCK_MODE)
    print(f"✅ Connected to FPGA at {fpga.resource_path}")

    root = ctk.CTk()
    app = FpgaMonitorApp(root, fpga)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        fpga.close()

if __name__ == "__main__":
    main()