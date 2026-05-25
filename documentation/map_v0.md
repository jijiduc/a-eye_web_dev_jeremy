# Initial map of the repo/website state 

## A-eye web
This is a web platform (Flask) for external medical specialist in eye to share, get processed and retrieve eye MRI datas. 
After an Auth0 authentification, MRI datas can be uploaded. Thoses can be used in the automated eye segmentation module (running on chacha : HPC cluster). After the segmentation, the resulting NIfTIs can be be downloaded. The results are also savec on a mat-tech lab shared HEVS storage server : Filer01.

## Python files

| file | usage |
|---|---|
| `app.py` | initialise the Flask app, register modules (Aut0, Mail) and the routes |
| `config.py` | the one place for hardcoded values |
| `routes.py` | HTTP routes endpoints |
| `main.py` | `getSegmentation()` — segmentation process using slurm on chacha |
| `utils.py` | helpers functions (i.e. DICOM to NIfTI, Auth0, log, docker,...) |
| `run.py` | entry point to create Flask instance |
