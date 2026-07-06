let selection = [];
let selectionCaseInfoMap = new Map();
let segmentationResult = [];
const MAX_CASES = 5;

// ensure no duplicate, correct file extension, and case limit in the selection
async function onSelectionFilter() {
    let selectedFiles = document.getElementById('file-input').files;
    let rejectedFileNames = [];
    let rejectedReasons = [];
    let newFiles = [];

    for (let i = 0; i < selectedFiles.length; i++) {
        let file = selectedFiles[i];
        let duplicate = selection.some(existing =>
            existing.name === file.name &&
            existing.size === file.size &&
            existing.lastModified === file.lastModified
        );
        if (!duplicate) {
            const nameLower = file.name.toLowerCase();
            const isValidExtension = nameLower.endsWith('.nii') ||
                nameLower.endsWith('.nii.gz') ||
                nameLower.endsWith('.zip') ||
                nameLower.endsWith('.7z');
            if (isValidExtension) {
                newFiles.push(file);
            } else {
                rejectedFileNames.push(file.name);
                rejectedReasons.push('unsupported file format (allowed: .nii, .nii.gz, .zip, .7z)');
            }
        }
    }

    // Checking selected cases informations to restrict if needed
    let maxCases = currentCaseCount();
    for (let i = 0; i < newFiles.length; i++) {
        let file = newFiles[i];
        let info = await getCaseInfo(file);

        if (maxCases + info.count > MAX_CASES) {
            rejectedFileNames.push(file.name);
            rejectedReasons.push('would exceed the ' + MAX_CASES + ' cases limit');
        } else {
            selection.push(file);
            selectionCaseInfoMap.set(file, info);
            maxCases += info.count;
        }
    }
    // display the notice if needed
    if (rejectedFileNames.length > 0) {
        onRejectionNotice(rejectedFileNames, rejectedReasons);
    }
    // to reset a previously selected input
    document.getElementById('file-input').value = '';
    renderFileList();
}

function currentCaseCount() {
    let total = 0;
    selectionCaseInfoMap.forEach(
        info => { total += info.count; }
    );
    return total;
}

// Display a notice in case of selection's rejection
function onRejectionNotice(names, reasons) {
    let notice = document.getElementById('rejection-tooltip');
    notice.innerHTML = '';

    for (let i = 0; i < names.length; i++) {
        let msg = document.createElement('div');
        msg.textContent = names[i] + ' has been rejected: ' + reasons[i];
        notice.appendChild(msg);
    }

    notice.style.display = 'block';
    clearTimeout(window._rejectionTimer);
    window._rejectionTimer = setTimeout(function () { notice.style.display = 'none'; }, 6000);
}

function unselectFile(index) {
    selectionCaseInfoMap.delete(selection[index]);
    selection.splice(index, 1);
    renderFileList();
}

function renderFileList() {
    let fileList = document.getElementById('file-list');
    let title = document.getElementById('selected-files-title');

    if (selection.length > 0) {
        const cases = currentCaseCount();
        title.style.display = 'block';
        title.innerHTML = ` <span class="badge me-1" style="background:var(--btn-secondary-bg);">
                                ${selection.length} file ${selection.length > 1 ? 's' : ''}</span>
                            <span class="badge" style="background:var(--link-color);">
                                ${cases} / ${MAX_CASES} cases</span>`;
        buildFileList(fileList, selection, unselectFile, [], selectionCaseInfoMap);
    } else {
        title.style.display = 'none';
        fileList.innerHTML = '';
    }

    let uploadButton = document.getElementById('upload-button');
    if (selection.length > 0) {
        uploadButton.classList.remove('btn-secondary');
        uploadButton.classList.add('btn-success');
        uploadButton.disabled = false;
    } else {
        uploadButton.classList.remove('btn-success');
        uploadButton.classList.add('btn-secondary');
        uploadButton.disabled = true;
    }
}

/*
* Handles the multi-file upload :
*   - managing UI states
*   - preparing form data
*   - submitting files to the server
*/
function uploadFiles() {
    let formData = new FormData();

    selection.forEach(file => formData.append('files[]', file));

    ['rejection-tooltip', 'selected-files-title', 'file-list'].forEach(id => {
        document.getElementById(id).style.display = 'none';
    });

    ['upload-button', 'select-file-button'].forEach(id => {
        const btn = document.getElementById(id);
        btn.disabled = true;
        btn.classList.remove('btn-success');
        btn.classList.add('btn-secondary');
    });

    const uploadFileList = document.getElementById('display-file-list');
    buildFileList(uploadFileList, selection, null, [], selectionCaseInfoMap);

    document.getElementById('status-section').style.display = 'block';

    const bar = document.getElementById('progress-bar');
    bar.classList.add('progress-bar-animated', 'progress-bar-striped');
    bar.classList.remove('bg-danger');
    bar.classList.add('bg-success');
    bar.textContent = 'upload in progress...';

    fetch('/upload', {
        method: 'POST',
        body: formData
    })
        .then(response => response.json())
        .then(data => {
            bar.classList.remove('progress-bar-animated', 'progress-bar-striped');

            if (data.status === 'success') {
                bar.textContent = 'Upload complete';
                const caseList = [];

                selection.forEach(file => {
                    const info = selectionCaseInfoMap.get(file);
                    const fileMetadata = data.metadata?.[file.name] || {};
                    if (info?.labels) {
                        info.labels.forEach(label => {
                            caseList.push({ name: label, metadata: fileMetadata[label] || {} });
                        });
                    } else {
                        caseList.push({ name: file.name, metadata: fileMetadata[file.name] || {} });
                    }
                });
                buildFileList(uploadFileList, caseList, null, [
                    {
                        label: 'view metadata',
                        onOpen: (caseItem, idx, row) => { row.innerHTML = renderMetadataTable(caseItem.metadata); },
                    }
                ]);
                alert(data.message);

                const segmentButton = document.getElementById('segment-button');
                segmentButton.classList.remove('btn-secondary');
                segmentButton.classList.add('btn-success');
                segmentButton.disabled = false;
            } else {
                throw new Error(data.message || 'Upload failed');
            }
        })
        .catch(error => {
            bar.classList.remove('progress-bar-animated', 'progress-bar-striped');
            bar.classList.remove('bg-success');
            bar.classList.add('bg-danger');
            bar.textContent = 'Upload failed';

            alert(error.message);
            console.error('Error:', error);
        });
}

/*
* Handles the file segmentation process :
*   - managing the UI state
*   - initiating a server request
*   - processing the response
*/
function segmentFiles() {
    ['segment-button', 'upload-button'].forEach(id => {
        const btn = document.getElementById(id);
        btn.disabled = true;
        btn.classList.remove('btn-success');
        btn.classList.add('btn-secondary');
    });

    const bar = document.getElementById('progress-bar');
    bar.classList.add('progress-bar-animated', 'progress-bar-striped');
    bar.classList.remove('bg-success', 'bg-danger');
    bar.classList.add('bg-primary');
    bar.textContent = 'segmentation in progress...';

    const popup = new bootstrap.Modal(document.getElementById('segmentation-popup-notice'));
    popup.show();

    fetch('/segment', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            popup.hide();
            bar.classList.remove('progress-bar-animated', 'progress-bar-striped');

            if (data.download_url) {
                bar.textContent = 'Segmentation complete';

                const downloadButton = document.getElementById('download-button');
                downloadButton.disabled = false;
                downloadButton.classList.remove('btn-secondary');
                downloadButton.classList.add('btn-success');
                downloadButton.setAttribute('data-download-url', data.download_url);

                const biomarkersButton = document.getElementById('biomarkers-button');
                biomarkersButton.disabled = false;
                biomarkersButton.classList.remove('btn-secondary');
                biomarkersButton.classList.add('btn-success');

                segmentationResult = data.result || [];
                document.getElementById('status-section').style.display = 'none';
                document.getElementById('segmentation-result-section').style.display = 'block';
                buildResultFileList(segmentationResult);
                alert(data.message);
            } else {
                throw new Error(data.message || 'segmentation failed');
            }
        })
        .catch(error => {
            popup.hide();
            bar.classList.remove('progress-bar-animated', 'progress-bar-striped');
            bar.classList.remove('bg-primary');
            bar.classList.add('bg-danger');
            bar.textContent = 'segmentation failed';

            alert(error.message);
            console.error('Error:', error);
        });
}


/*
* Handles the biomarkers extraction process:
*   - managing UI state
*   - initiating the server request
*   - processing the response
*/
function extractBiomarkers() {
    const biomarkersButton = document.getElementById('biomarkers-button');
    biomarkersButton.disabled = true;
    biomarkersButton.classList.remove('btn-success');
    biomarkersButton.classList.add('btn-secondary');

    // hide the metadata list
    document.getElementById('display-file-list').style.display = 'none';
    // add the progress bar
    const bar = document.getElementById('progress-bar');
    bar.classList.add('progress-bar-animated', 'progress-bar-striped');
    bar.classList.remove('bg-success', 'bg-primary', 'bg-danger');
    bar.classList.add('bg-warning');
    bar.textContent = 'biomarkers extraction in progress...';

    document.getElementById('status-section').style.display = 'block';

    const caseNames = segmentationResult.map(r => r.name);

    fetch('/biomarkers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ case_names: caseNames })
    })
        .then(response => response.json())
        .then(data => {
            bar.classList.remove('progress-bar-animated', 'progress-bar-striped');

            if (data.status === 'success') {
                bar.textContent = 'Biomarkers extraction complete';

                biomarkersButton.disabled = true;
                biomarkersButton.classList.remove('btn-success');
                biomarkersButton.classList.add('btn-secondary');

                document.getElementById('display-file-list').style.display = '';
                document.getElementById('status-section').style.display = 'none';

                // merge biomarker data into segmentationResult and rebuild the list
                data.results.forEach(biomarkerResult => {
                    const match = segmentationResult.find(r => r.name === biomarkerResult.case_name);
                    if (match) match.biomarkers = biomarkerResult;
                });
                buildResultFileList(segmentationResult);
                alert(data.message);
            } else {
                throw new Error(data.message || 'Extraction failed');
                document.getElementById('display-file-list').style.display = '';
            }
        })
        .catch(error => {
            bar.classList.remove('progress-bar-animated', 'progress-bar-striped');
            bar.classList.remove('bg-warning');
            bar.classList.add('bg-danger');
            bar.textContent = 'Biomarkers extraction failed';

            document.getElementById('display-file-list').style.display = '';

            alert(error.message);
            console.error('Error:', error);
        });
}


/*
* Build the result file list with a segmentation action per row
*/
function buildResultFileList(results) {
    const dropdowns = [
        {
            label: 'segmentation',
            onOpen: async (result, idx, row) => {
                row.innerHTML = renderSegmentationDropdownContent(result, idx);

                const overlay = document.getElementById(`niivue-overlay-${idx}`);
                const panel = document.getElementById(`info-panel-${idx}`);

                new ResizeObserver(() => {
                    panel.style.maxHeight = overlay.offsetHeight + 'px';
                }).observe(overlay);

                await window.initNiivueOverlay(`niivue-overlay-${idx}`,
                                                 `/result/${result.input_name}`,
                                                  `/result/${result.both_name}`);
                await window.initNiivue(`niivue-eyes-${idx}`, `/result/${result.both_name}`, 'eye-seg', 0, 9);
            },
            onClose: (result, idx, row) => { row.innerHTML = ''; }
        }
    ];

    if (results.some(r => r.biomarkers)) {
        dropdowns.push({
            label: 'biomarkers',
            onOpen: (result, idx, row) => { row.innerHTML = renderBiomarkersDropdownContent(result.biomarkers); },
            onClose: (result, idx, row) => { row.innerHTML = ''; }
        });
    }

    if ((results.some(r => r.biomarkers?.left?.reference || r.biomarkers?.right?.reference))) {
        dropdowns.push({
            label: 'statistics',
            onOpen: (result, idx, row) => {
                row.innerHTML = renderStatisticalDropdownContent(result.biomarkers);
                addMouseWheelZoom(row);
            },
            onClose: (result, idx, row) => { row.innerHTML = ''; }
        });
    }

    buildFileList(document.getElementById('result-file-list'), results, null, dropdowns);
}


// Click behaviour on the download button
document.getElementById('download-button').addEventListener('click', function () {
    window.location.href = this.getAttribute('data-download-url');
});

// for .wheel-zoom image : escape pressed -> image back to its original form
document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    document.querySelectorAll('.wheel-zoom img').forEach((img) => img.panzoom?.reset());
});
