#!/usr/bin/env python3
"""
project_token_usage.py
Benchmarks and projects daily, weekly, monthly, and yearly token usage and dollar costs
for the Hermes scientific agent environment and automated research routines.
"""

import sys
import os

# Pricing per 1,000,000 tokens (Google AI Studio)
PRICING = {
    "gemini-3.5-flash": {
        "prompt_uncached": 0.10,
        "prompt_cached": 0.025,
        "candidate_and_thinking": 0.40
    },
    "gemini-3.8-flash": {
        "prompt_uncached": 0.75,
        "prompt_cached": 0.1875,
        "candidate_and_thinking": 3.75
    }
}

# Empirical Measurements from Live Executions:
# 1. Literature Deep Reviews (2 papers/day via gemini-3.5-flash):
#    - Prompt: 145 tokens per paper * 2 = 290 tokens
#    - Output + Thinking (512 budget): 3,045 tokens * 2 = 6,090 tokens
#    Total = 6,380 tokens/day
REV_PROMPT = 145 * 2
REV_OUT_THINK = 3045 * 2
COST_REVIEWS = (REV_PROMPT / 1e6 * PRICING["gemini-3.5-flash"]["prompt_uncached"]) + \
               (REV_OUT_THINK / 1e6 * PRICING["gemini-3.5-flash"]["candidate_and_thinking"])

# 2. Morning Takeaway Delivery (1 run/day via gemini-3.8-flash):
#    - Injected script summary prompt: ~350 tokens
#    - 3-bullet insight output + thinking: ~550 tokens
#    Total = 900 tokens/day
DELIV_PROMPT = 350
DELIV_OUT_THINK = 550
COST_DELIVERY = (DELIV_PROMPT / 1e6 * PRICING["gemini-3.8-flash"]["prompt_uncached"]) + \
                (DELIV_OUT_THINK / 1e6 * PRICING["gemini-3.8-flash"]["candidate_and_thinking"])

# 3. Evening Research EOD Progress Log (1 run/day via gemini-3.8-flash):
#    - Git log sweep prompt: ~600 tokens
#    - Daily log entry generation: ~700 tokens
#    Total = 1,300 tokens/day
EOD_PROMPT = 600
EOD_OUT_THINK = 700
COST_EOD = (EOD_PROMPT / 1e6 * PRICING["gemini-3.8-flash"]["prompt_uncached"]) + \
           (EOD_OUT_THINK / 1e6 * PRICING["gemini-3.8-flash"]["candidate_and_thinking"])

# 4. Zero-Token Local Daemons:
#    - Workspace Knowledge Indexer (every 4 hrs): 0 tokens
#    - hermes-watch background monitors: 0 tokens
#    - agent-status / system-tune: 0 tokens
#    - hf-daily-papers raw API sweep: 0 tokens

DAILY_AUTO_TOKENS = (REV_PROMPT + REV_OUT_THINK) + (DELIV_PROMPT + DELIV_OUT_THINK) + (EOD_PROMPT + EOD_OUT_THINK)
DAILY_AUTO_COST = COST_REVIEWS + COST_DELIVERY + COST_EOD

def print_projection():
    print("\n" + "═" * 78)
    print(" 📊 HERMES SCIENTIFIC AGENT — DAILY TOKEN BENCHMARK & COST PROJECTION")
    print("═" * 78)
    
    print("\n1️⃣  Empirical Baseline: 100% Automated Background Routines (Daily)")
    print("─" * 78)
    print(f" • 2× In-Depth Paper Reviews (gemini-3.5-flash) : {REV_PROMPT + REV_OUT_THINK:6,d} tokens  |  ${COST_REVIEWS:.4f} / day")
    print(f" • Morning Digest Delivery    (gemini-3.8-flash) : {DELIV_PROMPT + DELIV_OUT_THINK:6,d} tokens  |  ${COST_DELIVERY:.4f} / day")
    print(f" • Evening EOD Progress Log   (gemini-3.8-flash) : {EOD_PROMPT + EOD_OUT_THINK:6,d} tokens  |  ${COST_EOD:.4f} / day")
    print(f" • Workspace Indexer (every 4h, local script)    :      0 tokens  |  $0.0000 / day")
    print(f" • Zero-Token Watchdogs (hermes-watch)           :      0 tokens  |  $0.0000 / day")
    print("─" * 78)
    print(f" TOTAL AUTOMATED BASELINE                        : {DAILY_AUTO_TOKENS:6,d} tokens  |  ${DAILY_AUTO_COST:.4f} / day")
    print(f"   ↳ Weekly Automated Baseline                   : {DAILY_AUTO_TOKENS * 7:6,d} tokens  |  ${DAILY_AUTO_COST * 7:.3f} / week")
    print(f"   ↳ Monthly Automated Baseline (30 Days)        : {DAILY_AUTO_TOKENS * 30:6,d} tokens  |  ${DAILY_AUTO_COST * 30:.2f} / month")
    print(f"   ↳ Yearly Automated Baseline (365 Days)        : {DAILY_AUTO_TOKENS * 365:6,d} tokens  |  ${DAILY_AUTO_COST * 365:.2f} / year")

    print("\n2️⃣  Projected Total Usage Under Different Research Workloads")
    print("─" * 78)
    
    scenarios = [
        ("A. Passive Day (Automated only + 2 quick queries)", 15000),
        ("B. Typical Research Day (Automated + 15 interactive turns)", 65000),
        ("C. Heavy Sprint Day (Automated + 40 turns, code & debugging)", 180000)
    ]

    print(f"{'Workload Scenario':<45} | {'Daily Tokens':<13} | {'Daily Cost':<10} | {'Monthly Cost'}")
    print("─" * 78)

    for name, user_tokens in scenarios:
        total_tokens = DAILY_AUTO_TOKENS + user_tokens
        # In interactive multi-turn, ~70% is prompt (benefiting from 75% cache discount), ~30% is output + thinking
        cached_prompt = user_tokens * 0.70
        output_thought = user_tokens * 0.30
        
        interactive_cost = (cached_prompt / 1e6 * PRICING["gemini-3.8-flash"]["prompt_cached"]) + \
                           (output_thought / 1e6 * PRICING["gemini-3.8-flash"]["candidate_and_thinking"])
        total_cost = DAILY_AUTO_COST + interactive_cost
        
        print(f"{name:<45} | {total_tokens:8,d} tok  | ${total_cost:7.4f}  | ${total_cost * 30:6.2f} / mo")

    print("─" * 78)

    print("\n3️⃣  Zero-Token Architecture Savings Breakdown")
    print("─" * 78)
    # Comparison: If training/log polling was done via LLM every 30s:
    # 2 calls/min * 60 = 120 calls/hr * 1,200 tokens = 144,000 tokens/hr * 8 hrs = 1,152,000 tokens/day ($2.50+/day)
    print(" • Continuous Polling LLM Pattern (Typical AI agents) : ~1.15M tokens/day  |  ~$75.00 / month")
    print(f" • IUABTW Zero-Token Event Watchdog Architecture       :       0 tokens/day  |  $ 0.00 / month")
    print(f" • Net Monthly Savings from Zero-Token Watchdogs      : ~34.5M tokens/month |  ~$75.00 / month saved!")
    print("═" * 78 + "\n")

if __name__ == "__main__":
    print_projection()
