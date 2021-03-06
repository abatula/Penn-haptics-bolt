#!/usr/bin/env python
import roslib; roslib.load_manifest('pr2_arm_state_aggregator')
import rospy
import os
import rosjson_time
import tf
import threading
import pr2_joint_states_listener
from pr2_arm_state_aggregator.msg import PR2ArmState
from pr2_arm_state_aggregator.msg import ArmJointState
from pr2_arm_state_aggregator.msg import TransformVerbose

class PR2ArmAggregator:

    def __init__(self, arm_name):
        rospy.init_node('pr2_arm_state_pub', anonymous=True)
        rospy.loginfo('pr2_arm_state_pub initializing...')
        self.arm_name = arm_name
        self.arm_side = arm_name[0]
        self.pr2_arm_state = PR2ArmState()
        self.pr2_arm_state.arm_name = self.arm_name

        self.tf_listener = tf.TransformListener()
        rospy.loginfo('tf listener up and running...')
        self.joint_states = pr2_joint_states_listener.PR2JointStatesListener()
        rospy.loginfo('pr2 joint state listener up and running...')
        self.joint_names = [self.arm_side+'_shoulder_pan_joint',
                   self.arm_side+'_shoulder_lift_joint',
                   self.arm_side+'_upper_arm_roll_joint',
                   self.arm_side+'_elbow_flex_joint',
                   self.arm_side+'_forearm_roll_joint',
                   self.arm_side+'_wrist_flex_joint',
                   self.arm_side+'_wrist_roll_joint',
                   self.arm_side+'_gripper_joint']
        self.tf_child_names = [ '/'+self.arm_side+'_shoulder_pan_link',
                                '/'+self.arm_side+'_shoulder_lift_link',
                                '/'+self.arm_side+'_upper_arm_roll_link',
                                '/'+self.arm_side+'_upper_arm_link',
                                '/'+self.arm_side+'_elbow_flex_link',
                                '/'+self.arm_side+'_forearm_roll_link',
                                '/'+self.arm_side+'_forearm_link',
                                '/'+self.arm_side+'_wrist_flex_link',
                                '/'+self.arm_side+'_wrist_roll_link',
                                '/'+self.arm_side+'_gripper_palm_link',
                                '/'+self.arm_side+'_gripper_tool_frame',
                                '/'+self.arm_side+'_gripper_l_finger_link',
                                '/'+self.arm_side+'_gripper_l_finger_tip_link',
                                '/'+self.arm_side+'_gripper_r_finger_link',
                                '/'+self.arm_side+'_gripper_r_finger_tip_link'
                                ]
        self.tf_parent_name = '/torso_lift_link'
        
        for ind,joint_name in enumerate(self.joint_names):
            new_joint_state = ArmJointState()
            self.pr2_arm_state.joint_states.append(new_joint_state)
            self.pr2_arm_state.joint_states[ind].name = joint_name

        for ind,xform_name in enumerate(self.tf_child_names):
            new_tf = TransformVerbose()
            self.pr2_arm_state.transforms.append(new_tf)
            self.pr2_arm_state.transforms[ind].child_frame_id = xform_name
            self.pr2_arm_state.transforms[ind].parent_frame_id = self.tf_parent_name
        new_tf = TransformVerbose()
        self.pr2_arm_state.transforms.append(new_tf)
        end_ind = len(self.pr2_arm_state.transforms)-1
        self.pr2_arm_state.transforms[end_ind].child_frame_id = '/torso_lift_link'
        self.pr2_arm_state.transforms[end_ind].parent_frame_id = '/base_link'

        rospy.sleep(1.0) #sleeps to give the tf listener enough time to buffer
        rospy.loginfo('Beginning to Publish Arm Joint Positions, Velocities, Efforts, and Transformations...')

 
    # Called every loop to gather data
    def gatherArmData(self):
          
        #Grab all Joint efforts
        (valid, position, velocity, effort) = self.joint_states.return_joint_states(self.joint_names)
        
        for ind,joint_name in enumerate(self.joint_names):
            self.pr2_arm_state.joint_states[ind].position = position[ind]
            self.pr2_arm_state.joint_states[ind].velocity = velocity[ind]
            self.pr2_arm_state.joint_states[ind].effort = effort[ind]
        
        #Grab transformations
        for ind,xform_name in enumerate(self.tf_child_names):
            #Grab Transformations for each finger, and tool frame 
            (tf_trans, tf_rot, tf_valid) = self.tfLookUp(self.tf_parent_name, xform_name)
            self.pr2_arm_state.transforms[ind].transform.translation.x = tf_trans[0]
            self.pr2_arm_state.transforms[ind].transform.translation.y = tf_trans[1]
            self.pr2_arm_state.transforms[ind].transform.translation.z = tf_trans[2]
            self.pr2_arm_state.transforms[ind].transform.rotation.x = tf_rot[0]
            self.pr2_arm_state.transforms[ind].transform.rotation.y = tf_rot[1]
            self.pr2_arm_state.transforms[ind].transform.rotation.z = tf_rot[2]
            self.pr2_arm_state.transforms[ind].transform.rotation.w = tf_rot[3]
            self.pr2_arm_state.transforms[ind].transform_valid = tf_valid

    def tfLookUp(self, transform_from, transform_to):
        tf_trans = [0.0, 0.0, 0.0]
        tf_rot = [0.0, 0.0, 0.0, 0.0]
        tf_valid = True
        try:
            (tf_trans,tf_rot) = self.tf_listener.lookupTransform(transform_from, transform_to, rospy.Time(0))
        except (tf.LookupException, tf.ConnectivityException):
            tf_valid = False
        return (tf_trans, tf_rot, tf_valid)

    # Setup the subscriber Node
    def startPublisher(self):
        # Initialize the subscriber node 
        pub = rospy.Publisher("pr2_arm_state", PR2ArmState)
        rate = rospy.Rate(100.0)
        while not rospy.is_shutdown():
          self.gatherArmData()
          pub.publish(self.pr2_arm_state)
          rate.sleep()

if __name__ == '__main__':

    pr2_arm_agg = PR2ArmAggregator('left_arm')
    pr2_arm_agg.startPublisher()
