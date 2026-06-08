# Metadata

In the platform, only NifTi (Neuroimaging Informatics Technology Initiative) or DICOM (Digital Imaging and Communications in Medicine) data are allowed at upload.

## NifTi

An example of metada of a Nifty file (found using NiiVue extension (Ctrl+Shift+H)) :

```
Dim Info = 54

Image Dimensions (1-8): 3, 176, 256, 176, 1, 1, 1, 1

Intent Parameters (1-3): 0, 0, 0

Intent Code = 0

Datatype = 4 (2-Byte Signed Integer)

Bits Per Voxel = 16

Slice Start = 0

Voxel Dimensions (1-8): 1, 1, 1, 1, 1.9, 0, 0, 0

Image Offset = 352

Data Scale: Slope = 1 Intercept = 0

Slice End = 0

Slice Code = 0

Units Code = 10 (Millimeters, Seconds)

Display Range: Max = 0 Min = 0

Slice Duration = 0

Time Axis Shift = 0

Description: "TE=3.4;Time=115927.745;phase=1"

Auxiliary File: ""

Q-Form Code = 1 (Scanner)

S-Form Code = 1 (Scanner)

Quaternion Parameters: b = -0.0007194803 c = 0.03053004 d = -0.02354878

Quaternion Offsets: x = -97.99937438964844 y = -82.425048828125 z = -176.22132873535156

S-Form Parameters X: 0.9970267, 0.04701859, 0.06104851, -97.99937

S-Form Parameters Y: -0.04710645, 0.9988899, 0, -82.42505

S-Form Parameters Z: -0.06098077, -0.00287578, 0.9981342, -176.2213

Intent Name: ""
```
## DICOM

An example of metada of a DICOM file (found using NiiVue extension (Ctrl+Shift+H)) :

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

## Plan of changes

To display the metadata uploaded to the users in the segmentation pipeline page :

1. Extract metadata by extension (Nibabel, dicom2nifti then Nibabel)
2. Include the metadata in the JSON response to the upload
3. Update segmentation.html to display the metada