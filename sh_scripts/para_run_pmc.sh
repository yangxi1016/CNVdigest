#!/bin/sh

#SBATCH --job-name=PMC2txt
#SBATCH --output=PMC2txt_%A_%a.out
#SBATCH --error=PMC2txt_%A_%a.err
#SBATCH --ntasks-per-node=8
##SBATCH --array=1-16
##SBATCH --time=01:00:00
##SBATCH --partition=sandyb
#SBATCH --ntasks=1
##SBATCH --mem-per-cpu=4000


#echo 'TID' $SLURM_ARRAY_TASK_ID
yhrun  python para_LIT_pmc.py $1 $SLURM_ARRAY_TASK_ID
