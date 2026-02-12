from dai_lerobot.robot import Robot, RobotConfig
from pathlib import Path

def calibrate(robot: Robot):
    robot.calibrate()

if __name__ == "__main__":
    config = RobotConfig(
        id="dai_right_robot",
        port='/dev/ttyUSB0',
        calibration_dir=Path("calibration_cache"),
    )
    
    robot = Robot(config=config)
    robot.connect(calibrate=False) 
    calibrate(robot)
    robot.disconnect()