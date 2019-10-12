import Network_3_0 as Network
import argparse
import time
import hashlib

class Packet:
    ## the number of bytes used to store packet length
    seq_num_S_length = 10
    length_S_length = 10

    ## length of md5 checksum in hex
    checksum_length = 32 

    # Length of ack-nak section
    ACK_NAK_length = 2
    
    ## initialize each packet with a sequence number and message    
    def __init__(self, seq_num: int, msg_S: str = "", ACK: int = 0, NAK: int = 0):
        self.seq_num = seq_num
        self.msg_S = msg_S
        self.ACK = ACK
        self.NAK = NAK

    @classmethod
    def from_byte_S(self, byte_S: str):
        if Packet.corrupt(byte_S):
            raise RuntimeError('Cannot initialize Packet: byte_S is corrupt')
        #extract the fields
        seq_num = int(byte_S[Packet.length_S_length : Packet.length_S_length + Packet.seq_num_S_length])
        ack = byte_S[Packet.seq_num_S_length + Packet.seq_num_S_length + Packet.checksum_length: Packet.seq_num_S_length + Packet.length_S_length + Packet.checksum_length + Packet.ACK_NAK_length - 1]
        nak = byte_S[Packet.seq_num_S_length + Packet.seq_num_S_length + Packet.checksum_length + Packet.ACK_NAK_length - 1: Packet.seq_num_S_length + Packet.length_S_length + Packet.checksum_length + Packet.ACK_NAK_length]
        msg_S = byte_S[Packet.length_S_length + Packet.seq_num_S_length + Packet.checksum_length + Packet.ACK_NAK_length:]
        return self(seq_num, msg_S, int(ack), int(nak))

        
    def get_byte_S(self) -> str:
        #convert sequence number of a byte field of seq_num_S_length bytes
        seq_num_S = str(self.seq_num).zfill(self.seq_num_S_length)
        #convert length to a byte field of length_S_length bytes
        length_S = str(self.length_S_length + len(seq_num_S) + self.checksum_length + self.ACK_NAK_length + len(self.msg_S)).zfill(self.length_S_length)
        #compute the checksum
        checksum = hashlib.md5((length_S + seq_num_S + str(self.ACK) + str(self.NAK) + self.msg_S).encode('utf-8'))
        checksum_S = checksum.hexdigest()
        #compile into a string

        return length_S + seq_num_S + checksum_S + str(self.ACK) + str(self.NAK) + self.msg_S
   
    
    @staticmethod
    def corrupt(byte_S: str) -> bool:
        #extract the fields
        length_S = byte_S[0:Packet.length_S_length]
        seq_num_S = byte_S[Packet.length_S_length : Packet.seq_num_S_length + Packet.seq_num_S_length]
        checksum_S = byte_S[Packet.seq_num_S_length + Packet.seq_num_S_length : Packet.seq_num_S_length + Packet.length_S_length + Packet.checksum_length]
        ack_nak_S = byte_S[Packet.seq_num_S_length + Packet.seq_num_S_length + Packet.checksum_length: Packet.seq_num_S_length + Packet.length_S_length + Packet.checksum_length + Packet.ACK_NAK_length]
        msg_S = byte_S[Packet.seq_num_S_length + Packet.seq_num_S_length + Packet.checksum_length + Packet.ACK_NAK_length :]

        #compute the checksum locally
        checksum = hashlib.md5(str(length_S + seq_num_S + ack_nak_S + msg_S).encode('utf-8'))
        computed_checksum_S = checksum.hexdigest()

        #and check if the same
        return checksum_S != computed_checksum_S
    
    def isACK(self) -> bool:
        return self.ACK == 1

    def isNAK(self) -> bool:
        return self.NAK == 1

    def print_debug(self):
        print("Seq_num_S: " + str(self.seq_num))
        print("self.ACK: " + str(self.ACK))
        print("self.isACK(): " + str(self.isACK()))
        print("self.NAK: " + str(self.NAK))
        print("self.isNAK(): " + str(self.isNAK()))
        print("self.msg_s: " + self.msg_S)


# Should just put corruption checking in try catch block

class RDT:
    ## latest sequence number used in a packet
    seq_num = 1
    ## buffer of bytes read from network
    byte_buffer = '' 
    timeout_secs = 0.5

    def __init__(self, role_S, server_S, port):
        self.network = Network.NetworkLayer(role_S, server_S, port)
    
    def disconnect(self):
        self.network.disconnect()
        
    def rdt_3_0_send(self, msg_S):

        p = Packet(self.seq_num, msg_S)

        while True:

            self.network.udt_send(p.get_byte_S())
            self.byte_buffer = ''
            currentTime = time.time()
            timeout = False

            while len(self.byte_buffer) == 0:
                self.byte_buffer = self.network.udt_receive()
                
                if (time.time() - currentTime) > self.timeout_secs:
                    timeout = True
                    break
            
            if timeout is True:
                print("Timeout from packet loss!")
                continue

            length = int(self.byte_buffer[:Packet.length_S_length])
            

            if Packet.corrupt(self.byte_buffer[:length]):
                print("Sender: Response packet corrupt.")
                continue
            
            responsePacket = Packet.from_byte_S(self.byte_buffer[:length])

            responsePacket = Packet.from_byte_S(self.byte_buffer[:length])

            if self.seq_num > responsePacket.seq_num:

                #print("resending ack for received packet")
                senderResponse = Packet(p.seq_num, ACK=1)
                self.network.udt_send(senderResponse.get_byte_S())

            if responsePacket.isACK():
                #print("Sender: Received ACK!")
                self.seq_num += 1
                return

            if responsePacket.isNAK():
                #print("Sender: recieved NAK")
                continue


    def rdt_3_0_receive(self):

        ret_S = None
        byte_S = self.network.udt_receive()
        self.byte_buffer += byte_S
        current_seq_num = self.seq_num

        #keep extracting packets - if reordered, could get more than one
        while self.seq_num == current_seq_num:

            #check if we have received enough bytes
            if(len(self.byte_buffer) < Packet.length_S_length):
                #print("Reciever print 1")
                break

            #extract length of packet
            length = int(self.byte_buffer[:Packet.length_S_length])
            if len(self.byte_buffer) < length:
                self.byte_buffer = self.byte_buffer[length:]
                break

            if Packet.corrupt(self.byte_buffer[0:length]):
                print("Reciever: corrupted packet")
                #Send NACK
                NAK = Packet(self.seq_num, NAK=1)
                #print("Receiver: Sending a NAK packet: " + NAK.get_byte_S())
                self.network.udt_send(NAK.get_byte_S())
                self.byte_buffer = self.byte_buffer[length:]
                continue
            
            p = Packet.from_byte_S(self.byte_buffer[0:length])

            if not p.isACK():

                if self.seq_num > p.seq_num:
                    #send ACK
                    ACK = Packet(p.seq_num, ACK=1)
                    self.network.udt_send(ACK.get_byte_S())

                elif p.seq_num == self.seq_num:
                    #send ACK
                    ACK = Packet(self.seq_num, ACK=1)
                    self.network.udt_send(ACK.get_byte_S())
                    #increment sequence
                    self.seq_num += 1# % 2
                
                #deliver data: 
                ret_S = p.msg_S if (ret_S is None) else ret_S + p.msg_S

            #reset buffer to exit while loop
            self.byte_buffer = self.byte_buffer[length:]
        return ret_S
        

if __name__ == '__main__':
    parser =  argparse.ArgumentParser(description='RDT implementation.')
    parser.add_argument('role', help='Role is either client or server.', choices=['client', 'server'])
    parser.add_argument('server', help='Server.')
    parser.add_argument('port', help='Port.', type=int)
    args = parser.parse_args()
    
    rdt = RDT(args.role, args.server, args.port)
    if args.role == 'client':
        rdt.rdt_1_0_send('MSG_FROM_CLIENT')
        time.sleep(2)
        print(rdt.rdt_1_0_receive())
        rdt.disconnect()
        
        
    else:
        time.sleep(1)
        print(rdt.rdt_1_0_receive())
        rdt.rdt_1_0_send('MSG_FROM_SERVER')
        rdt.disconnect()
        


        
        
