#!/bin/sh

#echo 'TID' $SLURM_ARRAY_TASK_ID

if [ -e "$6" ]; then
  echo "In Redis mode" >&2
  yhrun -n $1 python mpi_LIT_pmc.py $2 $3 $4 $5 -s $6
  exit 0
fi

if ! [ -e "$6" ]; then
  echo "In TXT mode" >&2
  yhrun -n $1 python mpi_LIT_pmc.py $2 $3 $4 $5
  exit 0
fi


