class CompactFormatter:
    """
    Format a single-line compact status for Claude usage monitoring.
    """

    def format(
        self,
        tokens_used,
        token_limit,
        usage_percentage,
        burn_rate,
        predicted_end_str,
        reset_time_str,
        current_time_str,
        tokens_left,
        language=None,
    ):
        # Affichage multilingue minimaliste (français inclus)
        if language == "fr":
            return (
                f"Claude : {tokens_used:,}/{token_limit:,} ({usage_percentage:.1f}%) | "
                f"🔥{burn_rate:.1f}/min | Fin: {predicted_end_str} | Reset: {reset_time_str} | {current_time_str}"
            )
        elif language == "es":
            return (
                f"Claude : {tokens_used:,}/{token_limit:,} ({usage_percentage:.1f}%) | "
                f"🔥{burn_rate:.1f}/min | Fin: {predicted_end_str} | Reset: {reset_time_str} | {current_time_str}"
            )
        elif language == "de":
            return (
                f"Claude : {tokens_used:,}/{token_limit:,} ({usage_percentage:.1f}%) | "
                f"🔥{burn_rate:.1f}/min | Ende: {predicted_end_str} | Reset: {reset_time_str} | {current_time_str}"
            )
        else:
            return (
                f"Claude : {tokens_used:,}/{token_limit:,} ({usage_percentage:.1f}%) | "
                f"🔥{burn_rate:.1f}/min | End: {predicted_end_str} | Reset: {reset_time_str} | {current_time_str}"
            )
