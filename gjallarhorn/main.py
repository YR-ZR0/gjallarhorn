#!/usr/bin/env python3
"""
Gjallarhorn is a taskwarrior reminder system.
"""


import multiprocessing
import subprocess
import sys
import time
from datetime import timedelta
from pathlib import Path

import click
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, render_template
from pytimeparse.timeparse import timeparse
from tasklib import TaskWarrior
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from icecream import ic

HOME = str(Path.home())
app = Flask(__name__)

sched = BackgroundScheduler(
    {
        "apscheduler.jobstores.default": {
            "type": "sqlalchemy",
            "url": "sqlite:///jobs.sqlite",
        }
    }
)


class FileEventHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith(".data"):
            buildjoblist()


class FileWatcher:
    def __init__(self):
        self.event_handler = FileEventHandler()
        self.observer = Observer()

    def run(self):
        self.observer.schedule(
            self.event_handler, path=f"{HOME}/.task/", recursive=True
        )
        self.observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
        self.observer.join()


def buildjoblist():
    """
    Trigger a refresh of the task list, and then build the job list
    """
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
        print(f"Job Name: {job.id} Next Run: {sched.get_job(job.id).trigger}")


@app.route("/sched")
def get_sched():
    """
    Return the current job list as a HTML page
    """
    jobs = sched.get_jobs()
    return render_template("sched.html", jobs=jobs)


def notification(title: str, reminder_time):
    """
    Fire the notification based on time
    """
    subprocess.Popen(
        [
            "notify-send",
            f"Gjallarhorn\nTask {title}\nDue at {reminder_time.strftime('%r')}",
        ]
    )


def calcdelta(remind: str, due):
    """
    Take the reminder UDA and due and calculate the delta.
    """
    notificationtime = due - timedelta(seconds=timeparse(remind))
    return notificationtime


def check(task_list):
    """
    Check each task has a due date and see if a reminder delta exists
    the remind delta is duedate - reminder e.g.
    5pm and remind is 1 h so notify at 4pm
    """
    considered = {}
    for task in task_list:
        item = task_list[task]
        if "reminder" in item and item["reminder"] != item["due"]:
            print(f'Decided {item["task"]} by Delta')
            remind = str(item["reminder"])
            delt = calcdelta(remind, item["due"])
            considered[item["task"]] = {"due": item["due"], "remind": delt}
        else:
            print(f'Decided {item["task"]} by Due')
            considered[item["task"]] = {"remind": item["due"], "due": item["due"]}
    return considered


def gather():
    """
    Loop over tasks that have a due and find the following:
    Reminder UDA
    Due Date of the task
    """
    tasks = TaskWarrior(f"{HOME}/.task").tasks.pending()
    task_list = {}
    i = 0
    taskfilt = tasks.filter("due")
    for task in taskfilt:
        due_date = task["due"]
        if "remind" in task:
            remind_time = task["remind"]
        else:
            remind_time = due_date
        record = {
            "due": due_date,
            "reminder": remind_time,
            "task": task["description"],
        }
        task_list[i] = record
        i = i + 1
    itemlist = check(task_list)
    return itemlist


@click.command()
@click.option("--web", "-w", is_flag=True, help="enable web interface")
def main(web):
    """
    the main function for kicking off the Gjallarhorn
    """
    try:
        multiprocessing.Process(target=FileWatcher().run, daemon=True).start()
        buildjoblist()
        sched.start()
        if web:
            print("Starting web interface")
            multiprocessing.Process(target=app.run, daemon=True).start()
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        print("Exiting")
        sched.shutdown()
        sys.exit(0)


if __name__ == "__main__":
    main()
