import tkinter as tk
from tkinter import filedialog, messagebox
import numpy as np
import rasterio
from scipy.ndimage import uniform_filter, median_filter

# ---------- Фильтры ---------- #
def mean_filter(img: np.ndarray, size: int) -> np.ndarray:
    return uniform_filter(img, size=size)

def median_filter_img(img: np.ndarray, size: int) -> np.ndarray:
    return median_filter(img, size=size)

# ---------- Обработка GeoTIFF ---------- #
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
            raise ValueError("Неизвестный метод фильтрации")

        if nodata is not None:
            filtered[mask] = nodata

        profile.update(dtype=rasterio.float32)

        with rasterio.open(output_path, 'w', **profile) as dst:
            dst.write(filtered.astype(np.float32), 1)

# ---------- GUI-приложение ---------- #
class FilterApp:
    def __init__(self, master):
        self.master = master
        master.title("Простой фильтр для GeoTIFF")
        master.geometry("400x300")

        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.window_size = tk.IntVar(value=3)
        self.method = tk.StringVar(value="mean")

        tk.Label(master, text="Входной GeoTIFF:").pack(pady=5)
        tk.Entry(master, textvariable=self.input_path, width=40).pack()
        tk.Button(master, text="Выбрать файл", command=self.browse_input).pack()

        tk.Label(master, text="Размер окна (нечетное число):").pack(pady=5)
        tk.Entry(master, textvariable=self.window_size).pack()

        tk.Label(master, text="Метод фильтрации:").pack(pady=5)
        tk.Radiobutton(master, text="Средний (mean)", variable=self.method, value="mean").pack()
        tk.Radiobutton(master, text="Медианный (median)", variable=self.method, value="median").pack()

        tk.Label(master, text="Выходной файл:").pack(pady=5)
        tk.Entry(master, textvariable=self.output_path, width=40).pack()
        tk.Button(master, text="Сохранить как...", command=self.browse_output).pack()

        tk.Button(master, text="Применить фильтр", command=self.run_filter).pack(pady=15)

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
                raise ValueError("Убедитесь, что все поля заполнены и размер окна нечётный.")

            apply_filter_to_geotiff(in_path, out_path, size, method)
            messagebox.showinfo("Готово", f"Фильтр '{method}' успешно применён!")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

# ---------- Запуск ---------- #
if __name__ == "__main__":
    root = tk.Tk()
    app = FilterApp(root)
    root.mainloop()
