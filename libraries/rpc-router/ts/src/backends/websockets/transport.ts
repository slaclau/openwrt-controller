import { AbstractDuplexConnection, ConnectionManager } from '../../protocol';
import { AbstractServer, AbstractClient } from '../../lifecycle';
import { DuplexRouter } from '../../types';
import { ConnectionBrokenException, ConnectionRefusedException } from '../../exceptions';

/**
 * Framework-specific pipe translation layer handling raw string frames.
 */
export class WebsocketsDuplexConnection extends AbstractDuplexConnection {
    private ws: any;

    constructor(
        websocket: any,
        router: DuplexRouter,
        clientId?: string,
        manager?: ConnectionManager
    ) {
        super(router, clientId);
        this.ws = websocket;

        if (manager) {
            manager.register(this.clientId, this);
        }

        // Direct network traffic straight down into the handleMessage parser loop
        this.ws.onmessage = async (event: any) => {
            const rawData = typeof event.data !== 'undefined' ? event.data : event;
            await this.handleMessage(rawData.toString());
        };

        this.ws.onclose = async () => {
            if (manager) {
                manager.unregister(this.clientId);
            }
            await this.close();
        };

        this.ws.onerror = async () => {
            if (manager) {
                manager.unregister(this.clientId);
            }
            await this.close();
        };
    }

    protected async _rawSend(payloadStr: string): Promise<void> {
        try {
            // 1 signifies standard WebSocket.OPEN state
            if (this.ws.readyState !== 1) {
                throw new ConnectionBrokenException();
            }
            this.ws.send(payloadStr);
        } catch (err) {
            throw new ConnectionBrokenException(err instanceof Error ? err.message : String(err));
        }
    }

    protected async _rawClose(): Promise<void> {
        if (this.ws.readyState === 0 || this.ws.readyState === 1) { // CONNECTING or OPEN
            this.ws.close();
        }
    }
}

/**
 * Concrete WebSocket Server mapping lifecycle hooks directly to the Node 'ws' package.
 */
export class WebsocketServer extends AbstractServer {
    private port: number;
    private host: string;
    private _server: any | null = null;

    constructor(router: DuplexRouter, host: string, port: number) {
        super(router);
        this.host = host;
        this.port = port;
    }

    protected async _rawStart(): Promise<void> {
        // Dynamic import isolates this backend code from frontend compilation boundaries
        const { WebSocketServer: NodeWSServer } = await import('ws');

        this._server = new NodeWSServer({ host: this.host, port: this.port });

        this._server.on('connection', (websocket: any) => {
            new WebsocketsDuplexConnection(websocket, this.router, undefined, this.manager);
        });

        console.info(`WebSocket Server active on ws://${this.host}:${this.port}`);
    }

    protected async _rawStop(): Promise<void> {
        if (this._server) {
            return new Promise<void>((resolve, reject) => {
                this._server!.close((err: any) => {
                    if (err) reject(err);
                    else {
                        console.info("WebSocket Server shut down cleanly");
                        resolve();
                    }
                });
            });
        }
    }
}

/**
 * Concrete WebSocket Client mapping connection handshakes directly to native web context APIs or ws wrappers.
 */
export class WebsocketClient extends AbstractClient {
    private targetUrl: string;

    constructor(router: DuplexRouter, targetUrl: string) {
        super(router);
        this.targetUrl = targetUrl;
    }

    protected async _createConnection(): Promise<WebsocketsDuplexConnection> {
        return new Promise<WebsocketsDuplexConnection>(async (resolve, reject) => {
            try {
                const WSConstructor = typeof WebSocket !== 'undefined' ? WebSocket : (await import('ws')).default;
                const websocket = new WSConstructor(this.targetUrl);

                websocket.onopen = () => {
                    websocket.onerror = null;
                    resolve(new WebsocketsDuplexConnection(websocket, this.router));
                };

                websocket.onerror = () => {
                    reject(new ConnectionRefusedException());
                };
            } catch (err) {
                reject(new ConnectionRefusedException());
            }
        });
    }
}
