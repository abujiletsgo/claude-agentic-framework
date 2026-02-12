#!/bin/bash
# Quick fix to make characters stay visible longer

FILE="src/components/GameWorld3DIntegrated.vue"

# Increase workstation count
sed -i '' 's/const WORKSTATION_COUNT = 8/const WORKSTATION_COUNT = 16/' "$FILE"

# Increase radius
sed -i '' 's/const WORKSTATION_RADIUS = 8/const WORKSTATION_RADIUS = 10/' "$FILE"

# Increase activity timeout (30 seconds instead of 5)
sed -i '' 's/const ACTIVITY_TIMEOUT = 5000/const ACTIVITY_TIMEOUT = 30000/' "$FILE"

# Increase recent window (5 minutes instead of 1)
sed -i '' 's/const recentWindow = 60000/const recentWindow = 300000/' "$FILE"

echo "✅ Fixed! Characters will now:"
echo "  - Stay visible for 5 minutes (was 1 minute)"
echo "  - Stay 'working' for 30 seconds (was 5 seconds)"
echo "  - Support 16 characters (was 8)"
echo ""
echo "Refresh your browser to see changes!"
