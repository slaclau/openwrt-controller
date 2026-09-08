import { DuplexRouter, RPCFrame } from './types';
import { ConnectionBrokenException } from './exceptions';

/**
 * Manages active connection lifetimes across an application topology.
 * Symmetrically replicates Python's ConnectionManager registry.
 */
export class ConnectionManager {
    public activeConnections = new Map<string, AbstractDuplexConnection>();

    public register(clientId: string, connection: AbstractDuplexConnection): void {
        this.activeConnections.set(clientId, connection);
    }

    public unregister(clientId: string): void {
        this.activeConnections.delete(clientId);
    }

    public changeId(clientId: string, connection: AbstractDuplexConnection): void {
        if (connection.clientId === clientId) return;
        if (!this.activeConnections.has(connection.clientId)) {
            throw new Error("Unregistered connection");
        }
        this.unregister(connection.clientId);
        connection.clientId = clientId;
        this.register(clientId, connection);
    }

    public get(clientId: string): AbstractDuplexConnection | null {
        const conn = this.activeConnections.get(clientId);
        return conn && conn.isAlive ? conn : null;
    }

    public async broadcast(method: string, payload: any = null, exclude: string[] = []): Promise<number> {
        let count = 0;
        for (const [clientId, conn] of this.activeConnections.entries()) {
            if (exclude.includes(clientId)) continue;
            count++;
            await conn.send(method, payload);
        }
        return count;
    }

    public async sendTo(clientId: string, method: string, payload: any = null): Promise<void> {
        const conn = this.get(clientId);
        if (!conn) throw new Error(`No client with id ${clientId}`);
        await conn.send(method, payload);
    }
}

/**
 * Symmetrical Protocol Engine.
 * Completely encapsulates background task listeners and request lifecycles.
 */
export abstract class AbstractDuplexConnection {
    public clientId: string;
    public isAlive: boolean = false;
    protected router: DuplexRouter;

    // Tracks active outgoing request promises across the transport boundary
    private pendingCalls = new Map<string, {
        resolve: (val: any) => void;
        reject: (err: Error) => void;
        timer: any;
    }>();

    constructor(router: DuplexRouter, clientId?: string) {
        this.router = router;
        this.clientId = clientId || `rpc-${Math.random().toString(36).substring(2, 10)}`;
    }

    // Network transport primitives to be overridden by subclasses
    protected abstract _rawSend(payloadStr: string): Promise<void>;
    protected abstract _rawClose(): Promise<void>;

    /**
     * Initializes the connection layout and switches state flags.
     * Replicates Python's __aenter__ protocol boot handler.
     */
    public async open(): Promise<this> {
        this.isAlive = true;

        if (this.router.connectHandler) {
            try {
                await this.router.connectHandler(this);
            } catch (err) {
                this.isAlive = false;
                await this._rawClose();
                throw err;
            }
        }
        return this;
    }

    /**
     * Fires a one-way fire-and-forget message without expecting a return payload packet.
     */
    public async send(method: string, payload: any = null): Promise<void> {
        if (!this.isAlive) throw new ConnectionBrokenException();
        const frame: RPCFrame = { id: null, type: 'signal', method, payload };
        await this._dispatchFrame(frame);
    }

    /**
     * Issues a synchronous round-trip request with configurable timeout intervals.
     */
    public async call(method: string, payload: any = null, timeoutMs: number = 5000): Promise<any> {
        if (!this.isAlive) throw new ConnectionBrokenException();

        const callId = `rpc-${crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2, 11)}`;
        const frame: RPCFrame = { id: callId, type: 'request', method, payload };

        return new Promise((resolve, reject) => {
            const timer = setTimeout(() => {
                this.pendingCalls.delete(callId);
                reject(new Error(`Call to '${method}' timed out`));
            }, timeoutMs);

            this.pendingCalls.set(callId, { resolve, reject, timer });

            this._dispatchFrame(frame).catch((err) => {
                clearTimeout(timer);
                this.pendingCalls.delete(callId);
                reject(err);
            });
        });
    }

    /**
     * Symmetrical message processor fed directly by structural streaming handles.
     */
    protected async handleMessage(rawMessage: string): Promise<void> {
        if (!this.isAlive) return;

        try {
            const frame: RPCFrame = JSON.parse(rawMessage);

            for (const handler of this.router.receiveHandlers) {
                handler(this, frame);
            }

            const { type, id, method, payload, error } = frame;

            // Handle inbound response resolving an outstanding outbound call
            if (type === 'response' || type === 'error') {
                if (id && this.pendingCalls.has(id)) {
                    const deferred = this.pendingCalls.get(id)!;
                    clearTimeout(deferred.timer);
                    this.pendingCalls.delete(id);

                    if (type === 'error' || error) {
                        deferred.reject(new Error(error || "Remote exception occurred"));
                    } else {
                        deferred.resolve(payload);
                    }
                }
                return;
            }

            // Handle inbound requests arriving from the remote peer
            if (type === 'request' && id && method) {
                const route = this.router.routes.get(method);
                if (!route) {
                    await this._dispatchFrame({
                        id, type: 'error', error: `Method '${method}' not registered`
                    });
                    return;
                }

                try {
                    const result = await route(payload, this);
                    await this._dispatchFrame({ id, type: 'response', payload: result });
                } catch (execErr: any) {
                    await this._dispatchFrame({
                        id, type: 'error', error: execErr?.message || String(execErr)
                    });
                }
                return;
            }

            // Handle inbound fire-and-forget signals
            if (type === 'signal' && method) {
                const route = this.router.routes.get(method);
                if (route) {
                    Promise.resolve(route(payload, this)).catch(() => { });
                }
                return;
            }

        } catch (parseErr) {
            // Discard corrupted frames silently matching Python logic
        }
    }

    private async _dispatchFrame(frame: RPCFrame): Promise<void> {
        for (const handler of this.router.sendHandlers) {
            handler(this, frame);
        }
        await this._rawSend(JSON.stringify(frame));
    }

    /**
     * Clears tracking contexts and handles structural streaming shutdown.
     * Replicates Python's __aexit__ teardown mechanics.
     */
    public async close(): Promise<void> {
        this.isAlive = false;
        for (const [id, deferred] of this.pendingCalls.entries()) {
            clearTimeout(deferred.timer);
            deferred.reject(new Error("Connection closed explicitly"));
        }
        this.pendingCalls.clear();
        await this._rawClose();
    }
}
