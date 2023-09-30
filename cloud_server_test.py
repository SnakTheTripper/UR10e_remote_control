import zmq

# Define the server's IP address and port
# server_ip = "10.0.0.8"
server_port = "8090"

def main():
    context = zmq.Context()
    socket = context.socket(zmq.REP)

    # Bind the socket to the server's IP address and port
    socket.bind(f"tcp://*:{server_port}")
    print(f"Server listening on *ip:{server_port}")

    while True:
        message = socket.recv().decode()
        print(f"Received from client: {message}")

        if message == "0":
            response = "Server will shut down."
            socket.send(response.encode())
            return
        else:
            # Respond to the client
            response = "Received local message: "+message
            socket.send(response.encode())


if __name__ == "__main__":
    main()