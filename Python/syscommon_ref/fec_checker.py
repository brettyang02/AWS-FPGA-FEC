class IL_FEC_Checker:
    def __init__(self, seed=0x1, n=544, t=15, m=10, n_interleave=1):
        self.n = n  # Codeword size (symbols)
        self.t = t  # Error threshold
        self.m = m  # Symbol size (bits)
        self.n_interleave = n_interleave #
        
        # Reference PRBS (matches sr_in = sr[62]^sr[61])
        self.sr = seed & 0x7FFFFFFFFFFFFFFF 
        
        # Global Stats
        self.total_bits = 0
        self.total_bit_errors_pre = 0
        self.total_bit_errors_post = 0
        self.total_frames = 0
        self.total_frame_errors = 0
        
        # Per-interleave state tracking
        self.cur_idx = 0
        self.symbol_bit_idx = [0] * n_interleave
        self.symbol_bit_errs = [0] * n_interleave
        self.cw_sym_idx = [0] * n_interleave
        self.cw_sym_errs = [0] * n_interleave
        self.cw_bit_errs = [0] * n_interleave
        self.new_symbol = [True] * n_interleave

    def step(self, data_in):
        # 1. Advance reference PRBS to match hardware
        sr_in = ((self.sr >> 62) ^ (self.sr >> 61)) & 0x1
        self.sr = ((self.sr << 1) | sr_in) & 0x7FFFFFFFFFFFFFFF
        
        # 2. Check for bit error
        error = 1 if (data_in != sr_in) else 0
        cc = self.cur_idx
        
        self.total_bits += 1
        self.total_bit_errors_pre += error
        self.cw_bit_errs[cc] += error

        # 3. Handle Symbol and Codeword logic
        if self.new_symbol[cc]:
            self.new_symbol[cc] = False
            self.symbol_bit_idx[cc] = 1
            self.symbol_bit_errs[cc] = error
            
            if self.cw_sym_idx[cc] < self.n:
                self.cw_sym_idx[cc] += 1
            else:
                # Codeword Finished
                self.total_frames += 1
                if self.cw_sym_errs[cc] > self.t:
                    self.total_frame_errors += 1
                    self.total_bit_errors_post += self.cw_bit_errs[cc]
                
                self.cw_sym_idx[cc] = 1
                self.cw_sym_errs[cc] = 0
                self.cw_bit_errs[cc] = error
        else:
            self.symbol_bit_idx[cc] += 1
            self.symbol_bit_errs[cc] += error

        # 4. Symbol Completion
        if self.symbol_bit_idx[cc] == self.m:
            if self.symbol_bit_errs[cc] > 0:
                self.cw_sym_errs[cc] += 1
            self.new_symbol[cc] = True
            self.cur_idx = (self.cur_idx + 1) % self.n_interleave