import PySimpleGUI as sg
from threading import Lock

from PIL import Image
from io import BytesIO
import base64
import sys

from lmscore import Lms
from b64icons import Icons

NAME = 'L'
VERSION = '20240208'
WINDOW_TITLE = f'{NAME}'
WINDOW_THEME = 'DarkBlue3'
POPUP_THEME = 'GrayGrayGray'

sg.theme(WINDOW_THEME)
# True if PyInstaller bundled
_BUNDLED = getattr(sys, 'frozen', False)

WIDTH_SECTION = 56
WIDTH_NAME = 6
WIDTH_ELEMENT = WIDTH_SECTION - WIDTH_NAME - 1
FONTSTRING = 'Consolas 8'
BROWSER_SIZE_W = 1080
BROWSER_SIZE_H = 580
IMG_SIZE_W = 650
IMG_SIZE_H = 320
IMG_SIZE = (IMG_SIZE_W, IMG_SIZE_H)
BROWSER_SIZE = f'{BROWSER_SIZE_W},{BROWSER_SIZE_H}'

SCROLL_AMOUNT = 50

DEFAULT_URL = 'https://www.gbeti.or.kr'

class K:
    pass
K.CHECK_Display = 'CHECK_Display'
K.BTN_Close     = 'BTN_Close'
K.TAB_Login     = 'TAB_Login'
K.TAB_List      = 'TAB_List'
K.TAB_Progress  = 'TAB_Progress'
K.INPUT_URL     = 'INPUT_URL'
K.INPUT_ID      = 'INPUT_ID'
K.INPUT_PW      = 'INPUT_PW'
K.BTN_Login     = 'BTN_Login'
K.SHOW_BROWSER  = 'SHOW_BROWSER'
K.LIST_Courses  = 'LIST_Courses'
K.TEXT_Sub1     = 'TEXT_Subject1'
K.TEXT_Sub2     = 'TEXT_Subject2'
K.TEXT_Time     = 'TEXT_Time'
K.PBAR_Time     = 'PBAR_Time'
K.LOG           = 'OUTPUT_Log'
K.IMG           = 'OUTPUT_Img'

def log(*args, **kwargs):
    print(f'[{NAME}]',*args, **kwargs)

def Name(text, w=WIDTH_NAME, **kwargs):
    return sg.Text(text, **kwargs, size=w, justification='r')

def Collapsible(layout, key, title='', arrows=('-','+'), collapsed=False):
    """
    User Defined Element
    A "collapsable section" element. Like a container element that can be collapsed and brought back
    :param layout:Tuple[List[sg.Element]]: The layout for the section
    :param key:Any: Key used to make this section visible / invisible
    :param title:str: Title to show next to arrow
    :param arrows:Tuple[str, str]: The strings to use to show the section is (Open, Closed).
    :param collapsed:bool: If True, then the section begins in a collapsed state
    :return:sg.Column: Column including the arrows, title and the layout that is pinned
    """
    return sg.Column([[sg.T((arrows[1] if collapsed else arrows[0]), enable_events=True, k=key+'-ARROW'),
                       sg.T(title, enable_events=True, key=key+'-TITLE')],
                      [sg.pin(sg.Column(layout, key=key, visible=not collapsed, metadata=arrows))]], pad=(0,0))

class LmsGui():
    def __init__(self):
        self.core = None
        self.lock = Lock()
        sg.set_options(font=FONTSTRING)
        image =    sg.Image('', s=IMG_SIZE, visible=False, k=K.IMG)
        topbar =    [sg.Col([
                         [sg.T(f'{NAME} v{VERSION}', size=26)],
                     ], p=0, element_justification='l'),
                     sg.Col([
                        [sg.Checkbox('화면 보기', default=False, enable_events=True, k=K.CHECK_Display), 
                         sg.Button(image_data=Icons.CLOSE, k=K.BTN_Close, disabled=True)]], p=0, element_justification='r'),
                         sg.T('강의 닫기')
                    ]
        if _BUNDLED:
            topbar.insert(1, sg.Sizer(20, 16))
        else:
            topbar.insert(1, sg.Button(image_data=Icons.bCLOSE, k='DBGBTN1'))
        layout1 =   Collapsible(
                        [[Name('URL'), sg.Input(DEFAULT_URL, s=WIDTH_ELEMENT, k=K.INPUT_URL)],
                         [sg.Col([[Name('ID'), sg.Input(s=15, k=K.INPUT_ID)], [Name('PW'), sg.Input(s=15, password_char='*', k=K.INPUT_PW)]
                                 ],p=0),
                          sg.Button('로그인', s=(10,2), k=K.BTN_Login),
                          sg.Checkbox('브라우저 창 열기', default=False, k=K.SHOW_BROWSER)]]
                        , K.TAB_Login, '로그인')
        layout2 =   Collapsible([[sg.Listbox(values=[], s=(WIDTH_SECTION,3), bind_return_key=True, k=K.LIST_Courses)]]
                        , K.TAB_List, '수강 과정')
        layout3 =   Collapsible(
                        [[sg.T('', k=K.TEXT_Sub1)],
                         [sg.T('', k=K.TEXT_Sub2)],
                         [sg.T('', k=K.TEXT_Time, justification='c')],
                         [sg.ProgressBar(100, s=(35,24), orientation='h', k=K.PBAR_Time)]]  # size????
                    , K.TAB_Progress, '진행도', collapsed=True)
        # output =   sg.Output(s=(WIDTH_SECTION,8), k=K.LOG)
        self.layout = [[image,
                        sg.vtop(sg.Col([topbar, [layout1], [layout2], [layout3], [sg.Sizer(380, 0)]]))]]
                        # sg.Col([[layout1],[layout2],[layout3],[output]])]]
    def close(self):
        self.window = None
        self.core.close() if self.core else None

    def collapse_tab(self, key, visible=None):
        key = key.split('-')[0]
        element = self.window[key]
        visible = visible if visible != None else not element.visible
        element.update(visible=visible)
        arrow = self.window[key+'-ARROW']
        arrow.update(element.metadata[1] if not visible else element.metadata[0])

    def popup(self, text, *args, **kwargs):
        sg.theme(POPUP_THEME)
        l = len(text)
        if l < 20:
            l = (20 - l) // 2
            text = ' ' * l + text + ' ' * l + '\x00'
        sg.popup(text, *args, **kwargs, location=self.window.mouse_location(), 
                 grab_anywhere=True, modal=False, auto_close=True, auto_close_duration=5,
                 any_key_closes=True)
        sg.theme(WINDOW_THEME)

    def show(self):
        self.window = sg.Window(WINDOW_TITLE, self.layout, finalize=True, return_keyboard_events=True, 
                                enable_close_attempted_event=True, location=sg.user_settings_get_entry('-LOCATION-', (None, None)),
                                right_click_menu=sg.MENU_RIGHT_CLICK_DISABLED)
        self.wUrl   = self.window[K.INPUT_URL]
        self.wId    = self.window[K.INPUT_ID]
        self.wPw    = self.window[K.INPUT_PW]
        self.wBrowser = self.window[K.SHOW_BROWSER]
        self.wList  = self.window[K.LIST_Courses]
        self.wSubj1 = self.window[K.TEXT_Sub1]
        self.wSubj2 = self.window[K.TEXT_Sub2]
        self.wTime  = self.window[K.TEXT_Time]
        self.wPbar  = self.window[K.PBAR_Time]
        self.wSubj1.data = ''
        self.wSubj2.data = ''
        self.wTime.data = ''
        self.wPbar.data = ''
        # self.wLog   = self.window[K.LOG]
        self.wImg   = self.window[K.IMG]

    def main(self):
        w = self.window
        try:
            while True:
                event, values = w.read(timeout=100)
                self.refresh()
                if event in ('Exit', sg.WINDOW_CLOSE_ATTEMPTED_EVENT):
                    sg.user_settings_set_entry('-LOCATION-', w.current_location())
                    break
                elif event == 'MouseWheel:Up':
                    self.core.scroll(0, -SCROLL_AMOUNT) if self.core else None
                elif event == 'MouseWheel:Down':
                    self.core.scroll(0, SCROLL_AMOUNT) if self.core else None
                elif event == K.CHECK_Display:
                    visible = values[event]
                    self.wImg.update(visible=visible)
                elif event == K.BTN_Close:
                    if self.core:
                        self.core.stop = True
                elif event == 'DBGBTN1':    
                    break
                # Collapsible
                elif event.startswith('TAB_'):
                    self.collapse_tab(event)
                elif event == 'REFRESH':
                    pass
                elif event == K.BTN_Login:
                    w.start_thread(lambda: self.login(self.wId.get(), self.wPw.get(), self.wUrl.get(), self.wBrowser.get()), 'LOGIN-END')

                elif event == 'LOGIN-END':
                    if values[event]:   # Error
                        self.popup(values[event])
                    else:   # No Error
                        w.write_event_value('GET-COURSE', 1)
                elif event == 'GET-COURSE':
                    w.start_thread(self.get_course, 'GET-COURSE-END')
                elif event == 'GET-COURSE-END':
                    list_courses = []
                    for i in range(len(self.core.courseList)):
                        list_courses.append(self.core.courseList[i]['text'].strip())
                    self.wList.update(values=list_courses)
                elif event == K.LIST_Courses:
                    w[K.BTN_Close   ].update(disabled=False)
                    num = int(values[event][0][:4].strip()[1:-1])
                    w.start_thread(lambda: self.set_course(num-1), 'LEARN-END')
                elif event == 'LEARN-END':
                    message = values[event]
                    self.wSubj1.data = ''
                    self.wSubj2.data = ''
                    self.wTime.data = ''
                    self.wPbar.data = ''
                    w[K.BTN_Close   ].update(disabled=True)

                    if message == 'SUCCESS':
                        self.popup('수강 종료')
                    else:
                        self.popup(message)
                    w.write_event_value('GET-COURSE', 1)
        finally:
            if _BUNDLED:
                self.close()

    def login(self, id, pw, url, noheadless):
        with self.lock:
            self.core = self.core or Lms(self, url, noheadless, BROWSER_SIZE)
            self.request_refresh()
            error = self.core.login(id, pw)
            if not error:
                self.collapse_tab(K.TAB_Login, visible=False)
                self.collapse_tab(K.TAB_Progress, visible=True)
            return error
    def get_course(self):
        with self.lock:
            return self.core.get_course()
    def set_course(self, num):
        with self.lock:
            return self.core.set_course(num)

    # Update from not-main-thread
    def request_refresh(self):
        self.window.write_event_value('REFRESH', 0)

    def refresh(self):
        if self.core:
            if self.wImg.visible:
                try:
                    img = Image.open(BytesIO(base64.b64decode(self.core.driver.get_screenshot_as_base64())))
                    #ratio = min(IMG_SIZE_W / img.size[0], IMG_SIZE_H / img.size[1])
                    ratio = IMG_SIZE_H / img.size[1]
                    IMG_SIZE = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                    img = img.resize(IMG_SIZE)
                    b64 = BytesIO()
                    img.save(b64, format='PNG')
                    self.wImg.update(data=b64.getvalue(), size=IMG_SIZE)
                except:
                    pass
            self.wSubj1.update(self.wSubj1.data)
            self.wSubj2.update(self.wSubj2.data)
            self.wTime.update(self.wTime.data)
            self.wPbar.update(self.wPbar.data)

if __name__ == '__main__':
    Gui = LmsGui()
    Gui.show()
    Gui.main()

