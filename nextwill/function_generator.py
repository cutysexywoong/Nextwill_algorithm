"""
Function Generator GUI  —  웅 파트 Step 0
==========================================

24 GHz 대역 주파수 스윕 발생기를 모사한 학습용 GUI.

기능:
  - 스윕 파형 선택: 사인 / 삼각 / 사각파
  - 24.000~24.250 GHz 범위, 24.125 GHz 중심주파수
  - 스윕 반복률 실시간 조절 (실행 중에도 가능)
  - Run / Stop: 시간에 따른 순간 송신 주파수를 스크롤 그래프로 표시
  - 반복률을 바꿔도 위상이 점프하지 않는 phase accumulator 방식

목적: 파형·주파수·파장의 기초 감각을 다지고, 이후 레이더 신호 합성
(signal_synthesis.py)의 파형 생성 로직 토대로 사용.

실행:
  %LOCALAPPDATA%\\Programs\\Python\\Python313\\python.exe sim\\function_generator.py
"""

import tkinter as tk
from tkinter import ttk

import numpy as np
import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# matplotlib 그래프 안의 한글 라벨이 깨지지 않도록 Windows 한글 폰트 지정.
# (Tkinter 위젯은 시스템 폰트를 쓰므로 별도 설정 불필요)
matplotlib.rcParams["font.family"] = ["Malgun Gothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False  # 음수 부호(−) 깨짐 방지

# ----------------------------------------------------------------------------
# 디스플레이/주파수 스윕 파라미터
# ----------------------------------------------------------------------------
FS = 1000.0           # 디스플레이 샘플링 주파수 [Hz]
WINDOW_SEC = 1.0      # 화면에 보이는 시간 창 [s]
N_VISIBLE = int(FS * WINDOW_SEC)   # 화면 버퍼 샘플 수 (1000)
REFRESH_MS = 30       # 화면 갱신 주기 [ms]

# 화면에 표시할 RF 송신 주파수 범위와 중심주파수 [GHz]
RF_FREQ_MIN_GHZ = 24.000
RF_FREQ_MAX_GHZ = 24.250
RF_CENTER_FREQ_GHZ = 24.125
RF_HALF_BAND_GHZ = (RF_FREQ_MAX_GHZ - RF_FREQ_MIN_GHZ) / 2.0

# 주파수 스윕이 1초에 반복되는 횟수의 조절 범위 [Hz]
SWEEP_RATE_MIN_HZ, SWEEP_RATE_MAX_HZ = 0.5, 50.0
# 스윕 반복률 범위에 대응하는 주기 조절 범위 [ms]
PERIOD_MIN_MS = 1000.0 / SWEEP_RATE_MAX_HZ
PERIOD_MAX_MS = 1000.0 / SWEEP_RATE_MIN_HZ

WAVEFORMS = ("Sine 사인", "Triangle 삼각", "Square 사각")


def make_waveform(phase_cycles: np.ndarray, kind: str) -> np.ndarray:
    """위상(단위: cycle, 0~1 반복)을 받아 파형 값(-1~1)을 반환.

    phase_cycles 는 누적 위상이므로 정수부는 자동으로 주기 반복을 표현한다.
    """
    if kind.startswith("Sine"):
        return np.sin(2.0 * np.pi * phase_cycles)
    if kind.startswith("Square"):
        # sign(sin) — 0 에서 +1 로 시작
        return np.sign(np.sin(2.0 * np.pi * phase_cycles))
    if kind.startswith("Triangle"):
        # 주기 1, 범위 -1~1 삼각파 (peak at phase=0.5)
        p = phase_cycles
        return 2.0 * np.abs(2.0 * (p - np.floor(p + 0.5))) - 1.0
    raise ValueError(f"unknown waveform: {kind}")


class FunctionGeneratorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Function Generator — 펑션 제너레이터 (웅 Step 0)")

        # --- 신호 상태 ---
        self.phase = 0.0                       # 누적 위상 [cycles] — 연속성의 핵심
        self.running = False
        # 시작 전에는 중심주파수가 표시되도록 화면 버퍼를 초기화합니다.
        self.buffer = np.full(N_VISIBLE, RF_CENTER_FREQ_GHZ)
        self.tvec = np.arange(N_VISIBLE) / FS  # 시간축 [s]

        # --- Tk 변수 ---
        self.var_wave = tk.StringVar(value=WAVEFORMS[0])
        self.var_sweep_rate = tk.DoubleVar(value=2.0)
        self.var_period_ms = tk.DoubleVar(value=500.0)
        self.var_status = tk.StringVar(value="정지됨 — Run 을 누르세요")

        self._build_plot()
        self._build_controls()

    # ------------------------------------------------------------------ UI
    def _build_plot(self):
        self.fig = Figure(figsize=(8, 3.5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        (self.line,) = self.ax.plot(self.tvec, self.buffer, lw=1.6, color="#1f77b4")
        self.ax.set_xlim(0, WINDOW_SEC)
        # 세로축은 24.000~24.250 GHz 송신 주파수 범위입니다.
        self.ax.set_ylim(RF_FREQ_MIN_GHZ, RF_FREQ_MAX_GHZ)
        self.ax.set_xlabel("시간 time [s]")
        self.ax.set_ylabel("주파수 frequency [GHz]")
        self.ax.grid(True, alpha=0.3)
        self.fig.tight_layout()

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True,
                                         padx=8, pady=(8, 0))

    def _build_controls(self):
        panel = ttk.Frame(self.root, padding=8)
        panel.pack(side=tk.TOP, fill=tk.X)

        # 파형 선택
        wave_box = ttk.LabelFrame(panel, text="파형 Waveform", padding=6)
        wave_box.grid(row=0, column=0, rowspan=2, sticky="ns", padx=(0, 10))
        for w in WAVEFORMS:
            ttk.Radiobutton(wave_box, text=w, value=w,
                            variable=self.var_wave).pack(anchor="w")

        # 스윕 반복률 슬라이더 + 입력란
        freq_box = ttk.LabelFrame(panel, text="스윕 반복률 Sweep rate [Hz]", padding=6)
        freq_box.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        panel.columnconfigure(1, weight=1)
        self.freq_scale = ttk.Scale(freq_box,
                                    from_=SWEEP_RATE_MIN_HZ,
                                    to=SWEEP_RATE_MAX_HZ,
                                    variable=self.var_sweep_rate,
                                    orient=tk.HORIZONTAL,
                                    command=self._on_freq_scale)
        self.freq_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.freq_entry = ttk.Entry(freq_box, width=7)
        self.freq_entry.insert(0, f"{self.var_sweep_rate.get():.2f}")
        self.freq_entry.pack(side=tk.LEFT, padx=(8, 0))
        self.freq_entry.bind("<Return>", self._on_freq_entry)

        # 스윕 주기 슬라이더 + 입력란. 반복률과 항상 역수 관계로 동기화됩니다.
        period_box = ttk.LabelFrame(panel, text="주기 Period [ms]", padding=6)
        period_box.grid(row=1, column=1, sticky="ew", padx=(0, 10), pady=(6, 0))
        self.period_scale = ttk.Scale(
            period_box,
            from_=PERIOD_MIN_MS,
            to=PERIOD_MAX_MS,
            variable=self.var_period_ms,
            orient=tk.HORIZONTAL,
            command=self._on_period_scale,
        )
        self.period_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.period_entry = ttk.Entry(period_box, width=7)
        self.period_entry.insert(0, f"{self.var_period_ms.get():.1f}")
        self.period_entry.pack(side=tk.LEFT, padx=(8, 0))
        self.period_entry.bind("<Return>", self._on_period_entry)

        # Run / Stop 버튼
        btn_box = ttk.Frame(panel)
        btn_box.grid(row=0, column=2, rowspan=2, sticky="ns")
        self.btn_run = ttk.Button(btn_box, text="▶ Run", command=self.start)
        self.btn_run.pack(fill=tk.X, pady=2)
        self.btn_stop = ttk.Button(btn_box, text="■ Stop", command=self.stop,
                                   state=tk.DISABLED)
        self.btn_stop.pack(fill=tk.X, pady=2)

        # 상태 표시줄
        ttk.Label(self.root, textvariable=self.var_status,
                  relief=tk.SUNKEN, anchor="w", padding=4).pack(
            side=tk.BOTTOM, fill=tk.X)

    # -------------------------------------------------------------- 주파수 동기화
    def _on_freq_scale(self, _value):
        """반복률 슬라이더 이동 시 반복률 입력란과 주기를 갱신합니다."""
        sweep_rate = self.var_sweep_rate.get()
        self.freq_entry.delete(0, tk.END)
        self.freq_entry.insert(0, f"{sweep_rate:.2f}")
        self._sync_period_from_rate(sweep_rate)

    def _on_freq_entry(self, _event):
        """입력란 Enter 시 슬라이더/변수 갱신 (범위 클램프)."""
        try:
            f = float(self.freq_entry.get())
        except ValueError:
            f = self.var_sweep_rate.get()
        f = max(SWEEP_RATE_MIN_HZ, min(SWEEP_RATE_MAX_HZ, f))
        self.var_sweep_rate.set(f)
        self.freq_entry.delete(0, tk.END)
        self.freq_entry.insert(0, f"{f:.2f}")
        self._sync_period_from_rate(f)

    def _on_period_scale(self, _value):
        """주기 슬라이더 이동 시 주기 입력란과 반복률을 갱신합니다."""
        period_ms = self.var_period_ms.get()
        self.period_entry.delete(0, tk.END)
        self.period_entry.insert(0, f"{period_ms:.1f}")
        self._sync_rate_from_period(period_ms)

    def _on_period_entry(self, _event):
        """주기 입력란에서 Enter를 누르면 범위를 제한하고 반복률을 갱신합니다."""
        try:
            period_ms = float(self.period_entry.get())
        except ValueError:
            period_ms = self.var_period_ms.get()
        period_ms = max(PERIOD_MIN_MS, min(PERIOD_MAX_MS, period_ms))
        self.var_period_ms.set(period_ms)
        self.period_entry.delete(0, tk.END)
        self.period_entry.insert(0, f"{period_ms:.1f}")
        self._sync_rate_from_period(period_ms)

    def _sync_period_from_rate(self, sweep_rate):
        """스윕 반복률 [Hz]을 주기 [ms]로 변환하여 주기 UI에 반영합니다."""
        period_ms = 1000.0 / sweep_rate
        self.var_period_ms.set(period_ms)
        self.period_entry.delete(0, tk.END)
        self.period_entry.insert(0, f"{period_ms:.1f}")

    def _sync_rate_from_period(self, period_ms):
        """주기 [ms]를 스윕 반복률 [Hz]로 변환하여 반복률 UI에 반영합니다."""
        sweep_rate = 1000.0 / period_ms
        self.var_sweep_rate.set(sweep_rate)
        self.freq_entry.delete(0, tk.END)
        self.freq_entry.insert(0, f"{sweep_rate:.2f}")

    # ------------------------------------------------------------------ 실행 제어
    def start(self):
        if self.running:
            return
        self.running = True
        self.btn_run.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self._tick()

    def stop(self):
        self.running = False
        self.btn_run.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.var_status.set("정지됨 — Run 을 누르세요")

    # -------------------------------------------------------------- 애니메이션 루프
    def _tick(self):
        if not self.running:
            return

        # 이번 틱에 생성할 새 샘플 수 (실시간 흐름)
        n_new = max(1, int(round(FS * REFRESH_MS / 1000.0)))
        sweep_rate = float(self.var_sweep_rate.get())
        kind = self.var_wave.get()

        # 위상 누산기: 직전 위상에서 "이어서" 새 샘플의 누적 위상 계산.
        # 주파수가 바뀌어도 self.phase 는 연속이므로 파형이 점프하지 않는다.
        dphi = sweep_rate / FS  # 샘플당 스윕 위상 증가 [cycles]
        phases = self.phase + dphi * np.arange(1, n_new + 1)
        # 정규화 파형(-1~1)을 24.000~24.250 GHz 범위에 매핑합니다.
        sweep_wave = make_waveform(phases, kind)
        new_samples = RF_CENTER_FREQ_GHZ + RF_HALF_BAND_GHZ * sweep_wave
        self.phase = float(phases[-1] % 1.0)  # 위상 wrap (수치 누적 방지)

        # 롤링 버퍼: 왼쪽으로 시프트 후 새 샘플 추가 → 좌→우 스크롤 효과
        self.buffer = np.roll(self.buffer, -n_new)
        self.buffer[-n_new:] = new_samples

        self.line.set_ydata(self.buffer)
        self.canvas.draw_idle()

        period_ms = 1000.0 / sweep_rate if sweep_rate > 0 else float("inf")
        self.var_status.set(
            f"동작 중 ▶  스윕={kind.split()[0]}  반복률={sweep_rate:.2f} Hz  "
            f"주기={period_ms:.1f} ms  "
            f"RF={RF_FREQ_MIN_GHZ:.3f}~{RF_FREQ_MAX_GHZ:.3f} GHz  "
            f"중심={RF_CENTER_FREQ_GHZ:.3f} GHz"
        )

        self.root.after(REFRESH_MS, self._tick)


def main():
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista")  # Windows 기본 테마
    except tk.TclError:
        pass
    FunctionGeneratorApp(root)
    root.minsize(720, 460)
    root.mainloop()


if __name__ == "__main__":
    main()
