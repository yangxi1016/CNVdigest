#!/bin/sh

#echo 'TID' $SLURM_ARRAY_TASK_ID
yhrun -n $1 python merge.py
