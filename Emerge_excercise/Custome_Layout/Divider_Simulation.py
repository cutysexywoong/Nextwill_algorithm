#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""3.5-GHz 3-port divider EMerge simulation.

Divider_structure.py의 동일한 형상과 실제 100-ohm LumpedElement를 사용해
0.5~7.0 GHz를 0.5-GHz 간격으로 해석하고 Touchstone S3P와 결과 그래프를 저장합니다.
"""

import argparse
import sys
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import gmsh

# 로컬 단일 프로세스 실행에서 선택적 HPC 모듈 부재로 인한 import 오류 방지
sys.modules["mpi4py"] = MagicMock()
sys.modules["mpi4py.MPI"] = MagicMock()
sys.modules["mumps_emerge"] = MagicMock()
sys.modules["mumps_emerge.interface"] = MagicMock()

import emerge as em

from Divider_gmsh import (
    MAX_EDGE,
    MAX_FREQ,
    MIN_EDGE,
    PCB_EDGE_SIZE,
    configure_divider_gmsh,
)
from Divider_structure import F0, PORT_LENGTH, build_divider_model


SIM_NAME = "divider_3p_3p5GHz"

START_FREQ_GHZ = 0.5
STOP_FREQ_GHZ = 7.0
FREQ_STEP_GHZ = 0.5


def make_frequency_list():
    """DC를 제외한 0.5~7.0 GHz의 14개 지점을 만듭니다."""
    if START_FREQ_GHZ <= 0:
        raise ValueError("EMerge microwave simulation requires frequency > 0 Hz.")

    point_count = int(round((STOP_FREQ_GHZ - START_FREQ_GHZ) / FREQ_STEP_GHZ)) + 1
    return [
        (START_FREQ_GHZ + index * FREQ_STEP_GHZ) * 1e9
        for index in range(point_count)
    ]


def save_sparameter_plot(grid, output_file: Path):
    """디바이더의 주요 S-파라미터를 dB 그래프로 저장합니다."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ModuleNotFoundError:
        print("matplotlib가 없어 PNG 그래프 저장은 건너뜁니다.")
        return

    freq_ghz = np.asarray(grid.freq) / 1e9
    epsilon = 1e-15

    traces = {
        "S11 input return": grid.S(1, 1),
        "S21 output 2": grid.S(2, 1),
        "S31 output 3": grid.S(3, 1),
        "S23 isolation": grid.S(2, 3),
        "S22 output return": grid.S(2, 2),
        "S33 output return": grid.S(3, 3),
    }

    fig, ax = plt.subplots(figsize=(10, 6), dpi=140)
    for label, values in traces.items():
        values_db = 20.0 * np.log10(np.maximum(np.abs(values), epsilon))
        ax.plot(freq_ghz, values_db, linewidth=1.7, label=label)

    ax.axvline(F0 / 1e9, color="black", linestyle="--", linewidth=1.1,
               label=f"f0 = {F0 / 1e9:g} GHz")
    ax.set_title("3-Port Divider S-Parameters")
    ax.set_xlabel("Frequency [GHz]")
    ax.set_ylabel("Magnitude [dB]")
    ax.set_xlim(START_FREQ_GHZ, STOP_FREQ_GHZ)
    ax.set_ylim(-60, 2)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(output_file)
    plt.close(fig)


def main(output_dir: Path | None = None, visualize: bool = False):
    if output_dir is None:
        output_dir = Path(__file__).resolve().parent / "Divider_Coral"

    result_dir = output_dir / "result"
    s3p_dir = result_dir / "s3p"
    png_dir = result_dir / "png"
    s3p_dir.mkdir(exist_ok=True, parents=True)
    png_dir.mkdir(exist_ok=True, parents=True)

    frequencies = make_frequency_list()

    print("Building divider geometry and mesh...")
    print(f"Frequency range: {START_FREQ_GHZ:g}~{STOP_FREQ_GHZ:g} GHz")
    print(f"Frequency step : {FREQ_STEP_GHZ:g} GHz")
    print(f"Frequency points: {len(frequencies)}")
    print(f"P1/P2/P3 port length: {PORT_LENGTH:g} mm")
    print(f"Gmsh reference frequency: {MAX_FREQ / 1e9:g} GHz")
    print(
        "Gmsh edge sizes: "
        f"min={MIN_EDGE:.3f} mm, "
        f"pcb={PCB_EDGE_SIZE:.3f} mm, "
        f"max={MAX_EDGE:.3f} mm"
    )

    # Divider_structure 형상에 Divider_gmsh의 파장 기반 메시를 적용
    model = build_divider_model(
        show_viewer=False,
        frequencies=frequencies,
        mesh_configurator=configure_divider_gmsh,
    )
    model.set_solver(em.EMSolver.PARDISO)

    if visualize:
        print("Opening Divider Gmsh Viewer...")
        gmsh.fltk.run()

    print("Starting 3-port divider simulation...")
    data = model.mw.run_sweep(
        parallel=False,
        n_workers=1,
        frequency_groups=1,
        multi_processing=False,
    )

    grid = data.scalar.grid

    s3p_file = s3p_dir / f"{SIM_NAME}.s3p"
    grid.export_touchstone(
        str(s3p_file),
        Z0ref=50,
        format="RI",
        funit="GHZ",
    )
    print(f"S3P saved: {s3p_file}")

    png_file = png_dir / f"{SIM_NAME}_sparameters.png"
    save_sparameter_plot(grid, png_file)
    if png_file.exists():
        print(f"PNG saved: {png_file}")

    model.save()
    print("Divider simulation completed.")
    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="3-port divider EMerge simulation")
    parser.add_argument("--output", type=str, default=None, help="결과 저장 폴더")
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="해석 전에 Gmsh 메시 뷰어 열기",
    )
    args = parser.parse_args()

    output_path = Path(args.output) if args.output else None
    main(output_path, args.visualize)
