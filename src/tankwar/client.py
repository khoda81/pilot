import queue
import socket
import threading
from typing import Any, Mapping
from warnings import warn

import cv2
import numpy as np
from attr import dataclass

from .protobuf.game_socket_pb2 import *
from .session_storage import SessionStorage


def decode_image(image_message):
    image_type = image_message.WhichOneof("image_type")

    if image_type == "raw_image":
        raw_image = image_message.raw_image
        width, height = raw_image.width, raw_image.height
        image_data = np.frombuffer(raw_image.data, dtype=np.uint8)
        image = image_data.reshape((height, width, 4))  # RGBA
        return cv2.cvtColor(image, cv2.COLOR_RGBA2BGRA)  # Convert to BGR

    elif image_type == "png_image":
        png_data = np.frombuffer(image_message.png_image.data, dtype=np.uint8)
        return cv2.imdecode(png_data, cv2.IMREAD_COLOR)

    else:
        raise NotImplementedError(
            f"Handling images of {image_type} is not supported yet"
        )


@dataclass
class Entity:
    entity: int

    def index(self) -> int:
        return self.entity & ((1 << 32) - 1)

    def generation(self) -> int:
        return self.entity >> 32

    def __str__(self):
        return f"{self.index()}v{self.generation()}"


class NoTankAssignedException(Exception): ...


class GameClient:
    entity_states: dict[int, dict[str, Any]]

    def __init__(self, address=("localhost", 7878)):
        self.address = address
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.lock = threading.Lock()

        # Tank-related state tracking
        # tank_id -> {'image': ..., 'reward': ..., 'sensors': ...}
        self.storage = SessionStorage(mode="a")
        self.tank_turrets = {}
        self.balls = {}
        self.alive_tanks = set()
        self.dead_tanks = set()
        self.assigned_tanks = set()  # Set of tank IDs assigned to this client

        # List of tank IDs not currently controlled
        self.unused_tanks = queue.Queue()

        # Asynchronous message handling
        self.running = False
        self.receive_thread = None
        self.message_queue = queue.Queue()

    def connect(self):
        self.storage.open()
        self.sock.connect(self.address)
        self.request_tank_list()
        self.request_ball_list()

        self.running = True
        self.receive_thread = threading.Thread(
            target=read_server_messages,
            args=(self,),
            daemon=True,
        )
        self.receive_thread.start()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self.running = False
        self.sock.close()
        self.storage.__exit__()

    def send_message(self, client_message: ClientMessage) -> None:
        serialized_message = client_message.SerializeToString()
        varint_buf = []

        number = len(serialized_message)
        while number >> 7:
            varint_buf.append(number & 0x7F | 0x80)
            number >>= 7

        varint_buf.append(number)

        self.sock.sendall(bytes(varint_buf))
        self.sock.sendall(serialized_message)

    def receive_message(self) -> ServerMessage | None:
        shift = 0
        length = 0
        while True:
            inp = self.sock.recv(1)
            if not inp:
                raise ConnectionAbortedError

            [i] = inp
            length |= (i & 0x7F) << shift
            shift += 7
            if not (i & 0x80):
                break

        message_data = self.sock.recv(length)

        if not message_data:
            return None

        return ServerMessage.FromString(message_data)

    def process_server_message(self, message: ServerMessage):
        if message.HasField("tank_spawned"):
            self.handle_tank_spawned(message.tank_spawned)

        elif message.HasField("tank_died"):
            self.handle_tank_died(message.tank_died)

        elif message.HasField("tank_assigned"):
            self.handle_tank_assigned(message.tank_assigned)

        elif message.HasField("tank_list"):
            self.handle_tank_list(message.tank_list)

        elif message.HasField("ball_list"):
            self.handle_ball_list(message.ball_list)

        elif message.HasField("observation_update"):
            self.handle_observation_update(message.observation_update)

        else:
            print(f"Unhandled message from server: {message}")

    def handle_tank_spawned(self, tank: Tank):
        self.alive_tanks.add(tank.tank_id)

        dtype = [("turret_id", np.uint64)]
        turrets = np.asarray([turret.turret_id for turret in tank.turrets], dtype=dtype)
        self.storage.entity_data(tank.tank_id)["turrets"] = turrets

    def handle_tank_died(self, tank_id: int):
        self.dead_tanks.add(tank_id)
        self.alive_tanks.discard(tank_id)
        self.assigned_tanks.discard(tank_id)

    def handle_tank_assigned(self, tank_id):
        self.unused_tanks.put(tank_id)
        self.assigned_tanks.add(tank_id)

    def handle_tank_list(self, tank_list: TankList):
        for tank in tank_list.tanks:
            if tank.tank_id not in self.dead_tanks:
                self.handle_tank_spawned(tank)

    def handle_ball_list(self, ball_list: BallList):
        self.balls = {ball.ball_id: ball for ball in ball_list.balls}

    def handle_observation_update(self, update: ObservationUpdate):
        data_kind = update.WhichOneof("observation")

        if data_kind == "image":
            array = decode_image(update.image)

        elif data_kind == "reward":
            array = np.asarray(update.reward.reward, dtype=np.float64)

        elif data_kind == "position":
            array = np.asarray(
                (update.position.x, update.position.y),
                dtype=np.dtype([("x", np.float32), ("y", np.float32)]),
            )

        elif data_kind == "tank_controls":
            array = np.asarray(
                (update.tank_controls.right_engine, update.tank_controls.left_engine),
                dtype=np.dtype(
                    [("right_engine", np.float32), ("left_engine", np.float32)]
                ),
            )

        elif data_kind == "turret_controls":
            array = np.asarray(
                (update.turret_controls.rotation_speed, update.turret_controls.count),
                dtype=np.dtype([("rotation_speed", np.float32), ("count", np.int32)]),
            )

        elif data_kind == "rotation_in_radians":
            array = np.asarray(update.rotation_in_radians, dtype=np.float32)

        else:
            warn(f"Unexpected observation kind: {data_kind}")
            array = np.asarray(getattr(update, data_kind))

        self.storage.add_row(update.entity, data_kind, array, update.timestamp)

    # ---- Control Methods ----

    def get_tank(self, timeout=1.0) -> int | None:
        try:
            return self.unused_tanks.get(block=False)

        except queue.Empty:
            pass

        self.send_message(ClientMessage(spawn_tank_request=SpawnTankRequest()))

        try:
            return self.unused_tanks.get(timeout=timeout)
        except queue.Empty:
            pass

    def send_tank_controls(
        self,
        tank_id: int,
        controls: TankControlState | Mapping | None,
    ):
        self.send_message(
            ClientMessage(
                tank_control_update=TankControlUpdate(
                    tank_id=tank_id,
                    controls=controls,
                )
            )
        )

    def send_turret_controls(self, turret_id: int, controls: TurretControlState):
        self.send_message(
            ClientMessage(
                turret_control_update=TurretControlUpdate(
                    turret_id=turret_id,
                    controls=controls,
                )
            )
        )

    def request_update(self, entity: int, observation_kind: ObservationKind):
        self.send_message(
            ClientMessage(
                observation_request=ObservationRequest(
                    entity=entity, observation_kind=observation_kind
                )
            )
        )

    def request_tank_list(self):
        self.send_message(ClientMessage(tanks_list_request=TanksListRequest()))

    def request_ball_list(self):
        self.send_message(ClientMessage(ball_list_request=BallsListRequest()))

    def subscribe(
        self,
        entity: int,
        observation_kind: ObservationKind,
        cooldown: float | None = 0.0,
    ):
        self.send_message(
            ClientMessage(
                subscription_request=SubscriptionRequest(
                    entity=entity,
                    observation_kind=observation_kind,
                    cooldown=cooldown,
                )
            )
        )


def read_server_messages(client: GameClient):
    try:
        while client.running:
            message = client.receive_message()
            if message:
                client.process_server_message(message)

    except ConnectionAbortedError:
        pass

    except ConnectionResetError:
        pass

    finally:
        client.running = False
