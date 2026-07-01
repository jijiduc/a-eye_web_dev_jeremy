const VOLUME_LABELS = {
    vol_lens: 'lens',
    vol_globe: 'globe',
    vol_optic_nerve: 'optic nerve',
    vol_intraconal_fat: 'intraconal fat',
    vol_extraconal_fat: 'extraconal fat',
    vol_lateral_rectus_muscle: 'lateral rectus muscle',
    vol_medial_rectus_muscle: 'medial rectus muscle',
    vol_inferior_rectus_muscle: 'inferior rectus muscle',
    vol_superior_rectus_muscle: 'superior rectus muscle',
    vol_total: 'Total segmented volume',
};

/**
 * Render the metadata table
 * @param {string} fields - The key-values object containing the metadata
 */

function renderMetadataTable(fields) {
    // check that the fields dictionnary isn't empty
    if (!Object.keys(fields).length) {
        return `<p class="text-warning d-block"> Metadata not available...</p>`
    }
    let row=``;
    for (const key in fields) {
        const value = fields?.[key];
        const cleanedValue = Array.isArray(value) ? value.join(', ') : String(value);

        row += `
            <tr>
                <td class="label-cell">${key}</td>
                <td class="value-cell">${cleanedValue}</td>
            </tr>`;
    }
    return `
    <table class="styled-table">
        <thead>
            <tr>
                <th>Fields</th>
                <th>Values</th>
            </tr>
        </thead>
        <tbody>
            ${row}
        </tbody>
    </table>`;
}


/*
*   To render the legends of ROI after segmentation
*/
function renderSegmentationLegend() {
    const legends = window.EYE_LABELS.slice(1).map(({ name, color }) =>
        `<div class="seg-legend-bloc">
            <span class="seg-legend-swatch" style="background: rgb(${color})"></span>
            <span>${name}</span>
        </div>`
    ).join('');
    return `<div class="seg-legend">
                <strong>Labels of segmentation</strong>${legends}
            </div>`;
}

// Appends sub-rows for each case in a selected file
function addLabelRow(ulElement, labels) {
    labels.forEach(label => {
        const row = document.createElement('li');
        row.className = 'list-group-item fl-case-label';
        row.textContent = label;
        ulElement.appendChild(row);
    });
}

/*
*   Build a file list with an optional remove button and dropdowns buttons
*/
function buildFileList(ulElement, files, onRemove = null, dropdowns = [], caseInfoMap = null) {
    ulElement.innerHTML = '';

    const header = document.createElement('li');
    header.className = 'list-group-item d-flex justify-content-between align-items-center';
    header.style.backgroundColor = 'var(--progress-bg)';
    header.style.color = 'var(--text-color)';

    const headerFilename = document.createElement('span');
    headerFilename.style.fontWeight = 'bold';
    headerFilename.textContent = 'Selected files/cases';
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

        if (dropdowns.length > 0) {
            const btnGroup = document.createElement('div');
            btnGroup.className = 'd-flex gap-2';
            fileRow.appendChild(btnGroup);
            ulElement.appendChild(fileRow);

            dropdowns.forEach(({ label, onOpen, onClose }) => {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'btn btn-primary btn-sm';
                btn.textContent = label;
                btnGroup.appendChild(btn);

                const dropdownRow = document.createElement('li');
                dropdownRow.className = 'list-group-item';
                dropdownRow.style.display = 'none';
                ulElement.appendChild(dropdownRow);

                btn.onclick = async () => {
                    const collapsed = dropdownRow.style.display === 'none';
                    dropdownRow.style.display = collapsed ? 'block' : 'none';
                    btn.textContent = collapsed ? 'hide' : label;
                    if (collapsed) {
                        await onOpen(file, index, dropdownRow);
                    } else if (onClose) {
                        onClose(file, index, dropdownRow);
                    }
                };
            });
        } else {
            ulElement.appendChild(fileRow);
        }

        const info = caseInfoMap?.get(file);
        if (info?.labels) {
            addLabelRow(ulElement, info.labels);
        }
    });
}

/*
* Render the axial length measurements table
*/
function renderAxialLengthTable(sideData) {
    const rows = [
        ['Axial length', sideData.axial_length, 'mm'],
        ['AL (cornea)', sideData.axial_length_cornea, 'mm'],
        ['Extra anterior', sideData.extra_anterior, 'mm'],
    ].map(([label, value, unit]) => {
        const display = value !== null ? value.toFixed(2) + ' ' + unit : '—';
        return `<tr>
            <td class="label-cell">${label}</td>
            <td class="value-cell">${display}</td>
        </tr>`;
    }).join('');
    return `<table class="styled-table">
        <thead><tr><th>Measure</th><th>Value</th></tr></thead>
        <tbody>${rows}</tbody>
    </table>`;
}

/*
* Render a table for volumetry measurements
*/
function renderVolumetryTable(sideData) {
    const labels = window.EYE_LABELS || [];
    const rows = Object.entries(VOLUME_LABELS).map(([key, displayName]) => {
        const val = sideData[key];
        const display = val !== null ? val.toFixed(1) + ' mm³' : '—';
        const label = labels.find(label => label.name === displayName);
        const dot = label
            ? `<span style="display:inline-block; width:10px; height:10px; background:rgb(${label.color}); border:1px solid var(--swatch-border); border-radius:2px; margin-right:4px;"></span>`
            : '';
        return `<tr>
            <td class="label-cell">${dot}${displayName}</td>
            <td class="value-cell">${display}</td>
        </tr>`;
    }).join('');
    return `<table class="styled-table">
        <thead><tr><th>Region</th><th>Volume</th></tr></thead>
        <tbody>${rows}</tbody>
    </table>`;
}

/*
* Build the HTML content shown inside the biomarkers dropdown row
*/
function renderBiomarkersDropdownContent(results) {
    return `<div>
    <details class="mb-3" style="font-size:0.82em;">
        <summary style="cursor: pointer; font-weight: 600; list-style: none; display: flex; align-items: center; gap: 6px; color:var(--summary-link-color);">
            <i class="fa-solid fa-circle-info"></i> How are biomarkers computed?
        </summary>
        <p class="mt-2 mb-1" style="line-height:1.5;"><strong>Axial length</strong><br>
            The axial length is defined as the distance from the anterior surface of the cornea to the posterior pole of the ocular bulb. The base measurement spans from the anterior lens surface to the posterior globe surface; the corneal extension is added separately to obtain the full axial length.
            The method inputs both the automated segmented labels and T1w images.
            A ray is traced between the centroids of the lens and globe segmentations and extended to the full volume bounding box. The anterior lens edge and posterior globe edge are identified as the extreme intersection points of that ray with those structures.
            The corneal boundary is then estimated from the T1-weighted intensity gradient along the same ray. It corresponds to the first gradient peak after the first major drop in the region anterior to the lens.
            Both eyes are extracted independently.
        </p>
        <p class="mb-1" style="line-height:1.5;"><strong>Volumetry</strong><br>
            The volume of each segmented structure is computed by counting the number of voxels belonging to that label
            and multiplying by the physical voxel volume (in mm³).
        </p>
        <p class="mt-1 mb-0 text-muted">
            Reference: <em>A-eye paper </em>
        </p>
    </details>
    <div class="row g-3">
        ${['left', 'right'].map(side => {
        const data = results[side];
        if (!data || data.error) {
            return `<div class="col-6">
                    <p class="text-danger">${data?.error || 'No data'}</p>
                </div>`;
        }
        return `<div class="col-12 col-md-6">
            <div class="card h-100 shadow-sm border-0">
                <div class="card-header d-flex align-items-center gap-2" style="background:var(--card-bg);">
                    <i class="fa-solid fa-eye fa-fw text-success"></i>
                    <strong class="text-capitalize">${side} eye</strong>
                </div>
                <div class="card-body d-flex flex-column gap-4">
                    <div>
                        <p class="text-muted small fw-semibold text-uppercase mb-2 text-center">
                            Volumetry
                        </p>
                        ${renderVolumetryTable(data)}
                    </div>
                    ${data.axial_length_image ? `
                    <div>
                        <p class="text-muted small fw-semibold text-uppercase mb-2 text-center">
                            Axial length visualisation
                        </p>
                        <img src="${data.axial_length_image}" class="img-fluid rounded" style="background:#000; width:100%;" alt="Axial length ${side} eye">
                    </div>` : ''}
                    <div>
                        <p class="text-muted small fw-semibold text-uppercase mb-2 text-center">
                            Axial length
                        </p>
                        ${renderAxialLengthTable(data)}
                    </div>
                </div>
            </div>
        </div>`;
    }).join('')}
    </div>
</div>`;
}
