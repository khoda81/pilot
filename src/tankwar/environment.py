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
    observation_space: gym.spaces.Dict
    action_space: gym.spaces.Dict

    def __init__(
        self,
        client: client.GameClient | None = None,
        render_mode: str | None = None,
        ball_id: int | None = None,
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

        position = Dict(
            x=Box(-np.inf, np.inf, dtype=np.float32),
            y=Box(-np.inf, np.inf, dtype=np.float32),
        )

        image = Box(0, 255, shape=(200, 200, 3), dtype=np.uint8)

        self.observation_space = Dict(
            player_pov=image,
            player_position=position,
            player_rotation=Box(-np.inf, np.inf, shape=(), dtype=np.float32),
        )

        self.ball_id = ball_id
        if self.ball_id is not None:
            self.observation_space["ball_position"] = position

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

        self.player_id = self.client.get_tank()

        if self.player_id is None:
            raise TankwarEnvException("Failed to receive a tank to control, quitting!")

        # Subscribe to images and rewards for the spawned player
        if self.render_mode is not None:
            self.client.subscribe(self.player_id, client.ObservationKind.IMAGE)

        self.client.subscribe(self.player_id, client.ObservationKind.REWARDS)
        self.reward_index = 0

        observation = self._get_obs()
        info = self._get_info()

        if self.render_mode == "human":
            self.render()

        return observation, info

    def step(self, action: dict[str, np.ndarray | Any]):
        self.send_update_requests()

        tank_control = client.TankControlState(
            left_engine=float(action["left_engine"]),
            right_engine=float(action["right_engine"]),
        )

        turret_controls = client.TurretControlState(
            count=int(action["firing"]),
            rotation_speed=float(action["turret_rotation"]),
        )

        self.client.send_tank_controls(self.player_id, tank_control)

        player_state = self.client.storage.metadata(self.player_id)

        # Assuming player is a tank
        turrets: list[client.Turret] = player_state.get("turrets", [])

        for turret in turrets:
            self.client.send_turret_controls(turret["turret_id"], turret_controls)

        try:
            reward_updates = self.client.storage.get_dataset(self.player_id, "reward")
            new_rewards = reward_updates[self.reward_index :]["reward"]
            self.reward_index = len(reward_updates)
            reward = new_rewards.sum()

        except KeyError:
            reward = 0.0

        terminated = False
        truncated = False
        observation = self._get_obs()
        info = self._get_info()

        if self.render_mode == "human":
            self.render()

        return observation, reward, terminated, truncated, info

    def send_update_requests(self):
        if "ball_position" in self.observation_space.keys():
            self.client.request_update(self.ball_id, client.ObservationKind.POSITION)

        if "player_position" in self.observation_space.keys():
            self.client.request_update(self.player_id, client.ObservationKind.POSITION)

        if "player_rotation" in self.observation_space.keys():
            self.client.request_update(self.player_id, client.ObservationKind.ROTATION)

        if (
            "player_pov" in self.observation_space.keys()
            or self.render_mode is not None
        ):
            self.client.request_update(self.player_id, client.ObservationKind.IMAGE)

    def render(self):
        if self.render_mode == "rgb_array":
            return self._get_image_array()

        elif self.render_mode == "human":
            image = self._get_image_array()
            # TODO: Switch to pygame for rendering

            window_name = f"Player #{client.Entity(self.player_id)}"
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
        obs = {}

        if "player_pov" in self.observation_space.keys():
            obs["player_pov"] = self._get_image_array()

        obs.update(self._get_position("ball_position", self.ball_id))
        obs.update(self._get_position("player_position", self.player_id))

        if "player_rotation" in self.observation_space.keys():
            try:
                player_rotation = self.get_latest_value(
                    self.player_id, "rotation_in_radians"
                )

            except KeyError:
                player_rotation = np.zeros_like(
                    self.observation_space["player_rotation"].sample()
                )

            obs["player_rotation"] = player_rotation

        return obs

    def get_latest_value(self, entity: int, component: str):
        return self.client.storage.get_dataset(entity, component)[-1][component]

    def _get_position(self, obs_id, entity) -> dict[str, np.ndarray]:
        if obs_id not in self.observation_space.keys():
            return {}

        try:
            position = self.get_latest_value(entity, "position")
            position = {"x": position["x"], "y": position["y"]}

        except KeyError:
            space = self.observation_space[obs_id]
            position = {
                "x": np.asarray(0.0, dtype=space["x"].dtype),
                "y": np.asarray(0.0, dtype=space["y"].dtype),
            }

        return {obs_id: position}

    def _get_image_array(self) -> np.ndarray:
        try:
            return self.get_latest_value(self.player_id, "image")

        except KeyError:
            return self.no_signal_img
