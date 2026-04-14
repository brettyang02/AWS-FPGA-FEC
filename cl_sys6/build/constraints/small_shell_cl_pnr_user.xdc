# =============================================================================
# Amazon FPGA Hardware Development Kit
#
# Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Amazon Software License (the "License"). You may not use
# this file except in compliance with the License. A copy of the License is
# located at
#
#    http://aws.amazon.com/asl/
#
# or in the "license" file accompanying this file. This file is distributed on
# an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, express or
# implied. See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================


# Add Small_Shell P&R constraints here

# Ignore CDC timing paths between AWS Shell (250MHz) and Core Clock
set_false_path -from [get_clocks clk_out1_clk_mmcm_a] -to [get_clocks clk_main_a0]
set_false_path -from [get_clocks clk_main_a0] -to [get_clocks clk_out1_clk_mmcm_a]

set_false_path -from [get_clocks clk_out2_clk_mmcm_b] -to [get_clocks clk_main_a0]
set_false_path -from [get_clocks clk_main_a0] -to [get_clocks clk_out2_clk_mmcm_b]

set_false_path -from [get_clocks clk_out1_clk_mmcm_c] -to [get_clocks clk_main_a0]
set_false_path -from [get_clocks clk_main_a0] -to [get_clocks clk_out1_clk_mmcm_c]
