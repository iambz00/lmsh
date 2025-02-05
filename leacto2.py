class Leacto(QMainWindow, form_class):
    def __init__(self):
        super().__init__()
        self._setup_ui()
        self.show()

    def _setup_ui(self):
        self.setupUi(self)
        self.setWindowTitle(WINDOW_TITLE)
        self.setWindowIcon(QIcon(WINDOW_ICON))

    def create_empty_subwindow(self):
        subwindow = QMdiSubWindow()
        subwindow.setWidget(QWidget())
        subwindow.setWindowTitle("Empty Subwindow")
        self.mdiArea.addSubWindow(subwindow)
        subwindow.show()

if __name__ == "__main__" :
    app = QApplication(sys.argv)
    window = Leacto()
    #sys.exit(app.exec())

    window.setGeometry(1560,480,0,0)