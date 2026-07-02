#!/usr/bin/env python3
import emerge as em
import gmsh
import numpy as np

mm = 0.001

th = 0.4
er = 4.0
tand = 0.013
cond_t = 0.017
cond_s = 4.1e7

PORT_W = 0.8012
ORIG_PORT_L = 2.0
PORT_L = 2.0
L_W, C_W = 0.238, 2.914

L1, L3, L5, L7, L9, L11, L13 = 1.203, 2.121, 2.229, 2.248, 2.229, 2.121, 1.203
C2, C4, C6, C8, C10, C12 = 1.434, 1.511, 1.527, 1.527, 1.511, 1.434

CENTER_Y = 5.0

MAX_FREQ = 50e9
c = 3e8
lambda_val = (c / MAX_FREQ) * 1000
MAX_EDGE = lambda_val / 3    
MIN_EDGE = lambda_val / 30
PCB_EDGE_SIZE = lambda_val / 10

Hair = 18.75

pcbmat = em.Material(er=er, tand=tand, color='#4d7c0f', opacity=0.7)
condmat = em.Material(cond=cond_s, name="Gold", color='#ffc107', opacity=1.0)

m = em.Simulation('chebyshev_lpf_pyvista')

layouter = em.geo.PCB(
    th, 
    unit=mm, 
    material=pcbmat, 
    trace_material=condmat,
    trace_thickness=cond_t * mm,
    thick_traces=True,
    layers=2
)

START_X_OFFSET = 1.0

layouter.new(START_X_OFFSET, CENTER_Y, PORT_W, (1,0)).store('p1')\
    .straight(PORT_L, PORT_W)\
    .straight(L1, L_W).straight(C2, C_W)\
    .straight(L3, L_W).straight(C4, C_W)\
    .straight(L5, L_W).straight(C6, C_W)\
    .straight(L7, L_W)\
    .straight(C8, C_W).straight(L9, L_W)\
    .straight(C10, C_W).straight(L11, L_W)\
    .straight(C12, C_W).straight(L13, L_W)\
    .straight(PORT_L, PORT_W).store('p2')

traces = layouter.compile_paths(merge=True)

TOTAL_WIDTH = ORIG_PORT_L + L1 + C2 + L3 + C4 + L5 + C6 + L7 + C8 + L9 + C10 + L11 + C12 + L13 + ORIG_PORT_L
TOTAL_HEIGHT = 10.0

x_margin = 1.0
trace_y_top = CENTER_Y + C_W / 2
trace_y_bottom = CENTER_Y - C_W / 2
y_margin_top = TOTAL_HEIGHT - trace_y_top
y_margin_bottom = trace_y_bottom - 0

layouter.determine_bounds(leftmargin=x_margin, topmargin=y_margin_top, rightmargin=x_margin, bottommargin=y_margin_bottom)

substrate = layouter.generate_pcb(split_z=False, merge=True)

pcb_x = (TOTAL_WIDTH + 2 * x_margin) * mm
pcb_y = TOTAL_HEIGHT * mm

ground = em.geo.Box(
    pcb_x,
    pcb_y,
    cond_t * mm,
    position=(0, 0, -(th + cond_t) * mm)
)
ground.set_material(condmat)

AIRBOX_Z_START = -(th + cond_t)
AIRBOX_HEIGHT = (th + cond_t) + Hair

air = em.geo.Box(
    pcb_x,
    pcb_y,
    AIRBOX_HEIGHT * mm,
    position=(0, 0, AIRBOX_Z_START * mm)
)
air.material = em.Material(name="Air", color='#87ceeb', opacity=0.3)

p1 = layouter.lumped_port(layouter.load('p1'))
p2 = layouter.lumped_port(layouter.load('p2'))

m.commit_geometry()

freq_list = [1e6, 10e6, 100e6] + list(np.arange(1e9, 50e9 + 1e9, 1e9))
m.mw.set_frequency(freq_list)

m.mesher.set_boundary_size(traces.face('+z'), MIN_EDGE * mm, growth_rate=1.5)

m.mesher.set_boundary_size(substrate, PCB_EDGE_SIZE * mm)

gmsh.option.setNumber("Mesh.MeshSizeMin", MIN_EDGE * mm)
gmsh.option.setNumber("Mesh.MeshSizeMax", MAX_EDGE * mm)

m.generate_mesh()

port1 = m.mw.bc.LumpedPort(p1, 1, Z0=50)
port2 = m.mw.bc.LumpedPort(p2, 2, Z0=50)

m.mw.bc.AbsorbingBoundary(air.top, order=2, abctype='B')
m.mw.bc.AbsorbingBoundary(air.left, order=2, abctype='B')
m.mw.bc.AbsorbingBoundary(air.right, order=2, abctype='B')
m.mw.bc.AbsorbingBoundary(air.front, order=2, abctype='B')
m.mw.bc.AbsorbingBoundary(air.back, order=2, abctype='B')

m.display._plot.add_mesh(m.display.mesh(substrate), color='#4d7c0f', opacity=0.7, show_edges=True)

m.display._plot.add_mesh(m.display.mesh(traces), color='#ffc107', opacity=1.0, show_edges=True)

m.display._plot.add_mesh(m.display.mesh(ground), color='#ffc107', opacity=1.0, show_edges=True)

m.display._plot.add_mesh(m.display.mesh(air), color='#87ceeb', opacity=0.3, show_edges=True)


m.display.show()

print("✅ PyVista 시각화 종료")
