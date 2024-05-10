import socket, select, sys

class ChatServer():
    def __init__(self, host = "localhost", port = 6000):
        self.network = {
            "default": {
                "connections": [],
                "names": []
            }
        }
        self.RECV_BUFFER = 4096
        self.HOST = host
        self.PORT = port
        self.server_socket = 0
        self.separator = "|||" 

    def init(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.HOST, self.PORT))
        self.server_socket.listen(2)
        self.network["default"]["connections"].append(self.server_socket)
        self.network["default"]["names"].append("<server>")

        print "Running chat server at {}:{}".format(self.HOST, self.PORT)

        while True:
            all_connections = []
            for key in self.network:
                all_connections += self.network[key]["connections"]
            read_sockets, write_sockets, error_sockets = select.select(all_connections,[],[])

            for sock in read_sockets:

                if sock == self.server_socket:
                    sockfd, addr = self.server_socket.accept()


                    roomsList = ""
                    for group in self.network.keys():
                        numberOfMembersInRoom = len(self.network[group]["connections"])
                        if group == "default":
                            numberOfMembersInRoom -= 1  # exclude server
                        roomsList += group + " <{}>::".format(numberOfMembersInRoom)
                    roomsList = roomsList[:-2]
                    sockfd.send(roomsList)
                    group = sockfd.recv(32)

                    if group == "":
                        continue
                    elif group not in self.network.keys():

                        self.network[group] = {
                            "connections": [],
                            "names": []
                        }

                    clientName = sockfd.recv(100)
                    if clientName == "":
                        continue
                    elif clientName not in self.network[group]["names"]:
                        self.network[group]["names"].append(clientName)
                        self.network[group]["connections"].append(sockfd)
                        msg_notification = "{} joined [{}] from <{}:{}>".format(clientName, group, addr[0], addr[1])
                        print msg_notification
                        self.broadcast(group, sockfd, msg_notification, isInfo = True)
                        sockfd.send("SERVER_INFO" + self.separator + "Welcome.")
                    else:
                        sockfd.send("SERVER_FAIL" + self.separator + "Cannot have same name.")
                else:
                    try:
                        data = sock.recv(self.RECV_BUFFER)
                        group = data.split(self.separator, 1)[0]
                        if "LIST" in data:
                            self.sendList(group, sock)
                        elif len(data) > 0:
                            self.broadcast(group, sock, data.split(self.separator, 1)[1])
                        else:
                            raise
                    except:
                        i = None
                        group = ""
                        for key in self.network:
                            if sock in self.network[key]["connections"]:
                                i = self.network[key]["connections"].index(sock)
                                group = key
                                break
                        if (i != None and group != ""):
                            msg_notification = "{} from [{}] <{}:{}> went offline.".format(self.network[group]["names"][i], group, addr[0], addr[1])
                            self.broadcast(group, sock, msg_notification, isInfo = True)
                            print msg_notification
                            del self.network[group]["connections"][i]
                            del self.network[group]["names"][i]
                        continue

        self.server_socket.close()

    def broadcast(self, group, sender, message, isInfo = False):
        i = self.network[group]["connections"].index(sender)
        sender_name = self.network[group]["names"][i]
        if isInfo:
            sender_name = "SERVER_INFO"

        recievers = self.network[group]["connections"]

        try:
            if "@" in message:
                sendTo = message.split("@", 1)[1].split(" ", 1)[0]
                j = self.network[group]["names"].index(sendTo)
                recievers = [self.network[group]["connections"][j]]
        except:
            sender.send("SERVER_INFO" + self.separator + "Your message was broadcasted.")
            print "name not found, sending to all :P"

        message = sender_name + self.separator + message
        for socket in recievers:
            if socket != self.server_socket and socket != sender:
                try:
                    socket.send(message)
                except:

                    i = self.network[group]["connections"].index(socket)
                    print "removing", self.network[group]["names"][i]
                    del self.network[group]["connections"][i]
                    del self.network[group]["names"][i]
                    socket.close()

    def sendList(self, group, requestor):
        if group == "default":
            names = self.network[group]["names"][1:]
            connections = self.network[group]["connections"][1:]
        else:
            names = self.network[group]["names"]
            connections = self.network[group]["connections"]

        list_str = ""
        for name, addr in zip(names, connections):
            host, port = addr.getpeername()
            list_str += name + " <{}:{}>::".format(host, port)
        requestor.send(list_str[:-2]) # remove end ::

def main():
    import os
    my_inet = os.popen('ifconfig | grep "inet addr" | cut -d: -f2 | cut -d" " -f1 | head -1')
    host = my_inet.read().strip()

    try:
        port = int(sys.argv[1])
    except:
        port = int(raw_input("Port: "))

    server = ChatServer(host = host, port = port)
    server.init()

if __name__ == '__main__':
    main()
