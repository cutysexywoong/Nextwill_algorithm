# 작업 폴더 파일 안내서

> 기준: `C:\FIrst_Woong`에 **현재 실제로 존재하는 프로젝트 파일**을 정리했다. `.git` 내부 기록과 자동 캐시는 제외했다.

## 1. 이 폴더를 한눈에 보면

| 폴더 | 쉬운 설명 |
|---|---|
| `Emerge_excercise/Custome_Layout` | 25×25 픽셀 무늬로 PCB 필터를 만들고 EMerge로 해석하는 현재 핵심 작업 |
| `coral_v1-yongmo-emerge` | 50 Ω 선로·저역통과필터·헤어핀 필터를 여러 방식으로 표시/해석한 실험 모음 |
| `EMerge_Study/EMerge_example` | EMerge 기능별 학습 예제 |
| `s2p_viewer` | 시뮬레이션 결과인 Touchstone 파일을 그래프로 보는 프로그램 |
| `birthday_check` | Python 기초 연습용 생일 달력 프로그램 |

핵심 흐름은 다음과 같다.

`레이아웃 생성 → PCB/공기/포트 구성 → 메쉬 생성 → 주파수 해석 → S-파라미터 저장·표시`

## 2. 현재 핵심: `Emerge_excercise/Custome_Layout`

| 파일 | 역할과 의미 |
|---|---|
| `Custome_Layout.py` | 25×25 문자열에서 `1`인 칸 238개를 0.4 mm 금속 픽셀로 바꾼다. `CustomeConfig`는 치수, `Pixel`은 한 칸, `LayoutData`는 전체 결과를 담는다. |
| `Custome_gmsh.py` | 위 픽셀과 양쪽 포트, 20×20 mm PCB, 접지면, 40×40 mm 공기 상자를 만든 뒤 **Gmsh 메쉬**를 눈으로 확인한다. 실제 해석은 하지 않는다. |
| `Custome_structure.py` | 같은 모델을 EMerge 3D 뷰어로 표시한다. 재료 색과 투명도를 줘 PCB 구조 확인에 알맞다. |
| `Custome_Simulation.py` | 실제 해석 담당. 8·9·10·11·12 GHz를 계산하고 S2P와 레이아웃 PNG를 저장한다. MPI 관련 모듈은 가짜 객체로 대체하고 PARDISO를 사용한다. NPZ 저장은 현재 주석 처리되어 있다. |
| `Custome_Layout.zip` | `Custome_Layout.py`, `Custome_Simulation.py`를 묶어 둔 전달/백업 파일이다. |
| `Custome_structure.zip` | `Custome_structure.py`, `Custome_gmsh.py`를 묶어 둔 전달/백업 파일이다. |
| `model.png` | 3D 직육면체 모델 화면 캡처. 현재 픽셀 패턴보다는 공기 상자 같은 단순 박스를 보여 주는 참고 이미지다. |
| `Coral2/result/png/custome_bpf_v3_custom_20x20.png` | 생성된 금속 픽셀 패턴을 검은 배경에 저장한 결과 이미지다. |
| `Coral2/result/s2p/custome_bpf_v3_custom_20x20.s2p` | 2포트 S-파라미터 결과. 현재는 **10 GHz 한 점만** 있어, 코드에 지정된 5점 해석이 모두 저장된 결과는 아닌 것으로 보인다. |

`Custome_Layout/Custome_Layout.py`는 위 레이아웃 파일과 해시까지 같은 **완전한 복사본**이다.

## 3. `coral_v1-yongmo-emerge`

세 설계의 공통 조건은 FR-4와 비슷한 기판(`er=4`), 금 도체, 50 Ω 포트, 1 MHz~50 GHz 해석이다.

### 설계별 의미

| 폴더 | 설계 |
|---|---|
| `50Ohm_EMerge` | 폭 0.8012 mm, 길이 26.298 mm인 기본 50 Ω 마이크로스트립. 다른 결과를 비교하는 기준선이다. |
| `Filter_EMerge` | 폭이 좁고 넓은 선로를 번갈아 배치한 13차 체비셰프 저역통과필터(LPF)다. |
| `Hairpin_EMerge` | 크기가 다른 U자 공진기 3개를 가까이 둔 헤어핀 필터다. |

각 폴더의 파일 이름은 같은 규칙을 쓴다.

| 파일 계열 | 역할 |
|---|---|
| `*_Lumped_EM_1.py` | 1차 배치로 전체 주파수 해석을 실행하고 S2P를 저장한다. |
| `*_Lumped_EM_2.py` | 2차 배치. PCB를 더 큰 공기 상자 중앙으로 옮긴 개선/비교안이다. `Filter` 버전은 상세 한글 주석도 추가됐다. |
| `*_Lumped_Gmsh_1.py` | 1차 배치의 Gmsh 메쉬 확인용이다. |
| `*_Lumped_Gmsh_2.py` | 2차 중앙 배치의 Gmsh 메쉬 확인용이다. |
| `*_Lumped_pyvista_1.py` | 1차 구조를 PyVista의 낮은 수준 API로 직접 색칠해 표시한다. |
| `*_Lumped_pyvista_2.py` | 2차 구조를 PyVista로 표시한다. |
| `*_Lumped_Structure_1.py` | 1차 구조를 EMerge의 `display.add_object` 방식으로 표시한다. |
| `*_Lumped_Structure_2.py` | 2차 구조를 EMerge 기본 표시 방식으로 확인한다. |

따라서 아래 24개 파일은 각각 위 표의 조합이다.

- `50Ohm_emerge_Lumped_EM_1.py`, `50Ohm_emerge_Lumped_EM_2.py`
- `50Ohm_emerge_Lumped_Gmsh_1.py`, `50Ohm_emerge_Lumped_Gmsh_2.py`
- `50Ohm_emerge_Lumped_pyvista_1.py`, `50Ohm_emerge_Lumped_pyvista_2.py`
- `50Ohm_emerge_Lumped_Structure_1.py`, `50Ohm_emerge_Lumped_Structure_2.py`
- `Filter_emerge_Lumped_EM_1.py`, `Filter_emerge_Lumped_EM_2.py`
- `Filter_emerge_Lumped_Gmsh_1.py`, `Filter_emerge_Lumped_Gmsh_2.py`
- `Filter_emerge_Lumped_pyvista_1.py`, `Filter_emerge_Lumped_pyvista_2.py`
- `Filter_emerge_Lumped_Structure_1.py`, `Filter_emerge_Lumped_Structure_2.py`
- `Hairpin_emerge_Lumped_EM_1.py`, `Hairpin_emerge_Lumped_EM_2.py`
- `Hairpin_emerge_Lumped_Gmsh_1.py`, `Hairpin_emerge_Lumped_Gmsh_2.py`
- `Hairpin_emerge_Lumped_pyvista_1.py`, `Hairpin_emerge_Lumped_pyvista_2.py`
- `Hairpin_emerge_Lumped_Structure_1.py`, `Hairpin_emerge_Lumped_Structure_2.py`

`hybrid_coupler`는 내용이 없는 빈 파일로, 아직 구현되지 않은 자리표시자에 가깝다.

## 4. `EMerge_Study/EMerge_example`

| 파일 | 배우는 내용 |
|---|---|
| `boundary_selection.py` | 불리언 연산 뒤에도 원하는 면을 골라 포트·흡수 경계를 지정하는 법과 원거리장 계산 |
| `differential_common_mode.py` | 4개 단일 포트를 차동 모드(DM)와 공통 모드(CM)로 묶어 S-파라미터와 전계를 비교하는 법 |
| `helix_antenna.py` | 헬릭스 안테나 형상, 급전, 흡수 경계, S11, 2D/3D 방사 패턴 계산 |
| `lumped_element_filter.py` | PCB 선로 사이에 인덕터·커패시터·비아 같은 집중소자를 넣은 필터 해석 |
| `mode_alignment.py` | 다중 모드 도파관에서 편파 방향과 위상을 정렬해 모드 번호를 일정하게 유지하는 법 |
| `plot_hybrid_coupler_sparameters.py` | 외부 `.s4p`를 읽어 하이브리드 커플러의 S11/S21/S31/S41을 논문 기준 대역과 비교해 PNG로 저장 |
| `slotline_transition.py` | 마이크로스트립-슬롯라인 전환 구조와 적응형 메쉬 세분화 사용법 |
| `step_import.py` | STEP 3D 모델을 가져와 재료·포트·방사 경계를 붙이고 안테나를 해석하는 법 |

## 5. `s2p_viewer`

| 파일 | 역할과 의미 |
|---|---|
| `Spara.py` | Tkinter GUI에서 `.s1p`, `.s2p` 등 Touchstone 파일을 읽는다. DB/MA/RI 형식을 복소수로 바꿔 dB 그래프, S21 연속 위상, S11/S22 스미스 차트와 마우스 값을 표시한다. 화면 구성상 실제 그래프는 2포트 이상을 요구한다. |
| `4.s2p` | EMerge가 만든 2포트 예제 데이터. 0.1~30 GHz의 91개 지점이며 RI(실수/허수), 기준 임피던스 50 Ω 형식이다. |

## 6. `birthday_check`

| 파일 | 역할과 발전 과정 |
|---|---|
| `birthday_check_v1.py` | 지정 날짜의 요일만 계산하는 첫 버전이다. 현재 날짜는 코드에 고정돼 있다. |
| `birthday_check_v2.py` | 한 달 달력을 그리고 목표 날짜를 ANSI 빨간 글씨로 강조한다. 날짜는 여전히 고정값이다. |
| `birthday_check_v3.py` | 생일과 확인할 연도를 사용자에게 입력받고 잘못된 입력을 처리한다. |
| `README.md` | 프로그램 목적·기능·실행법을 소개한다. 실행 예시는 v2 기준이다. |
| `.gitignore` | Python 캐시와 VS Code 설정을 Git 추적에서 제외한다. |

## 7. 루트와 설정 파일

| 파일 | 역할 |
|---|---|
| `TODAY_WORK_SUMMARY.md` | 2026-05-13 Git/GitHub 연결, SSH 키 등록, 기본 Git 명령을 초보자용으로 기록한 작업 일지다. |
| `.vscode/settings.json` | VS Code가 Python 환경과 패키지를 Conda로 관리하도록 지정한다. |
| `.vscode/woong_exercise` | 내용이 없는 빈 자리표시자 파일이다. |
| `ayeyo` | `dfasdfsdf`만 적힌 테스트/메모 파일로 프로그램 기능은 없다. |

## 8. 알아둘 점

- EMerge 파일은 `emerge`, `gmsh`, `numpy`가 필요하며 표시/그래프에 `pyvista`, `matplotlib` 등이 추가로 필요할 수 있다.
- `coral_v1-yongmo-emerge`의 해석 파일은 결과 경로가 Linux의 `/scratch/home/...`로 고정되어 있어 현재 Windows에서 그대로 실행하면 경로 수정이 필요하다.
- `step_import.py`가 요구하는 `DielectricRod.step`과 하이브리드 그래프가 요구하는 `.s4p`는 현재 폴더에 없다.
- `plot_hybrid_coupler_sparameters.py`는 Touchstone 행렬 순서 해석을 다시 확인하는 편이 안전하다. 표준 SnP 순서는 보통 `S11, S21, ...`인데 코드 주석과 `reshape`는 행 우선 순서를 가정한다.
- `Custome_Simulation.py`는 마지막에 생성된 `.EMResults` 폴더를 삭제한다. 중간 원본 결과가 필요하면 이 부분을 먼저 확인해야 한다.
- `TODAY_WORK_SUMMARY.md`에는 이메일과 SSH 키 지문이 기록돼 있다. 공개 저장소에 올릴 때 공개 범위를 한 번 확인하는 것이 좋다.
- 현재 환경에서는 Python 실행기가 정상 시작되지 않아 실행 테스트 대신 코드·데이터·이미지를 정적 분석했다.

## 9. 초보자용 용어 5개

| 용어 | 뜻 |
|---|---|
| 메쉬 | 3D 구조를 계산 가능한 작은 조각으로 나눈 것 |
| 포트 | 전기 신호가 들어오고 나가는 입·출구 |
| S11 | 입력 신호 중 되돌아온 비율. 작을수록 정합이 좋다. |
| S21 | 입력에서 출력으로 전달된 비율. 통과 성능을 뜻한다. |
| 공기 상자 | 열린 공간을 컴퓨터 안에서 유한한 계산 영역으로 만든 것 |
