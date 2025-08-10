#!/usr/bin/env python3
"""
Test script for MCP Client Report API
Tests the /report endpoint with a sample ZIP file containing MP4 videos
"""

import asyncio
import json
import os
import tempfile
import zipfile
from pathlib import Path

import httpx


async def create_sample_zip() -> bytes:
    """Create a sample ZIP file with dummy MP4 files for testing"""
    
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create dummy MP4 files (just empty files with .mp4 extension for testing)
        mp4_files = [
            "traffic_violation_01.mp4",
            "traffic_violation_02.mp4",
            "parking_violation.mp4"
        ]
        
        for filename in mp4_files:
            file_path = temp_path / filename
            # Create a small dummy file (just some bytes to simulate MP4)
            with open(file_path, 'wb') as f:
                # Write some dummy data to simulate a video file
                dummy_data = b"dummy video data " * 1000  # ~17KB
                f.write(dummy_data)
        
        # Create ZIP file
        zip_path = temp_path / "test_videos.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for filename in mp4_files:
                file_path = temp_path / filename
                zipf.write(file_path, filename)
        
        # Read ZIP file content
        with open(zip_path, 'rb') as f:
            return f.read()


async def test_report_endpoint():
    """Test the /report endpoint with sample data"""
    
    # API endpoint
    api_url = "http://localhost:8001"
    report_endpoint = f"{api_url}/report"
    
    try:
        # Create sample ZIP file
        print("📦 Creating sample ZIP file with MP4 videos...")
        zip_content = await create_sample_zip()
        print(f"✓ Created ZIP file: {len(zip_content):,} bytes")
        
        # Prepare test data
        test_data = {
            "meta": json.dumps({
                "location": "서울시 강남구 역삼동 123-45",
                "coordinates": {
                    "latitude": 37.5665,
                    "longitude": 126.9780
                },
                "timestamp": "2025-01-10T14:30:00",
                "device": "dashcam_model_x",
                "reporter": {
                    "name": "김철수",
                    "phone": "010-1234-5678",
                    "email": "test@example.com"
                }
            }, ensure_ascii=False),
            "stt": "차량번호 12가3456 차량이 신호를 위반하여 교차로를 통과했습니다. 빨간불임에도 불구하고 속도를 줄이지 않고 그대로 직진했습니다. 보행자들이 건널목을 건너려던 상황이었는데 매우 위험했습니다."
        }
        
        # Prepare files for upload
        files = {
            'file': ('test_videos.zip', zip_content, 'application/zip')
        }
        
        print(f"\n📡 Sending request to {report_endpoint}")
        
        # Send request
        async with httpx.AsyncClient(timeout=300.0) as client:  # 5 minute timeout
            response = await client.post(
                report_endpoint,
                data=test_data,
                files=files
            )
        
        print(f"📊 Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Request successful!")
            print(result)
            
            # Extract and display key information concisely
            if 'report_result' in result:
                report_result = result['report_result']
                
                # Display user question from STT
                stt_content = result.get('stt_content', 'No STT content')
                print(f"\n📝 User Request: {stt_content}")
                
                # Display tools actually called
                tools_called = report_result.get('tools_called', [])
                if tools_called:
                    print(f"🔧 Tools Called: {', '.join(tools_called)}")
                else:
                    print(f"🔧 Tools Called: None")
                
                # Display final response (text only)
                if 'response' in report_result:
                    response_text = report_result['response'][0]["text"]
                    # Extract text if it's a complex structure
                    if isinstance(response_text, str):
                        final_text = response_text
                    else:
                        final_text = str(response_text)
                    
                    print(f"\n🤖 Final Response:")
                    print("=" * 60)
                    print(final_text)
                    print("=" * 60)
                    
            else:
                # Fallback for different response structure
                print(f"\n🤖 Response: {result.get('message', 'No message available')}")
        else:
            print("❌ Request failed!")
            print(f"Error: {response.text}")
            
    except httpx.ConnectError:
        print("❌ Connection failed!")
        print("Make sure the MCP Client server is running at http://localhost:8001")
        print("Run: cd mcp_client && uv run python main.py")
    except Exception as e:
        print(f"❌ Error occurred: {e}")


async def test_health_check():
    """Test the health check endpoint"""
    
    api_url = "http://localhost:8001"
    health_endpoint = f"{api_url}/"
    
    try:
        print("🏥 Checking server health...")
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(health_endpoint)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Server is healthy!")
            print(f"📡 Message: {result.get('message')}")
            print(f"🔗 MCP Connected: {result.get('mcp_connected')}")
        else:
            print(f"⚠️ Health check returned status {response.status_code}")
            
    except httpx.ConnectError:
        print("❌ Server is not responding!")
        return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False
    
    return True


async def test_mcp_status():
    """Test the MCP status endpoint"""
    
    api_url = "http://localhost:8001"
    mcp_endpoint = f"{api_url}/mcp/status"
    
    try:
        print("\n🔍 Checking MCP status...")
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(mcp_endpoint)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ MCP Status:")
            print(f"📊 Status: {result.get('status')}")
            print(f"🛠️ Tools count: {result.get('tools_count', 0)}")
            if result.get('tools'):
                print(f"🔧 Available tools: {', '.join(result['tools'])}")
        else:
            print(f"⚠️ MCP status returned status {response.status_code}")
            
    except Exception as e:
        print(f"❌ MCP status error: {e}")


async def main():
    """Main test function"""
    
    print("🚀 MCP Client Report API Test")
    print("=" * 50)
    
    # Quick server check
    if not await test_health_check():
        print("\n💡 Start server: cd mcp_client && uv run python main.py")
        return
    
    # Test report endpoint
    print("\n" + "=" * 50)
    await test_report_endpoint()
    
    print("\n🏁 Test completed!")


if __name__ == "__main__":
    asyncio.run(main())