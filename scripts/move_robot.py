from dai_lerobot.robot import Robot, RobotConfig
from pathlib import Path
import time

def move(robot: Robot):
    obs = robot.get_observation()
    print(obs)
    
    # 将所有值设置为0
    zero_action = {k: 0 for k in obs.keys()}
    zero_action["gripper.pos"] = 50
    print(f"发送动作: {zero_action}")
    
    robot.send_action(zero_action)
    time.sleep(5)


if __name__ == "__main__":
    config = RobotConfig(
        id="dai_right_robot",
        port='/dev/ttyUSB0',
        calibration_dir=Path("calibration_cache"),
    )
    
    robot = Robot(config=config)
    robot.connect(calibrate=True) 
    move( robot )
    robot.disconnect()