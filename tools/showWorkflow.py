import shutil
import sys
from xml.dom import minidom
import base64
import pickle
from pprint import pformat

IGNORE = {"savedWidgetGeometry", "controlAreaVisible", "context_settings"}

try:
    from Orange.widgets.utils.filedialogs import RecentPath
except ImportError:
    print("Orange is not installed in this environment")

def main():
    if len(sys.argv) <= 1:
        print("""
show-workflow <file.ows> [--list | widget-type or number]

Show workflow settings for all or selected widget(s).

--list prints widget names and exits
""")
    exit()

    fname = sys.argv[1]
    op = (sys.argv + [None])[2]
    wf = minidom.parse(fname)
    node_names = {
        n.getAttribute("id"): (n.getAttribute("name"), n.getAttribute("qualified_name"))
        for n in wf.getElementsByTagName("node")}

    if op == "--list":
        for wid, (name, qname) in node_names.items():
            print(f"{wid:2}: {name} ({qname})")
        exit()
    elif op:
        op = op.lower()

    for props in wf.getElementsByTagName("properties"):
        wid = props.getAttribute("node_id")
        name, qualified = node_names[wid]
        if op is not None and not (
                int(wid) == int(op) if op.isdigit()
                else op in name.lower() or op in qualified.lower()):
            continue
        s = f"{wid} {name} ({qualified})"
        print(s + "\n" + "-" * len(s))
        format = props.getAttribute("format")
        child = props.firstChild
        if format == "pickle":
            values = pickle.loads(base64.b64decode(child.nodeValue))
        elif format == "literal":
            values = eval(child.nodeValue)
        else:
            print(f"Unsupported settings format ({format})")

        for name, value in values.items():
            if name in IGNORE:
                continue
            if not isinstance(value, (int, float, bool, str, list, dict, type(None))):
                valtype = f" ({type(value)})"
            else:
                valtype = ""
            print(f"{name}{valtype}:", end=" " if not value or isinstance(value, (int, float, bool, str)) else "\n  ")
            print(pformat(value).replace("\n", "\n  "))
        contexts = values.get("context_settings")
        if contexts is not None:
            print("Contexts:")
            for ctx, context in enumerate(contexts):
                print(f"{ctx:<2}: " + pformat(context.__dict__).replace("\n", "\n    "))
        print()

if __name__ == "__main__":
    main()
