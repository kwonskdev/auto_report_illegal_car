import asyncio
import io
import json
import os
import shutil
import tempfile
import zipfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, File, Form, UploadFile
import uvicorn
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_anthropic import ChatAnthropic
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate

load_dotenv()


# Global MCP client instance
mcp_client: Optional[MultiServerMCPClient] = None


def load_mcp_config() -> Dict[str, Any]:
    """Load MCP server configuration from mcp.json"""
    mcp_config_path = Path(__file__).parent / "mcp.json"
    
    try:
        with open(mcp_config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"MCP config file not found at {mcp_config_path}")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error parsing MCP config file: {e}")
        return {}
    except Exception as e:
        print(f"Error loading MCP config: {e}")
        return {}


async def test_individual_server_connection(server_name: str, server_config: Dict[str, Any]) -> bool:
    """Test connection to individual MCP server"""
    try:
        from mcp import ClientSession
        from mcp.client.stdio import StdioServerParameters, stdio_client
        
        # Create server parameters
        server_params = StdioServerParameters(
            command=server_config["command"],
            args=server_config.get("args", [])
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


async def setup_mcp_client(mcp_server_config: Dict[str, Any]) -> Optional[MultiServerMCPClient]:
    """Initialize MCP client with server configurations"""
    global mcp_client
    
    if not mcp_server_config:
        print("No MCP server configuration provided.")
        return None

    try:
        if "mcpServers" in mcp_server_config:
            mcp_server_config = mcp_server_config["mcpServers"]
        
        # Test each server individually first
        connected_servers = []
        failed_servers = []
        
        print("🔍 Testing individual server connections...")
        for server_name, server_config in mcp_server_config.items():
            print(f"  Testing {server_name}...", end=" ")
            
            is_connected = await test_individual_server_connection(server_name, server_config)
            
            if is_connected:
                print("✓ Connected")
                connected_servers.append(server_name)
            else:
                print("❌ Failed")
                failed_servers.append(server_name)
        
        # Report individual results
        if connected_servers:
            print(f"✅ Successfully connected servers: {connected_servers}")
        if failed_servers:
            print(f"❌ Failed to connect servers: {failed_servers}")
        
        # Initialize MultiServerMCPClient with all servers (it will handle failures internally)
        client = MultiServerMCPClient(mcp_server_config)
        mcp_client = client
        
        # Test overall client functionality
        try:
            tools = await client.get_tools()
            print(f"📊 Total available tools from all servers: {len(tools) if tools else 0}")
            
            if tools:
                # Group tools by server if possible
                tool_names = [tool.name for tool in tools[:5]]
                print(f"🔧 Example tools: {tool_names}")
                
        except Exception as conn_error:
            print(f"⚠ MultiServerMCPClient created but tool fetching failed: {conn_error}")
            
        return client

    except Exception as e:
        print(f"❌ Failed to setup MCP client: {e}")
        return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup and shutdown events"""
    # Startup
    mcp_server_config = load_mcp_config()
    
    await setup_mcp_client(mcp_server_config)
    
    yield
    
    # Shutdown
    global mcp_client
    if mcp_client:
        print("Closing MCP client...")


app = FastAPI(title="MCP Client API", version="1.0.0", lifespan=lifespan)


async def extract_zip_contents(zip_content: bytes) -> Dict[str, Any]:
    """Extract MP4 files from ZIP archive and return file information with temp directory"""
    mp4_files = []
    total_duration = 0
    
    # Create temporary directory but don't use 'with' so it doesn't get auto-deleted
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)
    
    try:
        # Save ZIP file temporarily
        zip_path = temp_path / "uploaded.zip"
        with open(zip_path, 'wb') as f:
            f.write(zip_content)
        
        # Extract ZIP contents
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
            
            # Find all MP4 files
            for file_info in zip_ref.filelist:
                if file_info.filename.lower().endswith('.mp4'):
                    file_path = temp_path / file_info.filename
                    if file_path.exists():
                        file_size = file_path.stat().st_size
                        
                        # Try to get video duration (optional, requires ffprobe)
                        duration = None
                        try:
                            import subprocess
                            result = subprocess.run([
                                'ffprobe', '-v', 'quiet', '-print_format', 'json', 
                                '-show_format', str(file_path)
                            ], capture_output=True, text=True, timeout=10)
                            
                            if result.returncode == 0:
                                info = json.loads(result.stdout)
                                duration = float(info['format']['duration'])
                                total_duration += duration
                        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, 
                               json.JSONDecodeError, KeyError, FileNotFoundError):
                            pass  # ffprobe not available or failed
                        
                        mp4_files.append({
                            'filename': file_info.filename,
                            'size_bytes': file_size,
                            'duration_seconds': duration,
                            'file_path': str(file_path)  # 실제 파일 경로 포함
                        })
        
        return {
            'mp4_files': mp4_files,
            'total_files': len(mp4_files),
            'total_duration_seconds': total_duration if total_duration > 0 else None,
            'total_size_bytes': sum(f['size_bytes'] for f in mp4_files),
            'temp_directory': temp_dir  # 나중에 정리할 임시 디렉토리 경로
        }
    
    except Exception as e:
        # 에러 발생 시 즉시 정리
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise e


def cleanup_temp_directory(temp_dir: str):
    """Clean up temporary directory and all its contents"""
    try:
        if temp_dir and Path(temp_dir).exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
            print(f"🗑️ Cleaned up temporary directory: {temp_dir}")
    except Exception as e:
        print(f"⚠️ Failed to cleanup temp directory {temp_dir}: {e}")


async def call_anthropic_with_mcp(zip_content: bytes, meta: str, stt: str) -> Dict[str, Any]:
    """Call Anthropic API using MCP tools using Agent for multi-tool calling"""
    try:
        # Extract ZIP contents
        zip_info = await extract_zip_contents(zip_content)
        
        # Initialize Anthropic client
        llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            temperature=0.01
        )
        
        # Get available tools from MCP client and convert to proper format
        langchain_tools = []
        if mcp_client:
            try:
                # Get MCP tools and convert them to LangChain format
                mcp_tools = await mcp_client.get_tools()
                if mcp_tools:
                    # Use the MCP adapter's built-in tool conversion
                    langchain_tools = mcp_tools
                    print(f"🔧 Loaded {len(langchain_tools)} MCP tools")
            except Exception as tool_error:
                print(f"⚠️ Failed to load MCP tools: {tool_error}")
                langchain_tools = []
        
        # Prepare detailed message with ZIP and MP4 file analysis
        duration_info = f"- 총 재생시간: {zip_info['total_duration_seconds']:.1f}초" if zip_info['total_duration_seconds'] else "- 재생시간: 분석 불가"
        
        # Include file paths information for MCP tools to access
        file_paths_info = "\n".join([f"- {f['filename']}: {f['file_path']}" for f in zip_info['mp4_files']])
        
        message_content = f"""
        업로드된 파일 분석:
        
        === ZIP 파일 정보 ===
        - 총 파일 크기: {len(zip_content):,} bytes
        - MP4 파일 개수: {zip_info['total_files']}개
        - MP4 총 크기: {zip_info['total_size_bytes']:,} bytes
        {duration_info}
        
        === 포함된 MP4 파일들 ===
        {chr(10).join([f"- {f['filename']} ({f['size_bytes']:,} bytes)" + (f", {f['duration_seconds']:.1f}초" if f['duration_seconds'] else "") for f in zip_info['mp4_files']])}
        
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
        
        # Use Agent for multi-tool calling if tools are available
        if langchain_tools:
            try:
                # Create Agent prompt template
                agent_prompt = ChatPromptTemplate.from_messages([
                    ("system", "You are a helpful assistant that processes traffic violation reports. Use the available tools to analyze the data and create proper reports. You can use multiple tools in sequence to complete the task."),
                    ("human", "{input}"),
                    ("placeholder", "{agent_scratchpad}")
                ])
                
                # Create tool-calling agent
                agent = create_tool_calling_agent(llm, langchain_tools, agent_prompt)
                
                # Create agent executor with quiet output
                agent_executor = AgentExecutor(
                    agent=agent, 
                    tools=langchain_tools, 
                    verbose=True,  # Disable verbose output
                    max_iterations=5,  # Allow multiple tool calls
                    handle_parsing_errors=True
                )
                
                # Run the agent
                print("🤖 Starting Agent execution...")
                result = await agent_executor.ainvoke({
                    "input": message_content
                })
                
                response_content = result.get("output", "No response generated")
                
                # Extract tool names from intermediate steps
                tools_called = []
                intermediate_steps = result.get("intermediate_steps", [])
                for step in intermediate_steps:
                    if hasattr(step, '__len__') and len(step) > 0:
                        action = step[0]
                        if hasattr(action, 'tool'):
                            tools_called.append(action.tool)
                
                return {
                    "status": "success",
                    "response": response_content,
                    "tools_used": len(langchain_tools),
                    "tools_called": tools_called,
                    "agent_steps": len(intermediate_steps),
                    "zip_analysis": zip_info
                }
                
            except Exception as agent_error:
                print(f"⚠️ Agent execution failed, falling back to simple LLM: {agent_error}")
                # Fallback to simple tool binding
                try:
                    llm_with_tools = llm.bind_tools(langchain_tools)
                    response = await llm_with_tools.ainvoke(message_content)
                    response_content = response.content
                except Exception as binding_error:
                    print(f"⚠️ Tool binding also failed, calling without tools: {binding_error}")
                    response = await llm.ainvoke(message_content)
                    response_content = response.content
        else:
            # No tools available, use simple LLM
            response = await llm.ainvoke(message_content)
            response_content = response.content
        
        return {
            "status": "success",
            "response": response_content,
            "tools_used": len(langchain_tools),
            "zip_analysis": zip_info
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Anthropic API call failed: {str(e)}")


@app.post("/report")
async def report(
    file: UploadFile = File(...), 
    meta: str = Form(...),
    stt: str = Form(...)
):
    """
    ZIP 파일(MP4 영상들 포함), 메타데이터, speech-to-text 정보를 받아서 MCP 도구를 사용하여 Anthropic API로 분석
    """
    temp_dir = None
    try:
        # ZIP 파일 검증
        if not file.filename or not file.filename.lower().endswith('.zip'):
            raise HTTPException(status_code=400, detail="Only ZIP files are allowed")
        
        # ZIP 파일 데이터 읽기
        zip_content = await file.read()
        
        # ZIP 파일 유효성 검사
        try:
            with zipfile.ZipFile(io.BytesIO(zip_content), 'r') as zip_ref:
                # MP4 파일이 있는지 확인
                mp4_files = [f for f in zip_ref.namelist() if f.lower().endswith('.mp4')]
                if not mp4_files:
                    raise HTTPException(status_code=400, detail="No MP4 files found in the ZIP archive")
        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="Invalid ZIP file")
        
        # MCP 도구를 사용한 Anthropic API 호출 (파일 추출 포함)
        result = await call_anthropic_with_mcp(zip_content, meta, stt)
        
        # 임시 디렉토리 정보 저장 (정리용)
        temp_dir = result.get("zip_analysis", {}).get("temp_directory")
        
        return {
            "status": "success",
            "message": "Report vehicle completed successfully",
            "filename": file.filename,
            "meta_info": meta,
            "stt_content": stt,
            "zip_size": len(zip_content),
            "mp4_files_found": len(mp4_files),
            "report_result": result
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process ZIP file: {str(e)}")
    
    finally:
        # 분석 완료 후 임시 파일들 정리
        if temp_dir:
            cleanup_temp_directory(temp_dir)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "MCP Client API is running",
        "mcp_connected": mcp_client is not None
    }


@app.get("/mcp/status")
async def mcp_status():
    """Check MCP client status and available tools"""
    if not mcp_client:
        return {"status": "disconnected", "tools": []}
    
    try:
        tools = await mcp_client.get_tools()
        return {
            "status": "connected",
            "tools_count": len(tools) if tools else 0,
            "tools": [tool.name for tool in tools] if tools else []
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)