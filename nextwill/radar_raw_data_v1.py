"""1~3대의 정지/이동 드론에 대한 FMCW 레이더 Raw I/Q 생성기."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

SPEED_OF_LIGHT = 299_792_458.0


@dataclass
class RadarConfig:
    start_frequency_hz: float = 24.0e9
    stop_frequency_hz: float = 24.25e9
    center_frequency_hz: float = 24.125e9
    chirp_duration_s: float = 200e-6
    adc_sample_rate_hz: float = 100e6
    samples_per_chirp: int = 20_000
    number_of_chirps: int = 128
    radar_height_m: float = 2.0
    receiver_snr_db: float = 25.0

    @property
    def bandwidth_hz(self) -> float:
        return self.stop_frequency_hz - self.start_frequency_hz

    @property
    def chirp_slope_hz_per_s(self) -> float:
        return self.bandwidth_hz / self.chirp_duration_s

    @property
    def wavelength_m(self) -> float:
        return SPEED_OF_LIGHT / self.center_frequency_hz

    @property
    def pulse_repetition_frequency_hz(self) -> float:
        return 1.0 / self.chirp_duration_s

    @property
    def range_resolution_m(self) -> float:
        return SPEED_OF_LIGHT / (2.0 * self.bandwidth_hz)

    @property
    def maximum_unambiguous_range_m(self) -> float:
        return (
            SPEED_OF_LIGHT * self.adc_sample_rate_hz
            / (4.0 * self.chirp_slope_hz_per_s)
        )

    @property
    def maximum_unambiguous_velocity_mps(self) -> float:
        return self.wavelength_m / (4.0 * self.chirp_duration_s)


@dataclass
class DroneConfig:
    x_m: float = 0.0
    y_m: float = 1000.0
    altitude_m: float = 37.0
    velocity_x_mps: float = 0.0
    velocity_y_mps: float = 0.0
    velocity_z_mps: float = 0.0
    rotor_rpm: float = 1200.0
    rotor_count: int = 4
    blades_per_rotor: int = 2
    blade_radius_m: float = 0.08
    body_reflection_amplitude: float = 1.0
    blade_reflection_amplitude: float = 0.035

    @property
    def rotor_angular_speed_rad_s(self) -> float:
        return 2.0 * np.pi * self.rotor_rpm / 60.0

    @property
    def blade_tip_speed_mps(self) -> float:
        return self.rotor_angular_speed_rad_s * self.blade_radius_m

    @property
    def speed_mps(self) -> float:
        return math.sqrt(
            self.velocity_x_mps**2
            + self.velocity_y_mps**2
            + self.velocity_z_mps**2
        )


def _geometry(radar: RadarConfig, drone: DroneConfig, time_s: float) -> dict:
    x = drone.x_m + drone.velocity_x_mps * time_s
    y = drone.y_m + drone.velocity_y_mps * time_s
    altitude = drone.altitude_m + drone.velocity_z_mps * time_s
    z = altitude - radar.radar_height_m
    horizontal = math.hypot(x, y)
    slant = math.sqrt(x * x + y * y + z * z)
    radial_velocity = (
        x * drone.velocity_x_mps
        + y * drone.velocity_y_mps
        + z * drone.velocity_z_mps
    ) / slant
    return {
        "x_m": x,
        "y_m": y,
        "altitude_m": altitude,
        "horizontal_range_m": horizontal,
        "slant_range_m": slant,
        "horizontal_angle_deg": math.degrees(math.atan2(x, y)),
        "elevation_angle_deg": math.degrees(math.atan2(z, horizontal)),
        "radial_velocity_mps": radial_velocity,
    }


def _validate_radar(radar: RadarConfig) -> None:
    if radar.bandwidth_hz <= 0 or radar.chirp_duration_s <= 0:
        raise ValueError("종료 주파수와 Chirp 시간은 시작 주파수보다/0보다 커야 합니다.")
    if radar.adc_sample_rate_hz <= 0 or radar.samples_per_chirp <= 0:
        raise ValueError("ADC 샘플링 조건은 양수여야 합니다.")
    expected = round(radar.adc_sample_rate_hz * radar.chirp_duration_s)
    if radar.samples_per_chirp != expected:
        raise ValueError(f"Chirp당 샘플 수는 {expected}개여야 합니다.")
    if radar.number_of_chirps <= 0:
        raise ValueError("Chirp 개수는 1개 이상이어야 합니다.")


def validate_configuration(radar: RadarConfig, drone: DroneConfig) -> dict:
    _validate_radar(radar)
    if drone.rotor_count <= 0 or drone.blades_per_rotor <= 0:
        raise ValueError("로터와 블레이드 개수는 1개 이상이어야 합니다.")
    if drone.rotor_rpm < 0:
        raise ValueError("RPM은 0 이상이어야 합니다.")

    duration = radar.number_of_chirps * radar.chirp_duration_s
    initial = _geometry(radar, drone, 0.0)
    final = _geometry(radar, drone, duration)
    for label, item in (("초기", initial), ("최종", final)):
        if not 5.0 <= item["altitude_m"] <= 300.0:
            raise ValueError(f"{label} 드론 고도는 5~300 m 범위여야 합니다.")
        if item["y_m"] < 0.0:
            raise ValueError(f"{label} 드론은 레이더 정면(+Y)에 있어야 합니다.")
        if not 1.0 <= item["slant_range_m"] <= 5000.0:
            raise ValueError(f"{label} 직선거리는 1~5000 m 범위여야 합니다.")
        if not -50.0 <= item["horizontal_angle_deg"] <= 50.0:
            raise ValueError(f"{label} 수평각은 -50~50도 범위여야 합니다.")
        if not 0.0 <= item["elevation_angle_deg"] <= 10.0:
            raise ValueError(f"{label} 수직각은 0~10도 범위여야 합니다.")

    max_body_doppler = 2.0 * max(
        abs(initial["radial_velocity_mps"]), abs(final["radial_velocity_mps"])
    ) / radar.wavelength_m
    max_blade_doppler = 2.0 * drone.blade_tip_speed_mps / radar.wavelength_m
    if max_body_doppler + max_blade_doppler >= radar.pulse_repetition_frequency_hz / 2:
        raise ValueError("본체와 블레이드 Doppler 합이 Slow-time Nyquist를 초과합니다.")
    return {
        **initial,
        "initial": initial,
        "final": final,
        "speed_mps": drone.speed_mps,
        "maximum_body_doppler_hz": max_body_doppler,
        "maximum_blade_doppler_hz": max_blade_doppler,
    }


def validate_scene(radar: RadarConfig, drones: list[DroneConfig]) -> list[dict]:
    if not 1 <= len(drones) <= 3:
        raise ValueError("드론 수는 1~3대여야 합니다.")
    return [validate_configuration(radar, drone) for drone in drones]


def _chirp_phase(t: np.ndarray, radar: RadarConfig) -> np.ndarray:
    return 2.0 * np.pi * (
        radar.start_frequency_hz * t + 0.5 * radar.chirp_slope_hz_per_s * t**2
    )


def _echo(t, delay, amplitude, radar, phase=0.0):
    return amplitude * np.exp(1j * (_chirp_phase(t - delay, radar) + phase))


def generate_raw_data(
    radar: RadarConfig,
    drones: DroneConfig | list[DroneConfig] | tuple[DroneConfig, ...],
    seed: int = 2026,
) -> dict[str, np.ndarray | str]:
    """각 샘플 시각의 드론 위치를 반영한 복소 Raw I/Q를 생성합니다."""
    drone_list = [drones] if isinstance(drones, DroneConfig) else list(drones)
    derived_drones = validate_scene(radar, drone_list)
    fast = np.arange(radar.samples_per_chirp) / radar.adc_sample_rate_hz
    slow = np.arange(radar.number_of_chirps) * radar.chirp_duration_s
    tx = np.exp(1j * _chirp_phase(fast, radar)).astype(np.complex64)
    shape = (radar.number_of_chirps, radar.samples_per_chirp)
    reflected = np.empty(shape, np.complex64)
    clean = np.empty(shape, np.complex64)
    phase_sets = [
        np.linspace(0, 2 * np.pi, d.rotor_count * d.blades_per_rotor, endpoint=False)
        for d in drone_list
    ]

    for chirp_index, start in enumerate(slow):
        time = start + fast
        total = np.zeros_like(fast, dtype=np.complex128)
        for drone_index, (drone, phases) in enumerate(zip(drone_list, phase_sets)):
            x = drone.x_m + drone.velocity_x_mps * time
            y = drone.y_m + drone.velocity_y_mps * time
            z = drone.altitude_m + drone.velocity_z_mps * time - radar.radar_height_m
            horizontal = np.hypot(x, y)
            distance = np.sqrt(x**2 + y**2 + z**2)
            projection = horizontal / distance
            attenuation = (1000.0 / np.maximum(distance, 1.0)) ** 2
            offset = 0.73 * drone_index
            total += _echo(
                fast, 2 * distance / SPEED_OF_LIGHT,
                drone.body_reflection_amplitude * attenuation, radar, 0.15 + offset,
            )
            for blade_index, blade_phase in enumerate(phases):
                displacement = drone.blade_radius_m * projection * np.cos(
                    drone.rotor_angular_speed_rad_s * time + blade_phase
                )
                variation = 1.0 + 0.08 * math.cos(blade_index * 1.7)
                total += _echo(
                    fast, 2 * (distance + displacement) / SPEED_OF_LIGHT,
                    drone.blade_reflection_amplitude * variation * attenuation,
                    radar, 0.41 * blade_index + offset,
                )
        reflected[chirp_index] = total.astype(np.complex64)
        clean[chirp_index] = tx * np.conjugate(reflected[chirp_index])

    rng = np.random.default_rng(seed)
    signal_power = float(np.mean(np.abs(clean) ** 2))
    noise_power = signal_power / 10 ** (radar.receiver_snr_db / 10)
    sigma = math.sqrt(noise_power / 2)
    noise = sigma * (
        rng.standard_normal(shape, dtype=np.float32)
        + 1j * rng.standard_normal(shape, dtype=np.float32)
    )
    raw_iq = (clean + noise).astype(np.complex64)
    metadata = {
        "format_version": 2,
        "description": f"{len(drone_list)} stationary/moving drone FMCW raw I/Q",
        "array_layout": "[chirp_index, adc_sample_index]",
        "fft_plan": {"range_fft_axis": 1, "doppler_fft_axis": 0, "fft_applied": False},
        "radar": asdict(radar),
        "drone_count": len(drone_list),
        "drones": [asdict(d) for d in drone_list],
        "derived_drones": derived_drones,
        "derived": {
            "range_resolution_m": radar.range_resolution_m,
            "maximum_unambiguous_range_m": radar.maximum_unambiguous_range_m,
            "maximum_unambiguous_velocity_mps": radar.maximum_unambiguous_velocity_mps,
            "observation_duration_s": radar.number_of_chirps * radar.chirp_duration_s,
            "noise_power": noise_power,
            "seed": seed,
        },
    }
    return {
        "tx_reference": tx,
        "reflected_echo": reflected,
        "raw_iq": raw_iq,
        "fast_time_s": fast,
        "slow_time_s": slow,
        "instantaneous_frequency_hz": radar.start_frequency_hz + radar.chirp_slope_hz_per_s * fast,
        "metadata_json": json.dumps(metadata, ensure_ascii=False, indent=2),
    }


def save_raw_data(output_path: Path, data: dict, compressed: bool = False) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    (np.savez_compressed if compressed else np.savez)(output_path, **data)


def print_summary(data: dict, output_path: Path) -> None:
    metadata = json.loads(str(data["metadata_json"]))
    print(f"Raw data generated: {output_path}")
    print(f"raw_iq: {data['raw_iq'].shape}, {data['raw_iq'].dtype}")
    for index, (drone, item) in enumerate(
        zip(metadata["drones"], metadata["derived_drones"]), 1
    ):
        print(
            f"Drone {index}: range {item['initial']['slant_range_m']:.2f} -> "
            f"{item['final']['slant_range_m']:.2f} m, speed {item['speed_mps']:.2f} m/s, "
            f"RPM {drone['rotor_rpm']:.1f}"
        )
    print("FFT: not applied (Range axis=1, Doppler axis=0)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate FMCW complex raw I/Q.")
    parser.add_argument(
        "--output", type=Path,
        default=Path(__file__).resolve().parent / "generated_raw_data" / "drone_scene_raw_v1.npz",
    )
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--compressed", action="store_true")
    args = parser.parse_args()
    data = generate_raw_data(RadarConfig(), DroneConfig(), seed=args.seed)
    save_raw_data(args.output, data, compressed=args.compressed)
    print_summary(data, args.output)


if __name__ == "__main__":
    main()
