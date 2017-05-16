#!/bin/sh

#echo 'TID' $SLURM_ARRAY_TASK_ID

if [ -e "$5" ]; then
  echo "In Redis mode" >&2
  yhrun -n $1 python mpi_LIT_medline.py $2 $3 $4 -s $5
  exit 0
fi

if ! [ -e "$5" ]; then
  echo "In TXT mode" >&2
  yhrun -n $1 python mpi_LIT_medline.py $2 $3 $4
  exit 0
fi

