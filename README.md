Orange Tools
============

Handy utilities used in development of [Orange](http://orange.biolab.si) 
data mining software or its documentation. 

trim.py
-------
Trims the input PNG file. The upper-left pixel of the image is considered on
the border and is used to mark the border color. Border is clipped-out, border
color is considered a background and is transparent. 

    % python trim.py examples/paint-data.png
    .. processing /Users/username/Desktop/paint-data.png, size (1264, 858)
       -> trimming: paint-data.png, size (1241, 834)
       -> thumb: paint-data-thumb.png, size (180, 120)

To construct a appropriate screenshot file on Windows 8, go to Control Panel, 
type "shadows" in the search box, and go to System, then there disable 
"Show shadows under windows". Choose a weird enough color for the background.

todo.py
-------
Manage list of stickers for Orange. Prepares a list of html pages for sticker
printout. The following call will print out all stickers that are marked not
printed and are of priority 3.

    % python todo.py -p 3

Stickers are defined on google sheet that can be accessed by biolab members.

stamper.py
----------
Run it on a screenshot to place labels (circled numbers from 1 to 10).
These augmented screenshots are then used in the widget documentation.
