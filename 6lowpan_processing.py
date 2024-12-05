import socket
import json
import time 

node_ips = ["aaaa::212:7406:6:606",
		"aaaa::212:7407:7:707",
		"aaaa::212:7408:8:808",
		"aaaa::212:7409:9:909"]

def choose_node(number):
    if number == '1':
	node_addr = node_ips[0]
    elif number == '2':
	node_addr = node_ips[1]
    elif number == '3':
        node_addr = node_ips[2]
    elif number == '4':
	node_addr = node_ips[3]
    elif number == '0':     #number = 0 will connect to all nodes
	#do sth
	node_addr = "all"
    else:
	node_addr = "error"
    return node_addr

def processing_json_data(data):
	#Process json data
	message = json.loads(data)
	node = message.get("node")
	command = message.get("command")

	node_ip = choose_node(node)
	print("node is : {}, command is: {}".format(node_ip,command))

	return node_ip, command

def message_listening_to_PC(host, port): 
    socket4 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:	
	socket4.bind((host, port))
	socket4.listen(1)
        print("Server is listening on {}:{}".format(host,port))

	# Wait for a connection
        conn, addr = socket4.accept()
        print("Connected by {}".format(addr))
	
	# Receive the message
        data = conn.recv(1024).decode()
        print("Received: {}".format(data))
 
	conn.close()
    except Exception as e:
        print("Error: {}".format(e))
    finally: 
	socket4.close()
	return data

def message_sending_to_PC(message, host, port):
    socket4 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try: 
	# Connect to the VM
    	socket4.connect((host, port))
    	print("Connected to {}:{}".format(host, port))

    	# Send the message
    	socket4.sendall(message.encode())
    	print("Message sent!")

    except Exception as e:
        print("Error: {}".format(e))
    finally: 
	socket4.close()

def message_to_nodes(message, node_ipv6, port):
    socket6 = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
    try:
	# Send the UDP message
        print("Sending message to [{}]:{}".format(node_ipv6,port))
        socket6.sendto(message.encode(), (node_ipv6, port))

        # Set timeout for response (optional)
        socket6.settimeout(5)  # 5 seconds timeout for response

        # Listen for the response
        print("Waiting for response...")
        response, address = socket6.recvfrom(1024)  # Buffer size of 1024 bytes
        print("Received response from [{}]:{} - {}".format(address[0],address[1],response.decode()))		
    except Exception as e:
        print("Error: {}".format(e))
    finally:
	socket6.close()
	return response.decode()

	
if __name__ == "__main__":
    HOST_PC_listening = "0.0.0.0"
    HOST_PC_sending = raw_input("Enter HOST IP: ")
    PORT_to_PC = 5000       
    PORT_to_cooja = 3000

    while(1):
	message_recv_from_pc = message_listening_to_PC(HOST_PC_listening, PORT_to_PC)
	node_ip, cmd = processing_json_data(message_recv_from_pc)
	reply = message_to_nodes(cmd, node_ip, PORT_to_cooja)
	message_sending_to_PC(reply, HOST_PC_sending, PORT_to_PC)
	



