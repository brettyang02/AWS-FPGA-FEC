#!/bin/bash

# 1. Check if the AFI ID was provided as a command-line argument. If not, prompt the user.
if [ -z "$1" ]; then
    echo -n "Please enter the FPGA Image ID (e.g., afi-088b2bf689c7f1349): "
    read AFI_ID
else
    AFI_ID=$1
fi

# 2. Basic validation to ensure it looks like an AFI ID
if [[ ! "$AFI_ID" =~ ^afi-[a-zA-Z0-9]+$ ]]; then
    echo "Error: Invalid AFI ID format. It should start with 'afi-' followed by alphanumeric characters."
    exit 1
fi

echo "Modifying permissions to make $AFI_ID public to the network..."

# 3. Execute the AWS CLI command
aws ec2 modify-fpga-image-attribute \
    --fpga-image-id "$AFI_ID" \
    --attribute loadPermission \
    --operation-type add \
    --user-groups all

# 4. Check if the command succeeded and provide feedback
if [ $? -eq 0 ]; then
    echo "---"
    echo "Success! The AFI ($AFI_ID) is now public."
    echo "To verify the permissions at any time, run:"
    echo "aws ec2 describe-fpga-image-attribute --fpga-image-id $AFI_ID --attribute loadPermission"
else
    echo "---"
    echo "Error: Failed to modify the AFI."
    echo "Please check your AWS credentials, region settings, and ensure you own the AFI."
fi