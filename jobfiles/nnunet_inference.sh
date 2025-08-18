#!/bin/bash
#SBATCH --job-name=nnv1_inf    # job name
#SBATCH --nodes=1              # number of nodes to use
#SBATCH --ntasks=1             # total number of tasks across all nodes
#SBATCH --cpus-per-task=10     # cpu-cores per task (>1 if multi-threaded tasks)
#SBATCH --mem=64gb             # total memory (--mem-per-cpu per cpu-core 4G is default)
#SBATCH --time=1-23:59:00      # total run time limit (HH:MM:SS)
#SBATCH --gres=gpu:1           # number of gpus per node
#SBATCH --output=/home/jaime.barrancohernandez/results/nnunet/nnUNet_predict_jaime_barrancohernandez_unil_ch_20250818_142357.%N.%j.%a.out  # output log
#SBATCH --error=/home/jaime.barrancohernandez/results/nnunet/nnUNet_predict_jaime_barrancohernandez_unil_ch_20250818_142357.%N.%j.%a.err   # error log
#SBATCH --mail-type=BEGIN,END  # send email when job begins and ends
#SBATCH --mail-user=jaime.barrancohernandez@hevs.ch # email address to send notifications

apptainer exec \
    --nv \
    --bind /home/jaime.barrancohernandez/shared_datasets/nnunet/nnUNet:/opt/nnunet_resources \
    --bind /home/jaime.barrancohernandez/shared_datasets/nnunet/nnUNet/nnUNet_inference/input:/input \
    --bind /home/jaime.barrancohernandez/results/nnunet:/output \
    /home/jaime.barrancohernandez/shared_datasets/nnunet/nnunet.sif \
    nnUNet_predict \
    -i /input \
    -o /output \
    -tr nnUNetTrainerV2 \
    -ctr nnUNetTrainerV2CascadeFullRes \
    -m 3d_fullres \
    -p nnUNetPlansv2.1 \
    -t Task313_Eye