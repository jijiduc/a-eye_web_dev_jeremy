import nibabel as nib
import numpy as np
import numpy.typing as npt
from scipy.ndimage import map_coordinates
from scipy.signal import convolve, find_peaks
from skimage.measure import regionprops

from .al_data import ALData

LABELS: dict[int, str] = {
    1: "vol_lens",
    2: "vol_globe",
    3: "vol_optic_nerve",
    4: "vol_intraconal_fat",
    5: "vol_extraconal_fat",
    6: "vol_lateral_rectus_muscle",
    7: "vol_medial_rectus_muscle",
    8: "vol_inferior_rectus_muscle",
    9: "vol_superior_rectus_muscle",
}


def _centroid_of_mask(mask: npt.NDArray[np.int_]) -> npt.NDArray[np.float64]:
    """Return centroid (x,y,z) in voxel coordinates as float array"""
    region_properties = regionprops(mask.astype(int))

    if not region_properties:
        raise ValueError("Empty mask passed to _centroid_of_mask.")

    return np.asarray(region_properties[0].centroid, dtype=float)


def _nearest_labels(
    mask: npt.NDArray[np.int_], coords: npt.NDArray[np.float64]
) -> npt.NDArray[np.int_]:
    """Sample mask labels at each ray coordinate using nearest-neighbour rounding"""
    idx = np.round(coords).astype(int)
    idx[:, 0] = np.clip(idx[:, 0], 0, mask.shape[0] - 1)
    idx[:, 1] = np.clip(idx[:, 1], 0, mask.shape[1] - 1)
    idx[:, 2] = np.clip(idx[:, 2], 0, mask.shape[2] - 1)
    return mask[idx[:, 0], idx[:, 1], idx[:, 2]]


def _line_box_intersection(
    o: npt.NDArray[np.float64],
    r: npt.NDArray[np.float64],
    shape: tuple[int, ...],
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]] | tuple[None, None]:
    """Compute entry/exit points of a line through a 3D volume bounding box.

    Using slab algorithm, reference : https://en.wikipedia.org/wiki/Slab_method
    """
    eps = 1e-12
    t_close_list = []
    t_far_list = []

    # for each axis, compute the t values where the ray hits the low and high bounding planes
    for ax in range(3):
        r_i = float(r[ax])
        o_i = float(o[ax])
        l_i = 0.0
        h_i = float(shape[ax] - 1)
        if abs(r_i) < eps:
            # ray is parallel to this axis — valid only if origin is already inside the slab
            if not (l_i <= o_i <= h_i):
                return None, None
            continue
        # t at which the ray crosses each bounding plane along this axis
        t_i_low = (l_i - o_i) / r_i
        t_i_high = (h_i - o_i) / r_i
        # t_close is the entry into this slab and t_far the exit
        t_close_list.append(min(t_i_low, t_i_high))
        t_far_list.append(max(t_i_low, t_i_high))
    if not t_close_list:
        return None, None

    # the ray is inside the box only in the overlap of all three slabs
    t_close = max(t_close_list)
    t_far = min(t_far_list)
    if t_far < t_close:
        # slabs don't overlap — ray misses the box
        return None, None
    return o + t_close * r, o + t_far * r


def _detect_cornea(
    int_profile: npt.NDArray[np.float64],
    limit_idx: int,
    kernel: npt.NDArray[np.int_] | None = None,
    thr_list: list[float] | None = None,
    min_drop: float = 0.03,
    peak_prominence: float = 0.05,
) -> int | None:
    """Detect cornea as the first gradient peak after the first major gradient drop,
    searching in the region before limit_idx."""
    if kernel is None:
        kernel = np.array([1, 0, -1])

    grad = np.abs(convolve(int_profile, kernel, mode="same"))
    if grad.size == 0 or grad.max() == 0:
        return None

    norm_grad = grad / grad.max()

    if thr_list is None:
        thr_list = [0.45, 0.35, 0.25, 0.15, 0.1, 0.05]

    candidate_mask = np.arange(len(norm_grad)) < limit_idx
    first_drop_idx = None
    for thr in thr_list:
        cand_idxs = np.where((norm_grad > thr) & candidate_mask)[0]
        if cand_idxs.size == 0:
            continue
        i = int(cand_idxs[0])
        while i < limit_idx - 1:
            if norm_grad[i + 1] < norm_grad[i] - min_drop:
                while i < limit_idx - 1 and norm_grad[i + 1] < norm_grad[i]:
                    i += 1
                first_drop_idx = i
                break
            i += 1
        if first_drop_idx is not None:
            break

    if first_drop_idx is None or first_drop_idx >= limit_idx - 2:
        return None

    search_region = norm_grad[first_drop_idx + 1 : limit_idx]
    if search_region.size < 3:
        return None

    for prom in [peak_prominence, 0.05, 0.03, 0.01]:
        peaks, _ = find_peaks(search_region, prominence=prom)
        if len(peaks):
            return int(first_drop_idx + 1 + peaks[0])

    return int(first_drop_idx + 1 + np.argmax(search_region))


def compute_axial_length_data(
    segmented_image: nib.Nifti1Image, raw_image: nib.Nifti1Image
) -> ALData | None:
    """Compute all ray-based coordinates and measurements for axial length.

    Args:
        segmented_image (nib.Nifti1Image): _description_
        raw_image (nib.Nifti1Image): _description_

    Returns:
        ALData | None: return populated ALData or None
    """
    voxel_dim = np.array(segmented_image.header.get_zooms()[:3])
    segmented_arr = segmented_image.get_fdata()
    raw_image_array = raw_image.get_fdata()

    # extract binary masks for each structure from the segmentation labels
    lens_mask = (segmented_arr == 1).astype(int)
    globe_mask = (segmented_arr == 2).astype(int)
    optic_nerve_mask = (segmented_arr == 3).astype(int)
    intfat_mask = (segmented_arr == 4).astype(int)

    # ensure that lens and globe are present
    if np.count_nonzero(lens_mask) == 0 or np.count_nonzero(globe_mask) == 0:
        return None

    # find the geometric centroids
    try:
        lens_centroid = _centroid_of_mask(lens_mask)
        globe_centroid = _centroid_of_mask(globe_mask)
    except ValueError:
        return None

    # get the unit vector defining the ray axis from lens to globe
    lens_to_globe_vector = globe_centroid - lens_centroid
    norm = float(np.linalg.norm(lens_to_globe_vector))
    lens_to_globe_unit_vector = lens_to_globe_vector / norm

    # extend the ray to the full volume bounding box to capture cornea and intraconal_fat
    start, end = _line_box_intersection(
        lens_centroid, lens_to_globe_unit_vector, raw_image_array.shape
    )

    # sample densely enough to not miss any sub-voxel structure boundary
    approx_mm_length = float(np.linalg.norm((end - start) * voxel_dim))
    min_vox_mm = float(voxel_dim.min())
    samples = max(800, int(np.ceil(approx_mm_length / (min_vox_mm / 4.0))))
    ray_coords = np.linspace(start, end, samples)

    # sample MRI intensities and structure labels at each point along the ray
    intensities = map_coordinates(raw_image_array, ray_coords.T, order=1, mode="nearest")
    lens_labels_along = _nearest_labels(lens_mask, ray_coords)
    globe_labels_along = _nearest_labels(globe_mask, ray_coords)
    intfat_labels_along = _nearest_labels(intfat_mask, ray_coords)

    # find the anterior lens edge (first lens hit) and posterior globe edge (last globe hit)
    lens_idxs = np.where(lens_labels_along > 0)[0]
    globe_idxs = np.where(globe_labels_along > 0)[0]
    lens_ant_idx = int(lens_idxs.min())
    lens_ext_idx = int(lens_idxs.max())
    globe_ext_idx = int(globe_idxs.max())
    lens_anterior_boundary = ray_coords[lens_ant_idx]
    globe_posterior_boundary = ray_coords[globe_ext_idx]

    # detect cornea: first try a wide search (before posterior lens edge), then validate
    # that the result is truly anterior to the lens; fall back to a narrow search if not
    cornea_idx = _detect_cornea(intensities, lens_ext_idx)
    if cornea_idx is None or cornea_idx >= lens_ant_idx:
        cornea_idx = _detect_cornea(intensities, lens_ant_idx)
    if cornea_idx is not None and cornea_idx < lens_ant_idx:
        cornea_boundary = ray_coords[cornea_idx]
    else:
        cornea_boundary = None

    # find first intraconal fat sample beyond the posterior globe boundary
    intfat_search = np.where(intfat_labels_along[globe_ext_idx + 1 :] > 0)[0]
    if intfat_search.size:
        intfat_boundary = ray_coords[globe_ext_idx + 1 + intfat_search[0]]
    else:
        intfat_boundary = None

    # compute distances in mm
    lens_to_globe_vec_mm = (lens_anterior_boundary - globe_posterior_boundary) * voxel_dim
    axial_length_mm = float(np.round(np.linalg.norm(lens_to_globe_vec_mm), 2))

    extra_ant_mm = None
    axial_length_cornea_mm = None
    if cornea_boundary is not None:
        cornea_to_lens_vec_mm = (cornea_boundary - lens_anterior_boundary) * voxel_dim
        extra_ant_mm = float(np.round(np.linalg.norm(cornea_to_lens_vec_mm), 2))
        axial_length_cornea_mm = float(np.round(extra_ant_mm + axial_length_mm, 2))

    return ALData(
        raw_image_array=raw_image_array,
        voxel_dim=voxel_dim,
        lens_mask=lens_mask,
        globe_mask=globe_mask,
        optic_nerve_mask=optic_nerve_mask,
        intfat_mask=intfat_mask,
        lens_centroid=lens_centroid,
        globe_centroid=globe_centroid,
        lens_to_globe_unit_vector=lens_to_globe_unit_vector,
        lens_anterior_boundary=lens_anterior_boundary,
        globe_posterior_boundary=globe_posterior_boundary,
        cornea_boundary=cornea_boundary,
        intfat_boundary=intfat_boundary,
        axial_length_mm=axial_length_mm,
        extra_ant_mm=extra_ant_mm,
        axial_length_cornea_mm=axial_length_cornea_mm,
    )


def extract_axial_length_measurements(ray_data: ALData | None) -> dict[str, float]:
    """Extract axial length measurements from computed ray data.

    Args:
        ray_data (ALData | None): computed data for a single eye's axial length biomarker

    Returns:
        dict[str, float]: axial_length, axial_length_cornea and extra_anterior measurements in mm, NaN if not available

    """
    nan = float("nan")
    if ray_data is None:
        return {"axial_length": nan, "axial_length_cornea": nan, "extra_anterior": nan}

    if ray_data.axial_length_cornea_mm is not None:
        axial_length_cornea = ray_data.axial_length_cornea_mm
    else:
        axial_length_cornea = nan

    if ray_data.extra_ant_mm is not None:
        extra_anterior = ray_data.extra_ant_mm
    else:
        extra_anterior = nan

    return {
        "axial_length": ray_data.axial_length_mm,
        "axial_length_cornea": axial_length_cornea,
        "extra_anterior": extra_anterior,
    }


def compute_volumetry(image: nib.Nifti1Image) -> dict[str, float]:
    """Compute volumes for each classes of ROI in mm3.

    Args:
        image (nib.Nifti1Image): cropped segmented NIfTI image

    Returns:
        dict[str, float]: class name -> volume in mm3

    """
    dx, dy, dz = image.header.get_zooms()[:3]
    voxel_volume = float(dx * dy * dz)

    label_array = image.get_fdata()
    volumes: dict[str, float] = {}

    for i, name in LABELS.items():
        volumes[name] = float(np.count_nonzero(label_array == i)) * voxel_volume

    volumes["vol_total"] = float(np.count_nonzero(label_array)) * voxel_volume

    return volumes
