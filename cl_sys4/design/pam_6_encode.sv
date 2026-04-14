`timescale 1ns / 1ps

module pam_6_encode #(
    parameter SIGNAL_RESOLUTION = 8,
    parameter SYMBOL_SEPARATION = 48)(
    input clk,
    input rstn,
    input [2:0] symbol_in,
    input symbol_in_valid,
    output reg [SIGNAL_RESOLUTION-1:0] signal_out, //128 to -127 as signed int
    output reg signal_out_valid = 0);

    always @ (posedge clk) begin
        if (!rstn) begin
            signal_out_valid <= 0;
        end else begin
            if (symbol_in_valid) begin
                case(symbol_in)
                    3'b000: signal_out <= -SYMBOL_SEPARATION*2.5;
                    3'b001: signal_out <= -SYMBOL_SEPARATION*1.5;
                    3'b010: signal_out <= -SYMBOL_SEPARATION*0.5;
                    3'b011: signal_out <= SYMBOL_SEPARATION*0.5;
                    3'b100: signal_out <= SYMBOL_SEPARATION*1.5;
                    3'b101: signal_out <= SYMBOL_SEPARATION*2.5;
                endcase
                signal_out_valid <= 1;
            end else begin
                signal_out_valid <= 0; // To align with previous valid signal in order to convert back to binary data
            end
        end
    end
endmodule
