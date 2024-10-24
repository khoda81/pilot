from typing import Optional

import cv2
import gymnasium as gym
import numpy as np
from gymnasium.spaces import Box, Dict, OneOf

import client


class TankwarsEnv(gym.Env):

    def __init__(self, client: client.GameClient):
        self.client = client
        self.observation_space = Box(0, 255, shape=(200, 200, 3), dtype=np.uint8)
        self.action_space = Dict({
            "right_engine": Box(-1, 1, shape=(1,), dtype=np.float32),
            "left_engine": Box(-1, 1, shape=(1,), dtype=np.float32),
            "fire": Box(np.array(False), np.array(True), shape=(), dtype=bool),
        })
        self.no_signal_img = cv2.resize(cv2.imread('./no_img.jpg'), (200, 200))

    def get_info(self):
        return {}

    def reset(self, seed=None):
        super().reset(seed=seed)

        player_id = self.client.get_player()

        if player_id is None:
            # TODO: Custom exception class for 
            raise Exception("Failed to receive a player to control, quitting!")

        # 2. Subscribe to images and rewards for the spawned player
        self.client.subscribe_to_observation(player_id, client.ObservationKind.IMAGE, cooldown=0.1)
        self.client.subscribe_to_observation(player_id, client.ObservationKind.REWARDS, cooldown=0.1)

        return player_id

    def step(self, player_id, controls):
        self.client.send_controls(player_id, controls)
        player_state = self.get_state(player_id)
        reward = player_state.pop("reward", 0.0)
        terminated = False
        truncated = False
        info = self.get_info()

        return player_state, reward, terminated, truncated, info

    def render(self, player_id, player_state):
        image = player_state.get("image")

        if image is None:
            # PERF: Load the image once, instead of every frame
            image = self.no_signal_img

        cv2.imshow(f"Player #{player_id:160x}", image)
        cv2.waitKey(1)


gym.register(
    id="gymnasium_env/Tankwars-v0",
    entry_point=TankwarsEnv,
    nondeterministic=True,
)
