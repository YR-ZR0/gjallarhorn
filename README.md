# gjallarhorn 📯

A python program to watch over your tasks. and notify you when you have a task due.

## Prerequisites

* Have `notify-send` installed
* Set a custom UDA called 'Remind' (Optional). This is the time you want to be reminded of your task.

```shell
uda.remind.type=string
uda.remind.label=Remind
```

## Operation

`nohup python main.py`

This will kick off a task import where gjallarhorn will ingest the pending task file
filter it for tasks with a due tag initially.

It will then hand this list off to a decider to find out if you have a reminder tag (in this case it does due - remind e.g. due:10am remind:30m results in a 9:30am reminder), if this is not set we fallback to just reminding you as soon as the due date is reached.

This process is continued in a loop using a watcher to see if anything in .task with the ending .data (this can be {undo,pending,completed}.data) is changed then we recalculate the list

## Disclaimer

Could be optimized, so you may miss meetings/deadlines/anniversaries/baby births and those are on you 😂.

Probably not production grade but was made to fulfill a lack of having good desktop notifications for TW.
