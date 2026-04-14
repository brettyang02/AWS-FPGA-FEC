`timescale 1ns / 1ps

module random_noise #(
	parameter SIGNAL_RESOLUTION = 8,
    parameter RNG_SEED0 = 64'h1391A0B350391A0B,
    parameter RNG_SEED1 = 64'h50391A0B0392A7D3,
    parameter RNG_SEED2 = 64'h0392A7D350391A0B) (
    input clk,
    input rstn,
    input en,
    input [63:0] probability_in,
    input [31:0] probability_idx,
    
    output wire signed [SIGNAL_RESOLUTION-1:0] noise_out,
    output reg valid = 0);
    
    
    reg [63:0] probability [63:0];    
    
    wire [63:0] random;
    
    //wire random_valid;
    
    urng_64 #(
        .SEED0(RNG_SEED0),
        .SEED1(RNG_SEED1),
        .SEED2(RNG_SEED2)
        ) rng (
        .clk(clk),
        .rstn(rstn),
        .en(en),
        .data_out(random));
        
    reg signed [SIGNAL_RESOLUTION-1:0] noise_mag;
    
    wire signed [1:0] sign;
    
    assign sign[1] = random[0];
    assign sign[0] = 1'b1;
    
    assign noise_out = noise_mag*sign;
            
    always @(posedge clk) begin
        if (!rstn) begin
            valid <= 0;
            if (probability_idx != 32'hFFFFFFFF) begin
                probability[probability_idx] <= probability_in;
            end
        end else begin
            if (en) begin
                valid <= 1;
                noise_mag <= 7'd63; // default max value, in case random is so large
    
                begin: search_loop
                for (int i = 0; i < 64; i++) begin
                    if (random <= probability[i]) begin
                        noise_mag <= i[6:0];
                        disable search_loop; // exit the loop
                    end
                end
                end
    
            end else begin
                valid <= 0;
            end
        end
    end
        
endmodule


module noise_adder #(
	parameter SIGNAL_RESOLUTION = 8) (
    input clk,
    input rstn,
    input en,
    input signed [SIGNAL_RESOLUTION-1:0] signal_in,
    input signal_in_valid,
    input signed [SIGNAL_RESOLUTION-1:0] noise_in,
    input noise_in_valid,
    output reg signed [SIGNAL_RESOLUTION-1:0] signal_out,
    output reg valid = 0);
    
    wire signed [SIGNAL_RESOLUTION:0] sum; 
    
    assign sum = signal_in+noise_in;
    
    wire signed [SIGNAL_RESOLUTION-1:0] sum_shift; 
    assign sum_shift = {sum[SIGNAL_RESOLUTION],sum[SIGNAL_RESOLUTION-2:0]};
    
    always @ (posedge clk)
        
        //all probability values are loaded while resetn is held low
        if (!rstn) begin
            valid <= 0;
        end else begin
            if (en == 1 && signal_in_valid == 1 && noise_in_valid ==1) begin
                if (sum[SIGNAL_RESOLUTION] == 1'b0 && sum[SIGNAL_RESOLUTION-1] == 1'b1) begin
                    signal_out <= {{1'b0},{(SIGNAL_RESOLUTION-1){1'b1}}};
                end else if (sum[SIGNAL_RESOLUTION] == 1'b1 && sum[SIGNAL_RESOLUTION-1] == 1'b0) begin
                    signal_out <= {{1'b1},{(SIGNAL_RESOLUTION-1){1'b0}}};
                end else begin
                    signal_out <= sum_shift;
                end
                valid<=1;
            end else begin
                valid <= 0;
            end
        end
    
endmodule


module urng_64 #(
    parameter SEED0 = 64'd5030521883283424767,
    parameter SEED1 = 64'd18445829279364155008,
    parameter SEED2 = 64'd18436106298727503359
    )(
    // System signals
    input clk,                    // system clock
    input rstn,                   // system synchronous reset, active low

    // Data interface
    input en,                     // clock enable
    output reg valid,         // output data valid
    output reg [63:0] data_out    // output data
    );

    // Local variables
    reg [63:0] z1, z2, z3;
    wire [63:0] z1_next, z2_next, z3_next;
    
    //assign data_out = data_out_full[31:0];
    
    // Update state
    assign z1_next = {z1[39:1], z1[58:34] ^ z1[63:39]};
    assign z2_next = {z2[50:6], z2[44:26] ^ z2[63:45]};
    assign z3_next = {z3[56:9], z3[39:24] ^ z3[63:48]};
    
    always @ (posedge clk) begin
        if (!rstn) begin
            z1 <= SEED0;
            z2 <= SEED1;
            z3 <= SEED2;
        end
        else if (en) begin
            z1 <= z1_next;
            z2 <= z2_next;
            z3 <= z3_next;
        end
    end
    
    // Output data
    always @ (posedge clk) begin
        if (!rstn)
            valid <= 1'b0;
        else
            valid <= en;
    end
    
    always @ (posedge clk) begin
        if (!rstn)
            data_out <= 64'd0;
        else
            data_out <= (z1_next ^ z2_next ^ z3_next);

    end
    
endmodule


module random_noise_skip #(
	parameter SIGNAL_RESOLUTION = 8,
    parameter RNG_SEED0 = 64'h1391A0B350391A0B,
    parameter RNG_SEED1 = 64'h50391A0B0392A7D3,
    parameter RNG_SEED2 = 64'h0392A7D350391A0B) (
    input clk,
    input rstn,
    input en,
    input [63:0] probability_in,
    input [31:0] probability_idx,
    
    output wire signed [SIGNAL_RESOLUTION-1:0] noise_out,
    output reg valid = 0);
    
    
    reg [63:0] probability [63:0];    
    
    wire [63:0] random;
    
    //wire random_valid;
    
    urng_64 #(
        .SEED0(RNG_SEED0),
        .SEED1(RNG_SEED1),
        .SEED2(RNG_SEED2)
        ) rng (
        .clk(clk),
        .rstn(rstn),
        .en(en),
        .data_out(random));
        
    reg signed [SIGNAL_RESOLUTION-1:0] noise_mag;
    
    wire signed [1:0] sign;
    
    assign sign[1] = random[0];
    assign sign[0] = 1'b1;
    
    assign noise_out = noise_mag*sign;

    reg skip = 0;
            
    always @(posedge clk) begin
        if (!rstn) begin
            valid <= 0;
            if (probability_idx != 32'hFFFFFFFF) begin
                probability[probability_idx] <= probability_in;
            end
        end else begin
            if (en) begin
                noise_mag <= 7'd63; // default max value, in case random is so large
                if (skip ==0) begin
                    valid <=0;
                    skip <= ~skip;
                end else begin 
                    valid <=1;
                    skip <= ~skip;
                
    
                    begin: search_loop
                    for (int i = 0; i < 64; i++) begin
                        if (random <= probability[i]) begin
                            noise_mag <= i[6:0];
                            disable search_loop; // exit the loop
                        end
                    end
                    end
                end
    
            end else begin
                valid <= 0;
            end
        end
    end
        
endmodule

module FIR_filter #(
    //length of pulse response (UI) eg: if the pulse response is h = [1 0.5], PULSE_RESPONSE_LENGTH = 2
    parameter PULSE_RESPONSE_LENGTH = 5,
    //bit-resolution of output signal
    parameter SIGNAL_RESOLUTION = 7)(
    
    input clk,
    input rstn,
    input signed [SIGNAL_RESOLUTION-1:0] signal_in,
    input signal_in_valid,
    
    //specify channel coefficient and index when rstn is low

    //input signed [SIGNAL_RESOLUTION+1:0] channel_coefficient,
    //input [7:0] channel_coefficient_idx,
    
    output reg signed [SIGNAL_RESOLUTION-1:0] signal_out,
    output reg signal_out_valid =0);
       
    //stores channel pulse response
    //LPF
    reg signed [SIGNAL_RESOLUTION+1:0] channel_coefficient_reg [PULSE_RESPONSE_LENGTH-1:0] = {10'b0010110101,10'b0010010001,10'b0001011011,10'b0000110110,10'b0000010010};
       
    // stores time-dealayed memory of input signal
    reg signed [SIGNAL_RESOLUTION-1:0] channel_memory [PULSE_RESPONSE_LENGTH-1:0] = '{default:'0};
    
    //stores element-wise multiplication of channel coefficients with channel memory
    wire signed [2*SIGNAL_RESOLUTION:0] channel_memory_scaled [PULSE_RESPONSE_LENGTH-1:0];
        
    genvar i;
    
    //instantiate our custom multiplication blocks for each channel coefficient
    generate
        for (i=0; i < PULSE_RESPONSE_LENGTH; i=i+1) begin    
            
            assign channel_memory_scaled[i] = channel_memory[i]*channel_coefficient_reg[i];
                        
        end
    endgenerate
    
    //sum them up to calculate channel output
    wire signed [2*SIGNAL_RESOLUTION:0] channel_memory_scaled_sum [PULSE_RESPONSE_LENGTH-1:0];
    assign channel_memory_scaled_sum[0] = channel_memory_scaled[0];
    
    generate
        for (i=1; i < PULSE_RESPONSE_LENGTH; i=i+1) begin
            assign channel_memory_scaled_sum[i] = channel_memory_scaled_sum[i-1] + channel_memory_scaled[i];
        end
    endgenerate

    wire [SIGNAL_RESOLUTION-1:0] channel_out;

    wire [1:0] round;
    
    assign round = channel_memory_scaled_sum[PULSE_RESPONSE_LENGTH-1][SIGNAL_RESOLUTION-1];
    
    assign channel_out = (channel_memory_scaled_sum[PULSE_RESPONSE_LENGTH-1]>>>SIGNAL_RESOLUTION) + round;
    
    //reg delay = 0;


    always @ (posedge clk) begin
        if (!rstn) begin
            //delay <= 0;
            signal_out_valid <= 0;
            
            // program channel coefficients when rstn is low
            // channel_coefficient_idx = 0 corresponds to first (precursor) coefficient
            // channel_coefficient_idx = 8'hFF when no coefficient is being programmed
            //if (channel_coefficient_idx != 8'hFF) begin
            //    channel_coefficient_reg[channel_coefficient_idx] <= channel_coefficient;
            //end
            
        end else begin
            if (signal_in_valid) begin
                
                //update channel memory shift register
                channel_memory[PULSE_RESPONSE_LENGTH-1:1] <= channel_memory[PULSE_RESPONSE_LENGTH-2:0];
                channel_memory[0] <= signal_in;
                
                // wait 1 cycle before output signal is valid
                //if (delay == 0) begin
                //    delay <= 1;
                    
                //end else begin
                
                    //output signal
                    signal_out <= channel_out;
                    signal_out_valid <= 1;
                
                //end
                
            end else begin
                //signal_out_valid <= 0;
            end
        end
    end

endmodule