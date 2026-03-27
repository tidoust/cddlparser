export function isAlpha(ch: string): boolean {
  return ("a" <= ch && ch <= "z") || ("A" <= ch && ch <= "Z");
}

export function isExtendedAlpha(ch: string): boolean {
  return isAlpha(ch) || "@_$".includes(ch);
}

export function isUint(literal: string): boolean {
  return (
    literal.length > 0 &&
    "123456789".includes(literal[0]!) &&
    [...literal].every(ch => "0123456789".includes(ch))
  );
}