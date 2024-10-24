from typing import Optional

import cv2
import gymnasium as gym
import numpy as np

import client


class TankwarsEnvException(Exception):
    """Custom exception for errors in the Tankwars environment."""

    def __init__(self, message: str, player_id: Optional[int] = None):
        self.message = message
        self.player_id = player_id
        super().__init__(self.message)

    def __str__(self):
        if self.player_id is not None:
            return f"{self.message} (Player ID: {client.Entity(self.player_id)})"
        return self.message


class TankwarsEnv(gym.Env):
    render_mode = "human"
    metadata = {"render_modes": ["human", "rgb_array"]}

    def __init__(self, client: client.GameClient, render_mode: Optional[str] = None):
        super().__init__()

        self.client = client

        from gymnasium.spaces import Box, Dict

        self.observation_space = Box(0, 255, shape=(200, 200, 3), dtype=np.uint8)
        self.action_space = Dict(
            right_engine=Box(-1, 1, shape=(1,), dtype=np.float32),
            left_engine=Box(-1, 1, shape=(1,), dtype=np.float32),
            fire=Box(np.array(False), np.array(True), shape=(), dtype=bool),
        )

        self.no_signal_img = cv2.resize(cv2.imread("./no_img.jpg"), (200, 200))
        self.render_mode = render_mode

    def _get_info(self):
        return {}

    def reset(self, *, seed: Optional[int] = None, options: Optional[dict] = None):
        super().reset(seed=seed)

        self.agent_id = self.client.get_tank()

        # If the clients fails to acquire a tank, it returns None
        if self.agent_id is None:
            raise TankwarsEnvException(
                "Failed to receive a player to control, quitting!"
            )

        # Subscribe to images and rewards for the spawned player
        self.client.subscribe_to_observation(
            self.agent_id,
            client.ObservationKind.IMAGE,
            cooldown=0.1,
        )
        self.client.subscribe_to_observation(
            self.agent_id,
            client.ObservationKind.REWARDS,
            cooldown=0.1,
        )

        observation = self._get_obs()
        info = self._get_info()

        if self.render_mode == "human":
            self.render()

        return observation, info

    def step(self, action):
        self.client.send_tank_controls(self.agent_id, action)
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
            image = self._get_obs()
            # TODO: Switch to pygame for rendering
            cv2.imshow(f"Player #{client.Entity(self.agent_id)}", image)
            cv2.waitKey(1)

    def close(self):
        # TODO: Send a player kill request for tank
        # TODO: Close the opencv window

        return super().close()

    def _get_obs(self):
        return self._get_image_array()

    def _get_image_array(self):
        return self.client.entity_state(self.agent_id).get("image", self.no_signal_img)


gym.register(
    id="gymnasium_env/Tankwars-v0",
    entry_point=TankwarsEnv,
    nondeterministic=True,
)
