import random
import time

import cv2

from src.client import GameClient, ObservationKind


def main():
    host, port = "localhost", 7878
    client = GameClient((host, port))  # Create client with server address

    try:
        client.connect()

    except ConnectionRefusedError:
        return print(
            f"Could not connect to server at {host}:{port}. Is the server running?"
        )

    # 1. Spawn a new tank
    print("Requesting a tank to be controlled")
    tank_id = client.get_tank()

    if tank_id is None:
        return print("Failed to receive a tank to control, quitting!")

    # 2. Subscribe to images and rewards for the spawned tank
    print(f"Subscribing to tank {tank_id=}")
    client.subscribe_to_observation(tank_id, ObservationKind.IMAGE, cooldown=0.1)
    client.subscribe_to_observation(tank_id, ObservationKind.REWARDS, cooldown=0.1)
    client.subscribe_to_observation(
        tank_id, ObservationKind.TANK_CONTROLS, cooldown=0.1
    )

    for turret in client.entity_state(tank_id).get("turrets", []):
        print("Subscribing to turret", turret)
        client.subscribe_to_observation(
            turret.turret_id, ObservationKind.TURRET_CONTROLS, cooldown=0.1
        )

    # 3. Start sending random controls, requesting new images, and displaying them in a loop
    try:
        while True:
            # Request the latest image
            client.request_observation(tank_id, ObservationKind.IMAGE)

            # Send random controls
            if random.random() < 0.01:
                controls = {
                    "right_engine": random.uniform(-1, 1),
                    "left_engine": random.uniform(-1, 1),
                }

                client.send_tank_controls(tank_id, controls)

            for turret in client.entity_state(tank_id).get("turrets", []):
                turret_controls = client.entity_state(turret.turret_id).get(
                    "turret_controls", None
                )
                if turret_controls is not None:
                    print("Turret controls:", turret_controls)

                if random.random() < 0.01:
                    controls = {
                        "rotation_speed": random.uniform(-1, 1),
                        "count": random.choice([-1, 0, 2]),
                    }

                    client.send_turret_controls(turret.turret_id, controls)

            # Show latest image

            image = client.entity_state(tank_id).get("image")
            if image is not None:
                cv2.imshow(f"Player #{tank_id:160x}", image)
                key = cv2.waitKey(1)  # Refresh the window to update the image
                if key == 27:
                    break

            else:
                print("Player image was not set, skipping")

            if reward := client.entity_state(tank_id).pop("reward", 0.0):
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
