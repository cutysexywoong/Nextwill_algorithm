import os
import re
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox

import matplotlib
matplotlib.use("TkAgg")

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

try:
    import mplcursors
    from mplcursors import HoverMode
except ModuleNotFoundError:
    # mplcursors는 마우스 hover 값 표시만 담당하는 선택 패키지입니다.
    # 설치되어 있지 않아도 나머지 그래프와 GUI는 정상 작동하게 합니다.
    class _DisabledCursor:
        selections = ()

        def connect(self, _event):
            return lambda callback: callback

        def remove(self):
            pass

    class _MplCursorsFallback:
        @staticmethod
        def cursor(*_args, **_kwargs):
            return _DisabledCursor()

    class _HoverModeFallback:
        Transient = False

    mplcursors = _MplCursorsFallback()
    HoverMode = _HoverModeFallback


# ============================================================
# Touchstone SnP Parser
# ============================================================

def parse_touchstone_snp(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    match = re.match(r"\.s(\d+)p$", ext)

    if not match:
        raise ValueError("파일 확장자가 .sNp 형식이 아닙니다. 예: .s1p, .s2p, .s4p")

    nport = int(match.group(1))

    freq_unit = "GHz"
    parameter = "S"
    data_format = "MA"
    z0 = 50.0

    freq_scale = {
        "HZ": 1.0,
        "KHZ": 1e3,
        "MHZ": 1e6,
        "GHZ": 1e9,
    }

    numeric_tokens = []

    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        for raw_line in f:
            line = raw_line.split("!")[0].strip()

            if not line:
                continue

            if line.startswith("#"):
                tokens = line.upper().split()

                if len(tokens) >= 2 and tokens[1] in freq_scale:
                    freq_unit = tokens[1]

                if "S" in tokens:
                    parameter = "S"

                for fmt in ["DB", "MA", "RI"]:
                    if fmt in tokens:
                        data_format = fmt

                if "R" in tokens:
                    r_index = tokens.index("R")
                    if r_index + 1 < len(tokens):
                        z0 = float(tokens[r_index + 1])

                continue

            parts = line.replace(",", " ").split()

            for p in parts:
                try:
                    numeric_tokens.append(float(p))
                except ValueError:
                    pass

    if parameter != "S":
        raise ValueError("현재 코드는 S-parameter Touchstone 파일만 지원합니다.")

    values_per_freq = 1 + 2 * nport * nport

    if len(numeric_tokens) % values_per_freq != 0:
        raise ValueError(
            f"데이터 개수가 SnP 형식과 맞지 않습니다.\n"
            f"N-port = {nport}, 주파수당 필요한 숫자 개수 = {values_per_freq}, "
            f"전체 숫자 개수 = {len(numeric_tokens)}"
        )

    data = np.array(numeric_tokens).reshape(-1, values_per_freq)

    freq_hz = data[:, 0] * freq_scale[freq_unit.upper()]
    raw = data[:, 1:]

    nfreq = len(freq_hz)
    s = np.zeros((nfreq, nport, nport), dtype=complex)

    # Touchstone v1 ordering:
    # S11, S21, ... SN1, S12, S22, ... SN2, ... SNN
    pair_index = 0

    for col in range(nport):
        for row in range(nport):
            a = raw[:, 2 * pair_index]
            b = raw[:, 2 * pair_index + 1]

            if data_format == "DB":
                mag = 10 ** (a / 20.0)
                phase_rad = np.deg2rad(b)
                value = mag * np.exp(1j * phase_rad)

            elif data_format == "MA":
                mag = a
                phase_rad = np.deg2rad(b)
                value = mag * np.exp(1j * phase_rad)

            elif data_format == "RI":
                value = a + 1j * b

            else:
                raise ValueError(f"지원하지 않는 데이터 형식입니다: {data_format}")

            s[:, row, col] = value
            pair_index += 1

    return freq_hz, s, z0, data_format, freq_unit


# ============================================================
# Smith Chart Helper
# ============================================================

def gamma_from_z_norm(r, x):
    z = r + 1j * x
    return (z - 1) / (z + 1)


def draw_smith_chart(ax):
    ax.clear()

    ax.set_aspect("equal", adjustable="box")
    ax.set_box_aspect(1)
    ax.set_anchor("C")

    ax.set_xlim(-1.03, 1.03)
    ax.set_ylim(-1.03, 1.03)

    theta = np.linspace(0, 2 * np.pi, 1200)

    ax.plot(np.cos(theta), np.sin(theta), color="black", linewidth=1.2)

    r_values = [0, 0.2, 0.5, 1, 2, 5]
    x_sweep = np.linspace(-80, 80, 4000)

    for r in r_values:
        gamma = gamma_from_z_norm(r, x_sweep)
        mask = np.abs(gamma) <= 1.001
        ax.plot(
            np.real(gamma[mask]),
            np.imag(gamma[mask]),
            color="0.75",
            linewidth=0.7
        )

    x_values = [0.2, 0.5, 1, 2, 5, -0.2, -0.5, -1, -2, -5]
    r_sweep = np.linspace(0, 80, 4000)

    for x in x_values:
        gamma = gamma_from_z_norm(r_sweep, x)
        mask = np.abs(gamma) <= 1.001
        ax.plot(
            np.real(gamma[mask]),
            np.imag(gamma[mask]),
            color="0.75",
            linewidth=0.7
        )

    ax.axhline(0, color="0.60", linewidth=0.8)
    ax.axvline(0, color="0.85", linewidth=0.7)

    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_xticks([])
    ax.set_yticks([])

    for spine in ax.spines.values():
        spine.set_visible(False)

    ax.margins(0)
    ax.grid(False)


# ============================================================
# GUI Application
# ============================================================

class SNPViewerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SnP S-Parameter Viewer")

        self.file_var = tk.StringVar()

        self.start_freq_var = tk.StringVar()
        self.stop_freq_var = tk.StringVar()
        self.range_unit_var = tk.StringVar(value="")

        self.freq_hz = None
        self.s = None
        self.z0 = None
        self.fmt = None
        self.unit = None

        self.sparam_vars = {}
        self.sparam_indices = {}

        self.cursors = []

        self._build_gui()

    def _build_gui(self):
        self.root.geometry("1650x920")

        # --------------------------------------------------------
        # Left control panel
        # --------------------------------------------------------
        self.left_frame = tk.Frame(self.root, width=310, bg="#d9d9d9")
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y)
        self.left_frame.pack_propagate(False)

        plot_frame = tk.Frame(self.root)
        plot_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        label = tk.Label(
            self.left_frame,
            text="입력 파일",
            font=("Arial", 18),
            bg="#d9d9d9"
        )
        label.pack(pady=(35, 10), anchor="w", padx=20)

        entry = tk.Entry(
            self.left_frame,
            textvariable=self.file_var,
            font=("Arial", 11),
            width=33
        )
        entry.pack(padx=18, pady=5)

        button_frame = tk.Frame(self.left_frame, bg="#d9d9d9")
        button_frame.pack(pady=12)

        browse_button = tk.Button(
            button_frame,
            text="불러오기",
            font=("Arial", 12),
            command=self.browse_file,
            width=8
        )
        browse_button.pack(side=tk.LEFT, padx=5)

        apply_button = tk.Button(
            button_frame,
            text="적용",
            font=("Arial", 12),
            command=self.apply_plot,
            width=8
        )
        apply_button.pack(side=tk.LEFT, padx=5)

        self.info_label = tk.Label(
            self.left_frame,
            text="",
            justify=tk.LEFT,
            bg="#d9d9d9",
            font=("Arial", 10)
        )
        self.info_label.pack(pady=(8, 12), padx=20, anchor="w")

        # --------------------------------------------------------
        # Frequency range input
        # --------------------------------------------------------
        freq_frame = tk.LabelFrame(
            self.left_frame,
            text="Plot 주파수 범위",
            font=("Arial", 11, "bold"),
            bg="#d9d9d9",
            padx=10,
            pady=8
        )
        freq_frame.pack(fill=tk.X, padx=16, pady=(0, 12))

        unit_label = tk.Label(
            freq_frame,
            textvariable=self.range_unit_var,
            bg="#d9d9d9",
            font=("Arial", 10)
        )
        unit_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 5))

        start_label = tk.Label(
            freq_frame,
            text="시작",
            bg="#d9d9d9",
            font=("Arial", 10)
        )
        start_label.grid(row=1, column=0, sticky="w", pady=3)

        start_entry = tk.Entry(
            freq_frame,
            textvariable=self.start_freq_var,
            font=("Arial", 10),
            width=17
        )
        start_entry.grid(row=1, column=1, sticky="w", pady=3)

        stop_label = tk.Label(
            freq_frame,
            text="종료",
            bg="#d9d9d9",
            font=("Arial", 10)
        )
        stop_label.grid(row=2, column=0, sticky="w", pady=3)

        stop_entry = tk.Entry(
            freq_frame,
            textvariable=self.stop_freq_var,
            font=("Arial", 10),
            width=17
        )
        stop_entry.grid(row=2, column=1, sticky="w", pady=3)

        range_button = tk.Button(
            freq_frame,
            text="주파수 범위 적용",
            font=("Arial", 10),
            command=self.plot_selected_sparameters
        )
        range_button.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 2))

        start_entry.bind("<Return>", lambda event: self.plot_selected_sparameters())
        stop_entry.bind("<Return>", lambda event: self.plot_selected_sparameters())

        # --------------------------------------------------------
        # S-parameter selection area
        # --------------------------------------------------------
        select_label = tk.Label(
            self.left_frame,
            text="표시할 S-parameter",
            font=("Arial", 13, "bold"),
            bg="#d9d9d9"
        )
        select_label.pack(pady=(3, 5), padx=20, anchor="w")

        self.select_container = tk.Frame(self.left_frame, bg="#d9d9d9")
        self.select_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        self.select_canvas = tk.Canvas(
            self.select_container,
            bg="#d9d9d9",
            highlightthickness=0
        )

        self.select_scrollbar = tk.Scrollbar(
            self.select_container,
            orient=tk.VERTICAL,
            command=self.select_canvas.yview
        )

        self.checkbox_frame = tk.Frame(self.select_canvas, bg="#d9d9d9")

        self.checkbox_frame.bind(
            "<Configure>",
            lambda e: self.select_canvas.configure(
                scrollregion=self.select_canvas.bbox("all")
            )
        )

        self.select_canvas.create_window(
            (0, 0),
            window=self.checkbox_frame,
            anchor="nw"
        )

        self.select_canvas.configure(yscrollcommand=self.select_scrollbar.set)

        self.select_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.select_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # --------------------------------------------------------
        # Matplotlib Figure
        # --------------------------------------------------------
        self.fig = Figure(figsize=(14.5, 8.2), dpi=100, constrained_layout=True)

        gs = self.fig.add_gridspec(
            2, 2,
            width_ratios=[1.20, 1.45],
            height_ratios=[1.0, 1.0],
            wspace=0.08,
            hspace=0.15
        )

        self.ax_mag = self.fig.add_subplot(gs[0, 0])
        self.ax_phase = self.fig.add_subplot(gs[1, 0])
        self.ax_smith = self.fig.add_subplot(gs[:, 1])

        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.canvas.mpl_connect("axes_leave_event", self.clear_hover_annotations)
        self.canvas.mpl_connect("figure_leave_event", self.clear_hover_annotations)

        self._draw_empty_axes()

    def _draw_empty_axes(self):
        self.ax_mag.clear()
        self.ax_phase.clear()
        draw_smith_chart(self.ax_smith)

        self.ax_mag.set_title("S-parameter Magnitude")
        self.ax_mag.set_xlabel("Frequency")
        self.ax_mag.set_ylabel("Magnitude (dB)")
        self.ax_mag.grid(True)

        self.ax_phase.set_title("S-parameter Unwrapped Phase")
        self.ax_phase.set_xlabel("Frequency")
        self.ax_phase.set_ylabel("Phase (degree)")
        self.ax_phase.grid(True)

        self.ax_smith.set_title("Smith Chart")

        self.canvas.draw()

    def browse_file(self):
        filepath = filedialog.askopenfilename(
            title="SnP 파일 선택",
            filetypes=[
                ("Touchstone files", "*.s1p *.s2p *.s3p *.s4p *.s5p *.s6p *.s7p *.s8p *.s9p *.s10p *.s*p"),
                ("All files", "*.*")
            ]
        )

        if filepath:
            self.file_var.set(filepath)

    def apply_plot(self):
        filepath = self.file_var.get().strip()

        if not filepath:
            messagebox.showwarning("파일 없음", "SnP 파일 경로를 입력하거나 불러오세요.")
            return

        if not os.path.isfile(filepath):
            messagebox.showerror("파일 오류", "입력한 파일이 존재하지 않습니다.")
            return

        try:
            self.freq_hz, self.s, self.z0, self.fmt, self.unit = parse_touchstone_snp(filepath)
        except Exception as e:
            messagebox.showerror("파싱 오류", str(e))
            return

        self.create_sparam_checkboxes()
        self.set_default_frequency_range()
        self.plot_selected_sparameters()

        self.info_label.config(
            text=(
                f"파일 형식: S{self.s.shape[1]}P\n"
                f"데이터 타입: {self.fmt}\n"
                f"기준 임피던스: {self.z0:g} Ω\n"
                f"주파수 포인트: {len(self.freq_hz)}"
            )
        )

    def create_sparam_checkboxes(self):
        for widget in self.checkbox_frame.winfo_children():
            widget.destroy()

        self.sparam_vars.clear()
        self.sparam_indices.clear()

        nport = self.s.shape[1]

        for row in range(nport):
            for col in range(nport):
                label = f"S{row + 1}{col + 1}"

                var = tk.BooleanVar(value=True)

                self.sparam_vars[label] = var
                self.sparam_indices[label] = (row, col)

                cb = tk.Checkbutton(
                    self.checkbox_frame,
                    text=label,
                    variable=var,
                    command=self.plot_selected_sparameters,
                    bg="#d9d9d9",
                    font=("Arial", 11),
                    anchor="w"
                )
                cb.pack(fill=tk.X, anchor="w", padx=5, pady=2)

    def get_selected_sparams(self):
        selected = []

        for label, var in self.sparam_vars.items():
            if var.get():
                row, col = self.sparam_indices[label]
                selected.append((label, row, col))

        return selected

    def get_frequency_axis(self):
        fmax = np.max(self.freq_hz)

        if fmax >= 1e9:
            return self.freq_hz / 1e9, "Frequency (GHz)", "GHz"
        elif fmax >= 1e6:
            return self.freq_hz / 1e6, "Frequency (MHz)", "MHz"
        elif fmax >= 1e3:
            return self.freq_hz / 1e3, "Frequency (kHz)", "kHz"
        else:
            return self.freq_hz, "Frequency (Hz)", "Hz"

    def set_default_frequency_range(self):
        freq, f_label, f_unit = self.get_frequency_axis()

        self.start_freq_var.set(f"{np.min(freq):.6g}")
        self.stop_freq_var.set(f"{np.max(freq):.6g}")
        self.range_unit_var.set(f"단위: {f_unit}")

    def get_frequency_mask(self):
        freq, f_label, f_unit = self.get_frequency_axis()

        start_text = self.start_freq_var.get().strip()
        stop_text = self.stop_freq_var.get().strip()

        if start_text == "":
            start_freq = np.min(freq)
        else:
            start_freq = float(start_text)

        if stop_text == "":
            stop_freq = np.max(freq)
        else:
            stop_freq = float(stop_text)

        if start_freq > stop_freq:
            start_freq, stop_freq = stop_freq, start_freq

        mask = (freq >= start_freq) & (freq <= stop_freq)

        if not np.any(mask):
            raise ValueError(
                f"선택한 주파수 범위에 데이터가 없습니다.\n"
                f"입력 범위: {start_freq:g} ~ {stop_freq:g} {f_unit}\n"
                f"파일 범위: {np.min(freq):g} ~ {np.max(freq):g} {f_unit}"
            )

        return mask, start_freq, stop_freq

    def clear_cursors(self):
        for cursor in self.cursors:
            try:
                cursor.remove()
            except Exception:
                pass

        self.cursors.clear()

    def clear_hover_annotations(self, event=None):
        changed = False

        for cursor in self.cursors:
            try:
                for sel in list(cursor.selections):
                    try:
                        sel.remove()
                        changed = True
                    except Exception:
                        try:
                            sel.annotation.remove()
                            changed = True
                        except Exception:
                            pass
            except Exception:
                pass

        if changed:
            self.canvas.draw_idle()

    def plot_selected_sparameters(self):
        if self.freq_hz is None or self.s is None:
            return

        self.clear_hover_annotations()
        self.clear_cursors()

        try:
            mask, start_freq, stop_freq = self.get_frequency_mask()
        except ValueError as e:
            messagebox.showerror("주파수 범위 오류", str(e))
            return
        except Exception:
            messagebox.showerror(
                "주파수 입력 오류",
                "시작 주파수와 종료 주파수에는 숫자만 입력하세요."
            )
            return

        selected = self.get_selected_sparams()

        freq_all, f_label, f_unit = self.get_frequency_axis()
        freq = freq_all[mask]

        self.ax_mag.clear()
        self.ax_phase.clear()
        draw_smith_chart(self.ax_smith)

        self.ax_mag.set_title(
            f"S-parameter Magnitude ({start_freq:g} ~ {stop_freq:g} {f_unit})"
        )
        self.ax_phase.set_title(
            f"S-parameter Unwrapped Phase ({start_freq:g} ~ {stop_freq:g} {f_unit})"
        )
        self.ax_smith.set_title(
            f"Smith Chart ({start_freq:g} ~ {stop_freq:g} {f_unit})"
        )

        eps = 1e-20

        mag_lines = []
        phase_lines = []
        smith_lines = []

        smith_data_dict = {}

        if not selected:
            self.ax_mag.text(
                0.5, 0.5,
                "선택된 S-parameter가 없습니다.",
                transform=self.ax_mag.transAxes,
                ha="center",
                va="center"
            )

            self.ax_phase.text(
                0.5, 0.5,
                "선택된 S-parameter가 없습니다.",
                transform=self.ax_phase.transAxes,
                ha="center",
                va="center"
            )

            self.canvas.draw()
            return

        for label, row, col in selected:
            sij_full = self.s[:, row, col]
            sij = sij_full[mask]

            mag_db = 20 * np.log10(np.maximum(np.abs(sij), eps))
            phase_unwrapped_deg = np.rad2deg(np.unwrap(np.angle(sij)))

            mag_line, = self.ax_mag.plot(
                freq,
                mag_db,
                label=label,
                linewidth=1.5
            )

            phase_line, = self.ax_phase.plot(
                freq,
                phase_unwrapped_deg,
                label=label,
                linewidth=1.5
            )

            smith_line, = self.ax_smith.plot(
                np.real(sij),
                np.imag(sij),
                label=label,
                linewidth=1.7
            )

            mag_lines.append(mag_line)
            phase_lines.append(phase_line)
            smith_lines.append(smith_line)

            smith_data_dict[smith_line] = {
                "label": label,
                "data": sij
            }

        # --------------------------------------------------------
        # Magnitude plot
        # --------------------------------------------------------
        self.ax_mag.set_xlabel(f_label)
        self.ax_mag.set_ylabel("Magnitude (dB)")
        self.ax_mag.grid(True)

        self.ax_mag.legend(
            loc="upper center",
            bbox_to_anchor=(0.5, -0.18),
            ncol=min(4, max(1, len(selected))),
            frameon=True
        )

        # --------------------------------------------------------
        # Phase plot
        # --------------------------------------------------------
        self.ax_phase.set_xlabel(f_label)
        self.ax_phase.set_ylabel("Unwrapped Phase (degree)")
        self.ax_phase.grid(True)

        self.ax_phase.legend(
            loc="upper center",
            bbox_to_anchor=(0.5, -0.18),
            ncol=min(4, max(1, len(selected))),
            frameon=True
        )

        # --------------------------------------------------------
        # Smith chart
        # --------------------------------------------------------
        self.ax_smith.legend(
            loc="upper center",
            bbox_to_anchor=(0.5, -0.04),
            ncol=min(6, max(1, len(selected))),
            frameon=True
        )

        # --------------------------------------------------------
        # Hover: magnitude
        # --------------------------------------------------------
        mag_cursor = mplcursors.cursor(mag_lines, hover=HoverMode.Transient)

        @mag_cursor.connect("add")
        def on_add_mag(sel):
            line = sel.artist
            label = line.get_label()
            idx = int(round(sel.index))

            x_data = line.get_xdata()
            y_data = line.get_ydata()

            idx = max(0, min(idx, len(x_data) - 1))

            sel.annotation.set_text(
                f"{label}\n"
                f"f = {x_data[idx]:.6g} {f_unit}\n"
                f"|S| = {y_data[idx]:.3f} dB"
            )

        # --------------------------------------------------------
        # Hover: phase
        # --------------------------------------------------------
        phase_cursor = mplcursors.cursor(phase_lines, hover=HoverMode.Transient)

        @phase_cursor.connect("add")
        def on_add_phase(sel):
            line = sel.artist
            label = line.get_label()
            idx = int(round(sel.index))

            x_data = line.get_xdata()
            y_data = line.get_ydata()

            idx = max(0, min(idx, len(x_data) - 1))

            sel.annotation.set_text(
                f"{label}\n"
                f"f = {x_data[idx]:.6g} {f_unit}\n"
                f"phase = {y_data[idx]:.3f} deg"
            )

        # --------------------------------------------------------
        # Hover: Smith chart
        # --------------------------------------------------------
        smith_cursor = mplcursors.cursor(smith_lines, hover=HoverMode.Transient)

        @smith_cursor.connect("add")
        def on_add_smith(sel):
            line = sel.artist
            idx = int(round(sel.index))

            item = smith_data_dict[line]
            label = item["label"]
            sij = item["data"]

            idx = max(0, min(idx, len(sij) - 1))
            gamma = sij[idx]

            sel.annotation.set_text(
                f"{label}\n"
                f"f = {freq[idx]:.6g} {f_unit}\n"
                f"Re(Γ) = {np.real(gamma):.4f}\n"
                f"Im(Γ) = {np.imag(gamma):.4f}\n"
                f"|Γ| = {np.abs(gamma):.4f}\n"
                f"∠Γ = {np.rad2deg(np.angle(gamma)):.2f} deg"
            )

        self.cursors.extend([
            mag_cursor,
            phase_cursor,
            smith_cursor
        ])

        self.canvas.draw()


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    root = tk.Tk()
    app = SNPViewerApp(root)
    root.mainloop()
