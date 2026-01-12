#!/bin/bash
# Health check script for local AI services
# Usage: ./check-health.sh [--verbose|-v]

GATEWAY_URL="${GATEWAY_URL:-http://localhost:10000}"
VERBOSE=false

if [[ "$1" == "--verbose" ]] || [[ "$1" == "-v" ]]; then
    VERBOSE=true
fi

echo "=== Local AI Health Check ==="
echo ""

# Check gateway health (detailed endpoint)
echo "Checking gateway at $GATEWAY_URL..."
HEALTH=$(curl -s --connect-timeout 5 "$GATEWAY_URL/health/detailed" 2>/dev/null)

if [ -z "$HEALTH" ]; then
    echo "  Gateway: UNREACHABLE"
    echo ""
    echo "Falling back to individual container checks..."
    echo ""

    # Direct container checks
    services=(
        "comfyui|http://localhost:10001/system_stats"
        "cosmos|http://localhost:10002/health"
        "audiocraft|http://localhost:10003/"
        "tts|http://localhost:10004/v1/models"
    )

    for service in "${services[@]}"; do
        name=$(echo "$service" | cut -d'|' -f1)
        url=$(echo "$service" | cut -d'|' -f2)

        status=$(curl -s --connect-timeout 5 -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)

        if [ "$status" -ge 200 ] && [ "$status" -lt 500 ]; then
            echo "  $name: OK (HTTP $status)"
        elif [ "$status" == "000" ]; then
            echo "  $name: UNREACHABLE"
        else
            echo "  $name: ERROR (HTTP $status)"
        fi
    done
else
    # Parse gateway response
    overall=$(echo "$HEALTH" | jq -r '.status' 2>/dev/null)

    if [ "$overall" == "healthy" ]; then
        echo "  Overall: HEALTHY"
    else
        echo "  Overall: $overall"
    fi

    echo ""
    echo "Services:"

    # Extract service statuses
    for service in comfyui cosmos audiocraft tts; do
        status=$(echo "$HEALTH" | jq -r ".services.$service.status" 2>/dev/null)
        if [ "$status" == "healthy" ]; then
            echo "  $service: OK"
        else
            echo "  $service: $status"
        fi
    done

    if $VERBOSE; then
        echo ""
        echo "Raw response:"
        echo "$HEALTH" | jq .
    fi
fi

echo ""
echo "=== Docker Container Status ==="
docker ps --filter "name=local-ai" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "Docker not available"
