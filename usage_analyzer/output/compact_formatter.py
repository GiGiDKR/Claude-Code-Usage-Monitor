"""
Formatter compact pour affichage sur une ligne unique (mode tmux, terminaux étroits).
"""

from datetime import datetime

from usage_analyzer.themes import get_themed_console, print_themed


class CompactFormatter:
    """Formatter pour l'affichage compact sur une ligne."""

    def __init__(self):
        self.console = get_themed_console()

    def format_compact_line(
        self,
        tokens_used,
        token_limit,
        burn_rate,
        predicted_end,
        reset_time,
        current_time,
    ):
        """Formate les données en une ligne compacte."""
        # Format cible :
        #   Claude : 9.2K/35K (26.3%) | 🔥51.9/min | Fin : 02:13 | Reset : 18:00 | 17:57:08
        percent = (tokens_used / token_limit * 100) if token_limit else 0
        tokens_str = (
            f"{self._format_tokens(tokens_used)}/"
            f"{self._format_tokens(token_limit)} ({percent:.1f}%)"
        )
        burn_str = f"🔥{burn_rate:.1f}/min" if burn_rate is not None else ""
        end_str = f"Fin : {predicted_end}" if predicted_end else ""
        reset_str = f"Reset : {reset_time}" if reset_time else ""
        now_str = (
            current_time.strftime("%H:%M:%S")
            if isinstance(current_time, datetime)
            else str(current_time)
        )
        parts = [f"Claude : {tokens_str}", burn_str, end_str, reset_str, now_str]
        # Filtrer les vides et joindre
        return " | ".join([p for p in parts if p])

    def print_compact_status(self, active_block, data, args):
        """Affiche le statut en mode compact avec gestion des thèmes."""
        # Extraction des données nécessaires
        tokens_used = active_block.get("totalTokens", 0)
        token_limit = data.get("token_limit", 0)

        # Calcul du burn rate depuis active_block
        burn_rate_data = active_block.get("burnRate")
        burn_val = burn_rate_data.get("tokensPerMinute", 0) if burn_rate_data else 0

        predicted_end = data.get("predicted_end", "")
        reset_time = data.get("reset_time", "")
        now = datetime.now()

        line = self.format_compact_line(
            tokens_used, token_limit, burn_val, predicted_end, reset_time, now
        )
        print_themed(line, style="header")

    def _format_tokens(self, tokens):
        """Convertit les tokens en format K/M pour économiser l'espace."""
        if not isinstance(tokens, int) or tokens < 0:
            raise ValueError("tokens doit être un entier non négatif")
        if tokens >= 1_000_000:
            return f"{tokens / 1_000_000:.1f}M"
        elif tokens >= 1_000:
            return f"{tokens / 1_000:.1f}K"
        return str(tokens)

    def _handle_critical_notifications(self, notifications):
        """Gère l'affichage des notifications critiques même en mode compact."""
        for notif in notifications:
            print_themed(notif, style="error")
