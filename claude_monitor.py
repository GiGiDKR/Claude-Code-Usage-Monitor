#!/usr/bin/env python3

import argparse
import sys
import threading
from datetime import datetime, timedelta

import pytz

from usage_analyzer.api import analyze_usage
from usage_analyzer.output import CompactFormatter
from usage_analyzer.themes import ThemeType, get_themed_console, print_themed

# All internal calculations use UTC, display timezone is configurable
UTC_TZ = pytz.UTC
DEFAULT_TIMEZONE = "Europe/Warsaw"

# Notification persistence configuration
NOTIFICATION_MIN_DURATION = 5  # seconds - minimum time to display notifications

# Global notification state tracker
notification_states = {
    "switch_to_custom": {"triggered": False, "timestamp": None},
    "exceed_max_limit": {"triggered": False, "timestamp": None},
    "tokens_will_run_out": {"triggered": False, "timestamp": None},
}


def get_display_timezone(timezone_str):
    """Get a timezone object, falling back to default if invalid."""
    try:
        return pytz.timezone(timezone_str)
    except pytz.exceptions.UnknownTimeZoneError:
        return pytz.timezone(DEFAULT_TIMEZONE)


def update_notification_state(notification_type, condition_met, current_time):
    """Update notification state and return whether to show notification."""
    state = notification_states[notification_type]

    if condition_met:
        if not state["triggered"]:
            # First time triggering - record timestamp
            state["triggered"] = True
            state["timestamp"] = current_time
        return True
    else:
        if state["triggered"]:
            # Check if minimum duration has passed
            elapsed = (current_time - state["timestamp"]).total_seconds()
            if elapsed >= NOTIFICATION_MIN_DURATION:
                # Reset state after minimum duration
                state["triggered"] = False
                state["timestamp"] = None
                return False
            else:
                # Still within minimum duration - keep showing
                return True
        return False


# Terminal handling for Unix-like systems
try:
    import termios

    HAS_TERMIOS = True
except ImportError:
    HAS_TERMIOS = False


def format_time(minutes):
    """Format minutes into human-readable time (e.g., '3h 45m')."""
    if minutes < 60:
        return f"{int(minutes)}m"
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    if mins == 0:
        return f"{hours}h"
    return f"{hours}h {mins}m"


def create_token_progress_bar(percentage, width=50):
    """Create a token usage progress bar with bracket style."""
    filled = int(width * percentage / 100)
    green_bar = "█" * filled
    red_bar = "░" * (width - filled)

    if percentage >= 90:
        return f"🟢 [[cost.high]{green_bar}[cost.medium]{red_bar}[/]] {percentage:.1f}%"
    elif percentage >= 50:
        return f"🟢 [[cost.medium]{green_bar}[/][table.border]{red_bar}[/]] {percentage:.1f}%"
    else:
        return (
            f"🟢 [[cost.low]{green_bar}[/][table.border]{red_bar}[/]] {percentage:.1f}%"
        )


def create_time_progress_bar(elapsed_minutes, total_minutes, width=50):
    """Create a time progress bar showing time until reset."""
    if total_minutes <= 0:
        percentage = 0
    else:
        percentage = min(100, (elapsed_minutes / total_minutes) * 100)

    filled = int(width * percentage / 100)
    blue_bar = "█" * filled
    red_bar = "░" * (width - filled)

    remaining_time = format_time(max(0, total_minutes - elapsed_minutes))
    return (
        f"⏰ [[progress.bar]{blue_bar}[/][table.border]{red_bar}[/]] {remaining_time}"
    )


def print_header():
    """Return the stylized header with sparkles as a list of strings."""
    # Build header components for theme-aware styling
    sparkles = "✦ ✧ ✦ ✧"
    title = "CLAUDE CODE USAGE MONITOR"
    separator = "=" * 60

    return [
        f"[header]{sparkles}[/] [header]{title}[/] [header]{sparkles}[/]",
        f"[table.border]{separator}[/]",
        "",
    ]


def show_loading_screen():
    """Display a loading screen while fetching data."""
    screen_buffer = []
    screen_buffer.append("\033[H")  # Home position
    screen_buffer.extend(print_header())
    screen_buffer.append("")
    screen_buffer.append("[info]⏳ Loading...[/]")
    screen_buffer.append("")
    screen_buffer.append("[warning]Fetching Claude usage data...[/]")
    screen_buffer.append("")
    screen_buffer.append("[dim]This may take a few seconds[/]")

    # Clear screen and print buffer
    print("\033[2J" + "\n".join(screen_buffer) + "\033[J", end="", flush=True)


def get_velocity_indicator(burn_rate):
    """Get velocity emoji based on burn rate."""
    if burn_rate < 50:
        return "🐌"  # Slow
    elif burn_rate < 150:
        return "➡️"  # Normal
    elif burn_rate < 300:
        return "🚀"  # Fast
    else:
        return "⚡"  # Very fast


def calculate_hourly_burn_rate(blocks, current_time):
    """Calculate burn rate based on all sessions in the last hour."""
    if not blocks:
        return 0

    one_hour_ago = current_time - timedelta(hours=1)
    total_tokens = 0

    for block in blocks:
        start_time_str = block.get("startTime")
        if not start_time_str:
            continue

        # Parse start time - data from usage_analyzer is in UTC
        start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
        # Ensure it's in UTC for calculations
        if start_time.tzinfo is None:
            start_time = UTC_TZ.localize(start_time)
        else:
            start_time = start_time.astimezone(UTC_TZ)

        # Skip gaps
        if block.get("isGap", False):
            continue

        # Determine session end time
        if block.get("isActive", False):
            # For active sessions, use current time
            session_actual_end = current_time
        else:
            # For completed sessions, use actualEndTime or current time
            actual_end_str = block.get("actualEndTime")
            if actual_end_str:
                session_actual_end = datetime.fromisoformat(
                    actual_end_str.replace("Z", "+00:00")
                )
                # Ensure it's in UTC for calculations
                if session_actual_end.tzinfo is None:
                    session_actual_end = UTC_TZ.localize(session_actual_end)
                else:
                    session_actual_end = session_actual_end.astimezone(UTC_TZ)
            else:
                session_actual_end = current_time

        # Check if session overlaps with the last hour
        if session_actual_end < one_hour_ago:
            # Session ended before the last hour
            continue

        # Calculate how much of this session falls within the last hour
        session_start_in_hour = max(start_time, one_hour_ago)
        session_end_in_hour = min(session_actual_end, current_time)

        if session_end_in_hour <= session_start_in_hour:
            continue

        # Calculate portion of tokens used in the last hour
        total_session_duration = (
            session_actual_end - start_time
        ).total_seconds() / 60  # minutes
        hour_duration = (
            session_end_in_hour - session_start_in_hour
        ).total_seconds() / 60  # minutes

        if total_session_duration > 0:
            session_tokens = block.get("totalTokens", 0)
            tokens_in_hour = session_tokens * (hour_duration / total_session_duration)
            total_tokens += tokens_in_hour

    # Return tokens per minute
    return total_tokens / 60 if total_tokens > 0 else 0


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Claude Token Monitor - Real-time token usage monitoring"
    )
    parser.add_argument(
        "--plan",
        type=str,
        default="pro",
        choices=["pro", "max5", "max20", "custom_max"],
        help='Claude plan type (default: pro). Use "custom_max" to auto-detect from highest previous block',
    )
    parser.add_argument(
        "--reset-hour", type=int, help="Change the reset hour (0-23) for daily limits"
    )
    parser.add_argument(
        "--timezone",
        type=str,
        default="Europe/Warsaw",
        help="Timezone for reset times (default: Europe/Warsaw). Examples: US/Eastern, Asia/Tokyo, UTC",
    )
    parser.add_argument(
        "--theme",
        type=str,
        choices=["light", "dark", "auto"],
        help="Theme to use (auto-detects if not specified). Set to 'auto' for automatic detection based on terminal",
    )
    parser.add_argument(
        "--theme-debug",
        action="store_true",
        help="Show theme detection debug information and exit",
    )
    parser.add_argument(
        "--compact",
        "-c",
        action="store_true",
        help="Compact single-line display mode for tmux integration",
    )
    return parser.parse_args()


def get_token_limit(plan, blocks=None):
    # TODO calculate old based on limits
    limits = {"pro": 44000, "max5": 220000, "max20": 880000}

    """Get token limit based on plan type."""
    if plan == "custom_max" and blocks:
        max_tokens = 0
        for block in blocks:
            if not block.get("isGap", False) and not block.get("isActive", False):
                tokens = block.get("totalTokens", 0)
                if tokens > max_tokens:
                    max_tokens = tokens
        return max_tokens if max_tokens > 0 else limits["pro"]

    return limits.get(plan, 44000)


def setup_terminal():
    """Setup terminal for raw mode to prevent input interference."""
    if not HAS_TERMIOS or not sys.stdin.isatty():
        return None

    try:
        # Save current terminal settings
        old_settings = termios.tcgetattr(sys.stdin)
        # Set terminal to non-canonical mode (disable echo and line buffering)
        new_settings = termios.tcgetattr(sys.stdin)
        new_settings[3] = new_settings[3] & ~(termios.ECHO | termios.ICANON)
        termios.tcsetattr(sys.stdin, termios.TCSANOW, new_settings)
        return old_settings
    except Exception:
        return None


def restore_terminal(old_settings):
    """Restore terminal to original settings."""
    # Show cursor and exit alternate screen buffer
    print("\033[?25h\033[?1049l", end="", flush=True)

    if old_settings and HAS_TERMIOS and sys.stdin.isatty():
        try:
            termios.tcsetattr(sys.stdin, termios.TCSANOW, old_settings)
        except Exception:
            pass


def flush_input():
    """Flush any pending input to prevent display corruption."""
    if HAS_TERMIOS and sys.stdin.isatty():
        try:
            termios.tcflush(sys.stdin, termios.TCIFLUSH)
        except Exception:
            pass


def fetch_and_validate_data():
    """Fetch usage data and validate it's available."""
    data = analyze_usage()
    if not data or "blocks" not in data:
        return None
    return data


def find_active_block(blocks):
    """Find the active block from a list of blocks."""
    for block in blocks:
        if block.get("isActive", False):
            return block
    return None


def process_token_data(active_block, args, blocks, token_limit):
    """Process token data and handle limit checking/switching."""
    tokens_used = active_block.get("totalTokens", 0)
    original_limit = get_token_limit(args.plan)

    # Check if tokens exceed limit and switch to custom_max if needed
    if tokens_used > token_limit and args.plan != "custom_max":
        token_limit = get_token_limit("custom_max", blocks)

    tokens_left = max(0, token_limit - tokens_used)
    usage_percentage = (tokens_used / token_limit * 100) if token_limit else 0

    return {
        "tokens_used": tokens_used,
        "token_limit": token_limit,
        "original_limit": original_limit,
        "tokens_left": tokens_left,
        "usage_percentage": usage_percentage,
    }


def process_time_data(active_block, current_time):
    """Process time-related data from active block."""
    # Extract startTime from active block
    start_time_str = active_block.get("startTime")
    if start_time_str:
        start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
        if start_time.tzinfo is None:
            start_time = UTC_TZ.localize(start_time)
        else:
            start_time = start_time.astimezone(UTC_TZ)
    else:
        start_time = current_time

    # Extract endTime from active block
    end_time_str = active_block.get("endTime")
    if end_time_str:
        reset_time = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
        if reset_time.tzinfo is None:
            reset_time = UTC_TZ.localize(reset_time)
        else:
            reset_time = reset_time.astimezone(UTC_TZ)
    else:
        # Fallback: if no endTime, estimate 5 hours from startTime
        reset_time = start_time + timedelta(hours=5)

    return {"start_time": start_time, "reset_time": reset_time}


def calculate_predictions(
    current_time, reset_time, burn_rate, tokens_left, timezone_str
):
    """Calculate predicted end time and format times for display."""
    # Predicted end calculation
    if burn_rate > 0 and tokens_left > 0:
        minutes_to_depletion = tokens_left / burn_rate
        predicted_end_time = current_time + timedelta(minutes=minutes_to_depletion)
    else:
        predicted_end_time = reset_time

    # Convert to configured timezone for display
    local_tz = get_display_timezone(timezone_str)
    predicted_end_local = predicted_end_time.astimezone(local_tz)
    reset_time_local = reset_time.astimezone(local_tz)

    predicted_end_str = predicted_end_local.strftime("%H:%M")
    reset_time_str = reset_time_local.strftime("%H:%M")

    return {
        "predicted_end_time": predicted_end_time,
        "predicted_end_str": predicted_end_str,
        "reset_time_str": reset_time_str,
    }


def handle_notifications(
    token_data, predicted_end_time, reset_time, current_time, args
):
    """Handle notification state updates and return which notifications to show."""
    show_switch_notification = update_notification_state(
        "switch_to_custom",
        token_data["token_limit"] > token_data["original_limit"],
        current_time,
    )
    show_exceed_notification = update_notification_state(
        "exceed_max_limit",
        token_data["tokens_used"] > token_data["token_limit"],
        current_time,
    )
    show_tokens_will_run_out = update_notification_state(
        "tokens_will_run_out", predicted_end_time < reset_time, current_time
    )

    return {
        "show_switch": show_switch_notification,
        "show_exceed": show_exceed_notification,
        "show_will_run_out": show_tokens_will_run_out,
    }


def create_no_session_compact_line(token_limit, timezone_str):
    """Create compact line for when there's no active session."""
    now = datetime.now(UTC_TZ)
    display_tz = get_display_timezone(timezone_str)
    current_time_display = now.astimezone(display_tz)
    current_time_str = current_time_display.strftime("%H:%M:%S")
    compact_line = (
        f"Claude : 0/{token_limit:,} (0.0%) | 🔥0.0/min | "
        f"No active session | {current_time_str}"
    )
    return compact_line


def display_error_screen(error_message="Failed to get usage data"):
    """Display error screen with header and error message."""
    screen_buffer = []
    screen_buffer.append("\033[H")  # Home position
    screen_buffer.extend(print_header())
    screen_buffer.append(f"[error]{error_message}[/]")
    screen_buffer.append("")
    screen_buffer.append("[warning]Possible causes:[/]")
    screen_buffer.append("  • You're not logged into Claude")
    screen_buffer.append("  • Network connection issues")
    screen_buffer.append("")
    screen_buffer.append("[dim]Retrying in 3 seconds... (Ctrl+C to exit)[/]")

    console = get_themed_console()
    console.clear()
    for line in screen_buffer[1:]:  # Skip position control
        console.print(line)


def run_compact_mode(args, token_limit, compact_formatter, stop_event):
    """Handle compact mode monitoring loop."""
    while True:
        # Flush any pending input to prevent display corruption
        flush_input()

        # Build screen buffer for compact mode
        screen_buffer = []
        screen_buffer.append("\033[H")  # Home position

        data = fetch_and_validate_data()
        if not data:
            compact_line = (
                f"Claude : Error fetching data | {datetime.now().strftime('%H:%M:%S')}"
            )
            screen_buffer.append(compact_line)
            # Clear screen and print compact line
            console = get_themed_console()
            console.clear()
            for line in screen_buffer[1:]:
                console.print(line)
            stop_event.wait(timeout=3.0)
            continue

        active_block = find_active_block(data["blocks"])

        if not active_block:
            # Compact mode for no active session
            no_session_line = create_no_session_compact_line(token_limit, args.timezone)
            screen_buffer.append(no_session_line)
            # Clear screen and print compact line
            console = get_themed_console()
            console.clear()
            for line in screen_buffer[1:]:
                console.print(line)
            stop_event.wait(timeout=3.0)
            continue

        # Extract and process token data
        token_data = process_token_data(active_block, args, data["blocks"], token_limit)

        # Extract and process time data
        time_data = process_time_data(active_block, datetime.now(UTC_TZ))

        # Always use UTC for internal calculations
        current_time = datetime.now(UTC_TZ)

        # Calculate burn rate from ALL sessions in the last hour
        burn_rate = calculate_hourly_burn_rate(data["blocks"], current_time)

        # Calculate time to reset
        time_to_reset = time_data["reset_time"] - current_time
        minutes_to_reset = time_to_reset.total_seconds() / 60

        # Calculate predictions for display
        predictions = calculate_predictions(
            current_time,
            time_data["reset_time"],
            burn_rate,
            token_data["tokens_left"],
            args.timezone,
        )

        # Create the compact line
        if compact_formatter:
            burn_rate_data = active_block.get("burnRate")
            burn_val = (
                burn_rate_data.get("tokensPerMinute", 0)
                if burn_rate_data
                else burn_rate
            )

            line = compact_formatter.format_compact_line(
                token_data["tokens_used"],
                token_data["token_limit"],
                burn_val,
                predictions["predicted_end_str"],
                predictions["reset_time_str"],
                current_time,
            )
            screen_buffer.append(line)

        # Handle notifications
        notifications = handle_notifications(
            token_data,
            predictions["predicted_end_time"],
            time_data["reset_time"],
            current_time,
            args,
        )

        # Add critical notifications if necessary
        if notifications["show_switch"]:
            screen_buffer.append("")
            warning_msg = (
                f"🔄 WARNING: Switched to custom_max ({token_data['token_limit']:,})"
            )
            screen_buffer.append(warning_msg)
        if notifications["show_exceed"]:
            screen_buffer.append("")
            error_msg = (
                f"🚨 ERROR: TOKENS EXCEEDED MAX LIMIT! "
                f"({token_data['tokens_used']:,} > "
                f"{token_data['token_limit']:,})"
            )
            screen_buffer.append(error_msg)
        if notifications["show_will_run_out"]:
            screen_buffer.append("")
            screen_buffer.append("⚠️ ERROR: Tokens will run out BEFORE reset!")

        # Clear screen and print compact display
        console = get_themed_console()
        console.clear()
        for line in screen_buffer[1:]:  # Skip position control
            console.print(line)

        stop_event.wait(timeout=3.0)


def run_normal_mode(args, token_limit, stop_event):
    """Handle normal mode monitoring loop."""
    while True:
        # Flush any pending input to prevent display corruption
        flush_input()

        # Build complete screen in buffer
        screen_buffer = []
        screen_buffer.append("\033[H")  # Home position

        data = fetch_and_validate_data()
        if not data:
            display_error_screen()
            # Clear screen and print buffer with theme support
            console = get_themed_console()
            console.clear()
            for line in screen_buffer[1:]:  # Skip position control
                console.print(line)
            stop_event.wait(timeout=3.0)
            continue

        active_block = find_active_block(data["blocks"])

        if not active_block:
            # Normal mode for no active session
            screen_buffer.extend(print_header())
            screen_buffer.append(
                "📊 [value]Token Usage:[/]    🟢 [[cost.low]" + "░" * 50 + "[/]] 0.0%"
            )
            screen_buffer.append("")
            tokens_display = (
                f"🎯 [value]Tokens:[/]         [value]0[/] / "
                f"[dim]~{token_limit:,}[/] ([info]0 left[/])"
            )
            screen_buffer.append(tokens_display)
            burn_rate_display = (
                "🔥 [value]Burn Rate:[/]      [warning]0.0[/] [dim]tokens/min[/]"
            )
            screen_buffer.append(burn_rate_display)
            screen_buffer.append("")
            # Use configured timezone for time display
            display_tz = get_display_timezone(args.timezone)
            current_time_display = datetime.now(UTC_TZ).astimezone(display_tz)
            current_time_str = current_time_display.strftime("%H:%M:%S")
            status_line = (
                f"⏰ [dim]{current_time_str}[/] 📝 "
                f"[info]No active session[/] | "
                f"[dim]Ctrl+C to exit[/] 🟨"
            )
            screen_buffer.append(status_line)
            # Clear screen and print buffer with theme support
            console = get_themed_console()
            console.clear()
            for line in screen_buffer[1:]:  # Skip position control
                console.print(line)
            stop_event.wait(timeout=3.0)
            continue

        # Extract and process token data
        token_data = process_token_data(active_block, args, data["blocks"], token_limit)

        # Extract and process time data
        time_data = process_time_data(active_block, datetime.now(UTC_TZ))

        # Always use UTC for internal calculations
        current_time = datetime.now(UTC_TZ)

        # Calculate burn rate from ALL sessions in the last hour
        burn_rate = calculate_hourly_burn_rate(data["blocks"], current_time)

        # Calculate time to reset
        time_to_reset = time_data["reset_time"] - current_time
        minutes_to_reset = time_to_reset.total_seconds() / 60

        # Calculate predictions for display
        predictions = calculate_predictions(
            current_time,
            time_data["reset_time"],
            burn_rate,
            token_data["tokens_left"],
            args.timezone,
        )

        # Display header
        screen_buffer.extend(print_header())

        # Token Usage section
        token_progress = create_token_progress_bar(token_data["usage_percentage"])
        screen_buffer.append(f"📊 [value]Token Usage:[/]    {token_progress}")
        screen_buffer.append("")

        # Time to Reset section - calculate progress based on actual session duration
        if time_data["start_time"] and time_data["reset_time"]:
            # Calculate actual session duration and elapsed time
            total_session_minutes = (
                time_data["reset_time"] - time_data["start_time"]
            ).total_seconds() / 60
            elapsed_session_minutes = (
                current_time - time_data["start_time"]
            ).total_seconds() / 60
            elapsed_session_minutes = max(
                0, elapsed_session_minutes
            )  # Ensure non-negative
        else:
            # Fallback to 5 hours if times not available
            total_session_minutes = 300
            elapsed_session_minutes = max(0, 300 - minutes_to_reset)

        time_progress = create_time_progress_bar(
            elapsed_session_minutes, total_session_minutes
        )
        screen_buffer.append(f"⏳ [value]Time to Reset:[/]  {time_progress}")
        screen_buffer.append("")

        # Detailed stats
        tokens_details = (
            f"🎯 [value]Tokens:[/]         "
            f"[value]{token_data['tokens_used']:,}[/] / "
            f"[dim]~{token_limit:,}[/] "
            f"([info]{token_data['tokens_left']:,} left[/])"
        )
        screen_buffer.append(tokens_details)
        burn_rate_details = (
            f"🔥 [value]Burn Rate:[/]      "
            f"[warning]{burn_rate:.1f}[/] "
            f"[dim]tokens/min[/]"
        )
        screen_buffer.append(burn_rate_details)
        screen_buffer.append("")

        predicted_end_display = (
            f"🏁 [value]Predicted End:[/] {predictions['predicted_end_str']}"
        )
        screen_buffer.append(predicted_end_display)
        reset_time_display = (
            f"🔄 [value]Token Reset:[/]   {predictions['reset_time_str']}"
        )
        screen_buffer.append(reset_time_display)
        screen_buffer.append("")

        # Update persistent notifications using current conditions
        notifications = handle_notifications(
            token_data,
            predictions["predicted_end_time"],
            time_data["reset_time"],
            current_time,
            args,
        )

        # Normal mode - display existing notifications
        if notifications["show_switch"]:
            switch_msg = (
                f"🔄 [warning]Tokens exceeded {args.plan.upper()} "
                f"limit - switched to custom_max "
                f"({token_data['token_limit']:,})[/]"
            )
            screen_buffer.append(switch_msg)
            screen_buffer.append("")

        if notifications["show_exceed"]:
            exceed_msg = (
                f"🚨 [error]TOKENS EXCEEDED MAX LIMIT! "
                f"({token_data['tokens_used']:,} > "
                f"{token_data['token_limit']:,})[/]"
            )
            screen_buffer.append(exceed_msg)
            screen_buffer.append("")

        if notifications["show_will_run_out"]:
            screen_buffer.append("⚠️  [error]Tokens will run out BEFORE reset![/]")
            screen_buffer.append("")

        # Status line - use configured timezone for consistency
        display_tz = get_display_timezone(args.timezone)
        current_time_display = datetime.now(UTC_TZ).astimezone(display_tz)
        current_time_str = current_time_display.strftime("%H:%M:%S")
        status_line = (
            f"⏰ [dim]{current_time_str}[/] 📝 "
            f"[info]Smooth sailing...[/] | "
            f"[dim]Ctrl+C to exit[/] 🟨"
        )
        screen_buffer.append(status_line)

        # Clear screen and print entire buffer at once with theme support
        console = get_themed_console()
        console.clear()
        for line in screen_buffer[1:]:  # Skip position control
            console.print(line)

        stop_event.wait(timeout=3.0)


def main():
    """Main monitoring loop."""
    args = parse_args()

    # Handle theme setup
    if args.theme:
        theme_type = ThemeType(args.theme.lower())
        console = get_themed_console(force_theme=theme_type)
    else:
        console = get_themed_console()

    # Handle theme debug flag
    if args.theme_debug:
        from usage_analyzer.themes.console import debug_theme_info

        debug_info = debug_theme_info()
        print_themed("🎨 Theme Detection Debug Information", style="header")
        print_themed(f"Current theme: {debug_info['current_theme']}", style="info")
        print_themed(
            f"Console initialized: {debug_info['console_initialized']}", style="value"
        )

        detector_info = debug_info["detector_info"]
        print_themed("Environment variables:", style="subheader")
        for key, value in detector_info["environment_vars"].items():
            if value:
                print_themed(f"  {key}: {value}", style="label")

        caps = detector_info["terminal_capabilities"]
        print_themed(
            f"Terminal capabilities: {caps['colors']} colors, truecolor: {caps['truecolor']}",
            style="info",
        )
        print_themed(f"Platform: {detector_info['platform']}", style="value")
        return

    # Create event for clean refresh timing
    stop_event = threading.Event()

    # Setup terminal to prevent input interference
    old_terminal_settings = setup_terminal()

    # For 'custom_max' plan, we need to get data first to determine the limit
    if args.plan == "custom_max":
        print_themed(
            "Fetching initial data to determine custom max token limit...", style="info"
        )
        initial_data = analyze_usage()
        if initial_data and "blocks" in initial_data:
            token_limit = get_token_limit(args.plan, initial_data["blocks"])
            print_themed(
                f"Custom max token limit detected: {token_limit:,}", style="info"
            )
        else:
            token_limit = get_token_limit("pro")  # Fallback to pro
            print_themed(
                f"Failed to fetch data, falling back to Pro limit: {token_limit:,}",
                style="warning",
            )
    else:
        token_limit = get_token_limit(args.plan)

    # Initialize compact formatter if needed
    compact_formatter = None
    if args.compact:
        compact_formatter = CompactFormatter()

    try:
        # Enter alternate screen buffer, clear and hide cursor
        print("\033[?1049h\033[2J\033[H\033[?25l", end="", flush=True)

        # Show loading screen immediately
        show_loading_screen()

        if args.compact:
            run_compact_mode(args, token_limit, compact_formatter, stop_event)
        else:
            run_normal_mode(args, token_limit, stop_event)
    except KeyboardInterrupt:
        # Set the stop event for immediate response
        stop_event.set()
        # Restore terminal settings
        restore_terminal(old_terminal_settings)
        print_themed("\n\nMonitoring stopped.", style="info")
        sys.exit(0)
    except Exception as e:
        # Restore terminal on any error
        restore_terminal(old_terminal_settings)
        print(f"\n\nError: {e}")
        raise


if __name__ == "__main__":
    main()
