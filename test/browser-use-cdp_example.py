"""
Simple demonstration of the CDP feature.

To test this locally, follow these steps:
1. Create a shortcut for the executable Chrome file.
2. Add the following argument to the shortcut:
   - On Windows: `--remote-debugging-port=9222`
3. Open a web browser and navigate to `http://localhost:9222/json/version` to verify that the Remote Debugging Protocol (CDP) is running.
4. Launch this example.

@dev You need to set the `GOOGLE_API_KEY` environment variable before proceeding.
"""

import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv

load_dotenv()


from browser_use import Agent, Controller
from browser_use.browser import BrowserProfile, BrowserSession
from browser_use.llm import ChatAnthropic

api_key = os.getenv('ANTHROPIC_API_KEY')
if not api_key:
	raise ValueError('ANTHROPIC_API_KEY is not set')

browser_session = BrowserSession(
	browser_profile=BrowserProfile(
		headless=False,
	),
	cdp_url='http://localhost:9222',
)
controller = Controller()


async def main():
	task = """
	1. https://www.safetyreport.go.kr/#safereport/safereport3 접속
	2. 자동차·교통 위반 신고 유형 은 이륜차 위반 으로 선택
	3. 사진/동영상에서 파일 추가를 누르고 C:/Users/LGCNS/Desktop/KakaoTalk_20250727_124336306.mp4를 선택해서 열기까지 해줘
	4. 신고 발생 지역을 양화로 186으로 선택해줘
	"""
	# task = "안전 신문고 접속해서 신고하기 탭 클릭하고 자동차·교통 위반 탭 들어가"
	# Assert api_key is not None to satisfy type checker
	assert api_key is not None, 'ANTHROPIC_API_KEY must be set'
	model = ChatAnthropic(model='claude-3-5-sonnet-20240620', api_key=api_key)
	agent = Agent(
		task=task,
		llm=model,
		controller=controller,
		browser_session=browser_session,
	)

	await agent.run()
	await browser_session.close()

	input('Press Enter to close...')


if __name__ == '__main__':
	asyncio.run(main())