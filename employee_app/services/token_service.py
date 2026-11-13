"""
Token counting.

Why count tokens? An AI agent reads responses into its context window,
and the window is measured in tokens. Counting the tokens we send gives
a number for "how much of the agent's context did the trap fill?".

This is an ESTIMATE of context use: different models use different
tokenizers, so the exact count for a real model would differ a little.
Say this in your report.

If tiktoken is missing or cannot download its encoding file (offline PC),
the app keeps working and uses  tokens ~= characters / 4  instead.
method() tells you which one is active.
"""

import config as cfg


_encoder = None
_method = "estimate:chars/4"


def _load():
    global _encoder, _method

    if cfg.TOKEN_COUNTER != "tiktoken":
        _encoder = None
        _method = "estimate:chars/4"
        return

    try:
        import tiktoken

        _encoder = tiktoken.get_encoding(cfg.TOKEN_ENCODING)
        _method = f"tiktoken:{cfg.TOKEN_ENCODING}"

    except Exception as error:
        _encoder = None
        _method = "estimate:chars/4"
        print(
            f"[token_service] tiktoken not available "
            f"({error.__class__.__name__}). Using the chars/4 estimate."
        )


def count_tokens(text: str) -> int:
    if not text:
        return 0

    if _encoder is not None:
        # disallowed_special=() so any text can be counted, never raises
        return len(_encoder.encode(text, disallowed_special=()))

    return max(1, len(text) // 4)


def method() -> str:
    return _method


_load()
print(f"[token_service] token counter: {_method}")
