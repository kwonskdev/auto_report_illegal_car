"""MCP 서버 통신 관리 모듈.

이 모듈은 MCP(Model Context Protocol) 서버들과의 연결을 관리하고, 
도구(tool) 접근 기능을 제공하는 서비스 클래스를 포함합니다.
"""

import asyncio
from typing import Annotated, Dict, Any, Optional, List
from langchain_mcp_adapters.client import MultiServerMCPClient


class MCPService:
    """MCP 서버 통신을 관리하는 싱글톤 서비스 클래스.
    
    이 클래스는 여러 MCP 서버들과의 연결을 관리하고, 사용 가능한 도구들을 
    제공하는 기능을 담당합니다. 싱글톤 패턴을 사용하여 전역적으로 하나의 
    인스턴스만 존재하도록 보장합니다.
    
    Attributes
    ----------
    _instance : Optional[MCPService]
        싱글톤 인스턴스
    _client : Optional[MultiServerMCPClient]
        MCP 클라이언트 인스턴스
    """

    _instance: Optional["MCPService"] = None
    _client: Optional[MultiServerMCPClient] = None

    def __new__(cls) -> "MCPService":
        """싱글톤 패턴을 구현하는 생성자.
        
        Returns
        -------
        MCPService
            싱글톤 인스턴스
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    async def initialize(
        cls, mcp_server_config: Annotated[Dict[str, Any], "MCP 서버 설정"]
    ) -> Annotated[Optional[MultiServerMCPClient], "초기화된 MCP 클라이언트"]:
        """MCP 클라이언트를 서버 설정으로 초기화합니다.
        
        Parameters
        ----------
        mcp_server_config : Dict[str, Any]
            MCP 서버들의 설정 정보가 담긴 딕셔너리
            
        Returns
        -------
        Optional[MultiServerMCPClient]
            초기화된 MCP 클라이언트. 실패 시 None.
            
        Examples
        --------
        >>> config = {"mcpServers": {"server1": {...}}}
        >>> client = await MCPService.initialize(config)
        """
        if not mcp_server_config:
            print("No MCP server configuration provided.")
            return None

        try:
            if "mcpServers" in mcp_server_config:
                mcp_server_config = mcp_server_config["mcpServers"]

            # Test each server individually first
            connected_servers = []
            failed_servers = []

            print("Testing individual server connections...")
            for server_name, server_config in mcp_server_config.items():
                print(f"  Testing {server_name}...", end=" ")

                is_connected = await cls._test_individual_server_connection(
                    server_name, server_config
                )

                if is_connected:
                    print("Connected")
                    connected_servers.append(server_name)
                else:
                    print("Failed")
                    failed_servers.append(server_name)

            # Report individual results
            if connected_servers:
                print(f"Successfully connected servers: {connected_servers}")
            if failed_servers:
                print(f"Failed to connect servers: {failed_servers}")

            # Initialize MultiServerMCPClient with all servers
            client = MultiServerMCPClient(mcp_server_config)
            cls._client = client

            # Test overall client functionality
            try:
                tools = await client.get_tools()
                tools_count = len(tools) if tools else 0
                print(f"Total available tools from all servers: {tools_count}")

                if tools:
                    tool_names = [tool.name for tool in tools[:5]]
                    print(f"Example tools: {tool_names}")

            except Exception as conn_error:
                print(
                    f"WARNING: MultiServerMCPClient created but tool fetching failed: {conn_error}"
                )

            return client

        except Exception as error:
            print(f"Failed to setup MCP client: {error}")
            return None

    @staticmethod
    async def _test_individual_server_connection(
        server_name: Annotated[str, "서버 이름"],
        server_config: Annotated[Dict[str, Any], "서버 설정"],
    ) -> Annotated[bool, "연결 성공 여부"]:
        """개별 MCP 서버 연결을 테스트합니다.
        
        Parameters
        ----------
        server_name : str
            테스트할 서버의 이름
        server_config : Dict[str, Any]
            서버 설정 정보
            
        Returns
        -------
        bool
            연결 성공 시 True, 실패 시 False
        """
        try:
            from mcp import ClientSession
            from mcp.client.stdio import StdioServerParameters, stdio_client

            # Create server parameters
            server_params = StdioServerParameters(
                command=server_config["command"], args=server_config.get("args", [])
            )

            # Test connection with timeout
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await asyncio.wait_for(session.initialize(), timeout=10.0)
                    return True

        except asyncio.TimeoutError:
            return False
        except Exception:
            return False

    def is_connected(self) -> Annotated[bool, "MCP 클라이언트 연결 상태"]:
        """MCP 클라이언트가 연결되어 있는지 확인합니다.
        
        Returns
        -------
        bool
            연결되어 있으면 True, 아니면 False
        """
        return self._client is not None

    async def get_tools(self) -> Annotated[List[Any], "사용 가능한 MCP 도구 목록"]:
        """MCP 클라이언트에서 사용 가능한 도구들을 가져옵니다.
        
        Returns
        -------
        List[Any]
            사용 가능한 도구들의 리스트. 클라이언트가 없으면 빈 리스트.
        """
        if not self._client:
            return []
        return await self._client.get_tools()

    def get_client(self) -> Annotated[Optional[MultiServerMCPClient], "MCP 클라이언트 인스턴스"]:
        """MCP 클라이언트 인스턴스를 가져옵니다.
        
        Returns
        -------
        Optional[MultiServerMCPClient]
            MCP 클라이언트 인스턴스. 초기화되지 않았으면 None.
        """
        return self._client