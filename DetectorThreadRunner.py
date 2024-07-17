"""
   The purpose of this class it to separate variables used inside a detection and geolocation thread and other threads
   that take data from that thread. Mixing up variables between two threads might cause thread conflicts, unless
   operations done on those variables are thread safe. DO NOT BYPASS Detector.py AND READ FOM THIS CLASSES INSTANCE
   ATTRIBUTES. USE GETTERS METHODS IN Detector.py INSTANCE.
"""
import requests
import base64
import math
import time
import Fuse
import jetson.inference
import jetson.utils
from Triangulation import stereo_vision
from dotenv import load_dotenv

class DetectorThreadRunner:
    def __init__(
        self, l_camera, r_camera, pitch, spread, fov, t_fuse, GPS_node, log_file
    ):
        MODEL_ID = load_dotenv().parsed["MODEL_ID"]
        API_KEY = load_dotenv().parsed["API_KEY"]

        self.l_camera = l_camera
        self.r_camera = r_camera
        self.pitch = pitch
        self.spread = spread
        self.fov = fov
        self.GPS = GPS_node
        #self.d_net = jetson.inference.detectNet("")
        self.url = f"http://localhost:9001/{MODEL_ID}/8?api_key={API_KEY}"
        self.person_loc = None
        self.detection_time = None
        self.log_f = log_file
        if t_fuse is None:
            self.detect_fuse = Fuse.Fuse()
        else:
            self.detect_fuse = t_fuse

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
        l_image = self.l_camera.img
        # l_image = self.l_camera.Capture()
        while not self.r_camera.allow_read:
            pass
        r_image = self.r_camera.img
        # r_image = self.r_camera.Capture()

        # Get GPS location from Mavlink module. Scene GPS is read at about the same time its safe to assume that the
        # location stores is tah location at which those pictures were taken.
        while not self.GPS.allow_read:
            pass
        image_location = self.GPS.loc
        
        # Get detections from both images.
        l_detections = self.send_image_to_model(l_image)["predictions"]
        r_detections = self.send_image_to_model(r_image)["predictions"]

        # Go through list of objects detected on the left and find a box with the highest confidence value.
        # "all_detections_l" variable is not used anywhere it's just a leftover from debugging.
        best_detection_l, all_detections_l = self.get_best_detection(l_detections)
        # Do the same for right image
        best_detection_r, all_detections_r = self.get_best_detection(r_detections)

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
                self.person_loc, self.detection_time = self.get_persons_loc(
                    l_image,
                    best_detection_l,
                    best_detection_r,
                    self.spread,
                    self.fov,
                    image_location,
                    print_mode="h",
                )
            else:
                # low confidence triangulation, just prints to a file. Results of this triangulation will not be sent to
                # other threads.
                self.get_persons_loc(
                    l_image,
                    best_detection_l,
                    best_detection_r,
                    self.spread,
                    self.fov,
                    image_location,
                    print_mode="l",
                )

        if person_location_internal is not None:
            self.person_loc = person_location_internal
            self.detection_time = time_stamp_internal

    def send_image_to_model(self, image):
        response = requests.post(self.url, data={"image": base64.b64encode(image).decode('utf-8')})
        if response.status_code == 200:
            return response.json()
        else:
            print("Error in request to model server ", response.status_code, response.text)
            return None

    def kill(self):
        self.l_camera.kill()
        self.r_camera.kill()

    def get_best_detection(self, detections: list):
        best_detection = None
        weed_detected_list = []

        if len(detections) > 0:
            for detection in detections:
                if detection["class"] == "weed":
                    weed_detected_list.append(detection)
                    if (
                        best_detection is None
                        or detection["confidence"] > best_detection["confidence"]
                    ):
                        best_detection = detection
        else:
            return None, None
        return best_detection, weed_detected_list

    def get_persons_loc(
        self, image, best_l, best_r, spread, fov, location, print_mode=None
    ):
        time_stamp = None
        prefix = "Low confidence"
        # Triangulation function will perform calculations to get direct distance, horizontal angle, and a vertical
        # angle to the target. Returns None if calculation fails.
        distance, angle, vertical = stereo_vision(
            spread=spread,
            center_right=best_r.Center,
            center_left=best_l.Center,
            fov=fov,
            image_width=image.width,
            image_height=image.height,
        )
        if not math.isnan(distance):
            # If triangulation calculation did not fail, then use "get_persons_GPS()" method to combine, GPS, heading,
            # horizontal and vertical angles, camera pitch angle, and distance to predict targets GPS location.
            persons_cords_local = self.GPS.get_persons_GPS(
                distance, angle, location, vertical, self.pitch
            )
            # Save the timestamp of when this triangulation happened.
            time_stamp = time.time()
            # Print to log file.
            if print_mode is not None:
                if print_mode == "h":
                    prefix = ">>> High confidence"
                self.log_f.write(prefix + " distance:" + str(distance) + "\n")
                self.log_f.write(prefix + " horizontal angle:" + str(angle) + "\n")
                self.log_f.write(prefix + " vertical angle:" + str(vertical) + "\n")
                self.log_f.write(
                    prefix + " coordinates:" + str(persons_cords_local) + "\n\n"
                )
            # Return persons GPS and time when this triangulation happened.
            return persons_cords_local, time_stamp
        # Return None when triangulation fails.
        return None, None
