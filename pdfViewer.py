"""
@created: 2018-08-19 18:00:00
@author: (c) 2018 Jorj X. McKie
Display a PyMuPDF Document using Tkinter
-------------------------------------------------------------------------------
Dependencies:
-------------
PyMuPDF, PySimpleGUI > v2.9.0, Tkinter with Tk v8.6+, Python 3
License:
--------
GNU GPL V3+
Description
------------
Read filename from command line and start display with page 1.
Pages can be directly jumped to, or buttons for paging can be used.
We also interpret keyboard events to support paging by PageDown / PageUp
keys as if the resp. buttons were clicked. Similarly, we do not include
a 'Quit' button. Instead, the ESCAPE key can be used, or cancelling the window.
"""
import sys
import fitz
import PySimpleGUI as sg
from sys import exit

sg.theme('GreenTan')

if len(sys.argv) == 1:
    fname = sg.popup_get_file(
        'PDF Browser', 'PDF file to open', file_types=(("PDF Files", "*.pdf"),))
    if fname is None:
        sg.popup_cancel('Cancelling')
        exit(0)
else:
    fname = sys.argv[1]

doc = fitz.open(fname)
page_count = len(doc)

title = "PyMuPDF display of '%s', pages: %i" % (fname, page_count)

cur_page = 0  
data = doc[cur_page].getText() # show page 1 for start
txt_elem = sg.Multiline(
            default_text=data,
            size=(800,800),
            justification="c",font=["Arial", 15])
goto = sg.InputText(str(cur_page + 1), size=(5, 1))

layout = [
    [
        sg.Button('Prev'),
        sg.Button('Next'),
        sg.Text('Page:'),
        goto,
    ],
    [txt_elem],
]
my_keys = ("Next", "Next:34", "Prev", "Prior:33",
            "MouseWheel:Down", "MouseWheel:Up")

page_size = (600, 600)
window = sg.Window(title,
                    grab_anywhere=True,
                    resizable=True,
                   return_keyboard_events=True,
                    use_default_focus=False).Layout(layout)

old_page = 0

while True:
    event, values = window.read(timeout=100)
    zoom = 0
    force_page = False
    if event == sg.WIN_CLOSED:
        break

    if event in ("Escape:27",):  # this spares me a 'Quit' button!
        break
    if event[0] == chr(13):  # surprise: this is 'Enter'!
        try:
            cur_page = int(values[0]) - 1  # check if valid
            while cur_page < 0:
                cur_page += page_count
        except:
            cur_page = 0  # this guy's trying to fool me
        goto.update(str(cur_page + 1))
        # goto.TKStringVar.set(str(cur_page + 1))

    elif event in ("Next", "Next:34", "MouseWheel:Down"):
        cur_page += 1
    elif event in ("Prev", "Prior:33", "MouseWheel:Up"):
        cur_page -= 1
    

    # sanitize page number
    if cur_page >= page_count:  # wrap around
        cur_page = 0
    while cur_page < 0:  # we show conventional page numbers
        cur_page += page_count

    # prevent creating same data again
    if cur_page != old_page:
        force_page = True


    if force_page:
        data = doc[cur_page].getText()
        txt_elem.update(value=data)
        old_page = cur_page


    # update page number field
    if event in my_keys or not values[0]:
        goto.update(str(cur_page + 1))
        # goto.TKStringVar.set(str(cur_page + 1))