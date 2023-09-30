import zmq

# Define the server's IP address and port
server_ip = "20.100.204.66"
server_port = "8090"


def main():
    context = zmq.Context()
    socket = context.socket(zmq.REQ)

    # Connect to the server
    socket.connect(f"tcp://{server_ip}:{server_port}")
    print(f"Connected to {server_ip}:{server_port}")

    while True:
        message = input("Enter a message to send to the server (or 'exit' to quit): ")
        if message == 'exit':
            break
        socket.send(message.encode())

        # Receive and print the server's response
        response = socket.recv().decode()
        print(f"Received from server: {response}")


if __name__ == "__main__":
    main()