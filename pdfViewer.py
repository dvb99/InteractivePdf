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
import pyttsx3 as tts
import queue
import threading
import _thread
import pyaudio
import struct
from datetime import datetime
import os
import snowboydecoder
import signal
sys.path.append(os.path.join(os.path.dirname(__file__), './python'))

"""
    You want to look for 3 points in this code, marked with comment "LOCATION X". 
    1. Where you put your call that takes a long time
    2. Where the trigger to make the call takes place in the event loop
    3. Where the completion of the call is indicated in the event loop
    Demo on how to add a long-running item to your PySimpleGUI Event Loop   
   
"""
# initialize engine
engine = tts.init()
is_reading = False
interrupted = False
line_Num = 0

def getTextFromPage(doc,curPage):
    # returns all textlines from given page
    lines = []
    lines.extend(doc[curPage].getText().split('\n'))
    return lines

def signal_handler(signal, frame):
    global interrupted
    print("I think Ctrl C")
    interrupted = True


def interrupt_callback():
    global interrupted
    return interrupted

def keywordSTART(window):
    # inform main thread start event is requested.
    window.write_event_value('start', '')

def keywordSTOP(window):
    # inform main thread stop event is requested.
    window.write_event_value('stop', '')

def keywordHIGHLIGHT(window):
    # inform highlight of current line is requested.
    window.write_event_value('highlight','')

def alwaysListening(window):

    models=["resources/alexa/alexa_02092017.umdl","resources/models/jarvis.umdl",
            "resources/models/computer.umdl"]

    # sensitivity = [0.5]*len(models)

    detector = snowboydecoder.HotwordDetector(models, 
                                            sensitivity=[0.6,0.8,0.8,0.6],
                                            apply_frontend=True)
    callbacks = [lambda: keywordSTART(window),
                lambda: keywordSTOP(window),
                lambda: keywordSTOP(window),
                lambda : keywordHIGHLIGHT(window)]
    print('Listening... Press Ctrl+C to exit')

    # main loop
    # make sure you have the same numbers of callbacks and models
    detector.start(detected_callback=callbacks,
                sleep_time=0.01)

    detector.terminate()



def long_function(window):
    threading.Thread(target=alwaysListening, args=(window,), daemon=True).start()

# ############################# User callable CPU intensive code #############################
# Put your long running code inside this "wrapper"
# NEVER make calls to PySimpleGUI from this thread (or any thread)!
# Create one of these functions for EVERY long-running call you want to make
def readeachline(line):
    global engine
    try:
        engine.say(line)
        engine.runAndWait()
    except Exception:
        print("Exception at readeachline")
      #  _thread.exit()
    else:
        pass
    

def play(cur_page, gui_queue,pdfText):
    # LOCATION 1
    # this is our "long running function call"
    global is_reading , line_Num
    for line in pdfText:
        if is_reading:
            line_Num += 1
            readeachline(line)   # pipelining each line to function        
        else:
            _thread.exit()
            

    # at the end of the work, before exiting, send a message back to the GUI indicating end
    gui_queue.put('{} ::: done'.format(cur_page))
    # at this point, the thread exits
    return


def highlight(fname, cur_page , line):
    # highlight the line in original pdf file.
    doc = fitz.open(fname)
    page = doc[cur_page]
    ### SEARCH
    text = line
    text_instances = page.searchFor(text)
    ### HIGHLIGHT
    for inst in text_instances:
        highlight = page.addHighlightAnnot(inst)      
    ### OUTPUT  
    doc.save(fname, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)
    doc.close()
            
############################# Begin GUI code #############################
def the_gui():
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
            sg.Button('Initiate'),
        ],
        [txt_elem],
    ]
    my_keys = ("Next", "Next:34", "Prev", "Prior:33"
                "MouseWheel:Down", "MouseWheel:Up")

    page_size = (750,700)
    window = sg.Window(title,size=page_size,
                        grab_anywhere=True,
                        resizable=True,
                    return_keyboard_events=True,
                        use_default_focus=False).Layout(layout)

    old_page = 0
    gui_queue = queue.Queue()  # queue used to communicate between the gui and long-running code
    # --------------------- EVENT LOOP ---------------------
    while True:
        event, values = window.read(timeout=100)
        lines =[]
        force_page = False
        global is_reading ,line_Num
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
            line_Num = 0
        elif event in ("Prev", "Prior:33", "MouseWheel:Up"):
            cur_page -= 1
            line_Num = 0
        elif event =="start" :
            # LOCATION 2
            # STARTING long run by starting a thread
            if not is_reading:
                is_reading=True
                _thread.start_new_thread(play,(cur_page+1, gui_queue,getTextFromPage(doc,cur_page)[line_Num:],),)
            else :
                print("First stop the reading")
        
        elif event =='stop':
            if is_reading:
                is_reading=False
        
        elif event == "Initiate":
            # This function starts microphone such that it will continuously listen for hot wards
            long_function(window)

        elif event == "highlight":
            # This event highlights currently reading line.
            highlight(fname,cur_page,(getTextFromPage(doc,cur_page)[line_Num]))     
        # --------------- Read next message coming in from threads ---------------
        try:
            message = gui_queue.get_nowait()    # see if something has been posted to Queue
        except queue.Empty:                     # get_nowait() will get exception when Queue is empty
            message = None                      # nothing in queue so do nothing
        
        # if message received from queue, then some work was completed
        if message is not None:
            # LOCATION 3
            # this is the place you would execute code at ENDING of long running task
            # You can check the completed_work_id variable to see exactly which long-running function completed
            completed_work_id = int(message[:message.index(' :::')])
            print("Page {} read completed".format(completed_work_id))

    
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

    # if user exits the window, then close the window and exit the GUI func
    doc.close()
    window.Close()

############################# Main #############################

if __name__ == '__main__':
    the_gui()
    print('Exiting Program')