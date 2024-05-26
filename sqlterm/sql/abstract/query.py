from abc import ABCMeta, abstractmethod


class Query(metaclass=ABCMeta):
    def __repr__(self: "Query") -> str:
        return f"{type(self).__name__}(text='''{self.text}''')"

    @property
    @abstractmethod
    def text(self: "Query") -> str:
        ...
