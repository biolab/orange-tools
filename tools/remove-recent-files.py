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
remove-recent-files <file.ows>

Removes recent paths or urls except for the first file and/or the first url.
The script checks what the widget is loading to see what to keep.

Files from /datasets/ are always kept.

The tool works for the File widget. It probably doesn't break anything.
""")

defaults = {f"{d}.tab" for d in (
    "iris", "brown-selected", "housing", "titanic", "heart_disease", "zoo")}



fname = sys.argv[1]
wf = minidom.parse(fname)
node_names = {n.getAttribute("id"): n.getAttribute("name")
              for n in wf.getElementsByTagName("node")}

some_changes = False

for props in wf.getElementsByTagName("properties"):
    format = props.getAttribute("format")
    if format != "pickle":
        continue

    child = props.firstChild
    values = pickle.loads(base64.b64decode(child.nodeValue))
    name = node_names[props.getAttribute("node_id")]
    keep_url = values["source"]

    changed = False
    for key, value in list(values.items()):
        if isinstance(value, list) \
                and any(isinstance(path, RecentPath) for path in value):
            new_list = [
                path for i, path in enumerate(value)
                if not keep_url and i == 0
                or not isinstance(path, RecentPath)
                or path.abspath.split("/")[-2] == "datasets" and path.abspath.split("/")[-1] in defaults
            ]
            if len(new_list) != len(value):
                values[key] = new_list
                print(f"{name}: removed files")
                changed = True
        if key == "recent_urls" and len(value) > keep_url:
            values[key] = value[:keep_url]
            print(f"{name}: removed URLs")
            changed = True

    if changed:
        some_changes = True
        text = base64.b64encode(pickle.dumps(values))
        new_node = child.replaceWholeText(text.decode("ascii"))
        props.removeChild(child)
        props.appendChild(new_node)
    else:
        print(f"{name}: no changes")
    
if some_changes:
    print("Cleaned")
    shutil.move(fname, fname + ".bak")
    with open(fname, "wt") as f:
        wf.writexml(f)
else:
    print("No changes")
