## State of the segmentation/slurm 

### At start 

#### Segmentation

The segmentation process is handled by `getSegmentation` function in `main.py`.

The pipeline is : 
1. Uploading a file with MRI data (supported format : (.nii.gz / .zip /
    .7z / .nii)) in the segmentation page. 

2. This call the `/upload` route to :
    - Clear previous logs and files before uploading new ones
    - upload the files after some conversion, compression and renaming to the HPC

3. The cleaned datas are then used in the `/segment` route as :
        - Update the jobfile template (?) and copy it in HPC folder
        - launch the inference (nnUNet) and wait for result
        - Copy output folder from HPC
        - Copy the logs

4. The results are at disposal for download in the `/download` route

#### Inference command 
```bash
inference_command = f'ssh {SSH_USER} "sbatch --wait --partition=Dance --account=mattech --qos=normal {jobfile_hpc}"'
```
