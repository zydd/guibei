import abc

from .context import Context


class AstNode(abc.ABC):
    label_id = 0

    @abc.abstractmethod
    def annotate(self, context: Context, expected_type):
        raise NotImplementedError

    def compile(self) -> list:
        raise NotImplementedError(str(self))

    @staticmethod
    def next_id():
        AstNode.label_id += 1
        return AstNode.label_id

    @staticmethod
    def check_type(type_, expected_type):
        if expected_type:
            cur = type_
            while cur:
                if cur == expected_type:
                    break
                cur = cur.super_
            else:
                raise TypeError("Expected type {}, got {}".format(expected_type.name, type_.name))
