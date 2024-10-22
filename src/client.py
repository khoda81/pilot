import queue
import socket
import threading
from typing import Any, Optional
from warnings import warn

import cv2
import numpy as np
import varint
from attr import dataclass

from .protobuf.game_socket_pb2 import (
    ClientMessage,
    ObservationKind,
    ObservationRequest,
    ServerMessage,
    SpawnTankRequest,
    SubscriptionRequest,
    TankControlUpdate,
    TanksListRequest,
    TurretControlUpdate,
)


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

    def __init__(self, address: tuple):
        self.address = address
        self.sock = None
        self.lock = threading.Lock()

        # Tank-related state tracking
        # tank_id -> {'image': ..., 'reward': ..., 'sensors': ...}
        self.entity_states = {}
        self.alive_tanks = set()
        self.dead_tanks = set()
        self.assigned_tanks = set()  # Set of tank IDs assigned to this client

        # List of tank IDs not currently controlled
        self.unused_tanks = queue.Queue()

        # Asynchronous message handling
        self.running = False
        self.receive_thread = None
        self.message_queue = queue.Queue()

    def entity_state(self, tank_id) -> dict[str, Any]:
        return self.entity_states.setdefault(tank_id, {})

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(self.address)
        self.request_tank_list()

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
        if self.sock:
            self.sock.close()

    def send_message(self, client_message: ClientMessage) -> None:
        serialized_message = client_message.SerializeToString()
        length_prefix = varint.encode(len(serialized_message))
        self.sock.sendall(length_prefix)
        self.sock.sendall(serialized_message)

    def receive_message(self) -> Optional[ServerMessage]:
        # length = varint.decode_stream(self.sock.makefile("rb"))

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

        server_message = ServerMessage()
        server_message.ParseFromString(message_data)
        return server_message

    def process_server_message(self, message: ServerMessage):
        message_type = message.WhichOneof("message")

        if message_type == "tank_spawned":
            self.handle_tank_spawned(message.tank_spawned)

        elif message_type == "tank_died":
            self.handle_tank_died(message.tank_died)

        elif message_type == "tank_assigned":
            self.handle_tank_assigned(message.tank_assigned)

        elif message_type == "tank_list":
            self.handle_tank_list(message.tank_list)

        elif message_type == "observation_update":
            self.handle_observation_update(message.observation_update)

        else:
            print(f"Unhandled message from server: {message_type}")

    def handle_tank_spawned(self, tank):
        self.alive_tanks.add(tank.tank_id)
        self.entity_state(tank.tank_id)["turrets"] = tank.turrets

    def handle_tank_died(self, tank_id):
        self.dead_tanks.add(tank_id)
        self.alive_tanks.discard(tank_id)
        self.assigned_tanks.discard(tank_id)

    def handle_tank_assigned(self, tank_id):
        self.unused_tanks.put(tank_id)
        self.assigned_tanks.add(tank_id)

    def handle_tank_list(self, tank_list):
        for tank in tank_list.tanks:
            if tank.tank_id not in self.dead_tanks:
                self.handle_tank_spawned(tank)

    def handle_observation_update(self, observation):
        data_kind = observation.WhichOneof("observation")
        entity: int = observation.entity

        if data_kind == "image":
            self.entity_state(entity)[data_kind] = decode_image(observation.image)

        elif data_kind == "reward":
            entity_state = self.entity_state(entity)
            entity_state[data_kind] = (
                entity_state.get(data_kind, 0.0) + observation.reward.reward
            )

        else:
            if data_kind not in [
                "tank_controls",
                "turret_controls",
                "position",
                "rotation_in_radians",
            ]:
                warn(f"Unexpected observation kind: {data_kind}")

            self.entity_state(entity)[data_kind] = getattr(observation, data_kind)

    # ---- Control Methods ----

    def get_tank(self, timeout=1.0) -> Optional[int]:
        try:
            return self.unused_tanks.get(block=False)

        except queue.Empty:
            pass

        observation_request = ClientMessage(spawn_tank_request=SpawnTankRequest())
        self.send_message(observation_request)

        try:
            return self.unused_tanks.get(timeout=timeout)
        except queue.Empty:
            pass

    def send_tank_controls(self, tank_id: int, controls):
        self.send_message(
            ClientMessage(
                tank_control_update=TankControlUpdate(
                    tank_id=tank_id,
                    controls=controls,
                )
            )
        )

    def send_turret_controls(self, turret_id: int, controls):
        self.send_message(
            ClientMessage(
                turret_control_update=TurretControlUpdate(
                    turret_id=turret_id,
                    controls=controls,
                )
            )
        )

    def request_observation(self, entity: int, observation_kind: ObservationKind):
        observation_request = ClientMessage(
            observation_request=ObservationRequest(
                entity=entity, observation_kind=observation_kind
            )
        )

        self.send_message(observation_request)

    def request_tank_list(self):
        observation_request = ClientMessage(tanks_list_request=TanksListRequest())

        self.send_message(observation_request)

    def subscribe_to_observation(
        self,
        entity: int,
        observation_kind: ObservationKind,
        cooldown: Optional[float] = None,
    ):
        subscription_request = ClientMessage(
            subscription_request=SubscriptionRequest(
                entity=entity,
                observation_kind=observation_kind,
                cooldown=cooldown,
            )
        )

        self.send_message(subscription_request)


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
