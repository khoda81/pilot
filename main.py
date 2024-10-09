import random
import time

import cv2

from client import GameClient, ObservationKind


def main():
    host, port = "localhost", 7878
    client = GameClient((host, port))  # Create client with server address

    try:
        client.connect()

    except ConnectionRefusedError:
        return print(
            f"Could not connect to server at {host}:{port}. Is the server running?"
        )

    # 1. Request player list from the server
    print("Requesting player list from the server")
    client.request_player_list()

    # 2. Spawn a new player
    print("Requesting a player to be controlled")
    player_id = client.get_player()

    if player_id is None:
        return print("Failed to receive a player to control, quitting!")

    # 3. Subscribe to images and rewards for the spawned player
    print("Subscribing to player")
    client.subscribe_to_observation(player_id, ObservationKind.IMAGE, cooldown=0.1)
    client.subscribe_to_observation(player_id, ObservationKind.REWARDS, cooldown=0.1)

    # 4. Start sending random controls, requesting new images, and displaying them in a loop
    try:
        while True:
            # Request the latest image
            client.request_observation(player_id, ObservationKind.IMAGE)

            # Send random controls
            controls = {
                "right_engine": random.uniform(-1, 1),
                "left_engine": random.uniform(-1, 1),
                "fire": random.choice([True, False]),
            }

            client.send_controls(player_id, controls)

            # Show latest image
            player_state = client.player_state(player_id)

            image = player_state.get("image")
            if image is not None:
                cv2.imshow(f"Player #{player_id:160x}", image)
                cv2.waitKey(1)  # Refresh the window to update the image

            else:
                print("Player image was not set, skipping")

            if reward := player_state.pop("reward", 0.0):
                print("New reward:", reward)

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("Client stopped by user")

    finally:
        print("Error occurred, quitting!")
        client.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
