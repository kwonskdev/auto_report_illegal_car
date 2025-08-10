from dataclasses import dataclass
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
import time
import os
import pyautogui


@dataclass
class ReportInfo:
    title: str
    contents: str
    # phone: str
    violation_type: str  # ex. "10"
    file_name: str       # ex. "temp.mp4"
    address_query: str   # ex. "판교역로 166"
    report_datetime: datetime


def login_safety_rul(driver, wait):
    # 로그인

    driver.get("https://www.safetyreport.go.kr/#/main/login/login")

    id_input = wait.until(EC.presence_of_element_located((By.ID, "username")))
    id_input.clear()
    id_input.send_keys("parkij94")

    pw_input = driver.find_element(By.ID, "password")
    pw_input.clear()
    pw_input.send_keys("dlswnssl12!")

    buttons = driver.find_elements(By.CSS_SELECTOR, "button.button.big.blue")
    for btn in buttons:
        if "로그인" in btn.text:
            btn.click()
            break
    time.sleep(2)
    wait.until(EC.url_changes("https://www.safetyreport.go.kr/#main/login/login"))
    print("로그인 완료")


def get_stealth_script():
    return """
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
        Object.defineProperty(navigator, 'languages', { get: () => ['ko-KR', 'ko'] });
        window.chrome = { runtime: {}, app: { isInstalled: false } };
    """


def init_driver():
    # chrome driver option 옵션 세팅
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-session-crashed-bubble")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": get_stealth_script()})
    return driver


def click_cancel_button(img_path="cancel_button.png"):
    # 취소 버튼 클릭용
    try:
        btn_location = pyautogui.locateOnScreen(img_path, confidence=0.9)
        if btn_location:
            pyautogui.click(pyautogui.center(btn_location))
            print("취소버튼 클릭 완료")
    except Exception:
        print("취소 버튼 없음")


def select_violation_type(driver, violation_type):
    # 위반 종류 select
    '''
        Args:
            violation_type : {
                "02" : 교통위반,
                "03" : 이륜차 위반,
                "10" : 난폭/보복운전,
                "05" : 버스 전용차로 위반(고속도로 제외),
                "06" : 번호판 규정 위반,
                "07" : 불법등화, 반사판 가림 손상,
                "08" : 불법 튜닝, 해체, 조작
                "09" : 기타 자동차 안전기준 위반
                }
    '''
    select_elem = driver.find_element(By.CSS_SELECTOR, "span.bbs_sh select")
    select_obj = Select(select_elem)
    select_obj.select_by_value(violation_type)

def upload_file(driver, wait, file_name):
    # 지정경로 파일 업로드
    iframe = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[id^='raonkuploader_']")))
    driver.switch_to.frame(iframe)
    file_path = os.path.join(os.getcwd(), file_name)
    file_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']")))
    file_input.send_keys(file_path)
    driver.switch_to.default_content()

def find_location(driver, wait, address_query): 
    # 해당 사이트에서 위치 찾기
    driver.find_element(By.ID, "btnFindLoc").click()
    main_window = driver.current_window_handle

    # 새 창으로 전환
    for handle in driver.window_handles:
        if handle != main_window:
            driver.switch_to.window(handle)
            break

    WebDriverWait(driver, 10).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "__daum__viewerFrame_1")))
    input_box = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "region_name")))
    input_box.send_keys(address_query)
    driver.find_element(By.CSS_SELECTOR, "button.btn_search").click()
    first_address_li = driver.find_element(By.CSS_SELECTOR, "li.list_post_item[data-index='1']")
    link_post_button = first_address_li.find_element(By.CSS_SELECTOR, "button.link_post")
    link_post_button.click()

    # 메인 윈도우로 다시 전환
    driver.switch_to.window(main_window)

def fill_report_form(driver, report_info: ReportInfo):
    # 신고서 작성

    # 제목
    driver.find_element(By.ID, "C_A_TITLE").send_keys(report_info.title)
    # 신고 내용
    driver.find_element(By.ID, "C_A_CONTENTS").send_keys(report_info.contents)
    # 차량 번호 없음 체크
    checkbox = driver.find_element(By.ID, "chkNoVhrNo")
    if not checkbox.is_selected():
        checkbox.click()

    # 발생 일시 입력
    driver.find_element(By.ID, "DEVEL_DATE").send_keys(report_info.report_datetime.strftime("%Y-%m-%d"))
    Select(driver.find_element(By.ID, "DEVEL_TIME_HH")).select_by_value(report_info.report_datetime.strftime("%H"))
    Select(driver.find_element(By.ID, "DEVEL_TIME_MM")).select_by_value(report_info.report_datetime.strftime("%M"))
    
    
    # 로그인 시 불 필요 항목
    # 휴대전화 입력
    phone_input = driver.find_element(By.ID, "C_PHONE2")
    phone_input.clear()
    # phone_input.send_keys(report_info.phone)
    phone_input.send_keys("01095259873")
    # 인증번호 받기 버튼 클릭
    driver.find_element(By.ID, "authSelectBtn").click()
    # 팝업 내 문자 인증 버튼 클릭 (대기 포함)
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "div#smsAuth > button.ico_message.btnRequestPhoneAuthNo"))
    ).click()

def run_report(report_info: ReportInfo):
    driver = init_driver()
    wait = WebDriverWait(driver, 15)
    # login_safety_rul(driver, wait)
    driver.get("https://www.safetyreport.go.kr")

    try:
        # 신고하기 탭 클릭
        wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href,'#safereport')]"))).click()
        time.sleep(3)
        click_cancel_button()

        # 자동차 신고 탭 클릭
        wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@href='#safereport/safereport3']"))).click()
        time.sleep(3)
        click_cancel_button()

        # 위반 유형 선택
        select_violation_type(driver, report_info.violation_type)

        # 파일 업로드
        upload_file(driver, wait, report_info.file_name)

        # 위치 찾기
        find_location(driver, wait, report_info.address_query)

        # 신고 양식 작성 
        fill_report_form(driver, report_info)

        print("신고가 완료되었습니다.")
        
    except Exception as e:
        print("신고 중 오류 발생:", e)
    finally:
        time.sleep(500000)

        driver.quit()

if __name__ == "__main__":
    
    sample_report = ReportInfo(
        title="난폭운전 신고",
        contents="난폭운전 행위를 목격했습니다.",
        # phone="01095259873",
        violation_type="08",
        file_name="temp.mp4",
        address_query="판교역로 166",
        report_datetime=datetime.now()
    )
    run_report(sample_report)
