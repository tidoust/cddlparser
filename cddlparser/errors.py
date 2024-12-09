class ParserError(Exception):
    """
    CDDL tokenizer or parser error
    """

    def __init__(self, message: str = "A parsing error occurred"):
        self.message = message
        super().__init__(self.message)
