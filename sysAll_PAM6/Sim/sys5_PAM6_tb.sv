`timescale 1ns / 1ps


module sys5_PAM6_tb;

    reg clk=0;
    reg en;
    reg rstn;
    reg ifec_en = 1;
    
    reg [63:0] probability_in;
    reg [31:0] probability_idx= 32'hFFFFFFFF;
        
	wire [63:0] total_bits;
	wire [63:0] total_bit_errors_pre;
	wire [63:0] total_bit_errors_post;
	wire [63:0] total_frames;
	wire [63:0] total_frame_errors;
	

    sys5_PAM6_top dut (
	   .clk(clk),
	   .en(en),
	   .rstn(rstn),
	   .probability_in(probability_in),
	   .probability_idx(probability_idx),
	   .ifec_en(ifec_en),
	   .total_bits(total_bits),
	   .total_bit_errors_pre(total_bit_errors_pre),
	   .total_bit_errors_post(total_bit_errors_post),
	   .total_frames(total_frames),
	   .total_frame_errors(total_frame_errors)
	   
//	   .prbs_valid(prbs_valid),
//	   .prbs_data(prbs_data),
//	   .dec_data_valid(dec_data_valid),
//	   .dec_data(dec_data)
	   );
	   
	           
    always #10 clk = ~clk;
    
    integer i;
  
    reg [63:0] probability_mem [63:0];
    
    initial begin
    
//        f_prbs = $fopen("rtl_prbs.txt","w");
//        f_dec  = $fopen("rtl_decoded.txt","w");
        
        en<=0;
        rstn <= 0;
        
        $readmemh("noise18dB_sep24.mem", probability_mem);
//        $readmemh("no_noise.mem", probability_mem);
        
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
    
    /*
    integer f_prbs, f_dec;
    initial begin
      f_prbs = $fopen("rtl_prbs.txt","w");
      f_dec  = $fopen("rtl_decoded.txt","w");
    end
    
    always @(posedge clk) begin
      if (dut.prbs_valid)    $fwrite(f_prbs, "%0d\n", dut.prbs_data);
      if (dut.dec_data_valid)$fwrite(f_dec,  "%0d\n", dut.dec_data);
    end
    
    initial begin
        #100000;  // 100 us
        $display("Simulation end at %0t", $time);
        $finish;
    end
    final begin
      $fclose(f_prbs);
      $fclose(f_dec);
    end
    */
    
    

endmodule
