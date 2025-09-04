#!/bin/sh

# Start at current directory
DIR=$(pwd)

# find the project root directory
while [ "$DIR" != "/" ]; do
    if [ -d "$DIR/.git" ] || [ -f "$DIR/pyproject.toml" ]; then
        break
    fi
    DIR=$(dirname "$DIR")
done

cd "$DIR"

if [ ! -f "$DIR/.env" ]; then
    echo "[-] .env file not found!"
    exit 1
fi

# run the .env file to load environment variables
. "$DIR/.env"

ssh "$server_user@$server_name" -i "$server_key_path"