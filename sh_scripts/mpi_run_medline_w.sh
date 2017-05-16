#!/bin/sh

#echo 'TID' $SLURM_ARRAY_TASK_ID
yhrun -n $1 python mpi_LIT_medline_ww.py
