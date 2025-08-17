# blackbox-demo

## 개요
이 프로젝트는 블랙박스 영상 파일을 자동으로 녹화하고, 음성 명령(예: "블랙박스")을 인식하여 특정 시점 전후의 영상을 서버로 업로드하는 Python 기반 데모입니다.  
주요 기능은 실시간 영상 녹화, 음성 트리거, GPS(시뮬레이션 포함), 영상 파일 자동 업로드입니다.

## 주요 기능
- **실시간 영상 녹화**: 웹캠(기본 0번)을 통해 10초 단위로 mp4 파일로 저장
- **음성 인식 트리거**: "블랙박스" 등 한국어 음성 명령을 인식하여 이벤트 발생
- **이벤트 시점 영상 추출**: 음성 인식 시점 기준 전후 영상 파일 자동 탐색
- **서버 업로드**: 선택된 영상 파일을 zip으로 압축 후 HTTP POST로 서버 업로드
- **GPS 연동**: 실제 GPS 또는 시뮬레이션 데이터 사용 가능

## 설치 방법

1. Python 3.11 이상 필요
2. 의존성 설치
   ```bash
   pip install -r requirements.txt
   ```
   또는
   ```bash
   pip install opencv-python pyaudio requests speechrecognition
   ```

## 실행 방법

```bash
python main.py
```

- 프로그램 실행 시 음성 인식 스레드와 영상 녹화가 동시에 시작됩니다.
- "블랙박스"라고 말하면 해당 시점 전후의 영상이 자동으로 서버로 업로드됩니다.

## 파일 구조

- `main.py` : 전체 기능(녹화, 음성인식, 업로드, GPS 등) 구현
- `pyproject.toml` : 프로젝트 메타/의존성 관리
- `README.md` : 프로젝트 설명 파일

## 주요 의존성
- opencv-python
- pyaudio
- requests
- speechrecognition

## 참고/주의사항
- macOS, Linux, Windows 환경에서 동작(단, 카메라/마이크 권한 필요)
- 업로드 서버 URL은 코드 내에서 직접 수정 필요
- GPS는 실제 장치가 없으면 시뮬레이션 모드로 동작
