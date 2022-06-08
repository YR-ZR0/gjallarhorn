import subprocess
import time
from datetime import timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from pytimeparse.timeparse import timeparse
from tasklib import TaskWarrior
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from pathlib import Path


home = str(Path.home())


class FileEventHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith(".data"):
            buildjoblist()


"""
Trigger a refresh of the task list, and then build the job list
"""


def buildjoblist():
    gathered = gather()
    for title, stats in gathered.items():
        sched.add_job(
            notification,
            "date",
            misfire_grace_time=300,  # type: ignore
            args=[title, stats["due"]],
            run_date=stats["remind"],
            replace_existing=True,
            id=title,
        )
    for job in sched.get_jobs():
        print(job)


"""
Fire the notification based on time
"""


def notification(title, time):
    subprocess.Popen(
        ["notify-send", f"Gjallarhorn\nTask {title}\nDue at {time.strftime('%r')}"]
    )


"""
Take the reminder UDA and due and calculate the delta.
"""


def calcdelta(remind, due):
    notificationtime = due - timedelta(seconds=timeparse(remind))
    return notificationtime


"""
Check each task has a due date and see if a reminder delta exists
the remind delta is duedate - reminder e.g.
5pm and remind is 1 h so notify at 4pm
"""


def check(tList):
    considered = dict()
    for t in tList:
        item = tList[t]
        if "reminder" in item and item["reminder"] != item["due"]:
            print(f'Decided {item["task"]} by Delta')
            remind = str(item["reminder"])
            delt = calcdelta(remind, item["due"])
            considered[item["task"]] = {"due": item["due"], "remind": delt}
        else:
            print(f'Decided {item["task"]} by Due')
            considered[item["task"]] = {"remind": item["due"], "due": item["due"]}
    return considered


"""
Loop over tasks that have a due and find the following:
Reminder UDA
Due Date of the task
"""


def gather():
    tasks = TaskWarrior(f"{home}/.task").tasks.pending()
    tList = {}
    i = 0
    taskfilt = tasks.filter("due")
    for task in taskfilt:
        dueDate = task._data["due"]
        if "remind" in task._data:
            rTime = task._data["remind"]
        else:
            rTime = dueDate
        record = {"due": dueDate, "reminder": rTime, "task": task._data["description"]}
        tList[i] = record
        i = i + 1
    itemlist = check(tList)
    return itemlist


# Start the scheduler
sched = BackgroundScheduler(
    {
        "apscheduler.jobstores.default": {
            "type": "sqlalchemy",
            "url": "sqlite:///jobs.sqlite",
        }
    }
)

event_handler = FileEventHandler()
observer = Observer()
observer.schedule(event_handler, path=f"{home}/.task/", recursive=True)
buildjoblist()
observer.start()
sched.start()
observer.join()
try:
    while True:
        time.sleep(2)
except (KeyboardInterrupt, SystemExit):
    observer.stop()
    sched.shutdown()
