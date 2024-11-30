import base64
import logging
import os

import h5py
import numpy as np

# Set up logger
logger = logging.getLogger("SessionStorage")
logger.setLevel(logging.DEBUG)  # Uncomment to enable logging


class SessionStorage:
    def __init__(self, file_name: str | None = None, dir: str = "dataset/sessions"):
        # Ensure the directory exists
        os.makedirs(dir, exist_ok=True)

        if file_name is None:
            file_name = self._generate_unique_filename()

        # Set the full file path for the session storage
        self.file_path = os.path.join(dir, file_name)
        self.file: h5py.File | None = None

    def __enter__(self) -> "SessionStorage":
        self.open()
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def _generate_unique_filename(self) -> str:
        # Generates a unique file name
        return f"session_{os.urandom(4).hex()}.hdf5"

    def open(self) -> None:
        try:
            self.file = h5py.File(self.file_path, "a")
            logger.info(f"Opened file {self.file_path}")

        except IOError as e:
            logger.error(f"Failed to open file {self.file_path}: {e}")
            raise

    def close(self) -> None:
        if self.file is not None:
            self.file = self.file.__exit__()
            logger.info(f"Closed file {self.file_path}")

    def entities_with(self, component: str):
        if self.file is None:
            raise RuntimeError("File is not opened.")

        return self.file.require_group(component)

    def get_table(self, entity: int, component: str) -> h5py.Dataset:
        component_group = self.entities_with(component)

        try:
            return component_group[self._entity_to_id(entity)]

        except KeyError:
            raise KeyError(f"Dataset {entity}/{component} not found.")

    def add_row(
        self,
        entity: int,
        component: str,
        data: np.ndarray,
        timestamp: int,
        **kwargs,
    ) -> None:
        if self.file is None:
            raise RuntimeError("File is closed.")

        data_point = np.array(
            (timestamp, data),
            dtype=[
                ("timestamp", np.uint64),
                (component, data.dtype, data.shape),
            ],
        )

        component_group = self.file.require_group(component)
        entity_id = self._entity_to_id(entity)

        if component == "image":
            # Enable level 4 gzip compression for dataset
            kwargs.setdefault("compression", 4)

        # Create or access the dataset
        dataset = component_group.require_dataset(
            entity_id,
            shape=(0,),
            maxshape=(None,),
            dtype=data_point.dtype,
            **kwargs,
        )

        # Append new data as structured array
        dataset.resize(dataset.shape[0] + 1, axis=0)
        dataset[-1] = data_point
        logger.debug(f"Appended data to {entity}/{component}")

    def entity_data(self, entity: int) -> h5py.AttributeManager:
        group = self.file.require_group("entities")
        entity_id = self._entity_to_id(entity)
        return group.require_group(entity_id).attrs

    def _entity_to_id(self, entity: int) -> bytes:
        byte_rep = entity.to_bytes(8, "little")
        return base64.b64encode(byte_rep).decode("utf-8")

    def id_to_entity(entity_id: bytes) -> int:
        decoded_bytes = base64.b64decode(entity_id)
        return int.from_bytes(decoded_bytes, "little")
