#!/bin/bash
set -e  # Exit on any error

# Validate required inputs
if [ $# -lt 2 ]; then
    echo "Usage: $0 <design_name> <clock_recipe>"
    echo "Example: $0 cl_sys6 A2"
    exit 1
fi

DESIGN="$1"
CLOCK_RECIPE="$2"

echo "=== Starting AWS FPGA Build Process ==="
echo "Design: $DESIGN"
echo "Clock Recipe: $CLOCK_RECIPE"

# Navigate to aws-fpga and setup HDK
echo "[1/6] Navigating to aws-fpga..."
cd ~/capstone/aws-fpga

echo "[2/6] Setting up HDK environment..."
source hdk_setup.sh # Global scripts fails, just use this piece of the shell as a reference for now

# Navigate to design directory
echo "[3/6] Navigating to design directory..."
cd hdk/cl/examples/$DESIGN/

# Set CL_DIR
echo "[4/6] Setting CL_DIR..."
export CL_DIR=$(pwd)
echo "CL_DIR = $CL_DIR"

# Navigate to build scripts
echo "[5/6] Navigating to build scripts..."
cd build/scripts

# Run build
echo "[6/6] Running build..."
./aws_build_dcp_from_cl.py -c $DESIGN --mode small_shell --aws_clk_gen --clock_recipe_a $CLOCK_RECIPE

echo "=== Build Complete ==="