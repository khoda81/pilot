import socket
import time
import game_socket_pb2


def connect_to_server(host: str, port: int) -> socket.socket:
    """Connect to the server and return the socket."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    print(f"Connected to server at {host}:{port}")
    return sock


def encode_varint(value: int) -> bytes:
    """Encodes an integer as a protobuf varint (used for length-delimited)."""
    result = []
    while value > 127:
        result.append((value & 0x7F) | 0x80)
        value >>= 7

    result.append(value)
    return bytes(result)


def send_length_delimited_message(sock: socket.socket, message):
    # Serialize the message to a binary format
    serialized_data = message.SerializeToString()

    # Get the length of the serialized data and encode it as varint
    message_length = len(serialized_data)
    length_prefix = encode_varint(message_length)

    # Send the length prefix followed by the serialized data
    sock.sendall(length_prefix)
    sock.sendall(serialized_data)


def send_tank_control(
    sock: socket.socket,
    right: float,
    left: float,
    fire: bool = False,
) -> None:
    """Send tank engine control data to the server, length-delimited."""
    # Create the SetEngines message
    controls = game_socket_pb2.Controls(
        right_engine=right,
        left_engine=left,
        fire=fire,
    )

    control_data = game_socket_pb2.ControlUpdate(player_id=0, controls=controls)
    message = game_socket_pb2.ClientMessage(action=control_data)

    send_length_delimited_message(sock, message)


def send_spawn_request(sock: socket.socket) -> None:
    message = game_socket_pb2.SpawnPlayerRequest()
    message = game_socket_pb2.ClientMessage(spawn_player=message)

    send_length_delimited_message(sock, message)


def main() -> None:
    """Main function to control tank via the server."""
    host: str = "127.0.0.1"  # localhost
    port: int = 7878  # The port used by the server

    try:
        sock: socket.socket = connect_to_server(host, port)

        send_spawn_request(sock)

        #  TODO: Wait until server responds with the player that was spawned

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
