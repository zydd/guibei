
class Context:
    def __init__(self, parent=None):
        self.parent = parent
        self.root = parent.root if parent else self

        self.imports = list()
        self.variables: dict[str] = dict()
        self.types: dict[str] = dict()
        self.functions: dict[str] = dict()

    def new(self):
        return Context(self)

    def register_variable(self, var):
        assert str(var.name) not in self.variables, var.name
        self.variables[str(var.name)] = var

    def register_type(self, type_):
        assert str(type_.name) not in self.types
        self.types[str(type_.name)] = type_

    def register_func(self, func):
        assert str(func.name) not in self.functions
        self.functions[str(func.name)] = func

    def register_import(self, expr):
        self.root.imports.append(expr)

    def lookup(self, name: str):
        name = str(name)
        res = []

        if name in self.variables:
            res.append(self.variables[name])

        if name in self.types:
            res.append(self.types[name])

        if name in self.functions:
            res.append(self.functions[name])

        if len(res) == 1:
            return res[0]

        if len(res) > 1:
            raise KeyError(f"Ambiguous reference to '{name}'")

        if self.parent:
            return self.parent.lookup(name)

        raise KeyError(f"Name '{name}' not found in context")

    def lookup_type(self, name: str):
        name = str(name)
        if name in self.types:
            return self.types[name]

        if self.parent:
            return self.parent.lookup_type(name)

        raise KeyError(f"Type '{name}' not found in context")
