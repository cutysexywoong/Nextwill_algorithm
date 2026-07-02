#!/usr/bin/env python3
import emerge as em
import gmsh
import numpy as np
from pathlib import Path

def main():
    OUTPUT_DIR = Path("/scratch/home/yongmo0415/Lumped_2")
    
    mm = 0.001
    
    th = 0.4
    er = 4.0
    tand = 0.013
    cond_t = 0.017
    cond_s = 4.1e7
    
    PORT_W = 0.8012
    PORT_L = 2.0
    
    U1_W = 0.4
    U1_B = 4.568
    U1_H = 4.0
    
    U2_W = 0.8
    U2_B = 6.853
    U2_H = 5.0
    
    U3_W = 1.6
    U3_B = 10.279
    U3_H = 6.0
    
    gap_U1_U2 = 0.2
    gap_U2_U3 = 0.4
    
    CENTER_Y = 5.0 + 5.0
    
    MAX_FREQ = 50e9
    c = 3e8
    lambda_val = (c / MAX_FREQ) * 1000
    
    MAX_EDGE = lambda_val / 3
    MIN_EDGE = lambda_val / 30
    PCB_EDGE_SIZE = lambda_val / 10
    
    Hair = 18.75
    
    pcbmat = em.Material(er=er, tand=tand)
    condmat = em.Material(cond=cond_s, name="Gold")
    airmat = em.Material(name="Air")
    
    m = em.Simulation('hairpin_filter_lumped_2')
    m.check_version("2.0.0")
    
    m.set_solver(em.EMSolver.UMFPACK)
    
    layouter = em.geo.PCB(
        th, 
        unit=mm, 
        material=pcbmat, 
        trace_material=condmat,
        trace_thickness=cond_t * mm,
        thick_traces=True,
        layers=2
    )
    
    TOTAL_WIDTH = PORT_L + U1_B + gap_U1_U2 + U2_B + gap_U2_U3 + U3_B + PORT_L
    TOTAL_HEIGHT = 10.0
    
    X_MARGIN = TOTAL_WIDTH / 2
    Y_MARGIN = TOTAL_HEIGHT / 2
    
    x_margin = 1.0
    X_OFFSET = (TOTAL_WIDTH + 2 * x_margin) / 2
    
    current_x = X_OFFSET + x_margin
    
    layouter.new(current_x, CENTER_Y, PORT_W, (1,0)).store('p1').straight(PORT_L, PORT_W)
    current_x += PORT_L
    
    U1_x = current_x
    layouter.new(U1_x + U1_W/2, CENTER_Y - U1_H/2, U1_W, (0, 1)).straight(U1_H, U1_W)
    layouter.new(U1_x, CENTER_Y - U1_H/2 + U1_W/2, U1_W, (1, 0)).straight(U1_B, U1_W)
    layouter.new(U1_x + U1_B - U1_W/2, CENTER_Y - U1_H/2, U1_W, (0, 1)).straight(U1_H, U1_W)
    current_x += U1_B + gap_U1_U2
    
    U2_x = current_x
    layouter.new(U2_x + U2_W/2, CENTER_Y - U2_H/2, U2_W, (0, 1)).straight(U2_H, U2_W)
    layouter.new(U2_x, CENTER_Y + U2_H/2 - U2_W/2, U2_W, (1, 0)).straight(U2_B, U2_W)
    layouter.new(U2_x + U2_B - U2_W/2, CENTER_Y - U2_H/2, U2_W, (0, 1)).straight(U2_H, U2_W)
    current_x += U2_B + gap_U2_U3
    
    U3_x = current_x
    layouter.new(U3_x + U3_W/2, CENTER_Y - U3_H/2, U3_W, (0, 1)).straight(U3_H, U3_W)
    layouter.new(U3_x, CENTER_Y - U3_H/2 + U3_W/2, U3_W, (1, 0)).straight(U3_B, U3_W)
    layouter.new(U3_x + U3_B - U3_W/2, CENTER_Y - U3_H/2, U3_W, (0, 1)).straight(U3_H, U3_W)
    current_x += U3_B
    
    layouter.new(current_x, CENTER_Y, PORT_W, (1,0)).straight(PORT_L, PORT_W).store('p2')
    
    polies = layouter.compile_paths(merge=True)
    
    max_arm_height = max(U1_H, U2_H, U3_H)
    y_common_margin = (TOTAL_HEIGHT - max_arm_height) / 2
    y_margin_top = y_common_margin
    y_margin_bottom = y_common_margin
    
    layouter.determine_bounds(leftmargin=x_margin, topmargin=y_margin_top, rightmargin=x_margin, bottommargin=y_margin_bottom)
    
    pcb = layouter.generate_pcb(True, merge=True)
    
    PCB_X = (TOTAL_WIDTH + 2 * x_margin) * mm
    PCB_Y = TOTAL_HEIGHT * mm
    AIRBOX_X = PCB_X * 2
    AIRBOX_Y = TOTAL_HEIGHT * mm + 2 * Y_MARGIN * mm
    
    ground = em.geo.Box(
        PCB_X,
        PCB_Y,
        cond_t * mm,
        position=(X_OFFSET * mm, Y_MARGIN * mm, -(th + cond_t) * mm)
    )
    ground.set_material(condmat)
    
    AIRBOX_Z_START = -(th + cond_t)
    AIRBOX_HEIGHT = (th + cond_t) + Hair
    
    airbox = em.geo.Box(
        AIRBOX_X,
        AIRBOX_Y,
        AIRBOX_HEIGHT * mm,
        position=(0, 0, AIRBOX_Z_START * mm)
    )
    airbox.material = airmat
    
    p1 = layouter.lumped_port(layouter.load('p1'))
    p2 = layouter.lumped_port(layouter.load('p2'))
    
    m.commit_geometry()
    
    freq_list = [1e6, 10e6, 100e6] + list(np.arange(1e9, 50e9 + 1e9, 1e9))
    m.mw.set_frequency(freq_list)
    
    m.mesher.set_boundary_size(polies.face('+z'), MIN_EDGE * mm, growth_rate=10)
    m.mesher.set_boundary_size(pcb, PCB_EDGE_SIZE * mm)
    
    gmsh.option.setNumber("Mesh.MeshSizeMin", MIN_EDGE * mm)
    gmsh.option.setNumber("Mesh.MeshSizeMax", MAX_EDGE * mm)
    
    m.generate_mesh()
    
    port1 = m.mw.bc.LumpedPort(p1, 1, Z0=50)
    port2 = m.mw.bc.LumpedPort(p2, 2, Z0=50)
    
    m.mw.bc.AbsorbingBoundary(airbox.top, order=2, abctype='B')
    m.mw.bc.AbsorbingBoundary(airbox.left, order=2, abctype='B')
    m.mw.bc.AbsorbingBoundary(airbox.right, order=2, abctype='B')
    m.mw.bc.AbsorbingBoundary(airbox.front, order=2, abctype='B')
    m.mw.bc.AbsorbingBoundary(airbox.back, order=2, abctype='B')
    
    data = m.mw.run_sweep(
        parallel=True, 
        n_workers=32, 
        frequency_groups=53,
        multi_processing=True
    )
    
    grid = data.scalar.grid
    f = grid.freq
    S11 = grid.S(1, 1)
    S21 = grid.S(2, 1)
    
    S11_dB = 20 * np.log10(np.abs(S11) + 1e-12)
    S21_dB = 20 * np.log10(np.abs(S21) + 1e-12)
    
    OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
    s2p_file = OUTPUT_DIR / "hairpin_lumped_2.s2p"
    grid.export_touchstone(str(s2p_file), Z0ref=50, format="RI", funit="GHZ")
    print(f"✅ S2P 저장 완료: {s2p_file}")
    
    m.save()

if __name__ == "__main__":
    main()
