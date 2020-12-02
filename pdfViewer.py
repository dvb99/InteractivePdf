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
import pvporcupine
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

def getTextFromPage(doc,curPage):
    # returns all textlines from given page
    lines = []
    lines.extend(doc[curPage].getText().split('\n'))
    return lines

def listen_to_voice_commands(window):
    audio_stream = None
    handle = None
    pa = None
    try:
        library_path = 'C:/Users/dheer/AppData/Local/Programs/Python/Python38/Lib/site-packages/pvporcupine/lib/windows/amd64/libpv_porcupine.dll'
        model_file_path = 'C:/Users/dheer/AppData/Local/Programs/Python/Python38/Lib/site-packages/pvporcupine/lib/common/porcupine_params.pv'
    # keyword_file_paths = ['C:/Users/dheer/AppData/Local/Programs/Python/Python38/Lib/site-packages/pvporcupine/resources/keyword_files/windows/bumblebee_windows.ppn']
        
        # use bumblebee to start reading , terminator to stop reading 
        num_keywords = ['bumblebee','terminator']
        sensitivity = [0.2,0.6]
        handle = pvporcupine.create(library_path,
                                    model_file_path,
                                    keywords=num_keywords,
                                    sensitivities=sensitivity
                                    )

        pa = pyaudio.PyAudio()
        audio_stream = pa.open(
                rate=handle.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=handle.frame_length)
        print('Listening for keyword bumblebee , terminator')

        while True:
            pcm = audio_stream.read(handle.frame_length)
            pcm = struct.unpack_from("h" * handle.frame_length, pcm)
            result = handle.process(pcm)
            if result >= 0:
                print('[%s] detected keyword ' % (str(datetime.now())), num_keywords[result] )
                if num_keywords[result] == "bumblebee":
                    window.write_event_value('start', '')
                elif num_keywords[result] == "terminator":
                    window.write_event_value('stop', '')
    except KeyboardInterrupt:
        print('stopping ...')
    finally:
        if handle is not None:
            handle.delete()

        if audio_stream is not None:
            audio_stream.close()

        if pa is not None:
            pa.terminate()

    _AUDIO_DEVICE_INFO_KEYS = ['index',
                            'name',
                            'defaultSampleRate',
                            'maxInputChannels']
    

def long_function(window):
    threading.Thread(target=listen_to_voice_commands, args=(window,), daemon=True).start()

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
    global is_reading 
    for line in pdfText:
        if is_reading:
            readeachline(line)   # pipelining each line to function        
        else:
            _thread.exit()
            

    # at the end of the work, before exiting, send a message back to the GUI indicating end
    gui_queue.put('{} ::: done'.format(cur_page))
    # at this point, the thread exits
    return

    
            
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
        global is_reading
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
        elif event =="start" :
            # LOCATION 2
            # STARTING long run by starting a thread
            if not is_reading:
                is_reading=True
                _thread.start_new_thread(play,(cur_page+1, gui_queue,getTextFromPage(doc,cur_page),),)
            else :
                print("First stop the reading")
        
        elif event =='stop':
            if is_reading:
                is_reading=False
        
        elif event == "Initiate":
            # This function starts microphone such that it will continuously listen for hot wards
            long_function(window)
             
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