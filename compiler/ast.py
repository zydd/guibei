import abc

from .context import Context


class AstNode(abc.ABC):
    @abc.abstractmethod
    def annotate(self, context: Context):
        raise NotImplementedError

    def compile(self) -> list:
        raise NotImplementedError
