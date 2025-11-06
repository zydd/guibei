# class Context:
#     def __init__(self, parent=None):
#         self.parent: Context = parent
#         self.root = parent.root if parent else self

#         self.constants: dict[str] = dict()
#         self.functions: dict[str] = dict()
#         self.imports = list()
#         self.types: dict[str] = dict()
#         self.variables: dict[str] = dict()
#         self.data: list[bytes] = list()
#         self._current_function = None

#     def new(self):
#         return Context(self)

#     def register_const(self, const):
#         assert const.name not in self.constants
#         self.constants[const.name] = const

#     def register_func(self, func):
#         assert isinstance(func.name, str)
#         assert func.name not in self.functions
#         self.root.functions[func.name] = func

#     def register_import(self, expr):
#         self.root.imports.append(expr)

#     def register_type(self, type_):
#         assert isinstance(type_.name, str)
#         assert type_.name not in self.types
#         self.root.types[type_.name] = type_

#     def register_variable(self, var):
#         assert isinstance(var.name, str)
#         assert var.name not in self.variables, var.name
#         self.variables[var.name] = var

#         func = self.current_function()
#         assert var.name not in func.locals
#         func.locals[var.name] = var

#     def add_data(self, val):
#         i = len(self.root.data)
#         self.root.data.append(val)
#         return i

#     def current_function(self):
#         return self._current_function or self.parent.current_function()

#     def lookup(self, name: str):
#         res = []

#         if name in self.variables:
#             res.append(self.variables[name])

#         if name in self.constants:
#             res.append(self.constants[name])

#         if name in self.types:
#             res.append(self.types[name])

#         if name in self.functions:
#             res.append(self.functions[name])

#         if len(res) == 1:
#             return res[0]

#         if len(res) > 1:
#             raise KeyError(f"Ambiguous reference to '{name}'")

#         if self.parent:
#             return self.parent.lookup(name)

#         raise KeyError(f"Name '{name}' not found in context")

#     def lookup_var(self, name: str):
#         name = str(name)
#         res = []

#         if name in self.variables:
#             res.append(self.variables[name])

#         if name in self.constants:
#             res.append(self.constants[name])

#         if name in self.functions:
#             res.append(self.functions[name])

#         if len(res) == 1:
#             return res[0]

#         if len(res) > 1:
#             raise KeyError(f"Ambiguous reference to '{name}'")

#         if self.parent:
#             return self.parent.lookup_var(name)

#         raise KeyError(f"Name '{name}' not found in context")

#     def lookup_type(self, name: str):
#         name = str(name)
#         if name in self.types:
#             return self.types[name]

#         if self.parent:
#             return self.parent.lookup_type(name)

#         raise KeyError(f"Type '{name}' not found in context")
