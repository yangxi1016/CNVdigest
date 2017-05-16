#!/bin/sh
#
#SBATCH --job-name=MEDLINE-SENTS 
#SBATCH --ntasks-per-node=12 
#SBATCH --output=medline_sents.log 

#echo 'TID' $SLURM_ARRAY_TASK_ID

#echo "In Redis mode" >&2
#yhrun -n $1 python mpi_LIT_sentences.py $2 -s $3
#exit 0

if [ -e "$3" ]; then
  echo "In Redis mode" >&2
  yhrun -n $1 python mpi_LIT_sentences.py $2 -s $3
  exit 0
fi
if ! [ -e "$3" ]; then
  echo "In TSV mode" >&2
  yhrun -n $1 python mpi_LIT_sentences.py $2
  exit 0
fi
