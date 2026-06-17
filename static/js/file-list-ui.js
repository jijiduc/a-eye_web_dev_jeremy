/*
* Make the extracted metadata table for display in file list
*/
function renderMetadataTable(fields) {
    if (!fields || !Object.keys(fields).length)
        return '<em class="text-muted p-2 d-block">No metadata available.</em>';
    const rows = Object.entries(fields).map(([key, val]) => {
        const display = Array.isArray(val) ? val.join(', ') : String(val);
        return `<tr>
            <td style="white-space:nowrap; font-weight:500; width:40%;">${key}</td>
            <td style="word-break:break-all;">${display}</td>
        </tr>`;
    }).join('');
    return `<table class="table table-sm table-bordered table-striped table-hover mb-0" style="font-size:0.78em;">
        <thead class="table-dark"><tr><th>Field</th><th>Value</th></tr></thead>
        <tbody>${rows}</tbody>
    </table>`;
}

/*
*   To render the legends of ROI after segmentation
*/
function renderSegmentationLegend() {
    const labels = window.EYE_LABELS || [];
    const legends = labels.slice(1).map(({name, color}) =>
        `<div style="display: flex; align-items: center; gap: 6px; padding: 2px 0;">
            <span style="width: 12px; height: 12px; background: rgb(${color}); border: 1px solid #aaa; border-radius: 2px;"></span>
            <span>${name}</span>
        </div>`
    ).join('');
    return `<div style="font-size:0.78em; color:#212529;"><strong>Labels of segmentation</strong>${legends}</div>`;
}

/*
*   To build the different lists of files displayed,
*   with optional remove button / metadata dropdown
*/
function buildFileList(ulElement, files, onRemove = null, dropdownLabel = '', onOpen = null, onClose = null) {
    ulElement.innerHTML = '';
    const header = document.createElement('li');
    header.className = 'list-group-item d-flex justify-content-between align-items-center';
    header.style.backgroundColor = '#e9ecef';
    header.style.color = '#212529';

    const headerFilename = document.createElement('span');
    headerFilename.style.fontWeight = 'bold';
    headerFilename.textContent = 'filename';
    header.appendChild(headerFilename);

    ulElement.appendChild(header);

    files.forEach((file, index) => {
        const fileRow = document.createElement('li');
        fileRow.className = 'list-group-item d-flex justify-content-between align-items-center';

        const nameSpan = document.createElement('span');
        nameSpan.textContent = file.name;
        fileRow.appendChild(nameSpan);

        if (onRemove) {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'btn btn-danger btn-sm';
            btn.textContent = 'remove';
            btn.onclick = () => onRemove(index);
            fileRow.appendChild(btn);
        }

        if (onOpen) {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'btn btn-primary btn-sm';
            btn.textContent = dropdownLabel;
            fileRow.appendChild(btn);
            ulElement.appendChild(fileRow);

            const dropdownRow = document.createElement('li');
            dropdownRow.className = 'list-group-item';
            dropdownRow.style.cssText = 'display:none; background-color:#f8f9fa;';
            ulElement.appendChild(dropdownRow);

            btn.onclick = async () => {
                const collapsed = dropdownRow.style.display === 'none';
                dropdownRow.style.display = collapsed ? 'block' : 'none';
                btn.textContent = collapsed ? 'hide' : dropdownLabel;
                if (collapsed) {
                    await onOpen(file, index, dropdownRow);
                } else if (onClose) {
                    onClose(file, index, dropdownRow);
                }
            };
        } else {
            ulElement.appendChild(fileRow);
        }
    });
}
