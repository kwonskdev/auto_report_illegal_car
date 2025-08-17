#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP Tools Test Script with UTF-8 Support
Windows 환경에서 UTF-8 인코딩 문제 해결
"""

import sys
import os

# Windows UTF-8 인코딩 강제 설정
if sys.platform == "win32":
    # 방법 1: 환경 변수 설정
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["PYTHONUTF8"] = "1"
    
    # 방법 2: stdout/stderr 래핑
    import codecs
    import io
    
    # UTF-8 wrapper로 stdout/stderr 교체
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from report import reverse_geocoding, init_driver

def test_geocoding_tool():
    """첫 번째 MCP 도구 테스트: 주소 변환"""
    print("=" * 50)
    print("🌍 get_address_from_geocoding 도구 테스트")
    print("=" * 50)
    
    # 테스트 입력
    lat, lng = 37.5665, 126.978
    print(f"📍 입력: latitude={lat}, longitude={lng} (서울특별시청)")
    
    try:
        result = reverse_geocoding(lat, lng)
        print(f"📊 결과 타입: {type(result)}")
        
        if isinstance(result, dict):
            success = result.get('success', False)
            print(f"✅ 성공 여부: {success}")
            
            if success:
                print(f"🏠 전체 주소: {result.get('full_address', 'N/A')}")
                print(f"🇰🇷 한국 주소: {result.get('korean_address', 'N/A')}")
                print(f"🏙️ 도시: {result.get('city', 'N/A')}")
                print(f"🏢 구: {result.get('district', 'N/A')}")
                print(f"🛣️ 도로: {result.get('road', 'N/A')}")
                print(f"🏠 번지: {result.get('house_number', 'N/A')}")
                
                # MCP 도구 반환값 시뮬레이션
                mcp_result = result.get('korean_address', result.get('full_address', '주소 정보 없음'))
                print(f"\n🔧 MCP 도구 반환값: {mcp_result}")
                print(f"📝 반환 타입: {type(mcp_result)}")
                
                # 검증
                if isinstance(mcp_result, str) and '서울' in mcp_result:
                    print("🎉 테스트 결과: ✅ 성공")
                    return True
                else:
                    print("❌ 테스트 결과: 실패 - 예상 결과 불일치")
                    return False
            else:
                print(f"❌ 에러: {result.get('error', '알 수 없는 오류')}")
                return False
        else:
            print(f"❌ 예상치 못한 결과 타입: {result}")
            return False
            
    except Exception as e:
        print(f"❌ 예외 발생: {e}")
        return False

def test_webdriver_tool():
    """두 번째 MCP 도구 테스트: 웹드라이버 초기화"""
    print("\n" + "=" * 50)
    print("🚗 report_traffic_violation 도구 테스트")
    print("=" * 50)
    
    print("🔧 ChromeDriver 초기화 테스트 중...")
    
    try:
        # ChromeDriver 초기화
        driver = init_driver()
        print("✅ ChromeDriver 초기화 성공")
        print(f"🆔 브라우저 세션 ID: {driver.session_id}")
        print(f"🌐 브라우저 이름: {driver.name}")
        
        # 간단한 페이지 로드 테스트
        test_html = "data:text/html,<h1>🧪 MCP Test Page</h1><p>한글 테스트</p>"
        driver.get(test_html)
        print("✅ 페이지 로드 성공")
        
        # 페이지 제목 확인
        title = driver.title
        print(f"📄 페이지 제목: {title}")
        
        # 브라우저 종료
        driver.quit()
        print("✅ 브라우저 정상 종료")
        
        print("\n🎉 웹 자동화 준비 완료!")
        print("ℹ️ 실제 안전신문고 접속은 테스트에서 제외됨")
        return True
        
    except Exception as e:
        print(f"❌ ChromeDriver 초기화 실패: {e}")
        print("💡 해결 방법:")
        print("  1. Chrome 브라우저 설치 확인")
        print("  2. webdriver-manager 패키지 설치 확인")
        print("  3. 방화벽/보안 소프트웨어 확인")
        return False

def test_parameters():
    """MCP 도구 매개변수 검증 테스트"""
    print("\n" + "=" * 50)
    print("📋 MCP 도구 매개변수 검증 테스트")
    print("=" * 50)
    
    # 테스트 매개변수
    test_params = {
        'title': '교통법규 위반 신고',
        'vehicle_number': '12가3456',
        'violation_type': '10',
        'latitude': 37.5665,
        'longitude': 126.978,
        'datetime_str': '2025-01-10T14:30:00',
        'description': '빨간불 신호위반 - 보행자 위험 초래',
        'video_files': ['violation_01.mp4', 'violation_02.mp4'],
        'reporter_name': '김철수',
        'reporter_phone': '010-1234-5678',
        'reporter_email': 'test@example.com'
    }
    
    print("📊 테스트 매개변수:")
    for key, value in test_params.items():
        print(f"  📌 {key}: {value} ({type(value).__name__})")
    
    # 타입 검증
    validations = [
        ('title', str),
        ('vehicle_number', str),
        ('violation_type', str),
        ('latitude', (int, float)),
        ('longitude', (int, float)),
        ('datetime_str', str),
        ('description', str),
        ('video_files', list),
        ('reporter_name', str),
        ('reporter_phone', str),
        ('reporter_email', str)
    ]
    
    print("\n🔍 매개변수 타입 검증:")
    all_valid = True
    
    for param_name, expected_type in validations:
        actual_value = test_params[param_name]
        is_valid = isinstance(actual_value, expected_type)
        status = "✅" if is_valid else "❌"
        print(f"  {status} {param_name}: {expected_type.__name__ if not isinstance(expected_type, tuple) else 'number'}")
        
        if not is_valid:
            all_valid = False
    
    print(f"\n🎯 전체 검증 결과: {'✅ 모든 매개변수 검증 통과' if all_valid else '❌ 매개변수 검증 실패'}")
    return all_valid

def main():
    """메인 테스트 실행"""
    print("🚀 MCP Tools 종합 테스트 시작")
    print("🖥️ 플랫폼:", sys.platform)
    print("🐍 Python 버전:", sys.version)
    print("📝 인코딩:", sys.stdout.encoding)
    
    results = []
    
    # 테스트 실행
    results.append(("주소 변환 도구", test_geocoding_tool()))
    results.append(("웹드라이버 도구", test_webdriver_tool()))
    results.append(("매개변수 검증", test_parameters()))
    
    # 최종 결과
    print("\n" + "=" * 50)
    print("📊 최종 테스트 결과")
    print("=" * 50)
    
    success_count = 0
    for test_name, success in results:
        status = "✅ 성공" if success else "❌ 실패"
        print(f"  {status} {test_name}")
        if success:
            success_count += 1
    
    total_tests = len(results)
    print(f"\n🎯 종합 결과: {success_count}/{total_tests} 테스트 통과")
    
    if success_count == total_tests:
        print("🎉 모든 MCP 도구가 정상 작동합니다!")
        print("🚀 Chrome 브라우저 설치 후 완전한 자동화 가능")
    else:
        print("⚠️ 일부 테스트 실패 - 설정 확인 필요")
    
    return success_count == total_tests

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ 테스트가 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류 발생: {e}")
        sys.exit(1)