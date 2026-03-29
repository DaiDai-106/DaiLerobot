import abc
from dataclasses import dataclass
from pathlib import Path
from enum import Enum
import draccus

class TeleopEvents(Enum):
    """Shared constants for teleoperator events across teleoperators."""

    SUCCESS = "success"
    FAILURE = "failure"
    RERECORD_EPISODE = "rerecord_episode"
    IS_INTERVENTION = "is_intervention"
    TERMINATE_EPISODE = "terminate_episode"

@dataclass(kw_only=True)
class TeleoperatorConfig(draccus.ChoiceRegistry, abc.ABC):
    id: str | None = None  # Allows to distinguish between different teleoperators of the same type
    calibration_dir: Path | None = None  # 为未来做准备，如果是主从臂摇操的话，这里可以加载摇的标定数据， TODO 目前暂时是不需要的

    @property
    def type(self) -> str:
        return self.get_choice_name(self.__class__)