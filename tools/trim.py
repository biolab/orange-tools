"""
Blaz Zupan, blaz.zupan at fri.uni-lj.si
Ver 1.0: July 2010
"""

import argparse
from PIL import Image, ImageChops, ImageFilter
import os.path

# thumbnail_size = (180, 180)
thumbnail_size = (555, 1000)


def rgb_color_finder(rgb_img, color_min=(0, 0, 0), color_max=(255, 255, 255),
                     all_bands=1, r_mode='1'):
    """analyzes an RGB image, returns an image of the same size where each
    pixel is WHITE if the pixel in rgbImage MATCHES the color range
    color_min-to-color_max, or
    BLACK if the pixel in rgbImage DOES NOT MATCH the color range.
    a pixel is MATCHES the color range
            if all_bands!=0 and if for EVERY color pixel[i],
                color_min[i]<=pixel[i] and pixel[i]<=color_max[i], or
            if all_bands==0 and if for ANY color pixel[i],
                color_min[i]<=pixel[i] and pixel[i]<=color_max[i].
        r_mode determines the mode of the returned image ("1", "L" or "RGB")
    jjk  12/11/02"""
    in_bands = rgb_img.split()
    out_bands = []
    for src_band, c_min, c_max in zip(in_bands, color_min, color_max):
        out_bands.append(src_band.point(lambda v1, v2=c_min, v3=c_max:
                                        v2 <= v1 <= v3 and 255))
    if all_bands == 0:
        t_band = ImageChops.lighter(ImageChops.lighter(out_bands[0],
                                                       out_bands[1]),
                                    out_bands[2])
    else:
        t_band = ImageChops.darker(ImageChops.darker(out_bands[0],
                                                     out_bands[1]),
                                   out_bands[2])
    if r_mode == 'L':
        return t_band
    elif r_mode == 'RGB':
        return Image.merge('RGB', (t_band, t_band, t_band))  # 'RGB'
    else:  # r_mode=='1'
        return t_band.convert('1')


def rgb_color_replacer_by_mask(rgb_img, color, color_mask):
    rpl_img = Image.new(rgb_img.mode, rgb_img.size, color)
    return Image.composite(rpl_img, rgb_img, color_mask)


def rgb_color_replacer(rgb_img, color_min=(0, 0, 0), color_max=(32, 32, 32),
                       color_new=(255, 255, 255), all_bands=1):
    """analyzes an RGB image,
    finds all colors in the range color_min-to-color_max (see colorFinder()),
    creates and returns, with all found colors replaced by color_new"""
    color_mask = rgb_color_finder(rgb_img, color_min, color_max,
                                  all_bands=all_bands)
    rpl_img = Image.new(rgb_img.mode, rgb_img.size, color_new)
    return Image.composite(rpl_img, rgb_img, color_mask)


def get_bbox(im, border):
    """bounding box of an object different from frame color"""
    bg = Image.new(im.mode, im.size, border)
    diff = ImageChops.difference(im, bg)
    bbox = diff.getbbox()
    return bbox


def process(file_path, args):
    file_fullname, file_extension = os.path.splitext(file_path)
    file_name = os.path.basename(file_fullname)
    im = Image.open("%s" % file_path)
    print(".. processing %s, size %s" % (file_path, str(im.size)))

    # compute bounding box for cropping
    pim = im.convert("RGB", palette=Image.ADAPTIVE)

    t = pim.getpixel((1, 1))
    bbox = get_bbox(pim, t)
    bbox = (bbox[0]-args.border, bbox[1]-args.border,
            bbox[2]+args.border, bbox[3]+args.border)
    if not args.nocrop:
        pim = pim.crop(bbox)
    print("   -> trimming: %s.png, size %s, width at 80%% is %d" %
          (file_name, str(pim.size), int(pim.size[0]*0.8)))

    # transparent background
    pim.save("%s.png" % file_name, transparency=t)

    color_mask = rgb_color_finder(pim, t, t, all_bands=1)
    wim = rgb_color_replacer_by_mask(pim, (255, 255, 255), color_mask)
    wim.thumbnail(thumbnail_size, Image.LANCZOS)
    wim = wim.filter(ImageFilter.DETAIL)
    wim.save("%s.thumb.png" % file_name)
    print("   -> thumb: %s.thumb.png, size %s" % (file_name, str(wim.size)))


parser = argparse.ArgumentParser()
parser.add_argument("-n", "--nocrop", help="crop image",
                    action="store_true", default=False)
parser.add_argument("-b", "--border", help="border width", default=3)
parser.add_argument("files", type=str, help="file names to match")
arguments = parser.parse_args()

for f_name in arguments.files.split():
    process(f_name, arguments)
