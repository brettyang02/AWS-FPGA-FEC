# usage: sudo python3 gui_v2.0.py
import os
import mmap
import time
import struct
import sys
import math
import tkinter as tk
import customtkinter as ctk

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from customtkinter import filedialog

# ==============================================================================
# 1. CONSTANTS & ADDRESS MAP
# ==============================================================================
ADDR_CTRL        = 0x500
ADDR_N_INT       = 0x504
ADDR_PROB_IDX    = 0x508
ADDR_PROB_LO     = 0x510
ADDR_PROB_HI     = 0x514

ADDR_BITS_LO     = 0x600
ADDR_BITS_HI     = 0x604
ADDR_ERR_PRE_LO  = 0x610
ADDR_ERR_PRE_HI  = 0x614
ADDR_ERR_POST_LO = 0x620
ADDR_ERR_POST_HI = 0x624
ADDR_CORE_HB     = 0x638

ADDR_FRAMES_LO     = 0x640
ADDR_FRAMES_HI     = 0x644
ADDR_FRAME_ERR_LO  = 0x650
ADDR_FRAME_ERR_HI  = 0x654

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
# 3. NOISE GENERATOR
# ==============================================================================
def generate_pam6_noise(target_snr_db, filename, symbol_separation=24.0):
    d = symbol_separation / 2.0  
    Es = (35.0 / 3.0) * (d**2)
    
    if target_snr_db > 99:
        sigma = 0.000001
    else:
        noise_variance = Es / (10**(target_snr_db / 10.0))
        sigma = math.sqrt(noise_variance)

    max_uint64 = (2**64) - 1
    
    with open(filename, 'w') as f:
        for i in range(64):
            boundary = i + 0.5
            if sigma < 0.0001: 
                val_int = max_uint64
            else:
                cdf_prob = math.erf(boundary / (sigma * math.sqrt(2)))
                val_int = max_uint64 if cdf_prob >= 1.0 else int(cdf_prob * max_uint64)
            f.write(f"{val_int:016x}\n")

def load_probabilities(fpga, filename):
    try:
        with open(filename, 'r') as f:
            lines = [l.split('//')[0].strip() for l in f.readlines() if l.strip()]
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False
        
    for i, line in enumerate(lines):
        if i >= 64: break 
        val_64 = int(line.replace("_", ""), 16)
        fpga.poke(ADDR_PROB_LO, val_64 & 0xFFFFFFFF)
        fpga.poke(ADDR_PROB_HI, (val_64 >> 32) & 0xFFFFFFFF)
        fpga.poke(ADDR_PROB_IDX, i)
        time.sleep(0.001) 
        fpga.poke(ADDR_PROB_IDX, 0xFFFFFFFF)
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
        
        self.root.title("PAM6 Autonomous BER/FER Waterfall")
        self.root.geometry("1200x850")

        self.is_sweeping = False
        self.current_snr = 10
        self.target_stat = "Pre-FEC Errors"
        self.target_count = 100000
        self.mem_file = f"noise{self.current_snr}dB_sep24.mem"
        
        self.snr_ber_pre = {}
        self.snr_ber_post = {}
        
        # UI StringVars
        self.var_time = tk.StringVar(value="0.00")
        self.var_total_bits = tk.StringVar(value="0")
        self.var_err_pre = tk.StringVar(value="0")
        self.var_ber_pre = tk.StringVar(value="0.00e+00")
        self.var_err_post = tk.StringVar(value="0")
        self.var_ber_post = tk.StringVar(value="0.00e+00")
        self.var_total_frames = tk.StringVar(value="0")
        self.var_frame_errs = tk.StringVar(value="0")
        self.var_fer = tk.StringVar(value="0.00e+00")
        self.var_status = tk.StringVar(value="Idle")
        self.snr_display_var = tk.StringVar(value=f"{self.current_snr} dB")
        self.sweep_entries = {}

        self._build_ui()
        self.start_time = time.time()
        self.init_fpga()
        self.poll_fpga()

    def _build_ui(self):
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=3)
        self.root.grid_rowconfigure(0, weight=1)

        # --- LEFT PANEL (Scrollable) ---
        left_frame = ctk.CTkScrollableFrame(self.root, fg_color="transparent", label_text="FPGA Control Panel")
        left_frame.grid(row=0, column=0, padx=(20, 10), pady=20, sticky="nsew")

        # 1. System Metrics (Two-Column)
        stats_frame = ctk.CTkFrame(left_frame, corner_radius=15)
        stats_frame.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(stats_frame, text="System Metrics", font=("Roboto", 16, "bold")).pack(pady=10)

        metrics = [
            ("SNR:", self.snr_display_var),       ("Time (s):", self.var_time),
            ("Total Bits:", self.var_total_bits),  ("Pre Errs:", self.var_err_pre),
            ("BER (Pre):", self.var_ber_pre),      ("Post Errs:", self.var_err_post),
            ("BER (Post):", self.var_ber_post),    ("Frames:", self.var_total_frames),
            ("Frame Errs:", self.var_frame_errs),  ("FER:", self.var_fer)
        ]

        grid_frame = ctk.CTkFrame(stats_frame, fg_color="transparent")
        grid_frame.pack(pady=5, fill="x", padx=10)
        for i, (label_text, var) in enumerate(metrics):
            row_idx, col_off = i // 2, (i % 2) * 2
            ctk.CTkLabel(grid_frame, text=label_text, font=("Roboto", 11, "bold"), text_color="gray70").grid(row=row_idx, column=col_off, sticky="w", pady=2, padx=(5, 2))
            ctk.CTkLabel(grid_frame, textvariable=var, font=("Consolas", 12), text_color="#3498db").grid(row=row_idx, column=col_off+1, sticky="w", pady=2, padx=(0, 10))

        ctk.CTkButton(stats_frame, text="Manual Reset Core", height=28, command=self.manual_reset_btn).pack(pady=10, padx=20, fill="x")

        # 2. Sweep Controls
        sweep_frame = ctk.CTkFrame(left_frame, corner_radius=15)
        sweep_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(sweep_frame, text="Automated Sweep", font=("Roboto", 16, "bold")).pack(pady=(10, 5))

        input_grid = ctk.CTkFrame(sweep_frame, fg_color="transparent")
        input_grid.pack(pady=5, fill="x", padx=10)
        
        ctk.CTkLabel(input_grid, text="Start:").grid(row=0, column=0, sticky="w")
        self.sweep_entries["Start SNR:"] = ctk.CTkEntry(input_grid, width=60); self.sweep_entries["Start SNR:"].insert(0, "10")
        self.sweep_entries["Start SNR:"].grid(row=0, column=1, sticky="w", pady=2)

        ctk.CTkLabel(input_grid, text="Stop:").grid(row=0, column=2, sticky="w", padx=(10, 0))
        self.sweep_entries["Stop SNR:"] = ctk.CTkEntry(input_grid, width=60); self.sweep_entries["Stop SNR:"].insert(0, "30")
        self.sweep_entries["Stop SNR:"].grid(row=0, column=3, sticky="w", pady=2)

        ctk.CTkLabel(input_grid, text="Step:").grid(row=1, column=0, sticky="w")
        self.sweep_entries["Step Size:"] = ctk.CTkEntry(input_grid, width=60); self.sweep_entries["Step Size:"].insert(0, "1")
        self.sweep_entries["Step Size:"].grid(row=1, column=1, sticky="w", pady=2)

        ctk.CTkLabel(input_grid, text="Count:").grid(row=1, column=2, sticky="w", padx=(10, 0))
        self.entry_target_count = ctk.CTkEntry(input_grid, width=60); self.entry_target_count.insert(0, "100000")
        self.entry_target_count.grid(row=1, column=3, sticky="w", pady=2)

        ctk.CTkLabel(input_grid, text="Target:").grid(row=2, column=0, sticky="w", pady=5)
        self.combo_target_stat = ctk.CTkOptionMenu(input_grid, values=["Pre-FEC Errors", "Post-FEC Errors", "Frame Errors", "Total Frames"], height=24)
        self.combo_target_stat.set("Pre-FEC Errors"); self.combo_target_stat.grid(row=2, column=1, columnspan=3, sticky="ew", pady=5)

        ctk.CTkLabel(sweep_frame, textvariable=self.var_status, font=("Roboto", 11, "italic"), text_color="yellow").pack(pady=2)
        self.btn_sweep = ctk.CTkButton(sweep_frame, text="Start Sweep", fg_color="#27ae60", hover_color="#2ecc71", command=self.toggle_sweep)
        self.btn_sweep.pack(pady=10, padx=20, fill="x")

        # --- RIGHT PANEL (Graph & Save) ---
        graph_panel = ctk.CTkFrame(self.root, fg_color="transparent")
        graph_panel.grid(row=0, column=1, padx=(10, 20), pady=20, sticky="nsew")
        
        chart_container = ctk.CTkFrame(graph_panel, corner_radius=15)
        chart_container.pack(fill="both", expand=True)
        
        self.fig, self.ax = plt.subplots(figsize=(6, 4), dpi=100)
        self.fig.patch.set_facecolor('#2b2b2b'); self.ax.set_facecolor('#2b2b2b')
        self.ax.tick_params(colors='white'); [self.ax.spines[s].set_edgecolor('#555555') for s in self.ax.spines]
        self.ax.set_title("BER Waterfall Curve", color="white"); self.ax.set_xlabel("SNR (dB)", color="white"); self.ax.set_ylabel("Bit Error Rate (BER)", color="white")
        self.ax.set_yscale('log'); self.ax.grid(True, which="both", color='#444444', linestyle='--', alpha=0.5)

        self.line_pre, = self.ax.plot([], [], color='#e74c3c', label='Pre-FEC BER', linewidth=2, marker='o')
        self.line_post, = self.ax.plot([], [], color='#2ecc71', label='Post-FEC BER', linewidth=2, marker='s')
        self.ax.legend(facecolor='#2b2b2b', edgecolor='#555555', labelcolor='white')

        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_container)
        self.canvas.draw(); self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
        
        self.btn_save_graph = ctk.CTkButton(graph_panel, text="💾 Save Graph Image", fg_color="#34495e", command=self.save_graph_btn)
        self.btn_save_graph.pack(side="right", pady=(10, 0))

    def save_graph_btn(self):
        fpath = filedialog.asksaveasfilename(defaultextension=".png", initialfile=f"ber_{self.current_snr}dB.png", filetypes=[("PNG", "*.png"), ("PDF", "*.pdf")])
        if fpath:
            try:
                self.fig.savefig(fpath, bbox_inches='tight', dpi=150)
                self.btn_save_graph.configure(fg_color="#2ecc71", text="Saved! ✅")
                self.root.after(2000, lambda: self.btn_save_graph.configure(fg_color="#34495e", text="💾 Save Graph Image"))
            except Exception as e: print(f"Error: {e}")

    def init_fpga(self):
        self.fpga.poke(ADDR_CTRL, CTRL_SOFT_RST)
        time.sleep(0.1)
        if not os.path.exists(self.mem_file): generate_pam6_noise(self.current_snr, self.mem_file)
        load_probabilities(self.fpga, self.mem_file)
        self.fpga.poke(ADDR_N_INT, 1); self.fpga.poke(ADDR_CTRL, CTRL_SYNC_EN)

    def manual_reset_btn(self):
        self.init_fpga(); self.start_time = time.time(); self.snr_ber_pre.clear(); self.snr_ber_post.clear()

    def toggle_sweep(self):
        if not self.is_sweeping:
            try:
                self.current_snr = int(self.sweep_entries["Start SNR:"].get())
                self.stop_snr = int(self.sweep_entries["Stop SNR:"].get())
                self.step_snr = int(self.sweep_entries["Step Size:"].get())
                self.target_count = int(self.entry_target_count.get())
                self.target_stat = self.combo_target_stat.get()
                self.is_sweeping = True
                self.btn_sweep.configure(text="Stop Sweep", fg_color="#c0392b")
                self._transition_to_current_snr()
            except: self.var_status.set("Error: Invalid Inputs")
        else:
            self.is_sweeping = False
            self.btn_sweep.configure(text="Start Sweep", fg_color="#27ae60")

    def _transition_to_current_snr(self):
        self.mem_file = f"noise{self.current_snr}dB_sep24.mem"
        self.snr_display_var.set(f"{self.current_snr} dB")
        self.init_fpga(); self.start_time = time.time()

    def poll_fpga(self):
        self.fpga.poke(ADDR_CTRL, CTRL_SYNC_EN | CTRL_SNAP_REQ); self.fpga.poke(ADDR_CTRL, CTRL_SYNC_EN)
        bits, e_pre, e_post = self.fpga.read64(ADDR_BITS_LO, ADDR_BITS_HI), self.fpga.read64(ADDR_ERR_PRE_LO, ADDR_ERR_PRE_HI), self.fpga.read64(ADDR_ERR_POST_LO, ADDR_ERR_POST_HI)
        f_tot, f_err = self.fpga.read64(ADDR_FRAMES_LO, ADDR_FRAMES_HI), self.fpga.read64(ADDR_FRAME_ERR_LO, ADDR_FRAME_ERR_HI)
        
        b_pre, b_post, fer = (e_pre/bits if bits>0 else 0), (e_post/bits if bits>0 else 0), (f_err/f_tot if f_tot>0 else 0)
        self.var_time.set(f"{time.time()-self.start_time:.2f}"); self.var_total_bits.set(f"{bits:,}"); self.var_err_pre.set(f"{e_pre:,}")
        self.var_ber_pre.set(f"{b_pre:.2e}"); self.var_err_post.set(f"{e_post:,}"); self.var_ber_post.set(f"{b_post:.2e}")
        self.var_total_frames.set(f"{f_tot:,}"); self.var_frame_errs.set(f"{f_err:,}"); self.var_fer.set(f"{fer:.2e}")

        self.snr_ber_pre[self.current_snr], self.snr_ber_post[self.current_snr] = max(b_pre, 1e-12), max(b_post, 1e-12)
        snrs = sorted(self.snr_ber_pre.keys())
        self.line_pre.set_data(snrs, [self.snr_ber_pre[s] for s in snrs]); self.line_post.set_data(snrs, [self.snr_ber_post[s] for s in snrs])
        self.ax.relim(); self.ax.autoscale_view(); self.canvas.draw()

        if self.is_sweeping:
            val = {"Pre-FEC Errors": e_pre, "Post-FEC Errors": e_post, "Frame Errors": f_err, "Total Frames": f_tot}[self.target_stat]
            if val >= self.target_count:
                self.current_snr += self.step_snr
                if self.current_snr > self.stop_snr:
                    self.is_sweeping = False; self.btn_sweep.configure(text="Start Sweep", fg_color="#27ae60"); self.var_status.set("Complete ✅")
                else: self._transition_to_current_snr()
        self.root.after(1000, self.poll_fpga)

def main():
    if os.getuid() != 0: print("⚠️ Run with sudo."); return
    fpga = FpgaDriver(mock_mode=False); root = ctk.CTk(); app = FpgaMonitorApp(root, fpga)
    try: root.mainloop()
    finally: fpga.close()

if __name__ == "__main__": main()