import shutil
import sys
from xml.dom import minidom
import base64
import pickle

try:
    from Orange.widgets.utils.filedialogs import RecentPath
except ImportError:
    print("Orange is not installed in this environment")

if len(sys.argv) == 1:
    print("""
remove-recent-files <file.ows> [file] [url]

Removes recent paths and urls except for the first file and/or the first url.
The extra arguments tell what to keep. If none are given, it keeps the first file.

Files from /datasets/ are always kept.

The tool works for the File widget, and perhaps for others, too.
It probably doesn't break anything.
""")

fname = sys.argv[1]
keep_url = "url" in sys.argv[2:]
keep_file = "file" in sys.argv[2:] or not keep_url

wf = minidom.parse(fname)

some_changes = False

for props in wf.getElementsByTagName("properties"):
    format = props.getAttribute("format")
    if format != "pickle":
        continue

    child = props.firstChild
    values = pickle.loads(base64.b64decode(child.nodeValue))

    changed = False
    for key, value in list(values.items()):
        if isinstance(value, list) \
                and any(isinstance(path, RecentPath) for path in value):
            new_list = [
                path for i, path in enumerate(value)
                if keep_file and i == 0
                or not isinstance(path, RecentPath)
                or path.abspath.split("/")[-2] == "datasets"
            ]
            if len(new_list) != value:
                values[key] = new_list
                changed = True
        if key == "recent_urls" and value:
            values[key] = value[:keep_url]
            changed = True

    if changed:
        some_changes = True
        text = base64.b64encode(pickle.dumps(values))
        new_node = child.replaceWholeText(text.decode("ascii"))
        props.removeChild(child)
        props.appendChild(new_node)
    
if some_changes:
    print("Cleaned")
    shutil.move(fname, fname + ".bak")
    with open(fname, "wt") as f:
        wf.writexml(f)
else:
    print("No changes")
