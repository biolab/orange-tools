import argparse
import pathlib
import tinify
import time


def tinify_images(path, extensions):

    for file_path in [file for file in pathlib.Path(path).rglob('*')]:
        if file_path.suffix in extensions:
            print(f'Compressing image {file_path}')
            source = tinify.from_file(file_path)
            source.to_file(file_path)
            time.sleep(0.1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Tinify images.")

    parser.add_argument('-k', '--key', type=str, required=True,
                        help='API key')

    parser.add_argument('-p', '--path', type=str, required=True,
                        help='The directory to search.')

    parser.add_argument('-e', '--extensions', type=str, nargs='*',
                        default=['.png', '.jpg'],
                        help='The file extensions to search for.')

    args = parser.parse_args()

    tinify.key = args.key
    tinify_images(args.path, args.extensions)
