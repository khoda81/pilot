#!/bin/bash

# Generate Python code
protoc -I ../proto/ --python_out=./src/tankwar/protobuf --pyi_out=./src/tankwar/protobuf ../proto/game_socket.proto
