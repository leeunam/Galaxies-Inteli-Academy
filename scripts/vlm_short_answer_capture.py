"""Bounded byte-transparent tee and strict short-answer outcome, no response repair."""

import json

from scripts import vlm_encoder_probe as base

ANSWERS = ("yes", "no", "uncertain")


def decode(raw):
    def reject_constant(_):
        raise ValueError("constant")

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate_key")
            result[key] = value
        return result

    parsed = json.loads(
        raw.decode("utf-8"), object_pairs_hook=unique, parse_constant=reject_constant
    )
    if (
        type(parsed) is not dict
        or list(parsed) != ["answer"]
        or type(parsed["answer"]) is not str
        or parsed["answer"] not in ANSWERS
    ):
        raise ValueError("short_answer_contract")
    return parsed["answer"]


class Tee:
    """Return the original bytes unchanged, retaining at most the existing cap in memory."""

    def __init__(self, stream):
        self.stream = stream
        self.data = bytearray()

    def read(self, size):
        chunk = self.stream.read(size)
        self.data.extend(chunk[: max(0, base.LIMITS["stdout_bytes"] - len(self.data))])
        return chunk

    def close(self):
        self.stream.close()


def capture(argv, *, seconds, reserve, popen=None):
    """Reuse the frozen collector; discard its unrelated item_first decoding result."""
    factory = base.subprocess.Popen if popen is None else popen
    streams = []

    def start(*args, **kwargs):
        process = factory(*args, **kwargs)
        process.stdout = Tee(process.stdout)
        streams.append(process.stdout)
        return process

    result = base.capture(argv, seconds=seconds, reserve=reserve, popen=start)
    result.pop("native", None)
    result.pop("projected_value", None)
    # The old collector's decoder is for another schema. Its rejection is not
    # authority over this new contract; the same original bytes are parsed below.
    if result["stop_code"] == "stdout_invalid_original_schema":
        result["stop_code"] = None
    result.update(answer=None, format_status="not_assessed_technical_failure")
    if result["stop_code"] is None:
        try:
            result["answer"] = decode(bytes(streams[0].data))
            result["format_status"] = "valid"
        except (ValueError, TypeError, UnicodeError, RecursionError, IndexError):
            result["format_status"] = "invalid"
    return result
