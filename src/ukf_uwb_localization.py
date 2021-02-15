#! /usr/bin/env python

import rospy
import numpy as np
from ukf.fusion_ukf import FusionUKF
from ukf.datapoint import DataType, DataPoint
from nav_msgs.msg import Odometry
from visualization_msgs.msg import MarkerArray
from gtec_msgs.msg import Ranging
import tf
from tf.transformations import euler_from_quaternion, euler_from_quaternion 

class UKFUWBLocalization:
    def __init__(self, uwb_std=0.1, accel_std=0.01, yaw_accel_std=0.01, alpha=1):
        sensor_std = {
            DataType.UWB: {
                'std': [uwb_std],
                'nz': 1
            }
        }

        self.ukf = FusionUKF(sensor_std, accel_std, yaw_accel_std, alpha)

        self.anchor_poses = dict()
        self.tag_offset = self.retrieve_tag_offsets({"left_tag":1, "right_tag":0})

        print(self.tag_offset)

        anchors = '/gtec/toa/anchors'
        toa_ranging = '/gtec/toa/ranging'

        anchors_sub = rospy.Subscriber(anchors, MarkerArray, callback=self.add_anchors)
        ranging_sub = rospy.Subscriber(toa_ranging, Ranging, callback=self.add_ranging)
        odometry = '/odometry/filtered'
        odometry = rospy.Subscriber(odometry, Odometry, callback=self.add_odometry)

        publish_odom = '/jackal/uwb/odom'
        self.estimated_pose = rospy.Publisher(publish_odom, Odometry, queue_size=1)
        self.odom = Odometry()

    def retrieve_tag_offsets(self, tags, base_link='base_link'):
        transforms = dict() 

        listener = tf.TransformListener()

        rate = rospy.Rate(10.0)

        for tag in tags:
            while not rospy.is_shutdown():
                try:
                    (trans,rot) = listener.lookupTransform(base_link, tag, rospy.Time(0))
                    transforms[tags[tag]] = np.array([trans[0], trans[1]])
                    break

                except (tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException):
                    continue

                rate.sleep()

        return transforms

    def add_odometry(self, msg):
        px = msg.pose.pose.position.x
        py = msg.pose.pose.position.y

        v = msg.twist.twist.linear.x
        theta = euler_from_quaternion((
            msg.pose.pose.orientation.x,
            msg.pose.pose.orientation.y,
            msg.pose.pose.orientation.z,
            msg.pose.pose.orientation.w
        ))[2]

        if theta < 0:
            theta += (np.pi * 2)

        print theta, self.ukf.x[3]

        theta_yaw = msg.twist.twist.angular.z

        data = DataPoint(DataType.ODOMETRY, np.array([px, py, v, theta, theta_yaw]), rospy.get_time())

        self.ukf.update(data)

    def add_anchors(self, msg):
        # type: (MarkerArray) -> None

        for marker in msg.markers:
            self.anchor_poses[marker.id] = np.array([marker.pose.position.x,marker.pose.position.y]) 

    def add_ranging(self, msg):
        # type: (Ranging) -> None

        if msg.anchorId in self.anchor_poses:
            anchor_pose = self.anchor_poses[msg.anchorId]
            anchor_distance = msg.range / 1000.

            data = DataPoint(DataType.UWB, anchor_distance, rospy.get_time(), extra={
                "anchor": anchor_pose,
                # 'sensor_offset': self.tag_offset[msg.tagId]
                'sensor_offset': None
            })

            self.ukf.update(data)

    def intialize(self, x, P):
        self.ukf.initialize(x, P, rospy.get_time())

    def run(self):
        rate = rospy.Rate(30)

        while not rospy.is_shutdown():
            x, y, v, yaw, yaw_rate = self.ukf.x

            self.odom.pose.pose.position.x = x
            self.odom.pose.pose.position.y = y
            self.odom.twist.twist.linear.x = v
            self.odom.twist.twist.angular.z = yaw_rate

            self.estimated_pose.publish(self.odom)

            rate.sleep()

if __name__ == "__main__":
    rospy.init_node("ukf_uwb_localization_kalman")

    intial_pose = rospy.wait_for_message('/ground_truth/state', Odometry)
    x, y = intial_pose.pose.pose.position.x, intial_pose.pose.pose.position.y


    loc = UKFUWBLocalization(alpha=0.5)
    loc.intialize(np.array([x, y ]), np.eye(5) * .1)

    loc.run()

    rospy.spin()
