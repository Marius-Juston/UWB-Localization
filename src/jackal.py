#! /usr/bin/env python

import rospy

print(__name__)

from .ukf_uwb_localization import UKFUWBLocalization, get_tag_ids, get_time
from gtec_msgs.msg import Ranging

class Jackal():
    def __init__(self):
        p = [1.0001, 11.0, 14.0001, 20.9001, 1.0001, 0.0001, 0.0001, 3.9001, 4.9001, 1.0, 0, 0.0001, 0.0001, 0.0001, 2.0001, 0.0001, 0.0001]

        self.ns = rospy.get_namespace()
        self.right_tag, self.left_tag, self.anchor = get_tag_ids(self.ns)

        print("Namespace:", self.ns)

        self.is_localized = False
        rospy.set_param("is_localized", self.is_localized)

        self.loc = UKFUWBLocalization(p[0], p[1:7], accel_std=p[7], yaw_accel_std=p[8], alpha=p[9], beta=p[10], namespace=self.ns, right_tag=self.right_tag, left_tag=self.left_tag)

        rospy.set_param("left_id", self.left_tag)
        rospy.set_param("right_id", self.right_tag)
        rospy.set_param("anchor", self.anchor)

        toa_ranging = '/gtec/toa/ranging'

        ranging_sub = rospy.Subscriber(toa_ranging, Ranging, callback=self.add_ranging)

        self.ranging_data = []

    def add_ranging(self, msg):
        # type: (Ranging) -> None

        self.ranging_data.append(
            {
                "time": get_time(),
                "anchorID": msg.anchorId,
                "tagID": msg.tagId,
                "range": msg.range / 1000
            }
        )

    def explore_recorded_data(self):
        data = {
            "anchors": [],
            "localized": [],
            "unlocalized": []
        }

    def step(self):
        if self.is_localized:
            self.loc.step()
        else:
            pass

        
        rospy.set_param("is_localized", self.is_localized)

if __name__ == "__main__":
    rospy.init_node("full_jackal", anonymous=True)


    rospy.spin()


