#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""3.5 GHz, 3-port transmission-line divider Structure Viewer.

회로도에 표시된 전기적 길이를 2D 마이크로스트립 길이로 변환합니다.
    TL1: 70.71 ohm, 135 deg
    TL2: 70.71 ohm,  90 deg
    TL3: 70.71 ohm,  45 deg
    R1 : 100 ohm (출력 사이 격리 저항)
"""

import math

import emerge as em
import gmsh


# -----------------------------------------------------------------------------
# 회로 및 기판 조건
# -----------------------------------------------------------------------------
MM = 0.001
F0 = 3.5e9
PORT_Z0 = 50.0
BRANCH_Z0 = 70.71
ISOLATION_R = 100.0

SUBSTRATE_H = 0.508     # mm
SUBSTRATE_ER = 3.48
SUBSTRATE_TAND = 0.013
COPPER_T = 0.017        # mm
COPPER_COND = 4.1e7     # S/m

BOARD_MARGIN = 1.0      # mm
AIR_MARGIN = 5.0        # mm
AIR_HEIGHT = 10.0       # mm
PORT_LENGTH = 2.0      # mm, P1/P2/P3 피드 길이
TRACE_WIDTH = 0.608     # mm, 포트 및 모든 선로 폭
TL3_LINE_LENGTH = 6.64  # mm, 저항 아래쪽 선로 길이
RESISTOR_LENGTH = 1.0   # mm, 레이아웃에서 저항이 차지하는 수직 간격
RESISTOR_WIDTH = 0.5    # mm


def isolation_resistance(_frequency):
    """모델 저장이 가능하도록 모듈 수준에서 격리 저항값을 반환합니다."""
    return ISOLATION_R


def microstrip_parameters(width: float, height: float, er: float):
    """간단한 Hammerstad 근사식으로 Z0와 유효 유전율을 계산합니다."""
    u = width / height
    correction = 0.04 * (1.0 - u) ** 2 if u < 1.0 else 0.0
    er_eff = (er + 1.0) / 2.0 + (er - 1.0) / 2.0 * (
        1.0 / math.sqrt(1.0 + 12.0 / u) + correction
    )

    if u <= 1.0:
        z0 = 60.0 / math.sqrt(er_eff) * math.log(8.0 / u + u / 4.0)
    else:
        z0 = 120.0 * math.pi / (
            math.sqrt(er_eff)
            * (u + 1.393 + 0.667 * math.log(u + 1.444))
        )

    return z0, er_eff


def width_for_impedance(target_z0: float, height: float, er: float) -> float:
    """목표 임피던스가 나오는 마이크로스트립 폭을 이분법으로 찾습니다."""
    low = 0.02 * height
    high = 20.0 * height

    for _ in range(80):
        width = (low + high) / 2.0
        z0, _ = microstrip_parameters(width, height, er)
        if z0 > target_z0:
            low = width
        else:
            high = width

    return (low + high) / 2.0


def add_rectangle(layouter, x0, y0, x1, y1):
    """PCB 상면에 축과 나란한 직사각형 도체를 추가합니다."""
    layouter.add_poly([x0, x1, x1, x0], [y0, y0, y1, y1])


def add_horizontal(layouter, x0, x1, y, width):
    add_rectangle(layouter, min(x0, x1), y - width / 2.0,
                  max(x0, x1), y + width / 2.0)


def add_vertical(layouter, x, y0, y1, width):
    add_rectangle(layouter, x - width / 2.0, min(y0, y1),
                  x + width / 2.0, max(y0, y1))


def add_joint(layouter, x, y, width):
    """직각 선로가 만나는 곳의 작은 빈틈을 사각 패드로 채웁니다."""
    add_rectangle(layouter, x - width / 2.0, y - width / 2.0,
                  x + width / 2.0, y + width / 2.0)


def add_mitered_corner(layouter, x, y, width, outer_quadrant):
    """90도 코너의 바깥쪽을 45도 대각선으로 연결한 MBEND 형상을 만듭니다."""
    half = width / 2.0
    triangle_points = {
        "NW": [(x - half, y), (x, y), (x, y + half)],
        "NE": [(x, y + half), (x, y), (x + half, y)],
        "SW": [(x - half, y), (x, y), (x, y - half)],
        "SE": [(x, y - half), (x, y), (x + half, y)],
    }

    try:
        points = triangle_points[outer_quadrant]
    except KeyError as exc:
        raise ValueError(f"지원하지 않는 코너 방향: {outer_quadrant}") from exc

    layouter.add_poly(
        [point[0] for point in points],
        [point[1] for point in points],
    )


def build_divider_model(
    show_viewer: bool = True,
    frequencies=None,
    mesh_configurator=None,
):
    # 요청한 포트/선로 폭을 직접 사용하고 중심주파수의 유도 파장을 계산
    trace_w = TRACE_WIDTH
    estimated_z0, er_eff = microstrip_parameters(trace_w, SUBSTRATE_H, SUBSTRATE_ER)
    guided_wavelength = 3e8 / (F0 * math.sqrt(er_eff)) / MM  # mm

    length_135 = guided_wavelength * 135.0 / 360.0
    length_90 = guided_wavelength * 90.0 / 360.0
    length_45 = TL3_LINE_LENGTH

    # 그림과 같은 배치가 되면서 각 중심선 길이가 전기적 길이와 같도록 계산
    # 오른쪽: 선로 6.64 mm + 저항 1 mm = 7.64 mm
    # 그 반대쪽 세로 구간도 같은 7.64 mm로 만들어 대칭을 유지
    symmetric_side_length = TL3_LINE_LENGTH + RESISTOR_LENGTH
    vertical_drop_90 = symmetric_side_length
    horizontal_run = length_90 - vertical_drop_90
    upper_rise = (length_135 - horizontal_run) / 2.0

    # 세 포트가 각각 정확히 2 mm가 되도록 접합점과 기판 크기를 배치
    input_x = BOARD_MARGIN + PORT_LENGTH
    lower_y = BOARD_MARGIN + PORT_LENGTH
    input_y = lower_y + vertical_drop_90
    right_x = input_x + horizontal_run
    top_y = input_y + upper_rise
    resistor_bottom_y = lower_y + length_45

    if horizontal_run <= 0:
        raise ValueError("계산된 수평 선로 길이가 0 이하입니다.")

    input_port_x = input_x - PORT_LENGTH
    output2_port_x = right_x + PORT_LENGTH
    output3_port_y = lower_y - PORT_LENGTH
    board_x = output2_port_x + BOARD_MARGIN
    board_y = top_y + trace_w / 2.0 + BOARD_MARGIN

    print("3-port Divider Layout")
    print(f"  Center frequency : {F0 / 1e9:.3f} GHz")
    print(f"  Branch impedance : {BRANCH_Z0:.2f} ohm")
    print(f"  Isolation resistor: {ISOLATION_R:.1f} ohm")
    print(f"  Port/trace width : {trace_w:.3f} mm")
    print(f"  Estimated Z0     : {estimated_z0:.2f} ohm")
    print(f"  Resistor size    : {RESISTOR_WIDTH:.3f} x {RESISTOR_LENGTH:.3f} mm")
    print(f"  Symmetric height : {symmetric_side_length:.3f} mm")
    print(f"  P1/P2/P3 length : {PORT_LENGTH:.3f} mm")
    print(f"  Effective er     : {er_eff:.3f}")
    print(f"  Guided wavelength: {guided_wavelength:.3f} mm")
    print(f"  TL1 / TL2 / TL3 : {length_135:.3f} / {length_90:.3f} / {length_45:.3f} mm")

    pcb_material = em.Material(
        er=SUBSTRATE_ER, tand=SUBSTRATE_TAND,
        color="#4d7c0f", opacity=0.65,
    )
    copper_material = em.Material(
        cond=COPPER_COND, name="Copper",
        color="#c8b85b", opacity=1.0,
    )
    air_material = em.Material(name="Air", color="#87ceeb", opacity=0.08)

    model = em.Simulation(
        "divider_3p_3p5GHz_structure",
        store_system="msgpack",
    )
    model.check_version("2.7.4")

    layouter = em.geo.PCBNew(
        SUBSTRATE_H,
        unit=MM,
        material=pcb_material,
        trace_material=copper_material,
        trace_thickness=COPPER_T * MM,
        thick_traces=True,
        layers=2,
    )

    # 포트 피드 선로: 좌측 P1, 우측 P2, 아래쪽 P3
    add_horizontal(layouter, input_port_x, input_x, input_y, trace_w)
    add_horizontal(layouter, right_x, output2_port_x, input_y, trace_w)
    add_vertical(layouter, right_x, output3_port_y, lower_y, trace_w)

    # TL1 = 135 deg: 위쪽 U자 경로
    add_vertical(layouter, input_x, input_y, top_y, trace_w)
    add_horizontal(layouter, input_x, right_x, top_y, trace_w)
    add_vertical(layouter, right_x, input_y, top_y, trace_w)

    # TL2 = 90 deg: 아래쪽 L자 경로
    add_vertical(layouter, input_x, lower_y, input_y, trace_w)
    add_horizontal(layouter, input_x, right_x, lower_y, trace_w)

    # TL3 = 45 deg: P3 노드에서 저항 아래쪽까지의 수직 경로
    add_vertical(layouter, right_x, lower_y, resistor_bottom_y, trace_w)

    # 분기 접합부는 사각 패드로 채워 하나의 연속된 도체 패턴으로 만듦
    for x, y in [
        (input_x, input_y), (right_x, input_y), (right_x, lower_y),
    ]:
        add_joint(layouter, x, y, trace_w)

    # TL1의 위쪽 두 코너와 TL2의 아래쪽 한 코너를 MBEND처럼 45도로 깎음
    add_mitered_corner(layouter, input_x, top_y, trace_w, "NW")
    add_mitered_corner(layouter, right_x, top_y, trace_w, "NE")
    add_mitered_corner(layouter, input_x, lower_y, trace_w, "SW")

    # 먼저 실제 구리 선로만 병합합니다.
    traces = layouter.compile_paths(merge=True)

    # LumpedElement 생성 후에는 빈 후속 경로가 생기므로 compile_paths를 다시
    # 호출하지 않습니다. 두 구리 단자 사이에는 실제 100-ohm 경계면이 생성됩니다.
    layouter.new(
        right_x, resistor_bottom_y, RESISTOR_WIDTH, (0, 1)
    ).lumped_element(
        isolation_resistance,
        (RESISTOR_LENGTH, RESISTOR_WIDTH),
    )
    resistor_element = layouter.lumped_elements[-1]

    # 포트 면의 위치와 바깥쪽 방향
    layouter.new(input_port_x, input_y, trace_w, (-1, 0)).store("p1")
    layouter.new(output2_port_x, input_y, trace_w, (1, 0)).store("p2")
    layouter.new(right_x, output3_port_y, trace_w, (0, -1)).store("p3")

    layouter.determine_bounds(
        leftmargin=input_port_x,
        rightmargin=board_x - output2_port_x,
        bottommargin=output3_port_y,
        topmargin=board_y - (top_y + trace_w / 2.0),
    )
    pcb = layouter.generate_pcb(True, merge=True)

    ground = em.geo.Box(
        board_x * MM, board_y * MM, COPPER_T * MM,
        position=(0, 0, -(SUBSTRATE_H + COPPER_T) * MM),
    )
    ground.set_material(copper_material)

    airbox = em.geo.Box(
        (board_x + 2 * AIR_MARGIN) * MM,
        (board_y + 2 * AIR_MARGIN) * MM,
        (SUBSTRATE_H + COPPER_T + AIR_HEIGHT) * MM,
        position=(-AIR_MARGIN * MM, -AIR_MARGIN * MM,
                  -(SUBSTRATE_H + COPPER_T) * MM),
    )
    airbox.material = air_material

    p1 = layouter.lumped_port(layouter.load("p1"))
    p2 = layouter.lumped_port(layouter.load("p2"))
    p3 = layouter.lumped_port(layouter.load("p3"))

    model.commit_geometry()
    model.mw.set_frequency([F0] if frequencies is None else frequencies)

    if mesh_configurator is None:
        # 기본 Structure/Simulation용 메시 설정
        model.mesher.set_boundary_size(
            traces.face("+z"), 0.2 * MM, growth_rate=3,
        )
        model.mesher.set_boundary_size(pcb, 1.5 * MM)
        model.mesher.set_face_size(resistor_element, 0.1 * MM)
        gmsh.option.setNumber("Mesh.MeshSizeMin", 0.1 * MM)
        gmsh.option.setNumber("Mesh.MeshSizeMax", 3.0 * MM)
    else:
        mesh_configurator(model, traces, pcb, resistor_element)

    model.generate_mesh()

    # 50-ohm 기준의 3개 입출력 포트
    model.mw.bc.LumpedPort(p1, 1, Z0=PORT_Z0)
    model.mw.bc.LumpedPort(p2, 2, Z0=PORT_Z0)
    model.mw.bc.LumpedPort(p3, 3, Z0=PORT_Z0)
    model.mw.bc.LumpedElement(resistor_element)
    print(f"Applied ideal lumped resistor: {ISOLATION_R:.1f} ohm")

    model.display.add_object(pcb)
    model.display.add_object(traces)
    model.display.add_object(ground)
    model.display.add_object(airbox)
    model.display.add_object(resistor_element)
    model.display.add_object(p1)
    model.display.add_object(p2)
    model.display.add_object(p3)

    if show_viewer:
        print("Opening divider Structure Viewer...")
        model.display.show()

    return model


if __name__ == "__main__":
    build_divider_model(show_viewer=True)
