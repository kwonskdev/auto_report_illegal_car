#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VS Code용 Anthropic API 차량신고 시스템
Claude Desktop 없이 직접 API 호출로 동작
"""

import os
import json
import asyncio
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List
import subprocess
import tempfile
import sys
from pathlib import Path
from env import ANTHROPIC_API_KEY

# Anthropic 라이브러리
from anthropic import Anthropic

# 기존 report.py의 ReportInfo 클래스 재사용
@dataclass
class ReportInfo:
    title: str
    contents: str
    violation_type: str  # ex. "10"
    file_name: str       # ex. "temp.mp4"  
    address_query: str   # ex. "판교역로 166"
    report_datetime: datetime

class ViolationClassifier:
    """위반 유형 분류기"""
    
    VIOLATION_TYPES = {
        "02": "교통위반",
        "03": "이륜차 위반", 
        "10": "난폭/보복운전",
        "05": "버스 전용차로 위반(고속도로 제외)",
        "06": "번호판 규정 위반",
        "07": "불법등화, 반사판 가림 손상",
        "08": "불법 튜닝, 해체, 조작",
        "09": "기타 자동차 안전기준 위반"
    }
    
    @classmethod
    def classify_violation(cls, description: str) -> str:
        """신고 내용을 분석하여 위반 유형을 분류"""
        description_lower = description.lower()
        
        # 키워드 기반 분류 로직
        keywords_map = {
            "10": ["난폭", "보복", "끼어들", "급차선", "위협", "클랙슨", "욕설", "추월", "급정거", "급출발"],
            "02": ["신호위반", "속도위반", "정지선", "횡단보도", "과속", "신호등"],
            "03": ["오토바이", "이륜차", "스쿠터", "배달", "헬멧"],
            "05": ["버스차로", "전용차로", "BUS"],
            "06": ["번호판", "가림", "훼손"],
            "07": ["전조등", "후미등", "반사판"],
            "08": ["튜닝", "불법개조"],
            "09": ["기타"]
        }
        
        for violation_code, keywords in keywords_map.items():
            for keyword in keywords:
                if keyword in description_lower:
                    return violation_code
        
        return "10"  # 기본값: 난폭/보복운전

class VehicleReportAgent:
    """Anthropic API를 사용한 차량 신고 에이전트"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: Anthropic API 키 (없으면 환경변수에서 가져옴)
        """
        self.api_key = ANTHROPIC_API_KEY
        
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY가 설정되지 않았습니다. 환경변수를 확인하세요.")
        
        self.client = Anthropic(api_key=self.api_key)
        self.tools = self._setup_tools()
    
    def _setup_tools(self) -> List[Dict[str, Any]]:
        """Claude가 사용할 수 있는 도구 정의"""
        tools = [
            {
                "name": "submit_vehicle_report",
                "description": "차량 위반 행위를 자동으로 신고합니다",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "위반 행위 설명"
                        },
                        "location": {
                            "type": "string", 
                            "description": "발생 위치"
                        },
                        "video_file": {
                            "type": "string",
                            "description": "증빙 영상 파일명",
                            "default": "temp.mp4"
                        },
                        "datetime_str": {
                            "type": "string",
                            "description": "발생 일시 (YYYY-MM-DD HH:MM 형식)",
                            "default": None
                        }
                    },
                    "required": ["description", "location"]
                }
            },
            # {
            #     "name": "classify_violation_type",
            #     "description": "위반 행위를 분석하여 적절한 위반 유형을 분류합니다",
            #     "input_schema": {
            #         "type": "object",
            #         "properties": {
            #             "description": {
            #                 "type": "string",
            #                 "description": "위반 행위 설명"
            #             }
            #         },
            #         "required": ["description"]
            #     }
            # }
        ]
        
        print(f"🛠️  도구 설정 완료: {[tool['name'] for tool in tools]}")
        return tools
    
    def _execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:

        print(f"도구 실행 요청: '{tool_name}' - 파라미터: {parameters}")
        
        if tool_name == "submit_vehicle_report":
            print("submit_vehicle_report 도구 실행")
            return self._submit_report(parameters)
        elif tool_name == "classify_violation_type":
            print("classify_violation_type 도구 실행")
            return self._classify_violation(parameters)
        else:
            print(f"사용 가능한 도구: submit_vehicle_report, classify_violation_type")
            return {"error": f"Unknown tool: {tool_name}"}
    
    def _classify_violation(self, params: Dict[str, Any]) -> Dict[str, Any]:
    
        description = params["description"]
        violation_code = ViolationClassifier.classify_violation(description)
        violation_name = ViolationClassifier.VIOLATION_TYPES[violation_code]
        
        return {
            "violation_code": violation_code,
            "violation_name": violation_name,
            "description": description
        }
    
    def _submit_report(self, params: Dict[str, Any]) -> Dict[str, Any]:
       
        try:
            description = params["description"]
            location = params["location"]
            video_file = params.get("video_file", "temp.mp4")
            datetime_str = params.get("datetime_str")
            
            # 날짜 시간 처리
            if datetime_str:
                try:
                    report_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
                except:
                    report_datetime = datetime.now()
            else:
                report_datetime = datetime.now()
            
            # 위반 유형 자동 분류
            violation_type = ViolationClassifier.classify_violation(description)
            violation_name = ViolationClassifier.VIOLATION_TYPES[violation_type]
            
            # 제목 및 내용 생성
            title = f"{violation_name} 신고"
            contents = f"위반 행위: {description}\n발생 위치: {location}\n발생 일시: {report_datetime.strftime('%Y-%m-%d %H:%M')}"
            
            # ReportInfo 객체 생성
            report_info = ReportInfo(
                title=title,
                contents=contents,
                violation_type=violation_type,
                file_name=video_file,
                address_query=location,
                report_datetime=report_datetime
            )
            
            # report.py 실행
            result = self._execute_report_script(report_info)
            
            return {
                "success": True,
                "title": title,
                "violation_type": violation_type,
                "violation_name": violation_name,
                "location": location,
                "datetime": report_datetime.strftime('%Y-%m-%d %H:%M'),
                "result": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
        
    def _execute_report_script(self, report_info: ReportInfo) -> str:
        
        try:
            # 문자열 이스케이프 처리
            def escape_string(s):
                return s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')
            
            # 이스케이프 처리된 문자열들
            title_escaped = escape_string(report_info.title)
            contents_escaped = escape_string(report_info.contents)
            address_escaped = escape_string(report_info.address_query)
            
            # Windows 경로 처리 (백슬래시를 슬래시로 변경 또는 이스케이프)
            current_path = os.getcwd().replace('\\', '/')
            
            # 임시 실행 스크립트 생성
            script_content = f"""# -*- coding: utf-8 -*-
import sys
import os
sys.path.append(r'{os.getcwd()}')

from report import ReportInfo, run_report
from datetime import datetime

# 신고 정보 설정
report_info = ReportInfo(
    title="{title_escaped}",
    contents="{contents_escaped}",
    violation_type="{report_info.violation_type}",
    file_name="{report_info.file_name}",
    address_query="{address_escaped}",
    report_datetime=datetime({report_info.report_datetime.year}, {report_info.report_datetime.month}, {report_info.report_datetime.day}, {report_info.report_datetime.hour}, {report_info.report_datetime.minute})
)

# 신고 실행
try:
    run_report(report_info)
    print("신고 처리 완료")
except Exception as e:
    print(f"신고 처리 중 오류: {{e}}")
    """
            
            # UTF-8 인코딩으로 임시 파일 저장
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
                f.write(script_content)
                temp_script_path = f.name
            
            print(f"📝 임시 스크립트 생성: {temp_script_path}")
            print(f"🔍 경로 확인: {os.getcwd()}")
            
            # 생성된 스크립트 내용 확인 (디버깅용)
            print("🔍 생성된 스크립트 첫 5줄:")
            lines = script_content.split('\n')
            for i, line in enumerate(lines[:5]):
                print(f"   {i+1}: '{line}'")
            
            # 백그라운드에서 스크립트 실행
            subprocess.Popen([sys.executable, temp_script_path])
            
            # 임시 파일 정리 (약간의 지연 후)
            import threading
            def cleanup():
                import time
                time.sleep(5)
                try:
                    os.unlink(temp_script_path)
                    print(f"🗑️  임시 파일 정리 완료")
                except:
                    pass
            
            threading.Thread(target=cleanup).start()
            
            return "신고 프로세스가 백그라운드에서 시작되었습니다."
            
        except Exception as e:
            print(f"💥 스크립트 실행 오류: {e}")
            return f"스크립트 실행 오류: {str(e)}"
    
    def process_request(self, user_message: str) -> str:
       
        system_prompt = f"""
당신은 차량 위반 신고를 도와주는 AI 어시스턴트입니다.

사용 가능한 위반 유형:
- 02: 교통위반 (신고위반, 과속 등)
- 03: 이륜차 위반 (헬멧 미착용 등)
- 10: 난폭/보복운전 (끼어들기, 급차선변경 등)
- 05: 버스 전용차로 위반
- 06: 번호판 규정 위반
- 07: 불법등화, 반사판 관련
- 08: 불법 튜닝
- 09: 기타 안전기준 위반

바로 submit_vehicle_report 도구 사용해서 진행해줘.
"""

        try:
            messages = [{"role": "user", "content": user_message}]
            
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                system=system_prompt,
                tools=self.tools,
                messages=messages
            )
            
            # 응답 처리
            if response.content:
                # 도구 사용이 있는지 확인
                tool_calls = [content for content in response.content if content.type == "tool_use"]
                print(tool_calls)
                text_content = [content for content in response.content if content.type == "text"]
                
                if tool_calls:
                    # 도구 실행 및 결과 처리
                    messages.append({"role": "assistant", "content": response.content})
                    
                    # 각 도구 호출에 대한 결과 생성
                    tool_results = []
                    for tool_call in tool_calls:
                        tool_result = self._execute_tool(tool_call.name, tool_call.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_call.id,
                            "content": json.dumps(tool_result, ensure_ascii=False)
                        })
                    
                    # 도구 결과를 메시지에 추가
                    messages.append({"role": "user", "content": tool_results})
                    
                    # 최종 응답 생성
                    final_response = self.client.messages.create(
                        model="claude-3-5-sonnet-20241022",
                        max_tokens=500,
                        system="도구 실행 결과를 바탕으로 사용자에게 친근하고 명확한 응답을 해주세요.",
                        messages=messages
                    )
                    
                    if final_response.content and final_response.content[0].type == "text":
                        return final_response.content[0].text
                    else:
                        # 도구 실행 결과만으로 응답 생성
                        if tool_results:
                            result_summary = []
                            for result in tool_results:
                                result_data = json.loads(result["content"])
                                if result_data.get("success"):
                                    result_summary.append(f" {result_data.get('violation_name', '신고')} 처리 완료")
                                    result_summary.append(f" 위치: {result_data.get('location', 'N/A')}")
                                    result_summary.append(f" 일시: {result_data.get('datetime', 'N/A')}")
                                    result_summary.append(f" 처리 상태: {result_data.get('result', 'N/A')}")
                                else:
                                    result_summary.append(f" 오류: {result_data.get('error', '알 수 없는 오류')}")
                            
                            return "\n".join(result_summary)
                        else:
                            return "신고 처리가 완료되었습니다."
                
                # 일반 텍스트 응답
                elif text_content:
                    return text_content[0].text
            
            return "응답을 생성할 수 없습니다."
            
        except Exception as e:
            return f"오류가 발생했습니다: {str(e)}"

def main():
    """메인 실행 함수"""
    print("🚗 차량신고 AI 어시스턴트 시작!")
    print("ANTHROPIC_API_KEY 환경변수가 설정되어 있는지 확인하세요.\n")
    
    try:
        agent = VehicleReportAgent()
        print("✅ AI 어시스턴트가 준비되었습니다!")
        print("예시: '차가 갑자기 끼어들었어. 판교역로 166에서 신고해줘'\n")
        
        while True:
            user_input = input("\n💬 신고할 내용을 말씀해주세요 (종료: 'quit'): ")
            
            if user_input.lower() in ['quit', 'exit', '종료']:
                print("👋 프로그램을 종료합니다.")
                break
                
            if not user_input.strip():
                continue
                
            print("\n🤖 처리 중...")
            response = agent.process_request(user_input)
            print(f"\n📝 응답: {response}")
            
    except ValueError as e:
        print(f"❌ 설정 오류: {e}")
        print("ANTHROPIC_API_KEY 환경변수를 설정해주세요.")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    main()