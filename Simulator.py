import sys

#registers
reg_table={format(i, '05b'): i for i in range(32)} # map 5-bit reg to index
REGISTER_WIDTH=32
STACK_POINTER_INIT=0x17C

# initializing registers
reg_data={}
for r in reg_table:
    reg_data[r]='0'*32

# initialize stack pointer
reg_data['00010']=format(STACK_POINTER_INIT, '032b')

#memory
MEM_START=65536
MEM_END=65536+(32*4)-4
MEM_STEP=4

mem_data={} # initializing to 32 memory words

for i in range(32):
    loc=MEM_START+i*4
    mem_data[f"0x{loc:08X}"]=0


#types
instr_type_map={
    '0110011': 'R',
    '0000011': 'I',
    '0010011': 'I',
    '1100111': 'I',
    '0100011': 'S',
    '1100011': 'B',
    '1101111': 'J'
}


#helpers
def sign_extend(val, bits): # sign being extended here
    if val & (1<<(bits-1)):
        val-=(1<<bits)
    return val


def convert_bin_to_int(binary_str): # converting binary to integer
    val=int(binary_str, 2)
    if binary_str[0]=='1':
        val-=(1<<32)
    return val


def to_bin(val): # converting integer to binary
    return format(val & 0xFFFFFFFF,'032b')


def normalize(val): # keeping everything in the 32-bit range
    return val & 0xFFFFFFFF


#execution
def execute_program(instructions_list,output_file):
    output= ""

    # cleaning instructions
    instructions_list=[x.strip() for x in instructions_list if x.strip()]

    # loading instructions into memory
    instr_memory={}
    for i in range(len(instructions_list)):
        instr_memory[i*4]=instructions_list[i]

    pc=0

    while pc in instr_memory:
        curr_instr=instr_memory[pc]
        opcode=curr_instr[-7:]
        instr_type=instr_type_map[opcode]

        last_pc=pc

        # r type
        if instr_type=='R':
            funct7=curr_instr[:7]
            rs2=curr_instr[7:12]
            rs1=curr_instr[12:17]
            funct3=curr_instr[17:20]
            rd=curr_instr[20:25]

            a=int(reg_data[rs1],2)
            b=int(reg_data[rs2],2)

            # ALU operations
            if funct3=='000' and funct7=='0000000':  #add
                res=a+b
                reg_data[rd]=to_bin(res)

            elif funct3=='000' and funct7=='0100000':  #sub
                res=a-b
                reg_data[rd]=to_bin(res)

            elif funct3=='001':  #sll
                res=a<<(b & 31)
                reg_data[rd]=to_bin(res)

            elif funct3=='010':  #slt(signed)
                if convert_bin_to_int(reg_data[rs1])<convert_bin_to_int(reg_data[rs2]):
                    reg_data[rd]=to_bin(1)
                else:
                    reg_data[rd]=to_bin(0)

            elif funct3=='011':  #sltu(unsigned)
                reg_data[rd]=to_bin(1 if a<b else 0)

            elif funct3=='101' and funct7=='0000000':  #srl
                res=(a%(1<<32))>>(b & 31)
                reg_data[rd]=to_bin(res)

            elif funct3=='101' and funct7=='0100000':  #sra
                res=convert_bin_to_int(reg_data[rs1])>>(b & 31)
                reg_data[rd]=to_bin(res)

            elif funct3=='110':  #or
                reg_data[rd]=to_bin(a|b)

            elif funct3=='111':  #and
                reg_data[rd]=to_bin(a&b)

            pc+=4

        # i type
        elif instr_type=='I':
            imm=sign_extend(int(curr_instr[:12],2),12)

            rs1=curr_instr[12:17]
            funct3=curr_instr[17:20]
            rd=curr_instr[20:25]

            a=int(reg_data[rs1], 2)

            if opcode=='0010011':  #addi
                reg_data[rd]=to_bin(a + imm)
                pc+=4

            elif opcode=='0000011':  #lw
                addr=(a + imm) & 0xFFFFFFFF

                addr=addr-(addr%4)

                key=f"0x{addr:08X}"

                if key not in mem_data:
                    val=0
                else:
                    val=mem_data[key]

                reg_data[rd]=to_bin(val)

                pc+=4

            elif opcode=='1100111':  #jalr
                reg_data[rd]=to_bin(pc+4)

                pc=a+imm
                pc=pc & (~1)        #clearing the LSB
                pc=pc & 0xFFFFFFFF  #32-bit wrap

        # s type
        elif instr_type=='S':
            imm=sign_extend(int(curr_instr[:7]+curr_instr[20:25],2),12) #assigning the bit corresponding to the registers

            rs2=curr_instr[7:12] #bits for rs1 and rs2
            rs1=curr_instr[12:17]

            addr=(int(reg_data[rs1],2)+imm)&0xFFFFFFFF

            addr=addr-(addr%4)

            key=f"0x{addr:08X}"

            mem_data[key]=int(reg_data[rs2],2) # storing rs2 to memory

            pc+=4 # moving to next bit

        # b type
        elif instr_type=='B':
            imm_bits=curr_instr[0]+curr_instr[24]+curr_instr[1:7]+curr_instr[20:24]
            imm_bits= (
                curr_instr[0] +
                curr_instr[24] +
                curr_instr[1:7] +
                curr_instr[20:24]
                )

            imm_val=int(imm_bits + '0', 2)   
            imm_val=sign_extend(imm_val, 13) #extending to 13 bits
            
    
            rs2=curr_instr[7:12]
            rs1=curr_instr[12:17]
            funct3=curr_instr[17:20]

            if rs1=='00000' and rs2=='00000' and imm_val==0: #halt condition
                output+=f"0b{format(pc,'032b')} "
                for r in sorted(reg_data):
                    output+=f"0b{reg_data[r]} "   
                output+="\n"
                break

            if funct3=='000':  # beq
                pc = pc+imm_val if int(reg_data[rs1],2)==int(reg_data[rs2],2) else pc+4

            elif funct3=='001':  # bne
                pc=pc+imm_val if int(reg_data[rs1],2)!=int(reg_data[rs2],2) else pc+4

            elif funct3=='100':  # blt
                pc=pc+imm_val if convert_bin_to_int(reg_data[rs1])<convert_bin_to_int(reg_data[rs2]) else pc+4

            elif funct3=='101':  # bge
                pc=pc+imm_val if convert_bin_to_int(reg_data[rs1])>=convert_bin_to_int(reg_data[rs2]) else pc+4

            elif funct3=='110':  # bltu
                pc=pc+imm_val if int(reg_data[rs1], 2)<int(reg_data[rs2],2) else pc+4

            elif funct3=='111':  # bgeu
                pc=pc+imm_val if int(reg_data[rs1],2)>=int(reg_data[rs2],2) else pc+4

        # j type
        elif instr_type=='J':
            imm_bits=curr_instr[0] + curr_instr[12:20] + curr_instr[11] + curr_instr[1:11]
            imm_val=sign_extend(int(imm_bits, 2), 21) << 1 #extended

            rd=curr_instr[20:25] #saving return address

            reg_data[rd]=to_bin(pc+4)
            pc=pc+imm_val #jump to that value

        reg_data['00000']='0'*32  #make sure x0 is always zero

        output+=f"0b{format(pc & 0xFFFFFFFF, '032b')} "
        for r in sorted(reg_data):
            output+=f"0b{reg_data[r]} " #register output
        output += "\n"

    # memory storage
    for loc in range(MEM_START, MEM_END+1,4):
        loc_hex = f"0x{loc:08X}"
        output += f"{loc_hex}:0b{format(mem_data[loc_hex], '032b')}\n" 

    with open(output_file,"w") as f:
        f.write(output.strip())


# main
if __name__=="__main__":
    input_file=sys.argv[1]
    output_file=sys.argv[2]

    with open(input_file,"r") as f:
        instructions_list=f.readlines()

    execute_program(instructions_list, output_file)
