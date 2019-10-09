import Network 
import argparse
from time import sleep
import hashlib

class Packet:
    ## the number of bytes used to store packet length
    seq_num_S_length = 10
    length_S_length = 10
    ## length of md5 checksum in hex
    checksum_length = 32 
    
    ## initialize each packet with a sequence number and message    
    def __init__(self, seq_num, msg_S):
        self.seq_num = seq_num
        self.msg_S = msg_S
        
    @classmethod
    def from_byte_S(self, byte_S):
        if Packet.corrupt(byte_S):
            raise RuntimeError('Cannot initialize Packet: byte_S is corrupt')
        #extract the fields
        seq_num = int(byte_S[Packet.length_S_length : Packet.length_S_length+Packet.seq_num_S_length])
        msg_S = byte_S[Packet.length_S_length+Packet.seq_num_S_length+Packet.checksum_length :]
        return self(seq_num, msg_S)
        seq_num_S_length
        
    def get_byte_S(self):
        #convert sequence number of a byte field of seq_num_S_length bytes
        seq_num_S = str(self.seq_num).zfill(self.seq_num_S_length)
        print (seq_num_S)
        #convert length to a byte field of length_S_length bytes
        length_S = str(self.length_S_length + len(seq_num_S) + self.checksum_length + len(self.msg_S)).zfill(self.length_S_length)
        #compute the checksum
        checksum = hashlib.md5((length_S+seq_num_S+self.msg_S).encode('utf-8'))
        checksum_S = checksum.hexdigest()
        #compile into a string
        print("Length: " + length_S)
        print("Seq_num_S: " + seq_num_S)
        print("checksum_S: " + checksum_S )
        print("self.msg_s: " + self.msg_S)
        #print( length_S + seq_num_S + checksum_S + self.msg_S)
        return length_S + seq_num_S + checksum_S + self.msg_S
   
    
    @staticmethod
    def corrupt(byte_S):
        #extract the fields
        length_S = byte_S[0:Packet.length_S_length]
        seq_num_S = byte_S[Packet.length_S_length : Packet.seq_num_S_length+Packet.seq_num_S_length]
        checksum_S = byte_S[Packet.seq_num_S_length+Packet.seq_num_S_length : Packet.seq_num_S_length+Packet.length_S_length+Packet.checksum_length]
        msg_S = byte_S[Packet.seq_num_S_length+Packet.seq_num_S_length+Packet.checksum_length :]
        
        #compute the checksum locally
        checksum = hashlib.md5(str(length_S+seq_num_S+msg_S).encode('utf-8'))
        computed_checksum_S = checksum.hexdigest()
        #and check if the same
        return checksum_S != computed_checksum_S
        

class RDT:
    ## latest sequence number used in a packet
    seq_num = 1
    ## buffer of bytes read from network
    byte_buffer = '' 

    def __init__(self, role_S, server_S, port):
        self.network = Network.NetworkLayer(role_S, server_S, port)
    
    def disconnect(self):
        self.network.disconnect()
        
    def rdt_1_0_send(self, msg_S):
        p = Packet(self.seq_num, msg_S)
        self.seq_num += 1
        self.network.udt_send(p.get_byte_S())
        
    def rdt_1_0_receive(self):
        ret_S = None
        byte_S = self.network.udt_receive()
        self.byte_buffer += byte_S
        #keep extracting packets - if reordered, could get more than one
        while True:
            #check if we have received enough bytes
            print(ret_S)

            if(len(self.byte_buffer) < Packet.length_S_length):
                print("exit 1")
                return ret_S #not enough bytes to read packet length

            #extract length of packet
            length = int(self.byte_buffer[:Packet.length_S_length])
            if len(self.byte_buffer) < length:
                print("exit2")
                return ret_S #not enough bytes to read the whole packet
            #create packet from buffer content and add to return string
            p = Packet.from_byte_S(self.byte_buffer[0:length])
            ret_S = p.msg_S if (ret_S is None) else ret_S + p.msg_S
            #remove the packet bytes from the buffer
            self.byte_buffer = self.byte_buffer[length:]
            #if this was the last packet, will return on the next iteration
        print("********************************************receive exit")
            
    def isNAK(self, ret_S):
        pass

    def isACK(self, ret_S):
        pass
    
    #############
    # TODO:
    # 1. reciever sends back packet with "ACK" "NAK"
    # 2. 
    #############
    def rdt_2_1_send(self, msg_S):

        p = Packet(self.seq_num, msg_S)
        self.seq_num += 1

        # Wait for ack or nak
        while True:

            self.network.udt_send(p.get_byte_S())

            # Get recienver response....
            # How do we do this?

            # Check if ACK, then return

            if self.isACK(response):
                print("Packet ACK'd")
                return
            
            if self.isNAK(response):
                print("Packet NAK'd")
                continue
        
            # Should the sender check for corruption???
            #if Packet.corrupt(???)
            #if response == "corrupt":
            #    continue


            # Check if NAK, then resend
            # Check if corrupt, then resend



    #############
    # TODO:
    # 1. reciever sends back packet with "ACK" "NAK"
    # 2. 
    #############
    def rdt_2_1_receive(self):
        ret_S = None
        byte_S = self.network.udt_receive()
        self.byte_buffer += byte_S

        #keep extracting packets - if reordered, could get more than one
        while True:
            #check if we have received enough bytes
            if(len(self.byte_buffer) < Packet.length_S_length):
                return ret_S #not enough bytes to read packet length
            #extract length of packet
            length = int(self.byte_buffer[:Packet.length_S_length])
            if len(self.byte_buffer) < length:
                #print("exit2")
                return ret_S #not enough bytes to read the whole packet
            #create packet from buffer content and add to return string
            p = Packet.from_byte_S(self.byte_buffer[0:length])

            #packet must have current seq number and not corrupt to pass
            if (p.seq_num == seq_num and not Packet.corrupt(byte_S)):
                #deliver data: 

                ret_S = p.msg_S if (ret_S is None) else ret_S + p.msg_S
                #remove the packet bytes from the buffer
                self.byte_buffer = self.byte_buffer[length:]
                
                #Send ACK Packet

                #increment sequence RDT sequence number
                
            elif (Packet.corrupt(byte_S)):
                #Send NACK Packet
                pass

            elif (True):#not corrupt but wrong sequence number
                #Send Nack Packet
                pass

            elif (True): #
                pass




            
        print("********************************************receive exit")
    
        

if __name__ == '__main__':
    parser =  argparse.ArgumentParser(description='RDT implementation.')
    parser.add_argument('role', help='Role is either client or server.', choices=['client', 'server'])
    parser.add_argument('server', help='Server.')
    parser.add_argument('port', help='Port.', type=int)
    args = parser.parse_args()
    
    rdt = RDT(args.role, args.server, args.port)
    if args.role == 'client':
        rdt.rdt_1_0_send('MSG_FROM_CLIENT')
        sleep(2)
        print(rdt.rdt_1_0_receive())
        rdt.disconnect()
        
        
    else:
        sleep(1)
        print(rdt.rdt_1_0_receive())
        rdt.rdt_1_0_send('MSG_FROM_SERVER')
        rdt.disconnect()
        


        
        
