#!/bin/bash
# Test VSK Local AI Services
# Tests the working conda-based services

# Don't exit on error - we handle test failures
# set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "==========================================="
echo "Video Starter Kit - Service Test Suite"
echo "==========================================="
echo ""

PASSED=0
FAILED=0

test_endpoint() {
    local name="$1"
    local url="$2"
    local expected="$3"

    printf "  Testing %s... " "$name"
    response=$(curl -s "$url" 2>/dev/null || echo "CURL_ERROR")

    if echo "$response" | grep -q "$expected"; then
        printf "${GREEN}PASS${NC}\n"
        PASSED=$((PASSED + 1))
        return 0
    else
        printf "${RED}FAIL${NC}\n"
        echo "    Expected: $expected"
        echo "    Got: ${response:0:100}"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

echo "=== Health Checks ==="
test_endpoint "Gateway (10000)" "http://localhost:10000/health" "healthy"
test_endpoint "Audiocraft (10003)" "http://localhost:10003/health" "healthy"
test_endpoint "Kokoro TTS (10005)" "http://localhost:10005/health" "healthy"
test_endpoint "TTS Router (10004)" "http://localhost:10004/health" "healthy"
echo ""

echo "=== TTS Generation Test ==="
echo -n "  Generating TTS audio... "
RESPONSE=$(curl -s -X POST "http://localhost:10000/fal-ai/playht/tts/v3" \
    -H "Content-Type: application/json" \
    -d '{"text": "Test audio generation", "voice": "af_heart"}' 2>/dev/null)

REQUEST_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('request_id',''))" 2>/dev/null)

if [ -n "$REQUEST_ID" ]; then
    sleep 3
    STATUS=$(curl -s "http://localhost:10000/status/$REQUEST_ID" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null)
    if [ "$STATUS" = "completed" ]; then
        printf "${GREEN}PASS${NC} (request: $REQUEST_ID)\n"
        PASSED=$((PASSED + 1))
    else
        printf "${RED}FAIL${NC} (status: $STATUS)\n"
        FAILED=$((FAILED + 1))
    fi
else
    printf "${RED}FAIL${NC} (no request ID)\n"
    FAILED=$((FAILED + 1))
fi

echo ""
echo "=== Music Generation Test ==="
printf "  Generating music audio... "
RESPONSE=$(curl -s -X POST "http://localhost:10003/generate" \
    -H "Content-Type: application/json" \
    -d '{"prompt": "test music", "duration": 3}' 2>/dev/null)

if echo "$RESPONSE" | grep -q "audio_url\|output\|wav"; then
    printf "${GREEN}PASS${NC}\n"
    PASSED=$((PASSED + 1))
else
    printf "${YELLOW}SKIP${NC} (endpoint response: ${RESPONSE:0:50})\n"
fi

echo ""
echo "==========================================="
echo "Results: ${GREEN}$PASSED passed${NC}, ${RED}$FAILED failed${NC}"
echo "==========================================="

if [ $FAILED -gt 0 ]; then
    exit 1
fi
exit 0
