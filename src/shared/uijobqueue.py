from dataclasses import dataclass

from PySide6.QtCore import (
    QObject,
    QRunnable,
    Qt,
    QThreadPool,
    Signal,
    Slot
)

from PySide6.QtWidgets import (
    QHeaderView,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget
)


@dataclass
class JobPars:
    name: str

class JobSignals(QObject):
    finished = Signal(int, str) # Row, Result
    progress = Signal(int, int, str) # Row, Progress %, status

class JobTask(QRunnable):
    def __init__(self, row, jobpars: JobPars):
        super().__init__()
        self.pars = jobpars
        self.do_stop = False
        self.row = row
        self.signals = JobSignals()

    @Slot()
    def run(self):
        pass

    @Slot()
    def stop(self):
        self.do_stop = True

class uiJobQueue(QWidget):
    def __init__(self, max_thread: int=1):
        super().__init__()

        self.tablewidget = QTableWidget(0, 2)
        self.tablewidget.setMinimumHeight(200)
        self.tablewidget.setHorizontalHeaderLabels(["Job", "Status"])
        self.tablewidget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tablewidget.verticalHeader().setVisible(False)

        layout = QVBoxLayout(self)
        layout.addWidget(self.tablewidget)

        self.threadpool = QThreadPool()
        self._max_thread = max_thread
        self.threadpool.setMaxThreadCount(max_thread)

        self.job_counter = 0
        self._jobs: list[JobTask] = []

    def rowCount(self) -> int:
        return self.tablewidget.rowCount()

    def add_job(self, job: JobTask):
        self.job_counter += 1
        self.tablewidget.insertRow(self.tablewidget.rowCount())
        row = self.tablewidget.rowCount() - 1
        job.row = row

        self.tablewidget.setItem(row, 0, QTableWidgetItem(f"{job.pars.name}_{self.job_counter}"))
        pbar = QProgressBar()
        pbar.setMinimum(0)
        pbar.setMaximum(100)
        pbar.setValue(0)
        pbar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tablewidget.setCellWidget(row, 1, pbar)

        job.signals.progress.connect(self.update_job_progress)
        job.signals.finished.connect(self.finish_job)
        self._jobs.append(job)
        self.threadpool.start(job)

    @Slot(int, int, str)
    def update_job_progress(self, row: int, progress: int, status: str):
        pbar = self.tablewidget.cellWidget(row, 1)
        if not isinstance(pbar, QProgressBar):
            return

        pbar.setValue(progress)
        pbar.setTextVisible(True)
        pbar.setFormat(f"{status} %p%")
        if status == "Running":
            pbar.setStyleSheet("""
                QProgressBar::chunk { background-color: #d32f2f; }
                QProgressBar { text-align: center; color: black; font-weight: normal; }
            """)
        elif status == "Saving":
            pbar.setStyleSheet("""
                QProgressBar::chunk { background-color: #388e3c; }
                QProgressBar { text-align: center; color: black; font-weight: normal; }
            """)

    @Slot(int, str)
    def finish_job(self, row: int, result: str):
        self.tablewidget.removeCellWidget(row, 1)
        item = QTableWidgetItem(result)
        self.tablewidget.setItem(row, 1, item)

    def delete_selected(self):
        row = self.tablewidget.currentRow()
        if row < 0 or row >= len(self._jobs):
            return
        self._jobs[row].stop()
        self._jobs.pop(row)
        self.tablewidget.removeRow(row)
        for i, job in enumerate(self._jobs):
            job.row = i

    def stop(self):
        self.threadpool.setMaxThreadCount(0)

    def start(self):
        self.threadpool.setMaxThreadCount(self._max_thread)
