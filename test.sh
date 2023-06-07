#!/bin/zsh
curl -v -X POST -H "Content-Type: application/octet-stream" --data-binary "@ViewingActivity.csv" https://u7crgr0yuf.execute-api.us-east-1.amazonaws.com/ | jq
