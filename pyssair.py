# Copyright (c) 2025 Jifeng Wu
# Licensed under the Apache-2.0 License. See LICENSE file in the project root for full license information.
from collections import OrderedDict, deque
from dis import Instruction, get_instructions
from enum import Enum
from inspect import CO_VARARGS, CO_VARKEYWORDS
from itertools import chain
from types import CodeType
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Iterator

import networkx as nx
from put_back_iterator import PutBackIterator

EllipsisType = type(Ellipsis)
NoneType = type(None)


# IR Definition

# Base Classes
class IRInstruction(object): pass


class IRValue(object): pass


class IRBasicBlock(IRValue):
    def __init__(
            self,
            instructions,  # type: Sequence[IRInstruction]
    ):
        self.instructions = instructions  # type: Sequence[IRInstruction]


class IRRegion(IRValue):
    def __init__(
            self,
            name,  # type: str
            is_generator,  # type: bool
            posonlyargs,  # type: Sequence[str]
            args,  # type: Sequence[str]
            varargs,  # type: Optional[str]
            kwonlyargs,  # type: Sequence[str]
            varkeywords,  # type: Optional[str]
            basic_blocks,  # type: Sequence[IRBasicBlock]
    ):
        self.name = name  # type: str
        self.is_generator = is_generator  # type: bool
        self.posonlyargs = posonlyargs  # type: Sequence[str]
        self.args = args  # type: Sequence[str]
        self.varargs = varargs  # type: Optional[str]
        self.kwonlyargs = kwonlyargs  # type: Sequence[str]
        self.varkeywords = varkeywords  # type: Optional[str]
        self.basic_blocks = basic_blocks  # type: Sequence[IRBasicBlock]

    def iterate_child_regions(self, recursive=False):
        # type: (...) -> Iterator[Tuple[List[str], IRRegion]]
        path = [self.name]
        yield path, self
        for basic_block in self.basic_blocks:
            for instruction in basic_block.instructions:
                if isinstance(instruction, IRLoadChildRegion):
                    if recursive:
                        for child_region_path, child_region in instruction.child_region.iterate_child_regions(
                                recursive=recursive,
                        ):
                            yield path + child_region_path, child_region
                    else:
                        yield path + [instruction.child_region.name], instruction.child_region


# NOPs
'COPY_FREE_VARS'
'EXTENDED_ARG'
'NOP'
'RESUME'

# Stack Manipulation
'COPY'
'END_FOR'
'POP_TOP'
'SWAP'

# Interpreter State Manipulation
'KW_NAMES'
'RETURN_GENERATOR'

# Constants
'LOAD_ASSERTION_ERROR'
'LOAD_BUILD_CLASS'
'LOAD_CONST'
'PUSH_NULL'


class IRConstant(IRInstruction, IRValue):
    def __init__(self, value):
        self.value = value


class IRLoadChildRegion(IRInstruction, IRValue):
    def __init__(
            self,
            child_region,  # type: IRRegion
    ):
        self.child_region = child_region  # type: IRRegion


# Names
'LOAD_NAME'
'LOAD_CLOSURE'
'LOAD_FAST'
'LOAD_FAST_AND_CLEAR'
'LOAD_FAST_CHECK'
'LOAD_GLOBAL'
'STORE_NAME'
'STORE_FAST'
'STORE_GLOBAL'
'DELETE_NAME'
'DELETE_FAST'


class IRLoadName(IRInstruction, IRValue):
    def __init__(
            self,
            name,  # type: str
    ):
        self.name = name  # type: str


class IRLoadGlobal(IRInstruction, IRValue):
    def __init__(
            self,
            name,  # type: str
    ):
        self.name = name  # type: str


class IRStoreName(IRInstruction):
    def __init__(
            self,
            name,  # type: str
            value,  # type: IRValue
    ):
        self.name = name  # type: str
        self.value = value  # type: IRValue


class IRStoreGlobal(IRInstruction):
    def __init__(
            self,
            name,  # type: str
            value,  # type: IRValue
    ):
        self.name = name  # type: str
        self.value = value  # type: IRValue


class IRDeleteName(IRInstruction):
    def __init__(
            self,
            name,  # type: str
    ):
        self.name = name  # type: str


# Cells
'MAKE_CELL'
'LOAD_DEREF'
'STORE_DEREF'


class IRMakeCell(IRInstruction):
    def __init__(
            self,
            name,  # type: str
    ):
        self.name = name  # type: str


class IRLoadDeref(IRInstruction, IRValue):
    def __init__(
            self,
            name,  # type: str
    ):
        self.name = name  # type: str


class IRStoreDeref(IRInstruction):
    def __init__(
            self,
            name,  # type: str
            value,  # type: IRValue
    ):
        self.name = name  # type: str
        self.value = value  # type: IRValue


# Imports
'IMPORT_NAME'
'IMPORT_FROM'


class IRImportModule(IRInstruction, IRValue):
    def __init__(
            self,
            name,  # type: str
            level,  # type: int
            return_top_level_package,  # type: bool
    ):
        self.name = name  # type: str
        self.level = level  # type: int
        self.return_top_level_package = return_top_level_package  # type: bool


class IRImportFrom(IRInstruction, IRValue):
    def __init__(
            self,
            module,  # type: IRImportModule
            name,  # type: str
    ):
        self.module = module  # type: IRImportModule
        self.name = name  # type: str


# Unary Operations
'UNARY_INVERT'
'UNARY_NEGATIVE'
'UNARY_NOT'


class IRUnaryOperator(Enum):
    INVERT = '~'
    NOT = 'not'
    UNARY_ADD = '+'
    UNARY_SUB = '-'


class IRUnaryOp(IRInstruction, IRValue):
    def __init__(
            self,
            op,  # type: IRUnaryOperator
            operand,  # type: IRValue
    ):
        self.op = op  # type: IRUnaryOperator
        self.operand = operand  # type: IRValue


# Binary Operations
'BINARY_OP'
'COMPARE_OP'
'CONTAINS_OP'
'IS_OP'


class IRBinaryOperator(Enum):
    ADD = '+'
    BITWISE_AND = '&'
    FLOOR_DIV = '//'
    LSHIFT = '<<'
    MAT_MULT = '@'
    MULT = '*'
    MOD = '%'
    BITWISE_OR = '|'
    POW = '**'
    RSHIFT = '>>'
    SUB = '-'
    DIV = '/'
    BITWISE_XOR = '^'
    EQ = '=='
    NOT_EQ = '!='
    LT = '<'
    LE = '<='
    GT = '>'
    GE = '>='
    IS = 'is'
    IS_NOT = 'is not'
    IN = 'in'
    NOT_IN = 'not in'


ARGVAL_TO_IR_BINARY_OPERATORS = {
    0: IRBinaryOperator.ADD,
    1: IRBinaryOperator.BITWISE_AND,
    2: IRBinaryOperator.FLOOR_DIV,
    3: IRBinaryOperator.LSHIFT,
    4: IRBinaryOperator.MAT_MULT,
    5: IRBinaryOperator.MULT,
    6: IRBinaryOperator.MOD,
    7: IRBinaryOperator.BITWISE_OR,
    8: IRBinaryOperator.POW,
    9: IRBinaryOperator.RSHIFT,
    10: IRBinaryOperator.SUB,
    11: IRBinaryOperator.DIV,
    12: IRBinaryOperator.BITWISE_XOR,
    '==': IRBinaryOperator.EQ,
    '!=': IRBinaryOperator.NOT_EQ,
    '<': IRBinaryOperator.LT,
    '<=': IRBinaryOperator.LE,
    '>': IRBinaryOperator.GT,
    '>=': IRBinaryOperator.GE,
}

ARGVAL_TO_IR_INPLACE_BINARY_OPERATORS = {
    13: IRBinaryOperator.ADD,
    14: IRBinaryOperator.BITWISE_AND,
    15: IRBinaryOperator.FLOOR_DIV,
    16: IRBinaryOperator.LSHIFT,
    17: IRBinaryOperator.MAT_MULT,
    18: IRBinaryOperator.MULT,
    19: IRBinaryOperator.MOD,
    20: IRBinaryOperator.BITWISE_OR,
    21: IRBinaryOperator.POW,
    22: IRBinaryOperator.RSHIFT,
    23: IRBinaryOperator.SUB,
    24: IRBinaryOperator.DIV,
    25: IRBinaryOperator.BITWISE_XOR,
}


class IRBinaryOp(IRInstruction, IRValue):
    def __init__(
            self,
            left,  # type: IRValue
            op,  # type: IRBinaryOperator
            right,  # type: IRValue
    ):
        self.left = left  # type: IRValue
        self.op = op  # type: IRBinaryOperator
        self.right = right  # type: IRValue


class IRInPlaceBinaryOp(IRInstruction):
    def __init__(
            self,
            target,  # type: IRValue
            op,  # type: IRBinaryOperator
            value,  # type: IRValue
    ):
        self.target = target  # type: IRValue
        self.op = op  # type: IRBinaryOperator
        self.value = value  # type: IRValue


# String Formatting
'FORMAT_VALUE'
'BUILD_STRING'


class IRFormatValue(IRInstruction, IRValue):
    def __init__(
            self,
            value,  # type: IRValue
            format_spec,  # type: IRValue
    ):
        self.value = value  # type: IRValue
        self.format_spec = format_spec  # type: IRValue


class IRBuildString(IRInstruction, IRValue):
    def __init__(
            self,
            values,  # type: Sequence[IRValue]
    ):
        self.values = values  # type: Sequence[IRValue]


# Building Containers
'BUILD_LIST'
'BUILD_MAP'
'BUILD_CONST_KEY_MAP'
'BUILD_SET'
'BUILD_TUPLE'


class IRBuildList(IRInstruction, IRValue):
    def __init__(
            self,
            elts,  # type: Sequence[IRValue]
    ):
        self.elts = elts  # type: Sequence[IRValue]


class IRBuildMap(IRInstruction, IRValue):
    def __init__(
            self,
            keys,  # type: Sequence[IRValue]
            values,  # type: Sequence[IRValue]
    ):
        self.keys = keys  # type: Sequence[IRValue]
        self.values = values  # type: Sequence[IRValue]


class IRBuildSet(IRInstruction, IRValue):
    def __init__(
            self,
            elts,  # type: Sequence[IRValue]
    ):
        self.elts = elts  # type: Sequence[IRValue]


class IRBuildTuple(IRInstruction, IRValue):
    def __init__(
            self,
            elts,  # type: Sequence[IRValue]
    ):
        self.elts = elts  # type: Sequence[IRValue]


# Subscribing and Slicing
'BINARY_SUBSCR'
'STORE_SUBSCR'
'DELETE_SUBSCR'
'BUILD_SLICE'
'BINARY_SLICE'
'STORE_SLICE'


class IRLoadSubscr(IRInstruction, IRValue):
    def __init__(
            self,
            container,  # type: IRValue
            key,  # type: IRValue
    ):
        self.container = container  # type: IRValue
        self.key = key  # type: IRValue


class IRStoreSubscr(IRInstruction):
    def __init__(
            self,
            container,  # type: IRValue
            key,  # type: IRValue
            value,  # type: IRValue
    ):
        self.container = container  # type: IRValue
        self.key = key  # type: IRValue
        self.value = value  # type: IRValue


class IRDeleteSubscr(IRInstruction):
    def __init__(
            self,
            container,  # type: IRValue
            key,  # type: IRValue
    ):
        self.container = container  # type: IRValue
        self.key = key  # type: IRValue


class IRBuildSlice(IRInstruction, IRValue):
    def __init__(
            self,
            start,  # type: IRValue
            stop,  # type: IRValue
            step,  # type: IRValue
    ):
        self.start = start  # type: IRValue
        self.stop = stop  # type: IRValue
        self.step = step  # type: IRValue


# Manipulating Containers
'LIST_APPEND'
'LIST_EXTEND'
'MAP_ADD'
'DICT_UPDATE'
'DICT_MERGE'
'SET_ADD'
'SET_UPDATE'

# Unpacking Containers
'UNPACK_SEQUENCE'
'UNPACK_EX'


class IRUnpackSequence(IRInstruction, IRValue):
    def __init__(
            self,
            sequence,  # type: IRValue
            size,  # type: int
    ):
        self.sequence = sequence  # type: IRValue
        self.size = size  # type: int


class IRUnpackEx(IRInstruction, IRValue):
    def __init__(
            self,
            sequence,  # type: IRValue
            leading,  # type: int
            trailing,  # type: int
    ):
        self.sequence = sequence  # type: IRValue
        self.leading = leading  # type: int
        self.trailing = trailing  # type: int


# Attributes
'LOAD_ATTR'
'LOAD_SUPER_ATTR'
'STORE_ATTR'
'DELETE_ATTR'


class IRLoadAttr(IRInstruction, IRValue):
    def __init__(
            self,
            obj,  # type: IRValue
            attr,  # type: str
    ):
        self.obj = obj  # type: IRValue
        self.attr = attr  # type: str


class IRLoadSuperAttr(IRInstruction, IRValue):
    def __init__(
            self,
            cls_obj,  # type: IRValue
            self_obj,  # type: IRValue
            attr,  # type: str
    ):
        self.cls_obj = cls_obj  # type: IRValue
        self.self_obj = self_obj  # type: IRValue
        self.attr = attr  # type: str


class IRStoreAttr(IRInstruction):
    def __init__(
            self,
            obj,  # type: IRValue
            attr,  # type: str
            value,  # type: IRValue
    ):
        self.obj = obj  # type: IRValue
        self.attr = attr  # type: str
        self.value = value  # type: IRValue


class IRDeleteAttr(IRInstruction):
    def __init__(
            self,
            obj,  # type: IRValue
            attr,  # type: str
    ):
        self.obj = obj  # type: IRValue
        self.attr = attr  # type: str


# Function Calling
'CALL'
'CALL_FUNCTION_EX'
'CALL_INTRINSIC_1'


class IRCall(IRInstruction, IRValue):
    def __init__(
            self,
            func,  # type: IRValue
            args,  # type: Sequence[IRValue]
            keywords,  # type: Mapping[str, IRValue]
    ):
        self.func = func  # type: IRValue
        self.args = args  # type: Sequence[IRValue]
        self.keywords = keywords  # type: Mapping[str, IRValue]


class IRCallFunctionEx(IRInstruction, IRValue):
    def __init__(
            self,
            func,  # type: IRValue
            args,  # type: IRValue
            keywords,  # type: IRValue
    ):
        self.func = func  # type: IRValue
        self.args = args  # type: IRValue
        self.keywords = keywords  # type: IRValue


# Iterators
'GET_ITER'
'FOR_ITER'
'END_FOR'


class IRGetIter(IRInstruction, IRValue):
    def __init__(
            self,
            value,  # type: IRValue
    ):
        self.value = value  # type: IRValue


class IRForIter(IRInstruction, IRValue):
    def __init__(
            self,
            iter,  # type: IRValue
            target,  # type: IRBasicBlock
    ):
        self.iter = iter  # type: IRValue
        self.target = target  # type: IRBasicBlock


# Branching

'POP_JUMP_IF_TRUE'
'POP_JUMP_IF_FALSE'
'POP_JUMP_IF_NONE'
'POP_JUMP_IF_NOT_NONE'


class IRBranch(IRInstruction):
    def __init__(
            self,
            condition,  # type: IRValue
            target,  # type: IRBasicBlock
    ):
        self.condition = condition  # type: IRValue
        self.target = target  # type: IRBasicBlock


# Jumping
'JUMP_BACKWARD'
'JUMP_FORWARD'


class IRJump(IRInstruction):
    def __init__(
            self,
            target,  # type: IRBasicBlock
    ):
        self.target = target  # type: IRBasicBlock


# With Statements
'BEFORE_WITH'
# Building Functions
'MAKE_FUNCTION'
'SETUP_ANNOTATIONS'


class IRBuildFunction(IRInstruction, IRValue):
    def __init__(
            self,
            load_child_region,  # type: IRLoadChildRegion
            parameter_default_values,  # type: IRBuildTuple
            keyword_only_parameter_default_values,  # type: IRBuildMap
            free_variable_cells,  # type: IRValue
            annotations,  # type: Mapping[str, IRValue]
    ):
        self.load_child_region = load_child_region  # type: IRLoadChildRegion
        self.parameter_default_values = parameter_default_values  # type: IRBuildTuple
        self.keyword_only_parameter_default_values = keyword_only_parameter_default_values  # type: IRBuildMap
        self.free_variable_cells = free_variable_cells  # type: IRValue
        self.annotations = annotations  # type: Mapping[str, IRValue]


# Returning
'RETURN_CONST'
'RETURN_VALUE'


class IRReturn(IRInstruction):
    def __init__(
            self,
            value,  # type: IRValue
    ):
        self.value = value  # type: IRValue


# Yielding
'RETURN_GENERATOR'
'YIELD_VALUE'


class IRYield(IRInstruction, IRValue):
    def __init__(
            self,
            value,  # type: IRValue
    ):
        self.value = value  # type: IRValue


# Exceptions
'RAISE_VARARGS'
'RERAISE'


class IRRaise(IRInstruction):
    def __init__(
            self,
            exc,  # type: IRValue
    ):
        self.exc = exc  # type: IRValue


# IR Building


OPNAMES_WITH_KNOWN_CONTROL_FLOW_SEMANTICS = {
    # NOPs
    'COPY_FREE_VARS',
    'EXTENDED_ARG',
    'NOP',
    'RESUME',
    # Stack Manipulation
    'COPY',
    'POP_TOP',
    'SWAP',
    # Interpreter State Manipulation
    'KW_NAMES',
    # Constants
    'LOAD_ASSERTION_ERROR',
    'LOAD_BUILD_CLASS',
    'LOAD_CONST',
    'PUSH_NULL',
    # Names
    'LOAD_NAME',
    'LOAD_CLOSURE',
    'LOAD_FAST',
    'LOAD_FAST_AND_CLEAR',
    'LOAD_FAST_CHECK',
    'LOAD_GLOBAL',
    'STORE_NAME',
    'STORE_FAST',
    'STORE_GLOBAL',
    'DELETE_NAME',
    'DELETE_FAST',
    # Cells
    'MAKE_CELL',
    'LOAD_DEREF',
    'STORE_DEREF',
    # Imports
    'IMPORT_NAME',
    'IMPORT_FROM',
    # Unary Operations
    'UNARY_INVERT',
    'UNARY_NEGATIVE',
    'UNARY_NOT',
    # Binary Operations
    'BINARY_OP',
    'COMPARE_OP',
    'CONTAINS_OP',
    'IS_OP',
    # String Formatting
    'FORMAT_VALUE',
    'BUILD_STRING',
    # Building Containers
    'BUILD_LIST',
    'BUILD_MAP',
    'BUILD_CONST_KEY_MAP',
    'BUILD_SET',
    'BUILD_TUPLE',
    # Subscribing and Slicing
    'BINARY_SUBSCR',
    'STORE_SUBSCR',
    'DELETE_SUBSCR',
    'BUILD_SLICE',
    'BINARY_SLICE',
    'STORE_SLICE',
    # Manipulating Containers
    'LIST_APPEND',
    'LIST_EXTEND',
    'MAP_ADD',
    'DICT_UPDATE',
    'DICT_MERGE',
    'SET_ADD',
    'SET_UPDATE',
    # Unpacking Containers
    'UNPACK_SEQUENCE',
    'UNPACK_EX',
    # Attributes
    'LOAD_ATTR',
    'LOAD_SUPER_ATTR',
    'STORE_ATTR',
    'DELETE_ATTR',
    # Function Calling
    'CALL',
    'CALL_FUNCTION_EX',
    'CALL_INTRINSIC_1',
    # For Loops
    'GET_ITER',
    'FOR_ITER',
    'END_FOR',
    # Branching
    'POP_JUMP_IF_TRUE',
    'POP_JUMP_IF_FALSE',
    'POP_JUMP_IF_NONE',
    'POP_JUMP_IF_NOT_NONE',
    # Jumping
    'JUMP_BACKWARD',
    'JUMP_FORWARD',
    # With Statements
    'BEFORE_WITH',
    'WITH_EXCEPT_START',
    # Building Functions
    'MAKE_FUNCTION',
    'SETUP_ANNOTATIONS',
    # Returning
    'RETURN_CONST',
    'RETURN_VALUE',
    # Yielding
    'RETURN_GENERATOR',
    'YIELD_VALUE',
    # Exceptions
    # Exception handling is not supported in the IR
    'RAISE_VARARGS',
    'RERAISE',
    'CHECK_EXC_MATCH',
    'POP_EXCEPT',
    'PUSH_EXC_INFO',
}

BRANCHING_OPNAMES = {
    # Branching
    'FOR_ITER',
    'POP_JUMP_IF_TRUE',
    'POP_JUMP_IF_FALSE',
    'POP_JUMP_IF_NONE',
    'POP_JUMP_IF_NOT_NONE',
}

JUMPING_OPNAMES = {
    # Jumping
    'JUMP_BACKWARD',
    'JUMP_FORWARD',
}

YIELDING_OPNAMES = {
    # Yielding
    'YIELD_VALUE',
}

TERMINATING_OPNAMES = {
    # Branching
    'FOR_ITER',
    'POP_JUMP_IF_TRUE',
    'POP_JUMP_IF_FALSE',
    'POP_JUMP_IF_NONE',
    'POP_JUMP_IF_NOT_NONE',
    # Jumping
    'JUMP_BACKWARD',
    'JUMP_FORWARD',
    # Returning
    'RETURN_CONST',
    'RETURN_VALUE',
    # Yielding
    'YIELD_VALUE',
    # Exceptions
    'RAISE_VARARGS',
    'RERAISE',
}


class UnexpectedError(Exception): pass


def build_region(
        code,  # type: CodeType
):
    # type: (...) -> IRRegion
    name = code.co_name
    posonlyargcount = code.co_posonlyargcount
    argcount = code.co_argcount

    if code.co_flags & CO_VARARGS:
        varargscount = 1
    else:
        varargscount = 0

    kwonlyargcount = code.co_kwonlyargcount

    if code.co_flags & CO_VARKEYWORDS:
        varkeywordscount = 1
    else:
        varkeywordscount = 0

    count = posonlyargcount + argcount + varargscount + kwonlyargcount + varkeywordscount
    all_arguments = deque(code.co_varnames[:count])

    posonlyargs = tuple(all_arguments.popleft() for _ in range(posonlyargcount))
    args = tuple(all_arguments.popleft() for _ in range(argcount))

    if varargscount:
        varargs = all_arguments.popleft()
    else:
        varargs = None

    kwonlyargs = tuple(all_arguments.popleft() for _ in range(kwonlyargcount))

    if varkeywordscount:
        varkeywords = all_arguments.popleft()
    else:
        varkeywords = None

    bytecode_instructions = get_instructions(code)
    offsets_to_bytecode_basic_blocks, is_generator, cfg = partition_bytecode_basic_blocks(bytecode_instructions)

    # Translate bytecode instructions in each bytecode basic block
    stack = ()  # type: Sequence[IRValue]
    offsets_to_ir_basic_blocks = {}  # type: Dict[int, IRBasicBlock]
    offsets_to_final_stacks = {}  # type: Dict[int, Sequence[IRValue]]

    for offset in offsets_to_bytecode_basic_blocks:
        stack = build_basic_block(
            offsets_to_bytecode_basic_blocks=offsets_to_bytecode_basic_blocks,
            offset=offset,
            initial_stack=stack,
            offsets_to_ir_basic_blocks=offsets_to_ir_basic_blocks,
            offsets_to_final_stacks=offsets_to_final_stacks,
        )

    if stack:
        raise UnexpectedError('stack not empty after translating bytecode instructions in each bytecode basic block')

    return IRRegion(
        name=name,
        is_generator=is_generator,
        posonlyargs=posonlyargs,
        args=args,
        varargs=varargs,
        kwonlyargs=kwonlyargs,
        varkeywords=varkeywords,
        # Ensure the basic blocks are in the correct order
        basic_blocks=tuple(offsets_to_ir_basic_blocks[offset] for offset in offsets_to_bytecode_basic_blocks.keys()),
    )


def partition_bytecode_basic_blocks(
        bytecode_instructions,  # type: Iterable[Instruction]
):
    # type: (...) -> Tuple[Mapping[int, Sequence[Instruction]], bool, nx.DiGraph]
    """
    Partition bytecode instructions into bytecode basic blocks, keyed by their offsets.
    Each basic block is a list of bytecode instructions.
    """
    offsets_to_bytecode_basic_blocks = OrderedDict()
    is_generator = False
    cfg = nx.DiGraph()

    bytecode_instruction_iterator = PutBackIterator(bytecode_instructions)

    # Initialize current_basic_block and associate with the offset of the peeked first instruction
    current_basic_block = []
    if bytecode_instruction_iterator.has_next():
        first_stack_instruction = next(bytecode_instruction_iterator)
        first_offset = first_stack_instruction.offset
        offsets_to_bytecode_basic_blocks[first_offset] = current_basic_block
        bytecode_instruction_iterator.put_back(first_stack_instruction)

        # Iterate through all stack instructions
        for stack_instruction in bytecode_instruction_iterator:
            opname = stack_instruction.opname
            argval = stack_instruction.argval
            is_jump_target = stack_instruction.is_jump_target
            offset = stack_instruction.offset

            # Do we know the control flow semantics of the opname?
            if opname not in OPNAMES_WITH_KNOWN_CONTROL_FLOW_SEMANTICS:
                raise NotImplementedError('opname with unknown control flow semantics: %s' % (opname,))

            # Are we at the start of a new basic block?
            # In that case, reset current_basic_block
            if is_jump_target:
                if offset not in offsets_to_bytecode_basic_blocks:
                    offsets_to_bytecode_basic_blocks[offset] = []

                current_basic_block = offsets_to_bytecode_basic_blocks[offset]

            # Add the current instruction to current_basic_block
            # The next instruction should be the start of a new basic block
            # Peek the next instruction and check
            # Reset current_basic_block if not
            if opname in TERMINATING_OPNAMES:
                current_basic_block.append(stack_instruction)

                if bytecode_instruction_iterator.has_next():
                    next_instruction = next(bytecode_instruction_iterator)
                    if not next_instruction.is_jump_target:
                        offsets_to_bytecode_basic_blocks[next_instruction.offset] = current_basic_block = []
                    bytecode_instruction_iterator.put_back(next_instruction)
            # RETURN_GENERATOR, POP_TOP are the first two instructions of a generator
            # In this case, skip them
            elif opname == 'RETURN_GENERATOR':
                is_generator = True

                if bytecode_instruction_iterator.has_next() and next(bytecode_instruction_iterator).opname == 'POP_TOP':
                    continue

                raise UnexpectedError('RETURN_GENERATOR not followed by POP_TOP')
            # consecutive CALL_INTRINSIC_1(3), RERAISE in a generator
            # In this case, skip them
            elif is_generator and opname == 'CALL_INTRINSIC_1' and argval == 3:
                if bytecode_instruction_iterator.has_next() and next(bytecode_instruction_iterator).opname == 'RERAISE':
                    continue

                raise UnexpectedError('CALL_INTRINSIC_1(3) not followed by RERAISE in a generator')
            else:
                current_basic_block.append(stack_instruction)

        # Analyze CFG
        offset_iterator = PutBackIterator(offsets_to_bytecode_basic_blocks)
        for offset in offset_iterator:
            cfg.add_node(offset)

            basic_block = offsets_to_bytecode_basic_blocks[offset]
            if basic_block:
                last_bytecode_instruction_index = len(basic_block) - 1

                for i in range(last_bytecode_instruction_index):
                    if basic_block[i].opname in TERMINATING_OPNAMES:
                        raise UnexpectedError(
                            'basic block %d contains terminating opname in the middle' % (offset,)
                        )

                last_bytecode_instruction = basic_block[last_bytecode_instruction_index]
                last_bytecode_instruction_opname = last_bytecode_instruction.opname
                last_bytecode_instruction_argval = last_bytecode_instruction.argval

                if last_bytecode_instruction_opname not in TERMINATING_OPNAMES:
                    if not offset_iterator.has_next():
                        raise UnexpectedError(
                            'last basic block %d cannot terminate with a non-terminating opname' % (offset,)
                        )
                    else:
                        next_offset = next(offset_iterator)
                        cfg.add_edge(offset, next_offset)
                        offset_iterator.put_back(next_offset)
                elif last_bytecode_instruction_opname in BRANCHING_OPNAMES:
                    if not offset_iterator.has_next():
                        raise UnexpectedError(
                            'last basic block %d cannot terminate with a branching opname' % (offset,)
                        )
                    else:
                        cfg.add_edge(offset, last_bytecode_instruction_argval)
                        next_offset = next(offset_iterator)
                        cfg.add_edge(offset, next_offset)
                        offset_iterator.put_back(next_offset)
                elif last_bytecode_instruction_opname in YIELDING_OPNAMES:
                    if not offset_iterator.has_next():
                        raise UnexpectedError(
                            'last basic block %d cannot terminate with a suspending opname' % (offset,)
                        )
                    else:
                        next_offset = next(offset_iterator)
                        cfg.add_edge(offset, next_offset)
                        offset_iterator.put_back(next_offset)
                elif last_bytecode_instruction_opname in JUMPING_OPNAMES:
                    cfg.add_edge(offset, last_bytecode_instruction_argval)
            else:
                if offset_iterator.has_next():
                    next_offset = next(offset_iterator)
                    cfg.add_edge(offset, next_offset)
                    offset_iterator.put_back(next_offset)

        # Trim basic blocks based on CFG
        reachable_offsets = nx.descendants(cfg, first_offset) | {first_offset}
        non_reachable_offsets = set(offsets_to_bytecode_basic_blocks) - reachable_offsets
        for non_reachable_offset in non_reachable_offsets:
            del offsets_to_bytecode_basic_blocks[non_reachable_offset]
            cfg.remove_node(non_reachable_offset)

    return offsets_to_bytecode_basic_blocks, is_generator, cfg


def build_basic_block(
        # Read-only parameters
        offsets_to_bytecode_basic_blocks,  # type: Mapping[int, Sequence[Instruction]]
        offset,  # type: int
        initial_stack,  # type: Sequence[IRValue]
        # Read-write parameters
        offsets_to_ir_basic_blocks,  # type: Dict[int, IRBasicBlock]
        offsets_to_final_stacks,  # type: Dict[int, Sequence[IRValue]]
):
    # type: (...) -> Sequence[IRValue]
    if offset in offsets_to_final_stacks:
        return offsets_to_final_stacks[offset]
    else:
        stack = list(initial_stack)
        instructions = []

        # Used before CALL
        kw_names = None

        for stack_instruction in offsets_to_bytecode_basic_blocks[offset]:
            opname = stack_instruction.opname
            argval = stack_instruction.argval
            arg = stack_instruction.arg

            # NOPs
            if opname in ('COPY_FREE_VARS', 'EXTENDED_ARG', 'NOP', 'RESUME'):
                pass
            # Stack Manipulation
            elif opname == 'COPY':
                stack.append(stack[-argval])
            elif opname == 'POP_TOP':
                stack.pop()
            elif opname == 'SWAP':
                stack[-argval], stack[-1] = stack[-1], stack[-argval]
            # Interpreter State Manipulation
            elif opname == 'KW_NAMES':
                kw_names = argval
            # Constants
            elif opname == 'LOAD_ASSERTION_ERROR':
                instruction = IRConstant(value=AssertionError)
                instructions.append(instruction)
                stack.append(instruction)
            elif opname == 'LOAD_BUILD_CLASS':
                instruction = IRConstant(value=__build_class__)
                instructions.append(instruction)
                stack.append(instruction)
            elif opname == 'LOAD_CONST':
                if isinstance(argval, CodeType):
                    # Compile the bytecode into a separate region
                    region = build_region(code=argval)
                    instruction = IRLoadChildRegion(child_region=region)
                    instructions.append(instruction)
                    stack.append(instruction)
                else:
                    instruction = IRConstant(argval)
                    instructions.append(instruction)
                    stack.append(instruction)
            elif opname == 'PUSH_NULL':
                stack.append(IRConstant(value=None))
            # Names
            elif opname in (
                    'LOAD_NAME',
                    'LOAD_CLOSURE',
                    'LOAD_FAST',
                    'LOAD_FAST_AND_CLEAR',
                    'LOAD_FAST_CHECK',
            ):
                instruction = IRLoadName(argval)
                instructions.append(instruction)
                stack.append(instruction)
            elif opname == 'LOAD_GLOBAL':
                instruction = IRLoadGlobal(argval)
                instructions.append(instruction)
                if arg & 0b1:
                    stack.append(IRConstant(value=None))
                stack.append(instruction)
            elif opname in ('STORE_NAME', 'STORE_FAST'):
                value = stack.pop()
                instruction = IRStoreName(name=argval, value=value)
                instructions.append(instruction)
            elif opname == 'STORE_GLOBAL':
                value = stack.pop()
                instruction = IRStoreGlobal(name=argval, value=value)
                instructions.append(instruction)
            elif opname in ('DELETE_NAME', 'DELETE_FAST'):
                instruction = IRDeleteName(name=argval)
                instructions.append(instruction)
            # Cells
            elif opname == 'MAKE_CELL':
                instruction = IRMakeCell(name=argval)
                instructions.append(instruction)
            elif opname == 'LOAD_DEREF':
                instruction = IRLoadDeref(argval)
                instructions.append(instruction)
                stack.append(instruction)
            elif opname == 'STORE_DEREF':
                value = stack.pop()
                instruction = IRStoreDeref(name=argval, value=value)
                instructions.append(instruction)

            # Imports
            elif opname == 'IMPORT_NAME':
                fromlist = stack.pop()
                level = stack.pop()

                if not isinstance(level, IRConstant) or not isinstance(level.value, int):
                    raise UnexpectedError('cannot handle this IMPORT_NAME: %s' % (stack_instruction,))

                if isinstance(fromlist, IRConstant) and isinstance(fromlist.value, tuple) and len(fromlist.value):
                    name = argval
                    return_top_level_package = False
                elif isinstance(fromlist, IRConstant) and isinstance(fromlist.value, NoneType) and not level.value:
                    name = argval
                    return_top_level_package = True
                else:
                    raise UnexpectedError('cannot handle this IMPORT_NAME: %s' % (stack_instruction,))

                instruction = IRImportModule(name=name, level=level.value,
                                             return_top_level_package=return_top_level_package)
                instructions.append(instruction)

                stack.append(instruction)
            elif opname == 'IMPORT_FROM':
                module = stack[-1]
                if not isinstance(module, IRImportModule):
                    raise UnexpectedError('cannot handle this IMPORT_FROM: %s' % (stack_instruction,))
                instruction = IRImportFrom(module, argval)
                instructions.append(instruction)

                stack.append(instruction)
            # Unary Operations
            elif opname == 'UNARY_INVERT':
                value = stack.pop()
                instruction = IRUnaryOp(op=IRUnaryOperator.INVERT, operand=value)
                instructions.append(instruction)
                stack.append(instruction)
            elif opname == 'UNARY_NEGATIVE':
                value = stack.pop()
                instruction = IRUnaryOp(op=IRUnaryOperator.UNARY_SUB, operand=value)
                instructions.append(instruction)
                stack.append(instruction)
            elif opname == 'UNARY_NOT':
                value = stack.pop()
                instruction = IRUnaryOp(op=IRUnaryOperator.NOT, operand=value)
                instructions.append(instruction)
                stack.append(instruction)
            # Binary Operations
            elif opname in ('BINARY_OP', 'COMPARE_OP'):
                rhs = stack.pop()
                lhs = stack.pop()
                if argval in ARGVAL_TO_IR_BINARY_OPERATORS:
                    op = ARGVAL_TO_IR_BINARY_OPERATORS[argval]
                    instruction = IRBinaryOp(lhs, op, rhs)
                    instructions.append(instruction)

                    stack.append(instruction)
                elif argval in ARGVAL_TO_IR_INPLACE_BINARY_OPERATORS:
                    op = ARGVAL_TO_IR_INPLACE_BINARY_OPERATORS[argval]
                    instruction = IRInPlaceBinaryOp(lhs, op, rhs)
                    instructions.append(instruction)

                    stack.append(lhs)
                else:
                    raise UnexpectedError('unknown BINARY_OP: %s' % (stack_instruction,))
            elif opname == 'CONTAINS_OP':
                if argval:
                    op = IRBinaryOperator.NOT_IN
                else:
                    op = IRBinaryOperator.IN
                rhs = stack.pop()
                lhs = stack.pop()
                instruction = IRBinaryOp(left=lhs, op=op, right=rhs)
                instructions.append(instruction)
                stack.append(instruction)
            elif opname == 'IS_OP':
                if argval:
                    op = IRBinaryOperator.IS_NOT
                else:
                    op = IRBinaryOperator.IS
                rhs = stack.pop()
                lhs = stack.pop()
                instruction = IRBinaryOp(left=lhs, op=op, right=rhs)
                instructions.append(instruction)
                stack.append(instruction)
            # String Formatting
            elif opname == 'FORMAT_VALUE':
                if (arg & 0x04) == 0x04:
                    format_spec = stack.pop()
                else:
                    format_spec = IRConstant(None)
                    instructions.append(format_spec)

                value = stack.pop()

                if (arg & 0x03) == 0x01:
                    # call str() on value before formatting it
                    loaded_str = IRConstant(value=str)
                    instructions.append(loaded_str)

                    modified_value = IRCall(func=loaded_str, args=(value,), keywords={})
                    instructions.append(modified_value)
                elif (arg & 0x03) == 0x02:
                    # call repr() on value before formatting it
                    loaded_repr = IRConstant(value=repr)
                    instructions.append(loaded_repr)

                    modified_value = IRCall(func=loaded_repr, args=(value,), keywords={})
                    instructions.append(modified_value)
                elif (arg & 0x03) == 0x03:
                    # call ascii() on value before formatting it
                    loaded_ascii = IRConstant(value=ascii)
                    instructions.append(loaded_ascii)

                    modified_value = IRCall(func=loaded_ascii, args=(value,), keywords={})
                    instructions.append(modified_value)
                else:
                    modified_value = value

                instruction = IRFormatValue(value=modified_value, format_spec=format_spec)
                instructions.append(instruction)

                stack.append(instruction)
            elif opname == 'BUILD_STRING':
                strings = tuple(stack[-argval:])
                for _ in range(argval):
                    stack.pop()

                instruction = IRBuildString(values=strings)
                instructions.append(instruction)

                stack.append(instruction)
            # Building Containers
            elif opname in ('BUILD_LIST', 'BUILD_SET', 'BUILD_TUPLE'):
                if argval == 0:
                    values = tuple()
                else:
                    value_deque = deque()
                    for _ in range(argval):
                        value_deque.appendleft(stack.pop())
                    values = tuple(value_deque)
                if opname == 'BUILD_LIST':
                    instruction = IRBuildList(values)
                elif opname == 'BUILD_SET':
                    instruction = IRBuildSet(values)
                else:
                    instruction = IRBuildTuple(values)
                instructions.append(instruction)
                stack.append(instruction)
            elif opname == 'BUILD_MAP':
                key_deque = deque()
                value_deque = deque()

                for _ in range(argval):
                    value = stack.pop()
                    key = stack.pop()

                    key_deque.appendleft(key)
                    value_deque.appendleft(value)

                instruction = IRBuildMap(keys=tuple(key_deque), values=tuple(value_deque))
                instructions.append(instruction)

                stack.append(instruction)
            elif opname == 'BUILD_CONST_KEY_MAP':
                key_tuple = stack.pop()
                value_deque = deque()

                if not isinstance(key_tuple, IRConstant) or not isinstance(key_tuple.value, tuple):
                    raise UnexpectedError('key tuple is not a tuple literal in BUILD_CONST_KEY_MAP')

                keys = []
                for element in key_tuple.value:
                    instruction = IRConstant(value=element)
                    instructions.append(instruction)
                    keys.append(instruction)

                for _ in range(argval):
                    value = stack.pop()
                    value_deque.appendleft(value)

                instruction = IRBuildMap(keys=tuple(keys), values=tuple(value_deque))
                instructions.append(instruction)

                stack.append(instruction)
            # Subscribing and Slicing
            elif opname == 'BINARY_SUBSCR':
                key = stack.pop()
                container = stack.pop()

                instruction = IRLoadSubscr(key=key, container=container)
                instructions.append(instruction)

                stack.append(instruction)
            elif opname == 'STORE_SUBSCR':
                key = stack.pop()
                container = stack.pop()
                value = stack.pop()

                instruction = IRStoreSubscr(key, container, value)
                instructions.append(instruction)
            elif opname == 'DELETE_SUBSCR':
                key = stack.pop()
                container = stack.pop()

                instruction = IRDeleteSubscr(key=key, container=container)
                instructions.append(instruction)
            elif opname == 'BUILD_SLICE':
                if argval == 3:
                    step = stack.pop()
                else:
                    step = IRConstant(value=None)
                    instructions.append(step)
                end = stack.pop()
                start = stack.pop()

                instruction = IRBuildSlice(start=start, stop=end, step=step)
                instructions.append(instruction)
                stack.append(instruction)
            elif opname == 'BINARY_SLICE':
                end = stack.pop()
                start = stack.pop()
                container = stack.pop()

                step = IRConstant(value=None)
                instructions.append(step)

                build_slice_instruction = IRBuildSlice(start=start, stop=end, step=step)
                instructions.append(build_slice_instruction)

                binary_subscr_instruction = IRLoadSubscr(key=build_slice_instruction, container=container)
                instructions.append(binary_subscr_instruction)
                stack.append(binary_subscr_instruction)
            elif opname == 'STORE_SLICE':
                end = stack.pop()
                start = stack.pop()
                container = stack.pop()
                values = stack.pop()

                step = IRConstant(value=None)
                instructions.append(step)

                build_slice_instruction = IRBuildSlice(start=start, stop=end, step=step)
                instructions.append(build_slice_instruction)

                store_subscr_instruction = IRStoreSubscr(key=build_slice_instruction, container=container,
                                                         value=values)
                instructions.append(store_subscr_instruction)
            # Manipulating Containers
            elif opname == 'LIST_APPEND':
                item = stack.pop()
                list_to_be_appended = stack[-argval]

                append_method = IRLoadAttr(obj=list_to_be_appended, attr='append')
                instructions.append(append_method)

                call_instruction = IRCall(func=append_method, args=(item,), keywords={})
                instructions.append(call_instruction)
            elif opname == 'LIST_EXTEND':
                seq = stack.pop()
                list_to_be_extended = stack[-argval]

                extend_method = IRLoadAttr(obj=list_to_be_extended, attr='extend')
                instructions.append(extend_method)

                call_instruction = IRCall(func=extend_method, args=(seq,), keywords={})
                instructions.append(call_instruction)
            elif opname == 'MAP_ADD':
                value = stack.pop()
                key = stack.pop()
                dictionary = stack[-argval]

                instruction = IRStoreSubscr(key=key, container=dictionary, value=value)
                instructions.append(instruction)
            elif opname in ('DICT_UPDATE', 'DICT_MERGE'):
                mapping = stack.pop()

                dictionary = stack[-argval]

                update_method = IRLoadAttr(obj=dictionary, attr='update')
                instructions.append(update_method)

                call_instruction = IRCall(func=update_method, args=(mapping,), keywords={})
                instructions.append(call_instruction)
            elif opname == 'SET_ADD':
                item = stack.pop()
                set_to_be_updated = stack[-argval]

                add_method = IRLoadAttr(obj=set_to_be_updated, attr='add')
                instructions.append(add_method)

                call_instruction = IRCall(func=add_method, args=(item,), keywords={})
                instructions.append(call_instruction)
            elif opname == 'SET_UPDATE':
                seq = stack.pop()
                set_to_be_updated = stack[-argval]

                update_method = IRLoadAttr(obj=set_to_be_updated, attr='update')
                instructions.append(update_method)

                call_instruction = IRCall(func=update_method, args=(seq,), keywords={})
                instructions.append(call_instruction)
            # Unpacking Containers
            elif opname == 'UNPACK_SEQUENCE':
                sequence = stack.pop()

                unpack_sequence_instruction = IRUnpackSequence(sequence=sequence, size=argval)
                instructions.append(unpack_sequence_instruction)

                for index in range(argval - 1, -1, -1):
                    index_constant = IRConstant(value=index)
                    instructions.append(index_constant)

                    binary_subscr_instruction = IRLoadSubscr(key=index_constant,
                                                             container=unpack_sequence_instruction)
                    instructions.append(binary_subscr_instruction)

                    stack.append(binary_subscr_instruction)
            elif opname == 'UNPACK_EX':
                sequence = stack.pop()

                leading = argval & 0b11111111
                trailing = (argval >> 8)

                unpack_ex_instruction = IRUnpackEx(sequence=sequence, leading=leading, trailing=trailing)
                instructions.append(unpack_ex_instruction)

                for index in range(leading + trailing, -1, -1):
                    index_constant = IRConstant(value=index)
                    instructions.append(index_constant)

                    binary_subscr_instruction = IRLoadSubscr(key=index_constant, container=unpack_ex_instruction)
                    instructions.append(binary_subscr_instruction)

                    stack.append(binary_subscr_instruction)
            # Attributes
            elif opname == 'LOAD_ATTR':
                value = stack.pop()

                instruction = IRLoadAttr(value, argval)
                instructions.append(instruction)

                if arg & 0b1:
                    stack.append(IRConstant(value=None))
                stack.append(instruction)
            elif opname == 'LOAD_SUPER_ATTR':
                self_value = stack.pop()
                cls_vale = stack.pop()
                global_super_value = stack.pop()

                instruction = IRLoadSuperAttr(cls_vale, self_value, argval)
                instructions.append(instruction)

                if arg & 0b1:
                    stack.append(IRConstant(value=None))
                stack.append(instruction)
            elif opname == 'STORE_ATTR':
                obj = stack.pop()
                value = stack.pop()

                instruction = IRStoreAttr(obj, argval, value)
                instructions.append(instruction)
            elif opname == 'DELETE_ATTR':
                obj = stack.pop()
                instruction = IRDeleteAttr(obj=obj, attr=argval)
                instructions.append(instruction)
            # Function Calling
            elif opname == 'CALL':
                null_or_callable = stack[-(argval + 2)]
                callable_or_self = stack[-(argval + 1)]
                if argval:
                    arguments_and_keywords = tuple(stack[-argval:])
                else:
                    arguments_and_keywords = tuple()

                for _ in range(argval + 2):
                    stack.pop()

                if kw_names:
                    number_of_keywords = len(kw_names)
                    arguments = arguments_and_keywords[:-number_of_keywords]
                    keywords = dict(zip(kw_names, arguments_and_keywords[-number_of_keywords:]))

                    # Clear kw_names
                    kw_names = None
                else:
                    arguments = arguments_and_keywords
                    keywords = {}

                if isinstance(null_or_callable, IRConstant) and null_or_callable.value is None:
                    func = callable_or_self
                else:
                    func = null_or_callable
                    arguments = (callable_or_self,) + arguments

                instruction = IRCall(func, arguments, keywords)
                instructions.append(instruction)

                stack.append(instruction)
            elif opname == 'CALL_FUNCTION_EX':
                if argval & 0b1:
                    kwargs = stack.pop()
                else:
                    kwargs = IRConstant(None)
                    instructions.append(kwargs)

                args = stack.pop()
                func = stack.pop()

                # In the C source code:
                # STACK_SHRINK(((oparg & 1) ? 1 : 0));
                # STACK_SHRINK(2);
                # stack_pointer[-1] = result;
                # Overwriting top-of-stack with result = popping top-of-stack and pushing result
                placeholder = stack.pop()
                if (
                        not isinstance(placeholder, IRConstant)
                        or placeholder.value is not None
                ):
                    raise UnexpectedError('unknown placeholder used for CALL_FUNCTION_EX stack instruction')

                result = IRCallFunctionEx(func=func, args=args, keywords=kwargs)
                instructions.append(result)

                stack.append(result)
            elif opname == 'CALL_INTRINSIC_1':
                # Passes STACK[-1] as the argument and sets STACK[-1] to the result.

                # INTRINSIC_IMPORT_STAR
                if argval == 2:
                    module = stack[-1]
                    if not isinstance(module, IRImportModule):
                        raise UnexpectedError('unknown module')
                    instruction = IRImportFrom(module=module, name='*')
                    instructions.append(instruction)
                # INTRINSIC_LIST_TO_TUPLE
                elif argval == 6:
                    argument = stack.pop()

                    load_tuple = IRConstant(value=tuple)
                    instructions.append(load_tuple)

                    result = IRCall(func=load_tuple, args=(argument,), keywords={})
                    instructions.append(result)

                    stack.append(result)
                else:
                    raise NotImplementedError(stack_instruction)
            # For Loops
            elif opname == 'GET_ITER':
                value = stack.pop()
                instruction = IRGetIter(value)
                instructions.append(instruction)

                stack.append(instruction)
            elif opname == 'FOR_ITER':
                # before: [iter]; after: [iter, iter()] *or* [] (and jump over END_FOR.)
                iterator = stack.pop()

                # Branch out and translate stack instructions in target
                build_basic_block(
                    offsets_to_bytecode_basic_blocks=offsets_to_bytecode_basic_blocks,
                    offset=argval,
                    initial_stack=stack,
                    offsets_to_ir_basic_blocks=offsets_to_ir_basic_blocks,
                    offsets_to_final_stacks=offsets_to_final_stacks,
                )

                target = offsets_to_ir_basic_blocks[argval]
                instruction = IRForIter(iterator, target)
                instructions.append(instruction)

                stack.append(iterator)
                stack.append(instruction)
            elif opname == 'END_FOR':
                # We skip over END_FOR when branching from FOR_ITER
                pass
            # Branching
            elif opname == 'POP_JUMP_IF_TRUE':
                condition = stack.pop()

                # Branch out and translate stack instructions in target
                build_basic_block(
                    offsets_to_bytecode_basic_blocks=offsets_to_bytecode_basic_blocks,
                    offset=argval,
                    initial_stack=stack,
                    offsets_to_ir_basic_blocks=offsets_to_ir_basic_blocks,
                    offsets_to_final_stacks=offsets_to_final_stacks,
                )

                if_true = offsets_to_ir_basic_blocks[argval]
                instruction = IRBranch(condition, if_true)
                instructions.append(instruction)
            elif opname == 'POP_JUMP_IF_FALSE':
                condition = stack.pop()

                # Branch out and translate stack instructions in target
                build_basic_block(
                    offsets_to_bytecode_basic_blocks=offsets_to_bytecode_basic_blocks,
                    offset=argval,
                    initial_stack=stack,
                    offsets_to_ir_basic_blocks=offsets_to_ir_basic_blocks,
                    offsets_to_final_stacks=offsets_to_final_stacks,
                )

                if_false = offsets_to_ir_basic_blocks[argval]
                not_condition = IRUnaryOp(IRUnaryOperator.NOT, condition)
                instructions.append(not_condition)
                instruction = IRBranch(not_condition, if_false)
                instructions.append(instruction)
            elif opname == 'POP_JUMP_IF_NONE':
                value = stack.pop()

                # Branch out and translate stack instructions in target
                build_basic_block(
                    offsets_to_bytecode_basic_blocks=offsets_to_bytecode_basic_blocks,
                    offset=argval,
                    initial_stack=stack,
                    offsets_to_ir_basic_blocks=offsets_to_ir_basic_blocks,
                    offsets_to_final_stacks=offsets_to_final_stacks,
                )

                if_not_none = offsets_to_ir_basic_blocks[argval]
                none = IRConstant(value=None)
                instructions.append(none)
                value_is_none = IRBinaryOp(left=value, op=IRBinaryOperator.IS, right=none)
                instructions.append(value_is_none)
                instruction = IRBranch(value_is_none, if_not_none)
                instructions.append(instruction)
            elif opname == 'POP_JUMP_IF_NOT_NONE':
                value = stack.pop()

                # Branch out and translate stack instructions in target
                build_basic_block(
                    offsets_to_bytecode_basic_blocks=offsets_to_bytecode_basic_blocks,
                    offset=argval,
                    initial_stack=stack,
                    offsets_to_ir_basic_blocks=offsets_to_ir_basic_blocks,
                    offsets_to_final_stacks=offsets_to_final_stacks,
                )

                if_not_none = offsets_to_ir_basic_blocks[argval]
                none = IRConstant(value=None)
                instructions.append(none)
                value_is_not_none = IRBinaryOp(left=value, op=IRBinaryOperator.IS_NOT, right=none)
                instructions.append(value_is_not_none)
                instruction = IRBranch(value_is_not_none, if_not_none)
                instructions.append(instruction)
            # Jumping
            elif opname == 'JUMP_BACKWARD':
                # Branch out and translate stack instructions in target
                build_basic_block(
                    offsets_to_bytecode_basic_blocks=offsets_to_bytecode_basic_blocks,
                    offset=argval,
                    initial_stack=stack,
                    offsets_to_ir_basic_blocks=offsets_to_ir_basic_blocks,
                    offsets_to_final_stacks=offsets_to_final_stacks,
                )

                target = offsets_to_ir_basic_blocks[argval]
                instruction = IRJump(target)
                instructions.append(instruction)
            elif opname == 'JUMP_FORWARD':
                # Branch out and translate stack instructions in target
                build_basic_block(
                    offsets_to_bytecode_basic_blocks=offsets_to_bytecode_basic_blocks,
                    offset=argval,
                    initial_stack=stack,
                    offsets_to_ir_basic_blocks=offsets_to_ir_basic_blocks,
                    offsets_to_final_stacks=offsets_to_final_stacks,
                )

                target = offsets_to_ir_basic_blocks[argval]
                instruction = IRJump(target)
                instructions.append(instruction)
            # With Statements
            elif opname == 'BEFORE_WITH':
                manager = stack.pop()

                __exit__ = IRLoadAttr(obj=manager, attr='__exit__')
                instructions.append(__exit__)
                stack.append(__exit__)

                __enter__ = IRLoadAttr(obj=manager, attr='__enter__')
                instructions.append(__enter__)

                result = IRCall(func=__enter__, args=(), keywords={})
                instructions.append(result)

                stack.append(result)
            # Building Functions
            elif opname == 'MAKE_FUNCTION':
                """
                MAKE_FUNCTION(flags)
                Pushes a new function object on the stack. From bottom to top, the consumed stack must consist of values if the argument carries a specified flag value

                0x01 a tuple of default values for positional-only and positional-or-keyword parameters in positional order
                0x02 a dictionary of keyword-only parameters’ default values
                0x04 a tuple of strings containing parameters’ annotations
                0x08 a tuple containing cells for free variables, making a closure
                the code associated with the function (at STACK[-1])
                """
                load_region = stack.pop()
                if not isinstance(load_region, IRLoadChildRegion):
                    raise UnexpectedError(
                        "code_associated_with_function is not IRLoadRegion: %s" % (
                            load_region,
                        )
                    )

                if arg & 0x08:
                    free_variable_cells = stack.pop()
                    if not isinstance(free_variable_cells, IRBuildTuple):
                        raise UnexpectedError('unknown free variable cells layout')
                else:
                    free_variable_cells = IRBuildTuple(elts=())
                    instructions.append(free_variable_cells)

                annotations = OrderedDict()  # type: Dict[str, IRValue]
                if arg & 0x04:
                    annotation_tuple = stack.pop()
                    if (
                            (not isinstance(annotation_tuple, IRBuildTuple))
                            or (len(annotation_tuple.elts) % 2)
                    ):
                        raise UnexpectedError("unknown annotation tuple layout")

                    len_parameter_annotations = len(annotation_tuple.elts) // 2
                    for i in range(len_parameter_annotations):
                        parameter = annotation_tuple.elts[2 * i]
                        annotation = annotation_tuple.elts[2 * i + 1]

                        if (
                                (not isinstance(parameter, IRConstant))
                                or (not isinstance(parameter.value, str))
                                or (not isinstance(annotation, IRValue))
                        ):
                            raise UnexpectedError("unknown annotation tuple layout")

                        annotations[parameter.value] = annotation

                if arg & 0x02:
                    keyword_only_parameter_default_values = stack.pop()
                    if not isinstance(keyword_only_parameter_default_values, IRBuildMap):
                        raise UnexpectedError("unknown keyword only parameter default values layout")
                else:
                    keyword_only_parameter_default_values = IRBuildMap(keys=(), values=())
                    instructions.append(keyword_only_parameter_default_values)

                if arg & 0x01:
                    parameter_default_values = stack.pop()
                    if not isinstance(parameter_default_values, IRBuildTuple):
                        raise UnexpectedError("unknown parameter default values layout")
                else:
                    parameter_default_values = IRBuildTuple(elts=())
                    instructions.append(parameter_default_values)

                instruction = IRBuildFunction(
                    load_child_region=load_region,
                    parameter_default_values=parameter_default_values,
                    keyword_only_parameter_default_values=keyword_only_parameter_default_values,
                    annotations=annotations,
                    free_variable_cells=free_variable_cells,
                )
                instructions.append(instruction)

                stack.append(instruction)
            elif opname == 'SETUP_ANNOTATIONS':
                pass
            # Returning
            elif opname == 'RETURN_CONST':
                constant_instruction = IRConstant(argval)
                instructions.append(constant_instruction)
                return_instruction = IRReturn(constant_instruction)
                instructions.append(return_instruction)

                break
            elif opname == 'RETURN_VALUE':
                value = stack.pop()
                instruction = IRReturn(value)
                instructions.append(instruction)

                break
            # Yielding
            elif opname == 'YIELD_VALUE':
                value = stack.pop()
                instruction = IRYield(value=value)
                instructions.append(instruction)
                stack.append(instruction)
            # Exceptions
            elif opname == 'RAISE_VARARGS':
                if arg == 1:
                    exception_instance_or_type = stack.pop()
                    instruction = IRRaise(exception_instance_or_type)
                    instructions.append(instruction)

                    break
                else:
                    raise NotImplementedError(stack_instruction)
            else:
                raise NotImplementedError(stack_instruction)

        final_stack = tuple(stack)

        offsets_to_ir_basic_blocks[offset] = IRBasicBlock(instructions=tuple(instructions))
        offsets_to_final_stacks[offset] = final_stack

        return final_stack


def dump_region(
        region,  # type: IRRegion
):
    yield 'region name=%r is_generator=%r posonlyargs=%r args=%r varargs=%r kwonlyargs=%r varkeywords=%r' % (
        region.name,
        region.is_generator,
        region.posonlyargs,
        region.args,
        region.varargs,
        region.kwonlyargs,
        region.varkeywords

    )

    values_to_indices = {}

    def get_index(
            value,  # type: IRValue
    ):
        # type: (...) -> int
        if value not in values_to_indices:
            values_to_indices[value] = len(values_to_indices)
        return values_to_indices[value]

    for basic_block in region.basic_blocks:
        yield 'basic_block $%d' % (get_index(basic_block),)

        for instruction in basic_block.instructions:
            if isinstance(instruction, IRConstant):
                yield '$%d = constant %r' % (get_index(instruction), instruction.value)
            elif isinstance(instruction, IRLoadChildRegion):
                yield '$%d = load_child_region %r' % (get_index(instruction), instruction.child_region.name)
            elif isinstance(instruction, IRLoadName):
                yield '$%d = load_name %r' % (get_index(instruction), instruction.name)
            elif isinstance(instruction, IRLoadGlobal):
                yield '$%d = load_global %r' % (get_index(instruction), instruction.name)
            elif isinstance(instruction, IRStoreName):
                yield 'store_name $%d %r' % (get_index(instruction.value), instruction.name)
            elif isinstance(instruction, IRStoreGlobal):
                yield 'store_global $%d %r' % (get_index(instruction.value), instruction.name)
            elif isinstance(instruction, IRDeleteName):
                yield 'delete_name %r' % (instruction.name,)
            elif isinstance(instruction, IRMakeCell):
                yield 'make_cell %r' % (instruction.name,)
            elif isinstance(instruction, IRLoadDeref):
                yield '$%d = load_deref %r' % (get_index(instruction), instruction.name)
            elif isinstance(instruction, IRStoreDeref):
                yield 'store_deref $%d %r' % (get_index(instruction.value), instruction.name)
            elif isinstance(instruction, IRImportModule):
                yield '$%d = import_module %r level=%d return_top_level_package=%r' % (
                    get_index(instruction),
                    instruction.name,
                    instruction.level,
                    instruction.return_top_level_package
                )
            elif isinstance(instruction, IRImportFrom):
                yield '$%d = import_from $%d %r' % (get_index(instruction), get_index(instruction.module),
                                                    instruction.name)
            elif isinstance(instruction, IRUnaryOp):
                yield '$%d = %s $%d' % (get_index(instruction), instruction.op.value, get_index(instruction.operand))
            elif isinstance(instruction, IRBinaryOp):
                yield '$%d = $%d %s $%d' % (
                    get_index(instruction),
                    get_index(instruction.left),
                    instruction.op.value,
                    get_index(instruction.right)
                )
            elif isinstance(instruction, IRInPlaceBinaryOp):
                yield '$%d %s= $%d' % (get_index(instruction.target), instruction.op.value,
                                       get_index(instruction.value))
            elif isinstance(instruction, IRFormatValue):
                yield '$%d = format_value $%d format_spec=$%d' % (
                    get_index(instruction),
                    get_index(instruction.value),
                    get_index(instruction.format_spec)
                )
            elif isinstance(instruction, IRBuildString):
                yield '$%d = build_string values=[%s]' % (
                    get_index(instruction),
                    ', '.join(
                        '$%d' % (get_index(value),)
                        for value in instruction.values
                    )
                )
            elif isinstance(instruction, IRBuildList):
                yield '$%d = build_list elts=[%s]' % (
                    get_index(instruction),
                    ', '.join(
                        '$%d' % (get_index(elt),)
                        for elt in instruction.elts
                    )
                )
            elif isinstance(instruction, IRBuildMap):
                yield '$%d = build_map keys=[%s] values=[%s]' % (
                    get_index(instruction),
                    ', '.join('$%d' % (get_index(key),) for key in instruction.keys),
                    ', '.join('$%d' % (get_index(value),) for value in instruction.values),

                )
            elif isinstance(instruction, IRBuildSet):
                yield '$%d = build_set elts=[%s]' % (
                    get_index(instruction),
                    ', '.join(
                        '$%d' % (get_index(elt),)
                        for elt in instruction.elts
                    )
                )
            elif isinstance(instruction, IRBuildTuple):
                yield '$%d = build_tuple elts=[%s]' % (
                    get_index(instruction),
                    ', '.join(
                        '$%d' % (get_index(elt),)
                        for elt in instruction.elts
                    )
                )
            elif isinstance(instruction, IRLoadSubscr):
                yield '$%d = $%d[$%d]' % (
                    get_index(instruction),
                    get_index(instruction.container),
                    get_index(instruction.key)
                )
            elif isinstance(instruction, IRStoreSubscr):
                yield '$%d[$%d] = $%d' % (
                    get_index(instruction.container),
                    get_index(instruction.key),
                    get_index(instruction.value)
                )
            elif isinstance(instruction, IRDeleteSubscr):
                yield 'del $%d[$%d]' % (
                    get_index(instruction.container),
                    get_index(instruction.key)
                )
            elif isinstance(instruction, IRBuildSlice):
                yield '$%d = build_slice $%d:$%d:$%d' % (
                    get_index(instruction),
                    get_index(instruction.start),
                    get_index(instruction.stop),
                    get_index(instruction.step)
                )
            elif isinstance(instruction, IRUnpackSequence):
                yield '$%d = unpack_sequence $%d %d' % (
                    get_index(instruction),
                    get_index(instruction.sequence),
                    instruction.size
                )
            elif isinstance(instruction, IRUnpackEx):
                yield '$%d = unpack_ex $%d %d %d' % (
                    get_index(instruction),
                    get_index(instruction.sequence),
                    instruction.leading,
                    instruction.trailing
                )
            elif isinstance(instruction, IRLoadAttr):
                yield '$%d = load_attr $%d %r' % (
                    get_index(instruction),
                    get_index(instruction.obj),
                    instruction.attr
                )
            elif isinstance(instruction, IRLoadSuperAttr):
                yield '$%d = load_super_attr $%d $%d %r' % (
                    get_index(instruction),
                    get_index(instruction.cls_obj),
                    get_index(instruction.self_obj),
                    instruction.attr
                )
            elif isinstance(instruction, IRStoreAttr):
                yield 'store_attr $%d %r $%d' % (
                    get_index(instruction.obj),
                    instruction.attr,
                    get_index(instruction.value)
                )
            elif isinstance(instruction, IRDeleteAttr):
                yield 'delete_attr $%d %r' % (get_index(instruction.obj), instruction.attr)
            elif isinstance(instruction, IRCall):
                yield '$%d = $%d(%s)' % (
                    get_index(instruction),
                    get_index(instruction.func),
                    ', '.join(
                        chain(
                            ('$%d' % (get_index(arg),) for arg in instruction.args),
                            (
                                '%s=$%d' % (keyword_name, get_index(keyword))
                                for keyword_name, keyword in instruction.keywords.items()
                            ),
                        )
                    )

                )
            elif isinstance(instruction, IRCallFunctionEx):
                yield '$%d = $%d(*$%d, **$%d)' % (
                    get_index(instruction),
                    get_index(instruction.func),
                    get_index(instruction.args),
                    get_index(instruction.keywords),
                )
            elif isinstance(instruction, IRGetIter):
                yield '$%d = get_iter $%d' % (get_index(instruction), get_index(instruction.value))
            elif isinstance(instruction, IRForIter):
                yield '$%d = for_iter iter=$%d target=$%d' % (
                    get_index(instruction),
                    get_index(instruction.iter),
                    get_index(instruction.target)
                )
            elif isinstance(instruction, IRBranch):
                yield 'branch condition=$%d target=$%d' % (get_index(instruction.condition),
                                                           get_index(instruction.target))
            elif isinstance(instruction, IRJump):
                yield 'jump $%d' % (get_index(instruction.target),)
            elif isinstance(instruction, IRBuildFunction):
                yield '$%d = build_function load_child_region=$%d parameter_default_values=$%d keyword_only_parameter_default_values=$%d free_variable_cells=$%d annotations={%s}' % (
                    get_index(instruction),
                    get_index(instruction.load_child_region),
                    get_index(instruction.parameter_default_values),
                    get_index(instruction.keyword_only_parameter_default_values),
                    get_index(instruction.free_variable_cells),
                    ', '.join(
                        '%s: $%d' % (parameter, get_index(annotation))
                        for parameter, annotation in instruction.annotations.items()
                    ),

                )
            elif isinstance(instruction, IRReturn):
                yield 'return $%d' % (get_index(instruction.value),)
            elif isinstance(instruction, IRYield):
                yield '$%d = yield $%d' % (get_index(instruction), get_index(instruction.value))
            elif isinstance(instruction, IRRaise):
                yield 'raise $%d' % (get_index(instruction.exc),)
            else:
                raise NotImplementedError(instruction)
        yield ''
    yield ''
