from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import selenium.common.exceptions as SeleniumException
import time, os, sys
import getpass, urllib3, argparse

VERSION = "20240208"

class Lms:
    def __init__(self, gui, url, noheadless, size):
        os.environ["WDM_SSL_VERIFY"] = "0"
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        options = webdriver.ChromeOptions()
        options.add_argument("--log-level=3")
        im_not_headless = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        options.add_argument("user-agent=" + im_not_headless)
        if not noheadless:
            options.add_argument("--headless")
        options.add_argument("--window-size=" + size)
        options.add_argument("--disable-gpu")
        options.add_argument("--hide-scrollbars")
        options.add_argument("--mute-audio")
        options.add_argument("--autoplay-policy=no-user-gesture-required")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        self.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
        self.driver.implicitly_wait(3)
        self.hMain = self.driver.current_window_handle
        self.delay = 1
        self.wait = WebDriverWait(self.driver, timeout=10)
        self.url = url
        self.courseList = []
        self.gui = gui
        self.stop = False
    def __del__(self):
        self.close()
    def close_popups(self):
        while len(self.driver.window_handles) > 1:
            for handle in self.driver.window_handles:
                if handle != self.hMain:
                    self.driver.switch_to.window(handle)
                    self.driver.close()
        self.driver.switch_to.window(self.hMain)
    def login(self, userID=None, userPW=None):
        try:
            print("* 로그인 중...")
            self.driver.get(self.url + "/system/login/login.do")
            self.close_popups()
            self.gui.request_refresh()

            login_id = self.driver.find_element(By.CSS_SELECTOR, "#userInputId")
            login_id.click()

            webdriver.ActionChains(self.driver)\
                .pause(1)\
                .send_keys(userID).send_keys(Keys.TAB)\
                .pause(1)\
                .send_keys(userPW).perform()
            self.gui.request_refresh()
            webdriver.ActionChains(self.driver)\
                .pause(1)\
                .send_keys(Keys.ENTER)\
                .pause(3)\
                .perform()
        except Exception as e:
            print(" ...... 오류")
            return "Error"
        else:
            self.close_popups()
            try:
                if self.driver.current_url.find("login") > 0:
                    print(" ...... 실패")
                    return "다시 로그인하세요"
                print(" ...... 성공")
                return None
            except SeleniumException.UnexpectedAlertPresentException as e:
                print(" ...... 실패")
                return e.alert_text
    def get_course(self):
        print("\n* 과정 선택")
        self.driver.get(self.url + "/lh/ms/cs/atnlcListView.do?menuId=3000000101")

        self.driver.find_elements(By.CSS_SELECTOR, "#crseList > li")
        courses = self.driver.find_elements(By.CSS_SELECTOR, "#crseList > li")

        self.courseList = []
        for i in range(len(courses)):
            text = courses[i].find_element(By.CSS_SELECTOR, "a.title").text
            if len(text) > 40:
                text = text[:36] + "..."
            button = ""
            for abtn in courses[i].find_elements(By.CSS_SELECTOR, "a"):
                if abtn.text == "이어보기" or abtn.text == "학습하기":
                    button = abtn
                    break
            self.courseList.append({ 'text': f"  [{i+1}] {text}", 'obj': button})
        for i in range(len(self.courseList)):
            print(self.courseList[i]['text'])
        return self.courseList
    def set_course(self, num):
        if num not in range(len(self.courseList)):
            num = 0
        num_windows = len(self.driver.window_handles)
        try:
            self.courseList[num]['obj'].click()
            time.sleep(2)
        except SeleniumException.UnexpectedAlertPresentException as e:
            print("\n* 경고 - " + e.alert_text)
            self.driver.switch_to.alert().accept()
            return e.alert_text
        except Exception as e:
            print("\n* 오류 발생 - " + str(e))
            return 'ERROR'
        else:
            self.hLearn = self.get_new_window(num_windows)
            self.driver.switch_to.window(self.hLearn)
            self.learn(self.gui_progress)
            return 'SUCCESS'

    def select_course(self):
        for i in range(len(self.courseList)):
            print(self.courseList[i]['text'])
        print("  [0] 종료하기")
        num = int(input("\n  과정을 선택하세요 [1]: ") or "1") - 1
        if num == -1:
            self.close()
        else:
            if num not in range(len(self.courseList)):
                num = 0
            num_windows = len(self.driver.window_handles)
            self.courseList[num]['obj'].click()
            time.sleep(2)
            self.hLearn = self.get_new_window(num_windows)
            self.driver.switch_to.window(self.hLearn)
            self.learn()
    def get_new_window(self, num_windows_before):
        self.wait.until(EC.number_of_windows_to_be(num_windows_before + 1))
        return self.driver.window_handles[-1]
    def return_to_main(self):
        self.driver.switch_to.window(self.hMain)
    def learn(self, progress_func):
        return_status = ''
        print("\n* 수강 시작")
        current_subject = " "
        current_section = " "
        current_subsect = " "
        current_progress = 0.0
        # Get First Button
        startbutton = self.driver.find_element(By.CSS_SELECTOR, 'a.btn_learning_list')
        if startbutton.is_displayed():
            startbutton.click()
            time.sleep(2)
        try:
            while not self.stop:
                time.sleep(self.delay)
                subject = self.driver.find_element(By.CSS_SELECTOR, "div.class_list p.title_box").text.strip()
                section = self.driver.find_element(By.CSS_SELECTOR, "div.class_list_box.ing li.play div a").text.strip()
                if not section or section == "학습하기":
                    section = self.driver.find_element(By.CSS_SELECTOR, "div.class_list_box.ing p").text.strip()
                subsect = self.driver.find_element(By.CSS_SELECTOR, "#page-info").text.strip()
                if subject and subject != current_subject:
                    print(f"\r[차시]: {subject}")
                    self.gui.wSubj1.data = f"[차시]: {subject}"
                    current_subject = subject
                elif section and section != current_section:
                    print(f"\r  [강의]: {section} [{subsect}]")
                    self.gui.wSubj2.data = f"[강의]: {section} [{subsect}]"
                    current_section = section
                    current_subsect = subsect
                elif subsect and subsect != current_subsect:
                    print(f"\r  [강의]: {section} [{subsect}]")
                    self.gui.wSubj2.data = f"[강의]: {section} [{subsect}]"
                    current_subsect = subsect
                progress = float(self.driver.find_element(By.CSS_SELECTOR, "#lx-player div.vjs-progress-holder").get_attribute("aria-valuenow"))
                progress_time = self.driver.find_element(By.CSS_SELECTOR, "#lx-player div.vjs-progress-holder").get_attribute("aria-valuetext").strip().split()
                is_quizpage = self.driver.find_element(By.CSS_SELECTOR, "#quizPage").is_displayed()
                if len(progress_time) > 0:
                    played = progress_time[0]
                    length = progress_time[2]
                playbutton = self.driver.find_element(By.CSS_SELECTOR, "button.vjs-big-play-button")
                if progress == current_progress:
                    if is_quizpage:
                        print(f"\r    [퀴즈]")
                        self.gui.wSubj2.data = f"[퀴즈]"
                        current_progress = 100.0
                    elif played == length:
                        current_progress = 100.0
                        time.sleep(1)
                    elif playbutton.is_displayed():
                        print(f"\r! 재생 시작")
                        playbutton.click()
                else:
                    current_progress = progress
                progress_func(current_progress, played, length)
                if current_progress >= 100.0:
                    self.driver.execute_script("next_ScoBtn()")
            return_status = 'CLOSE'
        except SeleniumException.UnexpectedAlertPresentException as e:
            print("\n* 경고 - " + e.alert_text)
            #self.driver.switch_to.alert.accept()
            return_status = e.alert_text
        except SeleniumException.JavascriptException as e:
            print("\n* 수강 완료")
            return_status = 'FINISH'
        except Exception as e:
            print("\n* 오류 발생 - " + str(e))
            return_status = 'ERROR'
        except KeyboardInterrupt:
            time.sleep(2)

        if self.driver.service.is_connectable():
            self.stop = False
            self.driver.close()
            self.return_to_main()
        else:
            return_status = 'ERROR'
            print("\n* 종료합니다.\n")
            sys.exit(1)
        return return_status
    def gui_progress(self, progress = '', elapsed = '', total = ''):
        self.gui.wTime.data = f'{elapsed} / {total}'
        self.gui.wPbar.data = progress

    def print_progress(self, progress, played = "", length = ""):
        strLength = min(50, os.get_terminal_size().columns - 30)
        fillLength = int(round(strLength * progress / 100))
        filledStr = "-" * fillLength + " " * (strLength - fillLength)
        print(f"\r    [{played:>5} / {length:>5}] [{filledStr}] {progress:05.2f}%", end="", flush=True)
    def close(self):
        print("\n* 종료합니다.")
        if self.driver.service.is_connectable():
            self.driver.quit()
        sys.exit(0)
    def scroll(self, h, v):
        webdriver.ActionChains(self.driver).scroll_by_amount(h, v).perform()
    def get_screenshot(self):
        return self.driver.get_screenshot_as_base64()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(usage="%(prog)s [url]",
        description="",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        #add_help=False
        )
    default_url = "https://www.gbeti.or.kr"
    parser.add_argument("url", metavar="url", nargs="?", help="Target URL", default=default_url)
    parser.add_argument("-b", "--broswer", "--show", help="Show browser window(Not headless mode)", action="store_true")
    parser.add_argument("-s", "--size", help="Window size", metavar="w,h", default="1280,720")
    args = parser.parse_args()

    print(f"\n  강의 듣기 v{VERSION}\n")
    print("* options")
    vargs = vars(args)
    for k in vargs:
        print(f"{k:>12}: {vargs[k]}")
    lms = Lms(url=args.url, noheadless=args.broswer, size=args.size)
    userID = input("  ID: ")
    userPW = getpass.getpass("  PW: ")
    lms.login(userID, userPW)
    lms.select_course()
