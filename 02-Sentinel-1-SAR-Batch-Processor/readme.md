**Sentinel-1 SAR Batch Processor**

*Short Description:*

A graphical interface for automated preprocessing of Sentinel-1 SAR imagery, including orbit correction, noise removal, calibration, speckle filtering, and terrain correction. Supports DEM selection and logs processing progress and timing for each product.

- **Batch Processing of Sentinel-1 .zip Products**
  - Automatically detects and processes all `.zip` archives in a selected folder
  - Saves output to a user-defined directory

- **SNAP-Based Processing Chain**
  - **Apply Orbit File Correction**
  - **Remove Thermal Noise and Border Noise**
  - **Radiometric Calibration**
  - **Speckle Filtering** (Lee filter)
  - **Terrain Correction** with selectable DEM
  - **Band Math** (converting backscatter to dB)

- **Digital Elevation Model (DEM) Options**
  - **GETASSE30** (default – global, coarse resolution)
  - **SRTM 3Sec** (medium resolution)
  - **Copernicus 30m Global DEM** (high resolution, may take ~10 minutes per scene)

- **Graphical User Interface (GUI)**
  - Built with **Tkinter**
  - **File/folder selection** for input and output
  - **Dropdown menu** for DEM selection
  - **Scrollable log window** for real-time processing updates
  - Displays **per-file processing time**
  - All processing messages and errors are printed directly into the GUI
