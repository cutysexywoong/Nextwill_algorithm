"""정지 드론 1대의 송신/수신 FMCW 시간-주파수와 타깃 위치 통합 GUI."""

from __future__ import annotations

import math
import tkinter as tk
from tkinter import ttk

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

SPEED_OF_LIGHT = 299_792_458.0
HORIZONTAL_MIN_DEG = -50.0
HORIZONTAL_MAX_DEG = 50.0
VERTICAL_MIN_DEG = 0.0
VERTICAL_MAX_DEG = 10.0
MIN_RANGE_M = 1.0
MAX_RANGE_M = 5000.0


class StationaryDroneFMCWGUI:
    """송신 및 지연 수신의 순간 주파수 f(t)만 표시합니다."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Stationary Drone FMCW Time-Frequency GUI v1")
        self.root.geometry("1450x880")
        self.root.minsize(1050, 700)
        self.update_after_id = None
        self._create_variables()
        self._build_layout()
        self._schedule_update()

    def _create_variables(self):
        self.var_start_ghz = tk.StringVar(value="24.000")
        self.var_stop_ghz = tk.StringVar(value="24.250")
        self.var_chirp_time_ms = tk.StringVar(value="1.0")
        self.var_radar_height_m = tk.StringVar(value="2")
        self.var_x_m = tk.StringVar(value="0")
        self.var_y_m = tk.StringVar(value="1000")
        self.var_summary = tk.StringVar(value="")
        self.var_status = tk.StringVar(value="송신 조건과 정지 드론 좌표를 입력하세요.")

    @staticmethod
    def _add_entry(parent, row, label, variable):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(parent, textvariable=variable).grid(
            row=row, column=1, sticky="ew", padx=5, pady=5
        )

    def _build_layout(self):
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(1, weight=1)

        tx_frame = ttk.LabelFrame(main, text="1. 레이더 송신 FMCW 설정", padding=10)
        tx_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=(0, 8))
        tx_frame.columnconfigure(1, weight=1)
        self._add_entry(tx_frame, 0, "시작 주파수 [GHz]", self.var_start_ghz)
        self._add_entry(tx_frame, 1, "종료 주파수 [GHz]", self.var_stop_ghz)
        self._add_entry(tx_frame, 2, "Chirp time [ms]", self.var_chirp_time_ms)
        ttk.Label(
            tx_frame,
            text=(
                "상승 Chirp 1 ms + 하강 Chirp 1 ms = 전체 주기 2 ms\n"
                "송수신 삼각파 3주기와 Beat Frequency를 표시"
            ),
            foreground="#444444",
        ).grid(row=3, column=0, columnspan=2, sticky="w", padx=5, pady=(8, 0))

        target_frame = ttk.LabelFrame(main, text="2. 정지 드론 1대 설정", padding=10)
        target_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=(0, 8))
        target_frame.columnconfigure(1, weight=1)
        self._add_entry(
            target_frame,
            0,
            "레이더/드론 공통 높이 [m]",
            self.var_radar_height_m,
        )
        self._add_entry(target_frame, 1, "드론 X 좌표 [m]", self.var_x_m)
        self._add_entry(target_frame, 2, "드론 Y 좌표 [m]", self.var_y_m)
        ttk.Label(
            target_frame,
            text=(
                "레이더와 드론은 항상 같은 높이에 있습니다.\n"
                "드론 속도는 0 m/s이며 RPM·로터·블레이드는 사용하지 않습니다."
            ),
            foreground="#555555",
        ).grid(row=3, column=0, columnspan=2, sticky="w", padx=5, pady=(8, 0))

        plot_frame = ttk.LabelFrame(
            main,
            text="3. 시간에 따른 송신·수신 주파수 및 레이더 타깃 위치",
            padding=6,
        )
        plot_frame.grid(row=1, column=0, columnspan=2, sticky="nsew")
        plot_frame.columnconfigure(0, weight=1)
        plot_frame.rowconfigure(0, weight=1)

        self.figure = Figure(figsize=(13, 6.2), dpi=100)
        self.frequency_axis = self.figure.add_subplot(221)
        self.difference_axis = self.figure.add_subplot(223)
        self.target_axis = self.figure.add_subplot(122)
        self.canvas = FigureCanvasTkAgg(self.figure, master=plot_frame)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        ttk.Label(main, textvariable=self.var_summary).grid(
            row=2, column=0, columnspan=2, sticky="w", padx=4, pady=(8, 0)
        )
        ttk.Label(
            self.root,
            textvariable=self.var_status,
            relief="sunken",
            anchor="w",
            padding=5,
        ).pack(fill="x")

        for variable in (
            self.var_start_ghz,
            self.var_stop_ghz,
            self.var_chirp_time_ms,
            self.var_radar_height_m,
            self.var_x_m,
            self.var_y_m,
        ):
            variable.trace_add("write", self._schedule_update)

    def _read_conditions(self):
        start_hz = float(self.var_start_ghz.get()) * 1e9
        stop_hz = float(self.var_stop_ghz.get()) * 1e9
        chirp_s = float(self.var_chirp_time_ms.get()) * 1e-3
        radar_height = float(self.var_radar_height_m.get())
        x = float(self.var_x_m.get())
        y = float(self.var_y_m.get())
        altitude = radar_height

        if stop_hz <= start_hz:
            raise ValueError("종료 주파수는 시작 주파수보다 커야 합니다.")
        if chirp_s <= 0:
            raise ValueError("Chirp 시간은 0보다 커야 합니다.")
        if y < 0:
            raise ValueError("드론 Y 좌표는 레이더 정면 방향인 0 이상이어야 합니다.")
        if radar_height < 0:
            raise ValueError("레이더/드론 공통 높이는 0 m 이상이어야 합니다.")

        relative_height = altitude - radar_height
        horizontal_range = math.hypot(x, y)
        slant_range = math.sqrt(x * x + y * y + relative_height * relative_height)
        azimuth = math.degrees(math.atan2(x, y))
        elevation = math.degrees(math.atan2(relative_height, horizontal_range))
        if not MIN_RANGE_M <= slant_range <= MAX_RANGE_M:
            raise ValueError("레이더와 드론의 직선거리는 1~5000 m 범위여야 합니다.")
        if not HORIZONTAL_MIN_DEG <= azimuth <= HORIZONTAL_MAX_DEG:
            raise ValueError("드론 수평각은 -50~50도 범위여야 합니다.")
        if not VERTICAL_MIN_DEG <= elevation <= VERTICAL_MAX_DEG:
            raise ValueError("드론 수직각은 0~10도 범위여야 합니다.")

        # Chirp time은 상승 또는 하강에 걸리는 반주기입니다.
        slope = (stop_hz - start_hz) / chirp_s
        delay = 2.0 * slant_range / SPEED_OF_LIGHT
        return {
            "start_hz": start_hz,
            "stop_hz": stop_hz,
            "chirp_s": chirp_s,
            "period_s": 2.0 * chirp_s,
            "slope_hz_per_s": slope,
            "radar_height_m": radar_height,
            "x_m": x,
            "y_m": y,
            "altitude_m": altitude,
            "slant_range_m": slant_range,
            "azimuth_deg": azimuth,
            "elevation_deg": elevation,
            "delay_s": delay,
            "frequency_difference_hz": slope * delay,
        }

    def _schedule_update(self, *_):
        if self.update_after_id is not None:
            self.root.after_cancel(self.update_after_id)
        self.update_after_id = self.root.after(250, self._update_plots)

    def _update_plots(self):
        self.update_after_id = None
        self.frequency_axis.clear()
        self.difference_axis.clear()
        self.target_axis.clear()
        try:
            c = self._read_conditions()
            cycle_count = 3
            signal_duration_s = cycle_count * c["period_s"]
            tx_time_s = np.linspace(0.0, signal_duration_s, 4001)
            rx_time_s = np.linspace(
                c["delay_s"],
                signal_duration_s + c["delay_s"],
                4001,
            )

            def triangular_frequency(source_time_s):
                phase = np.mod(source_time_s, c["period_s"]) / c["period_s"]
                triangle = 1.0 - np.abs(2.0 * phase - 1.0)
                return c["start_hz"] + (c["stop_hz"] - c["start_hz"]) * triangle

            tx_frequency_hz = triangular_frequency(tx_time_s)
            # 수신 신호는 송신 삼각 FMCW가 왕복 지연된 복사본입니다.
            rx_frequency_hz = triangular_frequency(rx_time_s - c["delay_s"])

            max_time_ms = (signal_duration_s + c["delay_s"]) * 1e3
            frequency_margin_ghz = max((c["stop_hz"] - c["start_hz"]) / 1e9 * 0.05, 0.005)
            y_min = c["start_hz"] / 1e9 - frequency_margin_ghz
            y_max = c["stop_hz"] / 1e9 + frequency_margin_ghz

            self.frequency_axis.plot(
                tx_time_s * 1e3,
                tx_frequency_hz / 1e9,
                color="#1565c0",
                linewidth=1.8,
                label="Tx frequency f_tx(t)",
            )
            self.frequency_axis.plot(
                rx_time_s * 1e3,
                rx_frequency_hz / 1e9,
                color="#d32f2f",
                linewidth=1.5,
                label="Rx frequency f_rx(t)",
            )
            self.frequency_axis.set_xlim(0.0, max_time_ms)
            self.frequency_axis.set_ylim(y_min, y_max)
            self.frequency_axis.set_title(
                "Transmit and Reflected Receive Triangular FMCW (3 Cycles)"
            )
            self.frequency_axis.set_xlabel("Time [ms]")
            self.frequency_axis.set_ylabel("Frequency [GHz]")
            self.frequency_axis.grid(True, alpha=0.3)
            self.frequency_axis.legend(loc="lower right")

            # Beat frequency는 동일 시각 송수신 주파수 차이의 절댓값입니다.
            difference_time_s = np.linspace(
                c["delay_s"], signal_duration_s, 4000
            )
            tx_at_same_time_hz = triangular_frequency(difference_time_s)
            rx_at_same_time_hz = triangular_frequency(
                difference_time_s - c["delay_s"]
            )
            beat_frequency_hz = np.abs(tx_at_same_time_hz - rx_at_same_time_hz)
            self.difference_axis.plot(
                difference_time_s * 1e3,
                beat_frequency_hz / 1e6,
                color="#6a1b9a",
                linewidth=1.7,
                label="|f_tx(t) - f_rx(t)|",
            )
            self.difference_axis.set_ylim(bottom=0.0)
            self.difference_axis.set_xlim(0.0, max_time_ms)
            self.difference_axis.set_title("Beat Frequency")
            self.difference_axis.set_xlabel("Time [ms]")
            self.difference_axis.set_ylabel("Beat frequency [MHz]")
            self.difference_axis.grid(True, alpha=0.3)
            self.difference_axis.legend(loc="upper right")

            self.target_axis.set_facecolor("#071521")
            self.target_axis.set_xlim(HORIZONTAL_MIN_DEG, HORIZONTAL_MAX_DEG)
            self.target_axis.set_ylim(VERTICAL_MIN_DEG, VERTICAL_MAX_DEG)
            self.target_axis.axvline(0.0, color="#4dd0e1", linewidth=1.0)
            self.target_axis.axhline(
                2.0,
                color="#ffee58",
                linewidth=1.0,
                linestyle="--",
                label="Elevation center 2°",
            )
            self.target_axis.scatter(
                0.0,
                0.0,
                s=230,
                marker="^",
                color="#4dd0e1",
                edgecolor="white",
                linewidth=1.2,
                label="Radar",
                zorder=4,
            )
            self.target_axis.annotate(
                "Radar",
                (0.0, 0.0),
                xytext=(7, 8),
                textcoords="offset points",
                color="#b2ebf2",
            )
            self.target_axis.scatter(
                c["azimuth_deg"],
                c["elevation_deg"],
                s=180,
                color="#ff7043",
                edgecolor="#ffee58",
                linewidth=1.5,
                label="Stationary drone",
            )
            self.target_axis.annotate(
                f"Target\nR={c['slant_range_m']:.1f} m",
                (c["azimuth_deg"], c["elevation_deg"]),
                xytext=(8, 10),
                textcoords="offset points",
                color="#ffee58",
                fontweight="bold",
            )
            self.target_axis.set_title("Radar First-Person Target View", color="#b2ebf2")
            self.target_axis.set_xlabel("Horizontal angle [deg]", color="#80deea")
            self.target_axis.set_ylabel("Vertical angle [deg]", color="#80deea")
            self.target_axis.tick_params(colors="#80deea")
            self.target_axis.grid(True, color="#1e88a8", linestyle="--", alpha=0.4)
            self.target_axis.legend(loc="upper right")

            self.var_summary.set(
                f"거리 {c['slant_range_m']:.2f} m  |  "
                f"왕복 지연 {c['delay_s'] * 1e3:.6f} ms  |  "
                f"상승·하강 구간 Beat frequency {c['frequency_difference_hz'] / 1e6:.3f} MHz  |  "
                f"수평각 {c['azimuth_deg']:.2f}°  |  수직각 {c['elevation_deg']:.2f}°"
            )
            self.var_status.set(
                "송신과 지연 수신의 시간에 따른 순간 주파수를 표시합니다."
            )
        except (ValueError, ZeroDivisionError) as error:
            for axis in (
                self.frequency_axis,
                self.difference_axis,
                self.target_axis,
            ):
                axis.text(
                    0.5,
                    0.5,
                    str(error),
                    ha="center",
                    va="center",
                    transform=axis.transAxes,
                )
            self.var_summary.set("")
            self.var_status.set(f"입력 오류: {error}")

        self.figure.tight_layout()
        self.canvas.draw_idle()


def main():
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista")
    except tk.TclError:
        pass
    StationaryDroneFMCWGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
