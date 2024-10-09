import queue
import socket
import threading
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
import varint

from game_socket_pb2 import (
    ClientMessage,
    ControlUpdate,
    ObservationKind,
    ObservationRequest,
    PlayersListRequest,
    ServerMessage,
    SpawnPlayerRequest,
    SubscriptionRequest,
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


class NoPlayerAssignedException(Exception): ...


class GameClient:
    player_states: dict[int, dict[str, Any]]

    def __init__(self, address: tuple):
        self.address = address
        self.sock = None
        self.lock = threading.Lock()

        # Player-related state tracking
        # player_id -> {'image': ..., 'reward': ..., 'sensors': ...}
        self.player_states = {}
        self.assigned_players = set()  # Set of player IDs assigned to this client

        # List of player IDs not currently controlled
        self.unused_players = queue.Queue()

        # Asynchronous message handling
        self.running = False
        self.receive_thread = None
        self.message_queue = queue.Queue()

    def player_state(self, player_id) -> dict[str, Any]:
        return self.player_states.setdefault(player_id, {})

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(self.address)
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

        class SocketWrapper:
            """Wrap a socket to provide a read() method compatible with varint.decode_stream()."""

            def __init__(self, sock):
                self.sock = sock

            def read(self, num_bytes):
                """Read a specific number of bytes from the socket."""
                return self.sock.recv(num_bytes)

        length = varint.decode_stream(SocketWrapper(self.sock))
        message_data = self.sock.recv(length)

        if not message_data:
            return None

        server_message = ServerMessage()
        server_message.ParseFromString(message_data)
        return server_message

    def process_server_message(self, message: ServerMessage):
        message_type = message.WhichOneof("message")

        if message_type == "player_spawned":
            self.handle_player_spawned(message.player_spawned)

        elif message_type == "player_died":
            self.handle_player_died(message.player_died)

        elif message_type == "player_assigned":
            self.handle_player_assigned(message.player_assigned)

        elif message_type == "player_list":
            self.handle_player_list(message.player_list)

        elif message_type == "observation_update":
            self.handle_observation_update(message.observation_update)

        else:
            pass  # TODO:

    def handle_player_spawned(self, player_spawned):
        player_id = player_spawned.player_id
        self.player_state(player_id)["alive"] = True

    def handle_player_died(self, player_died):
        player_id = player_died
        player_state = self.player_state(player_id)
        player_state["alive"] = False
        player_state["assigned"] = False

    def handle_player_assigned(self, player_assigned):
        player_id = player_assigned
        self.unused_players.put(player_id)
        self.player_state(player_id)["assigned"] = True

    def handle_player_list(self, player_list):
        for player in player_list.players:
            player_id = player.player_id
        self.assigned_players.add(player_id)

    def handle_observation_update(self, observation):
        observation_kind = observation.WhichOneof("observation")
        player_id: int = observation.player_id

        player_state = self.player_state(player_id)

        if observation_kind == "image":
            player_state["image"] = decode_image(observation.image)

        elif observation_kind == "reward":
            player_state["reward"] = (
                player_state.get("reward", 0.0) + observation.reward.reward
            )

        elif observation_kind == "sensors":
            player_state["sensors"] = observation.sensors

    # ---- Control Methods ----

    def get_player(self, timeout=1.0) -> Optional[int]:
        try:
            return self.unused_players.get(block=False)

        except queue.Empty:
            pass

        observation_request = ClientMessage(spawn_player_request=SpawnPlayerRequest())
        self.send_message(observation_request)

        try:
            return self.unused_players.get(timeout=timeout)
        except queue.Empty:
            pass

    def send_controls(
        self,
        player_id: int,
        controls,
    ):
        control_update = ClientMessage(
            control_update=ControlUpdate(
                player_id=player_id,
                controls=controls,
            )
        )

        self.send_message(control_update)

    def request_observation(self, player_id: int, observation_kind: ObservationKind):
        observation_request = ClientMessage(
            observation_request=ObservationRequest(
                player_id=player_id, observation_kind=observation_kind
            )
        )

        self.send_message(observation_request)

    def request_player_list(self):
        observation_request = ClientMessage(players_list_request=PlayersListRequest())

        self.send_message(observation_request)

    def subscribe_to_observation(
        self,
        player_id: int,
        observation_kind: ObservationKind,
        cooldown: Optional[float] = None,
    ):
        subscription_request = ClientMessage(
            subscription_request=SubscriptionRequest(
                player_id=player_id,
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
        print("Connection closed!")

    except ConnectionResetError:
        print("Connection closed by the server!")

    finally:
        client.running = False
