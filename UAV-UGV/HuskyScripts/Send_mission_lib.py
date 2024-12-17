#!/usr/bin/env python

from __future__ import print_function
import actionlib
from geographic_msgs.msg import GeoPose
from robot_localization.srv import *
import rospy
import cpr_gps_navigation_msgs.msg
import utm
import cpr_gps_navigation_msgs.srv
from sensor_msgs.msg import NavSatFix
from robot_localization.srv import SetDatum

def find_utm_coords(lat, lon):
    u = utm.from_latlon(lat, lon)
    east = u[0]
    north = u[1]
    return north, east


'''
    Sets the datum and return datum in utm format.
    If the function fails to set the datum returns None
'''


def set_datum(datum_dict):
    # No need to convert to utm because the API uses lat/lon
    datum_north, datum_east = find_utm_coords(datum_dict["lat"], datum_dict["lon"])  # find utm coordinate of the datum
        
    rospy.wait_for_service('/set_datum',timeout = 2.0)
 
    try:
       datum_service = rospy.ServiceProxy('/set_datum', cpr_gps_navigation_msgs.srv.TaskSrv)
       res = datum_service("", [datum_dict["lat"], datum_dict["lon"]], [])
       rospy.loginfo("Datum set, sleeping for 2 seconds")
       print("Result: ", res)
       return {"north": datum_north, "east": datum_east}
    except rospy.ServiceException as e:
       print("Service call failed")
       return None


'''
    converts points (dict) from lon/lat format to utm format.
'''


def convert_point(point):
    north, east = find_utm_coords(point["lat"], point["lon"])
    return {"north": north, "east": east}


'''
    Crates the goal variable of type cpr_gps_navigation_msgs.msg.MissionGoal()
'''


def create_goal(goal_point, datum):
    # Creates a goal to send to the action server.
    goal = cpr_gps_navigation_msgs.msg.MissionGoal()

    goal.mission.header.seq = 1
    goal.mission.header.stamp = rospy.Time.now()
    goal.mission.header.frame_id = "map"

    goal_coords = convert_point(goal_point)

    goal.mission.goalpoint.x = goal_coords["east"] - datum["east"]
    goal.mission.goalpoint.y = goal_coords["north"] - datum["north"]
    goal.mission.goalpoint_theta = 0.0

    return goal


'''
    Creates list of viapoins in utm format.
    Also converts input list of viapoints from lon/lat
    format into utm format
'''


def create_viapoints_list(viapoints_list, datum_dict):
    result = []
    for point in viapoints_list:
        result.append(cpr_gps_navigation_msgs.msg.Waypoint())
        utm_point = convert_point(point)
        result[-1].x = utm_point["east"] - datum_dict["east"]
        result[-1].y = utm_point["north"] - datum_dict["north"]

    # result.reverse()
    return result


'''
    Sets final heading of the Husky.
'''


def set_final_heading(goal, theta):
    goal.mission.set_final_heading = True
    goal.mission.goalpoint_theta = theta


'''
    Sets tolerance of the points in the mission
'''


def set_tolerance(goal, m, rad):
    goal.mission.set_goal_tolerance = True
    goal.mission.pose_tolerance = m
    goal.mission.yaw_tolerance = rad


'''
    Creates and sends mission to the Husky
    goal point is a final destination (GPS coordinate) if the mission it is sent in form of a dictionary
    with key pairs of "lat": float_lat and "lon": float_lon
        example:
            goal_point = {"lat": 34.059361, "lon": -117.820990}
    
    Viapoints are a set of points that Husky has to travel through before reaching the goalpoint. 
    Viapoints are entered as a list of dictionaries. Each dictionary is a GPS coordinate formatted same 
    as goal point.
        example:
            viapoints = [{"lat": 34.059453, "lon": -117.821131}, {"lat": 34.059260, "lon": -117.821073}]
    
    Datum is a reference point that is near the mission. It is formatted same as a goal point.
        Example:
            datum = {"lat": 34.059319, "lon": -117.820521}
    
    Theta is the direction in Husky will face at the end of the mission. Formatted as a float value.
    
    # TODO: Figure out if theta is in rads or degrees: Degrees
    
    # tolerance_rad is acceptable error of theta. Assumed to be measured in radians. Formatted as a float value.
    
    # tolerance_m is acceptable error of the position of the Husky. Measured in meters, formatted as float.
    
    
    
    

'''


def send_mission(goal_dict, datum_dict=None, viapoints_list=[], theta=30,
                 tolerance_rad=0.4, tolerance_m=0.2, wait_time=60):
    print("Sending mission: ", goal_dict)
    if datum_dict is None:
        datum_dict = get_position_husky()
    print(datum_dict)
    datum_utm = set_datum(datum_dict)

    if datum_utm is None:
        return

    # sleep to make sure datum is set properly and ekfs are converged
    rospy.sleep(2.0)

    # Creates a SimpleActionClient, passing the type of the action
    client = actionlib.SimpleActionClient('missionplan', cpr_gps_navigation_msgs.msg.MissionAction)
    # Waits until the action server has started up and started
    # listening for goals.
    if client.wait_for_server(timeout=rospy.Duration(5.0)):
        goal = create_goal(goal_dict, datum_utm)

#        goal.mission.viapoints = create_viapoints_list(viapoints_list, datum_utm)

        set_final_heading(goal, theta)

        set_tolerance(goal, tolerance_m, tolerance_rad)
        # Sends the goal to the action server.
        client.send_goal(goal)

        if (client.wait_for_result(timeout=rospy.Duration(wait_time))):
            return client.get_result()
        else:
            client.cancel_goal()
            print("Mission took too long, moving on.")
            return False
    else:
        return False

    #client.wait_for_result()

    #return client.get_result()

global msg_lat
global msg_lon

def callback(data):
    global msg_lat, msg_lon
    msg_lat = data.latitude
    msg_lon = data.longitude

"""
Gets the current position of the Husky in the form of a dictionary with keys "lat" and "lon"
and sets the datum to that position.
"""
def get_position_husky():
    try:
       global msg_lon, msg_lat
       datum = {"lat":None, "lon":None}
       sub = rospy.Subscriber('/piksi_position/navsatfix_spp', NavSatFix, callback)
       msg_lon, msg_lat = None, None
      
       while True:
           if msg_lat is not None and msg_lon is not None:
              datum["lat"] = msg_lat
              datum["lon"] = msg_lon
              break
       return datum
    except Exception as e:
        print("Service call failed", e)
        return None



#=============TESTING================
if __name__ == '__main__':
    goal_point = {"lat": 34.0592138, "lon": -117.8204486}

    try:
        rospy.init_node('Mission_library')

        res = send_mission(goal_dict=goal_point)
        if res:
             print("mission completed!")
        else:
             print("mission failed!")
    except rospy.ROSInterruptException:
        print("mission failed!")
        pass

