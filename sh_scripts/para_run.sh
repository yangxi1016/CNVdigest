#!/bin/sh

#echo 'TID' $SLURM_ARRAY_TASK_ID
yhrun -n 1 -p work python para_LIT.py $1 $SLURM_ARRAY_TASK_ID $2
