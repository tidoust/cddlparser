export class ParserError extends Error {
    /**
     * CDDL tokenizer or parser error
     */
    constructor(message: string = "A parsing error occurred") {
        super(message);
        this.name = "ParserError";
    }
}
