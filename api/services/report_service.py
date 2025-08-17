"""신고 처리 서비스 모듈.

이 모듈은 불법 차량 신고 처리를 위한 비즈니스 로직을 담당하며,
MCP 도구와 Anthropic API를 활용한 영상 분석 및 신고서 작성 기능을 제공합니다.
"""

import os
from typing import Annotated, Dict, Any, List
from fastapi import HTTPException

from langchain_anthropic import ChatAnthropic
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate

from services.file_service import FileService
from services.mcp_service import MCPService


class ReportService:
    """신고 처리 관련 비즈니스 로직을 담당하는 서비스 클래스.
    
    이 클래스는 영상 파일과 메타데이터를 분석하여 불법 차량 신고서를 작성하는
    전체 프로세스를 관리합니다. MCP 도구와 Anthropic API를 활용하여
    지능적인 분석과 신고서 생성을 수행합니다.
    
    Attributes
    ----------
    mcp_service : MCPService
        MCP 서버 통신을 담당하는 서비스 인스턴스
    file_service : FileService
        파일 처리를 담당하는 서비스 인스턴스
    """

    def __init__(self) -> None:
        """ReportService 인스턴스를 초기화합니다."""
        self.mcp_service = MCPService()
        self.file_service = FileService()

    async def process_report(
        self,
        zip_content: Annotated[bytes, "ZIP 파일 바이트 데이터"],
        meta: Annotated[str, "메타데이터 문자열"],
        stt: Annotated[str, "음성인식 텍스트"],
    ) -> Annotated[Dict[str, Any], "신고 처리 결과"]:
        """MCP 도구와 Anthropic API를 사용하여 신고를 처리합니다.
        
        업로드된 ZIP 파일에서 영상을 추출하고, 메타데이터와 STT 내용을 분석하여
        안전신문고 신고서를 자동으로 작성합니다.
        
        Parameters
        ----------
        zip_content : bytes
            MP4 영상들이 포함된 ZIP 파일의 바이트 데이터
        meta : str
            GPS 좌표 등이 포함된 메타데이터
        stt : str
            "불법 자동차를 신고해줘" 등의 음성인식 결과 텍스트
            
        Returns
        -------
        Dict[str, Any]
            신고 처리 결과가 담긴 딕셔너리
            - status: 처리 상태 ("success" 등)
            - response: AI가 생성한 신고서 내용
            - tools_used: 사용된 도구 개수
            - tools_called: 호출된 도구들의 이름 리스트
            - zip_analysis: ZIP 파일 분석 결과
            
        Raises
        ------
        HTTPException
            신고 처리 중 오류 발생 시 (상태 코드 500)
            
        Examples
        --------
        >>> service = ReportService()
        >>> with open('violation.zip', 'rb') as f:
        ...     zip_data = f.read()
        >>> result = await service.process_report(zip_data, "GPS: 37.123, 127.456", "불법주차 신고")
        >>> print(result['status'])
        'success'
        """
        try:
            # Extract ZIP contents
            zip_info = await self.file_service.extract_zip_contents(zip_content)

            # Initialize Anthropic client
            llm = ChatAnthropic(
                model="claude-3-5-sonnet-20241022",
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                temperature=0.01,
            )

            # Get available tools from MCP client
            langchain_tools = []
            if self.mcp_service.is_connected():
                try:
                    mcp_tools = await self.mcp_service.get_tools()
                    if mcp_tools:
                        langchain_tools = mcp_tools
                        print(f"Loaded {len(langchain_tools)} MCP tools")
                except Exception as tool_error:
                    print(f"WARNING: Failed to load MCP tools: {tool_error}")
                    langchain_tools = []

            # Create detailed message for analysis
            message_content = self._create_analysis_message(zip_info, meta, stt, zip_content)

            # Process with tools if available
            if langchain_tools:
                return await self._process_with_agent(llm, langchain_tools, message_content, zip_info)
            return await self._process_without_tools(llm, message_content, zip_info)

        except Exception as error:
            raise HTTPException(
                status_code=500, detail=f"Report processing failed: {str(error)}"
            ) from error

    def _create_analysis_message(
        self,
        zip_info: Annotated[Dict[str, Any], "ZIP 파일 분석 정보"],
        meta: Annotated[str, "메타데이터"],
        stt: Annotated[str, "STT 텍스트"],
        zip_content: Annotated[bytes, "ZIP 파일 바이트 데이터"],
    ) -> Annotated[str, "AI 분석용 메시지"]:
        """AI 분석을 위한 상세한 메시지 내용을 생성합니다.
        
        Parameters
        ----------
        zip_info : Dict[str, Any]
            ZIP 파일 분석 결과
        meta : str
            메타데이터 문자열
        stt : str
            음성인식 텍스트
        zip_content : bytes
            ZIP 파일 바이트 데이터
            
        Returns
        -------
        str
            AI가 분석할 수 있도록 구조화된 메시지 내용
        """
        duration_info = (
            f"- 총 재생시간: {zip_info['total_duration_seconds']:.1f}초"
            if zip_info["total_duration_seconds"]
            else "- 재생시간: 분석 불가"
        )

        file_paths_info = "\\n".join(
            [f"- {file['filename']}: {file['file_path']}" for file in zip_info["mp4_files"]]
        )

        mp4_files_info = "\\n".join(
            [
                f"- {file['filename']} ({file['size_bytes']:,} bytes)"
                + (f", {file['duration_seconds']:.1f}초" if file["duration_seconds"] else "")
                for file in zip_info["mp4_files"]
            ]
        )

        return f"""
        업로드된 파일 분석:
        
        === ZIP 파일 정보 ===
        - 총 파일 크기: {len(zip_content):,} bytes
        - MP4 파일 개수: {zip_info['total_files']}개
        - MP4 총 크기: {zip_info['total_size_bytes']:,} bytes
        {duration_info}
        
        === 포함된 MP4 파일들 ===
        {mp4_files_info}
        
        === 추출된 파일 경로들 (MCP 도구 접근 가능) ===
        {file_paths_info}
        
        === 메타데이터 ===
        {meta}
        
        === STT (Speech-to-Text) 내용 ===
        {stt}
        
        === 분석 요청 ===
        위의 영상 파일들과 STT 내용, 메타데이터를 종합하여 안전신문고에 영상을 신고해주세요.
        
        단계별 작업:
        1. 먼저 메타데이터에서 GPS 좌표를 찾아 reverse_geocoding 도구로 정확한 주소를 확인하세요.
        2. STT 내용에서 차량번호, 위반유형, 시간 등 필요한 정보를 추출하세요.
        3. report_vehicle 도구를 사용하여 실제 안전신문고 신고서를 작성하세요.
        4. 추가로 필요한 정보가 있다면 다른 도구들을 활용하세요.
        
        모든 도구를 순차적으로 사용하여 완전한 신고서를 작성해주세요.
        """

    async def _process_with_agent(
        self,
        llm: Annotated[ChatAnthropic, "Anthropic 언어 모델"],
        langchain_tools: Annotated[List[Any], "사용 가능한 도구들"],
        message_content: Annotated[str, "분석 메시지"],
        zip_info: Annotated[Dict[str, Any], "ZIP 파일 정보"],
    ) -> Annotated[Dict[str, Any], "에이전트 처리 결과"]:
        """에이전트를 사용하여 도구들과 함께 신고를 처리합니다.
        
        Parameters
        ----------
        llm : ChatAnthropic
            Anthropic 언어 모델 인스턴스
        langchain_tools : List[Any]
            사용 가능한 MCP 도구들
        message_content : str
            AI 분석용 메시지
        zip_info : Dict[str, Any]
            ZIP 파일 분석 정보
            
        Returns
        -------
        Dict[str, Any]
            에이전트 처리 결과
        """
        try:
            # Create Agent prompt template
            agent_prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "You are a helpful assistant that processes traffic violation reports. "
                        "Use the available tools to analyze the data and create proper reports. "
                        "You can use multiple tools in sequence to complete the task.",
                    ),
                    ("human", "{input}"),
                    ("placeholder", "{agent_scratchpad}"),
                ]
            )

            # Create tool-calling agent
            agent = create_tool_calling_agent(llm, langchain_tools, agent_prompt)

            # Create agent executor
            agent_executor = AgentExecutor(
                agent=agent,
                tools=langchain_tools,
                verbose=True,
                max_iterations=10,
                handle_parsing_errors=True,
                early_stopping_method="generate",
                return_intermediate_steps=True,
            )

            # Run the agent
            print("Starting Agent execution...")

            tools_called = []
            response_content = ""

            async for event in agent_executor.astream_events(
                {"input": message_content}, version="v2"
            ):
                kind = event["event"]

                if kind == "on_tool_start":
                    # Get tool name from the correct location in the event
                    tool_name = event.get("data", {}).get("input", {}).get("tool", "unknown_tool")
                    if tool_name == "unknown_tool":
                        # Try alternative locations for tool name
                        tool_name = event.get("name", "unknown_tool")
                        if tool_name == "unknown_tool":
                            tool_name = event.get("data", {}).get("tool", "unknown_tool")
                    tools_called.append(tool_name)
                    print(f"Calling tool: {tool_name}")

                elif kind == "on_chain_end" and event.get("name") == "AgentExecutor":
                    response_content = event["data"]["output"]["output"]

            return {
                "status": "success",
                "response": response_content,
                "tools_used": len(langchain_tools),
                "tools_called": tools_called,
                "agent_steps": len(tools_called),
                "zip_analysis": zip_info,
            }

        except Exception as agent_error:
            print(f"WARNING: Agent execution failed, falling back to simple LLM: {agent_error}")
            return await self._process_with_fallback(llm, langchain_tools, message_content, zip_info)

    async def _process_with_fallback(
        self,
        llm: Annotated[ChatAnthropic, "Anthropic 언어 모델"],
        langchain_tools: Annotated[List[Any], "사용 가능한 도구들"],
        message_content: Annotated[str, "분석 메시지"],
        zip_info: Annotated[Dict[str, Any], "ZIP 파일 정보"],
    ) -> Annotated[Dict[str, Any], "폴백 처리 결과"]:
        """도구 바인딩을 사용한 폴백 처리를 수행합니다.
        
        Parameters
        ----------
        llm : ChatAnthropic
            Anthropic 언어 모델 인스턴스
        langchain_tools : List[Any]
            사용 가능한 MCP 도구들
        message_content : str
            AI 분석용 메시지
        zip_info : Dict[str, Any]
            ZIP 파일 분석 정보
            
        Returns
        -------
        Dict[str, Any]
            폴백 처리 결과
        """
        try:
            llm_with_tools = llm.bind_tools(langchain_tools)
            response = await llm_with_tools.ainvoke(message_content)
            response_content = response.content
        except Exception as binding_error:
            print(f"WARNING: Tool binding also failed, calling without tools: {binding_error}")
            response = await llm.ainvoke(message_content)
            response_content = response.content

        return {
            "status": "success",
            "response": response_content,
            "tools_used": len(langchain_tools),
            "zip_analysis": zip_info,
        }

    async def _process_without_tools(
        self,
        llm: Annotated[ChatAnthropic, "Anthropic 언어 모델"],
        message_content: Annotated[str, "분석 메시지"],
        zip_info: Annotated[Dict[str, Any], "ZIP 파일 정보"],
    ) -> Annotated[Dict[str, Any], "도구 없이 처리한 결과"]:
        """도구 없이 단순 LLM만 사용하여 처리합니다.
        
        Parameters
        ----------
        llm : ChatAnthropic
            Anthropic 언어 모델 인스턴스
        message_content : str
            AI 분석용 메시지
        zip_info : Dict[str, Any]
            ZIP 파일 분석 정보
            
        Returns
        -------
        Dict[str, Any]
            단순 LLM 처리 결과
        """
        response = await llm.ainvoke(message_content)
        response_content = response.content

        return {
            "status": "success",
            "response": response_content,
            "tools_used": 0,
            "zip_analysis": zip_info,
        }