from typing import Any, TypeAlias

# PolicyAction: TypeAlias = torch.Tensor
RobotAction: TypeAlias = dict[str, Any]  # noqa: UP040
# EnvAction: TypeAlias = np.ndarray
RobotObservation: TypeAlias = dict[str, Any]  # noqa: UP040
