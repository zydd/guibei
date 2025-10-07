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
