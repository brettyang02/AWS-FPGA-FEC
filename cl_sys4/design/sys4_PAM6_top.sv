`timescale 1ns/1ps

//Author: Richard Barrie

//single-part link with analog AWGN and Hamming 128,120 inner FEC

module sys4_PAM6_top #(
    
    parameter SIGNAL_RESOLUTION = 8,
    parameter SYMBOL_SEPARATION = 24,
    
    
    //random seeds
    parameter [63:0] RANDOM_64 [3:0] = {64'h2629488426294884, 64'h588f503226294884, 64'h2629188426294884, 64'h2645841236254785},
    

    parameter M = 10)(
    
    input wire clk,
    input wire en,
    input wire rstn,
    
    
    //amount of RS FEC symbol IL
    input wire [3:0] n_interleave,
    input wire ifec_en,
    
    //for loading markov model probabilities during reset
    input wire [63:0] probability_in,
    input wire [31:0] probability_idx,
       
	output wire [63:0] total_bits,
	output wire [63:0] total_bit_errors_pre,
	output wire [63:0] total_bit_errors_post,
	output wire [63:0] total_frames,
	output wire [63:0] total_frame_errors);
	
    //parameter [63:0] RANDOM_64 [3:0] = {64'h2629488426294884, 64'h588f503226294884, 64'h2629488426294884, 64'h2645841236454785};
    wire binary_data;
    wire binary_data_valid;
    
    prbs63_120_8 #(.SEED(RANDOM_64[0])) prbs(
        .clk(clk),
        .en(en),
        .rstn(rstn),
        .data(binary_data),
        .valid(binary_data_valid));
                
    wire binary_data_enc;
    wire binary_data_enc_valid;
    
    hamming_enc encoder (
        .clk(clk),
        .rstn(rstn),
        .data_in(binary_data),
        .data_in_valid(binary_data_valid),
        .data_out(binary_data_enc),
        .valid(binary_data_enc_valid));
    
    wire [2:0] symbol;
    wire symbol_valid;
    
    gray_encode_PAM6 ge(
        .clk(clk),
        .data(binary_data_enc),
        .en(binary_data_enc_valid),
        .rstn(rstn),
        .symbol(symbol),
        .valid(symbol_valid));
    
    
    // Generate voltage levels
    wire [SIGNAL_RESOLUTION-1:0] signal;
    wire signal_valid;
    
    pam_6_encode #(.SIGNAL_RESOLUTION(SIGNAL_RESOLUTION), .SYMBOL_SEPARATION(SYMBOL_SEPARATION)) pe(
        .clk(clk),
        .rstn(rstn),
        .symbol_in(symbol),
	    .symbol_in_valid(symbol_valid),
        .signal_out(signal),
        .signal_out_valid(signal_valid));
        
    
    wire signed [SIGNAL_RESOLUTION-1:0] noise;
    wire noise_valid;
    
//    reg [63:0] probability;
//    reg [31:0] probability_idx;
    
    random_noise #(.SIGNAL_RESOLUTION(SIGNAL_RESOLUTION),
        .RNG_SEED0(RANDOM_64[1]),
        .RNG_SEED1(RANDOM_64[2]),
        .RNG_SEED2(RANDOM_64[3])) r_noise(
        .clk(clk),
        .rstn(rstn),
        .en(en),
        .noise_out(noise),
        .valid(noise_valid),
        .probability_in(probability_in),
        .probability_idx(probability_idx)
        );
        
        
    wire signed [SIGNAL_RESOLUTION-1:0] ch_noise;
    wire ch_noise_valid;
        
    noise_adder #(.SIGNAL_RESOLUTION(SIGNAL_RESOLUTION)) na(
        .clk(clk),
        .rstn(rstn),
        .en(en),
        .noise_in(noise),
        .noise_in_valid(noise_valid),
        .signal_in(signal),
        .signal_in_valid(signal_valid),
        .signal_out(ch_noise),
        .valid(ch_noise_valid)
        );
        
    wire [2:0] symbol_r;
    wire symbol_r_valid;
    
    hard_slicer_PAM6 #(.SIGNAL_RESOLUTION(SIGNAL_RESOLUTION),
        .SYMBOL_SEPARATION(SYMBOL_SEPARATION)) slicer (
        .clk(clk),
        .rstn(rstn),
        .en(en),
        .signal_in(ch_noise),
        .signal_in_valid(ch_noise_valid),
        .symbol_out(symbol_r),
        .valid(symbol_r_valid)
        );
        
    wire binary_data_r;    
    wire binary_data_r_valid;
    
    gray_decode_PAM6 gd(
        .clk(clk),
        .symbol(symbol_r),
        .rstn(rstn),
        .en(symbol_r_valid),
        .data(binary_data_r),
        .valid(binary_data_r_valid));
        
    wire binary_data_dec;
    wire binary_data_dec_valid;
    
    hamming_dec decoder (
        .clk(clk),
        .rstn(rstn),
        .ifec_en(ifec_en),
        .data_in(binary_data_r),
        .data_in_valid(binary_data_r_valid),
        .data_out(binary_data_dec),
        .valid(binary_data_dec_valid));
                
    prbs63_IL_FEC_checker #(
        .SEED(RANDOM_64[0])) fec (
        .clk(clk),
        .data(binary_data_dec),
        .en(binary_data_dec_valid),
        .rstn(rstn),
        .n_interleave_in(n_interleave),
        .total_bits(total_bits),
        .total_bit_errors_post(total_bit_errors_post),
        .total_bit_errors_pre(total_bit_errors_pre),
        .total_frames(total_frames),
        .total_frame_errors(total_frame_errors));
		
endmodule