#!/usr/bin/env node

/**
 * Test script for version-checker.js utility
 */

const { getVersionInfo, formatVersionDisplay } = require('./claude-hooks/utilities/version-checker');

const CONSOLE_COLORS = {
    RESET: '\x1b[0m',
    BRIGHT: '\x1b[1m',
    DIM: '\x1b[2m',
    CYAN: '\x1b[36m',
    GREEN: '\x1b[32m',
    YELLOW: '\x1b[33m',
    GRAY: '\x1b[90m',
    RED: '\x1b[31m'
};

async function test() {
    console.log('Testing version-checker utility...\n');

    const projectRoot = __dirname;

    // Test with PyPI check
    console.log('1. Testing with PyPI check enabled:');
    const versionInfo = await getVersionInfo(projectRoot, { checkPyPI: true, timeout: 3000 });
    console.log('   Raw version info:', JSON.stringify(versionInfo, null, 2));
    const display = formatVersionDisplay(versionInfo, CONSOLE_COLORS);
    console.log('   Formatted:', display);

    console.log('\n2. Testing without PyPI check:');
    const localOnly = await getVersionInfo(projectRoot, { checkPyPI: false });
    console.log('   Raw version info:', JSON.stringify(localOnly, null, 2));
    const localDisplay = formatVersionDisplay(localOnly, CONSOLE_COLORS);
    console.log('   Formatted:', localDisplay);

    console.log('\n✅ Test completed!');
}

test().catch(error => {
    console.error('❌ Test failed:', error);
    process.exit(1);
});
