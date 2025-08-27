import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel

class MainGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sage Justice Suite")
        self.setGeometry(100, 100, 400, 300)
        label = QLabel("Welcome to Sage Justice - Arc 20", self)
        label.move(100, 130)

app = QApplication(sys.argv)
window = MainGUI()
window.show()
sys.exit(app.exec_())
