#!/bin/bash

# Generate protobuf files if they don't exist
if [ ! -f "photo_of_day_pb2.py" ]; then
    echo "\uD83D\uDD27 Generating protobuf files..."
    python -m grpc_tools.protoc \
        -I./proto \
        --python_out=. \
        --grpc_python_out=. \
        ./proto/photo_of_day.proto
    echo "✅ Protobuf files generated"
fi

# Start the gRPC server
echo "\uD83D\uDE80 Starting Photo of Day gRPC Service..."
exec python grpc_server.py