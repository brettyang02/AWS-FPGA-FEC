# Python

## Table of Contents

- [Overview](#Overview)
- [Folders](#Folders)
  - [noise](#noise)
  - [rtl_outputs](#rtl_outputs)
  - [syscommon_ref](#syscommon_ref)
  - [sys6_ref](#sys6_ref)
- [Files to Run](#Files-to-Run)
  - [sys6_model.py](#sys6_model.py)
  - [sys6_model_ber_snr_plot.py](#sys6_model_ber_snr_plot.py)
- [Python Quick Start Guide](#Python-Quick-Start-Guide)



## Overview

Python is a reference model built for verifying AWS BER-SNR results. It is intended to be a bit-accurate model to the System 6 PAM6 Verilog model. Developers can update the noise, rtl_outputs, sys6_ref, syscommon_ref files as needed. 

The files to run are `sys6_model.py` and `sys6_model_ber_snr_plot.py`.

## Folders

### noise

`noise` folder contains 10-20dB memory files to create noise. This is used to test behaviour of the model under different channel noise conditions in PAM6. Files are named `noiseXXdB_sep24.mem`, where `sep24` indicates the noise files are intended for `SYMBOL_SEPARATION = 24`. Users can update files to model various channel conditions.

### rtl_outputs

`rtl_outputs` contains folders with output bitstreams from Vivado Simulation of System6 PAM6. The files are obtained from running `sys6_PAM6_bit_extraction.sv` from `sysAll_PAM6/Sim` folder. Bitstream outputs are taken from each stage, `noiseXXdB/...` indicates the channel noise setting and `rtl_<module>.txt` indicates the module from which outputs are taken. The current version involves 1M bits of output from the PRBS stage. Users can update the files after running the Vivado Simulation with `sys6_PAM6_bit_extraction.sv`.

### syscommon_ref

`syscommon_ref` contains classes of modules that exist in System6 but also in other systems. Users can use these classes to build PAM6 versions of the other systems included in [FPGA-FEC](https://github.com/richard259/FPGA-FEC).

### sys6_ref

`sys6_ref` contains classes of modules that exist in System6 only. Users can use these classes to build System6 PAM6. 

## Files to Run

### sys6_model.py

This script runs the model at each noise level from 15dB to 20dB. For each noise level, it takes the corresponding `noise/noiseXX_dB_sep24.mem` and `rtl_outputs/noiseXXdB/*` files as input. Then the PRBS class generates sequences which passes through all classes in System 6. At the output, the following information are displayed: 

- `[XXdB] RTL-PRBS vs Ref-PRBS] Compared X bits (offset 0). Mismatches: X  BER=X` - compares PRBS outputs from `rtl_outputs` with that of the reference model. A mismatch count of 0 indicates the reference model is perfectly aligned with the Verilog design. 
- `[15dB] RTL-PreFEC vs Ref-PreFEC] Compared 999890 bits (offset 0). Mismatches: X  BER=X` - compares gray decoder outputs (prior to the final FEC block) from `rtl_outputs` with that of the reference model. The purpose of this output is to ensure the datapath is correct prior to error correction. A mismatch count of 0 indicates the reference model is perfectly aligned with the Verilog design. 
- Table with `Metric`, `RTL Value`, `Python Ref`, `Match?` information - compares FEC checker outputs. The purpose of this block is to ensure the FEC is modelled correctly. The columns correspond to the RTL net name at `prbs63_IL_FEC_checker` module output, value from rtl_output, value from current run of the Python reference model, and whether the values match within a specified tolerance. If the match value is ✅, it indicates the models are aligned within tolerance.

After each run, data is saved into `py_vs_rtl_BER_comparison_15db_20db.txt`.

### sys6_model_ber_snr_plot.py

This script runs the model at each noise level from 10dB to 20dB. For each noise level, it takes the corresponding `noise/noiseXX_dB_sep24.mem` files as input, and runs the model at the specified noise level. It increments the noise level once 100k post-FEC errors are reached, and proceeds to print error statistics and updates a plot. The purpose of this script is to compare the pre- and post- FEC errors with AWS results to ensure accuracy of the cloud implementation. The script starts outputting as soon as the script runs, the following information are displayed: 

- `STARTING SNR: X dB` - the channel noise for the current run
- `Post-FEC Errors: X` - a running tally of number of post-FEC errors
- `FINALIZED XX dB` - BER statistics for 100k post-FEC bit errors
- `Figure 1` - a plot with pre-FEC and post-FEC BER points in blue and red respectively

After each run, data is saved into `ber_sweep_10dB_20dB_100k_errors.txt`.

## Python Quick Start Guide

1. Clone `Python` folder
2. Run `python sys6_model.py` from inside `Python/`. Expect `py_vs_rtl_BER_comparison_15db_20db.txt` to be updated.
3. Run `python sys6_model_ber_snr_plot.py` from inside `Python/`. Expecct `ber_sweep_10dB_20dB_100k_errors.txt` to be updated.

