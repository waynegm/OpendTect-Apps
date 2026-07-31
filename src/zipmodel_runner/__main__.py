import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtWidgets import QApplication, QMessageBox
from shared.uiodbind import odbind_found
from ui.mainwindow import MainWindow

if __name__== "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    if odbind_found():
        window = MainWindow()
        window.show()
        app.exec()
    else:
        QMessageBox.critical(None, "Error: ⚠️ ODBind Not Found", "This application requires the ODBind plugin")
