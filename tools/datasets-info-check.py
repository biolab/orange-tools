import argparse
import json
import Orange
from pprint import pprint


parser = argparse.ArgumentParser(description="Checks data set info files for Orange Datasets.")
parser.add_argument("files", help="Local .info files", nargs="+")
args = parser.parse_args()

MANDATORY = ('name', 'description', 'version',
             'instances', 'variables', 'target')

for f in args.files:
    print("Info file: {}".format(f))
    with open(f) as json_data:
        d = json.load(json_data)
        # pprint(d)
        print("Loading: {:,} bytes".format(d["size"]), end="", flush=True)
        data = Orange.data.Table(d["url"])
        print()
        for key in MANDATORY:
            assert key in d, 'Missing field: {}'.format(key)
        assert len(data) == d["instances"], "Number of instances does not match, {} <> {}".format(
            len(data), d["instances"]
        )
        assert len(data.domain.attributes) == d["variables"],\
            "Number of attributes does not match, {} <> {}".format(
                d["variables"], len(data.domain.attributes)
        )
        print("Loaded, {} instances and {} attributes".format(len(data),
                                                              len(data.domain.attributes)))
        print()
