/**
 * Unified Memory Client
 * Supports both HTTP and MCP protocols with automatic fallback
 */

const https = require('https');
const http = require('http');
const { MCPClient } = require('./mcp-client');

class MemoryClient {
    constructor(config) {
        this.config = config;
        this.protocol = config.protocol || 'auto';
        this.preferredProtocol = config.preferredProtocol || 'mcp';
        this.fallbackEnabled = config.fallbackEnabled !== false;
        this.httpConfig = config.http || {};
        this.mcpConfig = config.mcp || {};

        // Connection state
        this.activeProtocol = null;
        this.httpAvailable = null;
        this.mcpAvailable = null;
        this.mcpClient = null;

        // Cache successful connections
        this.connectionCache = new Map();
    }

    /**
     * Initialize connection using the configured protocol
     */
    async connect() {
        if (this.protocol === 'http') {
            return this.connectHTTP();
        } else if (this.protocol === 'mcp') {
            return this.connectMCP();
        } else {
            // Auto mode: try preferred first, then fallback
            return this.connectAuto();
        }
    }

    /**
     * Auto-connect: try preferred protocol first, fallback if needed
     */
    async connectAuto() {
        const protocols = this.preferredProtocol === 'mcp' ? ['mcp', 'http'] : ['http', 'mcp'];

        for (const protocol of protocols) {
            try {
                if (protocol === 'mcp') {
                    await this.connectMCP();
                    this.activeProtocol = 'mcp';
                    return { protocol: 'mcp', client: this.mcpClient };
                } else {
                    await this.connectHTTP();
                    this.activeProtocol = 'http';
                    return { protocol: 'http', client: null };
                }
            } catch (error) {
                if (!this.fallbackEnabled || protocols.length === 1) {
                    throw error;
                }
                // Continue to try next protocol
                continue;
            }
        }

        throw new Error('Failed to connect using any available protocol');
    }

    /**
     * Connect using MCP protocol
     */
    async connectMCP() {
        if (this.mcpClient) {
            return this.mcpClient;
        }

        this.mcpClient = new MCPClient(
            this.mcpConfig.serverCommand,
            {
                workingDir: this.mcpConfig.serverWorkingDir,
                connectionTimeout: this.mcpConfig.connectionTimeout || 5000,
                toolCallTimeout: this.mcpConfig.toolCallTimeout || 10000
            }
        );

        // Handle MCP client errors gracefully
        this.mcpClient.on('error', (error) => {
            this.mcpAvailable = false;
        });

        await this.mcpClient.connect();
        this.mcpAvailable = true;
        return this.mcpClient;
    }

    /**
     * Connect using HTTP protocol
     */
    async connectHTTP() {
        // Test HTTP connection with a simple health check
        const healthResult = await this.queryHealthHTTP();
        if (!healthResult.success) {
            throw new Error(`HTTP connection failed: ${healthResult.error}`);
        }
        this.httpAvailable = true;
        return true;
    }

    /**
     * Query health status using active protocol
     */
    async getHealthStatus() {
        if (this.activeProtocol === 'mcp' && this.mcpClient) {
            return this.mcpClient.getHealthStatus();
        } else if (this.activeProtocol === 'http') {
            return this.queryHealthHTTP();
        } else {
            throw new Error('No active connection available');
        }
    }

    /**
     * Query health via HTTP
     */
    async queryHealthHTTP() {
        return new Promise((resolve) => {
            try {
                const healthPath = this.httpConfig.useDetailedHealthCheck ?
                    '/api/health/detailed' : '/api/health';
                const url = new URL(healthPath, this.httpConfig.endpoint);

                const requestOptions = {
                    hostname: url.hostname,
                    port: url.port || 8443,
                    path: url.pathname,
                    method: 'GET',
                    headers: {
                        'Authorization': `Bearer ${this.httpConfig.apiKey}`,
                        'Accept': 'application/json'
                    },
                    timeout: this.httpConfig.healthCheckTimeout || 3000,
                    rejectUnauthorized: false
                };

                const protocol = url.protocol === 'https:' ? https : http;
                const req = protocol.request(requestOptions, (res) => {
                    let data = '';
                    res.on('data', (chunk) => data += chunk);
                    res.on('end', () => {
                        try {
                            if (res.statusCode === 200) {
                                const healthData = JSON.parse(data);
                                resolve({ success: true, data: healthData });
                            } else {
                                resolve({ success: false, error: `HTTP ${res.statusCode}`, fallback: true });
                            }
                        } catch (parseError) {
                            resolve({ success: false, error: 'Invalid JSON response', fallback: true });
                        }
                    });
                });

                req.on('error', (error) => {
                    resolve({ success: false, error: error.message, fallback: true });
                });

                req.on('timeout', () => {
                    req.destroy();
                    resolve({ success: false, error: 'HTTP health check timeout', fallback: true });
                });

                req.end();

            } catch (error) {
                resolve({ success: false, error: error.message, fallback: true });
            }
        });
    }

    /**
     * Query memories using active protocol
     */
    async queryMemories(query, limit = 10) {
        if (this.activeProtocol === 'mcp' && this.mcpClient) {
            return this.mcpClient.queryMemories(query, limit);
        } else if (this.activeProtocol === 'http') {
            return this.queryMemoriesHTTP(query, limit);
        } else {
            throw new Error('No active connection available');
        }
    }

    /**
     * Query memories by time using active protocol
     */
    async queryMemoriesByTime(timeQuery, limit = 10) {
        if (this.activeProtocol === 'mcp' && this.mcpClient) {
            return this.mcpClient.queryMemoriesByTime(timeQuery, limit);
        } else if (this.activeProtocol === 'http') {
            return this.queryMemoriesHTTP(timeQuery, limit);
        } else {
            throw new Error('No active connection available');
        }
    }

    /**
     * Query memories via HTTP
     */
    async queryMemoriesHTTP(query, limit = 10) {
        return new Promise((resolve, reject) => {
            const url = new URL('/mcp', this.httpConfig.endpoint);
            const postData = JSON.stringify({
                jsonrpc: '2.0',
                id: 1,
                method: 'tools/call',
                params: {
                    name: 'retrieve_memory',
                    arguments: {
                        query: query,
                        n_results: limit
                    }
                }
            });

            const options = {
                hostname: url.hostname,
                port: url.port || 8443,
                path: url.pathname,
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Content-Length': Buffer.byteLength(postData),
                    'Authorization': `Bearer ${this.httpConfig.apiKey}`
                },
                rejectUnauthorized: false
            };

            const protocol = url.protocol === 'https:' ? https : http;
            const req = protocol.request(options, (res) => {
                let data = '';
                res.on('data', (chunk) => data += chunk);
                res.on('end', () => {
                    try {
                        const response = JSON.parse(data);
                        if (response.result && response.result.content) {
                            let textData = response.result.content[0].text;

                            try {
                                textData = textData
                                    .replace(/'/g, '"')
                                    .replace(/True/g, 'true')
                                    .replace(/False/g, 'false')
                                    .replace(/None/g, 'null');

                                const memories = JSON.parse(textData);
                                resolve(memories.results || memories.memories || []);
                            } catch (conversionError) {
                                console.warn('[Memory Client] Could not parse HTTP memory response:', conversionError.message);
                                resolve([]);
                            }
                        } else {
                            resolve([]);
                        }
                    } catch (parseError) {
                        console.warn('[Memory Client] HTTP parse error:', parseError.message);
                        resolve([]);
                    }
                });
            });

            req.on('error', (error) => {
                console.warn('[Memory Client] HTTP network error:', error.message);
                resolve([]);
            });

            req.write(postData);
            req.end();
        });
    }

    /**
     * Get connection status and available protocols
     */
    getConnectionInfo() {
        return {
            activeProtocol: this.activeProtocol,
            httpAvailable: this.httpAvailable,
            mcpAvailable: this.mcpAvailable,
            fallbackEnabled: this.fallbackEnabled,
            preferredProtocol: this.preferredProtocol
        };
    }

    /**
     * Disconnect from active protocol
     */
    async disconnect() {
        if (this.mcpClient) {
            try {
                await this.mcpClient.disconnect();
            } catch (error) {
                // Ignore cleanup errors
            }
            this.mcpClient = null;
        }

        this.activeProtocol = null;
        this.httpAvailable = null;
        this.mcpAvailable = null;
        this.connectionCache.clear();
    }
}

module.exports = { MemoryClient };