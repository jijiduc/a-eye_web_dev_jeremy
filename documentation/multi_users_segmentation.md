# Multi-users segmentation (MUS)

The MUS aim to enable multiple users to use the segmentation pipeline in parallel.

Slurm informations are documented [in the initial map.](map_v0.md#L87)

## Initial assesment on MUS
*In this section, links were correctly referencing functions before the fixes*

Race concurrence and data loss issues in MUS context are present and need to be fixed :

On HPC side : 

- `modify_jobfile()`, in [utils.py:540](../utils.py#L540), creates unique folder per user on chacha (like `/home/jaime.barrancohernandez/results/nnunet/<email>_<timestamp>/`). The results of the segmentation are therefore isolated.

On the a-eye_web side :

1. in [config.py](../config.py) :
    - The local paths are shared in [config.py:13-18](../config.py#L13-L18) for all users. Therefore, files would be mixed between concurrent users.
    - The HPC input path is also shared in [config.py:25](../config.py#L25). Concurrent users would then mix files. 
    - The HPC jobfile is also shared in [config.py:27](../config.py#L27). Concurrent users would then overwrite jobs. Thus this is a very unlikely scenario as once `sbatch`is made, any later `scp` overwritte won't have effect on it. Only a tiny, almost-simulteanous, timeframe between two `/segment` calls would trigger this issue.

2. `clean_folders()`, in [utils.py:445](../utils.py#L445), clear every previous logs and file on each `/upload`, in [routes.py:166](../routes.py#L166). This would lead to data loss. When a second user uploads data, it clear the previous user's one.

## Tests

Using 2 differents users accounts (having 4 at disposal) , I tested the assesment that : 

- `clean_folders()` does clear data on each uploads.

Other suspected issues aren't testable as is, because the race concurrence issues are "prevented" by the data loss effect of `clean_folders()`.

### Encountered issues 

User experience :

- `/segment`, because of the `--wait` argument in the batch command, block a FLask thread and provide no status information/update. The effect is that the user can't go to another page of the aeye website while waiting for the results. In case of quiting/reloading, status and job following is lost. 


## Planned changes
For MUS correction

+ Paths isolation 
    - use the same logic of unique folder creation to solve the paths issues (using user email)
    - also isolated segmentation request input on HPC
+ `clean_folders()` at user scope to only wipe it's data

*Remark* a cleaner practice would never use path as direct reference, but derive it from a structured object (like dataclass)

For UX improvements :

+ Async task handling
    - use an async task handler for the `/segment`*.

*\*celery is suggestion made by Jaime Barranco*

## Changes made

- added `models.py` containing `UserPaths` dataclass. This to holds all user-scoped paths for a single user's pipeline run in a centralized place.

### `utils.py`

- added `get_user_paths(user_email)` at [utils.py:36](../utils.py#L36) : 
    - a function to get all `UserPaths` fields from the user's email
- added `clear_folder(folder)` at [utils.py:31](../utils.py#L31) :
    -  a wrap of `delete_files_in_folder` and `delete_subfolders`
- modified `clean_folders(user_email)` at [utils.py:483](../utils.py#L483) : 
    - changed to wipes data belonging to only a given user
- modified `modify_jobfile()` : 
    - added the `hpc_input` parameter to isolate the HPC input bind per user

### `main.py`

- modified `getSegmentation(user_email, paths)` : 
    - use a `UserPaths` object and old path reference updated

### `routes.py`

- modified `/upload`,  `/segment` and `/download` : 
    - extracts `user_email` from session and update the old path to now `paths` via `get_user_paths`


### Tests
I conducted 3 tests on the segmentation process updated. During those I used sample datas and monitor evolution with the job in queue (in Dance) on [chacha](cheat_sheet.md#L40), the live logs from the [running docker container](cheat_sheet.md#L16-24) and verification of upload on Filer01: 

- using 1 account : upload and full pipeline completed successfully
- using 2 accounts in simul: both users uploaded concurrently. Two separate jobs submitted and completed independently. Results stored in distinct user folders — no data mixing observed
- using 4 accounts in simul: all 4 users uploaded concurrently. Four separate HPC jobs submitted. Results came back in stages, each correctly isolated to the corresponding user's folder and filer path — no data mixing observed

#### Conclusion 
I conclude that these tests validate my implementation and successfully correct the MUS issues.