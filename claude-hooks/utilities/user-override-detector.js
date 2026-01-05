/**
 * User Override Detector
 * Shared module for consistent #skip/#remember handling across all hooks
 *
 * Usage:
 *   const { detectUserOverrides } = require('./user-override-detector');
 *   const overrides = detectUserOverrides(userMessage);
 *   if (overrides.forceSkip) return;
 */

// User override patterns (case-insensitive, word boundary)
const USER_OVERRIDES = {
    forceRemember: /#remember\b/i,
    forceSkip: /#skip\b/i
};

/**
 * Detect user overrides in a message
 * @param {string} userMessage - The user's message text
 * @returns {Object} Override detection result
 */
function detectUserOverrides(userMessage) {
    if (!userMessage || typeof userMessage !== 'string') {
        return { forceRemember: false, forceSkip: false };
    }

    return {
        forceRemember: USER_OVERRIDES.forceRemember.test(userMessage),
        forceSkip: USER_OVERRIDES.forceSkip.test(userMessage)
    };
}

/**
 * Extract user message from various context formats
 * Handles different hook context structures
 * @param {Object} context - Hook context object
 * @returns {string|null} Extracted user message or null
 */
function extractUserMessage(context) {
    if (!context) return null;

    // Direct userMessage property
    if (context.userMessage) {
        return typeof context.userMessage === 'string'
            ? context.userMessage
            : null;
    }

    // From transcript (last user message)
    if (context.transcript_path) {
        // Transcript extraction should be done by caller
        return null;
    }

    // From message property
    if (context.message) {
        return typeof context.message === 'string'
            ? context.message
            : null;
    }

    return null;
}

/**
 * Console output for override actions
 */
const OVERRIDE_MESSAGES = {
    skip: '\x1b[33m\u23ed\ufe0f  Memory Hook\x1b[0m \x1b[2m\u2192\x1b[0m Skipped by user override (#skip)',
    remember: '\x1b[36m\ud83d\udcbe Memory Hook\x1b[0m \x1b[2m\u2192\x1b[0m Force triggered by user override (#remember)'
};

/**
 * Log override action to console
 * @param {'skip'|'remember'} action - The override action
 */
function logOverride(action) {
    if (OVERRIDE_MESSAGES[action]) {
        console.log(OVERRIDE_MESSAGES[action]);
    }
}

module.exports = {
    detectUserOverrides,
    extractUserMessage,
    logOverride,
    USER_OVERRIDES,
    OVERRIDE_MESSAGES
};
