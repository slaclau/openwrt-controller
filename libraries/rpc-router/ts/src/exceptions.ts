export class ConnectionBrokenException extends Error {
    constructor(message = "Connection broken") {
        super(message);
        this.name = "ConnectionBrokenException";
    }
}

export class ConnectionRefusedException extends Error {
    constructor(message = "Connection refused") {
        super(message);
        this.name = "ConnectionRefusedException";
    }
}