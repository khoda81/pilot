from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ObservationKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    NONE: _ClassVar[ObservationKind]
    IMAGE: _ClassVar[ObservationKind]
    SENSOR: _ClassVar[ObservationKind]
    TANK_CONTROLS: _ClassVar[ObservationKind]
    REWARDS: _ClassVar[ObservationKind]
    TURRET_CONTROLS: _ClassVar[ObservationKind]
    POSITION: _ClassVar[ObservationKind]
    ROTATION: _ClassVar[ObservationKind]
NONE: ObservationKind
IMAGE: ObservationKind
SENSOR: ObservationKind
TANK_CONTROLS: ObservationKind
REWARDS: ObservationKind
TURRET_CONTROLS: ObservationKind
POSITION: ObservationKind
ROTATION: ObservationKind

class ClientMessage(_message.Message):
    __slots__ = ("tank_control_update", "subscription_request", "spawn_tank_request", "tanks_list_request", "observation_request", "kill_tank_request", "turret_control_update")
    TANK_CONTROL_UPDATE_FIELD_NUMBER: _ClassVar[int]
    SUBSCRIPTION_REQUEST_FIELD_NUMBER: _ClassVar[int]
    SPAWN_TANK_REQUEST_FIELD_NUMBER: _ClassVar[int]
    TANKS_LIST_REQUEST_FIELD_NUMBER: _ClassVar[int]
    OBSERVATION_REQUEST_FIELD_NUMBER: _ClassVar[int]
    KILL_TANK_REQUEST_FIELD_NUMBER: _ClassVar[int]
    TURRET_CONTROL_UPDATE_FIELD_NUMBER: _ClassVar[int]
    tank_control_update: TankControlUpdate
    subscription_request: SubscriptionRequest
    spawn_tank_request: SpawnTankRequest
    tanks_list_request: TanksListRequest
    observation_request: ObservationRequest
    kill_tank_request: KillTankRequest
    turret_control_update: TurretControlUpdate
    def __init__(self, tank_control_update: _Optional[_Union[TankControlUpdate, _Mapping]] = ..., subscription_request: _Optional[_Union[SubscriptionRequest, _Mapping]] = ..., spawn_tank_request: _Optional[_Union[SpawnTankRequest, _Mapping]] = ..., tanks_list_request: _Optional[_Union[TanksListRequest, _Mapping]] = ..., observation_request: _Optional[_Union[ObservationRequest, _Mapping]] = ..., kill_tank_request: _Optional[_Union[KillTankRequest, _Mapping]] = ..., turret_control_update: _Optional[_Union[TurretControlUpdate, _Mapping]] = ...) -> None: ...

class SpawnTankRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class KillTankRequest(_message.Message):
    __slots__ = ("tank_id",)
    TANK_ID_FIELD_NUMBER: _ClassVar[int]
    tank_id: int
    def __init__(self, tank_id: _Optional[int] = ...) -> None: ...

class TanksListRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class TankControlUpdate(_message.Message):
    __slots__ = ("tank_id", "controls")
    TANK_ID_FIELD_NUMBER: _ClassVar[int]
    CONTROLS_FIELD_NUMBER: _ClassVar[int]
    tank_id: int
    controls: TankControlState
    def __init__(self, tank_id: _Optional[int] = ..., controls: _Optional[_Union[TankControlState, _Mapping]] = ...) -> None: ...

class TankControlState(_message.Message):
    __slots__ = ("right_engine", "left_engine")
    RIGHT_ENGINE_FIELD_NUMBER: _ClassVar[int]
    LEFT_ENGINE_FIELD_NUMBER: _ClassVar[int]
    right_engine: float
    left_engine: float
    def __init__(self, right_engine: _Optional[float] = ..., left_engine: _Optional[float] = ...) -> None: ...

class TurretControlUpdate(_message.Message):
    __slots__ = ("turret_id", "controls")
    TURRET_ID_FIELD_NUMBER: _ClassVar[int]
    CONTROLS_FIELD_NUMBER: _ClassVar[int]
    turret_id: int
    controls: TurretControlState
    def __init__(self, turret_id: _Optional[int] = ..., controls: _Optional[_Union[TurretControlState, _Mapping]] = ...) -> None: ...

class TurretControlState(_message.Message):
    __slots__ = ("rotation_speed", "count")
    ROTATION_SPEED_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    rotation_speed: float
    count: int
    def __init__(self, rotation_speed: _Optional[float] = ..., count: _Optional[int] = ...) -> None: ...

class SubscriptionRequest(_message.Message):
    __slots__ = ("entity", "observation_kind", "cooldown")
    ENTITY_FIELD_NUMBER: _ClassVar[int]
    OBSERVATION_KIND_FIELD_NUMBER: _ClassVar[int]
    COOLDOWN_FIELD_NUMBER: _ClassVar[int]
    entity: int
    observation_kind: ObservationKind
    cooldown: float
    def __init__(self, entity: _Optional[int] = ..., observation_kind: _Optional[_Union[ObservationKind, str]] = ..., cooldown: _Optional[float] = ...) -> None: ...

class ObservationRequest(_message.Message):
    __slots__ = ("entity", "observation_kind")
    ENTITY_FIELD_NUMBER: _ClassVar[int]
    OBSERVATION_KIND_FIELD_NUMBER: _ClassVar[int]
    entity: int
    observation_kind: ObservationKind
    def __init__(self, entity: _Optional[int] = ..., observation_kind: _Optional[_Union[ObservationKind, str]] = ...) -> None: ...

class ServerMessage(_message.Message):
    __slots__ = ("observation_update", "tank_spawned", "tank_died", "tank_list", "tank_assigned")
    OBSERVATION_UPDATE_FIELD_NUMBER: _ClassVar[int]
    TANK_SPAWNED_FIELD_NUMBER: _ClassVar[int]
    TANK_DIED_FIELD_NUMBER: _ClassVar[int]
    TANK_LIST_FIELD_NUMBER: _ClassVar[int]
    TANK_ASSIGNED_FIELD_NUMBER: _ClassVar[int]
    observation_update: ObservationUpdate
    tank_spawned: Tank
    tank_died: int
    tank_list: TankList
    tank_assigned: int
    def __init__(self, observation_update: _Optional[_Union[ObservationUpdate, _Mapping]] = ..., tank_spawned: _Optional[_Union[Tank, _Mapping]] = ..., tank_died: _Optional[int] = ..., tank_list: _Optional[_Union[TankList, _Mapping]] = ..., tank_assigned: _Optional[int] = ...) -> None: ...

class ObservationUpdate(_message.Message):
    __slots__ = ("entity", "timestamp", "image", "sensors", "tank_controls", "reward", "turret_controls", "position", "rotation_in_radians")
    ENTITY_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    IMAGE_FIELD_NUMBER: _ClassVar[int]
    SENSORS_FIELD_NUMBER: _ClassVar[int]
    TANK_CONTROLS_FIELD_NUMBER: _ClassVar[int]
    REWARD_FIELD_NUMBER: _ClassVar[int]
    TURRET_CONTROLS_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    ROTATION_IN_RADIANS_FIELD_NUMBER: _ClassVar[int]
    entity: int
    timestamp: int
    image: Image
    sensors: Sensors
    tank_controls: TankControlState
    reward: Reward
    turret_controls: TurretControlState
    position: Position
    rotation_in_radians: float
    def __init__(self, entity: _Optional[int] = ..., timestamp: _Optional[int] = ..., image: _Optional[_Union[Image, _Mapping]] = ..., sensors: _Optional[_Union[Sensors, _Mapping]] = ..., tank_controls: _Optional[_Union[TankControlState, _Mapping]] = ..., reward: _Optional[_Union[Reward, _Mapping]] = ..., turret_controls: _Optional[_Union[TurretControlState, _Mapping]] = ..., position: _Optional[_Union[Position, _Mapping]] = ..., rotation_in_radians: _Optional[float] = ...) -> None: ...

class Image(_message.Message):
    __slots__ = ("raw_image", "png_image")
    RAW_IMAGE_FIELD_NUMBER: _ClassVar[int]
    PNG_IMAGE_FIELD_NUMBER: _ClassVar[int]
    raw_image: RawRgbaImage
    png_image: PngImage
    def __init__(self, raw_image: _Optional[_Union[RawRgbaImage, _Mapping]] = ..., png_image: _Optional[_Union[PngImage, _Mapping]] = ...) -> None: ...

class RawRgbaImage(_message.Message):
    __slots__ = ("width", "height", "data")
    WIDTH_FIELD_NUMBER: _ClassVar[int]
    HEIGHT_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    width: int
    height: int
    data: bytes
    def __init__(self, width: _Optional[int] = ..., height: _Optional[int] = ..., data: _Optional[bytes] = ...) -> None: ...

class PngImage(_message.Message):
    __slots__ = ("data",)
    DATA_FIELD_NUMBER: _ClassVar[int]
    data: bytes
    def __init__(self, data: _Optional[bytes] = ...) -> None: ...

class Sensors(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class Reward(_message.Message):
    __slots__ = ("reward", "reason")
    REWARD_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    reward: float
    reason: str
    def __init__(self, reward: _Optional[float] = ..., reason: _Optional[str] = ...) -> None: ...

class Position(_message.Message):
    __slots__ = ("x", "y")
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    x: float
    y: float
    def __init__(self, x: _Optional[float] = ..., y: _Optional[float] = ...) -> None: ...

class TankList(_message.Message):
    __slots__ = ("tanks",)
    TANKS_FIELD_NUMBER: _ClassVar[int]
    tanks: _containers.RepeatedCompositeFieldContainer[Tank]
    def __init__(self, tanks: _Optional[_Iterable[_Union[Tank, _Mapping]]] = ...) -> None: ...

class Tank(_message.Message):
    __slots__ = ("tank_id", "turrets")
    TANK_ID_FIELD_NUMBER: _ClassVar[int]
    TURRETS_FIELD_NUMBER: _ClassVar[int]
    tank_id: int
    turrets: _containers.RepeatedCompositeFieldContainer[Turret]
    def __init__(self, tank_id: _Optional[int] = ..., turrets: _Optional[_Iterable[_Union[Turret, _Mapping]]] = ...) -> None: ...

class Turret(_message.Message):
    __slots__ = ("turret_id",)
    TURRET_ID_FIELD_NUMBER: _ClassVar[int]
    turret_id: int
    def __init__(self, turret_id: _Optional[int] = ...) -> None: ...
