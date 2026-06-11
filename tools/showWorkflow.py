import shutil
import sys
from xml.dom import minidom
import base64
import pickle
from pprint import pformat
import argparse

IGNORE = {"savedWidgetGeometry", "controlAreaVisible", "context_settings"}

def ensure_orange():
    try:
        import Orange
    except ImportError:
        print("Orange is not installed in this environment")
        sys.exit(1)


def list_widgets(node_names):
    for wid, (name, qname) in node_names.items():
        print(f"{wid:2}: {name} ({qname})")


def get_matching_widgets(node_names, workflow, widget_id=None):
    widgets = []

    ensure_orange()
    for props in workflow.getElementsByTagName("properties"):
        wid = props.getAttribute("node_id")
        name, qualified = node_names[wid]
        if widget_id is not None and not (
                int(wid) == int(widget_id) if widget_id.isdigit()
                else widget_id in name.lower() or widget_id in qualified.lower()):
            continue
        format = props.getAttribute("format")
        child = props.firstChild
        if format == "pickle":
            values = pickle.loads(base64.b64decode(child.nodeValue))
        elif format == "literal":
            values = eval(child.nodeValue)
        else:
            print(f"Unsupported settings format ({format})")
            continue

        widgets.append((wid, name, qualified, values, props))
    return widgets


def show(node_names, workflow, widget_id=None):
    for wid, name, qualified, values, _ in get_matching_widgets(node_names, workflow, widget_id):
        s = f"{wid} {name} ({qualified})"
        print(s + "\n" + "-" * len(s))
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


def remove_context(filename, node_names, workflow, widget_id, context_id=None):
    widgets = get_matching_widgets(node_names, workflow, widget_id)
    if not widgets:
        print(f"No matching widgets found for '{widget_id}'")
        return
    wid, name, _, values, propnode = widgets[0]
    contexts = values.get("context_settings")
    if contexts is None:
        print(f"No context settings found for widget {wid} ({name})")
    if context_id is None:
        contexts.clear()
    elif 0 <= context_id < len(contexts):
        contexts.pop(context_id)
    else:
        print(f"Invalid context ID {context_id} for widget {wid} ({name})")
    new_value = base64.b64encode(pickle.dumps(values)).decode()
    propnode.firstChild.nodeValue = new_value

    shutil.copy(filename, filename + ".bak")
    with open(filename, "w") as f:
        workflow.writexml(f)


def main():
    argparser = argparse.ArgumentParser(description="Show workflow settings for all or selected widget(s).")
    argparser.add_argument("file", help="Path to the .ows workflow file")

    subparsers = argparser.add_subparsers(dest="operation", help="Operation to perform", required=True)

    parser = subparsers.add_parser("list", help="Print widget names and exit")

    parser = subparsers.add_parser("show", help="Show settings for a widget")
    parser.add_argument("widget", nargs="?", help="Widget type or number to show (optional)")

    parser = subparsers.add_parser("remove-context", help="Remove context settings from a widget")
    parser.add_argument("widget", nargs="?", help="Widget type or number to show (optional)")
    parser.add_argument("context", nargs="?", help="Context number to remove (optional)")


    if len(sys.argv) == 2:
        sys.argv.append("show")

    args = argparser.parse_args()
    args.widget = args.widget.lower() if getattr(args, "widget", None) else None

    wf = minidom.parse(args.file)
    node_names = {
        n.getAttribute("id"): (n.getAttribute("name"), n.getAttribute("qualified_name"))
        for n in wf.getElementsByTagName("node")}

    if args.operation == "list":
        list_widgets(node_names)
    elif args.operation == "show":
        show(node_names, wf, args.widget)
    elif args.operation == "remove-context":
        if args.context is None:
            context = None
        elif args.context.isdigit():
            context = int(args.context)
        else:
            print(f"Invalid context ID: {args.context}, number expected")
            return
        remove_context(args.file, node_names, wf, args.widget, context)


if __name__ == "__main__":
    main()
