`timescale 1ns / 1ps

module ISI_channel_one_tap_PAM6 #(
    parameter SIGNAL_RESOLUTION = 8,
    parameter SYMBOL_SEPARATION = 48,
    parameter ALPHA = 0.5)(
    
    input clk,
    input rstn,
    input [2:0] symbol_in,
    input symbol_in_valid,
    
    output reg signed [SIGNAL_RESOLUTION-1:0] signal_out,
    output reg signal_out_valid =0);
    
    reg signed [SIGNAL_RESOLUTION-1:0] y0 [5:0] = {
        (SYMBOL_SEPARATION*-2.5) + ALPHA*SYMBOL_SEPARATION*2.5,
        (SYMBOL_SEPARATION*-2.5) + ALPHA*SYMBOL_SEPARATION*1.5,
        (SYMBOL_SEPARATION*-2.5) + ALPHA*SYMBOL_SEPARATION*0.5,
        (SYMBOL_SEPARATION*-2.5) - ALPHA*SYMBOL_SEPARATION*0.5,
        (SYMBOL_SEPARATION*-2.5) - ALPHA*SYMBOL_SEPARATION*1.5,
        (SYMBOL_SEPARATION*-2.5) - ALPHA*SYMBOL_SEPARATION*2.5
    };
    
    reg signed [SIGNAL_RESOLUTION-1:0] y1 [5:0] = {
        (SYMBOL_SEPARATION*-1.5) + ALPHA*SYMBOL_SEPARATION*2.5,
        (SYMBOL_SEPARATION*-1.5) + ALPHA*SYMBOL_SEPARATION*1.5,
        (SYMBOL_SEPARATION*-1.5) + ALPHA*SYMBOL_SEPARATION*0.5,
        (SYMBOL_SEPARATION*-1.5) - ALPHA*SYMBOL_SEPARATION*0.5,
        (SYMBOL_SEPARATION*-1.5) - ALPHA*SYMBOL_SEPARATION*1.5,
        (SYMBOL_SEPARATION*-1.5) - ALPHA*SYMBOL_SEPARATION*2.5
    };
    
    reg signed [SIGNAL_RESOLUTION-1:0] y2 [5:0] = {
        (SYMBOL_SEPARATION*-0.5) + ALPHA*SYMBOL_SEPARATION*2.5,
        (SYMBOL_SEPARATION*-0.5) + ALPHA*SYMBOL_SEPARATION*1.5,
        (SYMBOL_SEPARATION*-0.5) + ALPHA*SYMBOL_SEPARATION*0.5,
        (SYMBOL_SEPARATION*-0.5) - ALPHA*SYMBOL_SEPARATION*0.5,
        (SYMBOL_SEPARATION*-0.5) - ALPHA*SYMBOL_SEPARATION*1.5,
        (SYMBOL_SEPARATION*-0.5) - ALPHA*SYMBOL_SEPARATION*2.5
    };
    
    reg signed [SIGNAL_RESOLUTION-1:0] y3 [5:0] = {
        (SYMBOL_SEPARATION*0.5) + ALPHA*SYMBOL_SEPARATION*2.5,
        (SYMBOL_SEPARATION*0.5) + ALPHA*SYMBOL_SEPARATION*1.5,
        (SYMBOL_SEPARATION*0.5) + ALPHA*SYMBOL_SEPARATION*0.5,
        (SYMBOL_SEPARATION*0.5) - ALPHA*SYMBOL_SEPARATION*0.5,
        (SYMBOL_SEPARATION*0.5) - ALPHA*SYMBOL_SEPARATION*1.5,
        (SYMBOL_SEPARATION*0.5) - ALPHA*SYMBOL_SEPARATION*2.5
    };
    
    reg signed [SIGNAL_RESOLUTION-1:0] y4 [5:0] = {
        (SYMBOL_SEPARATION*1.5) + ALPHA*SYMBOL_SEPARATION*2.5,
        (SYMBOL_SEPARATION*1.5) + ALPHA*SYMBOL_SEPARATION*1.5,
        (SYMBOL_SEPARATION*1.5) + ALPHA*SYMBOL_SEPARATION*0.5,
        (SYMBOL_SEPARATION*1.5) - ALPHA*SYMBOL_SEPARATION*0.5,
        (SYMBOL_SEPARATION*1.5) - ALPHA*SYMBOL_SEPARATION*1.5,
        (SYMBOL_SEPARATION*1.5) - ALPHA*SYMBOL_SEPARATION*2.5
    };
    
    reg signed [SIGNAL_RESOLUTION-1:0] y5 [5:0] = {
        (SYMBOL_SEPARATION*2.5) + ALPHA*SYMBOL_SEPARATION*2.5,
        (SYMBOL_SEPARATION*2.5) + ALPHA*SYMBOL_SEPARATION*1.5,
        (SYMBOL_SEPARATION*2.5) + ALPHA*SYMBOL_SEPARATION*0.5,
        (SYMBOL_SEPARATION*2.5) - ALPHA*SYMBOL_SEPARATION*0.5,
        (SYMBOL_SEPARATION*2.5) - ALPHA*SYMBOL_SEPARATION*1.5,
        (SYMBOL_SEPARATION*2.5) - ALPHA*SYMBOL_SEPARATION*2.5
    };
    
    //reg delay = 0;
    reg [2:0] prev_symbol = 3'd2;

    always @ (posedge clk) begin
        if (!rstn) begin
            // delay <= 0;
            signal_out_valid <= 0;
            prev_symbol <= 3'd2;
            
        end else begin
            if (symbol_in_valid) begin
                
                prev_symbol <= symbol_in;
                
                // wait 1 cycle before output signal is valid
                //if (delay == 0) begin
                //    delay <= 1;
                    
                //end else begin
                
                case (symbol_in)
                    3'd0: signal_out <= y0[prev_symbol];
                    3'd1: signal_out <= y1[prev_symbol];
                    3'd2: signal_out <= y2[prev_symbol];
                    3'd3: signal_out <= y3[prev_symbol];
                    3'd4: signal_out <= y4[prev_symbol];
                    3'd5: signal_out <= y5[prev_symbol];
                    default: signal_out <= 0;
                endcase

                signal_out_valid <= 1;
                //end
                
            end else begin
                signal_out_valid <= 0;
            end
        end
    end

endmodule

