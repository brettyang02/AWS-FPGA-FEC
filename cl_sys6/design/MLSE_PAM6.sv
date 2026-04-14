`timescale 1ns / 1ps

module MLSE_PAM6 #(
    parameter SYMBOL_SEPARATION = 48,
    parameter SIGNAL_RESOLUTION = 8,
    parameter ALPHA = 0.1,
    parameter TRACEBACK = 10,
    parameter METRIC_RESOLUTION = 20
)(
    input clk,
    input rstn,
    input signed [SIGNAL_RESOLUTION-1:0] signal_in,
    input signal_in_valid,
    
    output reg [2:0] symbol_out,  // 3 bits for 6 symbols
    output reg valid = 0
);

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
    
    wire signed [2*SIGNAL_RESOLUTION+1:0] e0 [5:0];
    wire signed [2*SIGNAL_RESOLUTION+1:0] e1 [5:0];
    wire signed [2*SIGNAL_RESOLUTION+1:0] e2 [5:0];
    wire signed [2*SIGNAL_RESOLUTION+1:0] e3 [5:0];
    wire signed [2*SIGNAL_RESOLUTION+1:0] e4 [5:0];
    wire signed [2*SIGNAL_RESOLUTION+1:0] e5 [5:0];
    
    genvar i;
    generate
        for (i=0; i<6; i=i+1) begin
            assign e0[i] = (signal_in - y0[i]) * (signal_in - y0[i]);
            assign e1[i] = (signal_in - y1[i]) * (signal_in - y1[i]);
            assign e2[i] = (signal_in - y2[i]) * (signal_in - y2[i]);
            assign e3[i] = (signal_in - y3[i]) * (signal_in - y3[i]);
            assign e4[i] = (signal_in - y4[i]) * (signal_in - y4[i]);
            assign e5[i] = (signal_in - y5[i]) * (signal_in - y5[i]);
        end
    endgenerate

    reg [METRIC_RESOLUTION-1:0] survivor_path_metrics [5:0] = '{default:0};
    reg [2:0] prev_survivor_path_state [5:0] = '{default:3'd0};

    reg [2:0] survivor0 [TRACEBACK-1:0] = '{default:2'd0};
    reg [2:0] survivor1 [TRACEBACK-1:0] = '{default:2'd0};
    reg [2:0] survivor2 [TRACEBACK-1:0] = '{default:2'd0};
    reg [2:0] survivor3 [TRACEBACK-1:0] = '{default:2'd0};
    reg [2:0] survivor4 [TRACEBACK-1:0] = '{default:2'd0};
    reg [2:0] survivor5 [TRACEBACK-1:0] = '{default:2'd0};

    reg [7:0] delay = 0;
    
    // Helper function to find min metric and corresponding prev state for each next state
    function automatic [METRIC_RESOLUTION+2:0] find_min;
        input [METRIC_RESOLUTION-1:0] candidates [5:0];
        integer j;
        reg [METRIC_RESOLUTION-1:0] min_val;
        reg [2:0] min_idx;
    begin
        min_val = candidates[0];
        min_idx = 0;
        for (j=1; j<6; j=j+1) begin
            if (candidates[j] < min_val) begin
                min_val = candidates[j];
                min_idx = j[2:0];
            end
        end
        find_min = {min_idx, min_val};
    end
    endfunction
    
    integer k;
    always @(posedge clk) begin
        if (!rstn) begin
            valid <= 0;
            delay <= 0;
            for (k=0; k<6; k=k+1) begin
                survivor_path_metrics[k] <= 0;
                prev_survivor_path_state[k] <= 0;
                survivor0[k] <= 0;
                survivor1[k] <= 0;
                survivor2[k] <= 0;
                survivor3[k] <= 0;
                survivor4[k] <= 0;
                survivor5[k] <= 0;
            end
        end else if (!signal_in_valid) begin
            valid <= 0;
            // Normalize path metrics if all negative (overflow prevention)
            if (&{survivor_path_metrics[0][METRIC_RESOLUTION-1],
                   survivor_path_metrics[1][METRIC_RESOLUTION-1],
                   survivor_path_metrics[2][METRIC_RESOLUTION-1],
                   survivor_path_metrics[3][METRIC_RESOLUTION-1],
                   survivor_path_metrics[4][METRIC_RESOLUTION-1],
                   survivor_path_metrics[5][METRIC_RESOLUTION-1]}) begin
                for (k=0; k<6; k=k+1)
                    survivor_path_metrics[k] <= {1'b0, survivor_path_metrics[k][METRIC_RESOLUTION-2:0]};
            end
        end else begin
            // For each next state, compute candidate path metrics from all prev states + branch metric
            reg [METRIC_RESOLUTION-1:0] candidates [5:0];
            reg [METRIC_RESOLUTION+2:0] result;
            
            // State 0
            candidates[0] = e0[0] + survivor_path_metrics[0];
            candidates[1] = e0[1] + survivor_path_metrics[1];
            candidates[2] = e0[2] + survivor_path_metrics[2];
            candidates[3] = e0[3] + survivor_path_metrics[3];
            candidates[4] = e0[4] + survivor_path_metrics[4];
            candidates[5] = e0[5] + survivor_path_metrics[5];
            result = find_min(candidates);
            prev_survivor_path_state[0] <= result[METRIC_RESOLUTION+2:METRIC_RESOLUTION]; // min index
            survivor_path_metrics[0] <= result[METRIC_RESOLUTION-1:0]; // min value
            
            // State 1
            candidates[0] = e1[0] + survivor_path_metrics[0];
            candidates[1] = e1[1] + survivor_path_metrics[1];
            candidates[2] = e1[2] + survivor_path_metrics[2];
            candidates[3] = e1[3] + survivor_path_metrics[3];
            candidates[4] = e1[4] + survivor_path_metrics[4];
            candidates[5] = e1[5] + survivor_path_metrics[5];
            result = find_min(candidates);
            prev_survivor_path_state[1] <= result[METRIC_RESOLUTION+2:METRIC_RESOLUTION];
            survivor_path_metrics[1] <= result[METRIC_RESOLUTION-1:0];
            
            // State 2
            candidates[0] = e2[0] + survivor_path_metrics[0];
            candidates[1] = e2[1] + survivor_path_metrics[1];
            candidates[2] = e2[2] + survivor_path_metrics[2];
            candidates[3] = e2[3] + survivor_path_metrics[3];
            candidates[4] = e2[4] + survivor_path_metrics[4];
            candidates[5] = e2[5] + survivor_path_metrics[5];
            result = find_min(candidates);
            prev_survivor_path_state[2] <= result[METRIC_RESOLUTION+2:METRIC_RESOLUTION];
            survivor_path_metrics[2] <= result[METRIC_RESOLUTION-1:0];
            
            // State 3
            candidates[0] = e3[0] + survivor_path_metrics[0];
            candidates[1] = e3[1] + survivor_path_metrics[1];
            candidates[2] = e3[2] + survivor_path_metrics[2];
            candidates[3] = e3[3] + survivor_path_metrics[3];
            candidates[4] = e3[4] + survivor_path_metrics[4];
            candidates[5] = e3[5] + survivor_path_metrics[5];
            result = find_min(candidates);
            prev_survivor_path_state[3] <= result[METRIC_RESOLUTION+2:METRIC_RESOLUTION];
            survivor_path_metrics[3] <= result[METRIC_RESOLUTION-1:0];
            
            // State 4
            candidates[0] = e4[0] + survivor_path_metrics[0];
            candidates[1] = e4[1] + survivor_path_metrics[1];
            candidates[2] = e4[2] + survivor_path_metrics[2];
            candidates[3] = e4[3] + survivor_path_metrics[3];
            candidates[4] = e4[4] + survivor_path_metrics[4];
            candidates[5] = e4[5] + survivor_path_metrics[5];
            result = find_min(candidates);
            prev_survivor_path_state[4] <= result[METRIC_RESOLUTION+2:METRIC_RESOLUTION];
            survivor_path_metrics[4] <= result[METRIC_RESOLUTION-1:0];
            
            // State 5
            candidates[0] = e5[0] + survivor_path_metrics[0];
            candidates[1] = e5[1] + survivor_path_metrics[1];
            candidates[2] = e5[2] + survivor_path_metrics[2];
            candidates[3] = e5[3] + survivor_path_metrics[3];
            candidates[4] = e5[4] + survivor_path_metrics[4];
            candidates[5] = e5[5] + survivor_path_metrics[5];
            result = find_min(candidates);
            prev_survivor_path_state[5] <= result[METRIC_RESOLUTION+2:METRIC_RESOLUTION];
            survivor_path_metrics[5] <= result[METRIC_RESOLUTION-1:0];
            
            // Update survivor paths (traceback)
            case (prev_survivor_path_state[0])
                3'd0: survivor0 <= {survivor0[TRACEBACK-2:0], 3'd0};
                3'd1: survivor0 <= {survivor1[TRACEBACK-2:0], 3'd0};
                3'd2: survivor0 <= {survivor2[TRACEBACK-2:0], 3'd0};
                3'd3: survivor0 <= {survivor3[TRACEBACK-2:0], 3'd0};
                3'd4: survivor0 <= {survivor4[TRACEBACK-2:0], 3'd0};
                3'd5: survivor0 <= {survivor5[TRACEBACK-2:0], 3'd0};
                default: survivor0 <= {survivor0[TRACEBACK-2:0], 3'd0};
            endcase
            
            case (prev_survivor_path_state[1])
                3'd0: survivor1 <= {survivor0[TRACEBACK-2:0], 3'd1};
                3'd1: survivor1 <= {survivor1[TRACEBACK-2:0], 3'd1};
                3'd2: survivor1 <= {survivor2[TRACEBACK-2:0], 3'd1};
                3'd3: survivor1 <= {survivor3[TRACEBACK-2:0], 3'd1};
                3'd4: survivor1 <= {survivor4[TRACEBACK-2:0], 3'd1};
                3'd5: survivor1 <= {survivor5[TRACEBACK-2:0], 3'd1};
                default: survivor1 <= {survivor0[TRACEBACK-2:0], 3'd1};
            endcase
            
            case (prev_survivor_path_state[2])
                3'd0: survivor2 <= {survivor0[TRACEBACK-2:0], 3'd2};
                3'd1: survivor2 <= {survivor1[TRACEBACK-2:0], 3'd2};
                3'd2: survivor2 <= {survivor2[TRACEBACK-2:0], 3'd2};
                3'd3: survivor2 <= {survivor3[TRACEBACK-2:0], 3'd2};
                3'd4: survivor2 <= {survivor4[TRACEBACK-2:0], 3'd2};
                3'd5: survivor2 <= {survivor5[TRACEBACK-2:0], 3'd2};
                default: survivor2 <= {survivor0[TRACEBACK-2:0], 3'd2};
            endcase
            
            case (prev_survivor_path_state[3])
                3'd0: survivor3 <= {survivor0[TRACEBACK-2:0], 3'd3};
                3'd1: survivor3 <= {survivor1[TRACEBACK-2:0], 3'd3};
                3'd2: survivor3 <= {survivor2[TRACEBACK-2:0], 3'd3};
                3'd3: survivor3 <= {survivor3[TRACEBACK-2:0], 3'd3};
                3'd4: survivor3 <= {survivor4[TRACEBACK-2:0], 3'd3};
                3'd5: survivor3 <= {survivor5[TRACEBACK-2:0], 3'd3};
                default: survivor3 <= {survivor0[TRACEBACK-2:0], 3'd3};
            endcase
            
            case (prev_survivor_path_state[4])
                3'd0: survivor4 <= {survivor0[TRACEBACK-2:0], 3'd4};
                3'd1: survivor4 <= {survivor1[TRACEBACK-2:0], 3'd4};
                3'd2: survivor4 <= {survivor2[TRACEBACK-2:0], 3'd4};
                3'd3: survivor4 <= {survivor3[TRACEBACK-2:0], 3'd4};
                3'd4: survivor4 <= {survivor4[TRACEBACK-2:0], 3'd4};
                3'd5: survivor4 <= {survivor5[TRACEBACK-2:0], 3'd4};
                default: survivor4 <= {survivor0[TRACEBACK-2:0], 3'd4};
            endcase
            
            case (prev_survivor_path_state[5])
                3'd0: survivor5 <= {survivor0[TRACEBACK-2:0], 3'd5};
                3'd1: survivor5 <= {survivor1[TRACEBACK-2:0], 3'd5};
                3'd2: survivor5 <= {survivor2[TRACEBACK-2:0], 3'd5};
                3'd3: survivor5 <= {survivor3[TRACEBACK-2:0], 3'd5};
                3'd4: survivor5 <= {survivor4[TRACEBACK-2:0], 3'd5};
                3'd5: survivor5 <= {survivor5[TRACEBACK-2:0], 3'd5};
                default: survivor5 <= {survivor0[TRACEBACK-2:0], 3'd5};
            endcase
            

            // Delay and output decision after traceback length
            if (delay < TRACEBACK + 1) begin
                delay <= delay + 1;
                valid <= 0;
            end else begin
                // Pick best survivor path with lowest metric
                reg [METRIC_RESOLUTION-1:0] min_metric = survivor_path_metrics[0];
                reg [2:0] min_state = 0;
                for (k=1; k<6; k=k+1) begin
                    if (survivor_path_metrics[k] < min_metric) begin
                        min_metric = survivor_path_metrics[k];
                        min_state = k[2:0];
                    end
                end
                // Output the oldest symbol in the survivor path for min_state
                case(min_state)
                    3'd0: symbol_out <= survivor0[TRACEBACK-1];
                    3'd1: symbol_out <= survivor1[TRACEBACK-1];
                    3'd2: symbol_out <= survivor2[TRACEBACK-1];
                    3'd3: symbol_out <= survivor3[TRACEBACK-1];
                    3'd4: symbol_out <= survivor4[TRACEBACK-1];
                    3'd5: symbol_out <= survivor5[TRACEBACK-1];
                    default: symbol_out <= 3'd0;
                endcase
                valid <= 1;
            end
        end
    end


endmodule
