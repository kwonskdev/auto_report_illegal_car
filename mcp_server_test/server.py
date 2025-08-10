#!/usr/bin/env python3
"""
MCP Server for Safety Report Tools using FastMCP
Provides tools for vehicle reporting and reverse geocoding
"""

import logging
from typing import Dict, Any

from fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("safety-report-tools")


@mcp.tool(
    name="report_vehicle",
    description="Report vehicle violation",
)
def report_vehicle(
    vehicle_number: str,
    violation_type: str,
    location: str,
    datetime_str: str,
    description: str,
    video_files: list[str] = None,
    reporter_name: str = "익명",
    reporter_phone: str = "비공개",
    reporter_email: str = "비공개"
) -> str:
    return "신고했습니다."


@mcp.tool(
    name="reverse_geocoding",
    description="Reverse geocoding to get address from latitude and longitude",
)
def reverse_geocoding(
    latitude: float,
    longitude: float
) -> str:
    return "서울특별시 마포구 양화로 186"

if __name__ == "__main__":
    mcp.run()