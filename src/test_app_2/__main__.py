import sys
import time
from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtWidgets import (
    QApplication, QTableWidget, QTableWidgetItem, QProgressBar,
    QVBoxLayout, QWidget, QPushButton, QHeaderView
)

# 1. Worker Object remains the same (Thread-safe engine)
class JobWorker(QObject):
    progress_updated = Signal(int, int, str)  # row, progress, status
    finished = Signal()

    def __init__(self, target_row):
        super().__init__()
        self.target_row = target_row

    def run_job(self):
        self.progress_updated.emit(self.target_row, 0, "running")

        for progress in range(1, 101):
            time.sleep(0.03)  # Simulate real work delay
            self.progress_updated.emit(self.target_row, progress, "running")

        self.progress_updated.emit(self.target_row, 100, "done")
        self.finished.emit()


# 2. Main Application Window using QTableWidget
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Table-Based Progress Bars")
        self.resize(500, 450)

        # Layout UI
        layout = QVBoxLayout(self)
        self.start_btn = QPushButton("Start Sequential Background Jobs")

        # Initialize the Table Widget (10 rows, 3 columns)
        self.table_widget = QTableWidget(10, 3)
        self.table_widget.setHorizontalHeaderLabels(["Task ID", "Status", "Progress"])

        # Configure table visual layout behavior
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_widget.verticalHeader().setVisible(False)  # Hide row numbers

        layout.addWidget(self.table_widget)
        layout.addWidget(self.start_btn)

        # Populate the table structure
        for row in range(10):
            # Column 0: Task Identifier
            self.table_widget.setItem(row, 0, QTableWidgetItem(f"Job #{row + 1}"))

            # Column 1: Plain text status string
            self.table_widget.setItem(row, 1, QTableWidgetItem("IDLE"))

            # Column 2: Instantiated QProgressBar embedded directly into the cell view
            pbar = QProgressBar()
            pbar.setMinimum(0)
            pbar.setMaximum(100)
            pbar.setValue(0)
            pbar.setAlignment(Qt.AlignmentFlag.AlignCenter)

            # Use setCellWidget to lock the actual widget into the table cell grid
            self.table_widget.setCellWidget(row, 2, pbar)

        # Threading infrastructure management hooks
        self.start_btn.clicked.connect(self.start_chain_processing)
        self.current_job_index = 0
        self.thread = None
        self.worker = None

    def start_chain_processing(self):
        self.start_btn.setEnabled(False)
        self.current_job_index = 0
        self.launch_next_thread()

    def launch_next_thread(self):
        if self.current_job_index >= 10:
            self.start_btn.setEnabled(True)
            return

        self.thread = QThread()
        self.worker = JobWorker(self.current_job_index)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run_job)
        self.worker.progress_updated.connect(self.handle_gui_update)

        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.on_thread_finished)

        self.thread.start()

    def handle_gui_update(self, row, progress, status):
        """Safely updates table row cells directly from Thread Signals."""
        # Update text status column
        status_item = self.table_widget.item(row, 1)
        if status_item:
            status_item.setText(status.upper())

        # Retrieve the embedded QProgressBar widget from column index 2
        pbar = self.table_widget.cellWidget(row, 2)
        if isinstance(pbar, QProgressBar):
            pbar.setValue(progress)

            # Apply direct styling rules to modify color states natively
            if status == "running":
                pbar.setStyleSheet("""
                    QProgressBar::chunk { background-color: #d32f2f; }
                    QProgressBar { text-align: center; color: white; font-weight: bold; }
                """)
            elif status == "done":
                pbar.setStyleSheet("""
                    QProgressBar::chunk { background-color: #388e3c; }
                    QProgressBar { text-align: center; color: white; font-weight: bold; }
                """)

    def on_thread_finished(self):
        self.current_job_index += 1
        self.launch_next_thread()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
