import sys

register_map={
    "zero":0,"ra":1,"sp":2,"gp":3,"tp":4,
    "t0":5,"t1":6,"t2":7,"s0":8,"fp":8,"s1":9,
    "a0":10,"a1":11,"a2":12,"a3":13,"a4":14,
    "a5":15,"a6":16,"a7":17,"s2":18,"s3":19,
    "s4":20,"s5":21,"s6":22,"s7":23,"s8":24,
    "s9":25,"s10":26,"s11":27,"t3":28,"t4":29,
    "t5":30,"t6":31
}

r_type={
    "add":("0110011","000","0000000"),
    "sub":("0110011","000","0100000"),
    "sll":("0110011","001","0000000"),
    "slt":("0110011","010","0000000"),
    "sltu":("0110011","011","0000000"),
    "xor":("0110011","100","0000000"),
    "srl":("0110011","101","0000000"),
    "or":("0110011","110","0000000"),
    "and":("0110011","111","0000000")
}

i_type={
    "lw":("0000011","010"),
    "addi":("0010011","000"),
    "sltiu":("0010011","011"),
    "jalr":("1100111","000")
}


s_type={"sw":("0100011","010")}


b_type={
    "beq":("1100011","000"),
    "bne":("1100011","001"),
    "blt":("1100011","100"),
    "bge":("1100011","101"),
    "bltu":("1100011","110"),
    "bgeu":("1100011","111")
}


u_type={"lui":"0110111","auipc":"0010111"}


j_type={"jal":"1101111"}


def twos_comp(val,bits):
    if val<0:
        val=(1<<bits)+val
    return format(val,f'0{bits}b')


def parse_register(reg):
    return register_map[reg]


def encode_r(op,rd,rs1,rs2):
    opcode,funct3,funct7=r_type[op]
    return (
        funct7+
        format(rs2,'05b')+
        format(rs1,'05b')+
        funct3+
        format(rd,'05b')+
        opcode
    )


def encode_i(op,rd,rs1,imm):
    opcode,funct3=i_type[op]
    imm_bin=twos_comp(imm,12)
    return (
        imm_bin+
        format(rs1,'05b')+
        funct3+
        format(rd,'05b')+
        opcode
    )


def encode_s(op,rs2,rs1,imm):
    opcode,funct3=s_type[op]
    imm_bin=twos_comp(imm,12)
    return (
        imm_bin[:7]+
        format(rs2,'05b')+
        format(rs1,'05b')+
        funct3+
        imm_bin[7:]+
        opcode
    )


def encode_b(op,rs1,rs2,offset):
    opcode,funct3=b_type[op]
    imm=twos_comp(offset>>1,12)
    return (
        imm[0]+
        imm[2:8]+
        format(rs2,'05b')+
        format(rs1,'05b')+
        funct3+
        imm[8:12]+
        imm[1]+
        opcode
    )


def encode_u(op,rd,imm):
    opcode=u_type[op]
    imm_bin=twos_comp(imm,20)
    return imm_bin+format(rd,'05b')+opcode


def encode_j(op,rd,offset):
    opcode=j_type[op]
    imm=twos_comp(offset>>1,20)
    return (
        imm[0]+
        imm[10:20]+
        imm[9]+
        imm[1:9]+
        format(rd,'05b')+
        opcode
    )


def assemble(input_file,output_file):
    with open(input_file) as f:
        lines=[l.strip() for l in f if l.strip()]

    labels={}
    pc=0

    # pass 1
    for line in lines:
        if ":" in line:
            label=line.split(":")[0]
            labels[label]=pc
            if line.split(":")[1].strip()=="":
                continue
        pc+=4

    pc=0
    output=[]

    for line in lines:

        if ":" in line:
            line=line.split(":")[1].strip()
            if not line:
                continue

        parts=line.replace(","," ").replace("("," ").replace(")"," ").split()
        op=parts[0]

        if op in r_type:
            rd=parse_register(parts[1])
            rs1=parse_register(parts[2])
            rs2=parse_register(parts[3])
            out=encode_r(op,rd,rs1,rs2)

        elif op in i_type:
            if op=="lw":
                rd=parse_register(parts[1])
                imm=int(parts[2])
                rs1=parse_register(parts[3])
            else:
                rd=parse_register(parts[1])
                rs1=parse_register(parts[2])
                imm=int(parts[3])
            out=encode_i(op,rd,rs1,imm)

        elif op in s_type:
            rs2=parse_register(parts[1])
            imm=int(parts[2])
            rs1=parse_register(parts[3])
            out=encode_s(op,rs2,rs1,imm)

        elif op in b_type:
            rs1 = parse_register(parts[1])
            rs2 = parse_register(parts[2])
            target = parts[3]

            # check if target is a number
            if target.lstrip("-").isdigit():
                offset = int(target)
            else:
                offset = labels[target] - pc

            out = encode_b(op, rs1, rs2, offset)

        elif op in u_type:
            rd=parse_register(parts[1])
            imm=int(parts[2])
            out=encode_u(op,rd,imm)

        elif op in j_type:
            rd=parse_register(parts[1])
            label=parts[2]
            offset=labels[label]-pc
            out=encode_j(op,rd,offset)

        else:
            raise ValueError("Unknown instruction")

        output.append(out)
        pc+=4

    with open(output_file,"w") as f:
        for line in output:
            f.write(line+"\n")


if __name__=="__main__":

    input_file=sys.argv[1]
    output_file=sys.argv[2]
    readable=sys.argv[3] if len(sys.argv)>3 else None

    assemble(input_file,output_file)
