import requests

# 서버 URL
SERVER_URL = "http://127.0.0.1:8000/upload-movie"

# 테스트용 더미 파일 생성
def create_dummy_file():
    with open("test_video.mp4", "wb") as f:
        f.write(b"dummy video data for testing")
    return "test_video.mp4"

# 파일 업로드 테스트
def test_upload():
    # 더미 파일 생성
    file_path = create_dummy_file()
    
    # multipart/form-data로 전송
    files = {
        'binary': ('test_video.mp4', open(file_path, 'rb'), 'application/octet-stream'),
        'meta': (None, 'test_meta_data')
    }
    
    try:
        response = requests.post(SERVER_URL, files=files)
        
        if response.status_code == 200:
            print("✅ 업로드 성공!")
            print(response.json())
        else:
            print(f"❌ 업로드 실패: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ 오류: {e}")
    finally:
        files['binary'][1].close()

if __name__ == "__main__":
    test_upload()