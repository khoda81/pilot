import socket
import time

import game_socket_pb2


def connect_to_server(host: str, port: int) -> socket.socket:
    """Connect to the server and return the socket."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    print(f"Connected to server at {host}:{port}")
    return sock


def send_tank_control(sock: socket.socket, right: float, left: float) -> None:
    """Send tank engine control data to the server."""
    # Create the SetEngines message
    control_data = game_socket_pb2.SetEngines(right=right, left=left)
    message = game_socket_pb2.ClientMessage(engines=control_data)

    # Serialize the message to a binary format
    serialized_data = message.SerializeToString()

    # Send the serialized data over the socket
    sock.sendall(serialized_data)


def main() -> None:
    """Main function to control tank via the server."""
    host: str = "127.0.0.1"  # localhost
    port: int = 7878  # The port used by the server

    try:
        sock: socket.socket = connect_to_server(host, port)

        # Main control loop
        try:
            while True:
                # Example: Move forward at speed 1.0, no rotation
                send_tank_control(sock, 1.0, 0.0)
                time.sleep(1)

                # Example: Rotate right at speed 0.5, no forward movement
                send_tank_control(sock, 0.0, 0.5)
                time.sleep(1)

                # Example: Move backward at speed 0.7, slight left rotation
                send_tank_control(sock, -0.7, -0.2)
                time.sleep(1)

        except KeyboardInterrupt:
            print("Client stopped by user")

    except ConnectionRefusedError:
        print(f"Could not connect to server at {host}:{port}. Is the server running?")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if "sock" in locals():
            sock.close()
            print("Connection closed")


if __name__ == "__main__":
    main()
