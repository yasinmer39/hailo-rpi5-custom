import socket

# UDP socket (alıcı) setup
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('localhost', 5005))

print("Listening for detections...")
while True:
    data, addr = sock.recvfrom(1024)  # 1024 byte buffer
    message = data.decode()
    print(f"Received detection: {message}")