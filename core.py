from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import selenium.common.exceptions as SeleniumException
import time, os, urllib3

class LmsCore:
    def __init__(self, gui, headless = True, size = "1080,580"):
        self.delay = 0.3
        self.courseList = []
        self.gui = gui
        self.stop = False
        os.environ["WDM_SSL_VERIFY"] = "0"
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        options = webdriver.ChromeOptions()
        options.add_argument("--log-level=3")
        options.add_argument("--headless")
        options.add_argument("--window-size=" + size)
        options.add_argument("--disable-gpu")
        options.add_argument("--hide-scrollbars")
        options.add_argument("--mute-audio")
        options.add_argument("--autoplay-policy=no-user-gesture-required")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])

        driver_path = os.path.join(os.path.dirname(ChromeDriverManager().install()), "chromedriver.exe")

        # driver = webdriver.Chrome(service=ChromeService(driver_path), options=options)
        # driver.implicitly_wait(1)
        # user_agent = driver.execute_script("return navigator.userAgent")
        # driver.quit()
        # print(f"* Got User-Agent: {user_agent}")

        # user_agent = user_agent.replace("HeadlessChrome", "Chrome")
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36'
        print(f"* Set User-Agent: {user_agent}")
        options.add_argument("user-agent=" + user_agent)
        self.driver = webdriver.Chrome(service=ChromeService(driver_path), options=options)
        self.driver.implicitly_wait(1)

        self.hMain = self.driver.current_window_handle
        self.wait = WebDriverWait(self.driver, timeout=10)

    def __del__(self):
        if self.driver:
            self.close()

    def set_base_url(self, url):
        self.url = url

    def close_popups(self):
        while len(self.driver.window_handles) > 1:
            for handle in self.driver.window_handles:
                if handle != self.hMain:
                    self.driver.switch_to.window(handle)
                    self.driver.close()
        self.driver.switch_to.window(self.hMain)

    def login(self, url='', userID=None, userPW=None):
        self.set_base_url(url)
        try:
            print("* 로그인 중...")
            self.driver.get(self.url + "/system/login/login.do")
            self.close_popups()
            login_id = self.driver.find_element(By.CSS_SELECTOR, "#userInputId")
            login_id.click()
            webdriver.ActionChains(self.driver).pause(0.5)\
                .send_keys(userID).send_keys(Keys.TAB).pause(0.5)\
                .send_keys(userPW).pause(0.5)\
                .send_keys(Keys.ENTER).pause(1)\
                .perform()
        except Exception as e:
            e.add_note("+ 로그인 실패")
            raise
        else:
            self.close_popups()
            try:
                if self.driver.current_url.find("login") > 0:
                    raise Exception()
                print(" ...... 성공")
            except SeleniumException.UnexpectedAlertPresentException as e:
                e.add_note(e.alert_text)
                raise
            except Exception as e:
                e.add_note("+ 로그인 실패")
                raise

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

    def enter_course(self, num, signal):
        if num not in range(len(self.courseList)):
            num = 0
        num_windows = len(self.driver.window_handles)
        try:
            self.courseList[num]['obj'].click()
            time.sleep(2)
        except SeleniumException.UnexpectedAlertPresentException as e:
            print("\n* 경고 - " + e.alert_text)
            self.driver.switch_to.alert().accept()
            e.add_note(e.alert_text)
            raise
        except Exception as e:
            print("\n* 오류 발생 - " + str(e))
            raise
        else:
            self.hLearn = self.get_new_window(num_windows)
            self.driver.switch_to.window(self.hLearn)
            return self.learn(signal)

    def get_new_window(self, num_windows_before):
        self.wait.until(EC.number_of_windows_to_be(num_windows_before + 1))
        return self.driver.window_handles[-1]

    def return_to_main(self):
        self.driver.switch_to.window(self.hMain)

    def learn(self, signal):
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
                vjs_controlbar = self.driver.find_element(By.CSS_SELECTOR, "div.vjs-control-bar")
                if str(vjs_controlbar.value_of_css_property("opacity")) != "1":
                    # Show video player control bar
                    # Set best playback rate. The rate is saved in 'Local storage'.
                    self.driver.execute_script('''
                        document.querySelector('div.vjs-control-bar').style.opacity = 1
                        document.querySelector('.vjs-playback-rate.vjs-menu-button .vjs-menu-item').click()
                    ''')
                time.sleep(self.delay)
                subject = self.driver.find_element(By.CSS_SELECTOR, "div.class_list p.title_box").text.strip()
                section = self.driver.find_element(By.CSS_SELECTOR, "div.class_list_box.ing li.play div a").text.strip()
                if not section or section == "학습하기":
                    section = self.driver.find_element(By.CSS_SELECTOR, "div.class_list_box.ing p").text.strip()
                subsect = self.driver.find_element(By.CSS_SELECTOR, "#page-info").text.strip()
                if subject[1:3] == '차시':
                    subject = subject[:3] + '> ' + subject[3:]
                elif subject[2:4] == '차시':
                    subject = subject[:4] + '> ' + subject[4:]
                if subject and subject != current_subject:
                    print(f"\r[차시]: {subject}")
                    signal.emit([1, f"{subject}"])
                    current_subject = subject
                elif section and section != current_section:
                    print(f"\r  [강의]: {section} [{subsect}]")
                    signal.emit([2, f"{section} [{subsect}]"])
                    current_section = section
                    current_subsect = subsect
                elif subsect and subsect != current_subsect:
                    print(f"\r  [강의]: {section} [{subsect}]")
                    signal.emit([2, f"{section} [{subsect}]"])
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
                        signal.emit([2, "- 퀴즈 -"])
                        current_progress = 100.0
                    elif played == length:
                        current_progress = 100.0
                        time.sleep(1)
                    elif playbutton.is_displayed():
                        print(f"\r! 재생 시작")
                        playbutton.click()
                else:
                    current_progress = progress
                signal.emit([0, current_progress, played, length])
                if current_progress >= 100.0:
                    self.driver.execute_script("next_ScoBtn()")
            return_status = 'CLOSE'
            signal.emit([-1])
        except SeleniumException.UnexpectedAlertPresentException as e:
            print("\n* 경고 - " + e.alert_text)
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
            #sys.exit(1)
        return return_status

    def close(self):
        print("\n* 종료합니다.")
        if self.driver.service.is_connectable():
            self.driver.quit()
            self.driver = None

    def scroll(self, h, v):
        webdriver.ActionChains(self.driver).scroll_by_amount(h, -v).perform()
