"""
Create info file for a given data file. Run with --help for more help.
"""

import urllib.request
import pprint
import os.path
import Orange
import re
import argparse
import json
import readline
import shlex
import subprocess
import textwrap
import itertools
from serverfiles import LocalFiles, ServerFiles
from Orange.misc.environ import data_dir

# url = "/Users/blaz/Desktop/grades.tab"
# url = "http://file.biolab.si/datasets/grades.tab"

valid_url = re.compile(
    r'^(?:http|ftp)s?://' # http:// or https://
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
    r'localhost|' #localhost...
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
    r'(?::\d+)?' # optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE
)

parser = argparse.ArgumentParser(description='Creates data set info file for Orange Datasets.')
parser.add_argument("file_name", help="URL or local name of data file")
parser.add_argument("-u", "--upload", action="store_true",
                    help="upload local data file to server")
args = parser.parse_args()


def capitalize(s):
    return s[0].upper() + s[1:]


def tag_list():
    """List of available tags and their pretty-print with indices"""
    server_url = "http://butler.fri.uni-lj.si/datasets/"
    PATH = os.path.join(data_dir(), "datasets")
    local_files = LocalFiles(PATH, serverfiles=ServerFiles(server=server_url))
    local_info = local_files.serverfiles.allinfo()

    nested_tags = [i["tags"] for i in local_info.values() if i["tags"]]
    all_tags = sorted(list(set(itertools.chain(*nested_tags))))
    w = max(len(t) for t in all_tags)
    n = int(75 / (w + 5))

    s = ["{:>3}-{:<{width}}".format(i, t, width=w) for i, t in enumerate(all_tags)]
    c = "\n".join(["".join(s[x:x + n]) for x in range(0, len(s), n)])

    return all_tags, c


def squeeze(x):
    if type(x) == list:
        return " ".join(x)
    return x


def query(key, comment, multi_line=False, multi_item=False, extra=None):
    """
    Terminal query for an info description. For text spanning several lines,
    set multi_line to True. For entries spanning several items, set
    multi_item to True.
    """
    cap = capitalize(key)
    print("\n{}".format("\n".join(textwrap.wrap(comment))))
    if extra:
        print(extra)
    if multi_line or multi_item:
        print("{}:".format(cap))
        if key in helper_info:
            print("\n".join(textwrap.wrap("[{}]".format(helper_info[key]))))
        answer = list(iter(input, ''))
        if not multi_item:
            answer = " ".join(answer)
    else:
        if key in helper_info:
            answer = input("{} [{}]: ".format(cap, squeeze(helper_info[key])))
        else:
            answer = input("{}: ".format(cap))
    if not answer:
        if multi_line:
            return helper_info.get(key, "")
        elif multi_item:
            return helper_info.get(key, [])
        else:
            return squeeze(helper_info.get(key, ""))
    return answer


info = {}
file_is_local = False

if valid_url.match(args.file_name):
    print("URL:", args.file_name)
    site = urllib.request.urlopen(args.file_name)
    info["size"] = site.length
else:
    print("Local file:", args.file_name)
    info["size"] = os.path.getsize(args.file_name)
    file_is_local = True

data = Orange.data.Table(args.file_name)

base_name = os.path.basename(args.file_name)
info["name"] = os.path.splitext(base_name)[0]

target = None
if data.domain.has_discrete_class:
    target = "categorical"
elif data.domain.has_continuous_class:
    target = "numeric"
info["target"] = target

info["instances"] = len(data)
info["variables"] = len(data.domain.attributes) \
			+ len(data.domain.metas) \
			+ len(data.domain.class_vars)
info["version"] = "1.0"

print("\nBasic info from data file:")
pprint.pprint(info)

# storage location
info_file_name = "{}.info".format(args.file_name if file_is_local else base_name)

helper_info = {}
if os.path.exists(info_file_name):
    with open(info_file_name) as json_data:
        helper_info = json.load(json_data)

info["title"] = query("title", "Title is composed of one or few words. Use sentence case.")
year = query("year", "Year of first publication of the data set.")
info["year"] = int(year) if year else None
info["collection"] = query("collection", "Collection name, like UCI, R, or GEO.")

source = query("Source", "Source description (like UCI ML Repository, or KDD Cup Competitions")
if not source:
    info["source"] = None
else:
    source_url = query("Source URL", "URL of the source (required), like http://orange.biolab.si")
    info["source"] = "<a href='{}'>{}</a>".format(source_url, source)

info["description"] = query(
    "description",
    "Description can be composed of several lines. Spell check the writing first. "
    "Empty line to finish with description.",
    multi_line=True
)

info["references"] = query(
    "references",
    "References cite publication of a dataset. Use syntax of the type "
    "`Fisher XO (1987) The string problem. Annals of Strings 7(2):179–188.' "
    "One reference per line. For any links to PDFs or similar, use HTML syntax and "
    "anchor a publication title.",
    multi_item=True
)

info["seealso"] = query(
    "seealso",
    "Cite any other reference, like web sites, wikipedia pages or blogs."
    "Use HTML syntax for links.",
    multi_item=True
)

# tags
candidates, pp_tags = tag_list()
tag_s = query(
    "tags",
    "List of tags. One word per tag only. Use numbers for existing or words for new."
    "Separate by space. In case of multi-word tag, use '-' to link words (like machine-learning).",
    extra=pp_tags
)
if tag_s:
    info["tags"] = [candidates[int(t)] if t.isdigit() else t for t in tag_s.split(" ")]
else:
    info["tags"] = []

# url
if file_is_local or args.upload:
    cmd = "scp {} file:~/anonymous/datasets/".format(args.file_name)
    print("Uploading data file...")
    subprocess.run(shlex.split(cmd))
    info["url"] = "http://file.biolab.si/datasets/{}".format(base_name)
else:
    info["url"] = args.file_name

# finalize and save
print("Info record:")
pprint.pprint(info)

print()
print("Info record saved to {}.".format(info_file_name))

json.dump(info, open(info_file_name, "w"), sort_keys=True, indent=4)
