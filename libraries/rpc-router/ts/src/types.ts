import { AbstractDuplexConnection } from './protocol';

export type FrameType = 'signal' | 'request' | 'response' | 'error';

/**
 * The structured wire frame format matching your Python JSON protocol.
 */
export interface RPCFrame {
    id: string | null;
    type: FrameType;
    method?: string;
    payload?: any;
    error?: string;
}

// Interceptor and Lifecycle Callback Signatures
export type Handler = (ctx: AbstractDuplexConnection, frame: RPCFrame) => any;
export type ConnectHandler = (ctx: AbstractDuplexConnection) => Promise<void> | void;
export type RouteHandler = (payload: any, ctx: AbstractDuplexConnection) => Promise<any> | any;

/**
 * Symmetrical routing registry using an intuitive event syntax.
 */
export class DuplexRouter {
    public routes = new Map<string, RouteHandler>();
    public connectHandler: ConnectHandler | null = null;
    public receiveHandlers: Handler[] = [];
    public sendHandlers: Handler[] = [];

    /**
     * Registers an execution route handler for an inbound method name.
     */
    public on(method: string, handler: RouteHandler): this {
        this.routes.set(method, handler);
        return this;
    }

    /**
     * Registers a connection initializer hook.
     */
    public onConnect(handler: ConnectHandler): this {
        this.connectHandler = handler;
        return this;
    }

    /**
     * Appends an interceptor middleware executed immediately before parsing frames.
     */
    public beforeReceive(handler: Handler): this {
        this.receiveHandlers.push(handler);
        return this;
    }

    /**
     * Appends an interceptor middleware executed immediately prior to wire transmission.
     */
    public beforeSend(handler: Handler): this {
        this.sendHandlers.push(handler);
        return this;
    }
}
