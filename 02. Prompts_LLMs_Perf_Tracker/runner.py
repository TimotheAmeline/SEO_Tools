import datetime
from chatbot_client import query_chatbot
from analyzer import analyze_response
from history_manager import load_history

def run_tracking(prompts_df, platform_toggles, brand_keywords, force=False, log=None):
    results = []
    timestamp = datetime.datetime.utcnow().isoformat()

    # Load previous history and build lookup: (prompt_id, platform) -> previous rank
    previous_data = load_history()
    previous_lookup = {
        (row["prompt_id"], row["platform"]): row.get("rank")
        for row in previous_data
    }

    for i, row in prompts_df.iterrows():
        prompt = row["prompt"]
        prompt_id = row["prompt_id"]

        if log:
            log(f"📝 Prompt {i+1}/{len(prompts_df)}: '{prompt}'", "info")

        for platform, enabled in platform_toggles.items():
            if not enabled:
                continue

            # Check for duplicate unless force is enabled
            if not force and (prompt_id, platform) in previous_lookup:
                if log:
                    log(f"⚠️ Skipping {platform} - prompt already tracked.", "warning")
                continue

            try:
                if log:
                    log(f"→ Querying {platform}...", "info")

                response = query_chatbot(platform, prompt)

                if not response:
                    if log:
                        log(f"{platform} returned no output", "warning")
                    continue

                analysis = analyze_response(response, brand_keywords=brand_keywords)
                current_rank = analysis.get("rank")

                prev_rank = previous_lookup.get((prompt_id, platform))
                rank_change = None
                if prev_rank is not None and current_rank is not None:
                    try:
                        rank_change = int(prev_rank) - int(current_rank)
                    except:
                        rank_change = None

                if log:
                    log(
                        f"✓ {platform} | Mention: {analysis['brand_mentioned']} | "
                        f"Sentiment: {analysis['sentiment']} | Rank: {current_rank} | Change: {rank_change}",
                        "success"
                    )

                result_row = {
                    "timestamp": timestamp,
                    "prompt_id": prompt_id,
                    "platform": platform,
                    "prompt": prompt,
                    "response": response,
                    "brand_mentioned": analysis["brand_mentioned"],
                    "sentiment": analysis["sentiment"],
                    "rank": current_rank,
                    "previous_rank": prev_rank,
                    "rank_change": rank_change
                }
                results.append(result_row)

            except Exception as e:
                if log:
                    log(f"❌ Error with {platform}: {e}", "error")

    return results if results else None
