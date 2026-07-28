from __future__ import annotations

from abc import ABC, abstractmethod

from models import Listing


class RetailerClient(ABC):
    @abstractmethod
    def search(self) -> list[Listing]:
        """
        Find products and return them as Listing objects.
        """
        raise NotImplementedError