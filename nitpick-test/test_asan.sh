#!/bin/bash
set -e

echo "Creating a leaky program..."
cat << 'EOF' > leaky.npk
extern func:malloc = void*(uint64:size);

func:failsafe = int32(tbb32:err) {
    exit 1i32;
};

func:main = int32() {
    malloc(1024u64);
    return 0i32;
};
EOF

echo "Running nitpick-test on leaky program..."
# Expect failure because of ASAN leak
EXIT_CODE=0
./nitpick-test leaky.npk > output.txt 2>&1 || EXIT_CODE=$?

if [ "$EXIT_CODE" != "0" ]; then
    if grep -q "Direct leak" output.txt || grep -q "AddressSanitizer" output.txt; then
        echo "ASAN successfully detected the leak!"
    else
        echo "Failed to detect ASAN output!"
        cat output.txt
        exit 1
    fi
else
    echo "nitpick-test succeeded unexpectedly!"
    cat output.txt
    exit 1
fi

echo "All tests passed!"
