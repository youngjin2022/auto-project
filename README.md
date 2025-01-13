## 실행 전 필수 사항
```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 수정 및 삭제 시 깃 명령어
```bash
git add .
git commit -m "커밋 메세지 예) :read: 변경 (#12)"
git push origin $(git rev-parse --abbrev-ref HEAD)
-- 브랜치에 올라가지 않는 것 : .venv, tdms
```

## 1. 설정 파일 처리
```bash
config.ini 파일 읽기:
TDMS 파일이 저장된 디렉토리 경로(directory)와 API 엔드포인트(channel_names_url, channel_data_url)를 설정 파일에서 가져옵니다.
설정 파일 경로는 환경 변수 CONFIG_PATH에서 가져오며, 기본값은 config/config.ini입니다.
```

## 2. 기본 상수
```bash
주파수 범위 설정:
F_MIN: 최소 주파수(5 Hz)
F_MAX: 최대 주파수(3000 Hz)
```

## 3. 주요 기능
```bash
(1) 포트 대기
wait_for_port:
특정 호스트와 포트(예: localhost:8080)가 열릴 때까지 대기합니다.
(2) 최신 TDMS 파일 가져오기
get_latest_tdms_file:
설정된 디렉토리에서 가장 최근에 생성된 .tdms 파일을 찾아 반환합니다.
(3) TDMS 파일 읽기
read_tdms_file:
TDMS 파일을 읽어 TdmsFile 객체를 반환합니다.
(4) 채널 이름 추출
extract_channel_names:
TDMS 파일에서 각 채널의 이름(NI_ChannelName)을 추출합니다.
(5) API로 채널 이름 전송
send_channel_names_to_api:
추출한 채널 이름을 channel_names_url API로 POST 요청을 통해 전송합니다.
(6) FFT 계산
get_fft:
채널 데이터에 대해 FFT를 계산하여 주파수와 진폭 데이터를 반환합니다.
윈도우 함수(Hann)를 적용하여 신호를 스무딩하고, FFT 계산 후 스펙트럼 크기를 정규화합니다.
(7) Overall 값 계산
get_overall:
설정된 주파수 범위(F_MIN, F_MAX) 내에서 RMS 값을 계산하고 이를 Overall 값으로 반환합니다.
(8) 채널 데이터 추출
extract_channel_data:
TDMS 파일에서 각 채널의 데이터를 읽고, FFT와 Overall 값을 계산한 후 결과를 딕셔너리로 저장합니다.
(9) API로 채널 데이터 전송
send_channel_data_to_api:
추출된 채널 데이터를 channel_data_url API로 POST 요청을 통해 전송합니다.
```

## 4. 파일 시스템 이벤트 핸들링
```bash
TdmsFileHandler 클래스:
새로운 .tdms 파일이 생성되면 해당 파일을 읽고, 채널 데이터를 추출하여 API로 전송합니다.
watchdog 라이브러리를 사용하여 디렉토리를 모니터링합니다.
```

## 5. 메인 실행 흐름
```bash
포트 대기: wait_for_port("localhost", 8080)로 서버 포트가 열릴 때까지 대기.
초기 TDMS 처리:
최신 TDMS 파일을 읽어 채널 이름과 데이터를 추출한 후 API로 전송.
디렉토리 모니터링:
Observer를 통해 설정된 디렉토리에서 새로운 .tdms 파일 생성 이벤트를 감지하여 처리.
```

## 6. 주요 예외 처리
```bash
예외 발생 시 로직이 중단되지 않도록 대부분의 주요 함수에서 예외를 try-except로 처리합니다.
로그 처리 대신 단순히 예외를 무시하거나 통과하도록 구현.
전체 요약
이 코드는 TDMS 파일의 생성과 업데이트를 실시간으로 모니터링하고, 해당 파일에서 데이터를 추출하여 API로 전송하는 시스템입니## 다. 이를 통해 센서 
처리 및 실시간 분석이 가능하도록 설계되었습니다.
```

## 7. urlparse
```bash
urlparse는 
URL을 구성 요소별로 나눠서 처리할 수 있는 아주 유용한 도구
예)
urlparse는 channel_data_url을 다음과 같이 분리
scheme: "http"
hostname: "localhost"
port: 8080
path: "/api/channel/data"
```



