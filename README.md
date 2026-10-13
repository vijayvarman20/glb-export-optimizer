# GLB Export Optimizer

**Blender add-on by Vijay Varman**  
**Current version:** 1.1.0  
**License:** GPL-3.0-or-later  
**Minimum Blender version declared:** 5.0.0

GLB Export Optimizer helps 3D artists export selected objects to GLB with configurable Draco mesh compression and quantization settings.

## Features

- Export selected objects to GLB
- Configure Draco mesh compression and compression level
- Adjust position, normal, UV, vertex-color, and generic quantization
- Compare compressed and uncompressed export file sizes
- Report output size and estimated savings
- Access settings from the export file browser

## Installation

1. Download the latest release ZIP from the Releases section of this repository, or use the release ZIP attached to the Blender Extensions listing.
2. In Blender, open Preferences and go to Get Extensions / the add-on installation interface.
3. Choose Install from Disk and select the ZIP.
4. Enable the add-on if required.
5. Select objects, press F3, and search for **Export Optimized GLB**.

## Report a bug or request a feature

Please use GitHub Issues so the maintainer can track reports:

- [Report a bug](../../issues/new?template=bug_report.yml)
- [Request a feature](../../issues/new?template=feature_request.yml)

When reporting a bug, include your Blender version, operating system, exact steps to reproduce the problem, and any error message. Do not attach confidential assets or private project files.

## Support and compatibility

The add-on declares Blender 5.0.0 as its minimum version. Test exports in your target application because file-size savings and visual quality depend on the model and compression settings.

## License

This project is licensed under GPL-3.0-or-later. See [LICENSE](LICENSE).
