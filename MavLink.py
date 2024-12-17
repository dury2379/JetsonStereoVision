import atexit
import math

from pymavlink import mavutil
from threading import Thread
import time
import geopy
import geopy.distance


class MavLink:
    def __init__(self, connection_str, baud, timeout=3):
        self.GLOBAL_POSITION_TIMEOUT = timeout

        self.loc = {'lat': -91, 'lon': -181, 'hdg': -1.0, 'type': 'none'}
        self.warning = "None"
        self.allow_read = True

        self.is_running = True

        self.connection = mavutil.mavlink_connection(device=connection_str, baud=baud)
        self.connection.wait_heartbeat()

        self.thread = Thread(target=self.loop, args=())
        self.thread.deamon = True
        self.thread.start()

    '''def __init__(self):
        self.loc = {'lat': -91, 'lon': -181, 'hdg': -1.0, 'type': 'none'}
        self.allow_read = True
        self.is_running = False'''
    def loop(self):
        last_global_position_recv = time.time()

        while self.is_running:
            message = self.connection.recv_match()
            if 90 >= self.loc['lat'] >= -90:
                old_loc = geopy.Point(self.loc['lat'], self.loc['lon'])
            else:
                old_loc = None
            if message is not None and message.get_type() == 'GLOBAL_POSITION_INT':
                self.allow_read = False
                self.loc['lat'] = message.lat * (10 ** -7)
                self.loc['lon'] = message.lon * (10 ** -7)
                self.loc['hdg'] = message.hdg / 100
                self.loc['type'] = 'GLOBAL_POSITION_INT'
                self.warning = "None"
                self.allow_read = True
                last_global_position_recv = time.time()
                if old_loc is not None:
                    current_loc = geopy.Point(self.loc['lat'], self.loc['lon'])
                    # print("MAVLINK GPS:   Devience in GPS is:", geopy.distance.geodesic(old_loc, current_loc).meters)
            if message is not None and time.time() - last_global_position_recv > self.GLOBAL_POSITION_TIMEOUT and message.get_type() == 'GPS_RAW_INT':
                self.allow_read = False
                self.loc['lat'] = message.lat * (10 ** -7)
                self.loc['lon'] = message.lon * (10 ** -7)
                self.loc['type'] = 'GPS_RAW_INT'
                last_global_position_recv = time.time()
                self.warning = "WARNING: No 'GLOBAL_POSITION_INT' detected within timeout window"
                self.allow_read = True
                if old_loc is not None:
                    current_loc = geopy.Point(self.loc['lat'], self.loc['lon'])
                    # print("MAVLINK GPS:   Devience in GPS is:", geopy.distance.geodesic(old_loc, current_loc).meters)
            time.sleep(0.1)

    def get_persons_GPS(self, distance, angle, cords, vertical_angle=0, mount_pitch=0):
        # "angle" is measured from a ray going directly to the right, but GPS need it to be relative to the ray going
        # straight forward. This does that conversion
        offset = angle - 90
        # Sometimes targets are located low down. In that case actual distance from topdown, is smaller than direct
        # distance from cameras to the target. GPS geolocation only needs distance in topdown perspective. This
        # calculation converts direct distance to topdown distance.
        distance_adj = math.cos(math.radians(abs(vertical_angle + mount_pitch))) * distance
        # If no GPS coordinates were provided then use current GPS coordinates, otherwise use provided GPS coordinates.
        # This if statement converts longitude and latitude values into geopy.Point class instance. Used for GPS
        # coordinate generation.
        # TODO: When updating threading make this GPS coordinate and heading read thread safe.
        if cords is not None:
            drone_GPS = geopy.Point(cords['lat'], cords['lon'])
            hdg = cords['hdg']
        else:
            while not self.allow_read:
                pass
            if self.loc['hdg'] == 'None':
                return None
            drone_GPS = geopy.Point(self.loc['lat'], self.loc['lon'])
            hdg = self.loc['hdg']

        # print("MAVLINK GPS:   Direction to the person is:", (hdg + offset))
        print("MAVLINK GPS:   Distance adjusted:", distance_adj)
        # Combine distance from topdown perspective, GPS location of when images were captured and cardinal direction
        # pointing to the target to get GPS location of the target. Cardinal direction to the target is calculated by
        # combining heading of the GPS location and angle that measures deviation from ray pointing forwards and ray
        # pointing to the target. If cameras are pointing in the same direction as GPS of the drone is facing then ray
        # pointing forwards and heading is the same ray.
        person_GPS = geopy.distance.geodesic(meters=distance_adj).destination(drone_GPS, hdg + offset)
        return {'lat': person_GPS.latitude, 'lon': person_GPS.longitude}

    def is_thread_alive(self):
        return self.thread.is_alive()
    def kill(self):
        if self.is_running:
            self.is_running = False
            self.thread.join()
            self.connection.close()

def kill(core):
    core.kill()


if __name__ == '__main__':
    connection_str = "/dev/ttyACM0"
    baud = 57600
    GPS = MavLink(connection_str, baud)
    location = {'lat': 34.05911, 'lon': -117.82080, 'hdg': 30, 'type': 'Test'}
    print(GPS.get_persons_GPS(20.0, 90, location))
    atexit.register(kill, GPS)
