#!/bin/sh

#echo 'TID' $SLURM_ARRAY_TASK_ID
yhrun -N 1 -n 1 --exclusive -p work python TaggerOne_Wrap.py $1 $SLURM_ARRAY_TASK_ID $2
