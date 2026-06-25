#!/usr/bin/env python3
import emerge as em
import gmsh
import numpy as np

# 길이 단위 변환입니다. EMerge geometry는 meter 단위를 쓰므로,
# 논문 Fig. 5의 mm 치수를 코드에서는 mm=0.001로 변환합니다.
mm = 0.001

# 아래 주석의 "PDF p.N l.M"은 pdfplumber로 추출한 페이지별 텍스트 줄 번호입니다.
# Fig. 5 치수처럼 그림 안에만 있는 숫자는 텍스트 줄 번호가 없어서 "PDF p.3 Fig. 5"로 적었습니다.

# 기판 두께입니다. PDF p.3 l026: "상대 유전율이 10이고 두께가 1.6mm인 Taconic CER-10 기판".
th = 1.6

# 기판 유전율입니다. PDF p.3 l026: Taconic CER-10의 상대 유전율 10.
er = 10.0

# 논문 PDF에는 손실 탄젠트 값이 직접 적혀 있지 않습니다.
# Taconic CER-10에 대한 일반적인 EM 해석용 placeholder 값으로 두었으니,
# 보유한 기판 데이터시트 값이 있으면 이 값을 교체하는 것이 좋습니다.
tand = 0.0035

# 도체 두께입니다. 논문 PDF에는 금속 두께가 직접 적혀 있지 않습니다.
# 첫번째 참고 코드의 cond_t=0.017 mm 방식을 유지했습니다.
cond_t = 0.017

# 도체 전도도입니다. 논문 PDF에는 금속 전도도가 직접 적혀 있지 않습니다.
# 첫번째 참고 코드의 금 도체 설정 cond_s=4.1e7 S/m를 유지했습니다.
cond_s = 4.1e7

# 중심 주파수입니다. PDF p.1 l011: "중심 주파수 1.9GHz에서 55%의 대역폭".
F0 = 1.9e9

# 주파수 sweep 하한입니다. PDF p.3 Fig. 6의 그래프 x축이 0.5 GHz부터 시작하므로 0.5 GHz로 설정했습니다.
F_MIN = 0.5e9

# 주파수 sweep 상한입니다. PDF p.3 Fig. 6의 그래프 x축이 3.5 GHz까지 표시되므로 3.5 GHz로 설정했습니다.
F_MAX = 3.5e9

# 포트 급전선 폭입니다. PDF p.3 Fig. 5의 P1/P2 쪽 수평선 폭 callout "1.45"를 사용했습니다.
PORT_W = 1.45

# SMA/포트와 회로 사이의 급전선 여유 길이입니다.
# PDF p.3 Fig. 5에는 포트 fixture가 보이지만 이 길이 자체는 명시되지 않아,
# lumped port가 회로 edge와 바로 겹치지 않도록 둔 EMerge용 여유 파라미터입니다.
PORT_L = 5.0

# 상단/하단 수평 branch-line 한 섹션 길이입니다. PDF p.3 Fig. 5의 우측 상단 수평 callout "14.7"을 사용했습니다.
SECTION_L = 14.7

# 상단과 하단 branch-line 중심 간 세로 간격입니다. PDF p.3 Fig. 5의 우측 세로 callout "15.9"를 사용했습니다.
BRANCH_SPAN = 15.9

# 중앙 shorted parallel-coupled three-line 길이입니다. PDF p.3 Fig. 5의 하단 callout "15.0"을 사용했습니다.
COUPLED_L = 15.0

# 중앙 결합 3선의 하단 시작 offset입니다. PDF p.3 Fig. 5의 좌하단 callout "0.42"를 사용했습니다.
COUPLED_BOTTOM_OFFSET = 0.42

# 중앙 결합 3선의 상단 여유 offset입니다. PDF p.3 Fig. 5의 우하단 callout "0.48"을 사용했습니다.
COUPLED_TOP_OFFSET = 0.48

# 좌우 lambda/4 branch-line 폭입니다. PDF p.3 Fig. 5의 좌측 세로 branch callout "0.21"을 사용했습니다.
# 구조적으로는 PDF p.1 l020의 lambda/4 line(Z1, Z2) 중 물리 layout의 좁은 side branch에 해당합니다.
Z2_BRANCH_W = 0.21

# 결합 3선의 양쪽 선폭 Ws입니다. PDF p.2 l029-l030에서 B점 물리치수 (Wc, Ws)=(0.75 mm, 0.64 mm),
# PDF p.3 Fig. 5에도 side line callout "0.64"가 표시됩니다.
COUPLED_SIDE_W = 0.64

# 결합 3선의 중앙 선폭 Wc입니다. PDF p.2 l029-l030에서 B점 물리치수 (Wc, Ws)=(0.75 mm, 0.64 mm),
# PDF p.3 Fig. 5에도 center line callout "0.75"가 표시됩니다.
COUPLED_CENTER_W = 0.75

# 결합 3선 간격입니다. PDF p.2 Section II-B 본문은 공정 제약으로 gap을 최소값 100 um로 고정했다고 설명하고,
# PDF p.3 Fig. 5에도 gap callout "0.1"이 표시되어 0.10 mm로 설정했습니다.
COUPLED_GAP = 0.10

# 접지 단락 via 직경입니다. PDF p.3 l030: "비아 홀의 직경은 0.5mm".
VIA_D = 0.50

# PCB 좌우 여백입니다. 논문 치수는 금속 pattern 중심 치수 위주라서 board edge margin은 직접 제공되지 않습니다.
# EMerge에서 ground/airbox와 포트가 겹치지 않게 하기 위한 시뮬레이션 여유입니다.
EDGE_MARGIN_X = 2.0

# PCB 상하 여백입니다. 논문 치수에는 직접 제공되지 않으므로 EMerge board 생성용 여유값입니다.
EDGE_MARGIN_Y = 3.0

# airbox 높이입니다. 논문 치수가 아니라 radiation boundary가 구조와 충분히 떨어지게 둔 EM 해석용 값입니다.
HAIR = 35.0

# 자유공간 광속입니다. mesh size를 최고 주파수 파장 기준으로 잡기 위해 사용합니다.
c = 3e8

# 최고 해석 주파수 F_MAX에서 자유공간 파장을 mm로 계산합니다.
# 논문 p.3 Fig. 6의 3.5 GHz까지 sweep하는 조건에 맞춰 F_MAX를 기준으로 했습니다.
lambda_val = (c / F_MAX) * 1000

# 최대 mesh edge입니다. 논문 수치가 아니라 첫번째 참고 코드의 파장 기반 mesh 설정 방식을 따랐습니다.
MAX_EDGE = lambda_val / 4

# 최소 mesh edge입니다. 0.10 mm gap(PDF p.3 Fig. 5)을 해상하기 위해 첫번째 코드보다 촘촘하게 lambda/40로 설정했습니다.
MIN_EDGE = lambda_val / 40

# PCB dielectric mesh edge입니다. 논문 수치가 아니라 첫번째 참고 코드의 PCB boundary mesh sizing 패턴을 따른 값입니다.
PCB_EDGE_SIZE = lambda_val / 12

# 기판 재료입니다. er/th는 PDF p.3 l026의 CER-10 정보를 반영하고, 색/투명도는 display용입니다.
pcbmat = em.Material(er=er, tand=tand, color="#4d7c0f", opacity=0.7)

# 도체 재료입니다. 전도도는 논문에 직접 없어서 첫번째 참고 코드의 Gold 설정을 유지했습니다.
condmat = em.Material(cond=cond_s, name="Gold", color="#ffc107", opacity=1.0)

# airbox 재료입니다. 논문값이 아니라 흡수 경계 시각화와 해석 domain 설정용입니다.
airmat = em.Material(name="Air", color="#87ceeb", opacity=0.3)

# 시뮬레이션 이름입니다. 논문 제목의 two-section wideband 90 hybrid coupler 구조를 식별하기 위한 이름입니다.
m = em.Simulation("two_section_wideband_90_hybrid_coupler")

# PCB layouter 생성입니다. th/er는 PDF p.3 l026 근거, 나머지는 첫번째 참고 코드의 EMerge PCB API 사용 방식입니다.
layouter = em.geo.PCB(
    th,
    unit=mm,
    material=pcbmat,
    trace_material=condmat,
    trace_thickness=cond_t * mm,
    thick_traces=True,
    layers=2,
)

# 왼쪽 세로 branch x 위치입니다. PORT_L 뒤에서 시작하게 하여 P1/P3 lumped port 구간을 확보합니다.
left_x = EDGE_MARGIN_X + PORT_L

# 중앙 결합 3선 x 위치입니다. PDF p.3 Fig. 5에서 좌우 branch 사이 중간에 배치된 shorted coupled 3-line입니다.
mid_x = left_x + SECTION_L

# 오른쪽 세로 branch x 위치입니다. PDF p.3 Fig. 5의 한 섹션 길이 14.7 mm를 중앙 기준 오른쪽에도 적용합니다.
right_x = mid_x + SECTION_L

# 하단 수평선 y 위치입니다. EDGE_MARGIN_Y는 EMerge board 여유이고, 실제 branch 간격은 BRANCH_SPAN으로 정합니다.
bottom_y = EDGE_MARGIN_Y

# 상단 수평선 y 위치입니다. PDF p.3 Fig. 5의 상하 간격 15.9 mm를 bottom_y에 더했습니다.
top_y = bottom_y + BRANCH_SPAN

# 전체 수평 trace 길이입니다. 좌측 포트 여유 + 14.7 mm 섹션 2개 + 우측 포트 여유로 구성했습니다.
total_trace_l = PORT_L + 2.0 * SECTION_L + PORT_L

# 전체 구조의 시작 x 위치입니다. board edge와 trace 사이에 EDGE_MARGIN_X를 둡니다.
start_x = EDGE_MARGIN_X

# 전체 구조의 끝 x 위치입니다. 이후 board 크기 계산과 확인용 변수입니다.
end_x = start_x + total_trace_l

# PCB 폭입니다. 논문 Fig. 5의 회로 pattern을 담기 위한 EMerge board 폭으로, 좌우 여백을 포함합니다.
board_w = total_trace_l + 2.0 * EDGE_MARGIN_X

# PCB 높이입니다. PDF p.3 Fig. 5의 상하 branch 간격 15.9 mm에 상하 여백을 더했습니다.
board_h = BRANCH_SPAN + 2.0 * EDGE_MARGIN_Y

# 상단 main arm입니다. PDF p.3 Fig. 5의 포트 명칭 P1(input) -> P2(through)를 따릅니다.
layouter.new(start_x, top_y, PORT_W, (1, 0)).store("p1").straight(
    total_trace_l, PORT_W
).store("p2")

# 하단 main arm입니다. PDF p.3 Fig. 5의 포트 명칭 P3(coupled) -> P4(isolated)를 따릅니다.
layouter.new(start_x, bottom_y, PORT_W, (1, 0)).store("p3").straight(
    total_trace_l, PORT_W
).store("p4")

# 좌측 lambda/4 branch입니다. PDF p.1 l020은 Z1/Z2 lambda/4 line 경로를 설명하고,
# PDF p.3 Fig. 5의 좁은 세로선 폭 0.21 mm와 세로 길이 15.9 mm를 사용합니다.
layouter.new(left_x, bottom_y, Z2_BRANCH_W, (0, 1)).straight(
    BRANCH_SPAN, Z2_BRANCH_W
)

# 우측 lambda/4 branch입니다. 좌측 branch와 대칭 구조로, Fig. 1(a)의 2-section branch-line 형태를 구현합니다.
layouter.new(right_x, bottom_y, Z2_BRANCH_W, (0, 1)).straight(
    BRANCH_SPAN, Z2_BRANCH_W
)

# 중앙 shorted parallel-coupled three-line branch입니다.
# PDF p.1 l039는 제안 구조가 병렬 결합 3선을 쓰는 90도 하이브리드임을 설명하고,
# PDF p.2 l029-l030은 최종 B점의 물리 치수 Wc/Ws를 제시합니다.
coupled_bottom_y = bottom_y + COUPLED_BOTTOM_OFFSET

# 결합선 상단 위치입니다. PDF p.3 Fig. 5의 0.48 mm 상단 offset을 반영합니다.
coupled_top_y = top_y - COUPLED_TOP_OFFSET

# 결합선 길이입니다. PDF p.3 Fig. 5의 15.0 mm를 쓰되, 상하 arm 사이 실제 공간을 넘지 않도록 min으로 제한합니다.
coupled_l = min(COUPLED_L, coupled_top_y - coupled_bottom_y)

# 3선의 중심 간 pitch 계산입니다. Wc/2 + gap + Ws/2로,
# PDF p.2 l029-l030의 Wc=0.75 mm, Ws=0.64 mm와 PDF p.3 Fig. 5의 gap=0.1 mm를 사용합니다.
pitch_left = 0.5 * COUPLED_CENTER_W + COUPLED_GAP + 0.5 * COUPLED_SIDE_W

# 왼쪽 coupled side line 중심 x입니다. Fig. 5의 중앙 3선을 mid_x 기준으로 대칭 배치합니다.
left_coupled_x = mid_x - pitch_left

# 중앙 coupled line 중심 x입니다. PDF p.2 l029-l030의 Wc=0.75 mm 선에 해당합니다.
center_coupled_x = mid_x

# 오른쪽 coupled side line 중심 x입니다. Fig. 5의 중앙 3선을 mid_x 기준으로 대칭 배치합니다.
right_coupled_x = mid_x + pitch_left

# 결합 3선 세 가닥을 만듭니다. 순서는 side Ws, center Wc, side Ws입니다.
for x, w in (
    (left_coupled_x, COUPLED_SIDE_W),
    (center_coupled_x, COUPLED_CENTER_W),
    (right_coupled_x, COUPLED_SIDE_W),
):
    layouter.new(x, coupled_bottom_y, w, (0, 1)).straight(coupled_l, w)

# 하단 short bridge 폭입니다. PDF p.1 Fig. 1(b)와 p.3 Fig. 5는 결합 3선 하단이 short되는 구조를 보여줍니다.
short_bridge_w = 2.0 * pitch_left + COUPLED_SIDE_W

# 하단 short bridge입니다. 세 coupled line의 하단을 전기적으로 연결해 shorted coupled-line branch를 만듭니다.
layouter.new(left_coupled_x, coupled_bottom_y, short_bridge_w, (1, 0)).straight(
    2.0 * pitch_left, short_bridge_w
)

# 하단 main arm과 중앙 coupled branch를 이어주는 connector patch입니다.
# PDF p.3 Fig. 5의 실제 사진에서는 junction 불연속이 있고, PDF p.2 l027-l032는 이 불연속을 고려해 최적점을 조정했다고 설명합니다.
layouter.new(mid_x, bottom_y, COUPLED_CENTER_W, (0, 1)).straight(
    COUPLED_BOTTOM_OFFSET + 0.5 * COUPLED_CENTER_W, COUPLED_CENTER_W
)

# 상단 main arm과 중앙 coupled branch를 이어주는 connector patch입니다.
# 위 connector와 같은 이유로 junction overlap을 만들어 EMerge boolean merge가 끊기지 않도록 했습니다.
layouter.new(mid_x, coupled_top_y, COUPLED_CENTER_W, (0, 1)).straight(
    COUPLED_TOP_OFFSET + 0.5 * COUPLED_CENTER_W, COUPLED_CENTER_W
)

# trace path들을 하나의 금속 polygon으로 compile합니다. 논문값이 아니라 첫번째 참고 코드의 EMerge workflow입니다.
polies = layouter.compile_paths(merge=True)

# PCB 경계를 trace 주변으로 결정합니다. margin 값은 논문 치수가 아니라 board 생성용 여유입니다.
layouter.determine_bounds(
    leftmargin=EDGE_MARGIN_X,
    topmargin=EDGE_MARGIN_Y,
    rightmargin=EDGE_MARGIN_X,
    bottommargin=EDGE_MARGIN_Y,
)

# dielectric PCB body를 생성합니다. 첫번째 참고 코드와 같은 generate_pcb 방식입니다.
pcb = layouter.generate_pcb(True, merge=True)

# PCB x 크기입니다. board_w(mm)를 meter로 변환합니다.
PCB_X = board_w * mm

# PCB y 크기입니다. board_h(mm)를 meter로 변환합니다.
PCB_Y = board_h * mm

# airbox x 크기입니다. 논문값이 아니라 absorbing boundary가 금속과 떨어지도록 PCB보다 크게 잡았습니다.
AIRBOX_X = PCB_X * 1.6

# airbox y 크기입니다. 논문값이 아니라 absorbing boundary 여유입니다.
AIRBOX_Y = PCB_Y * 1.8

# 하부 ground plane입니다. 논문은 defected ground/multilayer 없이 단일층 구조라고 설명합니다(PDF p.1 l008-l010 요지).
ground = em.geo.Box(
    PCB_X,
    PCB_Y,
    cond_t * mm,
    position=(EDGE_MARGIN_X * mm, 0.0, -(th + cond_t) * mm),
)
ground.set_material(condmat)

# via는 PDF p.3 l030의 0.5 mm 지름을 사용합니다.
# 이 EMerge 예제 환경에서 원형 cylinder API 확인이 안 되어, 같은 외접 폭의 square plated post로 근사했습니다.
via = em.geo.Box(
    VIA_D * mm,
    VIA_D * mm,
    th * mm,
    position=((mid_x - VIA_D / 2) * mm, (coupled_bottom_y - VIA_D / 2) * mm, -th * mm),
)
via.set_material(condmat)

# airbox 시작 z입니다. substrate 아래 ground까지 포함하도록 -(th+cond_t)에서 시작합니다.
AIRBOX_Z_START = -(th + cond_t)

# airbox 높이입니다. substrate/ground 높이에 HAIR 여유를 더했습니다.
AIRBOX_HEIGHT = th + cond_t + HAIR

# absorbing boundary용 airbox입니다. 논문값이 아니라 EM 해석 domain 설정입니다.
airbox = em.geo.Box(
    AIRBOX_X,
    AIRBOX_Y,
    AIRBOX_HEIGHT * mm,
    position=(0.0, -EDGE_MARGIN_Y * mm, AIRBOX_Z_START * mm),
)
airbox.material = airmat

# P1 lumped port입니다. PDF p.3 Fig. 5의 P1(input) 위치와 이름을 따릅니다.
p1 = layouter.lumped_port(layouter.load("p1"))

# P2 lumped port입니다. PDF p.3 Fig. 5의 P2(through) 위치와 이름을 따릅니다.
p2 = layouter.lumped_port(layouter.load("p2"))

# P3 lumped port입니다. PDF p.3 Fig. 5의 P3(coupled) 위치와 이름을 따릅니다.
p3 = layouter.lumped_port(layouter.load("p3"))

# P4 lumped port입니다. PDF p.3 Fig. 5의 P4(isolated) 위치와 이름을 따릅니다.
p4 = layouter.lumped_port(layouter.load("p4"))

# geometry를 EMerge simulation에 commit합니다. 첫번째 참고 코드와 같은 workflow입니다.
m.commit_geometry()

# PDF p.3 Fig. 6의 x축 0.5-3.5 GHz를 0.05 GHz 간격으로 sweep합니다.
freq_list = list(np.arange(F_MIN, F_MAX + 0.05e9, 0.05e9))

# microwave solver frequency list를 설정합니다.
m.mw.set_frequency(freq_list)

# 금속 trace top face mesh size입니다. 0.1 mm gap을 포함한 결합선 구조를 해상하도록 MIN_EDGE를 적용합니다.
m.mesher.set_boundary_size(polies.face("+z"), MIN_EDGE * mm, growth_rate=10)

# PCB body mesh size입니다. 첫번째 참고 코드와 같은 boundary-size 설정 패턴입니다.
m.mesher.set_boundary_size(pcb, PCB_EDGE_SIZE * mm)

# gmsh global minimum mesh size입니다.
gmsh.option.setNumber("Mesh.MeshSizeMin", MIN_EDGE * mm)

# gmsh global maximum mesh size입니다.
gmsh.option.setNumber("Mesh.MeshSizeMax", MAX_EDGE * mm)

# mesh를 생성합니다.
m.generate_mesh()

# P1의 기준 임피던스입니다. 일반적인 4-port 측정/논문 S-parameter 비교는 50 ohm 기준이므로 Z0=50으로 둡니다.
port1 = m.mw.bc.LumpedPort(p1, 1, Z0=50)

# P2의 기준 임피던스입니다. P1과 같은 50 ohm measurement reference입니다.
port2 = m.mw.bc.LumpedPort(p2, 2, Z0=50)

# P3의 기준 임피던스입니다. PDF p.3 Fig. 5의 SMA 포트 측정 구조에 맞춰 50 ohm으로 둡니다.
port3 = m.mw.bc.LumpedPort(p3, 3, Z0=50)

# P4의 기준 임피던스입니다. isolated port도 같은 50 ohm 기준으로 S41 isolation을 평가합니다.
port4 = m.mw.bc.LumpedPort(p4, 4, Z0=50)

# airbox 상단 absorbing boundary입니다. 논문값이 아니라 방사 경계 조건입니다.
m.mw.bc.AbsorbingBoundary(airbox.top, order=2, abctype="B")

# airbox 좌측 absorbing boundary입니다.
m.mw.bc.AbsorbingBoundary(airbox.left, order=2, abctype="B")

# airbox 우측 absorbing boundary입니다.
m.mw.bc.AbsorbingBoundary(airbox.right, order=2, abctype="B")

# airbox front absorbing boundary입니다.
m.mw.bc.AbsorbingBoundary(airbox.front, order=2, abctype="B")

# airbox back absorbing boundary입니다.
m.mw.bc.AbsorbingBoundary(airbox.back, order=2, abctype="B")

# display에 PCB dielectric을 추가합니다.
m.display.add_object(pcb)

# display에 금속 trace polygon을 추가합니다.
m.display.add_object(polies)

# display에 ground plane을 추가합니다.
m.display.add_object(ground)

# display에 shorting via 근사체를 추가합니다.
m.display.add_object(via)

# display에 airbox를 추가합니다.
m.display.add_object(airbox)

# display에 P1 port sheet를 추가합니다.
m.display.add_object(p1)

# display에 P2 port sheet를 추가합니다.
m.display.add_object(p2)

# display에 P3 port sheet를 추가합니다.
m.display.add_object(p3)

# display에 P4 port sheet를 추가합니다.
m.display.add_object(p4)

# 구조를 화면에 표시합니다.
m.display.show()

# 실행 완료 메시지입니다.
print("Hybrid coupler EMerge structure generated with four lumped ports.")
