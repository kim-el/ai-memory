# AI Memory — silent, no noise on terminal startup
if [ -x "$HOME/.ai-log/ai-memory" ]; then
    export PATH="$HOME/.ai-log:$PATH"
    # Only show banner for AI agent shells, never for user terminals
    if [ -n "$CLAUDE_SESSION_ID" ] || [ -n "$OPENCODE_SESSION" ]; then
        echo "[memory] ask me anything about past work"
    fi
fi
