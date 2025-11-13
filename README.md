# Bird Detecting Smart CCTV

이 프로젝트는 OpenCV 기반 영상 처리와 실시간 객체 인식을 결합하여 조류 출현을 감지하고 Flask 웹 서버를 통해 스트리밍하는 스마트 CCTV 예제입니다. 개인 NAS 또는 가정용 서버에 배포하여 별도의 플레이어 없이 웹 브라우저에서 실시간 영상을 확인할 수 있도록 설계되었습니다.

## 주요 기능

- **YOLOv8 기반 조류 감지**: Ultralytics의 사전 학습된 모델을 이용해 영상 속에서 `bird` 클래스를 감지합니다.
- **실시간 영상 스트리밍**: Flask가 제공하는 MJPEG 스트리밍 엔드포인트를 통해 브라우저에서 실시간 영상 확인.
- **감지 현황 대시보드**: 최근 감지된 조류 수와 신뢰도 등 요약 정보를 API 및 간단한 웹 UI로 제공.
- **환경 변수 기반 설정**: 비디오 소스와 모델 경로, 새로 분류할 라벨 목록 등을 환경 변수로 손쉽게 조정할 수 있습니다.

## 빠른 시작

1. **필수 라이브러리 설치**

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows의 경우 .venv\\Scripts\\activate
   pip install -r requirements.txt
   ```

2. **Flask 서버 실행**

   ```bash
   export FLASK_APP=birdcctv.app:create_app
   flask run --host=0.0.0.0 --port=8000
   ```

   또는 바로 실행 스크립트를 이용할 수 있습니다.

   ```bash
   python run.py
   ```

   처음 실행 시 Ultralytics 모델 가중치(`yolov8n.pt`)가 자동으로 다운로드되며, 네트워크 속도에 따라 시간이 걸릴 수 있습니다.

3. **웹 브라우저 접속**

   웹 브라우저에서 `http://<서버 IP>:8000` (기본 포트) 으로 접속하면 실시간 스트림과 감지 현황을 확인할 수 있습니다.

## 환경 변수 옵션

| 이름 | 기본값 | 설명 |
|------|--------|------|
| `VIDEO_SOURCE` | `0` | OpenCV 비디오 캡처 소스. 웹캠 인덱스, 파일 경로, RTSP/HTTP 주소 등. |
| `CAMERA_DRIVER` | `opencv` | `opencv` 또는 `picamera2`. Raspberry Pi 카메라 모듈을 직접 사용할 경우 `picamera2` 선택. |
| `VIDEO_BACKEND` | `null` | OpenCV에서 사용할 백엔드(`v4l2`, `gstreamer`). 리눅스 V4L2 드라이버 강제 시 유용. |
| `MODEL_PATH` | `yolov8n.pt` | Ultralytics YOLO 모델 경로 또는 이름. `none`/`disabled`로 설정하면 감지 기능을 끌 수 있습니다. |
| `BIRD_LABELS` | `bird` | 감지 대상으로 사용할 라벨(쉼표로 구분). |
| `MIN_CONFIDENCE` | `0.4` | 감지 결과를 표시하기 위한 최소 신뢰도. |
| `FRAME_WIDTH` | `null` | 리사이즈할 프레임 가로 크기. 지정하지 않으면 원본 유지. |
| `PICAMERA_RESOLUTION` | `1280x720` | `CAMERA_DRIVER=picamera2`일 때 사용할 해상도. `1920x1080` 형태로 지정. |
| `PICAMERA_FPS` | `30` | Picamera2 캡처 프레임 레이트. |

환경 변수는 `.env` 파일이나 Docker/시스템 서비스 설정 등을 이용해 지정할 수 있습니다.

## Raspberry Pi에서 카메라 캡처 설정

1. **카메라 모듈 활성화**  
   `sudo raspi-config` → *Interface Options* → *Camera* → Enable.

2. **필수 패키지 설치**  
   Raspberry Pi OS (Bullseye 이상) 기준:

   ```bash
   sudo apt update
   sudo apt install -y python3-picamera2 python3-opencv libatlas-base-dev
   ```

3. **프로젝트 배포 및 의존성 설치**  
   Pi에 저장소를 복사한 뒤 `pip install -r requirements.txt` 실행. Picamera2는 apt로 설치되므로 `requirements.txt`에 포함되어 있지 않습니다.

4. **Picamera2 드라이버 사용**  
   아래와 같이 환경 변수를 지정하고 서버를 실행합니다.

   ```bash
   export CAMERA_DRIVER=picamera2
   export PICAMERA_RESOLUTION=1280x720   # 필요에 따라 변경
   export PICAMERA_FPS=25
   python run.py
   ```

   또는 systemd 서비스로 등록하여 부팅 시 자동 실행되도록 구성할 수 있습니다.

5. **성능 팁**  
   - GPU 메모리(`raspi-config` → *Performance Options* → *GPU Memory*)를 128MB 이상으로 늘리면 안정적입니다.
   - 감지 모델이 무겁게 느껴지면 `MODEL_PATH=none`으로 설정하고 단순 스트리밍만 수행한 뒤 NAS에서 추가 처리를 해도 됩니다.

## Synology NAS를 통한 스트리밍 아키텍처

Raspberry Pi는 카메라 캡처에 특화되어 있고, Synology NAS는 장시간 서비스 운영과 외부 공개에 적합합니다. 다음 두 가지 운영 패턴을 권장합니다.

### 패턴 A. Pi에서 감지 + NAS Reverse Proxy

1. Raspberry Pi에서 앞선 단계대로 Flask 서버를 실행하고, NAS와 동일한 네트워크에 연결합니다.
2. Synology DSM의 **제어판 → 로그인 포털 → 응용 프로그램 포털 → 역방향 프록시**에서 새 규칙을 추가합니다.
   - 소스: `https://nas도메인/birdcctv` (또는 원하는 경로)
   - 대상: `http://<raspberrypi-ip>:8000`
3. 필요 시 DSM의 인증서 관리에서 Let's Encrypt 인증서를 연결하여 HTTPS 접속을 제공합니다.
4. 외부에서 NAS 주소만 접속하면 Pi가 제공하는 스트림/대시보드를 사용할 수 있습니다.

### 패턴 B. NAS에서 감지 + Pi는 RTSP 공급자

1. **Pi에서 RTSP 송출 준비**

   ```bash
   sudo apt install -y libcamera-apps
   libcamera-vid --inline --framerate 25 --width 1280 --height 720 \
     --codec mjpeg -t 0 --listen -o tcp://0.0.0.0:8554 --profile high
   ```

   위 명령은 `rtsp://<pi-ip>:8554/` (TCP MJPEG) 형태의 스트림을 제공합니다. `screen`이나 `systemd` 서비스로 상시 실행하도록 설정하세요.

2. **Synology Container Manager(Docker)에서 애플리케이션 실행**
   - 레지스트리에서 `python:3.11-slim` 이미지를 다운로드하거나 직접 Dockerfile을 작성합니다.
   - 새 컨테이너를 생성하면서 이 저장소를 볼륨으로 마운트하거나, `docker build -t birdcctv .` 빌드 후 실행합니다.
   - 환경 변수 설정:
     - `VIDEO_SOURCE=rtsp://<pi-ip>:8554/`
     - `VIDEO_BACKEND=gstreamer` (RTSP 안정화를 위해 권장)
     - 필요 시 `MODEL_PATH`, `BIRD_LABELS` 등 추가 설정
   - 포트 매핑: `8000:8000`

   ```

3. **DSM 방화벽 및 DDNS 구성**  
   외부에서 접근하려면 DSM 방화벽에서 8000 포트를 허용하거나, 역방향 프록시를 이용해 443 포트로 노출합니다.



