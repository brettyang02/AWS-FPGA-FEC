# AWS-FPGA-FEC

This is the cleaned up version of the capstone project of group 148, UofT ECE 2025-26.

This project is an FPGA-accelerated wireline channel emulator for BER analysis, on the AWS EC2 F2 platform, for PAM-6 400G Ethernet exploration. 

The design is based on the PAM-4 200G Ethernet design by Mr. Richard Barrie, which is open-sourced on his GitHub repo [AWS-FPGA-FEC](https://github.com/richard259/FPGA-FEC). We would like to thank Mr. Barrie for his amazing work.


## Repo structure

- `docs/`: contains the documentation of the project, including the reports and tutorial videos. It contains:
    - Manual.pdf: the complete steps to run the project on AWS, from machine creation to GUI setup. A .md version of the manual can be found [here](https://brett-yang.notion.site/Manual-for-running-the-design-on-AWS-EC2-F2-instance-2e7f48807ff580379cc0ef8710af2647?source=copy_link).
    - Two videos: one for Vivado & simulation walkthrough, and one for AWS flow.
    - Mr. Richard Barries's master thesis, which explains in detail his PAM4 design.
    Final report, demo slides, and poster for the capstone project.
- `cl_sys4,5,6/`: contains the RTL code for system 4, 5, 6 from Richard's project. Copy these folders to the aws-fpga repo to run (see the tutorial videos for details).
- `runtime/`: contains the code for the runtime environment on AWS, including the GUI noise files. Copy this folder to the F2 instance to run the design (see the tutorial videos for details).
- `cl_pam4_ref/`: contains the RTL code for the PAM4 reference design, in AWS.
- `sysAll_PAM6/`: Vivado project for the PAM6 designs, with testbenches included.

