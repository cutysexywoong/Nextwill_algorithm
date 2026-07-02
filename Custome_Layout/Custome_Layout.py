# -*- coding: utf-8 -*-
"""
Custome Layout Generator v3 (Custom Pattern)
- 모자이크 크기: 25x25 (10x10mm)
- 픽셀 크기: 0.4mm
- 기판 크기: 20x20mm
- 사용자가 지정한 25x25 배열 기반 생성
- 대각선 제거 로직 적용
"""

from dataclasses import dataclass, field
from typing import List, Optional
import numpy as np

# 사용자가 방금 주신 커스텀 패턴
CUSTOM_PATTERN = [
     "0000000000000000000000000",
    "0000000000000000000000000",
    "0000000000000000000000000",
    "0110011111001101101001101",
    "0101011111101010110010111",
    "1011100010011111100011001",
    "1001110000001000110110000",
    "0101111100000000011110010",
    "1111111010110000011110000",
    "1000110111101000101011111",
    "1010011110001001010001111",
    "0001001111010100110100001",
    "0001100101000001000011000",
    "0101001111101011101100010",
    "1101101101001011101011011",
    "1100011011101011101111011",
    "0000100000001101100010000",
    "0111110011100010011100010",
    "1101100000001100000011001",
    "1000100011000010000010001",
    "1101101111100011110101001",
    "1110111100011001111100100",
    "0000000000000000000000000",
    "0000000000000000000000000",
    "0000000000000000000000000"
]

@dataclass
class CustomeConfig:
    board_size: float = 20.0
    pixel_boundary: float = 10.0
    boundary_offset: float = 5.0
    pixel_size: float = 0.4
    
    port_width: float = 1.2
    port_length: float = 3.0
    port_y: float = 10.0  # 기판 정중앙
    
    @property
    def grid_size(self) -> int:
        return 25
    
    @property
    def bd_left(self) -> float:
        return self.boundary_offset
        
    @property
    def bd_right(self) -> float:
        return self.boundary_offset + self.pixel_boundary

@dataclass
class Pixel:
    x: float
    y: float
    size: float
    pixel_id: int = 0

@dataclass
class LayoutData:
    pixels: List[Pixel] = field(default_factory=list)
    triangles: list = field(default_factory=list)
    config: CustomeConfig = field(default_factory=CustomeConfig)
    grid: Optional[np.ndarray] = None

class CustomePixelGenerator:
    def __init__(self, config: CustomeConfig):
        self.cfg = config
        self.grid = np.zeros((self.cfg.grid_size, self.cfg.grid_size), dtype=bool)

    def generate(self) -> LayoutData:
        layout = LayoutData(config=self.cfg)
        
        # 커스텀 패턴 리딩 (Y축은 텍스트 형태에서 위가 [0]이므로 물리 좌표계에 맞게 반전하여 치환)
        for row_idx, row_str in enumerate(CUSTOM_PATTERN):
            for col_idx, char in enumerate(row_str):
                grid_x = col_idx
                grid_y = (self.cfg.grid_size - 1) - row_idx
                
                if char == '1':
                    self.grid[grid_x, grid_y] = True
                    
        layout.triangles = [] # 룰 적용사항, 대각선 제거
        layout.pixels = self._grid_to_pixels()
        layout.grid = self.grid.copy()
        
        return layout

    def _grid_to_pixels(self) -> List[Pixel]:
        xs, ys = np.where(self.grid)
        pixels = []
        for i, (gx, gy) in enumerate(zip(xs, ys)):
            px = self.cfg.boundary_offset + gx * self.cfg.pixel_size
            py = self.cfg.boundary_offset + gy * self.cfg.pixel_size
            pixels.append(Pixel(px, py, self.cfg.pixel_size, i))
        return pixels

if __name__ == "__main__":
    print("Custome Layout Generator V3 (Custom Pattern) Test")
    config = CustomeConfig()
    generator = CustomePixelGenerator(config)
    layout = generator.generate()
    print(f"Pixels generated: {len(layout.pixels)}")
    print(f"Chamfer triangles: {len(layout.triangles)}")
