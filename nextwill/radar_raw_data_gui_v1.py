"""GUI에서 1~3대의 정지/이동 드론 Raw I/Q를 생성합니다."""

from __future__ import annotations

import json
import threading
import tkinter as tk
from dataclasses import replace
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from radar_raw_data_v1 import DroneConfig, RadarConfig, generate_raw_data, save_raw_data


class RawDataGeneratorGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Integrated FMCW Radar Scenario & Raw Data Generator")
        self.root.minsize(1100, 900)
        self.is_generating = False
        self._create_variables()
        self._build_layout()
        self._update_derived_fields()
        self._update_previews()

    def _create_variables(self):
        self.radar_vars = {
            "start": tk.StringVar(value="24.000"),
            "stop": tk.StringVar(value="24.250"),
            "center": tk.StringVar(value="24.125"),
            "chirp": tk.StringVar(value="200"),
            "sample_rate": tk.StringVar(value="100"),
            "samples": tk.StringVar(value="20000"),
            "chirps": tk.StringVar(value="128"),
            "snr": tk.StringVar(value="25"),
            "height": tk.StringVar(value="2"),
        }
        self.var_drone_count = tk.IntVar(value=1)
        defaults = [
            ("0", "1000", "37", "0", "0", "0", "1200"),
            ("-200", "1400", "60", "2", "-1", "0", "1000"),
            ("300", "1800", "90", "-1", "2", "0", "900"),
        ]
        self.drone_vars = []
        for x, y, z, vx, vy, vz, rpm in defaults:
            self.drone_vars.append({
                "x": tk.StringVar(value=x), "y": tk.StringVar(value=y),
                "altitude": tk.StringVar(value=z), "vx": tk.StringVar(value=vx),
                "vy": tk.StringVar(value=vy), "vz": tk.StringVar(value=vz),
                "rpm": tk.StringVar(value=rpm), "rotors": tk.StringVar(value="4"),
                "blades": tk.StringVar(value="2"), "radius": tk.StringVar(value="0.08"),
                "body": tk.StringVar(value="1.0"), "blade": tk.StringVar(value="0.035"),
            })
        output = Path(__file__).resolve().parent / "generated_raw_data" / "gui_moving_drones_raw_v1.npz"
        self.var_output = tk.StringVar(value=str(output))
        self.var_compressed = tk.BooleanVar(value=False)
        self.var_seed = tk.StringVar(value="2026")
        self.var_status = tk.StringVar(value="조건을 설정한 뒤 Raw Data 생성을 누르세요.")

    @staticmethod
    def _entry(parent, row, label, variable, readonly=False):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=4, pady=3)
        ttk.Entry(parent, textvariable=variable, state="readonly" if readonly else "normal").grid(
            row=row, column=1, sticky="ew", padx=4, pady=3
        )

    def _build_layout(self):
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill="both", expand=True)
        main.columnconfigure((0, 1), weight=1)
        main.rowconfigure(2, weight=2)
        main.rowconfigure(3, weight=1)

        radar = ttk.LabelFrame(main, text="1. FMCW 송신 및 ADC 조건", padding=10)
        radar.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=(0, 8))
        radar.columnconfigure(1, weight=1)
        fields = [
            ("시작 주파수 [GHz]", "start", False), ("종료 주파수 [GHz]", "stop", False),
            ("중심 주파수 [GHz]", "center", True), ("Chirp 시간 [us]", "chirp", False),
            ("ADC 샘플률 [MHz]", "sample_rate", False), ("Chirp당 샘플 수", "samples", True),
            ("Chirp 개수", "chirps", False), ("수신 SNR [dB]", "snr", False),
            ("레이더 높이 [m]", "height", False),
        ]
        for row, (label, key, readonly) in enumerate(fields):
            self._entry(radar, row, label, self.radar_vars[key], readonly)

        drones = ttk.LabelFrame(main, text="2. 드론 조건 (최대 3대)", padding=10)
        drones.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=(0, 8))
        drones.columnconfigure(1, weight=1)
        ttk.Label(drones, text="활성 드론 수").grid(row=0, column=0, sticky="w", padx=4)
        ttk.Spinbox(drones, from_=1, to=3, textvariable=self.var_drone_count, width=8,
                    state="readonly").grid(row=0, column=1, sticky="w", padx=4)
        notebook = ttk.Notebook(drones)
        notebook.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(8, 0))
        drone_fields = [
            ("X 좌표 [m]", "x"), ("Y 좌표 [m]", "y"), ("고도 [m]", "altitude"),
            ("X축 속도 Vx [m/s]", "vx"), ("Y축 속도 Vy [m/s]", "vy"),
            ("상승 속도 Vz [m/s]", "vz"), ("프로펠러 RPM", "rpm"),
            ("로터 개수", "rotors"), ("로터당 블레이드", "blades"),
            ("블레이드 반지름 [m]", "radius"), ("본체 반사 크기", "body"),
            ("블레이드 반사 크기", "blade"),
        ]
        for index, variables in enumerate(self.drone_vars, 1):
            tab = ttk.Frame(notebook, padding=8)
            tab.columnconfigure(1, weight=1)
            notebook.add(tab, text=f"드론 {index}")
            for row, (label, key) in enumerate(drone_fields):
                self._entry(tab, row, label, variables[key])

        output = ttk.LabelFrame(main, text="3. 출력", padding=10)
        output.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        output.columnconfigure(1, weight=1)
        ttk.Label(output, text="NPZ 경로").grid(row=0, column=0, padx=4)
        ttk.Entry(output, textvariable=self.var_output).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(output, text="찾기", command=self._browse_output).grid(row=0, column=2, padx=4)
        ttk.Label(output, text="난수 시드").grid(row=1, column=0, padx=4, pady=(6, 0))
        ttk.Entry(output, textvariable=self.var_seed, width=12).grid(row=1, column=1, sticky="w", padx=4, pady=(6, 0))
        ttk.Checkbutton(output, text="압축 저장", variable=self.var_compressed).grid(row=1, column=2, padx=4)


        preview = ttk.LabelFrame(
            main,
            text="4. FFT 이전 시간영역 송신·수신 I/Q 파형",
            padding=8,
        )
        preview.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(0, 8))
        preview.columnconfigure(0, weight=1)
        preview.rowconfigure(0, weight=1)
        self.preview_figure = Figure(figsize=(11, 3.6), dpi=100)
        self.signal_axis = self.preview_figure.add_subplot(111)
        self.preview_canvas = FigureCanvasTkAgg(self.preview_figure, master=preview)
        self.preview_canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        result = ttk.LabelFrame(main, text="5. 생성 결과", padding=8)
        result.grid(row=3, column=0, columnspan=2, sticky="nsew")
        result.columnconfigure(0, weight=1); result.rowconfigure(0, weight=1)
        self.result_text = tk.Text(result, height=10, font=("Consolas", 10), state="disabled")
        self.result_text.grid(row=0, column=0, sticky="nsew")
        bar = ttk.Scrollbar(result, command=self.result_text.yview)
        bar.grid(row=0, column=1, sticky="ns"); self.result_text.configure(yscrollcommand=bar.set)

        actions = ttk.Frame(main); actions.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        actions.columnconfigure(0, weight=1)
        self.progress = ttk.Progressbar(actions, mode="indeterminate")
        self.progress.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.generate_button = ttk.Button(actions, text="Raw Data 생성", command=self._start_generation)
        self.generate_button.grid(row=0, column=1)
        ttk.Label(self.root, textvariable=self.var_status, relief="sunken", anchor="w", padding=5).pack(fill="x")
        for key in ("start", "stop", "chirp", "sample_rate"):
            self.radar_vars[key].trace_add("write", self._update_derived_fields)
        self.radar_vars["height"].trace_add("write", self._schedule_preview_update)
        self.var_drone_count.trace_add("write", self._schedule_preview_update)
        for variables in self.drone_vars:
            for key in variables:
                variables[key].trace_add("write", self._schedule_preview_update)

    def _update_derived_fields(self, *_):
        try:
            start = float(self.radar_vars["start"].get()); stop = float(self.radar_vars["stop"].get())
            chirp = float(self.radar_vars["chirp"].get()); rate = float(self.radar_vars["sample_rate"].get())
        except ValueError:
            return
        self.radar_vars["center"].set(f"{(start + stop) / 2:.6f}")
        self.radar_vars["samples"].set(str(round(chirp * rate)))
        self._schedule_preview_update()

    def _schedule_preview_update(self, *_):
        """입력이 끝난 뒤 미리보기를 갱신해 타이핑 중 중복 계산을 줄입니다."""
        if hasattr(self, "preview_canvas"):
            if hasattr(self, "preview_after_id"):
                self.root.after_cancel(self.preview_after_id)
            self.preview_after_id = self.root.after(350, self._update_previews)

    def _update_previews(self):
        """FFT를 적용하기 전 첫 번째 Chirp의 시간영역 Beat I/Q를 표시합니다."""
        self.signal_axis.clear()
        try:
            radar, drones, seed, _ = self._build_configs()
            preview_radar = replace(radar, number_of_chirps=1)
            preview_data = generate_raw_data(preview_radar, drones, seed=seed)
            fast_time_us = preview_data["fast_time_s"] * 1e6
            transmit_iq = preview_data["tx_reference"]
            receive_iq = preview_data["reflected_echo"][0]
            # 화면 렌더링 부담을 줄이되 원 데이터 계산은 전체 ADC 샘플로 수행합니다.
            stride = max(1, len(fast_time_us) // 2500)
            self.signal_axis.plot(
                fast_time_us[::stride], transmit_iq.real[::stride],
                color="#1565c0", linewidth=1.0, label="Tx I (real)",
            )
            self.signal_axis.plot(
                fast_time_us[::stride], transmit_iq.imag[::stride],
                color="#42a5f5", linewidth=0.9, alpha=0.85, label="Tx Q (imag)",
            )
            self.signal_axis.plot(
                fast_time_us[::stride], receive_iq.real[::stride],
                color="#d32f2f", linewidth=1.0, label="Rx I (real)",
            )
            self.signal_axis.plot(
                fast_time_us[::stride], receive_iq.imag[::stride],
                color="#fb8c00", linewidth=0.9, alpha=0.85, label="Rx Q (imag)",
            )
            self.signal_axis.set_title(
                "Time-Domain Transmit and Receive I/Q Before FFT "
                f"({len(drones)} Drone{'s' if len(drones) > 1 else ''})"
            )
            self.signal_axis.set_xlabel("Time within one Chirp [us]")
            self.signal_axis.set_ylabel("Complex signal amplitude")
            self.signal_axis.grid(True, alpha=0.3)
            self.signal_axis.legend(loc="upper right", fontsize=8)
        except (ValueError, ZeroDivisionError) as error:
            self.signal_axis.text(
                0.5,
                0.5,
                f"유효한 송신·드론 조건을 입력하세요.\n{error}",
                ha="center",
                va="center",
                transform=self.signal_axis.transAxes,
            )
        self.preview_figure.tight_layout()
        self.preview_canvas.draw_idle()

    def _browse_output(self):
        selected = filedialog.asksaveasfilename(defaultextension=".npz", filetypes=[("NumPy archive", "*.npz")])
        if selected: self.var_output.set(selected)

    def _build_configs(self):
        v = self.radar_vars
        radar = RadarConfig(
            float(v["start"].get()) * 1e9, float(v["stop"].get()) * 1e9,
            float(v["center"].get()) * 1e9, float(v["chirp"].get()) * 1e-6,
            float(v["sample_rate"].get()) * 1e6, int(v["samples"].get()),
            int(v["chirps"].get()), float(v["height"].get()), float(v["snr"].get()),
        )
        count = int(self.var_drone_count.get())
        if not 1 <= count <= 3: raise ValueError("활성 드론 수는 1~3대여야 합니다.")
        drone_list = []
        for d in self.drone_vars[:count]:
            drone_list.append(DroneConfig(
                x_m=float(d["x"].get()), y_m=float(d["y"].get()), altitude_m=float(d["altitude"].get()),
                velocity_x_mps=float(d["vx"].get()), velocity_y_mps=float(d["vy"].get()),
                velocity_z_mps=float(d["vz"].get()), rotor_rpm=float(d["rpm"].get()),
                rotor_count=int(d["rotors"].get()), blades_per_rotor=int(d["blades"].get()),
                blade_radius_m=float(d["radius"].get()), body_reflection_amplitude=float(d["body"].get()),
                blade_reflection_amplitude=float(d["blade"].get()),
            ))
        path = Path(self.var_output.get()).expanduser().resolve().with_suffix(".npz")
        self.var_output.set(str(path))
        return radar, drone_list, int(self.var_seed.get()), path

    def _start_generation(self):
        if self.is_generating: return
        try: args = self._build_configs()
        except ValueError as error:
            messagebox.showerror("입력 오류", str(error)); return
        self.is_generating = True; self.generate_button.configure(state="disabled"); self.progress.start(12)
        self.var_status.set("드론 이동과 회전 반사를 계산하고 있습니다..."); self._set_result("Generating...\n")
        threading.Thread(target=self._worker, args=(*args, self.var_compressed.get()), daemon=True).start()

    def _worker(self, radar, drones, seed, path, compressed):
        try:
            data = generate_raw_data(radar, drones, seed); save_raw_data(path, data, compressed)
            metadata = json.loads(str(data["metadata_json"])); size = path.stat().st_size
        except Exception as error:
            self.root.after(0, self._failed, error); return
        self.root.after(0, self._finished, path, data["raw_iq"].shape, metadata, size)

    def _finished(self, path, shape, metadata, size):
        self.is_generating = False; self.progress.stop(); self.generate_button.configure(state="normal")
        lines = ["Raw data generation completed", "", f"Output: {path}",
                 f"File size: {size / 1024**2:.2f} MiB", f"raw_iq: {shape}, complex64",
                 f"Drone count: {metadata['drone_count']}"]
        for i, (drone, derived) in enumerate(zip(metadata["drones"], metadata["derived_drones"]), 1):
            lines += [f"Drone {i}: speed={derived['speed_mps']:.2f} m/s, RPM={drone['rotor_rpm']:.1f}",
                      f"  range={derived['initial']['slant_range_m']:.2f} -> {derived['final']['slant_range_m']:.2f} m",
                      f"  radial velocity={derived['initial']['radial_velocity_mps']:.2f} m/s"]
        lines += ["FFT: not applied", "Next: Range FFT axis=1, Doppler FFT axis=0"]
        self._set_result("\n".join(lines)); self.var_status.set(f"생성 완료: {path}")
        messagebox.showinfo("생성 완료", "Raw I/Q NPZ 파일을 저장했습니다.")

    def _failed(self, error):
        self.is_generating = False; self.progress.stop(); self.generate_button.configure(state="normal")
        self.var_status.set("생성 실패"); self._set_result(f"Generation failed\n\n{type(error).__name__}: {error}")
        messagebox.showerror("생성 실패", str(error))

    def _set_result(self, text):
        self.result_text.configure(state="normal"); self.result_text.delete("1.0", "end")
        self.result_text.insert("end", text); self.result_text.configure(state="disabled")


def main():
    root = tk.Tk()
    try: ttk.Style().theme_use("vista")
    except tk.TclError: pass
    RawDataGeneratorGUI(root); root.mainloop()


if __name__ == "__main__":
    main()
