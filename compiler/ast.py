import abc

from .context import Context


class AstNode(abc.ABC):
    @abc.abstractmethod
    def annotate(self, context: Context):
        raise NotImplementedError

    @abc.abstractmethod
    def compile(self) -> list:
        raise NotImplementedError
