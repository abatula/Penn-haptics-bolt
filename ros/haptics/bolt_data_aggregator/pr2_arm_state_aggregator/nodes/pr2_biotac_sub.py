#!/usr/bin/env python
import roslib; roslib.load_manifest('pr2_arm_state_aggregator')
import rospy
import os
import rosjson_time
import tf
import threading
import pr2_joint_states_listener
from std_msgs.msg import Int8
from std_msgs.msg import String
from pr2_gripper_accelerometer.msg import PR2GripperAccelerometerData
from biotac_sensors.msg import BioTacHand
from pr2_arm_state_aggregator.msg import PR2BioTacLog
from pr2_arm_state_aggregator.msg import ArmJointState
from pr2_arm_state_aggregator.msg import TransformVerbose

class PR2BioTacLogger:

    def __init__(self, arm_name):

        # Initialize node
        rospy.init_node('pr2_biotac_logger')
        rospy.loginfo('pr2_biotac_logger initializing...')
        self.arm_name = arm_name
        self.arm_side = arm_name[0]
        self.frame_count = 1
        self.tf_listener = tf.TransformListener()
        self.gripper_accelerometer = PR2GripperAccelerometerData()
        self.controller_state = Int8(0);
        self.controller_state_detail = String("");
        rospy.loginfo('tf listener up and running...')
        self.joint_states = pr2_joint_states_listener.PR2JointStatesListener()
        rospy.loginfo('pr2 joint state listener up and running...')

        # Setup which joints to listen to
        self.joint_names = [self.arm_side+'_shoulder_pan_joint',
                   self.arm_side+'_shoulder_lift_joint',
                   self.arm_side+'_upper_arm_roll_joint',
                   self.arm_side+'_elbow_flex_joint',
                   self.arm_side+'_forearm_roll_joint',
                   self.arm_side+'_wrist_flex_joint',
                   self.arm_side+'_wrist_roll_joint',
                   self.arm_side+'_gripper_joint']
        self.tf_child_names = [
                                '/'+self.arm_side+'_shoulder_pan_link',
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
        self.pr2_biotac_log = PR2BioTacLog()
        
        for ind,joint_name in enumerate(self.joint_names):
            new_joint_state = ArmJointState()
            self.pr2_biotac_log.joint_states.append(new_joint_state)
            self.pr2_biotac_log.joint_states[ind].name = joint_name

        for ind,xform_name in enumerate(self.tf_child_names):
            new_tf = TransformVerbose()
            self.pr2_biotac_log.transforms.append(new_tf)
            self.pr2_biotac_log.transforms[ind].child_frame_id = xform_name
            self.pr2_biotac_log.transforms[ind].parent_frame_id = self.tf_parent_name
        
        new_tf = TransformVerbose()
        self.pr2_biotac_log.transforms.append(new_tf)
        end_ind = len(self.pr2_biotac_log.transforms)-1
        self.pr2_biotac_log.transforms[end_ind].child_frame_id = '/torso_lift_link'
        self.pr2_biotac_log.transforms[end_ind].parent_frame_id = '/base_link'


        rospy.sleep(1.0) #sleeps to give the tf listener enough time to buffer
        rospy.loginfo('Let''s get this show on the road!')

        # File writing Setup
        #Find this node's directory for default data writing path
        self.package_dir = roslib.packages.get_pkg_dir('pr2_arm_state_aggregator')
        #Find the data writing path parameter. If it is not set, set it to be this nodes's directory
        self.path_param = rospy.get_name() + '/data_path'
        self.output_path = rospy.get_param(self.path_param, (self.package_dir) ) + '/json_files'

        # Check for 'json_files' directory
        dir_status = self.check_dir(self.output_path)
        if dir_status:
          rospy.loginfo('The ''json_files'' directory was successfully created.')

        #Find the output filename or set it to 'default.json if not set'
        self.file_param = rospy.get_name() + '/filename'
        self.fileName =  self.output_path+ '/' + rospy.get_param(self.file_param,'default.json')
        if not self.fileName.endswith('.json'):
          self.fileName = self.fileName + '.json'

        print "pqrst "+self.output_path
        

        # Create initial file - delete existing file with same name 
        self.fout = open(self.fileName,'w')
        self.fout.write("[\n")

        rospy.loginfo(rospy.get_name()+' Starting to Log to file %s:',self.fileName);

    # Called each time there is a new biotac message
    def biotacCallback(self,data):
        #Grab all Joint efforts
        (valid, position, velocity, effort) = self.joint_states.return_joint_states(self.joint_names)
        for ind,joint_name in enumerate(self.joint_names):
            self.pr2_biotac_log.joint_states[ind].position = position[ind]
            self.pr2_biotac_log.joint_states[ind].velocity = velocity[ind]
            self.pr2_biotac_log.joint_states[ind].effort = effort[ind]
        #print time
        for ind,xform_name in enumerate(self.tf_child_names):
            #Grab Transformations for each finger, and tool frame 
            (tf_trans, tf_rot, tf_valid) = self.tfLookUp(self.tf_parent_name, xform_name)
            self.pr2_biotac_log.transforms[ind].transform.translation = tf_trans
            self.pr2_biotac_log.transforms[ind].transform.rotation = tf_rot
            self.pr2_biotac_log.transforms[ind].transform_valid = tf_valid

        # Store off the BioTac Data Message
        self.pr2_biotac_log.bt_hand = data

        # Store the accelerometer and gripper aperture position
        self.pr2_biotac_log.gripper_accelerometer = self.gripper_accelerometer

        # Store the controller state 
        self.pr2_biotac_log.controller_state = self.controller_state
        self.pr2_biotac_log.controller_state_detail = self.controller_state_detail

        # Stores the frame count into the message
        self.pr2_biotac_log.frame_count = self.frame_count
        
        # Uses rosjson_time to convert message to JSON 
        toWrite = rosjson_time.ros_message_to_json(self.pr2_biotac_log) + "\n"
        self.fout.write(toWrite)

        # Move to next frame 
        self.frame_count += 1

    # Used to loop the transforms
    def tfLookUp(self, transform_from, transform_to):
        tf_trans = [0.0, 0.0, 0.0]
        tf_rot = [0.0, 0.0, 0.0, 0.0]
        tf_valid = True
        try:
            (tf_trans,tf_rot) = self.tf_listener.lookupTransform(transform_from, transform_to, rospy.Time(0))
        except (tf.LookupException, tf.ConnectivityException):
            tf_valid = False
        return (tf_trans, tf_rot, tf_valid)

    # Callback to store accelerometer and gripper information
    def gripperCallback(self, data):
        self.gripper_accelerometer = data

    # Callback to store controller state
    def controllerStateCallback(self,data):
        self.controller_state = data

    def controllerStateDetailCallback(self, data):
        self.controller_state_detail = data

    #Check if directory exits & create it
    def check_dir(self, f):
      if not os.path.exists(f):
        os.makedirs(f)
        return True
      return False

    # Setup the subscriber Node
    def startListener(self):
        # Initialize the subscriber node for BioTacs 
        rospy.Subscriber("biotac_pub", BioTacHand, self.biotacCallback,queue_size=1000)

        # Initialize subscriber node for accelerometer and gripper aperture
        rospy.Subscriber("pr2_gripper_accelerometer/data", PR2GripperAccelerometerData, self.gripperCallback, queue_size=1000)
        
        # Initialize subscriber node for controller state
        rospy.Subscriber("simple_gripper_controller_state", Int8, self.controllerStateCallback, queue_size=100)
        rospy.Subscriber("simple_gripper_controller_state_detailed", String, self.controllerStateDetailCallback, queue_size=100)

        rospy.spin()

    # Clean up by closing the file and adding the closing brackets
    def __del__(self):
      self.fout.write("]")
      self.fout.close()


if __name__ == '__main__':

    bt_listener = PR2BioTacLogger('left_arm')
    bt_listener.startListener()
