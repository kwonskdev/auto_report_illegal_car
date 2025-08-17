#!/usr/bin/env python3
"""
MCP Server for Safety Report Tools using FastMCP
Provides tools for traffic violation reporting and get address from geocoding
"""

import logging
from typing import Dict, Any

from fastmcp import FastMCP
from report import run_report, reverse_geocoding

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("safety-report-tools")


@mcp.tool(
    name="report_traffic_violation",
    description="Report traffic violation",
)
def report_traffic_violation(
    title: str,
    vehicle_number: str,
    violation_type: str,
    latitude: float,
    longitude: float,
    datetime_str: str,
    description: str,
    video_files: list[str] = None,
    reporter_name: str = "익명",
    reporter_phone: str = "비공개",
    reporter_email: str = "비공개"
) -> str:
    return run_report(title, vehicle_number, violation_type, latitude, longitude, datetime_str, description, video_files, reporter_name, reporter_phone, reporter_email)


@mcp.tool(
    name="get_address_from_geocoding",
    description="Reverse geocoding to get address from latitude and longitude",
)
def get_address_from_geocoding(
    latitude: float,
    longitude: float
) -> str:
    result = reverse_geocoding(latitude, longitude)
    if isinstance(result, dict) and result.get('success'):
        return result.get('korean_address', result.get('full_address', '주소 정보 없음'))
    else:
        return f"주소 검색 실패: {result.get('error', '알 수 없는 오류')}"


if __name__ == "__main__":
    mcp.run()