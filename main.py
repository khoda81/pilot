import time

import cv2
import gymnasium as gym

import environment
from src.client import Entity, GameClient, ObservationKind


def main():
    host, port = "localhost", 7878
    client = GameClient((host, port))  # Create client with server address

    try:
        client.connect()

    except ConnectionRefusedError:
        return print(
            f"Could not connect to server at {host}:{port}. Is the server running?"
        )

    env = gym.make("gymnasium_env/Tankwars-v0", client)
    player_id = env.reset()

    # 3. Start sending random controls, requesting new images, and displaying them in a loop
    try:
        while True:
            player_state = client.entity_state(player_id)

            # Send random controls
            controls = env.action_space.sample()
            player_state, reward, terminated, truncated, info = env.step(
                player_id, controls
            )

            # Show latest image
            env.render(player_id, player_state)

            print("New reward:", reward)

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("Client stopped by user!")

    except ConnectionResetError:
        print("Connection terminated by the server!")

    except ConnectionAbortedError:
        print("Connection terminated!")

    finally:
        client.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
