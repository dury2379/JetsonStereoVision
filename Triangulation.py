import math


def stereo_vision(spread, center_right, center_left, fov, image_width, image_height):
    # converting fov and image_width to float
    fov = fov * 1.0
    image_width = image_width * 1.0
    dpp = fov / image_width  # calculating degrees per pixel (dpp)

    # Get angle between right edge of the fov and the line of sight in the left image
    # (90 - fov / 2) -- calculates angle between the line that connects two cameras (spread/separation) and the edge of
    # the fov.
    # center_left[0] -- this is x position of the center of the detection, it is measured in pixels from leftmost edge
    # of the image.
    # (image_width - center_left[0]) -- converts x pixel value measured from left edge of the image to number of pixels
    # from right edge of the image.
    # Multiply value from above by amount of degrees per pixel (dpp) to get number angle between right edge of the fov
    # and line of sight to the target.
    # Add angle from above to angle between the line that connects two cameras (spread/separation) and the edge of the
    # fov and get angle between the spread and line of sight to the target
    angle_left = (90 - fov / 2) + (image_width - center_left[0]) * dpp
    # Do the same calculation as above but this time use angle measured from left side of the fov to the line of sight
    # to the target (uses x pixel value measured from left side of the image, so conversion is not needed).
    angle_right = (90 - fov / 2) + center_right[0] * dpp
    # Find 3rd angle.
    # Sum of all angles in a triangle is 180 deg.
    # By subtracting two angle calculated above from 180 deg get angle between two lines of sight when they converge on
    # target.
    angle_center = 180 - angle_left - angle_right

    # if angle is 0 or less tan 0, then triangle cannot be formed.
    # Triangulation fails.
    if angle_center <= 0:
        print("Object is too far!")
        return float('NaN'), float('NaN'), float('NaN')
    print("TRIANGULATION:    Central angle: ", angle_center)

    # Calculate vertical angle.
    # (center_left[1] + center_right[1]) / 2.0 -- average y pixel value from both left and right detections. This value
    # is measured in pixels from the top of the image going down.
    # (image_height / 2.0) -- subtract the amount of pixels to convert from pixels from the top, to amount of pixels
    # from central horizontal line.
    # Then multiply by degrees per pixel to get angle from ray going out of the center of that camera to the line of
    # sight to the target. Negative - target is above of where camera is looking, Positive - target is below of where
    # the camera is looking.
    # This measures angle in vertical profile only, not including targets offset left to right. Or simpli how many
    # degrees the camera should be rotated up or down so that horizontal middle line (the line that divides image into
    # top half and bottom half) will go through the center of the target.
    vertical_angle = ((center_left[1] + center_right[1]) / 2.0 - (image_height / 2.0)) * dpp
    print("TRIANGULATION:    Vertical angle:", vertical_angle)

    # Get the angle between line that connects the center of spread (line connecting two cameras) to target and another
    # line connecting center of the spread to left camera
    angle_center_target = 180 - angle_left - (angle_center / 2)
    print("TRIANGULATION:    Horizontal angle:", angle_center_target)

    # Convert angles to radians.
    # Used for sin()
    angle_left = math.radians(angle_left)
    angle_right = math.radians(angle_right)
    angle_center = math.radians(angle_center)

    # Using law of signs calculate distance from left camera to the target.
    distance_left = spread * math.sin(angle_right) / math.sin(angle_center)
    # Using law of signs calculate distance from right camera to the target.
    distance_right = spread * math.sin(angle_left) / math.sin(angle_center)

    # Calculate distance from the target to center point inbetween two cameras (center of the spread).
    # Simple take the average of distances from left camera to the target and distance from right camera to the target.
    distance_average = (distance_left + distance_right) / 2

    # Return 3 things:
    # 1. Distance from center of the camera spread to the target.
    # 2. Angle between two lines:
    #       -> one that connects center point on the spread to the target
    #       -> and another line that connects center point on the spread to the left camera.
    # 3. Angle from the horizontal centerline to the canter of the target. This angle does not include horizontal
    # deviation, and only tells how many degrees is the line of sight to the target is above the horizontal plane of
    # the camera.
    return distance_average, angle_center_target, vertical_angle


