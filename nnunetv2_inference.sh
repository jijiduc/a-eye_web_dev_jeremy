#!/bin/bash
#SBATCH --job-name=nnv2_inf    # job name
#SBATCH --nodes=1              # number of nodes to use
#SBATCH --ntasks=1             # total number of tasks across all nodes
#SBATCH --cpus-per-task=10     # cpu-cores per task (>1 if multi-threaded tasks)
#SBATCH --mem=64gb             # total memory (--mem-per-cpu per cpu-core 4G is default)
#SBATCH --time=1-23:59:00      # total run time limit (HH:MM:SS)
#SBATCH --gres=gpu:1           # number of gpus per node
#SBATCH --output=%N.%j.%a.out  # output log
#SBATCH --error=%N.%j.%a.err   # error log
#SBATCH --mail-type=BEGIN,END  # send email when job begins and ends
#SBATCH --mail-user=jaime.barrancohernandez@hevs.ch

apptainer exec \
    --nv \
    --bind /home/jaime.barrancohernandez/datasets/nnunetv2/35subs:/opt/nnunet_resources \
    --bind /home/jaime.barrancohernandez/datasets/nnunetv2/35subs/nnUNet_inference/input:/input \
    --bind /home/jaime.barrancohernandez/results:/output \
    /home/jaime.barrancohernandez/datasets/nnunetv2/nnunetv2/nnunetv2.sif \
    nnUNetv2_predict \
    -d Dataset313_Eye \
    -i /input \
    -o /output \
    -f 0 1 2 3 4 \
    -tr nnUNetTrainer \
    -c 3d_fullres \
    -p nnUNetPlans