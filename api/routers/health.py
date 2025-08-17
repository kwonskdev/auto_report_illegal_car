"""헬스체크 및 상태 확인 API 라우터 모듈.

이 모듈은 애플리케이션의 헬스체크와 MCP 서버 연결 상태를 확인하는 
FastAPI 엔드포인트들을 정의합니다.
"""

from typing import Annotated, Dict, Any, List
from fastapi import APIRouter

from services.mcp_service import MCPService

router = APIRouter()


@router.get("/")
async def root() -> Annotated[Dict[str, Any], "애플리케이션 헬스체크 결과"]:
    """애플리케이션의 기본 헬스체크 엔드포인트입니다.
    
    애플리케이션이 정상적으로 실행 중인지와 MCP 클라이언트의 연결 상태를 확인합니다.
    
    Returns
    -------
    Dict[str, Any]
        헬스체크 결과가 담긴 딕셔너리
        - message: 애플리케이션 상태 메시지
        - mcp_connected: MCP 클라이언트 연결 여부
        
    Examples
    --------
    >>> import httpx
    >>> response = httpx.get("/")
    >>> print(response.json()["message"])
    'MCP Client API is running'
    """
    mcp_service = MCPService()
    return {
        "message": "MCP Client API is running",
        "mcp_connected": mcp_service.is_connected(),
    }


@router.get("/mcp/status")
async def mcp_status() -> Annotated[Dict[str, Any], "MCP 서버 상태 및 도구 정보"]:
    """MCP 클라이언트의 연결 상태와 사용 가능한 도구들을 확인합니다.
    
    현재 연결된 MCP 서버들의 상태와 각 서버에서 제공하는 도구들의 
    목록 및 개수를 반환합니다.
    
    Returns
    -------
    Dict[str, Any]
        MCP 상태 정보가 담긴 딕셔너리
        - status: 연결 상태 ("connected", "disconnected", "error")
        - tools_count: 사용 가능한 도구의 총 개수
        - tools: 도구 이름들의 리스트 (연결된 경우)
        - error: 오류 메시지 (오류 발생 시)
        
    Examples
    --------
    >>> import httpx
    >>> response = httpx.get("/mcp/status")
    >>> status_data = response.json()
    >>> print(f"연결 상태: {status_data['status']}")
    >>> print(f"사용 가능한 도구: {status_data['tools_count']}개")
    """
    mcp_service = MCPService()

    if not mcp_service.is_connected():
        return {"status": "disconnected", "tools": []}

    try:
        tools = await mcp_service.get_tools()
        tool_names: List[str] = [tool.name for tool in tools] if tools else []
        
        return {
            "status": "connected",
            "tools_count": len(tools) if tools else 0,
            "tools": tool_names,
        }
    except Exception as error:
        return {"status": "error", "error": str(error)}