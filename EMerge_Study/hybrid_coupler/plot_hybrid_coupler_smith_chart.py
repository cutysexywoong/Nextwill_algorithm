#!/usr/bin/env python3
"""
3D EMerge simulation result(.s4p) 기반 Smith chart 코드입니다.

중요:
    Smith chart는 반드시 복소 반사계수 S11이 필요합니다.
    따라서 처음 만든 3D EMerge 시뮬레이션 결과 .s4p 파일에서 S11을 읽어 그립니다.
    논문 Fig. 6 이미지만으로는 정확한 Smith chart 값을 만들 수 없습니다.

실행:
    python plot_hybrid_coupler_smith_chart.py result.s4p
"""

from __future__ import annotations

# sys.argv로 Anaconda Prompt에서 입력한 .s4p 파일 경로를 받습니다.
import sys

# Path는 입력 파일 확인과 PNG 저장 경로 생성에 사용합니다.
from pathlib import Path

# numpy는 Touchstone 배열 처리, 복소수 계산, Smith grid 계산에 사용합니다.
import numpy as np

# matplotlib은 Smith chart를 그리는 데 사용합니다.
try:
    import matplotlib.pyplot as plt
except ModuleNotFoundError as exc:
    raise SystemExit(
        "matplotlib is required. In Anaconda Prompt, run:\n"
        "    conda install matplotlib"
    ) from exc


# 논문 중심 주파수입니다. PDF p.1 l011에서 1.9 GHz라고 설명합니다.
F0_GHZ = 1.9


def db_to_mag(db: np.ndarray | float) -> np.ndarray:
    # Touchstone DB 형식의 dB magnitude를 linear magnitude로 변환합니다.
    return 10 ** (np.asarray(db) / 20)


def parse_touchstone_s11(path: Path) -> tuple[np.ndarray, np.ndarray]:
    # 이 함수는 3D EMerge 시뮬레이션 결과 .s4p에서 복소 S11만 읽습니다.

    # Touchstone header의 주파수 단위를 GHz로 맞추기 위한 변환표입니다.
    unit_scale = {"HZ": 1e-9, "KHZ": 1e-6, "MHZ": 1e-3, "GHZ": 1.0}

    # header를 읽기 전 기본값은 MA(magnitude/angle)로 둡니다.
    data_format = "MA"

    # header를 읽기 전 기본 주파수 단위는 GHz로 둡니다.
    freq_scale = 1.0

    # 파일 안의 숫자를 순서대로 저장합니다.
    raw_numbers: list[float] = []

    # Touchstone 파일을 엽니다.
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        # 파일을 한 줄씩 읽습니다.
        for line in f:
            # Touchstone에서 ! 뒤쪽은 주석이므로 제거합니다.
            line = line.split("!")[0].strip()

            # 빈 줄은 건너뜁니다.
            if not line:
                continue

            # #으로 시작하는 줄은 option line입니다.
            if line.startswith("#"):
                # 대소문자를 통일합니다.
                tokens = line.upper().split()

                # 예: "# GHZ S DB R 50"에서 GHZ와 DB를 읽습니다.
                for token in tokens:
                    if token in unit_scale:
                        freq_scale = unit_scale[token]
                    if token in {"DB", "MA", "RI"}:
                        data_format = token
                continue

            # 실제 데이터 숫자를 float로 변환합니다.
            raw_numbers.extend(float(x) for x in line.split())

    # 4-port Touchstone 한 주파수 point는 frequency 1개 + Sij 16개 * 숫자 2개입니다.
    values_per_point = 1 + 2 * 4 * 4

    # 숫자 개수가 맞지 않으면 4-port .s4p 파일이 아닙니다.
    if len(raw_numbers) % values_per_point != 0:
        raise ValueError("This file does not look like a valid 4-port .s4p Touchstone file.")

    # 1차원 숫자 배열을 주파수 point별 행렬로 바꿉니다.
    arr = np.asarray(raw_numbers).reshape((-1, values_per_point))

    # 첫 번째 열은 주파수입니다. GHz로 변환합니다.
    freq_ghz = arr[:, 0] * freq_scale

    # 나머지는 S11, S12, ..., S44의 pair 데이터입니다.
    pairs = arr[:, 1:].reshape((-1, 16, 2))

    # Touchstone 일반 순서에서 첫 번째 pair가 S11입니다.
    s11_pair = pairs[:, 0, :]

    # DB 형식이면 dB magnitude와 phase(deg)를 복소 S11로 변환합니다.
    if data_format == "DB":
        s11 = db_to_mag(s11_pair[:, 0]) * np.exp(1j * np.deg2rad(s11_pair[:, 1]))

    # MA 형식이면 linear magnitude와 phase(deg)를 복소 S11로 변환합니다.
    elif data_format == "MA":
        s11 = s11_pair[:, 0] * np.exp(1j * np.deg2rad(s11_pair[:, 1]))

    # RI 형식이면 real과 imaginary를 그대로 복소수로 묶습니다.
    elif data_format == "RI":
        s11 = s11_pair[:, 0] + 1j * s11_pair[:, 1]

    # 그 외 형식은 지원하지 않습니다.
    else:
        raise ValueError(f"Unsupported Touchstone format: {data_format}")

    # 주파수와 복소 S11을 반환합니다.
    return freq_ghz, s11


def gamma_from_z(r: float, x: float) -> complex:
    # Smith chart grid용 normalized impedance z = r + jx입니다.
    z = r + 1j * x

    # normalized impedance를 reflection coefficient Gamma로 변환합니다.
    return (z - 1) / (z + 1)


def draw_smith_grid(ax: plt.Axes) -> None:
    # Smith chart 바깥 원 |Gamma| = 1을 그리기 위한 각도 배열입니다.
    theta = np.linspace(0, 2 * np.pi, 720)

    # 바깥 원을 그립니다.
    ax.plot(np.cos(theta), np.sin(theta), color="black", linewidth=1.2)

    # constant resistance circle을 그리기 위한 reactance sweep입니다.
    x_vals = np.linspace(-60, 60, 1600)

    # 자주 쓰는 normalized resistance 값을 grid로 표시합니다.
    for r in [0, 0.2, 0.5, 1, 2, 5]:
        # r은 고정하고 x만 바꿔 Gamma 좌표를 계산합니다.
        gamma = np.array([gamma_from_z(r, x) for x in x_vals])

        # Smith chart 내부만 표시합니다.
        visible = np.abs(gamma) <= 1.001

        # constant resistance circle을 그립니다.
        ax.plot(gamma.real[visible], gamma.imag[visible], color="0.78", linewidth=0.8)

    # constant reactance arc를 그리기 위한 resistance sweep입니다.
    r_vals = np.linspace(0, 20, 1200)

    # 양수/음수 reactance arc를 모두 그립니다.
    for x in [0.2, 0.5, 1, 2, 5, -0.2, -0.5, -1, -2, -5]:
        # x는 고정하고 r만 바꿔 Gamma 좌표를 계산합니다.
        gamma = np.array([gamma_from_z(r, x) for r in r_vals])

        # Smith chart 내부만 표시합니다.
        visible = np.abs(gamma) <= 1.001

        # constant reactance arc를 그립니다.
        ax.plot(gamma.real[visible], gamma.imag[visible], color="0.84", linewidth=0.8)

    # 실수축입니다.
    ax.axhline(0, color="0.55", linewidth=0.8)

    # 그래프가 원형으로 보이도록 x/y 비율을 고정합니다.
    ax.set_aspect("equal", adjustable="box")

    # Smith chart 전체가 보이도록 축 범위를 지정합니다.
    ax.set_xlim(-1.08, 1.08)
    ax.set_ylim(-1.08, 1.08)

    # 축 이름입니다.
    ax.set_xlabel("Real(Gamma)")
    ax.set_ylabel("Imag(Gamma)")

    # 직접 grid를 그렸으므로 기본 grid는 끕니다.
    ax.grid(False)


def main() -> None:
    # .s4p 파일 없이 실행하면 정확한 Smith chart 값을 만들 수 없으므로 중단합니다.
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage:\n"
            "    python plot_hybrid_coupler_smith_chart.py result.s4p\n\n"
            "Smith chart는 3D EMerge 시뮬레이션 결과 .s4p의 복소 S11 값이 필요합니다."
        )

    # 사용자가 입력한 .s4p 경로입니다.
    path = Path(sys.argv[1])

    # 입력 파일 존재 여부를 확인합니다.
    if not path.exists():
        raise SystemExit(f"File not found: {path}")

    # 3D 시뮬레이션 .s4p에서 복소 S11 값을 읽습니다.
    freq_ghz, s11 = parse_touchstone_s11(path)

    # Smith chart figure를 만듭니다.
    fig, ax = plt.subplots(figsize=(6.2, 6.2), dpi=140)

    # Smith chart grid를 먼저 그립니다.
    draw_smith_grid(ax)

    # 전체 주파수 범위의 S11 trajectory를 그립니다.
    ax.plot(s11.real, s11.imag, color="#6a51a3", linewidth=1.6, label="S11 from 3D EMerge .s4p")

    # 논문 p.3 l033-l034의 -20 dB 비교 대역 1.19-2.59 GHz를 따로 강조합니다.
    in_band = (freq_ghz >= 1.19) & (freq_ghz <= 2.59)
    ax.plot(s11.real[in_band], s11.imag[in_band], color="#238b45", linewidth=2.5, label="paper band 1.19-2.59 GHz")

    # 논문 중심 주파수 1.9 GHz와 가장 가까운 시뮬레이션 point를 찾습니다.
    idx_f0 = int(np.argmin(np.abs(freq_ghz - F0_GHZ)))

    # 중심 주파수 위치를 표시합니다.
    ax.scatter([s11.real[idx_f0]], [s11.imag[idx_f0]], color="black", s=28, zorder=4, label="paper f0 = 1.9 GHz")
    ax.annotate("1.9 GHz", (s11.real[idx_f0], s11.imag[idx_f0]), xytext=(8, 8), textcoords="offset points")

    # 제목과 범례입니다.
    ax.set_title(f"S11 Smith chart from 3D EMerge simulation: {path.name}")
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()

    # PNG 파일로 저장합니다.
    out = Path(__file__).with_name("hybrid_coupler_smith_chart.png")
    fig.savefig(out)
    print(f"Saved: {out}")

    # 화면에도 띄웁니다.
    plt.show()


# 이 파일을 직접 실행했을 때만 main()을 호출합니다.
if __name__ == "__main__":
    main()
