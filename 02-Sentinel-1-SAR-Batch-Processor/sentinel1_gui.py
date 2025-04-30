import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from glob import glob
import os
import time

# import all your preprocessing steps
import sentinel1_preprocess as prep


class Sentinel1App:
    def __init__(self, master):
        self.master = master
        master.title("Sentinel-1 Batch Processor")

        # --- Input / Output directory selection ---
        tk.Button(master, text="Select Input Folder", command=self.select_input).grid(row=0, column=0, padx=5, pady=5)
        tk.Button(master, text="Select Output Folder", command=self.select_output).grid(row=0, column=1, padx=5, pady=5)

        # --- DEM Choice Dropdown ---
        tk.Label(master, text="DEM Source:").grid(row=1, column=0, sticky="e", padx=(5,0))
        self.dem_var = tk.StringVar(value="GETASSE30")
        dem_options = ["GETASSE30", "SRTM 3Sec", "Copernicus 30m Global DEM"]
        tk.OptionMenu(master, self.dem_var, *dem_options).grid(row=1, column=1, sticky="w", padx=5)

        # --- Start button ---
        self.start_btn = tk.Button(master, text="Start Processing", command=self.start_processing)
        self.start_btn.grid(row=2, column=0, columnspan=2, pady=(5,10))

        # --- Log window ---
        self.log_text = scrolledtext.ScrolledText(master, state='disabled', width=85, height=20)
        self.log_text.grid(row=3, column=0, columnspan=2, padx=5, pady=5)

        # Internal state
        self.input_dir = ""
        self.output_dir = ""
        self.is_processing = False

    def select_input(self):
        d = filedialog.askdirectory(title="Select folder with Sentinel-1 .zip files")
        if d:
            self.input_dir = d
            self.log_message(f"Input folder set: {d}")

    def select_output(self):
        d = filedialog.askdirectory(title="Select output folder")
        if d:
            self.output_dir = d
            self.log_message(f"Output folder set: {d}")
            self.log_message(" ")

    def start_processing(self):
        if self.is_processing:
            return
        if not self.input_dir or not self.output_dir:
            messagebox.showwarning("Missing paths", "Please set both input and output folders first.")
            return

        dem_choice = self.dem_var.get()
        if dem_choice == "Copernicus 30m Global DEM":
            self.log_message("------------------!!!--------------------")
            self.log_message("Copernicus 30m Global DEM can take ~10 minutes to download/apply.")
            self.log_message("Make sure you have a fast connection and enough disk space.")
            self.log_message("------------------!!!--------------------")
        

        self.is_processing = True
        self.start_btn.config(state='disabled')
        self.log_message(" ")
        self.log_message("Starting batch processing…")

        all_zips = sorted(glob(os.path.join(self.input_dir, "*.zip")))
        for zip_fp in all_zips:
            fname = os.path.basename(zip_fp)
            self.log_message(f"\nProcessing {fname}")
            self.master.update_idletasks()
            t0 = time.time()
            try:
                # open & apply all steps
                prod = prep.open_product(zip_fp)
                prod = prep.apply_orbit_file(prod)
                prod = prep.remove_thermal_noise(prod)
                prod = prep.border_noise_remove(prod)
                prod = prep.calibrate(prod)
                prod = prep.speckle_filtering(prod)
                prep.DEM_NAME = dem_choice

                prod = prep.terrain_correction(prod)
                prod = prep.band_maths(prod)

                out_fp = prep.save_product(prod, self.output_dir)
                elapsed = time.time() - t0

                self.log_message(f"Saved → {os.path.basename(out_fp)}  "
                                 f"(time: {elapsed:.1f} s)")
            except Exception as e:
                self.log_message(f"Error: {e}")

        self.log_message("\n All done!")
        messagebox.showinfo("Finished", "Batch processing complete!")
        self.is_processing = False
        self.start_btn.config(state='normal')

    def log_message(self, msg: str):
        self.log_text.configure(state='normal')
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.configure(state='disabled')
        self.log_text.yview(tk.END)


if __name__ == "__main__":
    root = tk.Tk()
    app = Sentinel1App(root)
    root.mainloop()
