import logging
import os

import h5py
import numpy as np

# Set up logger
logger = logging.getLogger("SessionStorage")
# logger.setLevel(logging.INFO)  # Uncomment to enable logging


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
        self._open_file()
        return self

    def __exit__(self, *args) -> None:
        self._close_file()

    def _generate_unique_filename(self) -> str:
        # Generates a unique file name
        return f"session_{os.urandom(4).hex()}.hdf5"

    def _open_file(self) -> None:
        try:
            self.file = h5py.File(self.file_path, "a")
            logger.info(f"Opened file {self.file_path}")

        except IOError as e:
            logger.error(f"Failed to open file {self.file_path}: {e}")
            raise

    def _close_file(self) -> None:
        if self.file is not None:
            self.file.close()
            self.file.__exit__()
            self.file = None
            logger.info(f"Closed file {self.file_path}")

    def get_dataset(self, entity: int, component: str) -> h5py.Dataset:
        if self.file is None:
            raise RuntimeError("File is not opened.")

        try:
            component_group = self.file.require_group(component)
            return component_group[self.to_bytes64(entity)]

        except KeyError:
            logger.warning(f"Dataset {entity}/{component} not found.")
            raise KeyError("The requested entity/component does not exist.")

    def add_data(
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
        entity_id = self.to_bytes64(entity)

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

    def metadata(self, entity: int) -> h5py.AttributeManager:
        entity_id = self.to_bytes64(entity)
        entity_group = self.file.require_group(entity_id)
        return entity_group.attrs

    def to_bytes64(self, entity: int):
        return entity.to_bytes(8, "little")
