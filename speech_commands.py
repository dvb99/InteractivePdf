import sys
import os
import pyaudio
import struct
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), './python'))

import pvporcupine

audio_stream = None
handle = None
pa = None

try:
    library_path = 'C:/Users/dheer/AppData/Local/Programs/Python/Python38/Lib/site-packages/pvporcupine/lib/windows/amd64/libpv_porcupine.dll'
    model_file_path = 'C:/Users/dheer/AppData/Local/Programs/Python/Python38/Lib/site-packages/pvporcupine/lib/common/porcupine_params.pv'
   # keyword_file_paths = ['C:/Users/dheer/AppData/Local/Programs/Python/Python38/Lib/site-packages/pvporcupine/resources/keyword_files/windows/bumblebee_windows.ppn']
    num_keywords = ['terminator', 'bumblebee']
    # sensitivity = [0.2]

    handle = pvporcupine.create(library_path,
                                model_file_path,
                                keywords=num_keywords
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