# MCP Client - Traffic Violation Report System

MCP(Model Context Protocol) 클라이언트를 사용하여 교통법규 위반 영상을 분석하고 안전신문고 신고서를 자동 생성하는 시스템입니다.

## 주요 기능

- **ZIP 파일 처리**: MP4 영상이 포함된 ZIP 파일 업로드 및 분석
- **MCP 도구 연동**: 다양한 MCP 서버의 도구를 순차적으로 호출
- **AI 분석**: Claude를 통한 영상 내용과 STT 데이터 종합 분석
- **신고서 자동 생성**: 안전신문고 형식의 신고서 자동 작성

## 파일 구조

```
mcp_client/
├── main.py           # 메인 FastAPI 서버
├── report_test.py    # API 테스트 스크립트
├── mcp.json         # MCP 서버 설정 파일
├── pyproject.toml   # 프로젝트 설정 및 의존성
└── README.md        # 이 문서
```

## 설치 및 실행

### 1. 가상환경 설정
```bash
cd mcp_client
uv venv
```

### 2. 의존성 설치
```bash
uv sync
```

### 3. 환경 변수 설정
`.env` 파일을 생성하고 Anthropic API 키를 설정:
```env
ANTHROPIC_API_KEY=your_api_key_here
```

### 4. MCP 서버 실행
테스트용 MCP 서버 실행:
```bash
cd ../mcp_server_test
uv run python server.py
```

### 5. 메인 서버 실행
```bash
cd mcp_client
uv run python main.py
```

서버는 `http://localhost:8001`에서 실행됩니다.

## API 사용법

### POST `/report`
교통법규 위반 영상 분석 및 신고서 생성

**요청 파라미터:**
- `file`: ZIP 파일 (MP4 영상들 포함)
- `meta`: 메타데이터 (JSON 문자열 형태)
- `stt`: Speech-to-Text 내용 (문자열)

**응답 예시:**
```json
{
  "status": "success",
  "message": "Report vehicle completed successfully",
  "filename": "videos.zip",
  "report_result": {
    "status": "success",
    "response": "안전신문고 신고서가 작성되었습니다...",
    "tools_called": ["get_address_from_geocoding", "report_traffic_violation"],
    "agent_steps": 2
  }
}
```

### 기타 엔드포인트
- `GET /`: 서버 상태 확인
- `GET /mcp/status`: MCP 연결 상태 및 사용 가능한 도구 목록

## 테스트

### 자동 테스트 실행
```bash
uv run python report_test.py
```

테스트 스크립트는 다음 작업을 수행합니다:
1. 샘플 ZIP 파일 생성 (더미 MP4 파일들 포함)
2. 테스트 메타데이터 및 STT 데이터 준비
3. `/report` 엔드포인트에 POST 요청 전송
4. 응답 결과를 간결하게 표시

### 테스트 출력 예시
```
🚀 MCP Client Report API Test
==================================================
🏥 Server is healthy!

==================================================
📦 Creating sample ZIP file...
📡 Sending request to http://localhost:8001/report
📊 Status: 200
✅ Request successful!

📝 User Request: 차량번호 12가3456 차량이 신호를 위반하여...
🔧 Tools Called: get_address_from_geocoding, report_traffic_violation

🤖 Final Response:
============================================================
안전신문고 교통법규 위반 신고서가 성공적으로 작성되었습니다...
============================================================
```

## MCP 서버 설정

### 현재 설정 (mcp.json)
```json
{
  "mcpServers": {
    "report": {
      "command": "uv",
      "args": [
        "--directory",
        "../mcp_server_test",
        "run",
        "server.py"
      ],
      "transport": "stdio"
    }
  }
} 
```

### ⚠️ 중요: 실제 운영 환경 설정

현재 `mcp_server_test` 폴더의 서버는 **테스트용**입니다. 

**실제 운영 환경**에서는 다음 작업이 필요합니다:

1. **실제 MCP 서버 구축**: 
   - 실제 안전신문고 API 연동
   - 실제 지오코딩 서비스 연동
   - 데이터베이스 연결 등

2. **mcp.json 수정**:
   ```json
   {
     "mcpServers": {
       "safety-report-server": {
         "command": "path/to/actual/server",
         "args": ["--config", "production.json"],
         "transport": "stdio"
       },
       "geocoding-server": {
         "command": "path/to/geocoding/server",
         "args": ["--api-key", "real_api_key"],
         "transport": "stdio"
       }
     }
   }
   ```

3. **서버 재시작**:
   새로운 MCP 설정이 적용되도록 main.py 재시작

## 시스템 아키텍처

```
[Client] → [FastAPI Server] → [MCP Client] → [MCP Servers]
                ↓
         [LangChain Agent] → [Claude API]
                ↓
         [Response Processing] → [Client]
```

1. **파일 업로드**: ZIP 파일이 업로드되고 MP4 파일들이 추출됨
2. **MCP 연결**: 설정된 MCP 서버들과 연결하여 도구 목록 획득
3. **Agent 실행**: LangChain Agent가 순차적으로 MCP 도구들을 호출
4. **AI 분석**: Claude가 영상 정보와 STT를 종합하여 신고서 생성
5. **결과 반환**: 최종 신고서가 클라이언트에게 반환

## 문제 해결

### 서버 연결 실패
```bash
# MCP 서버 상태 확인
curl http://localhost:8001/mcp/status

# 서버 로그 확인
uv run python main.py  # 로그 출력 확인
```

### MCP 도구 인식 실패
1. `mcp.json` 파일 경로 확인
2. MCP 서버가 실행 중인지 확인
3. 서버 재시작 후 다시 시도

### API 키 오류
`.env` 파일에 올바른 `ANTHROPIC_API_KEY`가 설정되어 있는지 확인

## 개발자 정보

- **개발 환경**: Python 3.10+, UV, FastAPI
- **주요 라이브러리**: langchain, langchain-anthropic, langchain-mcp-adapters
- **테스트 도구**: httpx, pytest (선택사항)

## 라이선스

This project is for hackathon purposes.