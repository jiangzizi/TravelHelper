import socket

HOST = '127.0.0.1'  # 服务器的主机名或IP地址
PORT = 65432        # 服务器使用的端口

def start_client():
    """启动MCP客户端"""
    # AF_INET 表示使用IPv4, SOCK_STREAM 表示使用TCP
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((HOST, PORT))
            print(f"Connected to server at {HOST}:{PORT}")
            print("Type 'QUIT' to exit, 'PING' to test, or 'ECHO <your_message>' to echo.")

            while True:
                message = input("Client > ")
                if not message: # 如果用户只按回车
                    continue

                # 发送消息，确保添加换行符作为结束标志
                s.sendall((message + '\n').encode('utf-8'))

                if message.upper() == "QUIT":
                    print("Sent QUIT to server.")
                    # 等待服务器的最终确认或直接退出
                    # 这里简单地接收一次响应
                    try:
                        response_bytes = s.recv(1024)
                        if response_bytes:
                             print(f"Server < {response_bytes.decode('utf-8').strip()}")
                    except Exception as e:
                        print(f"Error receiving final response: {e}")
                    break # 退出客户端循环

                # 接收服务器的响应
                # 同样，为了简单，这里一次接收最多1024字节
                response_bytes = s.recv(1024)
                if not response_bytes:
                    print("Server closed connection unexpectedly.")
                    break
                
                response = response_bytes.decode('utf-8').strip()
                print(f"Server < {response}")

                if response.startswith("SERVER_NOTICE: Disconnecting"):
                    print("Disconnected by server.")
                    break


        except ConnectionRefusedError:
            print(f"Connection refused. Is the server running at {HOST}:{PORT}?")
        except ConnectionResetError:
            print("Connection to server was reset.")
        except BrokenPipeError:
            print("Connection to server was broken.")
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            print("Connection closed.")

if __name__ == "__main__":
    start_client()