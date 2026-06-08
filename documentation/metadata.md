# Metadata

In the platform, only NifTi (Neuroimaging Informatics Technology Initiative) or DICOM (Digital Imaging and Communications in Medicine) data are allowed at upload.

## NifTi

The NIfTI standard state that spatial coordinates must map to a Right-Anterior-Superior (RAS+) physical space.

An example of metadata of a NIfTI file (found using NiiVue extension (Ctrl+Shift+H)), c.f. [NifTi-1 doc](https://www.nitrc.org/docman/view.php/26/64/nifti1.h) :

```bash
# Encoding of which spatial axis corresponds to MRI frequency, phase, and slice encoding. Stored as a single byte (2 bits per axis). In this case : 2 + (1x4) + (3x16) = 54, where : axis 3 (Z : slice), axis 2 (Y : frequency) and axis 1 (X : phase)
# Axial acquisition :
#   - Slice (Z): aquisition made from foot-to-head
#   - Frequency (Y): encoding was performed back-to-front
#   - Phase (X): encoding made left-to-right

Dim Info = 54

# First value = number of dimensions
# Next values = voxel count per axis (x×y×z).
# A 4th value > 1 indicates a time series

Image Dimensions (1-8): 3, 176, 256, 176, 1, 1, 1, 1

# If intent code  != 0, parameters holds values related to the meaning of dataset content

Intent Parameters (1-3): 0, 0, 0

Intent Code = 0

#  Numeric type used to store each voxel

Datatype = 4 (2-Byte Signed Integer)

# states storage cost per voxel, total raw size ≈ 176×256×176×2 ≈ 15 MB
Bits Per Voxel = 16

# When != 0, provide with Slice End, values for fMRI slice-timing correction
Slice Start = 0

# First value = `qfac` (±1, encodes coordinate hande orientation). 
# Next three = physical voxel size in mm (here 1×1×1 mm isotropic). 
# Following values = TR in seconds if a time axis is present

Voxel Dimensions (1-8): 1, 1, 1, 1, 1.9, 0, 0, 0

# Byte position in the file where voxel data begins. For info, the NifTi-1 header is 348 bytes sizes
Image Offset = 352

# If the scl_slope field is nonzero, then each voxel value in the dataset should to recover physical values
Data Scale: Slope = 1 Intercept = 0

Slice End = 0

# Slice acquisition order for fMRI slice-timing correction - 0 = not applicable 
Slice Code = 0

# Encodes spatial and temporal units together in one byte
Units Code = 10 (Millimeters, Seconds)

# used for mapping (possibly scaled) dataset values to display colors if value !=0
Display Range: Max = 0 Min = 0

# Acquisition time per slice in seconds, here 0 - unknown
Slice Duration = 0

# The toffset field in s. can be used to indicate a nonzero start point for the time axis
Time Axis Shift = 0

# Free text (written by the scanner), here : TE = echo time in ms, Time= acquisition clock time, HHMMSS.SSS, phase = phase-encoding polarity

Description: "TE=3.4;Time=115927.745;phase=1"

# Optional path to auxiliary file
Auxiliary File: ""

# The qform transformationrelates the voxel co-ordinates (in mm) to scanner space (aka some frame of reference on the scanner), and is a rigid transform.
Q-Form Code = 1 (Scanner)

# The sform transformation relates the voxel co-ordinates to some standard space (eg. MNI space), is an affine transform
S-Form Code = 1 (Scanner)

# Rotation part of the Q-Form, encoded as a unit quaternion (the 4th component `a` is derived as `sqrt(1 − b²−c²−d²)`). Encodes the 3D orientation of the voxel grid in scanner space. Values close to 0 indicate near-axis-aligned orientation 
Quaternion Parameters: b = -0.0007194803 c = 0.03053004 d = -0.02354878

# Translation part of Q-Form: physical coordinates (mm) of voxel index (0, 0, 0) in scanner space. 
Quaternion Offsets: x = -97.99937438964844 y = -82.425048828125 z = -176.22132873535156

# The three rows of the 4×4 affine matrix (the 4th row is always [0, 0, 0, 1]). The first three values per row encode rotation and spacing; the fourth is translation. This matrix maps any voxel index (i, j, k) to physical mm coordinates (x, y, z)
S-Form Parameters X: 0.9970267, 0.04701859, 0.06104851, -97.99937

S-Form Parameters Y: -0.04710645, 0.9988899, 0, -82.42505

S-Form Parameters Z: -0.06098077, -0.00287578, 0.9981342, -176.2213

# Label for the intent
Intent Name: ""
```

## DICOM

An example of metadata of a DICOM file as viewed through NiiVue (Ctrl+Shift+H)

>  NiiVue converts DICOM to NIfTI before display

```
Dim Info = 54

Image Dimensions (1-8): 3, 176, 256, 1, 1, 1, 1, 1

Intent Parameters (1-3): 0, 0, 0

Intent Code = 0

Datatype = 4 (2-Byte Signed Integer)

Bits Per Voxel = 16

Slice Start = 0

Voxel Dimensions (1-8): -1, 1, 1, 1, 1.9, 0, 0, 0

Image Offset = 352

Data Scale: Slope = 1 Intercept = 0

Slice End = 0

Slice Code = 0

Units Code = 10 (Millimeters, Seconds)

Display Range: Max = 0 Min = 0

Slice Duration = 0

Time Axis Shift = 0

Description: "TE=3.4;Time=103711.820;phase=1"

Auxiliary File: ""

Q-Form Code = 1 (Scanner)

S-Form Code = 1 (Scanner)

Quaternion Parameters: b = -0.010471 c = -0.9998705 d = 0.0001279338

Quaternion Offsets: x = 90.21820831298828 y = -105.24014282226562 z = -0.799552321434021

S-Form Parameters X: -0.9994823, 0.02093617, 0.02443218, 90.21821

S-Form Parameters Y: 0.02094242, 0.9997807, 0, -105.2401

S-Form Parameters Z: 0.02442683, -0.0005116689, 0.9997016, -0.7995523

Intent Name: ""
```

## Plan of implementation

To display the metadata uploaded to the users in the segmentation pipeline page :

1. Extract metadata by extension (Nibabel, dicom2nifti then Nibabel)
2. Include the metadata in the JSON response to the upload
3. Update segmentation.html to display the metada