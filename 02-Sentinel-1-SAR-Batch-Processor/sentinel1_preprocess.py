import os
from glob import glob
import esa_snappy
from esa_snappy import ProductIO, GPF, HashMap, Product, ProductData, File, ProgressMonitor, jpy
import numpy as np


def create_product_name(source: Product, file_type: str = "GeoTIFF") -> str:
    name = source.getName()
    if file_type in ["GeoTIFF", "GeoTIFF-BigTIFF", "GDAL-GTiff-WRITER"]:
        ext = "tif"
    elif file_type == "JP2":
        ext = "jp2"
    else:
        ext = "dim"
    return f"{name}.{ext}"

# 1) Redirect all Java System.out/System.err to null
JavaSystem    = jpy.get_type("java.lang.System")
PrintStream   = jpy.get_type("java.io.PrintStream")
FileOutputStream = jpy.get_type("java.io.FileOutputStream")
null_ps       = PrintStream(FileOutputStream(os.devnull))
JavaSystem.setOut(null_ps)
JavaSystem.setErr(null_ps)

# 2) Disable all java.util.logging (SNAP uses JUL for those INFO:/WARNING: lines)
LogManager = jpy.get_type("java.util.logging.LogManager")
log_manager = LogManager.getLogManager()
log_manager.reset()

def create_progress_monitor():    
    NullPM = jpy.get_type("com.bc.ceres.core.NullProgressMonitor")
    return NullPM()


def read_product(path: str) -> Product:
    reader = ProductIO.getProductReader("SENTINEL-1")
    product = reader.readProductNodes(path, None)
    return product


def save_product(source, output_dir=None, output_path=None, file_type="GeoTIFF"):
    """
    Available formats: GeoTIFF-BigTIFF, HDF5, Snaphu, BEAM-DIMAP,
    GeoTIFF+XML, PolSARPro, NetCDF-CF, NetCDF-BEAM, ENVI, JP2,
    Generic Binary BSQ, Gamma, CSV, NetCDF4-CF, GeoTIFF, NetCDF4-BEAM
    """
    if output_path:
        output_file = output_path
    else:
        output_name = create_product_name(source, file_type)
        output_file = os.path.join(output_dir, output_name)
    increment = True
    pm = create_progress_monitor()
    GPF.writeProduct(source, File(output_file), file_type, increment, pm)
    source.closeIO()
    return output_file


def open_product(path: str) -> Product:
    try:
        product = read_product(path)
        return product
    except RuntimeError:
        source_fp = glob(path + "/**/*.safe", recursive=True)
        if len(source_fp) == 0:
            raise FileNotFoundError(f"File 'manifest.safe' not found at path: {path}. Aborting.")
        else:
            product = read_product(source_fp[0])
            return product


def get_product_info(product: Product) -> dict:
    """
    Product information:
    description, band_names, start_time, end_time
    """
    info = {
        "description": product.getDescription(),
        "band_names": product.getBandNames(),
        "start_time": product.getStartTime(),
        "end_time": product.getEndTime(),
    }
    return info


def get_product_metadata(product: Product, key: str) -> ProductData:
    try:
        abstracted_metadata = product.getMetadataRoot().getElement("Abstracted_Metadata")
        value = abstracted_metadata.getAttribute(key).getData()
        return value
    except RuntimeError:
        raise KeyError(f"Metadata attribute not found. Key error: {key}")


def detect_polarization(product: Product) -> str:
    """
    Detects polarization mode (VV,VH or HH,HV) based on band names.
    Returns 'VV,VH' or 'HH,HV'.
    """
    band_names = get_product_info(product)["band_names"]
    if any("VV" in band for band in band_names):
        return "VV,VH"
    elif any("HH" in band for band in band_names):
        return "HH,HV"
    else:
        raise ValueError("Unable to detect polarization. No VV or HH bands found.")


def apply_orbit_file(source: Product) -> Product:
    parameters = HashMap()
    parameters.put("orbitType", "Sentinel Precise (Auto Download)")
    parameters.put('Polynomial Degree', 3)
    parameters.put("continueOnFail", True)
    output = GPF.createProduct("Apply-Orbit-File", parameters, source)
    return output


def remove_thermal_noise(source: Product) -> Product:
    parameters = HashMap()
    parameters.put("removeThermalNoise", True)
    parameters.put("reIntroduceThermalNoise", False)
    output = GPF.createProduct("ThermalNoiseRemoval", parameters, source)
    return output


def border_noise_remove(source: Product) -> Product:
    polarization = detect_polarization(source)
    parameters = HashMap()
    parameters.put("selectedPolarisations", polarization)
    parameters.put('Border margin limit[pixels]', 500)
    parameters.put("trimThreshold", 50.0)
    output = GPF.createProduct("Remove-GRD-Border-Noise", parameters, source)
    return output


def calibrate(source: Product) -> Product:
    polarization = detect_polarization(source)
    parameters = HashMap()
    parameters.put("auxFile", "Product Auxiliary File")
    parameters.put("outputImageInComplex", False)
    parameters.put("outputImageScaleInDb", False)
    parameters.put("createGammaBand", False)
    parameters.put("createBetaBand", False)
    parameters.put("selectedPolarisations", polarization)
    parameters.put("outputSigmaBand", True)
    parameters.put("outputGammaBand", False)
    parameters.put("outputBetaBand", False)
    output = GPF.createProduct("Calibration", parameters, source)
    return output


def speckle_filtering(source: Product) -> Product:
    parameters = HashMap()
    parameters.put("filter", "Lee")
    parameters.put("Size X", 3)
    parameters.put("Size Y", 3)
    parameters.put("Frost Damping Factor", 2)
    parameters.put("estimateENL", True)
    parameters.put("enl", 1.0)
    parameters.put("numLooksStr", "1")
    parameters.put("windowSize", "7x7")
    parameters.put("targetWindowSizeStr", "3x3")
    parameters.put("sigmaStr", "0.9")
    parameters.put("Adaptive Neighbourhood Size", 50)
    output = GPF.createProduct("Speckle-Filter", parameters, source)
    return output


def terrain_correction(source: Product) -> Product:
    polarization = detect_polarization(source)
    parameters = HashMap()
    parameters.put("demName", globals().get("DEM_NAME", "GETASSE30"))
    parameters.put("externalDEMNoDataValue", 0.0)
    parameters.put("externalDEMApplyEGM", True)
    parameters.put("imgResamplingMethod", "BILINEAR_INTERPOLATION")
    parameters.put("demResamplingMethod", "BILINEAR_INTERPOLATION")
    
    if polarization == "VV,VH":
        parameters.put("pixelSpacingInMeter", 10.0)
        parameters.put('pixelSpacingInDegree', 8.983152841195215E-5)
    else:  # HH,HV
        parameters.put("pixelSpacingInMeter", 40.0)
        parameters.put('pixelSpacingInDegree', 3.593261136478086E-4)
    
    parameters.put("mapProjection", "AUTO:42001")
    parameters.put('alignToStandardGrid', False)
    parameters.put('standardGridOriginX', 0.0)
    parameters.put('standardGridOriginY', 0.0)
    parameters.put("nodataValueAtSea", False)
    parameters.put("saveDEM", False)
    parameters.put("saveLatLon", False)
    parameters.put("saveIncidenceAngleFromEllipsoid", False)
    parameters.put("saveLocalIncidenceAngle", False)
    parameters.put("saveProjectedLocalIncidenceAngle", False)
    parameters.put("saveSelectedSourceBand", True)
    parameters.put("outputComplex", False)
    parameters.put("applyRadiometricNormalization", False)
    parameters.put("saveSigmaNought", False)
    parameters.put("saveGammaNought", False)
    parameters.put("saveBetaNought", False)
    parameters.put("incidenceAngleForSigma0", "Use projected local incidence angle from DEM")
    parameters.put("incidenceAngleForGamma0", "Use projected local incidence angle from DEM")
    parameters.put("auxFile", "Latest Auxiliary File")
    output = GPF.createProduct("Terrain-Correction", parameters, source)
    return output


def linear_to_db(product: Product) -> Product:
    polarization = detect_polarization(product)
    pol_bands = "Sigma0_VV,Sigma0_VH" if polarization == "VV,VH" else "Sigma0_HH,Sigma0_HV"
    parameters = HashMap()
    parameters.put('sourceBands', pol_bands)
    output = GPF.createProduct("LinearToFromdB", parameters, product)
    return output


def band_maths(source: Product) -> Product:
    polarization = detect_polarization(source)
    GPF.getDefaultInstance().getOperatorSpiRegistry().loadOperatorSpis()
    BandDescriptor = jpy.get_type('org.esa.snap.core.gpf.common.BandMathsOp$BandDescriptor')

    band1_name = 'newBand_VV' if polarization == "VV,VH" else 'newBand_HH'
    band1_expr = 'Sigma0_VV*100000' if polarization == "VV,VH" else 'Sigma0_HH*100000'
    band2_name = 'newBand_VH' if polarization == "VV,VH" else 'newBand_HV'
    band2_expr = 'Sigma0_VH*100000' if polarization == "VV,VH" else 'Sigma0_HV*100000'

    targetBand1 = BandDescriptor()
    targetBand1.name = band1_name
    targetBand1.type = 'uint16'
    targetBand1.expression = band1_expr
    targetBand1.noDataValue = np.nan

    targetBand2 = BandDescriptor()
    targetBand2.name = band2_name
    targetBand2.type = 'uint16'
    targetBand2.expression = band2_expr
    targetBand2.noDataValue = np.nan

    targetBands = jpy.array('org.esa.snap.core.gpf.common.BandMathsOp$BandDescriptor', 2)
    targetBands[0] = targetBand1
    targetBands[1] = targetBand2

    parameters = HashMap()
    parameters.put('targetBands', targetBands)
    parameters.put('geographicError', 1.0E-5)
    output = GPF.createProduct('BandMaths', parameters, source)
    return output