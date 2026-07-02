function rawDataCases = raw_data()
%RAW_DATA 여러 대의 드론에 대한 FMCW 레이더 원시 I/Q 신호를 생성합니다.
%
% 반환값:
%   rawDataCases{1} - 드론 1대의 복소 원시 ADC 데이터 [Nd x Nr]
%   rawDataCases{2} - 드론 2대의 복소 원시 ADC 데이터 [Nd x Nr]
%   rawDataCases{3} - 드론 3대의 복소 원시 ADC 데이터 [Nd x Nr]
%
% 사용 예:
%   data = raw_data();
%   oneDroneData = data{1};
%   threeDroneData = data{3};
%
% 이 파일은 원시 I/Q 신호만 생성하며 FFT, STFT 및 그래프 처리는 하지 않습니다.

    %% 1. FMCW 레이더 파라미터
    params.c = 3e8;                 % 진공에서의 빛의 속도 [m/s]
    params.fc = 77e9;               % 레이더 반송파 중심주파수 [Hz]
    params.lambda = params.c / params.fc; % 반송파 파장 [m]

    params.B = 150e6;               % Chirp 대역폭 [Hz]
    params.Tc = 50e-6;              % 단일 Chirp 지속시간 [s]
    params.S = params.B / params.Tc; % Chirp 주파수 변화율 [Hz/s]

    params.Nr = 256;                % Chirp당 ADC 샘플 수
    params.Nd = 128;                % 프레임당 Chirp 수
    params.Fs = params.Nr / params.Tc; % ADC 샘플링 주파수 [Hz]

    %% 2. 드론 및 프로펠러 파라미터
    params.rpm = 3600;              % 프로펠러 회전 속도 [rpm]
    params.fRot = params.rpm / 60;  % 초당 프로펠러 회전수 [Hz]
    params.propRadius = 0.10;       % 프로펠러 반지름 [m], 참고용
    params.numRotors = 4;           % 드론의 로터 개수
    params.microAmp = 0.25;         % Micro-Doppler 위상 변조 강도

    %% 3. Fast-time 및 Slow-time 시간축
    % tFast는 1 x Nr 행 벡터, tSlow는 Nd x 1 열 벡터입니다.
    params.tFast = (0:params.Nr - 1) / params.Fs;
    params.tSlow = (0:params.Nd - 1).' * params.Tc;

    % 암시적 확장을 사용해 [Nd x Nr] 절대시간 격자를 만듭니다.
    params.t = params.tSlow + params.tFast;

    %% 4. 드론 수별 원시 I/Q 데이터 생성
    rawDataCases = cell(1, 3);
    for numDrones = 1:3
        rawDataCases{numDrones} = generate_scene(numDrones, params);
    end
end


function signal = generate_drone_signal(R0, velocity, amplitude, params)
%GENERATE_DRONE_SIGNAL 단일 드론의 복소 FMCW 비트 신호를 생성합니다.
%
% 입력값:
%   R0        - 초기 거리 [m]
%   velocity  - 방사 속도 [m/s], 양수는 멀어지고 음수는 접근
%   amplitude - 상대 반사 신호 크기
%   params    - 레이더 및 드론 파라미터 구조체

    % 등속 운동을 가정한 시간별 드론 거리 [m]
    range = R0 + velocity .* params.t;

    % 거리에 의해 발생하는 FMCW 비트 주파수 [Hz]
    beatFrequency = 2 .* params.S .* range ./ params.c;

    % 드론 본체의 왕복 경로에 따른 도플러 주파수 [Hz]
    dopplerFrequency = 2 .* velocity ./ params.lambda;

    % 거리 비트 위상과 본체 도플러 위상을 합산합니다.
    bodyPhase = 2 .* pi .* ( ...
        beatFrequency .* params.tFast + dopplerFrequency .* params.t);

    % 모든 로터의 Micro-Doppler 위상을 누적합니다.
    microPhase = zeros(size(params.t));
    for rotorIndex = 0:params.numRotors - 1
        rotorPhaseOffset = rotorIndex .* 2 .* pi ./ params.numRotors;
        microPhase = microPhase + params.microAmp .* sin( ...
            2 .* pi .* params.fRot .* params.t + rotorPhaseOffset);
    end

    % 전체 위상을 복소 지수로 변환하여 I/Q 신호를 생성합니다.
    signal = amplitude .* exp(1i .* (bodyPhase + microPhase));
end


function raw = generate_scene(numDrones, params)
%GENERATE_SCENE 지정한 수의 드론 신호와 복소 가우시안 잡음을 합산합니다.

    % 각 행은 [초기 거리(m), 방사 속도(m/s), 상대 반사 크기]입니다.
    drones = [
        30,  10, 1.0;
        45,  -6, 0.8;
        60,  15, 0.7
    ];

    if numDrones < 1 || numDrones > size(drones, 1) || fix(numDrones) ~= numDrones
        error('numDrones는 1, 2 또는 3인 정수여야 합니다.');
    end

    % 드론별 신호를 누적할 복소 원시 ADC 배열을 초기화합니다.
    raw = complex(zeros(params.Nd, params.Nr));
    for droneIndex = 1:numDrones
        raw = raw + generate_drone_signal( ...
            drones(droneIndex, 1), ...
            drones(droneIndex, 2), ...
            drones(droneIndex, 3), ...
            params);
    end

    % 실수부와 허수부에 전력을 절반씩 배분한 복소 가우시안 잡음입니다.
    noisePower = 0.05;
    noise = sqrt(noisePower / 2) .* ( ...
        randn(params.Nd, params.Nr) + ...
        1i .* randn(params.Nd, params.Nr));

    raw = raw + noise;
end
