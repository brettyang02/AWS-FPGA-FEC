`timescale 1ns / 1ps

module gray_encode_PAM6 #(
    parameter USE_FRAMED = 0 // 0 = Standard Cross QAM-32 (Default), 1 = Framed-cross
)(
    input  wire       clk,
    input  wire       rstn,
    input  wire       en,
    input  wire       data,
    output reg  [2:0] symbol,
    output reg        valid
);

    reg [2:0] bit_count;
    reg [4:0] shift_reg;
    reg [3:0] I_tmp, Q_tmp;
    reg phaseI; // 1 = output I, 0 = output Q
    reg flag; // having a valid symbol in shift_reg

    always @(posedge clk) begin
        if (!rstn) begin
            bit_count <= 0;
            shift_reg <= 0;
            I_tmp <= 0;
            Q_tmp <= 0;
            phaseI <= 0;
            symbol <= 0;
            valid <= 0;
            flag <= 0;
        end 
        else if (en) begin
            // Shift in new bit
            shift_reg <= {shift_reg[3:0], data};
            bit_count <= bit_count + 1;

            // Default: no valid output
            valid <= 0;

            if (bit_count == 3'd5) begin
                
                if (USE_FRAMED == 1) begin
                    // --- NEW SCHEME: Framed-cross QAM-32 ---
                    case (shift_reg)
                        // I = 0
                        5'b00000: begin I_tmp <= 0; Q_tmp <= 0; end
                        5'b00100: begin I_tmp <= 0; Q_tmp <= 1; end
                        5'b00101: begin I_tmp <= 0; Q_tmp <= 2; end
                        5'b10101: begin I_tmp <= 0; Q_tmp <= 3; end
                        5'b10100: begin I_tmp <= 0; Q_tmp <= 4; end
                        5'b10000: begin I_tmp <= 0; Q_tmp <= 5; end
                        // I = 1 (Note: Q=1 and Q=4 are empty in the frame)
                        5'b00001: begin I_tmp <= 1; Q_tmp <= 0; end
                        5'b00111: begin I_tmp <= 1; Q_tmp <= 2; end
                        5'b10111: begin I_tmp <= 1; Q_tmp <= 3; end
                        5'b10001: begin I_tmp <= 1; Q_tmp <= 5; end
                        // I = 2
                        5'b00011: begin I_tmp <= 2; Q_tmp <= 0; end
                        5'b00010: begin I_tmp <= 2; Q_tmp <= 1; end
                        5'b00110: begin I_tmp <= 2; Q_tmp <= 2; end
                        5'b10110: begin I_tmp <= 2; Q_tmp <= 3; end
                        5'b10010: begin I_tmp <= 2; Q_tmp <= 4; end
                        5'b10011: begin I_tmp <= 2; Q_tmp <= 5; end
                        // I = 3
                        5'b01011: begin I_tmp <= 3; Q_tmp <= 0; end
                        5'b01010: begin I_tmp <= 3; Q_tmp <= 1; end
                        5'b01110: begin I_tmp <= 3; Q_tmp <= 2; end
                        5'b11110: begin I_tmp <= 3; Q_tmp <= 3; end
                        5'b11010: begin I_tmp <= 3; Q_tmp <= 4; end
                        5'b11011: begin I_tmp <= 3; Q_tmp <= 5; end
                        // I = 4 (Note: Q=1 and Q=4 are empty in the frame)
                        5'b01001: begin I_tmp <= 4; Q_tmp <= 0; end
                        5'b01111: begin I_tmp <= 4; Q_tmp <= 2; end
                        5'b11111: begin I_tmp <= 4; Q_tmp <= 3; end
                        5'b11001: begin I_tmp <= 4; Q_tmp <= 5; end
                        // I = 5
                        5'b01000: begin I_tmp <= 5; Q_tmp <= 0; end
                        5'b01100: begin I_tmp <= 5; Q_tmp <= 1; end
                        5'b01101: begin I_tmp <= 5; Q_tmp <= 2; end
                        5'b11101: begin I_tmp <= 5; Q_tmp <= 3; end
                        5'b11100: begin I_tmp <= 5; Q_tmp <= 4; end
                        5'b11000: begin I_tmp <= 5; Q_tmp <= 5; end
                        default:  begin I_tmp <= 0; Q_tmp <= 0; end
                    endcase
                end else begin
                    // --- ORIGINAL SCHEME: Standard Cross QAM-32 ---
                    case (shift_reg)
                        5'b00000: begin I_tmp <= 0; Q_tmp <= 0; end
                        5'b00100: begin I_tmp <= 0; Q_tmp <= 1; end
                        5'b00101: begin I_tmp <= 0; Q_tmp <= 2; end
                        5'b10101: begin I_tmp <= 0; Q_tmp <= 3; end
                        5'b10100: begin I_tmp <= 0; Q_tmp <= 4; end
                        5'b10000: begin I_tmp <= 0; Q_tmp <= 5; end
                        
                        5'b00001: begin I_tmp <= 1; Q_tmp <= 0; end
                        5'b00111: begin I_tmp <= 1; Q_tmp <= 2; end
                        5'b10111: begin I_tmp <= 1; Q_tmp <= 3; end
                        5'b10001: begin I_tmp <= 1; Q_tmp <= 5; end
                        
                        5'b00011: begin I_tmp <= 2; Q_tmp <= 0; end
                        5'b00010: begin I_tmp <= 2; Q_tmp <= 1; end
                        5'b00110: begin I_tmp <= 2; Q_tmp <= 2; end
                        5'b10110: begin I_tmp <= 2; Q_tmp <= 3; end
                        5'b10010: begin I_tmp <= 2; Q_tmp <= 4; end
                        5'b10011: begin I_tmp <= 2; Q_tmp <= 5; end
                        
                        5'b01011: begin I_tmp <= 3; Q_tmp <= 0; end
                        5'b01010: begin I_tmp <= 3; Q_tmp <= 1; end
                        5'b01110: begin I_tmp <= 3; Q_tmp <= 2; end
                        5'b11110: begin I_tmp <= 3; Q_tmp <= 3; end
                        5'b11010: begin I_tmp <= 3; Q_tmp <= 4; end
                        5'b11011: begin I_tmp <= 3; Q_tmp <= 5; end
                        
                        5'b01001: begin I_tmp <= 4; Q_tmp <= 0; end
                        5'b01111: begin I_tmp <= 4; Q_tmp <= 2; end
                        5'b11111: begin I_tmp <= 4; Q_tmp <= 3; end
                        5'b11001: begin I_tmp <= 4; Q_tmp <= 5; end
                        
                        5'b01000: begin I_tmp <= 5; Q_tmp <= 0; end
                        5'b01100: begin I_tmp <= 5; Q_tmp <= 1; end
                        5'b01101: begin I_tmp <= 5; Q_tmp <= 2; end
                        5'b11101: begin I_tmp <= 5; Q_tmp <= 3; end
                        5'b11100: begin I_tmp <= 5; Q_tmp <= 4; end
                        5'b11000: begin I_tmp <= 5; Q_tmp <= 5; end
                        
                        default:  begin I_tmp <= 0; Q_tmp <= 0; end
                    endcase
                end

                // Start with I phase next cycle
                phaseI <= 1;
                bit_count <= 1;
                flag <= 1;
            end
            else if (phaseI) begin
                // Output I phase
                symbol <= I_tmp;
                valid  <= 1;
                phaseI <= 0;
            end
            else if (!phaseI && flag) begin
                // Output Q phase
                symbol <= Q_tmp;
                valid <= 1;
                flag <= 0;
            end
        end
    end
endmodule

`timescale 1ns / 1ps

module gray_decode_PAM6 #(
    parameter USE_FRAMED = 0 // 0 = Standard Cross QAM-32 (Default), 1 = Framed-cross
)(
    input clk,
    input rstn,
    input en,
    input [2:0] symbol,
    output reg data,
    output reg valid
);

    reg [2:0] I_reg, Q_reg;
    reg [4:0] shift_reg;
    reg [2:0] bit_idx;
    reg phaseI;
    reg flag_ready;
    reg flag_start;
    reg flag_started;
    
    always @(posedge clk) begin
        if (!rstn) begin
            I_reg <= 0;
            Q_reg <= 0;
            shift_reg <= 0;
            bit_idx <= 3'b111; // init to an impossible value
            phaseI <= 1;
            data <= 0;
            valid <= 0;
            flag_ready <= 0;
            flag_start <= 0;
            flag_started <= 0;
        end
        else if (en) begin
            if (phaseI) begin
                I_reg <= symbol;
                phaseI <= 0;
            end
            else begin
                // Store Q symbol when phaseI == 0
                Q_reg <= symbol;
                flag_ready <= 1;
                phaseI <= 1;
            end
        end
        
        if (flag_ready) begin
            
            if (USE_FRAMED == 1) begin
                // --- NEW SCHEME: Framed-cross QAM-32 ---
                case ({I_reg, Q_reg})
                    {3'd0, 3'd0}: shift_reg <= 5'b00000;
                    {3'd0, 3'd1}: shift_reg <= 5'b00100;
                    {3'd0, 3'd2}: shift_reg <= 5'b00101;
                    {3'd0, 3'd3}: shift_reg <= 5'b10101;
                    {3'd0, 3'd4}: shift_reg <= 5'b10100;
                    {3'd0, 3'd5}: shift_reg <= 5'b10000;

                    {3'd1, 3'd0}: shift_reg <= 5'b00001;
                    {3'd1, 3'd2}: shift_reg <= 5'b00111;
                    {3'd1, 3'd3}: shift_reg <= 5'b10111;
                    {3'd1, 3'd5}: shift_reg <= 5'b10001;

                    {3'd2, 3'd0}: shift_reg <= 5'b00011;
                    {3'd2, 3'd1}: shift_reg <= 5'b00010;
                    {3'd2, 3'd2}: shift_reg <= 5'b00110;
                    {3'd2, 3'd3}: shift_reg <= 5'b10110;
                    {3'd2, 3'd4}: shift_reg <= 5'b10010;
                    {3'd2, 3'd5}: shift_reg <= 5'b10011;

                    {3'd3, 3'd0}: shift_reg <= 5'b01011;
                    {3'd3, 3'd1}: shift_reg <= 5'b01010;
                    {3'd3, 3'd2}: shift_reg <= 5'b01110;
                    {3'd3, 3'd3}: shift_reg <= 5'b11110;
                    {3'd3, 3'd4}: shift_reg <= 5'b11010;
                    {3'd3, 3'd5}: shift_reg <= 5'b11011;

                    {3'd4, 3'd0}: shift_reg <= 5'b01001;
                    {3'd4, 3'd2}: shift_reg <= 5'b01111;
                    {3'd4, 3'd3}: shift_reg <= 5'b11111;
                    {3'd4, 3'd5}: shift_reg <= 5'b11001;

                    {3'd5, 3'd0}: shift_reg <= 5'b01000;
                    {3'd5, 3'd1}: shift_reg <= 5'b01100;
                    {3'd5, 3'd2}: shift_reg <= 5'b01101;
                    {3'd5, 3'd3}: shift_reg <= 5'b11101;
                    {3'd5, 3'd4}: shift_reg <= 5'b11100;
                    {3'd5, 3'd5}: shift_reg <= 5'b11000;

                    default: shift_reg <= 5'b00000;
                endcase
            end else begin
                // --- ORIGINAL SCHEME: Standard Cross QAM-32 ---
                case ({I_reg, Q_reg})
                    {3'd0, 3'd0}: shift_reg <= 5'b00000;
                    {3'd0, 3'd1}: shift_reg <= 5'b00100;
                    {3'd0, 3'd2}: shift_reg <= 5'b00101;
                    {3'd0, 3'd3}: shift_reg <= 5'b10101;
                    {3'd0, 3'd4}: shift_reg <= 5'b10100;
                    {3'd0, 3'd5}: shift_reg <= 5'b10000;

                    {3'd1, 3'd0}: shift_reg <= 5'b00001;
                    {3'd1, 3'd2}: shift_reg <= 5'b00111;
                    {3'd1, 3'd3}: shift_reg <= 5'b10111;
                    {3'd1, 3'd5}: shift_reg <= 5'b10001;

                    {3'd2, 3'd0}: shift_reg <= 5'b00011;
                    {3'd2, 3'd1}: shift_reg <= 5'b00010;
                    {3'd2, 3'd2}: shift_reg <= 5'b00110;
                    {3'd2, 3'd3}: shift_reg <= 5'b10110;
                    {3'd2, 3'd4}: shift_reg <= 5'b10010;
                    {3'd2, 3'd5}: shift_reg <= 5'b10011;

                    {3'd3, 3'd0}: shift_reg <= 5'b01011;
                    {3'd3, 3'd1}: shift_reg <= 5'b01010;
                    {3'd3, 3'd2}: shift_reg <= 5'b01110;
                    {3'd3, 3'd3}: shift_reg <= 5'b11110;
                    {3'd3, 3'd4}: shift_reg <= 5'b11010;
                    {3'd3, 3'd5}: shift_reg <= 5'b11011;

                    {3'd4, 3'd0}: shift_reg <= 5'b01001;
                    {3'd4, 3'd2}: shift_reg <= 5'b01111;
                    {3'd4, 3'd3}: shift_reg <= 5'b11111;
                    {3'd4, 3'd5}: shift_reg <= 5'b11001;

                    {3'd5, 3'd0}: shift_reg <= 5'b01000;
                    {3'd5, 3'd1}: shift_reg <= 5'b01100;
                    {3'd5, 3'd2}: shift_reg <= 5'b01101;
                    {3'd5, 3'd3}: shift_reg <= 5'b11101;
                    {3'd5, 3'd4}: shift_reg <= 5'b11100;
                    {3'd5, 3'd5}: shift_reg <= 5'b11000;

                    default: shift_reg <= 5'b00000;
                endcase
            end
            
            flag_ready <= 0;
            flag_start <= 1;
            // Send out 5 bits MSB first over next 5 cycles
            bit_idx <= 0;
            
            if (flag_started) begin
                data <= shift_reg[4 - bit_idx]; // MSB first
                valid <= 1;
            end
        end
        else if (flag_start) begin
            data <= shift_reg[4 - bit_idx]; // MSB first
            valid <= 1;
            bit_idx <= bit_idx + 1;
            flag_started <= 1;
        end

    end
endmodule