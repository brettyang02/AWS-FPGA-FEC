`timescale 1ns / 1ps

module hard_slicer_PAM6 #(
    parameter SIGNAL_RESOLUTION = 8,
    parameter SYMBOL_SEPARATION = 48)(
    
    input clk,
    input rstn,
    input en,
    input signed [SIGNAL_RESOLUTION-1:0] signal_in,
    input signal_in_valid,
    output reg [2:0] symbol_out,
    output reg valid =0);
    
    reg signed [SIGNAL_RESOLUTION-1:0] y [5:0] = {SYMBOL_SEPARATION*2.5,SYMBOL_SEPARATION*1.5,SYMBOL_SEPARATION*0.5,SYMBOL_SEPARATION*-0.5,SYMBOL_SEPARATION*-1.5,SYMBOL_SEPARATION*-2.5};
    
    wire signed [SIGNAL_RESOLUTION:0] e [5:0]; 
    
    assign e[0] = signal_in-y[0];
    assign e[1] = signal_in-y[1];
    assign e[2] = signal_in-y[2];
    assign e[3] = signal_in-y[3];
    assign e[4] = signal_in-y[4];
    assign e[5] = signal_in-y[5];
    
    wire signed [2*SIGNAL_RESOLUTION+1:0] e2 [5:0]; 
    
    assign e2[0] = e[0]*e[0];
    assign e2[1] = e[1]*e[1];
    assign e2[2] = e[2]*e[2];
    assign e2[3] = e[3]*e[3];
    assign e2[4] = e[4]*e[4];
    assign e2[5] = e[5]*e[5];

    always @(posedge clk) begin
    
        if (!rstn || !signal_in_valid) begin
            valid <=0;
            
        end else begin
            
            valid <=1;
        
            if (e2[0]<=e2[1] && e2[0]<=e2[2] && e2[0]<=e2[3] && e2[0]<=e2[4] && e2[0]<=e2[5]) begin
                symbol_out <= 0;
            end else if (e2[1]<=e2[0] && e2[1]<=e2[2] && e2[1]<=e2[3] && e2[1]<=e2[4] && e2[1]<=e2[5]) begin
                symbol_out <= 1;
            end else if (e2[2]<=e2[0] && e2[2]<=e2[1] && e2[2]<=e2[3] && e2[2]<=e2[4] && e2[2]<=e2[5]) begin
                symbol_out <= 2;
            end else if (e2[3]<=e2[0] && e2[3]<=e2[1] && e2[3]<=e2[2] && e2[3]<=e2[4] && e2[3]<=e2[5]) begin
                symbol_out <= 3;
            end else if (e2[4]<=e2[0] && e2[4]<=e2[1] && e2[4]<=e2[2] && e2[4]<=e2[3] && e2[4]<=e2[5]) begin
                symbol_out <= 4;
            end else begin
                symbol_out <= 5;
            end
        
        end
    end

    
endmodule
