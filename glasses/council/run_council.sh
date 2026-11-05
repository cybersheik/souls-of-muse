#!/bin/zsh
# Консилиум Muse: прогон договора через MoA-пресет muse-council (Hermes, профиль Jack).
# Использование: ./run_council.sh [contract.md] [playbook.md]
# Результат: council/out/<timestamp>/{query.md,answer.md}
set -euo pipefail
cd "$(dirname "$0")"
CONTRACT="${1:-demo-contract.md}"
PLAYBOOK="${2:-playbook-v0.md}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="out/$STAMP"; mkdir -p "$OUT"

{
  cat <<'EOF'
You are the Souls of Muse council: several Meta Muse models advise, and you, the aggregator, synthesise. A 19-year-old musician photographed this contract with her glasses and will hear your answer in her ear. Review it under English commercial law.

Produce exactly three parts:
1. EAR (max 90 words, spoken style, Russian): what to strike, what to discuss, one number to negotiate.
2. REVIEW (written, English): clause-by-clause findings with clause numbers, severity (red/amber/green), the fair alternative, and case or statute references where relevant (e.g. Panayiotou v Sony Music 1994, Copyright, Designs and Patents Act 1988).
3. The sentence, in English and Russian: "This is an opinion from several AI models, not legal advice." / "Это мнение нескольких ИИ-моделей, а не юридическая консультация."

Use the playbook below as our standard positions. Do not invent clauses that are not in the contract.

=== PLAYBOOK ===
EOF
  cat "$PLAYBOOK"
  echo; echo "=== CONTRACT ==="
  cat "$CONTRACT"
} > "$OUT/query.md"

echo "query: $OUT/query.md ($(wc -c < "$OUT/query.md") bytes)"
START=$(date +%s)
hermes -p jack chat --provider moa -m muse-council -Q --oneshot --max-turns 3 --query-file "$OUT/query.md" | tee "$OUT/answer.md"
echo; echo "elapsed: $(( $(date +%s) - START )) s → $OUT/answer.md"
