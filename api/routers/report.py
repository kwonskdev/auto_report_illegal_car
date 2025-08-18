"""신고 API 라우터 모듈.

이 모듈은 불법 차량 신고와 관련된 FastAPI 엔드포인트들을 정의합니다.
ZIP 파일 업로드, 메타데이터 및 STT 처리를 통한 자동 신고 기능을 제공합니다.
"""

import io
import zipfile
from typing import Annotated
from fastapi import APIRouter, HTTPException, File, Form, UploadFile

from services.report_service import ReportService
from services.file_service import FileService

router = APIRouter()


@router.post("/report")
async def report(
    file: Annotated[UploadFile, File(description="MP4 영상들이 포함된 ZIP 파일")],
    meta: Annotated[str, Form(description="GPS 좌표 등이 포함된 메타데이터")],
    stt: Annotated[str, Form(description="음성인식으로 변환된 텍스트")],
) -> Annotated[dict, "신고 처리 결과"]:
    """ZIP 파일과 메타데이터를 받아 MCP 도구를 사용하여 자동 신고를 처리합니다.
    
    업로드된 ZIP 파일에서 MP4 영상들을 추출하고, 메타데이터와 STT 내용을 분석하여
    안전신문고에 자동으로 신고서를 작성하는 엔드포인트입니다.
    
    Parameters
    ----------
    file : UploadFile
        MP4 영상들이 포함된 ZIP 파일
    meta : str
        GPS 좌표, 촬영시간 등이 포함된 메타데이터 문자열
    stt : str
        "불법 자동차를 신고해줘" 등의 음성인식 결과 텍스트
        
    Returns
    -------
    dict
        신고 처리 결과가 담긴 딕셔너리
        - status: 처리 상태
        - message: 처리 완료 메시지  
        - filename: 업로드된 파일명
        - meta_info: 메타데이터 내용
        - stt_content: STT 내용
        - zip_size: ZIP 파일 크기
        - mp4_files_found: 발견된 MP4 파일 개수
        - report_result: 상세 처리 결과
        
    Raises
    ------
    HTTPException
        - 400: ZIP 파일이 아니거나 MP4 파일이 없는 경우
        - 400: ZIP 파일이 손상된 경우  
        - 400: 기타 파일 처리 오류
        
    Examples
    --------
    >>> import httpx
    >>> files = {"file": ("video.zip", zip_data, "application/zip")}
    >>> data = {"meta": "GPS: 37.123, 127.456", "stt": "불법주차 신고"}
    >>> response = httpx.post("/report", files=files, data=data)
    >>> print(response.json()["status"])
    'success'
    """
    temp_dir = None
    try:
        # ZIP 파일 검증
        if not file.filename or not file.filename.lower().endswith(".zip"):
            raise HTTPException(status_code=400, detail="Only ZIP files are allowed")

        # ZIP 파일 데이터 읽기
        zip_content = await file.read()

        # ZIP 파일 유효성 검사
        try:
            with zipfile.ZipFile(io.BytesIO(zip_content), "r") as zip_ref:
                # MP4 파일이 있는지 확인
                mp4_files = [
                    filename
                    for filename in zip_ref.namelist()
                    if filename.lower().endswith(".mp4")
                ]
                if not mp4_files:
                    raise HTTPException(
                        status_code=400, detail="No MP4 files found in the ZIP archive"
                    )
        except zipfile.BadZipFile as error:
            raise HTTPException(status_code=400, detail="Invalid ZIP file") from error

        # 신고 서비스 호출
        report_service = ReportService()
        result = await report_service.process_report(zip_content, meta, stt)

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
            "report_result": result,
        }

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=400, detail=f"Failed to process ZIP file: {str(error)}"
        ) from error

    finally:
        # 분석 완료 후 임시 파일들 정리
        if temp_dir:
            FileService.cleanup_temp_directory(temp_dir)