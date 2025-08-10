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
from browser_use.agent.views import ActionResult
from browser_use.browser.context import BrowserContext

api_key = os.getenv('ANTHROPIC_API_KEY')
if not api_key:
	raise ValueError('ANTHROPIC_API_KEY is not set')

browser_session = BrowserSession(
	browser_profile=BrowserProfile(
		headless=False,
	),
	cdp_url='http://localhost:9222',
)

class EnhancedController(Controller):
    def __init__(self):
        super().__init__()
        self._register_file_upload_actions()
    
    def _register_file_upload_actions(self):
        @self.registry.action("Upload file by clicking element and handling file chooser dialog automatically")
        async def upload_file_with_dialog(element_index: int, file_path: str, browser: BrowserContext):
            try:
                if not os.path.exists(file_path):
                    return ActionResult(error=f'File {file_path} does not exist')
                
                page = await browser.get_current_page()
                
                # Set up file chooser handler before clicking
                async def handle_file_chooser(file_chooser):
                    await file_chooser.set_files(file_path)
                
                # Wait for file chooser and handle it
                async with page.expect_file_chooser() as file_chooser_info:
                    # Click the element that triggers file chooser
                    dom_el = await browser.get_dom_element_by_index(element_index)
                    element = await browser.get_locate_element(dom_el)
                    if element:
                        await element.click()
                    else:
                        return ActionResult(error=f'Element at index {element_index} not found')
                
                file_chooser = await file_chooser_info.value
                await file_chooser.set_files(file_path)
                
                return ActionResult(extracted_content=f'Successfully uploaded file {file_path} via file chooser dialog', include_in_memory=True)
                
            except Exception as e:
                return ActionResult(error=f'File upload failed: {str(e)}')

        @self.registry.action("Smart file upload that tries multiple strategies including file dialog handling")
        async def smart_file_upload(element_index: int, file_path: str, browser: BrowserContext):
            try:
                if not os.path.exists(file_path):
                    return ActionResult(error=f'File {file_path} does not exist')
                
                page = await browser.get_current_page()
                
                # Strategy 1: Look for existing file inputs first
                file_inputs = await page.query_selector_all('input[type="file"]')
                if file_inputs:
                    await file_inputs[0].set_input_files(file_path)
                    return ActionResult(extracted_content=f'Uploaded file to existing input', include_in_memory=True)
                
                # Strategy 2: Click element and wait for file chooser dialog
                try:
                    async with page.expect_file_chooser() as file_chooser_info:
                        dom_el = await browser.get_dom_element_by_index(element_index)
                        element = await browser.get_locate_element(dom_el)
                        if element:
                            await element.click()
                        else:
                            return ActionResult(error=f'Element at index {element_index} not found')
                    
                    file_chooser = await file_chooser_info.value
                    await file_chooser.set_files(file_path)
                    return ActionResult(extracted_content=f'Successfully uploaded file via file chooser dialog', include_in_memory=True)
                    
                except Exception as dialog_error:
                    # Strategy 3: Try direct input handling
                    dom_el = await browser.get_dom_element_by_index(element_index)
                    element = await browser.get_locate_element(dom_el)
                    if element:
                        await element.click()
                        
                        # Wait for new file input to appear
                        for i in range(20):
                            await asyncio.sleep(0.1)
                            current_inputs = await page.query_selector_all('input[type="file"]')
                            if current_inputs:
                                await current_inputs[-1].set_input_files(file_path)
                                return ActionResult(extracted_content=f'Uploaded file to new input after click', include_in_memory=True)
                
                return ActionResult(error='Could not find file input element or handle file dialog')
                
            except Exception as e:
                return ActionResult(error=f'Smart upload failed: {str(e)}')


        @self.registry.action("Smart popup handler that can handle various popup types including address search")
        async def smart_popup_handler(element_index: int, search_text: str, browser: BrowserContext):
            try:
                page = await browser.get_current_page()
                
                # Click the element that opens popup first
                dom_el = await browser.get_dom_element_by_index(element_index)
                element = await browser.get_locate_element(dom_el)
                if element:
                    await element.click()
                else:
                    return ActionResult(error=f'Element at index {element_index} not found')
                
                # Wait for new page/popup to appear
                await asyncio.sleep(2)
                
                # Get all pages and find the newest one (popup)
                context = await browser.get_browser_context()
                all_pages = context.pages
                popup_page = all_pages[-1] if len(all_pages) > 1 else None
                
                if not popup_page:
                    return ActionResult(error='No popup window detected')
                
                try:
                    await popup_page.wait_for_load_state('domcontentloaded', timeout=10000)
                    await popup_page.wait_for_timeout(2000)  # Wait for popup to fully load
                    
                    # Strategy 1: Look for any text input and enter search text
                    text_inputs = await popup_page.query_selector_all('input[type="text"], input:not([type]), textarea, input')
                    search_success = False
                    
                    if text_inputs:
                        for input_field in text_inputs:
                            try:
                                is_visible = await input_field.is_visible()
                                is_enabled = await input_field.is_enabled()
                                
                                if is_visible and is_enabled:
                                    await input_field.fill(search_text)
                                    await popup_page.wait_for_timeout(500)
                                    
                                    # Look for submit button or press Enter
                                    submit_buttons = await popup_page.query_selector_all('button[type="submit"], input[type="submit"], button:has-text("검색"), button:has-text("찾기"), button:has-text("확인"), button')
                                    
                                    button_clicked = False
                                    for btn in submit_buttons:
                                        try:
                                            btn_visible = await btn.is_visible()
                                            if btn_visible:
                                                await btn.click()
                                                button_clicked = True
                                                break
                                        except:
                                            continue
                                    
                                    if not button_clicked:
                                        await input_field.press('Enter')
                                    
                                    await popup_page.wait_for_timeout(3000)  # Wait for results
                                    search_success = True
                                    break
                                    
                            except:
                                continue
                    
                    # Strategy 2: Look for clickable results and click the first one
                    if search_success:
                        await popup_page.wait_for_timeout(1000)
                        result_selectors = [
                            'tbody tr:first-child td:first-child',
                            'tr:first-child td:first-child', 
                            'tr:first-child td',
                            'tr:first-child',
                            '.result-item:first-child',
                            'li:first-child',
                            '.addr-item:first-child',
                            '.list-item:first-child'
                        ]
                        
                        for result_selector in result_selectors:
                            try:
                                result_item = await popup_page.query_selector(result_selector)
                                if result_item:
                                    is_visible = await result_item.is_visible()
                                    text_content = await result_item.text_content()
                                    
                                    if is_visible and text_content and len(text_content.strip()) > 0:
                                        await result_item.click()
                                        await popup_page.wait_for_timeout(1000)
                                        break
                            except:
                                continue
                    
                    # Close popup if it's still open
                    if not popup_page.is_closed():
                        await popup_page.close()
                    
                    return ActionResult(extracted_content=f'Successfully handled popup with search text: {search_text}', include_in_memory=True)
                        
                except Exception as popup_error:
                    return ActionResult(error=f'Error in smart popup handling: {str(popup_error)}')
                
            except Exception as e:
                return ActionResult(error=f'Smart popup handling failed: {str(e)}')

controller = EnhancedController()


async def main():
	task = """
	1. https://www.safetyreport.go.kr/#safereport/safereport3 접속
	2. 자동차·교통 위반 신고 유형 은 이륜차 위반 으로 선택
	3. 사진/동영상에서 파일 추가 버튼을 찾고, smart_file_upload 액션을 사용해서 C:/Users/LGCNS/Desktop/KakaoTalk_20250727_124336306.mp4 파일을 업로드해줘.
	4. 신고 발생 지역에서 위치 찾기 버튼을 찾고, smart_popup_handler 액션을 사용해서 "양화로 186"을 검색하고 선택해줘. 새 창이 열리더라도 자동으로 처리됩니다.
	
	참고사항:
	- 파일 업로드: smart_file_upload 액션이 파일 익스플로러 대화상자를 자동 처리
	- 주소 검색: smart_popup_handler 또는 handle_address_popup 액션이 팝업창을 자동 처리
	- 새 창이나 팝업이 열리면 자동으로 주소를 검색하고 첫 번째 결과를 선택합니다
    - 원하는 내용이 뜨지 않을 경우엔 스크롤을 이동합니다.
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