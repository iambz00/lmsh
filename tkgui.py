import tkinter as tk
import tkinter.ttk as ttk
from threading import Thread, Lock

from PIL import Image, ImageTk
from io import BytesIO
import base64, os, sys
from time import sleep

from tkcore import Lms
from b64icons import Icons

NAME = 'L'
VERSION = '0.4'
WINDOW_TITLE = f'{NAME} {VERSION}'
RESOURCE_DIR = 'Res'
WINDOW_ICON = 'file_code_icon_245987.ico'

# True if PyInstaller bundled
_BUNDLED = getattr(sys, 'frozen', False)
if _BUNDLED:
    WINDOW_ICON = os.path.join(RESOURCE_DIR, WINDOW_ICON)
else:
    WINDOW_ICON = os.path.join('icons', WINDOW_ICON)

BROWSER_SIZE_W = 1080
BROWSER_SIZE_H = 720
IMG_SIZE_W = 540
IMG_SIZE_H = 360
IMG_SIZE = (IMG_SIZE_W, IMG_SIZE_H)
BROWSER_SIZE = f'{BROWSER_SIZE_W},{BROWSER_SIZE_H}'

POLLING_DELAY = 200

MWHEEL_DELTA_UNIT = 120 # For Windows
SCROLL_AMOUNT = 40

DEFAULT_URL = 'https://www.gbeti.or.kr'

class LmsGui():
    class State():
        def __init__(self):
            self.statusbar = ''
            self.get_course = False
            self.clear()
        def clear(self):
            self.learning = False
            self.courseinfo1 = ''
            self.courseinfo2 = ''
            self.progress = 0.0
            self.played = ''
            self.length = ''

    def __init__(self):
        self.core = None
        self.ready = False
        self.lock = Lock()
        self.state = self.State()
        self.closed = False
        self.w = {}
        self.init_gui()
        self.state.statusbar = '준비 중... Headless Chrome'
        Thread(target=self.core_ready).start()
        self.window.after(POLLING_DELAY, self.poller)
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.window.mainloop()

    def init_gui(self):
        self.window = tk.Tk()
        self.window.title(WINDOW_TITLE)
        self.window.iconbitmap(WINDOW_ICON)
        #self.window.geometry()
        self.window.config(padx = 4)
        self.window.resizable(False, False)

        self.w['LeftPane'] = tk.Frame(self.window)  # Topbar
        self.w['RightPane'] = tk.Frame(self.window) # Login
        self.w['LeftPane'].pack(side='left', fill='y')
        #self.w['RightPane'].pack(side='left', fill='y')

        self.w['1.Topbar'] = tk.Frame(self.w['LeftPane'], relief="groove", bd=2)   # Topbar
        self.w['2.Login' ] = tk.LabelFrame(self.w['LeftPane'], text=" Login "     , padx=8, pady=8) # Login
        self.w['3.Course'] = tk.LabelFrame(self.w['LeftPane'], text=" CourseList ", padx=8, pady=8) # Course List
        self.w['4.Prgrs' ] = tk.LabelFrame(self.w['LeftPane'], text=" Progress "  , padx=8, pady=8) # Progress
        self.w['0.Statusbar'] = tk.Frame(self.w['LeftPane'], relief="groove", bd=2) # Status Bar
        self.w['1.Topbar'].pack(side='top', fill='x')
        self.w['2.Login' ].pack(side='top', fill='x')
        self.w['3.Course'].pack(side='top', fill='x')
        self.w['4.Prgrs' ].pack(side='top', fill='x')
        self.w['0.Statusbar'].pack(side='bottom', fill='x')

        # Topbar
        self.w['1.Topbar-Left'] = tk.Frame(self.w['1.Topbar'])
        self.w['1.Topbar-Left'].pack(side='left')
        self.w['1.Topbar-Right'] = tk.Frame(self.w['1.Topbar'])
        self.w['1.Topbar-Right'].pack(side='right')

        self.w['1.Topbar-Left-InnerTitle'] = tk.Label(self.w['1.Topbar-Left'], text = "Inner Title")
        self.w['1.Topbar-Left-InnerTitle'].pack(side='left')

        self.w['1.Topbar-Right-Button-Test'] = tk.Label(self.w['1.Topbar-Right'], text = "[테스트용]")
        self.w['1.Topbar-Right-Button-Browser'] = tk.Label(self.w['1.Topbar-Right'], text = "[브라우저]")
        self.w['1.Topbar-Right-Button-CloseCourse'] = tk.Label(self.w['1.Topbar-Right'], text = "[강의닫기]")
        self.w['1.Topbar-Right-Button-Test'].pack(side='left')
        self.w['1.Topbar-Right-Button-Browser'].pack(side='left')
        self.w['1.Topbar-Right-Button-CloseCourse'].pack(side='left')
        self.label_as_button = [self.w['1.Topbar-Right-Button-Test'], self.w['1.Topbar-Right-Button-Browser'], self.w['1.Topbar-Right-Button-CloseCourse']]
        for l in self.label_as_button:
            l.bind("<Enter>", self.handler_set_blue)
            l.bind("<Leave>", self.handler_set_black)

        # Login
        self.w['2.Login-Collapse'] = tk.Frame(self.w['2.Login'])
        self.w['2.Login-Collapse'].pack(fill='both', expand=True)
        _parent = self.w['2.Login-Collapse']
        self.w['2.Login']._collapse = _parent
        tk.Label(_parent, text="URL").grid(row=0, column=0)
        tk.Label(_parent, text="ID" ).grid(row=1, column=0)
        tk.Label(_parent, text="PW" ).grid(row=2, column=0)
        self.w['2.Login-Entry-URL'] = tk.Entry(_parent, width=32)
        self.w['2.Login-Entry-URL'].insert(0, DEFAULT_URL)
        self.w['2.Login-Entry-ID' ] = tk.Entry(_parent, width=15)
        self.w['2.Login-Entry-PW' ] = tk.Entry(_parent, width=15, show="*")
        self.w['2.Login-Entry-Button'] = tk.Button(_parent, text="로그인")

        self.w['2.Login-Entry-URL'].grid(row=0, column=1, columnspan=3, sticky="w")
        self.w['2.Login-Entry-ID' ].grid(row=1, column=1, sticky="w")
        self.w['2.Login-Entry-PW' ].grid(row=2, column=1, sticky="w")
        self.w['2.Login-Entry-Button'].grid(row=1, column=2, rowspan=2, sticky="news")

        # Course Info
        self.w['3.Course-Collapse'] = tk.Frame(self.w['3.Course'])
        self.w['3.Course-Collapse'].pack(fill='both', expand=True)
        self.w['3.Course']._collapse = self.w['3.Course-Collapse']

        self.w['3.Course-List'] = tk.Listbox(self.w['3.Course-Collapse'], selectmode="single", height=3)
        self.w['3.Course-List'].pack(fill='both')
        self.course_list = self.w['3.Course-List']
        self.course_list.bind('<Double-ButtonRelease-1>', self.handler_course)

        # Progress
        self.w['4.Prgrs-Collapse'] = tk.Frame(self.w['4.Prgrs'])
        self.w['4.Prgrs-Collapse'].pack(fill='both', expand=True)
        self.w['4.Prgrs']._collapse = self.w['4.Prgrs-Collapse']

        self.w['4.Prgrs-Line1'] = tk.Label(self.w['4.Prgrs-Collapse'], anchor='w')
        self.w['4.Prgrs-Line1'].pack(fill='x')
        self.w['4.Prgrs-Line2'] = tk.Label(self.w['4.Prgrs-Collapse'], anchor='w')
        self.w['4.Prgrs-Line2'].pack(fill='x')
        self.w['4.Prgrs-Line3'] = tk.Label(self.w['4.Prgrs-Collapse'], anchor='w')
        self.w['4.Prgrs-Line3'].pack(fill='x')
        self.progress = tk.DoubleVar()
        self.w['4.Prgrs-Progressbar'] = ttk.Progressbar(self.w['4.Prgrs-Collapse'], variable=self.progress)
        self.w['4.Prgrs-Progressbar'].pack(fill='x')

        self.browserimage = ImageTk.PhotoImage("RGB",size=(10,10))
        self.w['R.Browser'] = tk.Label(self.w['RightPane'], image=self.browserimage)
        self.w['R.Browser'].pack()
        self.w['R.Browser'].bind('<MouseWheel>', self.browser_scroll)

        # Status Bar
        self.w['0.Statusbar-Text'] = tk.Label(self.w['0.Statusbar'])
        self.statusbar = self.w['0.Statusbar-Text']
        self.statusbar.pack(side='left')

        # Inject widget key
        for (key, widget) in self.w.items():
            widget.key = key

        self.window.bind_all("<ButtonRelease-1>", self.handler)

    def __del__(self):
        if not self.closed:
            self.close()

    def close(self):
        #self.window.after_cancel(self.nextpoller)
        self.window.quit()
        self.window.destroy()
        self.window = None
        self.core.close() if self.core else None
        self.closed = True

    def core_ready(self):
        with self.lock:
            self.core = Lms(self, headless=True, size=BROWSER_SIZE)
            self.state.statusbar = ''

    def popup(self, text, *args, **kwargs):
        pass

    def poller(self):
        if self.window:
            self.statusbar.config(text=self.state.statusbar)
            if self.state.learning:
                self.progress.set(self.state.progress)
                self.w['4.Prgrs-Line1'].config(text=self.state.courseinfo1)
                self.w['4.Prgrs-Line2'].config(text=self.state.courseinfo2)
                self.w['4.Prgrs-Line3'].config(text=f'{self.state.played} / {self.state.length}')
                self.browser_screen_refresh()
            if self.state.get_course:
                self.get_courses()
            self.nextpoller = self.window.after(POLLING_DELAY, self.poller)

    def handler(self, event):
        widget = event.widget
        #print("Click", widget.key, event.x_root, event.y_root)
        if widget.winfo_class().upper() == 'LABELFRAME':
            self.toggle_frame(widget)
        match(widget.key):
            case '1.Topbar-Right-Button-Browser':   # Toggle Browser
                if self.w['RightPane'].winfo_viewable():
                    self.w['RightPane'].pack_forget()
                else:
                    self.w['RightPane'].pack(fill='y')
                    self.browser_screen_refresh(force=True)
            case '1.Topbar-Right-Button-CloseCourse':
                self.stop_course()
            case '2.Login-Entry-Button':
                Thread(target=self.login, args=[self.w['2.Login-Entry-URL'].get(), self.w['2.Login-Entry-ID'].get(), self.w['2.Login-Entry-PW'].get()]).start()

    def handler_set_blue(self, event):
        event.widget.config(fg = "#36f")

    def handler_set_black(self, event):
        event.widget.config(fg = "black")

    def handler_course(self, event):
        num = event.widget.curselection()[0]
        self.state.learning = True
        Thread(target=self.set_course, args=[num]).start()

    def toggle_frame(self, frame):
        try:
            collapse = frame._collapse
            if collapse.winfo_viewable():
                collapse.pack_forget()
                frame.configure(height=18)
            else:
                collapse.pack(fill='both')
                frame.configure(height=frame.winfo_reqheight())
        except:
            pass

    def login(self, url, userID, userPW):
        with self.lock:
            self.core.set_base_url(url)
            self.state.statusbar = '로그인 중...'
            try:
                self.core.login(userID=userID, userPW=userPW)
                self.toggle_frame(self.w['2.Login' ])
                self.state.get_course = True
                self.state.statusbar = ''
            except:
                self.state.statusbar = '로그인 실패'

    def get_courses(self):
        self.state.get_course = False
        with self.lock:
            self.state.statusbar = '강의 정보 수집 중...'
            self.courses = self.core.get_course()
            self.course_list.delete(0, self.course_list.size())
            for i in range(len(self.courses)):
                self.course_list.insert(i, self.courses[i]['text'].strip())
            self.state.statusbar = ''

    def set_course(self, num):
        try:
            self.state.statusbar = '수강 중...'
            self.core.set_course(num)
        except:
            self.state.clear()
        self.state.statusbar = ''

    def stop_course(self):
        if self.core:
            self.core.stop = True
            self.state.clear()

    def browser_screen_refresh(self, force=False):
        if self.core:
            if force or self.w['R.Browser'].winfo_viewable():
                try:
                    img = Image.open(BytesIO(base64.b64decode(self.core.get_screenshot())))
                    #ratio = min(IMG_SIZE_W / img.size[0], IMG_SIZE_H / img.size[1])
                    ratio = IMG_SIZE_H / img.size[1]
                    IMG_SIZE = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                    img = img.resize(IMG_SIZE)
                    if self.browserimage.width() != img.width:
                        self.browserimage = ImageTk.PhotoImage(image=img)
                        self.w['R.Browser'].config(image=self.browserimage)
                    else:
                        self.browserimage.paste(img)
                except:
                    pass
    def browser_scroll(self, event):
        amount = event.delta // MWHEEL_DELTA_UNIT
        self.core.scroll(0, amount * SCROLL_AMOUNT)
        self.browser_screen_refresh()

if __name__ == '__main__':
    Gui = LmsGui()
    Gui.window.geometry('+1400+600')
    #self = Gui
