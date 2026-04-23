#!/usr/bin/env python3
"""
Analyze content style from text examples.

Usage:
    python3 tools/research_content_style.py --input examples.txt --analyze
    python3 tools/research_content_style.py --input examples.txt --creator "Alex Hormozi"

Input: a text file with example scripts, transcripts, or posts (one per section, separated by ---)
Output: .tmp/style_analysis.json — structured analysis of patterns

The style researcher agent uses this to build/refine style guides.
"""

import argparse
import json
import os
import re
from collections import Counter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT = os.path.join(ROOT, ".tmp", "style_analysis.json")


def load_examples(path):
    with open(path) as f:
        text = f.read()
    sections = [s.strip() for s in text.split("---") if s.strip()]
    return sections


def analyze_text(sections, creator=None):
    all_sentences = []
    all_words = []
    hooks = []
    ctas = []

    for section in sections:
        lines = [l.strip() for l in section.split("\n") if l.strip()]
        if not lines:
            continue

        # First line is likely the hook
        hooks.append(lines[0])
        # Last line is likely the CTA
        if len(lines) > 1:
            ctas.append(lines[-1])

        for line in lines:
            sentences = re.split(r'[.!?]+', line)
            for s in sentences:
                s = s.strip()
                if s:
                    words = s.split()
                    all_sentences.append(s)
                    all_words.extend(w.lower() for w in words)

    # Sentence length stats
    lengths = [len(s.split()) for s in all_sentences]
    avg_length = sum(lengths) / len(lengths) if lengths else 0
    short_pct = len([l for l in lengths if l <= 10]) / len(lengths) * 100 if lengths else 0

    # Word frequency (top 30)
    word_freq = Counter(all_words)
    # Filter out common stop words for the frequency list
    stop = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "shall", "can", "to", "of", "in", "for",
            "on", "with", "at", "by", "from", "as", "into", "through", "during",
            "before", "after", "and", "but", "or", "nor", "not", "so", "yet",
            "both", "either", "neither", "each", "every", "all", "any", "few",
            "more", "most", "other", "some", "such", "no", "than", "too", "very",
            "just", "about", "up", "out", "if", "then", "that", "this", "it",
            "its", "i", "you", "he", "she", "we", "they", "me", "him", "her",
            "us", "them", "my", "your", "his", "our", "their", "what", "which",
            "who", "whom", "how", "when", "where", "why"}
    top_words = [(w, c) for w, c in word_freq.most_common(60) if w not in stop][:30]

    # Hook patterns
    hook_patterns = Counter()
    for h in hooks:
        h_lower = h.lower()
        if h_lower.startswith(("most ", "the #1", "the biggest")):
            hook_patterns["bold_claim"] += 1
        elif h_lower.startswith(("stop ", "don't ", "never ")):
            hook_patterns["pattern_interrupt"] += 1
        elif re.match(r'^\d', h):
            hook_patterns["number_hook"] += 1
        elif h_lower.startswith(("i ", "i've ", "i just", "last ")):
            hook_patterns["story_hook"] += 1
        elif h.endswith("?"):
            hook_patterns["question_hook"] += 1
        else:
            hook_patterns["other"] += 1

    # Flesch-Kincaid approximation
    total_words_count = len(all_words)
    total_sentences_count = len(all_sentences)
    syllable_count = sum(count_syllables(w) for w in all_words)

    if total_sentences_count > 0 and total_words_count > 0:
        fk_grade = (0.39 * (total_words_count / total_sentences_count) +
                    11.8 * (syllable_count / total_words_count) - 15.59)
    else:
        fk_grade = 0

    analysis = {
        "creator": creator or "unknown",
        "samples_analyzed": len(sections),
        "sentence_stats": {
            "average_words_per_sentence": round(avg_length, 1),
            "pct_under_10_words": round(short_pct, 1),
            "total_sentences": total_sentences_count,
        },
        "reading_level": {
            "flesch_kincaid_grade": round(fk_grade, 1),
            "assessment": "3rd grade or below" if fk_grade <= 3 else
                         "elementary" if fk_grade <= 5 else
                         "middle school" if fk_grade <= 8 else "advanced",
        },
        "top_words": [{"word": w, "count": c} for w, c in top_words],
        "hook_patterns": dict(hook_patterns),
        "sample_hooks": hooks[:10],
        "sample_ctas": ctas[:10],
    }
    return analysis


def count_syllables(word):
    word = word.lower().strip(".,!?;:'\"")
    if len(word) <= 2:
        return 1
    vowels = "aeiouy"
    count = 0
    prev_vowel = False
    for char in word:
        is_vowel = char in vowels
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    if word.endswith("e") and count > 1:
        count -= 1
    return max(count, 1)


def main():
    parser = argparse.ArgumentParser(description="Analyze content style patterns")
    parser.add_argument("--input", type=str, required=True, help="Path to text file with examples")
    parser.add_argument("--creator", type=str, default=None, help="Creator name")
    parser.add_argument("--analyze", action="store_true", help="Run analysis")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: file not found: {args.input}")
        return

    sections = load_examples(args.input)
    if not sections:
        print("Error: no content sections found. Separate examples with ---")
        return

    print(f"Loaded {len(sections)} examples from {args.input}")
    analysis = analyze_text(sections, creator=args.creator)

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w") as f:
        json.dump(analysis, f, indent=2)

    print(f"\nStyle Analysis — {analysis['creator']}")
    print(f"Samples: {analysis['samples_analyzed']}")
    print(f"Avg sentence length: {analysis['sentence_stats']['average_words_per_sentence']} words")
    print(f"Reading level: {analysis['reading_level']['assessment']} (FK grade {analysis['reading_level']['flesch_kincaid_grade']})")
    print(f"Hook patterns: {analysis['hook_patterns']}")
    print(f"Top words: {', '.join(w['word'] for w in analysis['top_words'][:15])}")
    print(f"\nOutput: {OUTPUT}")


if __name__ == "__main__":
    main()
