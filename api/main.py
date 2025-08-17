"""불법 차량 신고 MCP 클라이언트 애플리케이션.

이 모듈은 음성 명령으로 전달된 불법 차량 신고 요청을 처리하는 FastAPI 애플리케이션입니다.
STT로 변환된 텍스트와 영상 파일, 메타데이터를 분석하여 안전신문고에 자동으로 신고서를 작성합니다.

주요 기능:
- ZIP 파일에 포함된 MP4 영상 분석
- GPS 좌표를 활용한 위치 정보 추출  
- MCP 도구를 활용한 지능적 신고서 작성
- Anthropic API를 통한 자연어 처리
"""

from contextlib import asynccontextmanager
from typing import Annotated
from fastapi import FastAPI
import uvicorn

from config.config import Config
from services.mcp_service import MCPService
from routers import report, health


@asynccontextmanager
async def lifespan(
    app: Annotated[FastAPI, "FastAPI 애플리케이션 인스턴스"]
) -> Annotated[None, "애플리케이션 생명주기 컨텍스트"]:
    """FastAPI 애플리케이션의 시작과 종료를 관리하는 생명주기 컨텍스트 매니저.
    
    애플리케이션 시작 시 MCP 서버 설정을 로드하고 연결을 초기화합니다.
    종료 시에는 정리 작업을 수행합니다.
    
    Parameters
    ----------
    app : FastAPI
        FastAPI 애플리케이션 인스턴스
        
    Yields
    ------
    None
        애플리케이션이 실행 중인 동안 제어권을 양보
        
    Examples
    --------
    >>> app = FastAPI(lifespan=lifespan)
    >>> # 애플리케이션 시작 시 MCP 서버 초기화
    >>> # 애플리케이션 종료 시 정리 작업 수행
    """
    # Startup
    print("Starting MCP Client API...")
    mcp_server_config = Config.load_mcp_config()
    await MCPService.initialize(mcp_server_config)
    print("Application startup completed")

    yield

    # Shutdown
    print("Shutting down application...")
    print("Application shutdown completed")


# FastAPI 애플리케이션 인스턴스 생성
app = FastAPI(
    title="MCP Client API",
    version="1.0.0",
    description="""
    불법 차량 신고를 위한 MCP 클라이언트 API
    
    이 API는 음성 명령과 영상 파일을 받아 자동으로 안전신문고 신고서를 작성합니다.
    
    ## 주요 기능
    
    * **영상 분석**: ZIP 파일에 포함된 MP4 영상들을 자동 추출 및 분석
    * **위치 추출**: GPS 메타데이터를 통한 정확한 사고 위치 확인
    * **자동 신고**: MCP 도구를 활용한 지능적 신고서 자동 작성
    * **상태 모니터링**: MCP 서버 연결 상태 및 도구 현황 실시간 확인
    """,
    lifespan=lifespan,
)

# 라우터 등록
app.include_router(health.router, tags=["Health Check"])
app.include_router(report.router, tags=["Report"])


def main() -> None:
    """애플리케이션의 메인 진입점.
    
    uvicorn 서버를 사용하여 FastAPI 애플리케이션을 실행합니다.
    기본적으로 모든 인터페이스(0.0.0.0)의 8001번 포트에서 실행됩니다.
    
    Examples
    --------
    >>> python main.py
    # 또는
    >>> uvicorn main:app --host 0.0.0.0 --port 8001
    """
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info",
        access_log=True,
    )


if __name__ == "__main__":
    main()