#!/bin/bash

# Usage:
# ./upload_fpga.sh <BASE_FOLDER_NAME> <DCP_TARBALL_TO_INGEST>

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <BASE_FOLDER_NAME> <DCP_TARBALL_TO_INGEST>"
    exit 1
fi

# Arguments
BASE_FOLDER_NAME=$1
DCP_FOLDER_NAME=${BASE_FOLDER_NAME}
LOGS_FOLDER_NAME="${BASE_FOLDER_NAME}_logs"
DCP_TARBALL_TO_INGEST=$2

# Constants
DCP_BUCKET_NAME='uoft-capstone-2025148-bucket-tyra'
LOGS_BUCKET_NAME='uoft-capstone-2025148-log-bucket-tyra'
REGION='ca-central-1'

# Derived variables
DCP_TARBALL_NAME=$(basename ${DCP_TARBALL_TO_INGEST})
CL_DESIGN_NAME='cl_sys4_pam6'
CL_DESIGN_DESCRIPTION="Description of ${CL_DESIGN_NAME}"

echo "Creating S3 buckets (if not exist)..."
aws s3 mb s3://${DCP_BUCKET_NAME} --region ${REGION} || true
aws s3 mb s3://${DCP_BUCKET_NAME}/${DCP_FOLDER_NAME}/ || true
aws s3 mb s3://${LOGS_BUCKET_NAME}/${LOGS_FOLDER_NAME}/ --region ${REGION} || true

echo "Uploading DCP tarball to S3..."
aws s3 cp ${DCP_TARBALL_TO_INGEST} s3://${DCP_BUCKET_NAME}/${DCP_FOLDER_NAME}/

echo "Creating placeholder log file and uploading..."
touch LOGS_FILES_GO_HERE.txt
aws s3 cp LOGS_FILES_GO_HERE.txt s3://${LOGS_BUCKET_NAME}/${LOGS_FOLDER_NAME}/

echo "Creating FPGA image..."
aws ec2 create-fpga-image \
    --name ${CL_DESIGN_NAME} \
    --description "${CL_DESIGN_DESCRIPTION}" \
    --input-storage-location Bucket=${DCP_BUCKET_NAME},Key=${DCP_FOLDER_NAME}/${DCP_TARBALL_NAME} \
    --logs-storage-location Bucket=${LOGS_BUCKET_NAME},Key=${LOGS_FOLDER_NAME}/ \
    --region ${REGION}

echo "Done!"

