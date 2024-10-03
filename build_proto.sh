#!/bin/bash

# Generate Python code
python -m grpc_tools.protoc -I..\proto\ --python_out=. ..\proto\game_socket.proto
# ..\protoc-28.2-win64\bin\protoc.exe --proto_path=..\proto\ --python_out=. ..\proto\game_socket.proto

