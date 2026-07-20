import sys
import time
from PySide6.QtCore import Qt, QThreadPool, QRunnable, Signal, QObject, Slot
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout,
                               QPushButton, QListWidget, QWidget, QLabel)

# 1. Define communication signals for inter-thread communication
class WorkerSignals(QObject):
    finished = Signal(str, str) # Job ID, Result
    progress = Signal(str, int) # Job ID, Progress %

# 2. Define the Worker that executes a single job
class Worker(QRunnable):
    def __init__(self, job_id):
        super().__init__()
        self.job_id = job_id
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        """Simulate a long-running job."""
        print(f"Starting Job: {self.job_id}")
        for i in range(1, 101):
            time.sleep(0.05) # Simulating blocking work
            self.signals.progress.emit(self.job_id, i)

        # Job finished
        result = f"Completed at {time.strftime('%X')}"
        self.signals.finished.emit(self.job_id, result)

# 3. Main GUI Application
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PySide6 Work Queue Manager")
        self.resize(400, 300)

        # Initialize QThreadPool for managing the worker queue
        self.thread_pool = QThreadPool()
        print(f"Max threads available: {self.thread_pool.maxThreadCount()}")
        self.thread_pool.setMaxThreadCount(1)
        # Setup UI
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.label = QLabel("Job Queue Status: Idle")
        self.add_job_btn = QPushButton("Add New Job to Queue")
        self.queue_list = QListWidget()

        layout.addWidget(self.label)
        layout.addWidget(self.add_job_btn)
        layout.addWidget(self.queue_list)

        # Signals
        self.add_job_btn.clicked.connect(self.add_job)

        # Counter for generating unique job IDs
        self.job_counter = 0

    def add_job(self):
        self.job_counter += 1
        job_id = f"Job #{self.job_counter}"

        # Add visual representation to the GUI queue list
        self.queue_list.addItem(f"{job_id} - Queued (0%)")
        self.queue_list.scrollToBottom()

        # Create the worker and connect its signals to main thread slots
        worker = Worker(job_id)
        worker.signals.progress.connect(self.update_job_progress)
        worker.signals.finished.connect(self.finalize_job)

        # Enqueue job to QThreadPool
        self.thread_pool.start(worker)
        self.label.setText(f"Job Queue Status: {self.thread_pool.activeThreadCount()} active workers")

    @Slot(str, int)
    def update_job_progress(self, job_id, progress):
        items = self.queue_list.findItems(job_id, Qt.MatchFlag.MatchStartsWith)
        if items:
            items[0].setText(f"{job_id} - Processing ({progress}%)")

    @Slot(str, str)
    def finalize_job(self, job_id, result):
        items = self.queue_list.findItems(job_id, Qt.MatchFlag.MatchStartsWith)
        if items:
            items[0].setText(f"{job_id} - Finished - {result}")

        self.label.setText(f"Job Queue Status: {self.thread_pool.activeThreadCount()} active workers")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
