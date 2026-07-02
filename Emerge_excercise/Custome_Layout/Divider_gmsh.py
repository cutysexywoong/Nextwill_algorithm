#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Divider_structure.py 형상의 Gmsh 메시 전용 뷰어."""

import argparse
import math

import gmsh

from Divider_structure import (
    F0,
    MM,
    SUBSTRATE_ER,
    build_divider_model,
)


# 디바이더 해석 상한인 5.4 GHz를 기준으로 한 파장 기반 메시 설정
MAX_FREQ = 5.4e9
SPEED_OF_LIGHT = 3e8

LAMBDA_AIR_MM = SPEED_OF_LIGHT / MAX_FREQ * 1000.0
LAMBDA_SUBSTRATE_MM = LAMBDA_AIR_MM / math.sqrt(SUBSTRATE_ER)

MAX_EDGE = LAMBDA_AIR_MM / 4.0
MIN_EDGE = LAMBDA_SUBSTRATE_MM / 15.0
PCB_EDGE_SIZE = LAMBDA_SUBSTRATE_MM / 5.0


def configure_divider_gmsh(model, traces, pcb, resistor_element):
    """디바이더 도체, PCB 및 저항 면에 Gmsh 크기를 지정합니다."""
    model.mesher.set_boundary_size(
        traces.face("+z"), MIN_EDGE * MM, growth_rate=5,
    )
    model.mesher.set_boundary_size(pcb, PCB_EDGE_SIZE * MM)
    model.mesher.set_face_size(resistor_element, MIN_EDGE * MM)

    gmsh.option.setNumber("Mesh.MeshSizeMin", MIN_EDGE * MM)
    gmsh.option.setNumber("Mesh.MeshSizeMax", MAX_EDGE * MM)

    print("Divider Gmsh settings")
    print(f"  Reference frequency: {MAX_FREQ / 1e9:g} GHz")
    print(f"  Minimum edge      : {MIN_EDGE:.3f} mm")
    print(f"  PCB edge          : {PCB_EDGE_SIZE:.3f} mm")
    print(f"  Maximum edge      : {MAX_EDGE:.3f} mm")


def main(visualize: bool = True):
    model = build_divider_model(
        show_viewer=False,
        frequencies=[F0],
        mesh_configurator=configure_divider_gmsh,
    )
    print("Gmsh mesh generated")

    if visualize:
        print("Opening Divider Gmsh Viewer...")
        gmsh.fltk.run()

    return model


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Divider Gmsh mesh viewer")
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Gmsh GUI를 열지 않고 메시만 생성",
    )
    args = parser.parse_args()
    main(visualize=not args.no_gui)
