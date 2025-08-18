"""파일 처리 서비스 모듈.

이 모듈은 ZIP 파일 추출, MP4 파일 분석, 임시 디렉토리 관리 등의 
파일 관련 작업을 처리하는 서비스 클래스를 포함합니다.
"""

import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Annotated, Dict, Any, List


class FileService:
    """파일 처리 관련 기능을 제공하는 서비스 클래스.
    
    이 클래스는 ZIP 파일 추출, MP4 파일 메타데이터 분석, 임시 디렉토리 관리 등의
    파일 관련 작업을 처리하는 정적 메서드들을 제공합니다.
    """

    @staticmethod
    async def extract_zip_contents(
        zip_content: Annotated[bytes, "ZIP 파일의 바이트 데이터"]
    ) -> Annotated[Dict[str, Any], "추출된 파일 정보와 메타데이터"]:
        """ZIP 아카이브에서 MP4 파일들을 추출하고 파일 정보를 반환합니다.
        
        ZIP 파일에서 모든 MP4 파일을 찾아 임시 디렉토리에 추출하고,
        각 파일의 크기, 재생시간 등의 메타데이터를 수집합니다.
        
        Parameters
        ----------
        zip_content : bytes
            처리할 ZIP 파일의 바이트 데이터
            
        Returns
        -------
        Dict[str, Any]
            추출된 MP4 파일들의 정보가 담긴 딕셔너리
            - mp4_files: 각 MP4 파일의 상세 정보 리스트
            - total_files: 총 MP4 파일 개수
            - total_duration_seconds: 총 재생시간 (초)
            - total_size_bytes: 총 파일 크기 (바이트)
            - temp_directory: 임시 디렉토리 경로
            
        Raises
        ------
        Exception
            ZIP 파일 처리 중 오류 발생 시
            
        Examples
        --------
        >>> with open('video.zip', 'rb') as f:
        ...     zip_data = f.read()
        >>> result = await FileService.extract_zip_contents(zip_data)
        >>> print(f"Found {result['total_files']} MP4 files")
        """
        mp4_files: List[Dict[str, Any]] = []
        total_duration = 0

        # Create temporary directory but don't use 'with' so it doesn't get auto-deleted
        temp_dir = tempfile.mkdtemp()
        temp_path = Path(temp_dir)

        try:
            # Save ZIP file temporarily
            zip_path = temp_path / "uploaded.zip"
            with open(zip_path, "wb") as file:
                file.write(zip_content)

            # Extract ZIP contents
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(temp_dir)

                # Find all MP4 files
                for file_info in zip_ref.filelist:
                    if file_info.filename.lower().endswith(".mp4"):
                        file_path = temp_path / file_info.filename
                        if file_path.exists():
                            file_size = file_path.stat().st_size

                            # Try to get video duration (optional, requires ffprobe)
                            duration = FileService._get_video_duration(str(file_path))
                            if duration:
                                total_duration += duration

                            mp4_files.append(
                                {
                                    "filename": file_info.filename,
                                    "size_bytes": file_size,
                                    "duration_seconds": duration,
                                    "file_path": str(file_path),
                                }
                            )

            return {
                "mp4_files": mp4_files,
                "total_files": len(mp4_files),
                "total_duration_seconds": total_duration if total_duration > 0 else None,
                "total_size_bytes": sum(file["size_bytes"] for file in mp4_files),
                "temp_directory": temp_dir,
            }

        except Exception as error:
            # 에러 발생 시 즉시 정리
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise error

    @staticmethod
    def _get_video_duration(file_path: Annotated[str, "비디오 파일 경로"]) -> Annotated[float, "비디오 재생시간"]:
        """비디오 파일의 재생시간을 추출합니다.
        
        ffprobe를 사용하여 비디오 파일의 재생시간을 초 단위로 반환합니다.
        ffprobe가 없거나 오류가 발생하면 None을 반환합니다.
        
        Parameters
        ----------
        file_path : str
            비디오 파일의 전체 경로
            
        Returns
        -------
        float or None
            비디오 재생시간 (초). 실패 시 None.
        """
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "quiet",
                    "-print_format",
                    "json",
                    "-show_format",
                    file_path,
                ],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

            if result.returncode == 0:
                info = json.loads(result.stdout)
                return float(info["format"]["duration"])
        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            json.JSONDecodeError,
            KeyError,
            FileNotFoundError,
        ):
            pass  # ffprobe not available or failed

        return None

    @staticmethod
    def cleanup_temp_directory(temp_dir: Annotated[str, "정리할 임시 디렉토리 경로"]) -> None:
        """임시 디렉토리와 모든 내용을 정리합니다.
        
        지정된 임시 디렉토리를 재귀적으로 삭제합니다.
        디렉토리가 존재하지 않거나 삭제 중 오류가 발생해도 예외를 발생시키지 않습니다.
        
        Parameters
        ----------
        temp_dir : str
            삭제할 임시 디렉토리의 경로
            
        Examples
        --------
        >>> FileService.cleanup_temp_directory("/tmp/some_temp_dir")
        Cleaned up temporary directory: /tmp/some_temp_dir
        """
        try:
            if temp_dir and Path(temp_dir).exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
                print(f"Cleaned up temporary directory: {temp_dir}")
        except Exception as error:
            print(f"WARNING: Failed to cleanup temp directory {temp_dir}: {error}")