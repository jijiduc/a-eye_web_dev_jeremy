# Segmentation results display

**Goal :** is to add in the file display table, a display of the results

## Results of segmentation

After the segmententation inference of the nnUNet model, the output folder (named `output_<user>_<timestamp>/`) contains :

- `<case_id>.nii.gz`
    - The result of inference

- `postprocessing.json`
    - Contains three sets of _? probable ?_ Dice Similarity Coefficient (DSC) scores :

    | Key | Description |
    |---|---|
    | `dc_per_class_raw` | unknown yet  |
    | `dc_per_class_pp_all` | unknown yet  |
    | `dc_per_class_pp_per_class` | unknown yet  |

     Here, this score means `unknown yet`

- `prediction_time.txt`
    - Total inference time in seconds

- `plans.pkl`
    - Binary pickle file containing the nnUNet planning informations
- `logs/`
    - Subfolder with four log files:

    | File | Content |
    |---|---|
    | `app.log` | Flask backend log |
    | `console.log` | console output log |
    | `*.out` | Stdout of inference |
    | `*.err` | Stderr of inference |

---

## Plan

- **Frontend** :
    - Use same dropdown mechanic as for the metada to display result on click
    - Integrate a 2d viewer (like the NiiVue extension of vscode) with metadata in a side, scrollable block