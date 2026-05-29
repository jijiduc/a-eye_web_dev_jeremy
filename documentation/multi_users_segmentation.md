# Multi-users segmentation (MUS)

The MUS aim to enable multiple users to use the segmentation pipeline in parallel.

Slurm informations are documented [in the initial map.](map_v0.md#L87)

## Initial assesment on MUS

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

For UX improvements :

+ Async taks handling
    - use an async task handler for the `/segment`*.







*\*celery is suggestion made by Jaime Barranco*