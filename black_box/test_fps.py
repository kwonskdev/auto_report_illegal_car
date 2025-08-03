import cv2
import time

def test_camera_fps():
    """카메라의 실제 FPS를 정확히 측정"""
    cap = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)
    
    if not cap.isOpened():
        print("카메라를 열 수 없습니다.")
        return
    
    # 카메라 FPS 설정 시도
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    reported_fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"카메라 설정: {width}x{height}")
    print(f"설정된 FPS: {reported_fps}")
    
    # 실제 FPS 측정 (더 정확한 방법)
    print("\n100프레임으로 실제 FPS 측정 중...")
    
    frame_count = 0
    start_time = time.time()
    
    for i in range(100):
        ret, frame = cap.read()
        if ret:
            frame_count += 1
        
        if i % 10 == 0:
            elapsed = time.time() - start_time
            current_fps = (i + 1) / elapsed if elapsed > 0 else 0
            print(f"  {i+1}프레임: {current_fps:.2f} FPS")
    
    total_time = time.time() - start_time
    actual_fps = frame_count / total_time
    
    print(f"\n결과:")
    print(f"총 프레임: {frame_count}")
    print(f"총 시간: {total_time:.2f}초")
    print(f"실제 FPS: {actual_fps:.2f}")
    print(f"권장 녹화 FPS: {min(actual_fps, 30):.2f}")
    
    cap.release()
    
    return actual_fps

if __name__ == "__main__":
    test_camera_fps()