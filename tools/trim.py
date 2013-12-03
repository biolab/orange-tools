#!/sw/bin/python2.7

"""
Blaz Zupan, blaz.zupan at fri.uni-lj.si
Ver 1.0: July 2010

Trims the input PNG file. The upper-left pixel of the image is considered on the border
and is used to mark the border color. 
"""

import getopt
import sys
from PIL import Image
from PIL import ImageChops
from PIL import ImageFilter
import os.path
import glob
import re

thumbnail_size = (180, 180)
showcase_size= (400, 700)
border = 2

# file prefixes
ORG = "org" # original snapshot
SNP = "snp" # snapshot with transparent background
SCA = "shc" # showcase size (enhanced borders, white, front page)
TBN = "tbn" # thumbnail (white background)

def usage():
    print "usage: %s files [-b border -c]" % (sys.argv[0])
    print
    print "Examples:"
    print "%s files" % (sys.argv[0])
    print "%s files -b 10" % (sys.argv[0])
    print "%s -c file" % (sys.argv[0])
    print
    print "Filetypes (X-*.png):"
    print "  %s-*.png: original snapshots (with border/backgroun color)" % ORG
    print "  %s-*.png: thumbnail (white border/background)" % TBN
    print "  %s-*.png: snapshot (transparent border/background" % SNP
    print "  %s-*.png: showcase size (enhanced edges, white background, for front page)" % SCA
    sys.exit(0)
    
p_add = lambda a,b : map(lambda x,y: x+y, a, b)
p_check = lambda a, b: a[0]==b[0] or a[1]==b[1] 


def rgbColorFinder(rgbImg, colormin=(0,0,0), colormax=(255,255,255), allbands=1, rmode='1'):
    '''analyzes an RGB image, returns an image of the same size where each pixel is
            WHITE if the pixel in rgbImage MATCHES the color range colormin-to-colormax, or 
            BLACK if the pixel in rgbImage DOES NOT MATCH the color range.
        a pixel is MATCHES the color range
            if allbands!=0 and if for EVERY color pixel[i],
                colormin[i]<=pixel[i] and pixel[i]<=colormax[i], or
            if allbands==0 and if for ANY color pixel[i],
                colormin[i]<=pixel[i] and pixel[i]<=colormax[i].
        rmode determines the mode of the returned image ("1", "L" or "RGB")
    jjk  12/11/02'''
    inbands = rgbImg.split()
    outbands = []
    for srcband, cmin, cmax in zip(inbands, colormin, colormax):
        outbands.append(srcband.point(lambda v1, v2=cmin, v3=cmax: v2<=v1 and v1<=v3 and 255))
    if allbands==0:
        tband = ImageChops.lighter(ImageChops.lighter(outbands[0], outbands[1]), outbands[2])
    else:
        tband = ImageChops.darker(ImageChops.darker(outbands[0], outbands[1]), outbands[2])
    if rmode=='L':
        return tband
    elif rmode=='RGB':
        return Image.merge('RGB', (tband, tband, tband)) # 'RGB'
    else:  # rmode=='1'
        return tband.convert('1')
    
def rgbColorReplacerByMask(rgbImg, color, colorMask):
    rplImg = Image.new(rgbImg.mode, rgbImg.size, color)
    return Image.composite(rplImg, rgbImg, colorMask)

def rgbColorReplacer(rgbImg, colormin=(0,0,0), colormax=(32,32,32), colornew=(255,255,255), allbands=1):
    '''analyzes an RGB image,
    finds all colors in the range colormin-to-colormax (see colorFinder()),
    creates and returns, with all found colors replaced by colornew
    jjk  12/11/02'''
    colorMask = rgbColorFinder(rgbImg, colormin, colormax, allbands=allbands)
    rplImg = Image.new(rgbImg.mode, rgbImg.size, colornew)
    return Image.composite(rplImg, rgbImg, colorMask)

def get_bbox(im, border):
    """bounding box of an object different from frame color"""
    bg = Image.new(im.mode, im.size, border)
    diff = ImageChops.difference(im, bg)
    bbox = diff.getbbox()
    return bbox

def process(image_files, crop_only=False):
    global im
    for fname in image_files:
        im = Image.open("%s-%s.png" % (ORG, fname))
        print ".. processing %s, orig: %s" % (fname, str(im.size)),

        if not thumbnail_only:
            # compute bounding box for cropping
            pim = im.convert('P', palette=Image.ADAPTIVE)
            t = pim.getpixel((1,1))
            bbox = get_bbox(pim, t)
            bbox = (bbox[0]-border, bbox[1]-border, bbox[2]+border, bbox[3]+border)
            pim = pim.crop(bbox)
            print "-> %s" % (str(pim.size))
    
            if crop_only:
                pim.save("%s.png" % fname, transparency=t)
                return
            
            # save target snapshot with transparent background
            pim.save("%s-%s.png" % (SNP, fname), transparency=t)
            
            # construct image with white instead of transparent color, but remember the mask
            t = im.getpixel((1,1))
            color_mask = rgbColorFinder(im, t, t, allbands=1)
            wim = rgbColorReplacerByMask(im, (255,255,255), color_mask)
        else:
            wim = im
    
        # filter white image to emphasize the lines            
        wim = wim.filter(ImageFilter.DETAIL)
        if not thumbnail_only:
            wim = wim.crop(bbox)
        wim.save("dummy.png")

        # keep white (no transparency) with thumbnails
        wim.thumbnail(thumbnail_size, Image.ANTIALIAS)
        wim.save("%s-%s.png" % (TBN, fname))
        
        # showcase image (front page)
        im = Image.open("dummy.png")
        os.remove("dummy.png")
    
        im.thumbnail(showcase_size, Image.ANTIALIAS)
        im.save("%s-%s.png" % (SCA, fname))

def main(argv):  
    global border, crop_only, thumbnail_only
    crop_only = False
    thumbnail_only = False
    
    try:                                
        opts, args = getopt.getopt(argv, "ht:cb:m", ["help", "transparency=", "crop", "border=", "minimal"])
    except getopt.GetoptError:
        usage()
        sys.exit(2)

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit()
        elif opt in ("-t", "--transparency"):
            print ".. transparency color", arg
        elif opt in ("-b", "--border"):
            border = int(arg)
        elif opt in ("-c", "--crop"):
            crop_only = True 
        elif opt in ("-m", "--minimal"):
            thumbnail_only = True

    orig_pattern = re.compile("%s-(.+?).png" % ORG)

    if crop_only:
        candidates = [orig_pattern.match(name).group(1) for name in args]
        process(candidates, crop_only=True)
    else:
        thumb_pattern = re.compile("%s-(.+?).png" % TBN)
        candidates = [orig_pattern.match(name).group(1) for name in glob.glob("%s-*.png" % ORG)]
        thumbnails = [thumb_pattern.match(name).group(1) for name in glob.glob("%s-*.png" % TBN)]
        names = [candidate for candidate in candidates if candidate not in thumbnails]
        process(names)
    #    process(args)

main(sys.argv[1:])
