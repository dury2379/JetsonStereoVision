#!/usr/bin/python
import os
from datetime import datetime
from threading import Thread
import jetson_utils


class Jetson_Camera:

    def __init__(self, input_num, recording_dir, recording_name, flip=False):
        self.img = None
        self.video_input = None
        self.allow_read = True

        self.video_input_id = input_num
        # Set the expected input size for the model
        self.videoInput_setup = ["--input-width=1024", "--input-height=1024", "--input-rate=21.0"]
        if flip:
            self.videoInput_setup.append("--input-flip=rotate-180")
            print("CAMERA:    Added 180 deg rotation")
        self.video_input = jetson_utils.videoSource(str(self.video_input_id), self.videoInput_setup)
        print(recording_name + "Camera input is:" + str(input_num))

        if recording_name is None:
            now = datetime.now()
            recording_name = now.strftime("%Y-%m-%d_%H_%M_%S")
        self.output = jetson_utils.videoOutput(os.path.join(recording_dir, recording_name + '.avi'))
        self.alive = True
        self.thread = Thread(target=self.loop, args=())
        self.thread.deamon = True
        self.thread.start()

    def loop(self):
        try:
            while self.alive:
               img_local = self.video_input.Capture()
               if img_local is None:
                  print("Error: No image captured.")
                  continue
               
               self.allow_read = False
               self.img = self.pre_process(img_local)
               self.allow_read = True

               jetson_utils.cudaDeviceSynchronize()
               self.output.Render(img_local)
        except Exception as e:
            print("Error: ", e)

    def pre_process(self, img):
        # Tiling the 1024x1024 image into 4 512x512 images
        tiles = []
        
        coords = [
            (0, 0, 512, 512),
            (512, 0, 1024, 512),
            (0, 512, 512, 1024),
            (512, 512, 1024, 1024)
        ]
        
        for (x1, y1, x2, y2) in coords:
            tile = jetson_utils.cudaAllocMapped(width=512, height=512, format="rgb8")
            jetson_utils.cudaCrop(img, tile, x1, y1, x2, y2)
            tiles.append(tile)

        return tiles
    
    def is_thread_alive(self):
        return self.thread.isAlive()

    def kill(self):
        print("Killing the camera")
        self.alive = False
        self.thread.join()
