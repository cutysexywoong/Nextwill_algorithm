"""24 GHz 대역 주파수 스윕 발생기 GUI - 교재 근거 주석판.

기준 교재:
    천인국, 『파워 유저를 위한 파이썬 EXPRESS』, 생능출판, 2020.

교재와 코드의 주요 대응:
    - 함수 정의·호출(p.207), 매개변수 전달(p.214), 변수 범위(p.238)
    - 객체지향 프로그래밍과 클래스(p.365)
    - tkinter 시작과 위젯 구성(p.409), Entry·배치 관리자(p.412)
    - 버튼 콜백과 이벤트 구동 프로그래밍(p.420)
    - 예외 처리(p.489)
    - 모듈 재사용(p.533)
    - MatPlot 직선 그래프(p.609)
    - NumPy 기초(p.614), arange 데이터 생성(p.621)
    - NumPy 배열 함수와 sin 연산(p.626), 인덱싱·슬라이싱(p.631)

주의:
    교재는 tkinter와 MatPlot을 각각 설명하지만 Matplotlib Figure를 tkinter에
    삽입하는 FigureCanvasTkAgg 방식은 직접 다루지 않는다. 이 파일에서는
    p.409의 GUI 구성과 p.609의 그래프 개념을 결합해 확장 구현했다.

실행 기능:
    - 24.000~24.250 GHz, 중심 24.125 GHz의 순간 주파수 표시
    - 사인·삼각·사각 스윕 선택
    - 스윕 반복률과 주기의 양방향 동기화
    - Run/Stop 및 연속 스크롤 그래프
"""

# [교재 p.409, p.533]
# tkinter를 모듈로 가져와 윈도우와 위젯을 구성한다. p.533의 모듈 재사용
# 원칙에 따라 GUI·수치 계산·그래프 기능을 각각 검증된 모듈에서 가져온다.
import tkinter as tk
from tkinter import ttk

# [교재 p.614, p.621, p.626]
# NumPy 배열은 반복되는 시간 샘플과 주파수 값을 한 번에 계산하는 데 사용한다.
import numpy as np

# [교재 p.609]
# MatPlot의 직선 그래프 개념을 이용해 시간(x축)-주파수(y축) 관계를 표시한다.
import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# Matplotlib 그래프의 한글과 음수 기호가 깨지지 않도록 글꼴을 지정한다.
matplotlib.rcParams["font.family"] = ["Malgun Gothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False


# -----------------------------------------------------------------------------
# 디스플레이 및 RF 스윕 상수
# -----------------------------------------------------------------------------
# [교재 p.238]
# 함수 밖에서 정의한 값은 여러 메소드가 공동으로 참조하는 전역 상수다.
# 실행 중 바뀌는 GUI 상태는 클래스의 인스턴스 변수(self.*)에 따로 저장한다.
FS = 1000.0
WINDOW_SEC = 1.0
N_VISIBLE = int(FS * WINDOW_SEC)
REFRESH_MS = 30

# 송신 RF 순간 주파수 범위와 중심주파수 [GHz]
RF_FREQ_MIN_GHZ = 24.000
RF_FREQ_MAX_GHZ = 24.250
RF_CENTER_FREQ_GHZ = 24.125
RF_HALF_BAND_GHZ = (RF_FREQ_MAX_GHZ - RF_FREQ_MIN_GHZ) / 2.0

# 스윕 반복률 [Hz]과 이에 대응하는 주기 [ms]의 설정 범위
SWEEP_RATE_MIN_HZ, SWEEP_RATE_MAX_HZ = 0.5, 50.0
PERIOD_MIN_MS = 1000.0 / SWEEP_RATE_MAX_HZ
PERIOD_MAX_MS = 1000.0 / SWEEP_RATE_MIN_HZ

# 라디오 버튼에 표시하고 파형 생성 함수에 전달할 문자열 모음
WAVEFORMS = ("Sine 사인", "Triangle 삼각", "Square 사각")


# [교재 p.207, p.214]
# 반복되는 파형 계산을 함수로 분리해 재사용하며, phase_cycles와 kind를
# 매개변수로 받아 선택된 파형의 NumPy 배열을 반환한다.
def make_waveform(phase_cycles: np.ndarray, kind: str) -> np.ndarray:
    """누적 위상 배열을 받아 -1~1 범위의 정규화 파형을 반환한다."""

    # [교재 p.116]
    # if 문으로 라디오 버튼에서 선택된 파형 종류에 따라 계산식을 분기한다.
    if kind.startswith("Sine"):
        # [교재 p.626]
        # np.sin은 배열의 모든 위상 원소에 사인 함수를 한 번에 적용한다.
        return np.sin(2.0 * np.pi * phase_cycles)

    if kind.startswith("Square"):
        # 사인값의 부호만 취해 -1 또는 +1인 사각파를 만든다.
        return np.sign(np.sin(2.0 * np.pi * phase_cycles))

    if kind.startswith("Triangle"):
        # floor와 절댓값으로 주기 1, 범위 -1~1의 삼각파를 구성한다.
        p = phase_cycles
        return 2.0 * np.abs(2.0 * (p - np.floor(p + 0.5))) - 1.0

    # 지원하지 않는 문자열이 들어오면 호출자에게 명확한 오류를 전달한다.
    raise ValueError(f"unknown waveform: {kind}")


# [교재 p.365]
# 관련 데이터(위상, 버퍼, Tk 변수)와 기능(UI 구성, 이벤트 처리)을 하나의
# 객체로 묶는 객체지향 설계를 적용한다.
class FunctionGeneratorApp:
    def __init__(self, root: tk.Tk):
        """GUI 객체의 상태를 초기화하고 그래프와 조작 패널을 구성한다."""

        self.root = root
        root.title("Function Generator — 펑션 제너레이터 (교재 주석판)")

        # 클래스 각 메소드가 공유할 실행 상태를 인스턴스 변수에 저장한다.
        self.phase = 0.0
        self.running = False

        # [교재 p.614]
        # np.full로 그래프 버퍼 전체를 중심주파수 값으로 초기화한다.
        self.buffer = np.full(N_VISIBLE, RF_CENTER_FREQ_GHZ)

        # [교재 p.621]
        # np.arange로 0부터 N_VISIBLE-1까지의 샘플 번호를 만들고 시간으로 변환한다.
        self.tvec = np.arange(N_VISIBLE) / FS

        # [교재 p.409]
        # tkinter 변수는 위젯 값과 프로그램 상태를 연결한다.
        self.var_wave = tk.StringVar(value=WAVEFORMS[0])
        self.var_sweep_rate = tk.DoubleVar(value=2.0)
        self.var_period_ms = tk.DoubleVar(value=500.0)
        self.var_status = tk.StringVar(value="정지됨 — Run 을 누르세요")

        self._build_plot()
        self._build_controls()

    # [교재 p.609 + p.409의 확장 적용]
    # p.609의 MatPlot 그래프를 p.409의 tkinter 윈도우 안에 FigureCanvasTkAgg로
    # 삽입한다. FigureCanvasTkAgg 자체는 교재 범위를 넘어선 결합 구현이다.
    def _build_plot(self):
        self.fig = Figure(figsize=(8, 3.5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        (self.line,) = self.ax.plot(
            self.tvec,
            self.buffer,
            lw=1.6,
            color="#1f77b4",
        )
        self.ax.set_xlim(0, WINDOW_SEC)
        self.ax.set_ylim(RF_FREQ_MIN_GHZ, RF_FREQ_MAX_GHZ)
        self.ax.set_xlabel("시간 time [s]")
        self.ax.set_ylabel("주파수 frequency [GHz]")
        self.ax.grid(True, alpha=0.3)
        self.fig.tight_layout()

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        # [교재 p.412]
        # pack 배치 관리자로 그래프 위젯을 윈도우 상단에 배치한다.
        self.canvas.get_tk_widget().pack(
            side=tk.TOP,
            fill=tk.BOTH,
            expand=True,
            padx=8,
            pady=(8, 0),
        )

    # [교재 p.409, p.412]
    # Frame, LabelFrame, Radiobutton, Scale, Entry, Button, Label을 만들고
    # pack/grid 배치 관리자로 조작 패널을 구성한다.
    def _build_controls(self):
        panel = ttk.Frame(self.root, padding=8)
        panel.pack(side=tk.TOP, fill=tk.X)

        wave_box = ttk.LabelFrame(panel, text="파형 Waveform", padding=6)
        wave_box.grid(row=0, column=0, rowspan=2, sticky="ns", padx=(0, 10))

        # [교재 p.156]
        # for 반복문으로 같은 형식의 라디오 버튼 세 개를 중복 없이 생성한다.
        for waveform in WAVEFORMS:
            ttk.Radiobutton(
                wave_box,
                text=waveform,
                value=waveform,
                variable=self.var_wave,
            ).pack(anchor="w")

        freq_box = ttk.LabelFrame(
            panel,
            text="스윕 반복률 Sweep rate [Hz]",
            padding=6,
        )
        freq_box.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        panel.columnconfigure(1, weight=1)

        # [교재 p.420]
        # command에 콜백 메소드를 등록하여 슬라이더 조작 이벤트를 처리한다.
        self.freq_scale = ttk.Scale(
            freq_box,
            from_=SWEEP_RATE_MIN_HZ,
            to=SWEEP_RATE_MAX_HZ,
            variable=self.var_sweep_rate,
            orient=tk.HORIZONTAL,
            command=self._on_freq_scale,
        )
        self.freq_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # [교재 p.412]
        # Entry 위젯은 사용자가 반복률을 직접 입력할 수 있게 한다.
        self.freq_entry = ttk.Entry(freq_box, width=7)
        self.freq_entry.insert(0, f"{self.var_sweep_rate.get():.2f}")
        self.freq_entry.pack(side=tk.LEFT, padx=(8, 0))

        # [교재 p.439]
        # 키보드 Return 이벤트를 입력 처리 콜백과 연결한다.
        self.freq_entry.bind("<Return>", self._on_freq_entry)

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

        btn_box = ttk.Frame(panel)
        btn_box.grid(row=0, column=2, rowspan=2, sticky="ns")

        # [교재 p.420]
        # 버튼의 command 인수에 start/stop 콜백을 등록한다.
        self.btn_run = ttk.Button(btn_box, text="▶ Run", command=self.start)
        self.btn_run.pack(fill=tk.X, pady=2)
        self.btn_stop = ttk.Button(
            btn_box,
            text="■ Stop",
            command=self.stop,
            state=tk.DISABLED,
        )
        self.btn_stop.pack(fill=tk.X, pady=2)

        ttk.Label(
            self.root,
            textvariable=self.var_status,
            relief=tk.SUNKEN,
            anchor="w",
            padding=4,
        ).pack(side=tk.BOTTOM, fill=tk.X)

    # [교재 p.420]
    # 다음 메소드들은 GUI 이벤트가 발생했을 때 호출되는 콜백 함수다.
    def _on_freq_scale(self, _value):
        """반복률 슬라이더 값으로 입력란과 주기를 갱신한다."""
        sweep_rate = self.var_sweep_rate.get()
        self.freq_entry.delete(0, tk.END)
        self.freq_entry.insert(0, f"{sweep_rate:.2f}")
        self._sync_period_from_rate(sweep_rate)

    def _on_freq_entry(self, _event):
        """반복률 입력값을 읽고 허용 범위로 제한한다."""

        # [교재 p.489]
        # 숫자가 아닌 문자열 입력으로 float 변환이 실패해도 GUI가 종료되지 않도록
        # ValueError를 처리하고 직전 정상값으로 되돌린다.
        try:
            sweep_rate = float(self.freq_entry.get())
        except ValueError:
            sweep_rate = self.var_sweep_rate.get()

        sweep_rate = max(
            SWEEP_RATE_MIN_HZ,
            min(SWEEP_RATE_MAX_HZ, sweep_rate),
        )
        self.var_sweep_rate.set(sweep_rate)
        self.freq_entry.delete(0, tk.END)
        self.freq_entry.insert(0, f"{sweep_rate:.2f}")
        self._sync_period_from_rate(sweep_rate)

    def _on_period_scale(self, _value):
        """주기 슬라이더 값으로 입력란과 반복률을 갱신한다."""
        period_ms = self.var_period_ms.get()
        self.period_entry.delete(0, tk.END)
        self.period_entry.insert(0, f"{period_ms:.1f}")
        self._sync_rate_from_period(period_ms)

    def _on_period_entry(self, _event):
        """주기 입력값을 읽고 허용 범위로 제한한다."""

        # [교재 p.489] 잘못된 사용자 입력을 예외 처리한다.
        try:
            period_ms = float(self.period_entry.get())
        except ValueError:
            period_ms = self.var_period_ms.get()

        period_ms = max(PERIOD_MIN_MS, min(PERIOD_MAX_MS, period_ms))
        self.var_period_ms.set(period_ms)
        self.period_entry.delete(0, tk.END)
        self.period_entry.insert(0, f"{period_ms:.1f}")
        self._sync_rate_from_period(period_ms)

    # [교재 p.207, p.214]
    # 동기화 계산을 작은 함수로 분리하고 필요한 값만 매개변수로 전달한다.
    def _sync_period_from_rate(self, sweep_rate):
        period_ms = 1000.0 / sweep_rate
        self.var_period_ms.set(period_ms)
        self.period_entry.delete(0, tk.END)
        self.period_entry.insert(0, f"{period_ms:.1f}")

    def _sync_rate_from_period(self, period_ms):
        sweep_rate = 1000.0 / period_ms
        self.var_sweep_rate.set(sweep_rate)
        self.freq_entry.delete(0, tk.END)
        self.freq_entry.insert(0, f"{sweep_rate:.2f}")

    # [교재 p.420]
    # 버튼 이벤트에 따라 실행 상태와 버튼 활성화 상태를 바꾼다.
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

    # [교재 p.420, p.446~448의 확장 적용]
    # 이벤트 구동 구조와 애니메이션 개념을 적용한다. root.after로 일정 시간이
    # 지난 뒤 자기 자신을 다시 예약하여 Tk 메인 루프를 막지 않고 갱신한다.
    def _tick(self):
        if not self.running:
            return

        n_new = max(1, int(round(FS * REFRESH_MS / 1000.0)))
        sweep_rate = float(self.var_sweep_rate.get())
        kind = self.var_wave.get()

        # [교재 p.621, p.626]
        # arange로 새 샘플 인덱스 배열을 만들고 NumPy 벡터 연산으로 위상을 계산한다.
        dphi = sweep_rate / FS
        phases = self.phase + dphi * np.arange(1, n_new + 1)
        sweep_wave = make_waveform(phases, kind)

        # -1~1 파형을 중심 24.125 GHz, 범위 24.000~24.250 GHz로 선형 변환한다.
        new_samples = RF_CENTER_FREQ_GHZ + RF_HALF_BAND_GHZ * sweep_wave
        self.phase = float(phases[-1] % 1.0)

        # [교재 p.631]
        # 배열의 마지막 n_new 구간을 슬라이싱하여 새 주파수 샘플을 넣는다.
        # np.roll은 기존 데이터를 왼쪽으로 이동시켜 스크롤 효과를 만든다.
        self.buffer = np.roll(self.buffer, -n_new)
        self.buffer[-n_new:] = new_samples

        # [교재 p.609]
        # 계산된 y축 데이터만 교체하고 Matplotlib 캔버스를 다시 그린다.
        self.line.set_ydata(self.buffer)
        self.canvas.draw_idle()

        period_ms = 1000.0 / sweep_rate
        self.var_status.set(
            f"동작 중 ▶  스윕={kind.split()[0]}  반복률={sweep_rate:.2f} Hz  "
            f"주기={period_ms:.1f} ms  "
            f"RF={RF_FREQ_MIN_GHZ:.3f}~{RF_FREQ_MAX_GHZ:.3f} GHz  "
            f"중심={RF_CENTER_FREQ_GHZ:.3f} GHz"
        )

        self.root.after(REFRESH_MS, self._tick)


# [교재 p.207]
# 프로그램 시작 절차를 main 함수로 분리하여 재사용 가능한 코드와 실행 코드를
# 구분한다.
def main():
    # [교재 p.409]
    # 최상위 Tk 윈도우를 만든 뒤 애플리케이션 객체를 연결한다.
    root = tk.Tk()

    # [교재 p.489]
    # vista 테마가 없는 환경에서도 기본 테마로 계속 실행되도록 예외 처리한다.
    try:
        ttk.Style().theme_use("vista")
    except tk.TclError:
        pass

    FunctionGeneratorApp(root)
    root.minsize(720, 460)

    # [교재 p.409]
    # mainloop가 키보드·마우스·버튼·타이머 이벤트를 계속 기다리고 처리한다.
    root.mainloop()


# 파일을 직접 실행한 경우에만 GUI를 시작하고, 모듈로 import하면 시작하지 않는다.
if __name__ == "__main__":
    main()
