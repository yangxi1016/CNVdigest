#!/bin/sh

#SBATCH --job-name=MEDLINE2txt
#SBATCH --output=MEDLINE2txt_%A_%a.out
#SBATCH --error=MEDLINE2txt_%A_%a.err
#SBATCH --ntasks-per-node=8
##SBATCH --array=1-16
##SBATCH --time=01:00:00
##SBATCH --partition=sandyb
#SBATCH --ntasks=1
##SBATCH --mem-per-cpu=4000


#echo 'TID' $SLURM_ARRAY_TASK_ID
yhrun  python para_LIT.py $1 $SLURM_ARRAY_TASK_ID
