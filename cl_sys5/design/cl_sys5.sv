module cl_sys5 #(
    parameter EN_DDR = 0,
    parameter EN_HBM = 0
)(
    `include "cl_ports.vh"
);

`include "cl_id_defines.vh"

// ... [Clock Generation Block] ...
    wire clk_core;
    wire core_rst_n_sync; // We will ignore this signal in the final reset logic

    aws_clk_gen #(
        .CLK_GRP_A_EN(1), .CLK_GRP_B_EN(0), .CLK_GRP_C_EN(0), .CLK_HBM_EN(0)
    ) clk_gen_inst (
        .i_clk_main_a0(clk_main_a0), .i_rst_main_n(rst_main_n), .i_clk_hbm_ref(clk_hbm_ref),
        .s_axil_ctrl_awaddr(0), .s_axil_ctrl_awvalid(0), .s_axil_ctrl_wdata(0),
        .s_axil_ctrl_wstrb(0), .s_axil_ctrl_wvalid(0), .s_axil_ctrl_bready(0),
        .s_axil_ctrl_araddr(0), .s_axil_ctrl_arvalid(0), .s_axil_ctrl_rready(0),
        .o_clk_extra_a1(clk_core), .o_cl_rst_a1_n(core_rst_n_sync),
        .o_clk_extra_a2(), .o_cl_rst_a2_n(),
        .o_clk_extra_a3(), .o_cl_rst_a3_n(),
        .o_clk_extra_b0(), .o_cl_rst_b0_n(),
        .o_clk_extra_b1(), .o_cl_rst_b1_n(),
        .o_clk_extra_c0(), .o_cl_rst_c0_n(),
        .o_clk_extra_c1(), .o_cl_rst_c1_n()
    );

// ... [AXI Registers] ...

    reg [31:0] r_ctrl;
    reg [31:0] r_n_int;
    reg [31:0] r_prob_idx;
    reg [31:0] r_prob_lo;
    reg [31:0] r_prob_hi;
    reg prob_wr_toggle;

    // ---------------------------------------------------------
    // 1. Main Heartbeat (Counts on clk_main_a0)
    // ---------------------------------------------------------
    reg [31:0] main_heartbeat_ctr;
    always_ff @(posedge clk_main_a0) 
        if (!rst_main_n) main_heartbeat_ctr <= 0;
        else main_heartbeat_ctr <= main_heartbeat_ctr + 1;

    always_ff @(posedge clk_main_a0) begin
        if (!rst_main_n) begin
            cl_ocl_awready <= 1'b0;
            cl_ocl_wready  <= 1'b0;
            cl_ocl_bvalid  <= 1'b0;
            cl_ocl_bresp   <= 2'b00;

            r_ctrl         <= 32'b0;
            r_n_int        <= 32'b0;
            
            // Reset Index to -1 so we don't overwrite index 0 on reset
            r_prob_idx     <= 32'hFFFFFFFF; 
            
            r_prob_lo      <= 32'b0;
            r_prob_hi      <= 32'b0;
            prob_wr_toggle <= 1'b0;
        end else begin
            if (ocl_cl_awvalid && ocl_cl_wvalid) begin
                cl_ocl_awready <= 1'b1;
                cl_ocl_wready  <= 1'b1;
                case (ocl_cl_awaddr[11:0])
                    12'h500: r_ctrl     <= ocl_cl_wdata;
                    12'h504: r_n_int    <= ocl_cl_wdata;
                    12'h510: r_prob_lo  <= ocl_cl_wdata;
                    12'h514: r_prob_hi  <= ocl_cl_wdata;
                    12'h508: begin
                        r_prob_idx     <= ocl_cl_wdata;
                        prob_wr_toggle <= ~prob_wr_toggle; 
                    end
                endcase
            end else begin
                cl_ocl_awready <= 1'b0;
                cl_ocl_wready  <= 1'b0;
            end
            if (cl_ocl_awready && !cl_ocl_bvalid) cl_ocl_bvalid <= 1'b1;
            else if (ocl_cl_bready) cl_ocl_bvalid <= 1'b0;
        end
    end

// ... [CDC Logic - FIX APPLIED HERE] ...

    reg [1:0] sync_en, sync_soft_rst;
    
    // NEW: Manual synchronizer for the main hard reset
    reg [1:0] sync_hard_rst; 

    always_ff @(posedge clk_core) begin
        sync_en       <= {sync_en[0],       r_ctrl[0]};
        sync_soft_rst <= {sync_soft_rst[0], r_ctrl[1]};
        
        // Synchronize rst_main_n into clk_core domain
        // (1 = Reset released/High)
        sync_hard_rst <= {sync_hard_rst[0], rst_main_n};
    end
    
    wire core_enable   = sync_en[1];
    wire core_soft_rst = sync_soft_rst[1];
    wire core_hard_rst = sync_hard_rst[1];

    // FIX: Use our manual 'core_hard_rst' instead of the stuck 'core_rst_n_sync'
    wire final_rstn    = core_hard_rst & ~core_soft_rst;

    reg [31:0] n_int_core;
    reg [31:0] prob_idx_core;
    reg [63:0] prob_data_core;
    always_ff @(posedge clk_core) begin
        n_int_core     <= r_n_int;
        prob_idx_core  <= r_prob_idx;
        prob_data_core <= {r_prob_hi, r_prob_lo};
    end
    
// ... [Core Instantiation] ...

    // ---------------------------------------------------------
    // 2. Core Heartbeat (Standard - Resets on final_rstn)
    // ---------------------------------------------------------
    reg [31:0] core_heartbeat_ctr;
    always_ff @(posedge clk_core) begin
        if (!final_rstn) core_heartbeat_ctr <= 0;
        else core_heartbeat_ctr <= core_heartbeat_ctr + 1;
    end

    // ---------------------------------------------------------
    // 3. Core Heartbeat NO RESET (Counts strictly on Clock)
    // ---------------------------------------------------------
    reg [31:0] core_heartbeat_ctr_no_reset;
    
    // Initialize for simulation (FPGA will init to 0 on bitstream load)
    initial core_heartbeat_ctr_no_reset = 32'b0; 

    always_ff @(posedge clk_core) begin
        // No Reset Condition! 
        // This will count as long as clk_core is toggling.
        core_heartbeat_ctr_no_reset <= core_heartbeat_ctr_no_reset + 1;
    end

    wire [63:0] total_bits, total_err_pre, total_err_post, total_frames, total_frame_errs;

    reg ifec_en = 1;

    sys5_PAM6_top #(
        // .N_CORES(2)
    ) core_inst (
        .clk(clk_core),
        .rstn(final_rstn),
        .en(core_enable),
        .ifec_en(ifec_en),
        .probability_idx(prob_idx_core),
        .probability_in(prob_data_core),
        .total_bits(total_bits),
        .total_bit_errors_pre(total_err_pre),
        .total_bit_errors_post(total_err_post),
        .total_frames(total_frames),
        .total_frame_errors(total_frame_errs)
    );

// ... [Snapshot Logic] ...
    reg [2:0] sync_snap_req;
    always_ff @(posedge clk_core) sync_snap_req <= {sync_snap_req[1:0], r_ctrl[2]};
    wire core_snap_trigger = (sync_snap_req[1] && !sync_snap_req[2]);

    reg [63:0] bits_snap, err_pre_snap, err_post_snap, total_frames_snap, total_frame_errs_snap;
    reg [31:0] heartbeat_snap;

    always_ff @(posedge clk_core) begin
        if (!final_rstn) begin
             bits_snap <= 0; err_pre_snap <= 0; err_post_snap <= 0; heartbeat_snap <= 0; total_frames_snap <= 0; total_frame_errs_snap <= 0;
        end else if (core_snap_trigger) begin
             bits_snap <= total_bits; err_pre_snap <= total_err_pre; 
             err_post_snap <= total_err_post; 
             total_frames_snap <= total_frames; total_frame_errs_snap <= total_frame_errs;
             heartbeat_snap <= core_heartbeat_ctr; // Captures the RESETTABLE counter
        end
    end

    // ---------------------------------------------------------
    // 4. PCIe Sync Logic (Existing Snapshot + NEW Live Counters)
    // ---------------------------------------------------------
    reg [63:0] bits_pcie, err_pre_pcie, err_post_pcie, total_frames_pcie, total_frame_errs_pcie;
    reg [31:0] heartbeat_pcie; // This is the SNAPSHOT version
    
    // CDC Synchronizers for the LIVE core counters so we can read them on AXI
    reg [31:0] core_hb_live_sync1, core_hb_live_sync2;
    reg [31:0] core_hb_nr_live_sync1, core_hb_nr_live_sync2;

    always_ff @(posedge clk_main_a0) begin
        // Existing Snapshot Logic
        bits_pcie      <= bits_snap; 
        err_pre_pcie   <= err_pre_snap; 
        err_post_pcie  <= err_post_snap; 
        heartbeat_pcie <= heartbeat_snap; // 'core_heartbeat_ctr_pcie'
        total_frames_pcie <= total_frames_snap;
        total_frame_errs_pcie <= total_frame_errs_snap;
        

        // Synchronize LIVE core counter (Standard)
        core_hb_live_sync1 <= core_heartbeat_ctr;
        core_hb_live_sync2 <= core_hb_live_sync1;

        // Synchronize LIVE core counter (No Reset)
        core_hb_nr_live_sync1 <= core_heartbeat_ctr_no_reset;
        core_hb_nr_live_sync2 <= core_hb_nr_live_sync1;
    end

// ... [Read Logic] ...
    reg [31:0] rdata_reg;
    always_ff @(posedge clk_main_a0) begin
        if (!rst_main_n) begin
            cl_ocl_arready <= 0; cl_ocl_rvalid <= 0; cl_ocl_rdata <= 0;
        end else begin
            if (ocl_cl_arvalid && !cl_ocl_arready) begin
                cl_ocl_arready <= 1;
                case (ocl_cl_araddr[11:0])
                    12'h600: rdata_reg <= bits_pcie[31:0];
                    12'h604: rdata_reg <= bits_pcie[63:32];
                    12'h610: rdata_reg <= err_pre_pcie[31:0];
                    12'h614: rdata_reg <= err_pre_pcie[63:32];
                    12'h620: rdata_reg <= err_post_pcie[31:0];
                    12'h624: rdata_reg <= err_post_pcie[63:32];
                    
                    
                    // 0x630: Snapshot of Core Counter (core_heartbeat_ctr_pcie)
                    12'h630: rdata_reg <= heartbeat_pcie;
                    
                    // 0x634: Main Counter (main_heartbeat_ctr)
                    12'h634: rdata_reg <= main_heartbeat_ctr;

                    // 0x638: LIVE Core Counter (Resettable, Synced to AXI)
                    12'h638: rdata_reg <= core_hb_live_sync2;

                    // 0x63C: LIVE Core Counter (NO RESET, Synced to AXI)
                    12'h63C: rdata_reg <= core_hb_nr_live_sync2;
                    
                    12'h640: rdata_reg <= total_frames_pcie[31:0];
                    12'h644: rdata_reg <= total_frames_pcie[63:32];
                    12'h650: rdata_reg <= total_frame_errs_pcie[31:0];
                    12'h654: rdata_reg <= total_frame_errs_pcie[63:32];

                    default: rdata_reg <= 32'hDEAD_BEEF;
                endcase
            end else cl_ocl_arready <= 0;

            if (cl_ocl_arready && !cl_ocl_rvalid) begin
                cl_ocl_rvalid <= 1; cl_ocl_rdata <= rdata_reg;
            end else if (cl_ocl_rvalid && ocl_cl_rready) cl_ocl_rvalid <= 0;
        end
    end


    // Globals
    always_comb begin
        cl_sh_flr_done    = 'b1;
        cl_sh_status0     = 'b0;
        cl_sh_status1     = 'b0;
        cl_sh_status2     = 'b0;
        cl_sh_id0         = `CL_SH_ID0;
        cl_sh_id1         = `CL_SH_ID1;
        cl_sh_status_vled = 'b0;
        cl_sh_dma_wr_full = 'b0;
        cl_sh_dma_rd_full = 'b0;
    end

    // PCIM
    always_comb begin
        cl_sh_pcim_awaddr=0; cl_sh_pcim_awsize=0; cl_sh_pcim_awburst=0; cl_sh_pcim_awvalid=0;
        cl_sh_pcim_wdata=0; cl_sh_pcim_wstrb=0; cl_sh_pcim_wlast=0; cl_sh_pcim_wvalid=0;
        cl_sh_pcim_araddr=0; cl_sh_pcim_arsize=0; cl_sh_pcim_arburst=0; cl_sh_pcim_arvalid=0;
        cl_sh_pcim_awid=0; cl_sh_pcim_awlen=0; cl_sh_pcim_awcache=0; cl_sh_pcim_awlock=0;
        cl_sh_pcim_awprot=0; cl_sh_pcim_awqos=0; cl_sh_pcim_awuser=0; cl_sh_pcim_wid=0;
        cl_sh_pcim_wuser=0; cl_sh_pcim_arid=0; cl_sh_pcim_arlen=0; cl_sh_pcim_arcache=0;
        cl_sh_pcim_arlock=0; cl_sh_pcim_arprot=0; cl_sh_pcim_arqos=0; cl_sh_pcim_aruser=0;
        cl_sh_pcim_rready=0;
    end

    // PCIS
    always_comb begin
        cl_sh_dma_pcis_bresp=0; cl_sh_dma_pcis_rresp=0; cl_sh_dma_pcis_rvalid=0;
        cl_sh_dma_pcis_awready=0; cl_sh_dma_pcis_wready=0; cl_sh_dma_pcis_bid=0;
        cl_sh_dma_pcis_bvalid=0; cl_sh_dma_pcis_arready=0; cl_sh_dma_pcis_rid=0;
        cl_sh_dma_pcis_rdata=0; cl_sh_dma_pcis_rlast=0; cl_sh_dma_pcis_ruser=0;
    end

    // SDA
    always_comb begin
        cl_sda_bresp=0; cl_sda_rresp=0; cl_sda_rvalid=0; cl_sda_awready=0;
        cl_sda_wready=0; cl_sda_bvalid=0; cl_sda_arready=0; cl_sda_rdata=0;
    end

    // Interrupts & JTAG
    always_comb begin
        cl_sh_apppf_irq_req = 'b0;
    end

    // HBM & DDR
    always_comb begin
        cl_sh_ddr_stat_ack=0; cl_sh_ddr_stat_rdata=0; cl_sh_ddr_stat_int=0;
    end

    // ========================================================================
    // DDR TIE-OFFS 
    // ========================================================================
    assign sh_cl_ddr_is_ready = 1'b0;

    assign ddr_sh_stat_int = 1'b0;
    assign sh_ddr_stat_bus_ack = 1'b0;
    assign sh_ddr_stat_bus_rdata = 32'b0;

    assign cl_sh_ddr_axi_awready = 1'b0;
    assign cl_sh_ddr_axi_wready  = 1'b0;
    assign cl_sh_ddr_axi_bvalid  = 1'b0;
    assign cl_sh_ddr_axi_bresp   = 2'b00;
    
    assign cl_sh_ddr_axi_arready = 1'b0;
    assign cl_sh_ddr_axi_rvalid  = 1'b0;
    assign cl_sh_ddr_axi_rdata   = 512'b0;
    assign cl_sh_ddr_axi_rresp   = 2'b00;
    assign cl_sh_ddr_axi_rlast   = 1'b0;
    assign cl_sh_ddr_axi_bid     = 16'b0;
    assign cl_sh_ddr_axi_rid     = 16'b0;

endmodule
