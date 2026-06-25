#!/usr/bin/env python3
"""
3D EMerge simulation result(.s4p) 기반 S-parameter 그래프 코드입니다.

중요:
    이 코드는 논문 Fig. 6을 임의로 따라 그리는 코드가 아닙니다.
    반드시 처음 만든 3D EMerge 시뮬레이션을 실행해서 나온 Touchstone .s4p 파일을 입력해야 합니다.

실행:
    python plot_hybrid_coupler_sparameters.py result.s4p

논문은 비교 기준으로만 사용합니다.
    - f0 = 1.9 GHz: PDF p.1 l011
    - S11/S41 < -20 dB 대역 1.19-2.59 GHz: PDF p.3 l033-l034
    - 1 dB power imbalance 대역 1.39-2.45 GHz: PDF p.3 l030
"""

from __future__ import annotations

# sys.argv로 Anaconda Prompt에서 입력한 .s4p 파일 경로를 받습니다.
import sys

# Path는 입력 파일 확인과 PNG 저장 경로 생성에 사용합니다.
from pathlib import Path

# numpy는 Touchstone 숫자 배열 처리와 dB 변환에 사용합니다.
import numpy as np

# matplotlib은 그래프를 그리는 라이브러리입니다.
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
    # Touchstone DB 형식의 dB 값을 linear magnitude로 바꿉니다.
    return 10 ** (np.asarray(db) / 20)


def mag_to_db(mag: np.ndarray) -> np.ndarray:
    # log10(0)을 피하기 위해 아주 작은 하한값을 둡니다.
    mag = np.maximum(np.asarray(mag), 1e-15)

    # S-parameter magnitude는 20*log10(|S|)로 dB 변환합니다.
    return 20 * np.log10(mag)


def parse_touchstone_s4p(path: Path) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    # 이 함수는 3D EMerge 시뮬레이션 결과인 4-port Touchstone .s4p 파일을 읽습니다.

    # Touchstone header의 주파수 단위를 GHz로 통일하기 위한 변환표입니다.
    unit_scale = {"HZ": 1e-9, "KHZ": 1e-6, "MHZ": 1e-3, "GHZ": 1.0}

    # header를 읽기 전 기본값은 MA(magnitude/angle)로 둡니다.
    data_format = "MA"

    # header를 읽기 전 기본 주파수 단위는 GHz라고 가정합니다.
    freq_scale = 1.0

    # 파일에서 읽은 숫자를 모두 순서대로 저장합니다.
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
                # 대소문자를 통일해 단위와 형식을 찾습니다.
                tokens = line.upper().split()

                # 예: "# GHZ S DB R 50" 같은 줄에서 GHZ와 DB를 읽습니다.
                for token in tokens:
                    if token in unit_scale:
                        freq_scale = unit_scale[token]
                    if token in {"DB", "MA", "RI"}:
                        data_format = token
                continue

            # 실제 숫자 데이터 줄을 float로 변환해서 저장합니다.
            raw_numbers.extend(float(x) for x in line.split())

    # 4-port Touchstone 한 주파수 point는 frequency 1개 + Sij 16개 * 숫자 2개입니다.
    values_per_point = 1 + 2 * 4 * 4

    # 숫자 개수가 맞지 않으면 .s4p 형식이 아니거나 포트 수가 다르다는 뜻입니다.
    if len(raw_numbers) % values_per_point != 0:
        raise ValueError("This file does not look like a valid 4-port .s4p Touchstone file.")

    # 1차원 숫자 배열을 주파수 point별 행렬로 바꿉니다.
    arr = np.asarray(raw_numbers).reshape((-1, values_per_point))

    # 첫 번째 열은 주파수입니다. header 단위를 반영해 GHz로 변환합니다.
    freq_ghz = arr[:, 0] * freq_scale

    # 나머지는 S11, S12, ..., S44의 pair 데이터입니다.
    pairs = arr[:, 1:].reshape((-1, 16, 2))

    # Touchstone DB 형식이면 첫 값이 dB, 둘째 값이 phase(deg)입니다.
    if data_format == "DB":
        s_complex = db_to_mag(pairs[:, :, 0]) * np.exp(1j * np.deg2rad(pairs[:, :, 1]))

    # Touchstone MA 형식이면 첫 값이 magnitude, 둘째 값이 phase(deg)입니다.
    elif data_format == "MA":
        s_complex = pairs[:, :, 0] * np.exp(1j * np.deg2rad(pairs[:, :, 1]))

    # Touchstone RI 형식이면 첫 값이 real, 둘째 값이 imaginary입니다.
    elif data_format == "RI":
        s_complex = pairs[:, :, 0] + 1j * pairs[:, :, 1]

    # 그 외 형식은 이 간단 parser에서 지원하지 않습니다.
    else:
        raise ValueError(f"Unsupported Touchstone format: {data_format}")

    # 일반적인 SnP 순서는 S11 S12 S13 S14 S21 S22 ... 입니다.
    s = s_complex.reshape((-1, 4, 4))

    # 3D 시뮬레이션 결과에서 논문 Fig. 6(b)에 해당하는 네 항목을 뽑습니다.
    traces = {
        # S11: P1 입력 반사입니다.
        "S11": mag_to_db(np.abs(s[:, 0, 0])),
        # S21: P1 -> P2 through 전달입니다.
        "S21": mag_to_db(np.abs(s[:, 1, 0])),
        # S31: P1 -> P3 coupled 전달입니다.
        "S31": mag_to_db(np.abs(s[:, 2, 0])),
        # S41: P1 -> P4 isolated 전달입니다.
        "S41": mag_to_db(np.abs(s[:, 3, 0])),
    }

    # 주파수와 dB trace들을 반환합니다.
    return freq_ghz, traces


def main() -> None:
    # .s4p 파일 없이 실행하면 잘못된 reference 그래프가 생기므로 중단합니다.
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage:\n"
            "    python plot_hybrid_coupler_sparameters.py result.s4p\n\n"
            "먼저 3D EMerge 시뮬레이션을 실행해서 .s4p 파일을 만든 뒤 그 파일을 넣어야 합니다."
        )

    # 사용자가 입력한 .s4p 경로입니다.
    path = Path(sys.argv[1])

    # 입력 파일 존재 여부를 확인합니다.
    if not path.exists():
        raise SystemExit(f"File not found: {path}")

    # 3D 시뮬레이션 .s4p에서 S-parameter 값을 읽습니다.
    freq_ghz, traces = parse_touchstone_s4p(path)

    # 그래프 canvas를 만듭니다.
    fig, ax = plt.subplots(figsize=(8.2, 5.0), dpi=140)

    # S11, S21, S31, S41을 각각 그립니다.
    ax.plot(freq_ghz, traces["S11"], label="S11 return", linewidth=2)
    ax.plot(freq_ghz, traces["S21"], label="S21 through", linewidth=2)
    ax.plot(freq_ghz, traces["S31"], label="S31 coupled", linewidth=2)
    ax.plot(freq_ghz, traces["S41"], label="S41 isolation", linewidth=2)

    # 논문 p.3 l033-l034의 -20 dB return/isolation 대역을 비교용으로 표시합니다.
    ax.axvspan(1.19, 2.59, color="#9ecae1", alpha=0.22, label="paper: S11/S41 < -20 dB")

    # 논문 p.3 l030의 1 dB power imbalance 대역을 비교용으로 표시합니다.
    ax.axvspan(1.39, 2.45, color="#74c476", alpha=0.18, label="paper: 1-dB imbalance")

    # 논문 중심 주파수 1.9 GHz를 표시합니다.
    ax.axvline(F0_GHZ, color="black", linestyle="--", linewidth=1.1, label="paper f0 = 1.9 GHz")

    # -20 dB 기준선을 표시합니다.
    ax.axhline(-20, color="0.35", linestyle=":", linewidth=1.2)

    # 그래프 제목과 축 이름입니다.
    ax.set_title(f"S-parameters from 3D EMerge simulation: {path.name}")
    ax.set_xlabel("Frequency (GHz)")
    ax.set_ylabel("Magnitude (dB)")

    # 논문 Fig. 6(b)와 비교하기 쉽도록 같은 주파수 범위를 기본 표시 범위로 둡니다.
    ax.set_xlim(0.5, 3.5)
    ax.set_ylim(-50, 2)

    # 읽기 쉽게 grid와 legend를 켭니다.
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()

    # PNG 파일로 저장합니다.
    out = Path(__file__).with_name("hybrid_coupler_sparameters.png")
    fig.savefig(out)
    print(f"Saved: {out}")

    # 화면에도 그래프를 띄웁니다.
    plt.show()


# 이 파일을 직접 실행했을 때만 main()을 호출합니다.
if __name__ == "__main__":
    main()
