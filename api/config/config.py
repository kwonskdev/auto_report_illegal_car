"""애플리케이션 설정 관리 모듈.

이 모듈은 MCP 서버 설정을 비롯한 애플리케이션의 다양한 설정을 로드하고 관리하는 기능을 제공합니다.
"""

import json
from pathlib import Path
from typing import Annotated, Dict, Any
from dotenv import load_dotenv

load_dotenv()


class Config:
    """애플리케이션 설정을 관리하는 클래스.
    
    이 클래스는 다양한 설정 파일을 로드하고 파싱하는 정적 메서드들을 제공합니다.
    주로 MCP 서버 설정과 같은 외부 설정 파일을 처리하는 데 사용됩니다.
    """

    @staticmethod
    def load_mcp_config() -> Annotated[Dict[str, Any], "MCP 서버 설정 딕셔너리"]:
        """MCP 서버 설정 파일을 로드합니다.
        
        mcp.json 파일에서 MCP 서버들의 설정 정보를 읽어와 딕셔너리 형태로 반환합니다.
        파일이 존재하지 않거나 파싱 오류가 발생할 경우 빈 딕셔너리를 반환합니다.
        
        Returns
        -------
        Dict[str, Any]
            MCP 서버 설정이 담긴 딕셔너리. 오류 발생 시 빈 딕셔너리.
            
        Examples
        --------
        >>> config = Config.load_mcp_config()
        >>> print(config.get('mcpServers', {}))
        """
        mcp_config_path = Path(__file__).parent.parent / "mcp.json"

        try:
            with open(mcp_config_path, "r", encoding="utf-8") as file:
                return json.load(file)
        except FileNotFoundError:
            print(f"MCP config file not found at {mcp_config_path}")
            return {}
        except json.JSONDecodeError as error:
            print(f"Error parsing MCP config file: {error}")
            return {}
        except Exception as error:
            print(f"Error loading MCP config: {error}")
            return {}