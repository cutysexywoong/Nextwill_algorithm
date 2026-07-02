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

    ax.set_xlim(-1.05, 1.05)
    ax.set_ylim(-1.05, 1.05)

    theta = np.linspace(0, 2 * np.pi, 1000)
    ax.plot(np.cos(theta), np.sin(theta), color="black", linewidth=1.1)

    # constant resistance circles
    r_values = [0, 0.2, 0.5, 1, 2, 5]
    x_sweep = np.linspace(-50, 50, 3000)

    for r in r_values:
        gamma = gamma_from_z_norm(r, x_sweep)
        mask = np.abs(gamma) <= 1.001
        ax.plot(
            np.real(gamma[mask]),
            np.imag(gamma[mask]),
            color="0.75",
            linewidth=0.7
        )

    # constant reactance arcs
    x_values = [0.2, 0.5, 1, 2, 5, -0.2, -0.5, -1, -2, -5]
    r_sweep = np.linspace(0, 50, 3000)

    for x in x_values:
        gamma = gamma_from_z_norm(r_sweep, x)
        mask = np.abs(gamma) <= 1.001
        ax.plot(
            np.real(gamma[mask]),
            np.imag(gamma[mask]),
            color="0.75",
            linewidth=0.7
        )

    ax.axhline(0, color="0.65", linewidth=0.8)
    ax.axvline(0, color="0.85", linewidth=0.7)

    # 축 눈금/라벨 제거
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
        self.cursors = []

        self._build_gui()

    def _build_gui(self):
        self.root.geometry("1520x860")

        left_frame = tk.Frame(self.root, width=270, bg="#d9d9d9")
        left_frame.pack(side=tk.LEFT, fill=tk.Y)

        plot_frame = tk.Frame(self.root)
        plot_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        label = tk.Label(
            left_frame,
            text="입력 파일",
            font=("Arial", 18),
            bg="#d9d9d9"
        )
        label.pack(pady=(50, 10), anchor="w", padx=20)

        entry = tk.Entry(
            left_frame,
            textvariable=self.file_var,
            font=("Arial", 12),
            width=28
        )
        entry.pack(padx=20, pady=5)

        # 버튼 같은 줄
        button_frame = tk.Frame(left_frame, bg="#d9d9d9")
        button_frame.pack(pady=15)

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
            left_frame,
            text="",
            justify=tk.LEFT,
            bg="#d9d9d9",
            font=("Arial", 10)
        )
        self.info_label.pack(pady=20, padx=20, anchor="w")

        # Figure / GridSpec
        self.fig = Figure(figsize=(13.5, 7.6), dpi=100, constrained_layout=True)
        gs = self.fig.add_gridspec(
            2, 2,
            width_ratios=[1.55, 1.0],
            height_ratios=[1.0, 1.0],
            wspace=0.18,
            hspace=0.12
        )

        self.ax_db = self.fig.add_subplot(gs[0, 0])
        self.ax_phase = self.fig.add_subplot(gs[1, 0])
        self.ax_s11 = self.fig.add_subplot(gs[0, 1])
        self.ax_s22 = self.fig.add_subplot(gs[1, 1])

        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # 마우스가 축/그림을 벗어나면 hover annotation 제거
        self.canvas.mpl_connect("axes_leave_event", self.clear_hover_annotations)
        self.canvas.mpl_connect("figure_leave_event", self.clear_hover_annotations)

        self._draw_empty_axes()

    def _draw_empty_axes(self):
        self.ax_db.clear()
        self.ax_phase.clear()

        self.ax_db.set_title("S-parameter (dB)")
        self.ax_phase.set_title("S21 (Unwrapped Phase)")
        self.ax_db.set_xlabel("Frequency")
        self.ax_db.set_ylabel("Magnitude (dB)")
        self.ax_phase.set_xlabel("Frequency")
        self.ax_phase.set_ylabel("Phase (degree)")

        self.ax_db.grid(True)
        self.ax_phase.grid(True)

        draw_smith_chart(self.ax_s11)
        draw_smith_chart(self.ax_s22)

        self.ax_s11.set_title("S11 (Smith Chart)")
        self.ax_s22.set_title("S22 (Smith Chart)")

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
            freq_hz, s, z0, fmt, unit = parse_touchstone_snp(filepath)
        except Exception as e:
            messagebox.showerror("파싱 오류", str(e))
            return

        nport = s.shape[1]
        if nport < 2:
            messagebox.showerror("포트 오류", "현재 그래프 구성은 최소 S2P 파일 이상을 기준으로 합니다.")
            return

        self.plot_sparameters(freq_hz, s, z0, fmt, unit)

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

    def plot_sparameters(self, freq_hz, s, z0, fmt, unit):
        self.clear_cursors()
        self.clear_hover_annotations()

        fmax = np.max(freq_hz)

        if fmax >= 1e9:
            freq = freq_hz / 1e9
            f_label = "Frequency (GHz)"
            f_unit = "GHz"
        elif fmax >= 1e6:
            freq = freq_hz / 1e6
            f_label = "Frequency (MHz)"
            f_unit = "MHz"
        elif fmax >= 1e3:
            freq = freq_hz / 1e3
            f_label = "Frequency (kHz)"
            f_unit = "kHz"
        else:
            freq = freq_hz
            f_label = "Frequency (Hz)"
            f_unit = "Hz"

        eps = 1e-20

        s11 = s[:, 0, 0]
        s21 = s[:, 1, 0]
        s12 = s[:, 0, 1]
        s22 = s[:, 1, 1]

        s11_db = 20 * np.log10(np.maximum(np.abs(s11), eps))
        s21_db = 20 * np.log10(np.maximum(np.abs(s21), eps))
        s12_db = 20 * np.log10(np.maximum(np.abs(s12), eps))
        s22_db = 20 * np.log10(np.maximum(np.abs(s22), eps))

        s21_phase_unwrapped_deg = np.rad2deg(np.unwrap(np.angle(s21)))

        # Clear axes
        self.ax_db.clear()
        self.ax_phase.clear()
        draw_smith_chart(self.ax_s11)
        draw_smith_chart(self.ax_s22)

        # --------------------------------------------------------
        # 좌측 상단: dB magnitude
        # --------------------------------------------------------
        line_s11_db, = self.ax_db.plot(freq, s11_db, label="S11")
        line_s12_db, = self.ax_db.plot(freq, s12_db, label="S12")
        line_s21_db, = self.ax_db.plot(freq, s21_db, label="S21")
        line_s22_db, = self.ax_db.plot(freq, s22_db, label="S22")

        self.ax_db.set_title("S-parameter (dB)")
        self.ax_db.set_xlabel(f_label)
        self.ax_db.set_ylabel("Magnitude (dB)")
        self.ax_db.grid(True)

        # 범례를 그래프 외부(아래)로 이동
        self.ax_db.legend(
            loc="upper center",
            bbox_to_anchor=(0.5, -0.18),
            ncol=4,
            frameon=True
        )

        # --------------------------------------------------------
        # 좌측 하단: S21 phase
        # --------------------------------------------------------
        line_s21_phase, = self.ax_phase.plot(
            freq,
            s21_phase_unwrapped_deg,
            label="S21 phase"
        )

        self.ax_phase.set_title("S21 (Unwrapped Phase)")
        self.ax_phase.set_xlabel(f_label)
        self.ax_phase.set_ylabel("Phase (degree)")
        self.ax_phase.grid(True)

        # 범례를 그래프 외부로 이동
        self.ax_phase.legend(
            loc="upper right",
            bbox_to_anchor=(1.0, 1.02),
            frameon=True
        )

        # --------------------------------------------------------
        # 우측 상단: S11 Smith Chart
        # --------------------------------------------------------
        line_s11_smith, = self.ax_s11.plot(
            np.real(s11),
            np.imag(s11),
            linewidth=1.6,
            label="S11"
        )
        start_s11 = self.ax_s11.scatter(np.real(s11[0]), np.imag(s11[0]), marker="o", label="Start")
        end_s11 = self.ax_s11.scatter(np.real(s11[-1]), np.imag(s11[-1]), marker="x", label="End")

        self.ax_s11.set_title("S11 (Smith Chart)")

        # 범례를 차트 외부 오른쪽으로 이동
        self.ax_s11.legend(
            loc="upper left",
            bbox_to_anchor=(1.02, 1.00),
            borderaxespad=0.0,
            frameon=True
        )

        # --------------------------------------------------------
        # 우측 하단: S22 Smith Chart
        # --------------------------------------------------------
        line_s22_smith, = self.ax_s22.plot(
            np.real(s22),
            np.imag(s22),
            linewidth=1.6,
            label="S22"
        )
        start_s22 = self.ax_s22.scatter(np.real(s22[0]), np.imag(s22[0]), marker="o", label="Start")
        end_s22 = self.ax_s22.scatter(np.real(s22[-1]), np.imag(s22[-1]), marker="x", label="End")

        self.ax_s22.set_title("S22 (Smith Chart)")

        self.ax_s22.legend(
            loc="upper left",
            bbox_to_anchor=(1.02, 1.00),
            borderaxespad=0.0,
            frameon=True
        )

        # --------------------------------------------------------
        # Hover cursor
        # --------------------------------------------------------
        db_lines = [line_s11_db, line_s12_db, line_s21_db, line_s22_db]
        db_cursor = mplcursors.cursor(db_lines, hover=HoverMode.Transient)

        @db_cursor.connect("add")
        def on_add_db(sel):
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

        phase_cursor = mplcursors.cursor([line_s21_phase], hover=HoverMode.Transient)

        @phase_cursor.connect("add")
        def on_add_phase(sel):
            idx = int(round(sel.index))
            x_data = line_s21_phase.get_xdata()
            y_data = line_s21_phase.get_ydata()

            idx = max(0, min(idx, len(x_data) - 1))

            sel.annotation.set_text(
                f"S21 phase\n"
                f"f = {x_data[idx]:.6g} {f_unit}\n"
                f"phase = {y_data[idx]:.3f} deg"
            )

        s11_cursor = mplcursors.cursor([line_s11_smith], hover=HoverMode.Transient)

        @s11_cursor.connect("add")
        def on_add_s11_smith(sel):
            idx = int(round(sel.index))
            idx = max(0, min(idx, len(s11) - 1))
            gamma = s11[idx]

            sel.annotation.set_text(
                f"S11\n"
                f"f = {freq[idx]:.6g} {f_unit}\n"
                f"Re(Γ) = {np.real(gamma):.4f}\n"
                f"Im(Γ) = {np.imag(gamma):.4f}\n"
                f"|Γ| = {np.abs(gamma):.4f}\n"
                f"∠Γ = {np.rad2deg(np.angle(gamma)):.2f} deg"
            )

        s22_cursor = mplcursors.cursor([line_s22_smith], hover=HoverMode.Transient)

        @s22_cursor.connect("add")
        def on_add_s22_smith(sel):
            idx = int(round(sel.index))
            idx = max(0, min(idx, len(s22) - 1))
            gamma = s22[idx]

            sel.annotation.set_text(
                f"S22\n"
                f"f = {freq[idx]:.6g} {f_unit}\n"
                f"Re(Γ) = {np.real(gamma):.4f}\n"
                f"Im(Γ) = {np.imag(gamma):.4f}\n"
                f"|Γ| = {np.abs(gamma):.4f}\n"
                f"∠Γ = {np.rad2deg(np.angle(gamma)):.2f} deg"
            )

        self.cursors.extend([
            db_cursor,
            phase_cursor,
            s11_cursor,
            s22_cursor
        ])

        self.canvas.draw()

        self.info_label.config(
            text=(
                f"파일 형식: S{s.shape[1]}P\n"
                f"데이터 타입: {fmt}\n"
                f"기준 임피던스: {z0:g} Ω\n"
                f"주파수 포인트: {len(freq_hz)}"
            )
        )


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    root = tk.Tk()
    app = SNPViewerApp(root)
    root.mainloop()
