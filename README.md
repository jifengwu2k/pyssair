# `pyssair`

`pyssair` is a first-of-its-kind project that faithfully converts Python bytecode into a static single assignment (SSA)-like intermediate representation (IR) for program analysis.

## Why `pyssair`?

SSA IRs, like LLVM IR for C/C++/Rust, have enabled rich tooling and analysis for those languages. Yet, no open project has tackled the challenge of converting Python bytecode into an SSA-style IR for program analysis - until now.

Python program analysis tools today overwhelmingly rely on the builtin `ast` module - meaning they prioritize **syntax** first, rather than **operational semantics**. This works well enough for code linters, but quickly becomes brittle and tedious for general-purpose program analysis. As a result:

- Projects invent awkward, fragile code to "simulate" control flow and runtime effects.
- Different analysis tools must repeatedly reimplement core logic.
- The richness of Python's dynamic semantics is often missing or approximated.

Some projects (like [Numba](https://numba.pydata.org/)) convert Python bytecode to SSA IR internally, but they do so only to support **optimized execution of a *restricted subset* of Python** (e.g., for numerical/scientific code) - not for analysis. For such projects, this SSA IR is an undocumented implementation detail, opaque and unstable.

`pyssair`, in contrast, exposes a stable, well-documented SSA IR as a *front and center* API.

## Demo

Given the following Python source `test.py`:

```python
import os
import os.path
from typing import Iterable, Iterator, List, Sequence


def process_data(data: Iterable[int], *, multiplier: int = 2, filter_even: bool = True) -> List[int]:
    result = []

    def inner_filter(val: int) -> int:
        nonlocal multiplier

        if filter_even and val % 2:
            multiplier += 1

        return val * multiplier

    for val in data:
        result.append(inner_filter(val))

    return result


def read_numbers(source_file: str) -> Iterator[int]:
    if not os.path.isfile(source_file):
        raise FileNotFoundError(f'{source_file} not found.')

    with open(source_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and line.isdigit():
                yield int(line)


class Statistics:
    def __init__(self, values: Sequence[int]):
        self.values = values

    def mean(self) -> float:
        return sum(self.values) / len(self.values) if self.values else 0.0


if __name__ == '__main__':
    with open('numbers.txt', 'w') as f:
        for i in range(10):
            f.write(str(i) + '\n')

    numbers = read_numbers('numbers.txt')
    processed_numbers = process_data(numbers, multiplier=3, filter_even=True)

    if processed_numbers:
        print('Processed numbers:')
        for val in processed_numbers:
            print(val, end=' ')

        statistics = Statistics(processed_numbers)
        print('Mean:', statistics.mean())
    else:
        print('No data was processed.')

    os.remove('numbers.txt')
```

Running:

```python
from pyssair import IRRegion, build_region, dump_region

with open('test.py', 'r') as f:
    code = compile(f.read(), 'test.py', 'exec')
region = build_region(code)  # type: IRRegion
for child_region_path, child_region in region.iterate_child_regions(recursive=True):
    print('Region with path', child_region_path)
    for line in dump_region(child_region):
        print(line)
```

Will output a readable, SSA-style IR (truncated for clarity):

```text
Region with path ['<module>']
region name='<module>' is_generator=False posonlyargs=() args=() varargs=None kwonlyargs=() varkeywords=None
basic_block $0
$1 = constant 0
$2 = constant None
$3 = import_module 'os' level=0 return_top_level_package=True
store_name $3 'os'
$4 = constant 0
$5 = constant None
$6 = import_module 'os.path' level=0 return_top_level_package=True
store_name $6 'os'
... (imports and typing aliasing) ...
$33 = load_child_region 'process_data'
$34 = build_tuple elts=[]
$35 = build_tuple elts=[]
$36 = build_function load_child_region=$33 parameter_default_values=$35 keyword_only_parameter_default_values=$19 free_variable_cells=$34 annotations={data: $23, ...}
store_name $36 'process_data'
$44 = load_child_region 'read_numbers'
...
basic_block $62
$63 = load_name 'open'
$64 = constant 'numbers.txt'
$65 = constant 'w'
$66 = $63($64, $65)
$67 = load_attr $66 '__exit__'
$68 = load_attr $66 '__enter__'
$69 = $68()
store_name $69 'f'
$70 = load_name 'range'
$71 = constant 10
$72 = $70($71)
$73 = get_iter $72

basic_block $74
$75 = for_iter iter=$73 target=$76

basic_block $77
store_name $75 'i'
$78 = load_name 'f'
$79 = load_attr $78 'write'
$80 = load_name 'str'
$81 = load_name 'i'
$82 = $80($81)
$83 = constant '\n'
$84 = $82 + $83
$85 = $79($84)
jump $74

...(more SSA blocks for all code regions)...
Region with path ['<module>', 'process_data']
region name='process_data' ...
basic_block $0
make_cell 'multiplier'
make_cell 'filter_even'
$1 = build_list elts=[]
store_name $1 'result'
...
basic_block $16
$17 = for_iter iter=$15 target=$18

basic_block $19
store_name $17 'val'
$20 = load_name 'result'
$21 = load_attr $20 'append'
$22 = load_name 'inner_filter'
$23 = load_name 'val'
$24 = $22($23)
$25 = $21($24)
jump $16
...
Region with path ['<module>', 'process_data', 'inner_filter']
region name='inner_filter' ...
basic_block $0
$1 = load_deref 'filter_even'
$2 = not $1
branch condition=$2 target=$3

basic_block $4
$5 = load_name 'val'
$6 = constant 2
$7 = $5 % $6
$8 = not $7
branch condition=$8 target=$3

basic_block $9
$10 = load_deref 'multiplier'
$11 = constant 1
$10 += $11
store_deref $10 'multiplier'

basic_block $3
$12 = load_name 'val'
$13 = load_deref 'multiplier'
$14 = $12 * $13
return $14
...
```

## Design

- **Dynamic-First:** The IR aims to be true to *Python's real execution* (dynamic types, late binding, etc.).
    - If something isn't known until runtime, it's left symbolic in the IR.
        - No static name resolution.
    - Functions and classes are built *dynamically*.
- **Compositional:** Each IR class is explicit and typed.

## Limitations

- Supports **Python 3.12** only.
- Some instructions (especially async/await, exception handling) are **not yet implemented** and will raise exceptions if encountered.
- Only the main executable control flow is covered. *Exception handlers (try/except/finally) and unreachable code are ignored* for now.

## Contributing

Contributions are welcome! Please submit pull requests or open issues on the GitHub repository.

## License

This project is licensed under the [Apache-2.0 License](LICENSE).

## `pyssair` IR Reference

The `pyssair` IR is organized as follows.

### `IRRegion`

Represents any region of Python code. Members:

- `name` (`str`): The region's name. `<module>` for top-level.
- `is_generator` (`bool`): Does the region contain a `yield`?
- `posonlyargs` (`Sequence[str]`): Positional-only argument names (3.8+)
- `args` (`Sequence[str]`): Regular arg names
- `varargs` (`Optional[str]`): The `*args` parameter
- `kwonlyargs` (`Sequence[str]`): Keyword-only names
- `varkeywords` (`Optional[str]`): The `**kwargs` parameter
- `basic_blocks` (`Sequence[IRBasicBlock]`): The code within this region.

**Child code** (functions/classes inside): available through `child_regions()`.

### `IRBasicBlock`

A straight-line sequence of instructions. Members:

- `instructions` (`List[IRInstruction]`)

### Constants and Regions

- `IRConstant(value): IRInstruction, IRValue`: Any constant literal (number, str, bool, None, tuple, etc.)
- `IRLoadChildRegion(child_region: IRRegion): IRInstruction, IRValue`: Reference to child region (functions/classes inside current region). Used for building functions and classes.

### Names

- `IRLoadName(name: str): IRInstruction, IRValue`
- `IRLoadGlobal(name: str): IRInstruction, IRValue`
- `IRStoreName(name: str, value: IRValue): IRInstruction`
- `IRStoreGlobal(name: str, value: IRValue): IRInstruction`
- `IRDeleteName(name: str): IRInstruction`

### Cells (Closures/Nonlocals)

- `IRMakeCell(name: str): IRInstruction`
- `IRLoadDeref(name: str): IRInstruction, IRValue`
- `IRStoreDeref(name: str, value: IRValue): IRInstruction`

### Imports

- `IRImportModule(name: str, level: int, return_top_level_package: bool): IRInstruction, IRValue`
- `IRImportFrom(module: IRImportModule, name: str): IRInstruction, IRValue`

### Unary Operations

```
class IRUnaryOperator(Enum):
    INVERT = '~'
    NOT = 'not'
    UNARY_ADD = '+'
    UNARY_SUB = '-'
```

- `IRUnaryOp(op: IRUnaryOperator, operand: IRValue): IRInstruction, IRValue`

### Binary Operations

```
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
```

- `IRBinaryOp(left: IRValue, op: IRBinaryOperator, right: IRValue): IRInstruction, IRValue`
- `IRInPlaceBinaryOp(target: IRValue, op: IRBinaryOperator, value: IRValue): IRInstruction`

### String Formatting

- `IRFormatValue(value: IRValue, format_spec: IRValue): IRInstruction, IRValue`
- `IRBuildString(values: Sequence[IRValue]): IRInstruction, IRValue`

### Building Containers

- `IRBuildList(elts: Sequence[IRValue]): IRInstruction, IRValue`
- `IRBuildMap(keys: Sequence[IRValue], values: Sequence[IRValue]): IRInstruction, IRValue`
- `IRBuildSet(elts: Sequence[IRValue]): IRInstruction, IRValue`
- `IRBuildTuple(elts: Sequence[IRValue]): IRInstruction, IRValue`

### Subscribing and Slicing

- `IRLoadSubscr(container: IRValue, key: IRValue): IRInstruction, IRValue`
- `IRBuildSlice(start: IRValue, stop: IRValue, step: IRValue): IRInstruction, IRValue`
- `IRStoreSubscr(container: IRValue, key: IRValue, value: IRValue): IRInstruction`
- `IRDeleteSubscr(container: IRValue, key: IRValue): IRInstruction`

### Unpacking Containers

- `IRUnpackSequence(sequence: IRValue, size: int): IRInstruction, IRValue`
- `IRUnpackEx(sequence: IRValue, leading: int, trailing: int): IRInstruction, IRValue`

### Attributes

- `IRLoadAttr(obj: IRValue, attr: str): IRInstruction, IRValue`
- `IRLoadSuperAttr(cls_obj: IRValue, self_obj: IRValue, attr: str): IRInstruction, IRValue`
- `IRStoreAttr(obj: IRValue, attr: str, value: IRValue): IRInstruction`
- `IRDeleteAttr(obj: IRValue, attr: str): IRInstruction`

### Function Calling

- `IRCall(func: IRValue, args: Sequence[IRValue], keywords: Mapping[str, IRValue]): IRInstruction, IRValue`: Call with specified positional and keyword args.
- `IRCallFunctionEx(func: IRValue, args: IRValue, keywords: IRValue): IRInstruction, IRValue`: Call with arbitrary argument expansion.

### Iterators

- `IRGetIter(value: IRValue): IRInstruction, IRValue`: Get iterator
- `IRForIter(iter: IRValue, target: IRBasicBlock): IRInstruction, IRValue`: Calls `next` on an iterator; jumps to `target` on iterator exhaustion.

### Branching

- `IRBranch(condition: IRValue, target: IRBasicBlock): IRInstruction`: Conditional branch

### Jumping

- `IRJump(target: IRBasicBlock): IRInstruction`: Unconditional jump

### Building Functions

- `IRBuildFunction(load_child_region: IRLoadChildRegion, parameter_default_values: IRBuildTuple, keyword_only_parameter_default_values: IRBuildMap, free_variable_cells: IRValue, annotations: Mapping[str, IRValue])`: Build function object.

### Returning

- `IRReturn(value: IRValue): IRInstruction`: Return value

### Yielding

- `IRYield(value: IRValue): IRInstruction, IRValue`: Yield value, also catches value sent to generator.

### Exceptions

- `IRRaise(exc: IRValue): IRInstruction`: Raise exception