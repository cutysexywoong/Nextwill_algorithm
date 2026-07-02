"""레이더 위치에서 타깃을 바라보는 1인칭 시야 GUI (v2).

좌표계:
    X: 레이더 기준 좌우 거리 [m]
    Y: 레이더 정면 거리 [m]
    Z: 지면 기준 드론 고도 [m]

화면 좌표:
    가로축: 수평각 [-50, 50] deg
    세로축: 수직각 [0, 10] deg, 중심 2 deg
"""

import math
import tkinter as tk
from tkinter import messagebox, ttk

import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.patches import Circle, Ellipse, Polygon, Rectangle


matplotlib.rcParams["font.family"] = ["Malgun Gothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

HORIZONTAL_MIN_DEG = -50.0
HORIZONTAL_MAX_DEG = 50.0
VERTICAL_MIN_DEG = 0.0
VERTICAL_MAX_DEG = 10.0
ELEVATION_CENTER_DEG = 2.0
RADAR_HEIGHT_M = 2.0
MIN_RANGE_M = 1.0
MAX_RANGE_M = 5000.0
DRONE_MIN_ALTITUDE_M = 5.0
DRONE_MAX_ALTITUDE_M = 300.0


class RadarFirstPersonApp:
    """레이더 시점의 각도 화면에 한 개의 드론 타깃을 표시합니다."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Radar First-Person Target View v2")

        self.var_coordinate = tk.StringVar(value="(0, 1000, 37)")
        self.var_horizontal = tk.DoubleVar(value=0.0)
        self.var_vertical = tk.DoubleVar(value=2.0)
        self.var_status = tk.StringVar(
            value="(x, y, z) 좌표를 입력한 뒤 Target Plot을 누르세요."
        )

        self._build_view()
        self._build_controls()
        self.plot_target()

    def _build_view(self):
        """레이더의 정면 시야를 나타내는 Matplotlib 화면을 만듭니다."""
        self.figure = Figure(figsize=(9, 5.8), dpi=100, facecolor="#071521")
        self.ax = self.figure.add_subplot(111)
        self.figure.subplots_adjust(left=0.09, right=0.97, bottom=0.11, top=0.90)

        self.canvas = FigureCanvasTkAgg(self.figure, master=self.root)
        self.canvas.get_tk_widget().pack(
            side=tk.TOP,
            fill=tk.BOTH,
            expand=True,
            padx=10,
            pady=(10, 4),
        )

    def _build_controls(self):
        coordinate_panel = ttk.LabelFrame(
            self.root,
            text="Target coordinate [m] - (x, y, altitude)",
            padding=8,
        )
        coordinate_panel.pack(side=tk.TOP, fill=tk.X, padx=10, pady=4)

        ttk.Label(coordinate_panel, text="좌표 (x, y, z)").pack(
            side=tk.LEFT,
            padx=(4, 8),
        )
        self.coordinate_entry = ttk.Entry(
            coordinate_panel,
            textvariable=self.var_coordinate,
            width=28,
            font=("Consolas", 11),
        )
        self.coordinate_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self.coordinate_entry.bind("<Return>", self.plot_target)

        ttk.Button(
            coordinate_panel,
            text="● Target Plot",
            command=self.plot_target,
        ).pack(side=tk.LEFT, padx=(10, 4))
        ttk.Button(
            coordinate_panel,
            text="Clear",
            command=self.clear_view,
        ).pack(side=tk.LEFT, padx=4)

        angle_panel = ttk.LabelFrame(
            self.root,
            text="Radar line of sight",
            padding=8,
        )
        angle_panel.pack(side=tk.TOP, fill=tk.X, padx=10, pady=4)
        angle_panel.columnconfigure(1, weight=1)

        ttk.Label(angle_panel, text="수평각 [-50°~50°]").grid(
            row=0,
            column=0,
            padx=5,
        )
        ttk.Scale(
            angle_panel,
            from_=HORIZONTAL_MIN_DEG,
            to=HORIZONTAL_MAX_DEG,
            variable=self.var_horizontal,
            command=self._on_angle_change,
        ).grid(row=0, column=1, sticky="ew", padx=5)
        self.horizontal_value = ttk.Label(angle_panel, width=10)
        self.horizontal_value.grid(row=0, column=2, padx=5)

        ttk.Label(angle_panel, text="수직각 [0°~10°], 중심 2°").grid(
            row=1,
            column=0,
            padx=5,
        )
        ttk.Scale(
            angle_panel,
            from_=VERTICAL_MIN_DEG,
            to=VERTICAL_MAX_DEG,
            variable=self.var_vertical,
            command=self._on_angle_change,
        ).grid(row=1, column=1, sticky="ew", padx=5)
        self.vertical_value = ttk.Label(angle_panel, width=10)
        self.vertical_value.grid(row=1, column=2, padx=5)

        ttk.Label(
            self.root,
            textvariable=self.var_status,
            relief=tk.SUNKEN,
            anchor="w",
            padding=6,
        ).pack(side=tk.BOTTOM, fill=tk.X)

    def _read_coordinate(self):
        """입력란의 '(x, y, z)' 문자열을 검사하여 실수 좌표로 반환합니다."""
        text = self.var_coordinate.get().strip()
        if text.startswith("(") and text.endswith(")"):
            text = text[1:-1].strip()

        parts = [part.strip() for part in text.split(",")]
        if len(parts) != 3:
            raise ValueError("좌표를 (x, y, z) 형식으로 입력하세요.")

        try:
            x, y, z = (float(part) for part in parts)
        except ValueError as error:
            raise ValueError("x, y, z에는 숫자를 입력해야 합니다.") from error

        if not all(math.isfinite(value) for value in (x, y, z)):
            raise ValueError("x, y, z에는 유한한 숫자를 입력해야 합니다.")

        if y < 0:
            raise ValueError("레이더 정면거리 y는 0 이상의 값이어야 합니다.")
        if not DRONE_MIN_ALTITUDE_M <= z <= DRONE_MAX_ALTITUDE_M:
            raise ValueError("드론 고도는 5~300 m 범위여야 합니다.")

        horizontal_distance = math.hypot(x, y)
        relative_height = z - RADAR_HEIGHT_M
        distance = math.sqrt(x * x + y * y + relative_height * relative_height)
        if not MIN_RANGE_M <= distance <= MAX_RANGE_M:
            raise ValueError("레이더와 타깃의 직선거리는 1~5000 m 범위여야 합니다.")

        horizontal_deg = math.degrees(math.atan2(x, y))
        vertical_deg = math.degrees(math.atan2(relative_height, horizontal_distance))

        if not HORIZONTAL_MIN_DEG <= horizontal_deg <= HORIZONTAL_MAX_DEG:
            raise ValueError("타깃 수평각은 -50°~50° 범위여야 합니다.")
        if not VERTICAL_MIN_DEG <= vertical_deg <= VERTICAL_MAX_DEG:
            raise ValueError("타깃 수직각은 0°~10° 범위여야 합니다.")

        return x, y, z, distance, horizontal_deg, vertical_deg

    def _on_angle_change(self, _value=None):
        """슬라이더 각도를 현재 거리 좌표에 적용하고 화면을 갱신합니다."""
        try:
            _, _, _, distance, current_horizontal, current_vertical = (
                self._read_coordinate()
            )
        except ValueError:
            return

        horizontal_deg = float(self.var_horizontal.get())
        vertical_deg = float(self.var_vertical.get())
        horizontal_rad = math.radians(horizontal_deg)
        vertical_rad = math.radians(vertical_deg)

        horizontal_distance = distance * math.cos(vertical_rad)
        x = horizontal_distance * math.sin(horizontal_rad)
        y = horizontal_distance * math.cos(horizontal_rad)
        z = RADAR_HEIGHT_M + distance * math.sin(vertical_rad)

        # 고도 제한을 벗어나는 각도는 적용하지 않고 기존 타깃 각도로 되돌립니다.
        if not DRONE_MIN_ALTITUDE_M <= z <= DRONE_MAX_ALTITUDE_M:
            self.var_horizontal.set(current_horizontal)
            self.var_vertical.set(current_vertical)
            self.var_status.set("설정한 각도에서는 드론 고도 5~300 m 조건을 벗어납니다.")
            return

        self.var_coordinate.set(f"({x:.4f}, {y:.4f}, {z:.4f})")
        self.plot_target(show_error=False)

    def _format_hud(self):
        """레이더 1인칭 화면의 고정 시야각과 HUD 스타일을 적용합니다."""
        self.ax.set_facecolor("#071521")
        self.ax.set_xlim(HORIZONTAL_MIN_DEG, HORIZONTAL_MAX_DEG)
        self.ax.set_ylim(VERTICAL_MIN_DEG, VERTICAL_MAX_DEG)
        self.ax.set_xlabel("Horizontal angle [deg]", color="#80deea")
        self.ax.set_ylabel("Vertical angle [deg]", color="#80deea")
        self.ax.set_title("RADAR FIRST-PERSON VIEW", color="#b2ebf2", pad=12)
        self.ax.tick_params(colors="#80deea")
        self.ax.grid(True, color="#1e88a8", linestyle="--", alpha=0.38)

        for spine in self.ax.spines.values():
            spine.set_color("#26c6da")

        # 정면 0°와 고각 커버리지 중심 2°를 기준선으로 표시합니다.
        self.ax.axvline(0.0, color="#4dd0e1", linewidth=1.0, alpha=0.75)
        self.ax.axhline(0.0, color="#4dd0e1", linewidth=0.8, alpha=0.45)
        self.ax.axhline(
            ELEVATION_CENTER_DEG,
            color="#ffee58",
            linewidth=1.1,
            alpha=0.85,
        )
        self.ax.plot(
            [-1.5, 1.5],
            [ELEVATION_CENTER_DEG, ELEVATION_CENTER_DEG],
            color="#ffee58",
            linewidth=1.5,
        )
        self.ax.plot(
            [0.0, 0.0],
            [ELEVATION_CENTER_DEG - 0.5, ELEVATION_CENTER_DEG + 0.5],
            color="#ffee58",
            linewidth=1.5,
        )

        self.ax.text(
            HORIZONTAL_MIN_DEG + 2,
            VERTICAL_MAX_DEG - 0.5,
            "FOV  H:100°  EL:0°~10°  CENTER:2°",
            color="#80cbc4",
            fontsize=9,
            va="top",
        )

    def _draw_radar_at_origin(self, horizontal_deg, vertical_deg):
        """HUD 주축에 레이더를 직접 그려 받침점을 정확히 (0°, 0°)에 둡니다."""
        base_x = 0.0
        base_y = 0.0

        # 받침대의 아래쪽 중심이 데이터 좌표 원점과 정확히 일치합니다.
        self.ax.add_patch(
            Ellipse(
                (base_x, base_y + 0.20),
                width=2.4,
                height=0.4,
                facecolor="#263f4a",
                edgecolor="#80deea",
                linewidth=1.2,
                zorder=20,
            )
        )
        self.ax.add_patch(
            Rectangle(
                (base_x - 0.7, base_y + 0.2),
                width=1.4,
                height=0.4,
                facecolor="#355866",
                edgecolor="#80deea",
                linewidth=1.0,
                zorder=19,
            )
        )
        self.ax.add_patch(
            Rectangle(
                (base_x - 0.15, base_y + 0.58),
                width=0.3,
                height=0.85,
                facecolor="#607d8b",
                edgecolor="#b2ebf2",
                linewidth=1.0,
                zorder=21,
            )
        )

        pivot_x = base_x
        pivot_y = base_y + 1.43

        # 타깃 방향을 HUD 화면상의 단위 벡터로 변환합니다.
        target_dx = horizontal_deg - pivot_x
        target_dy = vertical_deg - pivot_y
        target_norm = math.hypot(target_dx, target_dy)
        if target_norm < 1e-9:
            direction_x, direction_y = 0.0, 1.0
        else:
            direction_x = target_dx / target_norm
            direction_y = target_dy / target_norm

        right_x = direction_y
        right_y = -direction_x
        dish_half_width = 0.95

        dish_left = (
            pivot_x - dish_half_width * right_x,
            pivot_y - dish_half_width * right_y,
        )
        dish_right = (
            pivot_x + dish_half_width * right_x,
            pivot_y + dish_half_width * right_y,
        )
        dish_back = (
            pivot_x - 0.38 * direction_x,
            pivot_y - 0.38 * direction_y,
        )

        # 포물면 안테나를 HUD 색상에 맞춘 삼각형 실루엣으로 표현합니다.
        self.ax.add_patch(
            Polygon(
                [dish_left, dish_right, dish_back],
                closed=True,
                facecolor="#90a4ae",
                edgecolor="#b2ebf2",
                linewidth=1.2,
                zorder=22,
            )
        )
        self.ax.add_patch(
            Circle(
                (pivot_x, pivot_y),
                radius=0.15,
                facecolor="#ff8f00",
                edgecolor="#ffe0b2",
                linewidth=1.0,
                zorder=24,
            )
        )

        feed_x = pivot_x + 0.68 * direction_x
        feed_y = pivot_y + 0.68 * direction_y
        self.ax.plot(
            [pivot_x, feed_x],
            [pivot_y, feed_y],
            color="#ffb300",
            linewidth=2.0,
            zorder=23,
        )
        self.ax.add_patch(
            Circle(
                (feed_x, feed_y),
                radius=0.12,
                facecolor="#ff6f00",
                edgecolor="#fff3e0",
                linewidth=0.9,
                zorder=24,
            )
        )

        self.ax.text(
            0.0,
            2.45,
            "RADAR H=2 m",
            color="#80deea",
            fontsize=8,
            ha="center",
            va="bottom",
            zorder=25,
        )

    def _draw_drone_silhouette(self, horizontal_deg, vertical_deg, distance):
        """각도 화면에 거리에 따라 크기가 달라지는 드론 실루엣을 그립니다."""
        # 가까운 타깃은 크게, 먼 타깃은 작게 표시하되 식별 가능한 최소 크기를 둡니다.
        range_ratio = (distance - MIN_RANGE_M) / (MAX_RANGE_M - MIN_RANGE_M)
        # HUD를 가리지 않도록 이전 크기의 약 40% 수준으로 축소합니다.
        size = max(0.22, 0.78 - 0.52 * range_ratio)
        body_width = 2.0 * size
        body_height = 0.75 * size
        arm_x = 2.2 * size
        arm_y = 1.25 * size
        rotor_radius = 0.42 * size

        self.ax.add_patch(
            Ellipse(
                (horizontal_deg, vertical_deg),
                body_width,
                body_height,
                facecolor="#ff7043",
                edgecolor="#ffe0b2",
                linewidth=1.3,
                zorder=7,
            )
        )

        # X형 암과 네 개의 프로펠러를 정면에서 본 형태입니다.
        for x_sign, y_sign in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
            rotor_x = horizontal_deg + x_sign * arm_x
            rotor_y = vertical_deg + y_sign * arm_y
            self.ax.plot(
                [horizontal_deg, rotor_x],
                [vertical_deg, rotor_y],
                color="#b0bec5",
                linewidth=2.3,
                zorder=5,
            )
            self.ax.add_patch(
                Circle(
                    (rotor_x, rotor_y),
                    rotor_radius,
                    facecolor="#263238",
                    edgecolor="#4dd0e1",
                    linewidth=1.1,
                    zorder=8,
                )
            )

        # 드론의 위쪽 방향을 나타내는 작은 노즈 표시입니다.
        self.ax.add_patch(
            Polygon(
                [
                    (horizontal_deg, vertical_deg + body_height),
                    (horizontal_deg - 0.38 * size, vertical_deg + 0.15 * size),
                    (horizontal_deg + 0.38 * size, vertical_deg + 0.15 * size),
                ],
                closed=True,
                facecolor="#ffee58",
                edgecolor="#fff9c4",
                zorder=9,
            )
        )

    def plot_target(self, _event=None, show_error=True):
        """좌표를 각도로 변환하고 레이더 1인칭 화면에 타깃을 표시합니다."""
        try:
            x, y, z, distance, horizontal_deg, vertical_deg = (
                self._read_coordinate()
            )
        except ValueError as error:
            if show_error:
                messagebox.showerror("입력 오류", str(error), parent=self.root)
            return

        self.var_coordinate.set(f"({x:g}, {y:g}, {z:g})")
        self.var_horizontal.set(horizontal_deg)
        self.var_vertical.set(vertical_deg)
        self.horizontal_value.config(text=f"{horizontal_deg:+.2f}°")
        self.vertical_value.config(text=f"{vertical_deg:.2f}°")

        self.ax.clear()
        self._format_hud()
        self._draw_radar_at_origin(horizontal_deg, vertical_deg)
        self._draw_drone_silhouette(horizontal_deg, vertical_deg, distance)

        self.ax.scatter(
            horizontal_deg,
            vertical_deg,
            s=85,
            facecolors="none",
            edgecolors="#ffeb3b",
            linewidths=1.2,
            zorder=10,
        )
        self.ax.text(
            horizontal_deg,
            min(vertical_deg + 0.9, VERTICAL_MAX_DEG - 0.3),
            f"TARGET\nR={distance:.1f} m",
            color="#ffeb3b",
            fontsize=9,
            ha="center",
            va="bottom",
            weight="bold",
            zorder=11,
        )

        self.ax.text(
            HORIZONTAL_MAX_DEG - 2,
            VERTICAL_MAX_DEG - 0.5,
            f"AZ {horizontal_deg:+.2f}°\nEL {vertical_deg:.2f}°\nRNG {distance:.1f} m",
            color="#a5d6a7",
            fontsize=9,
            ha="right",
            va="top",
            family="monospace",
        )

        self.canvas.draw_idle()
        self.var_status.set(
            f"Target=({x:.1f}, {y:.1f}, altitude={z:.1f}) m  |  "
            f"Range={distance:.1f} m  |  "
            f"Horizontal={horizontal_deg:+.2f}°  |  Vertical={vertical_deg:.2f}°"
        )

    def clear_view(self):
        """입력값과 레이더 화면을 초기화합니다."""
        self.var_coordinate.set("")
        self.var_horizontal.set(0.0)
        self.var_vertical.set(ELEVATION_CENTER_DEG)
        self.horizontal_value.config(text="+0.00°")
        self.vertical_value.config(text=f"{ELEVATION_CENTER_DEG:.2f}°")
        self.ax.clear()
        self._format_hud()
        self._draw_radar_at_origin(0.0, ELEVATION_CENTER_DEG)
        self.canvas.draw_idle()
        self.var_status.set("화면이 초기화되었습니다.")
        self.coordinate_entry.focus_set()


def main():
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista")
    except tk.TclError:
        pass

    RadarFirstPersonApp(root)
    root.minsize(820, 720)
    root.mainloop()


if __name__ == "__main__":
    main()
