#!/bin/bash
set -e

echo "Building nitpick-safety..."
make

echo "Creating mock_file.npk..."
cat << 'EOF' > mock_file.npk
func main() -> NIL:
    // This is a comment with wild and raw(
    let str1 = "This string has wild and raw( and { and }"
    let str2 = `This is a 
    multi-line string with wild and 
    raw( and {
    and // comments inside strings
    }`
    
    // Test failsafe string triviality
    failsafe {
        pass("not trivial because string {");
    }
    
    failsafe {
        pass(NIL)
    }

    let a = wildx alloc(10) // should trigger
    raw(a) // should trigger
end
EOF

echo "Running nitpick-safety..."
./nitpick-safety mock_file.npk > output.txt 2>&1 || true

cat output.txt

if grep -q "mock_file.npk:19: \[WILD\]" output.txt && grep -q "mock_file.npk:20: \[RAW\]" output.txt && grep -q "mock_file.npk:15: \[FAILSAFE\]" output.txt; then
    echo "Expected hits found!"
else
    echo "Missing expected hits!"
    exit 1
fi

if grep -q "str1" output.txt || grep -q "str2" output.txt || grep -q "multi-line" output.txt || grep -q "comment with wild" output.txt || grep -q "not trivial" output.txt; then
    echo "False positives found inside strings/comments!"
    exit 1
else
    echo "No false positives in strings/comments."
fi

echo "All tests passed!"
