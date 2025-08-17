import cv2
import os
import platform
import threading
import time
from datetime import datetime
import speech_recognition as sr
from pathlib import Path
import requests
import zipfile
import io
import json
from dotenv import load_dotenv
# import serial

# 환경변수 로드
load_dotenv()

# 필수 환경변수 목록
REQUIRED_ENV_VARS = [
    "TARGET_DIR", "WINDOW_SECONDS", "GPS_BAUDRATE", "UPLOAD_URL",
    "CHUNK_DURATION", "VIDEO_FPS", "VIDEO_WIDTH", "VIDEO_HEIGHT",
    "WAIT_SECONDS", "COMPRESSION_LEVEL", "SIMULATION_BASE_LAT", 
    "SIMULATION_BASE_LNG", "VOICE_LANGUAGE", "TRIGGER_PHRASES"
]

# 환경변수 체크
missing_vars = []
for var in REQUIRED_ENV_VARS:
    if os.getenv(var) is None:
        missing_vars.append(var)

if missing_vars:
    print(f"ERROR: 다음 환경변수들이 설정되지 않았습니다: {', '.join(missing_vars)}")
    print("blackbox-demo/.env 파일을 확인해주세요.")
    exit(1)

# 환경변수에서 설정 로드
TARGET_DIR = os.path.expanduser(os.getenv("TARGET_DIR"))
FMT = "%Y%m%d%H%M%S"
WINDOW = int(os.getenv("WINDOW_SECONDS"))
GPS_BAUDRATE = int(os.getenv("GPS_BAUDRATE"))
UPLOAD_URL = os.getenv("UPLOAD_URL")
CHUNK_DURATION = int(os.getenv("CHUNK_DURATION"))
VIDEO_FPS = int(os.getenv("VIDEO_FPS"))
VIDEO_WIDTH = int(os.getenv("VIDEO_WIDTH"))
VIDEO_HEIGHT = int(os.getenv("VIDEO_HEIGHT"))
WAIT_SECONDS = int(os.getenv("WAIT_SECONDS"))
COMPRESSION_LEVEL = int(os.getenv("COMPRESSION_LEVEL"))
SIMULATION_BASE_LAT = float(os.getenv("SIMULATION_BASE_LAT"))
SIMULATION_BASE_LNG = float(os.getenv("SIMULATION_BASE_LNG"))
VOICE_LANGUAGE = os.getenv("VOICE_LANGUAGE")
TRIGGER_PHRASES = os.getenv("TRIGGER_PHRASES").split(",")

# OS별 GPS 포트 자동 설정
def get_gps_port():
    system = platform.system().lower()
    if system == "windows":
        return "COM3"
    else:  # Linux, macOS
        return "/dev/ttyUSB0"

GPS_PORT = get_gps_port()

class GPSManager:
    def __init__(self, port=GPS_PORT, baudrate=GPS_BAUDRATE):
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None
        self.current_gps = {'lat': 0.0, 'lng': 0.0, 'timestamp': '', 'valid': False}
        self.gps_lock = threading.Lock()
        self.gps_running = False
        self.gps_queue = queue.Queue()
        
    def connect_gps(self):
        """GPS 수신기 연결"""
        try:
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=1)
            print(f"GPS 연결 성공: {self.port}")
            return True
        except Exception as e:
            print(f"GPS 연결 실패: {e}")
            print("GPS 시뮬레이션 모드로 동작합니다.")
            return False
    
    def parse_nmea_sentence(self, sentence):
        """NMEA 문장 파싱"""
        try:
            if sentence.startswith('$GPGGA') or sentence.startswith('$GNGGA'):
                parts = sentence.split(',')
                if len(parts) >= 6 and parts[2] and parts[4]:
                    # 위도 파싱
                    lat_raw = float(parts[2])
                    lat_deg = int(lat_raw // 100)
                    lat_min = lat_raw % 100
                    lat = lat_deg + lat_min / 60.0
                    if parts[3] == 'S':
                        lat = -lat
                    
                    # 경도 파싱
                    lng_raw = float(parts[4])
                    lng_deg = int(lng_raw // 100)
                    lng_min = lng_raw % 100
                    lng = lng_deg + lng_min / 60.0
                    if parts[5] == 'W':
                        lng = -lng
                    
                    return lat, lng, True
        except Exception as e:
            pass
        return None, None, False
    
    def gps_reader_thread(self, stop_event):
        """GPS 데이터 읽기 스레드"""
        self.gps_running = True
        simulation_base_lat = SIMULATION_BASE_LAT  # 서울시청 위도
        simulation_base_lng = SIMULATION_BASE_LNG  # 서울시청 경도
        
        while self.gps_running and not stop_event.is_set():
            try:
                if self.serial_conn and self.serial_conn.is_open:
                    # 실제 GPS에서 데이터 읽기
                    line = self.serial_conn.readline().decode('ascii', errors='ignore').strip()
                    if line:
                        lat, lng, valid = self.parse_nmea_sentence(line)
                        if valid:
                            with self.gps_lock:
                                self.current_gps = {
                                    'lat': lat,
                                    'lng': lng,
                                    'timestamp': datetime.now().isoformat(),
                                    'valid': True
                                }
                            print(f"GPS: {lat:.6f}, {lng:.6f}")
                else:
                    # GPS 연결이 없을 때 시뮬레이션
                    import random
                    with self.gps_lock:
                        self.current_gps = {
                            'lat': simulation_base_lat + random.uniform(-0.001, 0.001),
                            'lng': simulation_base_lng + random.uniform(-0.001, 0.001),
                            'timestamp': datetime.now().isoformat(),
                            'valid': False  # 시뮬레이션임을 표시
                        }
                
                time.sleep(1)  # 1초마다 업데이트
                
            except Exception as e:
                print(f"GPS 읽기 오류: {e}")
                time.sleep(1)
    
    def get_current_gps(self):
        """현재 GPS 데이터 반환"""
        with self.gps_lock:
            return self.current_gps.copy()
    
    def start_gps(self, stop_event):
        """GPS 수신 시작"""
        self.connect_gps()
        gps_thread = threading.Thread(target=self.gps_reader_thread, args=(stop_event,), daemon=True)
        gps_thread.start()
        return gps_thread
    
    def stop_gps(self):
        """GPS 수신 중지"""
        self.gps_running = False
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()




def test_send_files():
    file_paths = [
    "/Users/nunu/Documents/vidchunk/20250803134048.mp4",
    "/Users/nunu/Documents/vidchunk/20250803134058.mp4"]
    upload_url=UPLOAD_URL
    try:
        zip_buffer = io.BytesIO()
        file_names = []
        total_size_mb = 0        
        metadata = {
            'total_files': str(file_paths),
            'file_type': 'blackbox_video',
            'chunk_duration': '10',
            'format': 'mp4',
            'lat': '33.5072',
            'lng': '126.4938'
        }   

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED, compresslevel=COMPRESSION_LEVEL) as zip_file:
            for i, file_path in enumerate(file_paths):
                if not os.path.exists(file_path):
                    print(f"No such file: {os.path.basename(file_path)}")
                    continue
                
                file_size = os.path.getsize(file_path)
                file_size_mb = file_size / (1024 * 1024)
                total_size_mb += file_size_mb
                file_name = os.path.basename(file_path)

                zip_file.write(file_path, file_name)
                file_names.append(file_name)

        zip_buffer.seek(0)
        zip_data = zip_buffer.getvalue()
        zip_size_mb = len(zip_data) / (1024 * 1024)

        print(f"Compressed: {total_size_mb:.1f}MB → {zip_size_mb:.1f}MB")

        # files = {   
        #     'file': ('blackbox_videos.zip', zip_data, 'application/zip')  # 바이너리 데이터 + 파일명 + MIME 타입
        # }

        files = {"file": zip_data}
        data = {"meta": json.dumps(metadata, ensure_ascii=False)} 
        print(data)

        response = requests.post(upload_url, files=files, data=data)
        # 열린 파일들 정리
        for file_obj in files.values():
            if hasattr(file_obj[1], 'close'):
                file_obj[1].close()
        
        if response.status_code == 200:
            print("File upload success.")
            print(f"Response: {response.text[:200]}")
            return True
        else:
            print(f"File upload failed. (HTTP {response.status_code})")
            print(f"Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        print("Timeout")
        return False
    except requests.exceptions.ConnectionError:
        print("Connection error - Check server status.")
        return False
    except Exception as e:
        print(f"Unexpected exception: {str(e)}")
        return False
    finally:
        # 혹시 모를 파일 핸들 정리
        try:
            for file_obj in files.values():
                if hasattr(file_obj[1], 'close'):
                    file_obj[1].close()
        except:
            pass

def upload_video_files(file_paths: list, upload_url=None):
    if upload_url is None:
        upload_url = UPLOAD_URL
    """
    비디오 파일들을 서버에 한 번에 업로드 (메타데이터 포함)
    
    Args:
        file_paths: 업로드할 파일 경로들의 리스트
        upload_url: 업로드 서버 URL
    
    Returns:
        bool: 모든 파일이 성공적으로 업로드되면 True
    """
    print(f"\nStart File upload - {len(file_paths)} files.")
    print(f"Upload URL: {upload_url}")
    
    try:
        zip_buffer = io.BytesIO()
        file_names = []
        total_size_mb = 0
        metadata = {
            'total_files': str(file_paths),
            'file_type': 'blackbox_video',
            'chunk_duration': '10',
            'format': 'mp4'
        }   

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED, compresslevel=COMPRESSION_LEVEL) as zip_file:
            for i, file_path in enumerate(file_paths):
                if not os.path.exists(file_path):
                    print(f"No such file: {os.path.basename(file_path)}")
                    continue
                
                file_size = os.path.getsize(file_path)
                file_size_mb = file_size / (1024 * 1024)
                total_size_mb += file_size_mb
                file_name = os.path.basename(file_path)

                zip_file.write(file_path, file_name)
                file_names.append(file_name)

        zip_buffer.seek(0)
        zip_data = zip_buffer.getvalue()
        zip_size_mb = len(zip_data) / (1024 * 1024)

        print(f"Compressed: {total_size_mb:.1f}MB → {zip_size_mb:.1f}MB")

        # files = {   
        #     'file': ('blackbox_videos.zip', zip_data, 'application/zip')  # 바이너리 데이터 + 파일명 + MIME 타입
        # }

        files = {"file": zip_data}
        data = {"meta": json.dumps(metadata, ensure_ascii=False)} 


        response = requests.post(upload_url, files=files, data=data)
        # 열린 파일들 정리
        for file_obj in files.values():
            if hasattr(file_obj[1], 'close'):
                file_obj[1].close()
        
        if response.status_code == 200:
            print("File upload success.")
            print(f"Response: {response.text[:200]}")
            return True
        else:
            print(f"File upload failed. (HTTP {response.status_code})")
            print(f"Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        print("Timeout")
        return False
    except requests.exceptions.ConnectionError:
        print("Connection error - Check server status.")
        return False
    except Exception as e:
        print(f"Unexpected exception: {str(e)}")
        return False
    finally:
        # 혹시 모를 파일 핸들 정리
        try:
            for file_obj in files.values():
                if hasattr(file_obj[1], 'close'):
                    file_obj[1].close()
        except:
            pass

def get_valid_video_files(wakeup_time: datetime, window: int = WINDOW, wait_seconds=None):
    if wait_seconds is None:
        wait_seconds = WAIT_SECONDS
    """
    wakeup_time 기준으로 유효한 비디오 파일들을 반환
    
    Args:
        wakeup_time: 음성으로 "블랙박스" 호출한 datetime 객체
        window: 사용하지 않음 (호환성을 위해 유지)
        wait_seconds: 파일 완성 대기 시간 (기본 20초)
                     10초 파일 주기 + wakeup 이후 파일 완성 + 여유시간
    
    Returns:
        list: 유효한 비디오 파일 경로들의 리스트
             시간 차이 ≥5초: 4개 파일 (wakeup 이후 + wakeup 이전 3개)
             시간 차이 <5초: 3개 파일 (wakeup 이후 + wakeup 이전 2개)
    """
    # wakeup_time이 이미 문자열 형태로 출력되었으므로 여기서는 출력하지 않음
    
    # 파일 완성 대기 (wakeup 이후 파일까지 충분히 기다림)
    print(f"파일 완성 대기 중... ({wait_seconds}초)")
    time.sleep(wait_seconds)
    
    # 저장 디렉토리에서 모든 .mp4 파일 찾기
    all_files = list(Path(TARGET_DIR).glob("*.mp4"))
    
    # 파일명을 기준으로 시간 파싱 및 wakeup 시간 기준으로 분류
    pre_wakeup_files = []   # wakeup 이전에 생성된 파일들
    post_wakeup_files = []  # wakeup 이후에 생성된 파일들

    for file_path in all_files:
        # 파일명에서 확장자 제외하고 시간 부분만 추출
        file_time_str = file_path.stem

        try:
            # 파일명을 datetime 객체로 변환
            file_dt = datetime.strptime(file_time_str, FMT)

            # wakeup 시간과 비교하여 분류
            if file_dt < wakeup_time:
                # wakeup 이전 파일: (파일경로, 생성시간) 튜플로 저장
                pre_wakeup_files.append((file_path, file_dt))
            else:
                # wakeup 이후 파일: (파일경로, 생성시간) 튜플로 저장
                post_wakeup_files.append((file_path, file_dt))
                
        except ValueError:
            # 파일명이 시간 형식이 아닌 경우 스킵
            continue
    
    # wakeup 이전 파일들을 시간순으로 정렬 (최신순)
    pre_wakeup_files.sort(key=lambda x: x[1], reverse=True)
    
    # wakeup 이후 파일들을 시간순으로 정렬 (오래된 순)
    post_wakeup_files.sort(key=lambda x: x[1])
    
    # wakeup 이전 파일들 중에서 최대 3-4개 선택 (최신순)
    valid_pre_files = pre_wakeup_files[:4]
    for file_path, file_dt in valid_pre_files:
        print(f"이전 파일: {file_path.name}")
    
    # wakeup 이후 파일 중 첫 번째 파일 선택 (가장 빠른 것)
    valid_post_file = None
    if post_wakeup_files:
        valid_post_file = post_wakeup_files[0]
        print(f"이후 파일: {valid_post_file[0].name}")
    
    # 결과 조합
    if len(valid_pre_files) >= 3 and valid_post_file:
        # 가장 최근 wakeup 이전 파일과 wakeup 시간의 차이 계산
        latest_pre_file_time = valid_pre_files[0][1]
        time_diff = (wakeup_time - latest_pre_file_time).total_seconds()
        
        if time_diff >= 5:  # 5초 이상 차이나면
            # wakeup 이후 1개 + wakeup 이전 3개 = 총 4개 파일
            result_files = [valid_post_file] + valid_pre_files[:3]
            print(f"시간 차이 {time_diff:.1f}초 (≥5초) - 4개 파일 반환")
        else:  # 5초 미만 차이나면
            # wakeup 이후 1개 + wakeup 이전 2개 = 총 3개 파일
            result_files = [valid_post_file] + valid_pre_files[:2]
            print(f"시간 차이 {time_diff:.1f}초 (<5초) - 3개 파일 반환")
            
        return [str(f[0]) for f in result_files]
    
    all_files = []
    if valid_post_file:
        all_files.append(valid_post_file)
    all_files.extend(valid_pre_files)
    
    print(f"파일 부족 - {len(all_files)}개 파일 반환")
    return [str(f[0]) for f in all_files]

def on_wakeup():
    # 1) 호출 시각 기록
    now = datetime.now()
    print(f"[Wakeup]: {now.strftime(FMT)}")

    # 2) 전후 윈도우 내 파일 검색
    files = get_valid_video_files(now)
    if not files:
        print("No video files found")
        return

    # 3) 찾은 파일 목록 출력 혹은 후처리
    print("Found video files:")
    for f in files:
        print("  -", f)
    
    upload_video_files(files)

def audio_listener(stop_event: threading.Event):
    recognizer = sr.Recognizer()
    try:
        mic = sr.Microphone()
    except OSError as e:
        print(f"Microphone access error: {e}")
        stop_event.set()
        return

    # 주변 소음 레벨 세팅
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)

    trigger_phrases = TRIGGER_PHRASES

    def callback(recognizer, audio):
        try:
            text = recognizer.recognize_google(audio, language=VOICE_LANGUAGE)
            print(f"[VOICE] {text}")
            if any(phrase in text for phrase in trigger_phrases):
                on_wakeup()
        except sr.UnknownValueError:
            pass  # 인식 실패
        except sr.RequestError as e:
            print(f"request error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

    # 백그라운드로 계속 청취
    recognizer.listen_in_background(mic, callback)

    # stop_event가 세트되면 종료
    while not stop_event.is_set():
        time.sleep(0.1)

def video_recorder(stop_event: threading.Event):
    os.makedirs(TARGET_DIR, exist_ok=True)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Camera not opened")
        stop_event.set()
        return

    cap.set(cv2.CAP_PROP_FPS, VIDEO_FPS)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, VIDEO_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, VIDEO_HEIGHT)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'avc1'))

    fps = cap.get(cv2.CAP_PROP_FPS) or float(VIDEO_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')

    chunk_duration = CHUNK_DURATION  # seconds
    frames_per_chunk = int(fps * chunk_duration)

    frame_count = 0
    out = None

    try:
        while not stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                print("Frame read failed")
                break

            if frame_count % frames_per_chunk == 0:
                if out:
                    out.release()
                timestamp = datetime.now().strftime(FMT)
                filename = f"{timestamp}.mp4"
                filepath = os.path.join(TARGET_DIR, filename)
                out = cv2.VideoWriter(filepath, fourcc, fps, (width, height))
                print(f"[Recording] {filepath}")

            out.write(frame)
            frame_count += 1

            # cv2.imshow('Recording', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("User requested to stop")
                stop_event.set()
                break

    finally:
        if out:
            out.release()
        cap.release()
        cv2.destroyAllWindows()

def main():
    # test_send_files()
    # test_files = [
    # "/Users/nunu/Documents/vidchunk/20250803134048.mp4",
    # "/Users/nunu/Documents/vidchunk/20250803134058.mp4", 
    # "/Users/nunu/Documents/vidchunk/20250803134108.mp4",
    # "/Users/nunu/Documents/vidchunk/20250803134118.mp4"]
    # meta_data = {
    #     "title": "테스트 영상",
    #     "description": "API 테스트용 영상입니다",
    #     "duration": "120초"
    # }
    # with open("/Users/nunu/Documents/vidchunk/20250803134118.mp4", "rb") as f:   
    #     files = {"file": f}
    #     data = {"meta": str(meta_data)}        
    #     response = requests.post("http://192.168.1.129:80ß00/upload-movie", files=files, data=data)


    # upload_video_files(test_files)

    print(f"Save directory: {TARGET_DIR}")
    stop_event = threading.Event()

    try:
        # 1) 음성 인식 스레드 시작
        audio_thread = threading.Thread(target=audio_listener, args=(stop_event,), daemon=True)
        audio_thread.start()

        # 2) 영상 녹화 (메인 스레드)
        video_recorder(stop_event)

    except KeyboardInterrupt:
        print("\nProgram is shutting down...")
    finally:
        # 3) 종료 대기
        stop_event.set()
        if 'audio_thread' in locals():
            audio_thread.join(timeout=2)
        print("Program is shut down")

if __name__ == "__main__":
    main()
