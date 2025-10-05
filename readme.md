# Syntax


## Keywords and Symbols

- Declarations: `const`, `func`, `let`
- Type system: `impl`, `for`, `trait`, `type`
- Control flow: `case`, `else`, `for`, `if`, `match`, `while`
- Operator overloading: `infixl`, `infixr`, `unaryl`, `unaryr`

Symbols:
- `#` - line comment
- `:` - start block, type annotation, trait bounds
- `->` - return type
- `+` - trait bound list
- `(`, `)` - function call, sub-expression, tuple
- `[`, `]` - indexing, array
- `{`, `}` - named tuple, closure?
- `<`, `>` - macro args, type function args
- `,` - function args, array, tuple, named tuple
- `.` - member access, floating point literal
- `"` - string literal
- `'` - char literal?
- `=` - assignment, named function args?

```rust
func foo()
func foo(a)
func foo(a, b)

let foo = func(a): bar(a)
```

```rust
let a = 3
let a: i32 = 3
```

```rust
const a = 3
const a: i32 = 3
```

---


```rust
if 1 > 2:
    foo()

if 1 < 2:
    foo()
else:
    bar()

let a = if 1 < 2: 3 else: 4
```

```python
match a:
    case 1: foo()
    case 2: bar()
    case _: baz()

match (a, 3 + 4):
    case (_, 12): foo()
    case (_,  _): bar()
```

```python
func foo(a):
    case 0: bar()
    case a: baz(a)
```

```rust
trait Index:
    type Elem

    func [](self, i: usize) -> Elem:
        self.at(i)

    func at(self, i: usize) -> Elem
```
```rust
impl Index for i32:
    type Elem: i32

    func at(self, i):
        case (self, 0): self
```
```rust
type Vec2i: {x: i32, y: i32}
type Vec2<T>: {x: T, y: T}
type Vec2u: Vec2<u32>
```
---
```python
# function foo below
func foo(a):
    case 0: bar()  # call bar
    case a: baz(a  # argument a
                + 0)
```

```rust
let a: i32 = 3
const a: i32 = 3
const a<const N: i32>: i32 = N
```

```rust
trait HashTable<Key: Hashable, Value>:
    func find(self, key: K) -> Value
```

```rust
trait Number -> Add + Sub + Mul + Div
```

## Operator overloading


||||
|---------|------------------------------|-------------|
|Infix    | `func (infixl 5 +)(lhs, rhs)`| `lhs + rhs` |
|Prefix   | `func (unaryl 5 ~)(value)`   | `~value`    |
|Postfix  | `func (unaryr 5 !)(value)`   | `value!`    |
|Indexing | `func [](value, i)`          | `value[i]`  |
|Call     | `func ()(value, a)`          | `value(a)`  |
|Template | `func <value, i>`            | `value<i>`  |

Notes:
- Indexing has higher precedence than all other operators
- Limit precedence to 10 like Haskell?
- Should it be possible to overload assignment operator?


Syntax candidates:

```sh
# Infix

infixl 5 +
func (+)(lhs, rhs)  # <-

func infixl 5 (+)(lhs, rhs)
func (infixl 5 +)(lhs, rhs)

func (lhs) + (rhs)
func (lhs) (+) (rhs)
func (lhs) infixl 5 + (rhs)
func (lhs) (infixl 5 +) (rhs)

(lhs) (infixl 5 +) (rhs)

infixl5 (+)(lhs, rhs)
infixl 5 (+)(lhs, rhs)


# Prefix
unaryl 7 ~
func ~(value)
func (~)(value)  # <-

func unaryl 7 (~)(value)
func (unaryl 7 ~)(value)

unaryl7 (~)(value)
unaryl 7 (~)(value)


# Postfix
unaryr 7
func (value)!  # <-

func (value)(unaryr 7 !)

func unaryr 7 (!)(value)
func (unaryr 7 !)(value)

unaryr7 (!)(value)
unaryr 7 (!)(value)


# Indexing
func value[i]
func (value)[i]
func [value, i]
func [](value, i)  # <-
func ([])(value, i)
```


# Type system

## Type specialization


```rust
trait Specialized
    func call(self)

impl<T: Debug> Specialized for T:
    func call(self):
        println("debug print: {:?}", self)


impl<T: Display> Specialized for T:
    func call(self):
        println("display print: {}", self)


:deriving(Display, Debug)
data SomeType

impl Specialized for SomeType as Display

impl<Display> Specialized for SomeType
```

## Function specialization

```rust
func call<T>(v: T):
    match T:
        case Display:
            println("display print: {}", self)
        case Debug:
            println("debug print: {:?}", self)


let var: SomeType

call(var as Display)

call<Display>(var)
```

## TODO: Mixins


```python
class ImplA1:
    def callA():
        print('A1')

class ImplA2:
    def callA():
        print('A2')

class ImplAB:
    def callB():
        callA()
        print('B')

class Cls(ImplA1, ImplAB):
    def exec():
        callA()
        callB()

# Should not be allowed due to overlapping implementation:
class ClsErr(ImplA1, ImplA2, ImplAB)
```
