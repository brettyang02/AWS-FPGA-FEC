`timescale 1ns / 1ps


module sys6_PAM6_bit_extraction;

    reg clk=0;
    reg en;
    reg rstn;
    reg precode_en = 1;
    
    reg [63:0] probability_in;
    reg [31:0] probability_idx= 32'hFFFFFFFF;
    
    reg [3:0] n_interleave = 1;
    
	wire [63:0] total_bits;
	wire [63:0] total_bit_errors_pre;
	wire [63:0] total_bit_errors_post;
	wire [63:0] total_frames;
	wire [63:0] total_frame_errors;
	
  wire [2:0] ge_data;
	wire [2:0] mlse_symbol_o;
	wire [8-1:0] isi_signal_o; // // SIGNAL_RESOLUTION=8
	

    sys6_PAM6_top dut (
	   .clk(clk),
	   .en(en),
	   .rstn(rstn),
	   .probability_in(probability_in),
	   .probability_idx(probability_idx),
	   //.precode_en(precode_en),
	   .n_interleave(n_interleave),
	   .total_bits(total_bits),
	   .total_bit_errors_pre(total_bit_errors_pre),
	   .total_bit_errors_post(total_bit_errors_post),
	   .total_frames(total_frames),
	   .total_frame_errors(total_frame_errors),
	   
	   .prbs_valid(prbs_valid),
	   .prbs_data(prbs_data),
     .ge_valid(ge_valid),
	   .ge_data(ge_data),
	   .isi_signal_o(isi_signal_o),
	   .isi_valid_o(isi_valid_o),
	   .mlse_valid_o(mlse_valid_o),
	   .mlse_symbol_o(mlse_symbol_o),
	   .dec_data_valid(dec_data_valid),
	   .dec_data(dec_data)
	   );
	   
	           
    always #10 clk = ~clk;
    
    integer i;
  
    reg [63:0] probability_mem [63:0];
    
    initial begin
    
//        f_prbs = $fopen("rtl_prbs.txt","w");
//        f_ge = $fopen("rtl_ge.txt","w");
//        f_isi = $fopen("rtl_isi.txt","w");
//        f_mlse = $fopen("rtl_mlse.txt","w");
//        f_dec  = $fopen("rtl_decoded.txt","w");
        
        en<=0;
        rstn <= 0;
        
        $readmemh("no_noise.mem", probability_mem);
//        $readmemh("noise15dB.mem", probability_mem);
        
        for (i=0;i<64;i=i+1) begin
            #20
            probability_idx <= i;
            probability_in <= probability_mem[i];
        end
        
        #20
        probability_idx <= 32'hFFFFFFFF;

        #20 
        en<= 1;
        rstn <=1;        
        
    end
    
    integer f_prbs, f_ge, f_isi, f_mlse, f_dec;
    initial begin
      f_prbs = $fopen("rtl_prbs.txt","w");
      f_ge = $fopen("rtl_ge.txt","w");
      f_isi = $fopen("rtl_isi.txt","w");
      f_mlse = $fopen("rtl_mlse.txt","w");
      f_dec  = $fopen("rtl_decoded.txt","w");
    end
    
    always @(posedge clk) begin
      if (dut.prbs_valid)    $fwrite(f_prbs, "%0d\n", dut.prbs_data);
      if (dut.ge_valid)    $fwrite(f_ge, "%0d\n", dut.ge_data);
      if (dut.isi_valid_o)  $fwrite(f_isi,  "%0d\n", dut.isi_signal_o);
      if (dut.mlse_valid_o)  $fwrite(f_mlse,  "%0d\n", dut.mlse_symbol_o);
      if (dut.dec_data_valid)$fwrite(f_dec,  "%0d\n", dut.dec_data);
    end
    
    initial begin
//        #2000000;  // 100 us
        #100000;  // reference: #1Mil = 50k decoded bits
        $display("Simulation end at %0t", $time);
        $finish;
    end
    final begin
      $fclose(f_prbs);
      $fclose(f_ge);
      $fclose(f_isi);
      $fclose(f_mlse);
      $fclose(f_dec);
    end
    
    

endmodule
