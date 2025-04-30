import tkinter as tk
from tkinter import filedialog, messagebox
import numpy as np
import rasterio
from scipy.ndimage import uniform_filter, median_filter

# ---------- Filters ---------- #
def mean_filter(img: np.ndarray, size: int) -> np.ndarray:
    return uniform_filter(img, size=size)

def median_filter_img(img: np.ndarray, size: int) -> np.ndarray:
    return median_filter(img, size=size)

# ---------- GeoTIFF Processing ---------- #
def apply_filter_to_geotiff(input_path: str, output_path: str, window_size: int, method: str):
    with rasterio.open(input_path) as src:
        profile = src.profile
        image = src.read(1)
        nodata = src.nodata
        mask = (image == nodata) if nodata is not None else np.isnan(image)
        image = image.astype(np.float32)

        if method == "mean":
            filtered = mean_filter(image, window_size)
        elif method == "median":
            filtered = median_filter_img(image, window_size)
        else:
            raise ValueError("Unknown filtering method")

        if nodata is not None:
            filtered[mask] = nodata

        profile.update(dtype=rasterio.float32 -dtype=rasterio.float32)

        with rasterio.open(output_path, 'w', **profile) as dst:
            dst.write(filtered.astype(np.float32), 1)

# ---------- GUI Application ---------- #
class FilterApp:
    def __init__(self, master):
        self.master = master
        master.title("Simple GeoTIFF Filter")
        master.geometry("400x300")

        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.window_size = tk.IntVar(value=3)
        self.method = tk.StringVar(value="mean")

        tk.Label(master, text="Input GeoTIFF:").pack(pady=5)
        tk.Entry(master, textvariable=self.input_path, width=40).pack()
        tk.Button(master, text="Select File", command=self.browse_input).pack()

        tk.Label(master, text="Window Size (odd number):").pack(pady=5)
        tk.Entry(master, textvariable=self.window_size).pack()

        tk.Label(master, text="Filtering Method:").pack(pady=5)
        tk.Radiobutton(master, text="Mean", variable=self.method, value="mean").pack()
        tk.Radiobutton(master, text="Median", variable=self.method, value="median").pack()

        tk.Label(master, text="Output File:").pack(pady=5)
        tk.Entry(master, textvariable=self.output_path, width=40).pack()
        tk.Button(master, text="Save As...", command=self.browse_output).pack()

        tk.Button(master, text="Apply Filter", command=self.run_filter).pack(pady=15)

    def browse_input(self):
        filename = filedialog.askopenfilename(filetypes=[("GeoTIFF", "*.tif *.tiff")])
        if filename:
            self.input_path.set(filename)

    def browse_output(self):
        filename = filedialog.asksaveasfilename(defaultextension=".tif",
                                               filetypes=[("GeoTIFF", "*.tif *.tiff")])
        if filename:
            self.output_path.set(filename)

    def run_filter(self):
        try:
            in_path = self.input_path.get()
            out_path = self.output_path.get()
            size = int(self.window_size.get())
            method = self.method.get()

            if not (in_path and out_path and size % 2 == 1):
                raise ValueError("Ensure all fields are filled and window size is an odd number.")

            apply_filter_to_geotiff(in_path, out_path, size, method)
            messagebox.showinfo("Done", f"Filter '{method}' successfully applied!")
        except Exception as e:
            messagebox.showerror("Error", str(e))

# ---------- Run ---------- #
if __name__ == "__main__":
    root = tk.Tk()
    app = FilterApp(root)
    root.mainloop()