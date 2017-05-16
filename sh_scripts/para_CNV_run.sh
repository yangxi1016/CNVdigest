#!/bin/sh

yhrun -N 1 -n 1 --exclusive -p work python TagCNV_Wrap.py $1 $SLURM_ARRAY_TASK_ID $2
