#!/bin/bash -eu
# Lionstone's core is standard-library only: put src/ on the path instead of pip installing.
for fuzzer in $(find "$SRC/lionstone/fuzz" -name '*_fuzzer.py'); do
  compile_python_fuzzer "$fuzzer" --paths "$SRC/lionstone/src"
done
