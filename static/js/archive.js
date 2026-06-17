let archiveWorker = null;

// Listing the files in a .zip/.7z via worker
function listArchiveEntries(file) {
    return new Promise((resolve, reject) => {
        archiveWorker ??= new Worker('/static/js/archive-worker.js');
        let id = crypto.randomUUID();

        const onMessage = (event) => {
            if (event.data.id !== id) {
                return;
            }

            archiveWorker.removeEventListener('message', onMessage);

            if (event.data.error) {
                reject(event.data.error);
            } else {
                resolve(event.data.paths);
            }
        };

        archiveWorker.addEventListener('message', onMessage);

        file.arrayBuffer().then(buffer => {
            archiveWorker.postMessage({ id, name: file.name, buffer });
        });
    });
}

// Getting cases number and providing labels
async function getCaseInfo(file) {
    let nameLower = file.name.toLowerCase();

    // 1. if archive, get the list of files in it
    if (nameLower.endsWith('.zip') || nameLower.endsWith('.7z')) {
        let paths = await listArchiveEntries(file);
        let visitedDicom = new Set();
        let labels = [];

        // Prepare labels for the different cases
        for (let path of paths) {
            path = path.toLowerCase();

            if (path.endsWith('.nii') || path.endsWith('.nii.gz')) {
                labels.push(path.endsWith('.gz') ? path.slice(0, -3) : path);
            } else if (path.endsWith('.dcm')) {
                let dossier = path.includes('/') ? path.slice(0, path.lastIndexOf('/')) : '';

                if (!visitedDicom.has(dossier)) {
                    visitedDicom.add(dossier);
                    labels.push(dossier ? `${dossier}/<DICOM series>` : 'DICOM series');
                }
            }
        }

        return { count: labels.length || 1, labels: labels.length ? labels : null };
    }

    // 2. if .nii.gz
    if (nameLower.endsWith('.nii.gz')) {
        return { count: 1, labels: [file.name.slice(0, -3)] };
    }

    // 3, else simple .nii / default
    return { count: 1, labels: null };
}
