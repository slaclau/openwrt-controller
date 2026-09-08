import { DuplexRouter, Handler, ConnectHandler } from './types';
import { ConnectionManager, AbstractDuplexConnection } from './protocol';

/**
 * Base endpoint routing proxy layer.
 * Mirrors Python's AbstractEndpoint constructor hook setup.
 */
export abstract class AbstractEndpoint {
    public router: DuplexRouter;

    constructor(router: DuplexRouter) {
        this.router = router;
    }

    /**
     * Proxies directly to the underlying DuplexRouter's connect initialization registry.
     */
    public onConnect(handler: ConnectHandler): this {
        this.router.onConnect(handler);
        return this;
    }

    /**
     * Proxies directly to the underlying DuplexRouter's inbound frame interceptor array.
     */
    public beforeReceive(handler: Handler): this {
        this.router.beforeReceive(handler);
        return this;
    }

    /**
     * Proxies directly to the underlying DuplexRouter's outbound frame interceptor array.
     */
    public beforeSend(handler: Handler): this {
        this.router.beforeSend(handler);
        return this;
    }
}

/**
 * Symmetrical Lifecycle Manager for Servers.
 * Subclasses implement low-level server networking triggers (_rawStart, _rawStop).
 */
export abstract class AbstractServer extends AbstractEndpoint {
    public manager: ConnectionManager;

    constructor(router: DuplexRouter) {
        super(router);
        this.manager = new ConnectionManager();
    }

    protected abstract _rawStart(): Promise<void>;
    protected abstract _rawStop(): Promise<void>;

    /**
     * Activates the low-level server listener and yields the network registry manager.
     * Replicates Python's __aenter__ block initialization setup.
     */
    public async start(): Promise<ConnectionManager> {
        await this._rawStart();
        return this.manager;
    }

    /**
     * Closes active listeners and terminates tracking pipelines across all connections.
     * Replicates Python's __aexit__ cleanup routine.
     */
    public async stop(): Promise<void> {
        // 1. Cleanly disconnect all remaining active connections tracked by the server
        const activeConns = Array.from(this.manager.activeConnections.values());
        for (const conn of activeConns) {
            if (conn.isAlive) {
                await conn.close();
            }
        }

        // 2. Trigger transport shutdown
        await this._rawStop();
    }
}

/**
 * Symmetrical Lifecycle Manager for Clients.
 * Subclasses implement raw socket connection triggers (_createConnection).
 */
export abstract class AbstractClient extends AbstractEndpoint {
    protected _conn: AbstractDuplexConnection | null = null;

    constructor(router: DuplexRouter) {
        super(router);
    }

    protected abstract _createConnection(): Promise<AbstractDuplexConnection>;

    /**
     * Opens the raw network pipe infrastructure and provisions connection execution cycles.
     * Replicates Python's __aenter__ client implementation hook.
     */
    public async connect(): Promise<AbstractDuplexConnection> {
        this._conn = await this._createConnection();
        await this._conn.open();
        return this._conn;
    }

    /**
     * Terminates active running pipelines cleanly.
     * Replicates Python's __aexit__ client execution drop.
     */
    public async disconnect(): Promise<void> {
        if (this._conn) {
            await this._conn.close();
            this._conn = null;
        }
    }
}
