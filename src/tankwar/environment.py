import importlib.resources
from typing import Any

import cv2
import gymnasium as gym
import numpy as np

from tankwar import client


class TankwarEnvException(Exception):
    """Custom exception for errors in the Tankwars environment."""

    def __init__(self, message: str, player_id: int | None = None):
        self.message = message
        self.player_id = player_id

        super().__init__(self.message)

    def __str__(self):
        return (
            self.message
            if self.player_id is None
            else f"{self.message} (Player ID: {client.Entity(self.player_id)})"
        )


class TankwarEnv(gym.Env):
    metadata = {"render_modes": ["human", "rgb_array"]}

    def __init__(
        self,
        client: client.GameClient | None = None,
        render_mode: str | None = None,
    ):
        super().__init__()

        if client is None:
            raise ValueError(
                "No client was provided for the env, connect a client and pass it to the env spec:"
                "with GameClient((host, port)) as client:"
                "   gym.make(..., client=client)"
            )

        self.client = client
        self.render_mode = render_mode

        from gymnasium.spaces import Box, Dict

        self.observation_space = Box(0, 255, shape=(200, 200, 3), dtype=np.uint8)
        self.action_space = Dict(
            right_engine=Box(-1, 1, shape=(), dtype=np.float32),
            left_engine=Box(-1, 1, shape=(), dtype=np.float32),
            turret_rotation=Box(-1, 1, shape=(), dtype=np.float32),
            firing=Box(np.array(False), np.array(True), shape=(), dtype=bool),
        )

        img_path = importlib.resources.files("tankwar.assets").joinpath("no_signal.jpg")
        with img_path.open("rb") as f:
            img_bytes = f.read()
            img_array = np.frombuffer(img_bytes, np.uint8)
            self.no_signal_img = cv2.resize(
                cv2.imdecode(img_array, cv2.IMREAD_COLOR), (200, 200)
            )

    def _get_info(self):
        return {}

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        # TODO: Send a player kill request for the current tank (if any)

        self.agent_id = self.client.get_tank()

        if self.agent_id is None:
            raise TankwarEnvException("Failed to receive a tank to control, quitting!")

        # Subscribe to images and rewards for the spawned player
        if self.render_mode is not None:
            self.client.subscribe_to_observation(
                self.agent_id, client.ObservationKind.IMAGE
            )

        self.client.subscribe_to_observation(
            self.agent_id, client.ObservationKind.REWARDS
        )

        observation = self._get_obs()
        info = self._get_info()

        if self.render_mode == "human":
            self.render()

        return observation, info

    def step(self, action: dict[str, np.ndarray | Any]):
        tank_control = client.TankControlState(
            left_engine=float(action["left_engine"]),
            right_engine=float(action["right_engine"]),
        )

        turret_controls = client.TurretControlState(
            count=int(action["firing"]),
            rotation_speed=float(action["turret_rotation"]),
        )

        self.client.send_tank_controls(self.agent_id, tank_control)

        if self.render_mode is not None:
            self.client.request_observation(self.agent_id, client.ObservationKind.IMAGE)

        agent_state = self.client.entity_state(self.agent_id)
        turrets: list[client.Turret] = agent_state.get("turrets", [])

        for turret in turrets:
            self.client.send_turret_controls(turret.turret_id, turret_controls)

        terminated = False
        truncated = False
        reward = self.client.entity_state(self.agent_id).pop("reward", 0.0)
        observation = self._get_obs()
        info = self._get_info()

        if self.render_mode == "human":
            self.render()

        return observation, reward, terminated, truncated, info

    def render(self):
        if self.render_mode == "rgb_array":
            return self._get_image_array()

        elif self.render_mode == "human":
            image = self._get_image_array()
            # TODO: Switch to pygame for rendering

            window_name = f"Player #{client.Entity(self.agent_id)}"
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

            width, height, *_ = image.shape
            scale = max(600 // width, 1)

            resized_image = cv2.resize(
                image,
                (width * scale, height * scale),
                interpolation=cv2.INTER_NEAREST,
            )

            cv2.imshow(window_name, resized_image)
            cv2.waitKey(1)

    def close(self):
        # TODO: Send a player kill request for tank
        # TODO: Close the opencv window
        cv2.destroyAllWindows()
        return super().close()

    def _get_obs(self):
        return self._get_image_array()

    def _get_image_array(self) -> np.ndarray:
        return self.client.entity_state(self.agent_id).get("image", self.no_signal_img)
