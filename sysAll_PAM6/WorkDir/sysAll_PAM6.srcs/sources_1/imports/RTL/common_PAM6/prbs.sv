`timescale 1ns / 1ps

module prbs63 #(
    parameter SEED = 64'h0000000000000001,
    parameter N_PCS = 1)(
    input clk,
    input en,
    input rstn,
    output reg data,
    output reg valid = 0);
    
    reg [62:0] sr = SEED;
    wire sr_in;
    
    //reg[31:0] count=0;
    
    assign sr_in = (sr[62]^sr[61]);
    
    always @ (posedge clk)
    if (!rstn) begin
        sr = SEED;
        valid = 0;
        //count <= 0;
    end else begin
        if (en) begin
            //if (count < 120*N_PCS) begin
                sr <= {sr[61:0],sr_in};
                data <=  sr_in;
                valid <= 1;
                //count <= count +1;
            //end else if (count < 128*N_PCS-1) begin
                //valid <= 0;
                //count <= count +1;
            //end else if (count == 128*N_PCS-1) begin
                //valid <= 0;
                //count <=0;
           // end
            
        end else begin
	       valid <=0;	
	   end
    end
endmodule


module prbs63_IL_FEC_checker #(
    SEED = 64'h0000000000000001,
    parameter N = 544,
    parameter T = 15,
    parameter M = 10)(
    input clk,
    input data,
    input en,
    input rstn,
    //max 4
    input [3:0] n_interleave_in,
    //input stop,
    output reg [63:0] total_bits = 0,
    output reg [63:0] total_bit_errors_pre = 0,
    output reg [63:0] total_bit_errors_post = 0,
    output reg [63:0] total_frames = 0,
    output reg [63:0] total_frame_errors = 0
    );
    
    reg [31:0] delay = 0;
    reg [62:0] sr = SEED;
    wire sr_in;
    
    assign sr_in = (sr[62]^sr[61]);
    
    //number of bits received in current FEC symbol
    //reg [7:0] symbol_bit_index [7:0];
    reg [7:0] symbol_bit_index [3:0] = '{default:'0};
    
    //number of bits errors in current FEC symbol
    reg [7:0] symbol_bit_errors [3:0] = '{default:'0};
    
    //number of symbols completed in current FEC codeword
    reg [31:0] symbol_codeword_index [3:0] = '{default:'0};
    
    //number of symbols errors in current FEC codeword
    reg [31:0] symbol_codeword_errors [3:0] = '{default:'0};
    
    //number of bit errors in current FEC codeword
    reg [31:0] bit_codeword_errors [3:0] = '{default:'0};
    
    //interleaving index
    reg [31:0] cur_FEC_codeword = 0;
    
    reg new_symbol = 1;
    
    //flag if new bit received
    reg new_bit = 0;
    
    //flag if new bit is error
    reg error = 0;
    
    reg [3:0] n_interleave = 1;
    
    
    //at posedge clock, take in new bit and determine if there was a bit error
    always @ (posedge clk) begin
    
        if (!rstn) begin
            new_bit <=0;
            delay <= 0;
            sr <= SEED;
            total_frames <=0;
            total_frame_errors <= 0;
            total_bit_errors_pre <= 0;
            total_bit_errors_post <= 0;
            total_bits <=0;
            error <= 0;
            cur_FEC_codeword <= 0;
            new_symbol <= 1;
            
            n_interleave <= n_interleave_in;
            
            symbol_bit_index <= '{default:'0};
            symbol_bit_errors <= '{default:'0};
            symbol_codeword_index <= '{default:'0};
            symbol_codeword_errors <= '{default:'0};
            bit_codeword_errors <= '{default:'0};
            
        //end else if (stop) begin
        end else begin
        
            if (en) begin
                if (delay > 0) delay <= delay - 1;
                else begin
                    new_bit <= 1;
                    sr <= {sr[61:0],sr_in};
                    if (data == sr_in) error <= 0;
                    else  error <= 1;
                end
            end else begin
                new_bit<=0;
            end
            
            if (new_bit == 1) begin
            
                total_bits <= total_bits + 1;
                total_bit_errors_pre <= total_bit_errors_pre + error;
                bit_codeword_errors[cur_FEC_codeword] <= bit_codeword_errors[cur_FEC_codeword] + error;
                
                //new FEC symbol
                if (new_symbol==1) begin
                    new_symbol <= 0;
                    symbol_bit_index[cur_FEC_codeword] <= 1;
                    symbol_bit_errors[cur_FEC_codeword] <= error;
                    
                    //current codeword incomplete
                    if (symbol_codeword_index[cur_FEC_codeword] < N) begin
                        symbol_codeword_index[cur_FEC_codeword] <= symbol_codeword_index[cur_FEC_codeword] + 1;
                        symbol_codeword_errors[cur_FEC_codeword] <= symbol_codeword_errors[cur_FEC_codeword] + (symbol_bit_errors[cur_FEC_codeword]>0);
                    //codeword complete
                    end else begin
                        total_frames <= total_frames + 1;
                        symbol_codeword_index[cur_FEC_codeword] <= 1;
                        symbol_codeword_errors[cur_FEC_codeword] <= 0;
                        bit_codeword_errors[cur_FEC_codeword] <= 0;
                        if (symbol_codeword_errors[cur_FEC_codeword]+ (symbol_bit_errors[cur_FEC_codeword]>0) > T) begin
                            total_frame_errors <= total_frame_errors + 1;
                            total_bit_errors_post <= total_bit_errors_post + bit_codeword_errors[cur_FEC_codeword];
                        end
                    end
                    
                    
                end else begin
                
                symbol_bit_index[cur_FEC_codeword] <= symbol_bit_index[cur_FEC_codeword] +1;
                symbol_bit_errors[cur_FEC_codeword] <= symbol_bit_errors[cur_FEC_codeword] + error;
                
                end
                
                if (symbol_bit_index[cur_FEC_codeword] == M-1) begin
                    cur_FEC_codeword <= (cur_FEC_codeword+1)%n_interleave;
                    new_symbol <= 1;
                end
                

            end
        end
  end     
            
endmodule

//generates pseudo-random-binary-sequence of length 2^31-1 
module prbs63_120_8 #(
    parameter SEED = 64'h0000000000000001,
    parameter N_PCS = 1)(
    input clk,
    input en,
    input rstn,
    output reg data,
    output reg valid = 0);
    
    reg [62:0] sr = SEED;
    wire sr_in;
    
    reg[31:0] count=0;
    
    assign sr_in = (sr[62]^sr[61]);
    
    always @ (posedge clk)
    if (!rstn) begin
        sr = SEED;
        valid = 0;
        count <= 0;
    end else begin
        if (en) begin
            if (count < 120*N_PCS) begin
                sr <= {sr[61:0],sr_in};
                data <=  sr_in;
                valid <= 1;
                count <= count +1;
            end else if (count < 128*N_PCS-1) begin
                valid <= 0;
                count <= count +1;
            end else if (count == 128*N_PCS-1) begin
                valid <= 0;
                count <=0;
            end
            
        end else begin
	       valid <=0;	
	   end
    end
endmodule

module prbs63_ci_IL_FEC_checker #(
     SEED = 64'h0000000000000001,
    parameter N = 544,
    parameter T = 15,
    parameter M = 10,
    parameter W = 4,
    parameter LATENCY = 3600)(
    input clk,
    input data,
    input en,
    input rstn,
    //input stop,
    output reg [63:0] total_bits = 0,
    output reg [63:0] total_bit_errors_pre = 0,
    output reg [63:0] total_bit_errors_post = 0,
    output reg [63:0] total_frames = 0,
    output reg [63:0] total_frame_errors = 0
    
    
    //hybrid model statistics
//    output reg [63:0] fec_symbols = 0,
//    output reg [63:0] fec_symbol_errors = 0,
//    output reg [63:0] propagated_fec_symbol_errors = 0,
    
//    output reg [63:0] epc [23:0] = '{default:'0}
    
    );
    
    reg [31:0] delay = 0;
    reg [62:0] sr = SEED;
    wire sr_in;
    
    assign sr_in = (sr[62]^sr[61]);
    
    //number of bits received in current FEC symbol
    //reg [7:0] symbol_bit_index [7:0];
    reg [7:0] symbol_bit_index [7:0] = '{default:'0};
    
    //number of bits errors in current FEC symbol
    reg [7:0] symbol_bit_errors [7:0] = '{default:'0};
    
    //number of symbols completed in current FEC codeword
    reg [31:0] symbol_codeword_index [7:0] = '{default:'0};
    
    //number of symbols errors in current FEC codeword
    reg [31:0] symbol_codeword_errors [7:0] = '{default:'0};
    
    //number of bit errors in current FEC codeword
    reg [31:0] bit_codeword_errors [7:0] = '{default:'0};
    
    //interleaving index
    reg [31:0] cur_FEC_codeword = 0;
    
    reg new_symbol = 1;
    
    //flag if new bit received
    reg new_bit = 0;
    
    //flag if new bit is error
    reg error = 0;
    
    //hybrid model stats
    //reg [7:0] prev_fec_symbol_err = 8'b00000000;
    
    //at posedge clock, take in new bit and determine if there was a bit error
    always @ (posedge clk) begin
    
        if (!rstn) begin
            new_bit <=0;
            delay<=0;
            sr <= SEED;
            total_frames <=0;
            total_frame_errors <= 0;
            total_bit_errors_pre <= 0;
            total_bit_errors_post <= 0;
            total_bits <=0;
            error <= 0;
            cur_FEC_codeword <= 0;
            new_symbol <= 1;
            
            
            symbol_bit_index <= '{default:'0};
            symbol_bit_errors <= '{default:'0};
            symbol_codeword_index <= '{default:'0};
            symbol_codeword_errors <= '{default:'0};
            bit_codeword_errors <= '{default:'0};
            
            //prev_fec_symbol_err <= 0;
            //fec_symbols <= 0;
            //fec_symbol_errors <= 0;
            //propagated_fec_symbol_errors <= 0;
            
            //epc <= '{default:'0};
            
            
        //end else if (stop) begin
        end else begin
        
            if (en) begin
                if (delay<LATENCY) begin
                    delay <= delay+1;
                end else begin
                    
                    new_bit <= 1;
                    sr <= {sr[61:0],sr_in};
                    
                    if (data == sr_in) begin
                        error <= 0;
                    end else begin
                        error <= 1;
                    
                    end
                end
            end else begin
                new_bit<=0;
            end
            
            if (new_bit == 1) begin
            
                total_bits <= total_bits + 1;
                total_bit_errors_pre <= total_bit_errors_pre + error;
                bit_codeword_errors[cur_FEC_codeword] <= bit_codeword_errors[cur_FEC_codeword] + error;
                
                //new FEC symbol, count error statistics from previous FEC symbol in this RS codeword.
                if (new_symbol==1) begin
                    new_symbol <= 0;
                    symbol_bit_index[cur_FEC_codeword] <= 1;
                    symbol_bit_errors[cur_FEC_codeword] <= error;
                    
                    //hybrid model
                    //fec_symbols<=fec_symbols+1;
                    //fec_symbol_errors<=fec_symbol_errors+(symbol_bit_errors[cur_FEC_codeword]>0);
                    //propagated_fec_symbol_errors <= propagated_fec_symbol_errors + ((symbol_bit_errors[cur_FEC_codeword]>0)&&(prev_fec_symbol_err[cur_FEC_codeword]==1));
                    //prev_fec_symbol_err[cur_FEC_codeword] <= (symbol_bit_errors[cur_FEC_codeword]>0);
                    
                    //current codeword incomplete
                    if (symbol_codeword_index[cur_FEC_codeword] < N) begin
                        symbol_codeword_index[cur_FEC_codeword] <= symbol_codeword_index[cur_FEC_codeword] + 1;
                        symbol_codeword_errors[cur_FEC_codeword] <= symbol_codeword_errors[cur_FEC_codeword] + (symbol_bit_errors[cur_FEC_codeword]>0);
                    //codeword complete
                    end else begin
                        total_frames <= total_frames + 1;
                        symbol_codeword_index[cur_FEC_codeword] <= 1;
                        symbol_codeword_errors[cur_FEC_codeword] <= 0;
                        bit_codeword_errors[cur_FEC_codeword] <= 0;
                        
//                        if ((symbol_codeword_errors[cur_FEC_codeword]+(symbol_bit_errors[cur_FEC_codeword]>0)) < 23) begin
//                            epc[symbol_codeword_errors[cur_FEC_codeword]+ (symbol_bit_errors[cur_FEC_codeword]>0)] <= epc[symbol_codeword_errors[cur_FEC_codeword]+ (symbol_bit_errors[cur_FEC_codeword]>0)] + 1;
//                        end else begin
//                            epc[23]<=epc[23]+1;
//                        end
                              
                        if (symbol_codeword_errors[cur_FEC_codeword]+ (symbol_bit_errors[cur_FEC_codeword]>0) > T) begin
                            total_frame_errors <= total_frame_errors + 1;
                            //total_bit_errors_post <= total_bit_errors_post + bit_codeword_errors[cur_FEC_codeword]+symbol_bit_errors[cur_FEC_codeword];
                            total_bit_errors_post <= total_bit_errors_post + bit_codeword_errors[cur_FEC_codeword];
                        end
                    end
                    
                    
                end else begin
                
                symbol_bit_index[cur_FEC_codeword] <= symbol_bit_index[cur_FEC_codeword] +1;
                symbol_bit_errors[cur_FEC_codeword] <= symbol_bit_errors[cur_FEC_codeword] + error;
                
                end
                //current FEC symbol complete
                if (symbol_bit_index[cur_FEC_codeword] == M-1) begin
                    cur_FEC_codeword <= (cur_FEC_codeword+1)%W;
                    new_symbol <= 1;
                end
                
            end
        end
  end     
            
endmodule