'''
Created on Oct 12, 2016

@author: mwittie
'''
import queue
import threading
from typing import *


# wrapper class for a queue of packets
class Interface:
    # @param maxsize - the maximum size of the queue storing packets
    def __init__(self, maxsize=0):
        self.queue = queue.Queue(maxsize)
        self.mtu = None

    # get packet from the queue interface
    def get(self):
        try:
            return self.queue.get(False)
        except queue.Empty:
            return None

    # put the packet into the interface queue
    # @param pkt - Packet to be inserted into the queue
    # @param block - if True, block until room in queue, if False may throw queue.Full exception
    def put(self, pkt, block=False):
        self.queue.put(pkt, block)


# Implements a network layer packet (different from the RDT packet
# from programming assignment 2).
# NOTE: This class will need to be extended to for the packet to include
# the fields necessary for the completion of this assignment.
class NetworkPacket:
    # packet encoding lengths
    dst_addr_S_length = 5
    id_length = 5
    offset_length = 13
    flag_len = 1
    header_len = dst_addr_S_length + id_length + offset_length + flag_len

    # @param dst_addr: address of the destination host
    # @param data_S: packet payload
    # dummy comment for purposes of merge conflict practice
    # id: unique id for data to tell that multiple segments belong to same block of data
    # offset: where the bytes are to be inserted
    # flag: 1 is more fragments are coming, 0 is final fragment

    def __init__(self, dst_addr: int, id: int, offset: int, flag: int, data_S: str):
        self.dst_addr = dst_addr
        self.id = id
        self.offset = offset
        self.flag = flag
        self.data_S = data_S
    # called when printing the object

    def __str__(self):
        return self.to_byte_S()

    # convert packet to a byte string for transmission over links
    def to_byte_S(self):
        byte_S = str(self.dst_addr).zfill(self.dst_addr_S_length)
        byte_S += str(self.id).zfill(self.id_length)
        byte_S += str(self.offset).zfill(self.offset_length)
        byte_S += str(self.flag)
        byte_S += self.data_S
        return byte_S

    # extract a packet object from a byte string
    # @param byte_S: byte string representation of the packet
    @classmethod
    def from_byte_S(cls, byte_S: str):
        dst_addr = int(byte_S[0: NetworkPacket.dst_addr_S_length])
        id = int(
            byte_S[NetworkPacket.dst_addr_S_length:NetworkPacket.dst_addr_S_length + NetworkPacket.id_length])
        offset = int(byte_S[NetworkPacket.dst_addr_S_length + NetworkPacket.id_length:
                            NetworkPacket.dst_addr_S_length + NetworkPacket.id_length + NetworkPacket.offset_length])
        flag = int(byte_S[NetworkPacket.dst_addr_S_length + NetworkPacket.id_length + NetworkPacket.offset_length:
                          NetworkPacket.dst_addr_S_length + NetworkPacket.id_length + NetworkPacket.offset_length + 1])
        data_S = byte_S[NetworkPacket.dst_addr_S_length + NetworkPacket.id_length +
                        NetworkPacket.offset_length + NetworkPacket.flag_len:]
        return cls(dst_addr, id, offset, flag, data_S)

    @classmethod
    # for some reason the function notations was breaking the code, so I removed them. 
    # I prefer having them, so not sure how to get them back - Matteo
    def fragment(cls, packet, mtu: int):

        newPayloadSize = mtu - NetworkPacket.header_len
        msg = packet.data_S
        packet_list = []
        currentOffset = packet.offset
        currentFlag = packet.flag

        print("breaking up packet")
        while True:

            if len(msg) > newPayloadSize:

                
                msg_seg = msg[0:newPayloadSize]
                msg = msg[newPayloadSize:]
                new_packet = cls(packet.dst_addr, packet.id, currentOffset, 1, msg_seg)
                packet_list.append(new_packet)
                currentOffset += newPayloadSize
            else:
                if currentFlag == 0:
                    flagToUse = 0
                else:
                    flagToUse = 1

                new_packet = cls(packet.dst_addr, packet.id, currentOffset, flagToUse, msg)
                packet_list.append(new_packet)
                break

        return packet_list

    @classmethod
    # for some reason the function notations was breaking the code, so I removed them. 
    # I prefer having them, so not sure how to get them back - Matteo
    def defragment(cls, packet_list):
        sorted_packet_list = sorted(packet_list, key=lambda x: x.offset)
        message_joined = "".join(
            [packet.data_S for packet in sorted_packet_list])
        new_packet = cls(packet_list[0].dst_addr,
                         packet_list[0].id, 0, 0, message_joined)
        return new_packet

    def print(self):
        print('\n'.join("{k}: {v}".format(k=key, v=val)
                        for (key, val) in self.__dict__.items()))


# use this to test fragmentation

# pack = NetworkPacket(
#     5, 1, 0, 0, "Hellow meowww meow meow i like to go to the toilet and meowoooowowowowowo")
# len(pack.to_byte_S())
# print("MTU = 50")
# print("Packet Header Length: " + str(NetworkPacket.header_len))
# print("new packet data length: " + str(50 - NetworkPacket.header_len))
# pack_list = NetworkPacket.fragment(pack, 50)
# pack_list[0].print()
# print()
# pack_list[1].print()
# print()
# pack_list[2].print()
# print()

# NetworkPacket.defragment(pack_list).print()

# Implements a network host for receiving and transmitting data


class Host:

    # @param addr: address of this node represented as an integer
    def __init__(self, addr: int):
        self.addr = addr
        self.in_intf_L = [Interface()]
        self.out_intf_L = [Interface()]
        self.stop = False  # for thread termination

    # called when printing the object
    def __str__(self):
        return 'Host_%s' % (self.addr)

    # create a packet and enqueue for transmission
    # @param dst_addr: destination address for the packet
    # @param data_S: data being transmitted to the network layer
    def udt_send(self, dst_addr: int, id: int, offset: int, flag: int, data_S: str):
        p = NetworkPacket(dst_addr, id, offset, flag, data_S)
        out_mtu = self.out_intf_L[0].mtu

        # if outgoing MTU is too small, fragment packet
        if (len(p.to_byte_S()) > out_mtu):
            #generate packet fragments
            pkt_fragment_list = NetworkPacket.fragment(p,out_mtu)
            # send all packet fragments
            for pkt in pkt_fragment_list:
                self.out_intf_L[0].put(pkt.to_byte_S())
                print('%s: sending packet "%s" on the out interface with mtu=%d' %
                   (self, pkt, self.out_intf_L[0].mtu))
        else:
            # if outgoing MTU is big enough, send packet
            self.out_intf_L[0].put(p.to_byte_S())
            print('%s: sending packet "%s" on the out interface with mtu=%d' %
               (self, p, self.out_intf_L[0].mtu))

        # send packets always enqueued successfully
        # self.out_intf_L[0].put(p.to_byte_S())
        # print('%s: sending packet "%s" on the out interface with mtu=%d' %
        #       (self, p, self.out_intf_L[0].mtu))

    # receive packet from the network layer
    def udt_receive(self) -> str:
        pkt_S = self.in_intf_L[0].get()
        if pkt_S is not None:
            return pkt_S
          

    # thread target for the host to keep receiving data
    def run(self):
        print(threading.currentThread().getName() + ': Starting')
        pkt_list = []
        while True:
            # receive data arriving to the in interface
            pkt_S = self.udt_receive()
            if pkt_S is not None:
                p = NetworkPacket.from_byte_S(pkt_S)
                pkt_list.append(p)
                if p.flag == 0: 
                    full_packet = NetworkPacket.defragment(pkt_list)
                    pkt_list = []
                    print('%s: received packet "%s" on the in interface' % (self, full_packet.to_byte_S()))

            # terminate
            if(self.stop):
                print(threading.currentThread().getName() + ': Ending')
                return


# Implements a multi-interface router described in class
class Router:

    # @param name: friendly router name for debugging
    # @param intf_count: the number of input and output interfaces
    # @param max_queue_size: max queue length (passed to Interface)
    def __init__(self, name, intf_count, max_queue_size, forwarding_table, input_node: bool):
        self.stop = False  # for thread termination
        self.name = name
        # create a list of interfaces
        self.in_intf_L = [Interface(max_queue_size) for _ in range(intf_count)]
        self.out_intf_L = [Interface(max_queue_size)
                           for _ in range(intf_count)]
        self.forwarding_table = forwarding_table
        self.input_node = input_node

    # called when printing the object
    def __str__(self):
        return 'Router_%s' % (self.name)

    # look through the content of incoming interfaces and forward to
    # appropriate outgoing interfaces
    def forward(self):
        for i in range(len(self.in_intf_L)):
            pkt_S = None
            try:
                # get packet from interface i
                pkt_S = self.in_intf_L[i].get()
                # if packet exists make a forwarding decision
                if pkt_S is not None:
                    
                    
                    p = NetworkPacket.from_byte_S(pkt_S)  # parse a packet out
                    if self.input_node == True:
                        out_interface = i#self.forwarding_table[i]
                    else:
                        out_interface = self.forwarding_table[p.dst_addr]
                    out_mtu = self.out_intf_L[out_interface].mtu
                    # HERE you will need to implement a lookup into the
                    # forwarding table to find the appropriate outgoing interface
                    # for now we assume the outgoing interface is also i

                    # if packet is too big for outgoing MTU, fragment packet
                    if (len(pkt_S) > out_mtu):
                        # generate packet fragments
                        pkt_fragment_list = NetworkPacket.fragment(p, out_mtu)
                        # send all packet fragments
                        for pkt in pkt_fragment_list:
                            self.out_intf_L[out_interface].put(pkt.to_byte_S(), True)
                            print('%s: forwarding packet "%s" from interface %d to %d with mtu %d'
                                % (self, pkt, i, out_interface, out_mtu))
                    else:
                        # if outgoing MTU is big enough, send packet
                        self.out_intf_L[out_interface].put(p.to_byte_S(), True)
                        print('%s: forwarding packet "%s" from interface %d to %d with mtu %d'
                              % (self, p, i, out_interface, out_mtu))

            except queue.Full:
                #print('%s: packet "%s" lost on interface %d' % (self, p, i))
                pass

    # thread target for the host to keep forwarding data
    def run(self):
        print(threading.currentThread().getName() + ': Starting')
        while True:
            self.forward()
            if self.stop:
                print(threading.currentThread().getName() + ': Ending')
                return
