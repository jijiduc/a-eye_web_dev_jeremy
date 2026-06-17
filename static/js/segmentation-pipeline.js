let selection = [];
let segmentationResult = [];
const allowedExtensions = ['gz', 'zip', '7z', 'nii'];

// ensure no duplicate and correct file extension in the selection
function onSelectionFilter() {
    let selectedFiles = document.getElementById('file-input').files;
    let unallowedFiles = [];

    for (let i = 0; i < selectedFiles.length; i++) {
        let file = selectedFiles[i];
        let duplicate = selection.some(existing =>
            existing.name === file.name &&
            existing.size === file.size &&
            existing.lastModified === file.lastModified
        );
        if (!duplicate) {
            let extension = file.name.split('.').pop().toLowerCase();
            if (allowedExtensions.includes(extension)) {
                selection.push(file);
            } else {
                unallowedFiles.push(file.name);
            }
        }
    }

    if (unallowedFiles.length > 0) {
        onRejectionNotice(unallowedFiles);
    }

    renderFileList();
}

// Display a notice in case of selection's rejection
function onRejectionNotice(fileNames) {
    let notice = document.getElementById('rejection-tooltip');
    notice.innerHTML = '';

    fileNames.forEach(name => {
        let errorMessage = document.createElement('div');
        errorMessage.textContent = name + ' has been rejected: unsupported file format (only allowing: .nii, .nii.gz, .zip, .7z)';
        notice.appendChild(errorMessage);
    });

    notice.style.display = 'block';
    clearTimeout(window._rejectionTimer);

    window._rejectionTimer = setTimeout(function () {
        notice.style.display = 'none';
    }, 4000);
}

function unselectFile(index) {
    selection.splice(index, 1);
    renderFileList();
}

function renderFileList() {
    let fileList = document.getElementById('file-list');
    let title = document.getElementById('selected-files-title');

    if (selection.length > 0) {
        title.style.display = 'block';
        title.textContent = selection.length + ' selected file(s)';
        buildFileList(fileList, selection, unselectFile);
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

    ['upload-button', 'choose-file-button'].forEach(id => {
        const btn = document.getElementById(id);
        btn.disabled = true;
        btn.classList.remove('btn-success');
        btn.classList.add('btn-secondary');
    });

    const uploadFileList = document.getElementById('display-file-list');
    buildFileList(uploadFileList, selection);

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
                buildFileList(uploadFileList, selection, null, 'view metadata',
                    (file, idx, row) => { row.innerHTML = renderMetadataTable(data.metadata?.[file.name]); });
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

            alert(error.message || 'An error occurred while uploading files.');
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

    fetch('/segment', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            bar.classList.remove('progress-bar-animated', 'progress-bar-striped');

            if (data.download_url) {
                bar.textContent = 'Segmentation complete';

                const downloadButton = document.getElementById('download-button');
                downloadButton.disabled = false;
                downloadButton.classList.remove('btn-secondary');
                downloadButton.classList.add('btn-success');
                downloadButton.setAttribute('data-download-url', data.download_url);

                segmentationResult = data.result || [];
                document.getElementById('status-section').style.display = 'none';
                document.getElementById('segmentation-result-section').style.display = 'block';
                buildFileList(
                    document.getElementById('result-file-list'),
                    segmentationResult,
                    null,
                    'view results',
                    async (result, idx, row) => {
                        row.innerHTML = `
                            <div style="display:flex; width:100%; gap:8px; align-items:flex-start;">
                                <div style="flex:1; min-width:0; display:flex; flex-direction:column; gap:4px;">
                                    <small class="text-muted">Before segmentation</small>
                                    <canvas id="niivue-input-${idx}" style="display:block; width:100%; aspect-ratio:1/1;"></canvas>
                                </div>
                                <div id="info-panel-${idx}" style="flex:0 0 20%; overflow-y:auto; border-left:2px solid #33961d; border-right:2px solid #33961d; padding:0 8px;">
                                    ${renderSegmentationLegend()}
                                    <div style="margin-top:8px; font-size:0.78em; color:#212529;"><strong style="margin-bottom:5px;">Metadata</strong></div>
                                    <div>${renderMetadataTable(result.metadata)}</div>
                                </div>
                                <div style="flex:1; min-width:0; display:flex; flex-direction:column; gap:4px;">
                                    <small class="text-muted">After segmentation</small>
                                    <canvas id="niivue-output-${idx}" style="display:block; width:100%; aspect-ratio:1/1;"></canvas>
                                </div>
                            </div>`;
                        // to keep the center panel height in sync with niivues
                        const niivues = document.getElementById(`niivue-input-${idx}`);
                        const panel  = document.getElementById(`info-panel-${idx}`);
                        new ResizeObserver(() => {
                            panel.style.maxHeight = niivues.offsetHeight + 'px';
                        }).observe(niivues);

                        await window.initNiivue(`niivue-input-${idx}`, `/result/${result.input_name}`);
                        await window.initNiivue(`niivue-output-${idx}`, `/result/${result.name}`, 'eye-seg', 0, 9);
                    },
                    (result, idx, row) => { row.innerHTML = ''; }
                );
                alert(data.message);
            } else {
                throw new Error(data.message || 'segmentation failed');
            }
        })
        .catch(error => {
            bar.classList.remove('progress-bar-animated', 'progress-bar-striped');
            bar.classList.remove('bg-primary');
            bar.classList.add('bg-danger');
            bar.textContent = 'segmentation failed';

            alert(error.message || 'An error occurred during segmentation.');
            console.error('Error:', error);
        });
}

document.addEventListener('DOMContentLoaded', function () {
    document.getElementById('download-button').addEventListener('click', function () {
        const downloadUrl = this.getAttribute('data-download-url');
        if (downloadUrl) {
            window.location.href = downloadUrl;
        } else {
            alert('No file available for download. Please run segmentation first.');
        }
    });
});
