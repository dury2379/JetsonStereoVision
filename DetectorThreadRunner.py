"""
   The purpose of this class it to separate variables used inside a detection and geolocation thread and other threads
   that take data from that thread. Mixing up variables between two threads might cause thread conflicts, unless
   operations done on those variables are thread safe. DO NOT BYPASS Detector.py AND READ FOM THIS CLASSES INSTANCE
   ATTRIBUTES. USE GETTERS METHODS IN Detector.py INSTANCE.
"""

import math
import time
import Fuse
import jetson_inference
from Triangulation import stereo_vision


class DetectorThreadRunner:
    def __init__(self, l_camera, r_camera, pitch, spread, fov, t_fuse, GPS_node, log_file):
        self.l_camera = l_camera
        self.r_camera = r_camera
        self.pitch = pitch
        self.spread = spread
        self.fov = fov
        self.GPS = GPS_node
#        self.d_net = jetson_inference.detectNet(model="model/ssd-mobilenet.onnx", labels="model/labels.txt", input_blob="input_0", output_cvg="scores", output_bbox="boxes")
        self.d_net = jetson_inference.detectNet()
        self.person_loc = None
        self.detection_time = None
        self.log_f = log_file
        self.detect_fuse = Fuse.Fuse(t_fuse)

    def swap_cameras(self):
        self.l_camera, self.r_camera = self.r_camera, self.l_camera

    def thread_loop(self):
        r_image = None
        l_image = None
        image_location = None
        l_detections = None
        r_detections = None
        best_detection_l = None
        best_detection_r = None
        person_location_internal = None
        time_stamp_internal = None

        # Get images from both cameras.
        while not self.l_camera.allow_read:
            pass
        l_images = self.l_camera.img

        while not self.r_camera.allow_read:
            pass
        r_images = self.r_camera.img

        # Get GPS location from Mavlink module. Scene GPS is read at about the same time its safe to assume that the
        # location stores is tah location at which those pictures were taken.
        while not self.GPS.allow_read:
            pass
        image_location = self.GPS.loc
        
        try:
            # Use Jetson detect net to get a list of objects detected in left and right images
            # if l_image is not None:
            #    l_detections = self.d_net.Detect(l_image, overlay="box,labels,conf")
            # if r_image is not None: 
            #    r_detections = self.d_net.Detect(r_image, overlay="box,labels,conf")
            
            all_l_detections = []
            all_r_detections = []
            
            # Process each tile separately
            for l_image, r_image in zip(l_images, r_images):
                # Run inference on each tile
                l_detections = self.d_net.Detect(l_image, overlay="box,labels,conf")
                r_detections = self.d_net.Detect(r_image, overlay="box,labels,conf")
                
                all_l_detections.extend(l_detections)
                all_r_detections.extend(r_detections)
        except Exception as e:
            print("Error: ", e)
        # Go through list of objects detected on the left and find a box with the highest confidence value.
        # "all_detections_l" variable is not used anywhere it's just a leftover from debugging.
        best_detection_l, all_detections_l = self.get_best_detection(all_l_detections)
        # Do the same for right image
        best_detection_r, all_detections_r = self.get_best_detection(all_r_detections)

        """
            For triangulation to work with multiple targets, triangulation code has to know which detection in left 
            image correlates to which detection in the right image. In this case an assumption is made: the detection
            with the highest confidence in the left image corresponds to the right image's highest confidence detection.
            So, best detection in the left image is the same target as the right image best detection. Then 
            triangulation will be performed on those two detections. 
        """

        if best_detection_l is None or best_detection_r is None:
            # If only one of the cameras got a detection or neither, the that means it might be a false positive or,
            # target is too far away. In ether case triangulation should be delayed. So, the fuse is punished (fined).
            self.detect_fuse.punish()
        else:
            # If both images got a detection, the reward the fuse, indicating that detections is likely is not a false
            # positive and target is close.
            self.detect_fuse.reward()
            if self.detect_fuse:
                # If fuse fused, that there were multiple high confidence detection in a short period of time. So,
                # a triangulation is performed and the results of this triangulation will be sent to other threads.
                self.person_loc, self.detection_time = self.get_persons_loc(l_images, best_detection_l,
                                                                            best_detection_r, image_location,
                                                                            self.spread, self.fov,
                                                                            print_mode="h")
            else:
                # low confidence triangulation, just prints to a file. Results of this triangulation will not be sent to
                # other threads.
                self.get_persons_loc(l_images, best_detection_l, best_detection_r, self.spread, self.fov,
                                     image_location, print_mode="l")

        if person_location_internal is not None:
            self.person_loc = person_location_internal
            self.detection_time = time_stamp_internal

    def kill(self):
        self.l_camera.kill()
        self.r_camera.kill()

    def get_best_detection(self, detections: list):
        best_detection = None
        people_detected_list = []

        if len(detections) > 0:
            for detection in detections:
                if self.d_net.GetClassDesc(detection.ClassID) == 'person':
                    people_detected_list.append(detection)
                    if best_detection is None or detection.Confidence > best_detection.Confidence:
                        best_detection = detection
        else:
            return None, None
        return best_detection, people_detected_list

    def get_persons_loc(self, images, best_l, best_r, spread, fov, location, print_mode=None):
        time_stamp = None
        prefix = "Low confidence"
        persons_cords_local = None
        # Triangulation function will perform calculations to get direct distance, horizontal angle, and a vertical
        # angle to the target. Returns None if calculation fails.
        # For each tile in the image, calculate the distance, angle, and vertical angle to the target.
        
        for image in images:
            distance, angle, vertical = stereo_vision(spread=spread,
                                                    center_right=best_r.Center,
                                                    center_left=best_l.Center,
                                                    fov=fov,
                                                    image_width=image.width,
                                                    image_height=image.height)
            if not math.isnan(distance):
                # If triangulation calculation did not fail, then use "get_persons_GPS()" method to combine, GPS, heading,
                # horizontal and vertical angles, camera pitch angle, and distance to predict targets GPS location.
                persons_cords_local = self.GPS.get_persons_GPS(distance, angle, location,
                                                            vertical, self.pitch)
                # Save the timestamp of when this triangulation happened.
                time_stamp = time.time()
                # Print to log file.
                if print_mode is not None:
                    if print_mode == "h":
                        prefix = ">>> High confidence"
                    self.log_f.write(prefix + " distance:" + str(distance) + "\n")
                    self.log_f.write(prefix + " horizontal angle:" + str(angle) + "\n")
                    self.log_f.write(prefix + " vertical angle:" + str(vertical) + "\n")
                    self.log_f.write(prefix + " coordinates:" + str(persons_cords_local) + "\n\n")
                # Return persons GPS and time when this triangulation happened.
                return persons_cords_local, time_stamp
        # Return None when triangulation fails.
        return None, None
