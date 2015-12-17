"""
Post-it sticker handling for Orange tasks.
Reads the data from orange-todo google sheet, and formats html
documents with text for up to six stickers.

Author: Blaz Zupan, 2015
"""

import os
import glob
import argparse
import sys
from collections import Counter
import Orange.data

print_priority = 3

priority_word = {
    0: "no",
    1: "low",
    2: "medium",
    3: "high",
    4: "very high",
    5: "urgent"
}

html_head = """
<html><link rel="stylesheet" type="text/css" href="todo-template.css">
<meta http-equiv="Content-Type" content="text/html;charset=utf8">
<body>
<table>
"""

html_tail = """
</table>
</body>
</html>
"""

html_body = """
<td>
<div>
<p class="id">{}{} ({}) {:04d}</p>
<p class="important">{}</p>
<p class="description">{}</p>
<p class="smallprint">{}</p>
</div>
</td>
"""


class Data:
    def __init__(self):
        self.data = None

    def __call__(self):
        if self.data:
            return self.data
        else:
            data = Orange.data.Table(
                "https://docs.google.com/spreadsheets/d/"
                "1spQ3zuXUEvoD-hpYEm33-lyS3OzV6cjhE7YlFlBoOw8/"
                "edit?usp=sharing"
            )
            self.data = data
            return self.data


def str_value(x):
    return str(x) if str(x) != "?" else ""


def print_stickers(sticker_priority):
    data = sticker_data()

    for f_name in glob.glob("todo-*.html"):
        os.remove(f_name)

    docs = 0
    count = 0
    for d in data:
        if (d["Printed?"] == "yes") or (int(d["Priority"]) != sticker_priority):
            continue
        if count % 6 == 0:
            if count != 0:
                f.write(html_tail)
                f.close()
            docs += 1
            f = open("todo-%02d.html" % docs, "w")
            f.write(html_head)

        if count % 2 == 0:
            f.write("<tr>\n")
        f.write(html_body.format(
            "%s - " % str(d["Owner"]) if str(d["Owner"]) != "?" else "",
            priority_word[int(d["Priority"])],
            "*" * int(d["Difficulty"]),
            int(d["ID"]),
            str(d["Title"]),
            str(d["Task"]),
            str_value(d["SmallPrint"])
            )
        )
        if count % 2 != 0:
            f.write("</tr>\n")
        count += 1
    print("Stickers on the output: {}".format(count))
    if count:
        f.write(html_tail)
        f.close()


def print_statistics():
    data = sticker_data()

    print("Total stickers: {}".format(len(data)))
    print("Stickers to print: {}".format(sum((1 for d in data
                                              if d["Printed?"] == "no"))))
    ps = Counter(int(d["Priority"]) for d in data if d["Printed?"] == "no")
    print("\n".join(("  {:>9}({}): {}".format(priority_word[p], p, n)
                     for p, n in sorted(ps.items()))))

sticker_data = Data()

parser = argparse.ArgumentParser(description='Process sticker arguments.')
parser.add_argument("-s", "--statistics", action="store_true", default=False,
                    help='print sticker statistics')
parser.add_argument("-p", "--priority", default=None,
                    help='print stickers with specified priority')

if len(sys.argv) == 1:
    parser.print_help()

args = parser.parse_args()
if args.statistics:
    print_statistics()
if args.priority:
    print_stickers(int(args.priority))
