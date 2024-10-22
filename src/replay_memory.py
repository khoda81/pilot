import math
from typing import Optional, Union

import numpy as np


class DynamicArray:
    def __init__(self, *, maxlen: Optional[int] = None) -> None:
        self.maxlen = math.inf if maxlen is None else maxlen
        self.buffer = None
        self.tail = 0

    def _resize(self):
        """Resize the buffer by doubling its size if maxlen is None (dynamic buffer)."""
        prev_size, *sample_shape = self.buffer.shape

        new_length = 2 * prev_size
        new_length = max(1, new_length)
        new_length = min(self.maxlen, new_length)

        new_shape = (new_length, *sample_shape)
        new_buf = np.empty(new_shape, dtype=self.buffer.dtype)

        part1, part2 = self.parts()
        new_buf[: len(part1)] = part1
        new_buf[len(part1) : len(part1) + len(part2)] = part2

        self.buffer = new_buf
        self.head = 0

    def append(self, value: np.ndarray) -> None:
        """Append a value to the deque."""

        # If this is the first item, create the buffer
        if self.buffer is None:
            self.buffer = value[None].copy()
            self.tail += 1

            return

        if len(self.buffer) <= self.tail < self.maxlen:
            self._resize()

        tail = self.tail % len(self.buffer)
        self.buffer[tail] = value
        self.tail += 1

    def parts(self):
        if self.tail <= len(self.buffer):
            return self.buffer[: self.tail], self.buffer[self.tail : self.tail]

        split_point = self.tail % len(self.buffer)
        return self.buffer[split_point:], self.buffer[:split_point]

    def last(self):
        if self.buffer is None:
            raise IndexError("Can't read last item, since the buffer is empty")

        return self.buffer[self.tail - 1 % len(self.buffer)]

    def __len__(self):
        return 0 if self.buffer is None else min(self.tail, len(self.buffer))

    def __bool__(self):
        return self.__len__() != 0


class UpdateBuffer:
    def __init__(self, *, capacity: Optional[int] = None):
        self.updates = DynamicArray(maxlen=capacity)

    @property
    def buffer(self):
        return self.updates.buffer

    def append(self, timestamp: Union[int, np.ndarray], data: np.ndarray):
        sample = np.array(
            (timestamp, data),
            dtype=[("timestamp", np.int32), ("data", data.dtype, data.shape)],
        )

        self.updates.append(sample)

    def __len__(self):
        return len(self.updates)

    def __bool__(self):
        return bool(self.updates)
