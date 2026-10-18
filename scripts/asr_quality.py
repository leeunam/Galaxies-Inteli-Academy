"""Reference-based ASR metrics. No reference means no measured transcript accuracy."""

import re
import unicodedata


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text).casefold()
    text = "".join(" " if unicodedata.category(c).startswith("P") else c for c in text)
    return re.sub(r"\s+", " ", text).strip()


def distance(reference, hypothesis) -> int:
    previous = list(range(len(hypothesis) + 1))
    for i, a in enumerate(reference, 1):
        current = [i]
        for j, b in enumerate(hypothesis, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (a != b)))
        previous = current
    return previous[-1]


def transcript_errors(reference: str, hypothesis: str) -> dict:
    ref, hyp = normalize(reference), normalize(hypothesis)
    word_errors = distance(ref.split(), hyp.split())
    # CER includes normalized spaces; accents and lexical forms are preserved.
    char_errors = distance(ref, hyp)
    return {
        "normalization": "NFC_casefold_punctuation_to_space_collapse_spaces_v1",
        "word_errors": word_errors,
        "reference_words": len(ref.split()),
        "wer": word_errors / len(ref.split()) if ref.split() else None,
        "character_errors": char_errors,
        "reference_characters": len(ref),
        "cer": char_errors / len(ref) if ref else None,
        "empty_reference_match": ref == hyp if not ref else None,
    }


def evaluate_references(references: list[dict], hypotheses: dict[str, dict]) -> dict:
    if not references:
        raise ValueError("Human references are required before measuring accuracy")
    rows = []
    seen = set()
    for reference in references:
        video_id = reference["video_id"]
        if video_id in seen or video_id not in hypotheses:
            raise ValueError("Duplicate or unknown reference video ID")
        seen.add(video_id)
        if reference.get("listened") is not True or not reference.get("reviewer"):
            raise ValueError("A human listening review is required")
        if not isinstance(reference.get("text"), str):
            raise TypeError("Reference text must be supplied explicitly")
        audio_type = reference.get("audio_type")
        if audio_type not in {
            "speech",
            "singing",
            "mixed",
            "instrumental",
            "no_vocal",
            "inaudible",
        }:
            raise ValueError("Audio type must be reviewed")
        if reference.get("uncertain_spans") or audio_type == "inaudible":
            rows.append({"video_id": video_id, "status": "excluded_uncertain_reference"})
            continue
        if not normalize(reference["text"]) and audio_type not in {"instrumental", "no_vocal"}:
            raise ValueError("An empty reference requires a confirmed absence of vocals")
        hypothesis = hypotheses[video_id]
        rows.append(
            {
                "video_id": video_id,
                "status": "evaluated_against_human_reference",
                "audio_type": audio_type,
                "baseline": transcript_errors(
                    reference["text"], hypothesis["replayed_baseline"]["transcript"]
                ),
                "diagnostic": transcript_errors(reference["text"], hypothesis["transcript"]),
            }
        )
    totals = {}
    for mode in ["baseline", "diagnostic"]:
        evaluated = [r[mode] for r in rows if mode in r]
        words = sum(r["reference_words"] for r in evaluated)
        characters = sum(r["reference_characters"] for r in evaluated)
        word_errors = sum(r["word_errors"] for r in evaluated)
        character_errors = sum(r["character_errors"] for r in evaluated)
        totals[mode] = {
            "reference_words": words,
            "word_errors": word_errors,
            "wer": word_errors / words if words else None,
            "reference_characters": characters,
            "character_errors": character_errors,
            "cer": character_errors / characters if characters else None,
        }
    return {
        "videos": rows,
        "totals": totals,
        "scope": "small assisted pilot, not population ASR accuracy",
    }


def main():
    import argparse
    import json
    from pathlib import Path

    from scripts.pilot_licensed_media import atomic_json
    from scripts.pilot_youtube_media import private_path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--references", type=Path, required=True)
    parser.add_argument("--hypotheses-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    references = json.loads(private_path(args.references).read_text())
    root, output = private_path(args.hypotheses_root), private_path(args.output)
    if output.exists():
        parser.error("Preserve previous measurements; use a fresh output path")
    hypotheses = {p.parent.name: json.loads(p.read_text()) for p in root.glob("*/features.json")}
    result = evaluate_references(references, hypotheses)
    atomic_json(output, result)
    print(
        json.dumps(
            {
                "evaluated": sum(
                    r["status"] == "evaluated_against_human_reference" for r in result["videos"]
                )
            }
        )
    )


if __name__ == "__main__":
    main()
