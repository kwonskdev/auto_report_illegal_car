import requests
import json
import time

def reverse_geocoding(lat, lng):
    """
    OpenStreetMap Nominatim을 사용한 무료 역지오코딩
    API 키가 필요하지 않음
    
    Args:
        lat (float): 위도
        lng (float): 경도
    
    Returns:
        dict: 주소 정보 또는 에러 메시지
    """
    url = "https://nominatim.openstreetmap.org/reverse"
    
    params = {
        "lat": lat,
        "lon": lng,
        "format": "json",
        "accept-language": "ko,en",  # 한국어 우선, 영어 보조
        "addressdetails": 1,
        "zoom": 18  # 상세한 주소 정보
    }
    
    headers = {
        "User-Agent": "ReverseGeocodingApp/1.0 (ij.park.94@gmail.com)"  # 실제 이메일로 변경 권장
    }
    
    try:
        # Nominatim은 초당 1회 요청 제한이 있으므로 잠시 대기
        time.sleep(1)
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if 'display_name' in data:
            address = data.get('address', {})
            
            # 한국 주소 형태로 정리
            result = {
                'success': True,
                'full_address': data['display_name'],
                'country': address.get('country', ''),
                'state': address.get('state', ''),  # 시/도
                'city': address.get('city', '') or address.get('county', ''),  # 시/군
                'district': address.get('city_district', '') or address.get('borough', ''),  # 구
                'neighbourhood': address.get('neighbourhood', '') or address.get('suburb', ''),  # 동
                'road': address.get('road', ''),  # 도로명
                'house_number': address.get('house_number', ''),  # 건물번호
                'building': address.get('building', ''),  # 건물명
                'postcode': address.get('postcode', ''),  # 우편번호
                'coordinates': {
                    'lat': float(data.get('lat', lat)),
                    'lng': float(data.get('lon', lng))
                }
            }
            
            # 한국 주소 형태로 재구성
            korean_address_parts = []
            if result['country']: korean_address_parts.append(result['country'])
            # if result['state']: korean_address_parts.append(result['state'])
            if result['city']: korean_address_parts.append(result['city'])
            if result['district']: korean_address_parts.append(result['district'])
            # if result['neighbourhood']: korean_address_parts.append(result['neighbourhood'])
            if result['road']: korean_address_parts.append(result['road'])
            if result['house_number']: korean_address_parts.append(result['house_number'])
            
            result['korean_address'] = ' '.join(korean_address_parts)
            
            return result
        
        return {
            'success': False,
            'error': '해당 좌표의 주소를 찾을 수 없습니다.'
        }
        
    except requests.exceptions.Timeout:
        return {
            'success': False,
            'error': '요청 시간이 초과되었습니다.'
        }
    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'error': f'API 요청 실패: {str(e)}'
        }
    except json.JSONDecodeError:
        return {
            'success': False,
            'error': '응답 데이터를 파싱할 수 없습니다.'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'예상치 못한 오류: {str(e)}'
        }


 # 사용 예제
def main():
    print("🌍 무료 역지오코딩 서비스 (Nominatim)")
    print("=" * 50)
    
    # 테스트 좌표 (명동 일대)
    lat = 37.55667
    lng = 126.92361
    
    print(f"📍 좌표: 위도 {lat}, 경도 {lng}")
    print("주소 조회 중...")
    
    # 역지오코딩 실행
    result = reverse_geocoding(lat, lng)
    
    if result['success']:
        print("\n✅ 조회 성공!")
        print(f"🏠 전체 주소: {result['full_address']}")
        print(f"🇰🇷 한국식 주소: {result['korean_address']}")
        # print(f"🏢 도로명: {result['road']}")
        # print(f"🏘️  동네: {result['neighbourhood']}")
        # print(f"📮 우편번호: {result['postcode']}")
        
        # print("\n📊 상세 정보:")
        # for key, value in result.items():
        #     if key not in ['success', 'full_address', 'korean_address'] and value:
        #         print(f"  {key}: {value}")
    else:
        print(f"\n❌ 조회 실패: {result['error']}")
    
if __name__ == "__main__":
    main()